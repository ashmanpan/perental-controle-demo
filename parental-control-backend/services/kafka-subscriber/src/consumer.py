"""
Kafka Consumer - Consumes session events and updates Redis
"""
import json
import logging
import signal
import sys
from typing import Dict
from confluent_kafka import Consumer, KafkaError, KafkaException

from config import load_config
from redis_updater import RedisUpdater
from policy_checker import PolicyChecker

logger = logging.getLogger(__name__)


class SessionEventConsumer:
    """Consumes session events from Kafka"""

    def __init__(self):
        self.config = load_config()
        self.consumer = self._create_consumer()
        self.redis_updater = RedisUpdater(self.config)
        self.policy_checker = PolicyChecker(self.config)

        self.running = False
        self.messages_processed = 0
        self.messages_failed = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _create_consumer(self) -> Consumer:
        """Create Kafka consumer"""
        consumer_config = {
            'bootstrap.servers': self.config.kafka.bootstrap_servers,
            'group.id': self.config.kafka.group_id,
            'auto.offset.reset': self.config.kafka.auto_offset_reset,
            'enable.auto.commit': self.config.kafka.enable_auto_commit,
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 45000,
            'client.id': 'parental-control-subscriber'
        }

        # Add security for AWS MSK
        if self.config.kafka.security_protocol == 'SASL_SSL':
            consumer_config.update({
                'security.protocol': 'SASL_SSL',
                'sasl.mechanism': 'AWS_MSK_IAM',
            })

        logger.info(f"Creating Kafka consumer for group: {self.config.kafka.group_id}")
        return Consumer(consumer_config)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def start(self):
        """Start consuming messages"""
        logger.info("Starting Kafka consumer...")
        logger.info(f"Subscribing to topic: {self.config.kafka.topic}")

        try:
            # Subscribe to topic
            self.consumer.subscribe([self.config.kafka.topic])
            self.running = True

            # Main consumption loop
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition - not an error
                        logger.debug(f"Reached end of partition {msg.partition()}")
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                # Process message
                self._process_message(msg)

                # Commit offset manually if auto-commit is disabled
                if not self.config.kafka.enable_auto_commit:
                    self.consumer.commit(asynchronous=False)

                # Log stats periodically
                if self.messages_processed % 100 == 0:
                    self._log_stats()

        except KafkaException as e:
            logger.error(f"Kafka exception: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _process_message(self, msg):
        """Process a single Kafka message"""
        try:
            # Parse JSON message
            event = json.loads(msg.value().decode('utf-8'))
            event_type = event.get('eventType')

            logger.debug(f"Processing {event_type} event for {event.get('msisdn')}")

            # Handle different event types
            if event_type == 'SESSION_START':
                self._handle_session_start(event)
            elif event_type == 'SESSION_END':
                self._handle_session_end(event)
            elif event_type == 'IP_CHANGE':
                self._handle_ip_change(event)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return

            self.messages_processed += 1

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            self.messages_failed += 1
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            self.messages_failed += 1

    def _handle_session_start(self, event: Dict):
        """Handle SESSION_START event"""
        # Update Redis with session mapping
        success = self.redis_updater.handle_session_start(event)

        if not success:
            logger.error("Failed to update Redis for SESSION_START")
            return

        # Check if policy exists for this phone number
        msisdn = event['msisdn']
        private_ip = event['privateIP']

        if self.policy_checker.check_policy_exists(msisdn):
            logger.info(f"Policy found for {msisdn}, triggering enforcement")
            self.policy_checker.trigger_policy_enforcement(
                msisdn,
                private_ip,
                'SESSION_START'
            )

    def _handle_session_end(self, event: Dict):
        """Handle SESSION_END event"""
        # Update Redis (remove mappings)
        success = self.redis_updater.handle_session_end(event)

        if not success:
            logger.error("Failed to update Redis for SESSION_END")
            return

        # Optionally: Trigger policy cleanup
        msisdn = event['msisdn']
        private_ip = event['privateIP']

        if self.policy_checker.check_policy_exists(msisdn):
            logger.info(f"Policy found for {msisdn}, triggering cleanup")
            self.policy_checker.trigger_policy_enforcement(
                msisdn,
                private_ip,
                'SESSION_END'
            )

    def _handle_ip_change(self, event: Dict):
        """Handle IP_CHANGE event"""
        # Update Redis with new IP mapping
        success = self.redis_updater.handle_ip_change(event)

        if not success:
            logger.error("Failed to update Redis for IP_CHANGE")
            return

        # Check if policy exists and trigger enforcement with new IP
        msisdn = event['msisdn']
        new_private_ip = event['newPrivateIP']

        if self.policy_checker.check_policy_exists(msisdn):
            logger.info(f"Policy found for {msisdn}, triggering enforcement for new IP")
            self.policy_checker.trigger_policy_enforcement(
                msisdn,
                new_private_ip,
                'IP_CHANGE'
            )

    def _log_stats(self):
        """Log statistics"""
        redis_stats = self.redis_updater.get_stats()
        policy_stats = self.policy_checker.get_stats()

        logger.info(
            f"Stats - Processed: {self.messages_processed}, "
            f"Failed: {self.messages_failed}, "
            f"Redis Success: {redis_stats['updates_success']}, "
            f"Active Sessions: {redis_stats['active_sessions']}, "
            f"Policies Found: {policy_stats['policies_found']}, "
            f"Enforcement Triggered: {policy_stats['enforcement_triggered']}"
        )

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down consumer...")

        try:
            # Close consumer
            self.consumer.close()
            logger.info("Kafka consumer closed")

            # Final stats
            self._log_stats()

            # Health check
            if self.redis_updater.health_check():
                logger.info("Redis connection healthy")
            else:
                logger.warning("Redis connection unhealthy")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point"""
    # Configure logging
    log_level = load_config().log_level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 80)
    logger.info("Kafka Subscriber Service")
    logger.info("Cisco Parental Control - Session Event Consumer")
    logger.info("=" * 80)

    try:
        consumer = SessionEventConsumer()
        consumer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
