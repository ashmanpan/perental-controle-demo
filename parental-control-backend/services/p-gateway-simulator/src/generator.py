"""
P-Gateway Simulator - Main Generator
Simulates 5G SA P-Gateway session behavior and publishes to Kafka
"""
import time
import random
import logging
import signal
import sys
from datetime import datetime
from typing import List

from config import get_config
from session_manager import SessionManager, UserDatabase
from kafka_producer import SessionEventProducer, CloudWatchMetrics, create_topics_if_not_exist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PGatewaySimulator:
    """Main P-Gateway Simulator"""

    def __init__(self):
        self.config = get_config()
        self.session_manager = SessionManager()
        self.user_db = UserDatabase(self.config.simulation.test_users_count)
        self.kafka_producer = SessionEventProducer()
        self.cloudwatch = CloudWatchMetrics()

        self.running = False
        self.iteration_count = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("P-Gateway Simulator initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def start(self):
        """Start the simulator"""
        logger.info("Starting P-Gateway Simulator...")
        logger.info(f"Configuration: {self.config.simulation.sessions_per_second} sessions/second")

        # Create Kafka topics if needed
        try:
            create_topics_if_not_exist()
        except Exception as e:
            logger.warning(f"Could not create topics (may already exist): {e}")

        self.running = True

        # Main simulation loop
        last_metric_publish = time.time()
        metric_interval = self.config.monitoring.metrics_interval

        try:
            while self.running:
                loop_start = time.time()

                # Create new sessions
                self._create_sessions()

                # Process existing sessions (check expirations, IP changes)
                self._process_sessions()

                # Publish metrics periodically
                if time.time() - last_metric_publish >= metric_interval:
                    self._publish_metrics()
                    last_metric_publish = time.time()

                # Log statistics
                if self.iteration_count % 10 == 0:
                    self._log_stats()

                self.iteration_count += 1

                # Sleep to maintain desired rate (1 second per iteration)
                elapsed = time.time() - loop_start
                sleep_time = max(0, 1.0 - elapsed)
                time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Simulator error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _create_sessions(self):
        """Create new sessions according to configured rate"""
        for _ in range(self.config.simulation.sessions_per_second):
            try:
                # Get random user
                imsi, phone = self.user_db.get_random_user()

                # Check if user already has active session
                existing = self.session_manager.get_session_by_phone(phone)
                if existing:
                    continue  # Skip if user already has session

                # Create session
                session = self.session_manager.create_session(imsi, phone)

                # Publish to Kafka
                self.kafka_producer.publish_session_start(session)

            except Exception as e:
                logger.error(f"Failed to create session: {e}")

    def _process_sessions(self):
        """Process existing sessions for expirations and IP changes"""
        # Check for expired sessions
        expired_sessions = self.session_manager.get_expired_sessions()
        for session in expired_sessions:
            self._terminate_session(session.session_id, "EXPIRED")

        # Random early terminations
        active_sessions = self.session_manager.get_active_sessions()
        for session in active_sessions:
            # Early termination
            if random.random() < self.config.simulation.early_termination_probability / 100:
                self._terminate_session(session.session_id, "USER_INITIATED")

            # IP change (simulates handover)
            elif random.random() < self.config.simulation.ip_change_probability / 100:
                self._change_session_ip(session.session_id)

    def _terminate_session(self, session_id: str, reason: str):
        """Terminate a session"""
        try:
            session = self.session_manager.terminate_session(session_id)
            if session:
                # Publish termination event
                self.kafka_producer.publish_session_end(session)
                logger.debug(f"Session {session_id} terminated: {reason}")
        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")

    def _change_session_ip(self, session_id: str):
        """Change IP for a session"""
        try:
            result = self.session_manager.change_session_ip(session_id)
            if result:
                old_private, new_private, old_public, new_public = result
                session = self.session_manager.sessions[session_id]

                # Publish IP change event
                self.kafka_producer.publish_ip_change(
                    session,
                    old_private,
                    old_public
                )
                logger.debug(f"IP changed for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to change IP for session {session_id}: {e}")

    def _publish_metrics(self):
        """Publish metrics to CloudWatch"""
        try:
            stats = self.session_manager.get_stats()
            kafka_stats = self.kafka_producer.get_stats()

            metrics = {
                'ActiveSessions': stats['active_sessions'],
                'TotalSessionsCreated': stats['total_created'],
                'TotalSessionsTerminated': stats['total_terminated'],
                'TotalIPChanges': stats['total_ip_changes'],
                'KafkaPublishSuccess': kafka_stats['publish_success'],
                'KafkaPublishFailure': kafka_stats['publish_failure'],
                'PrivateIPsAvailable': stats['private_ips_available'],
                'PublicIPsAvailable': stats['public_ips_available']
            }

            self.cloudwatch.put_metrics(metrics)
            logger.debug(f"Published {len(metrics)} metrics to CloudWatch")

        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")

    def _log_stats(self):
        """Log current statistics"""
        stats = self.session_manager.get_stats()
        kafka_stats = self.kafka_producer.get_stats()

        logger.info(
            f"Stats - Active: {stats['active_sessions']}, "
            f"Created: {stats['total_created']}, "
            f"Terminated: {stats['total_terminated']}, "
            f"IP Changes: {stats['total_ip_changes']}, "
            f"Kafka Success: {kafka_stats['publish_success']}, "
            f"Kafka Failures: {kafka_stats['publish_failure']}"
        )

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down simulator...")

        # Terminate all active sessions
        active_sessions = self.session_manager.get_active_sessions()
        logger.info(f"Terminating {len(active_sessions)} active sessions...")

        for session in active_sessions:
            self._terminate_session(session.session_id, "SHUTDOWN")

        # Flush Kafka producer
        self.kafka_producer.close()

        # Final stats
        self._log_stats()

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    logger.info("=" * 80)
    logger.info("P-Gateway Simulator (5G SA)")
    logger.info("Cisco Parental Control - Session Data Generator")
    logger.info("=" * 80)

    try:
        simulator = PGatewaySimulator()
        simulator.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
