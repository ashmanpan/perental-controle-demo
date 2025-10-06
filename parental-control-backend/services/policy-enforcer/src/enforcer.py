"""
Policy Enforcer - Main Orchestrator
Enforces parental control policies by creating FTD firewall rules
"""
import logging
import signal
import sys
import time
from typing import Dict, List
from datetime import datetime

from config import load_config
from redis_client import RedisClient
from dynamodb_client import DynamoDBClient
from sqs_client import SQSClient
from ftd_client import FTDClient

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Main policy enforcement orchestrator"""

    def __init__(self):
        self.config = load_config()
        self.redis_client = RedisClient(self.config)
        self.dynamodb_client = DynamoDBClient(self.config)
        self.sqs_client = SQSClient(self.config)
        self.ftd_client = FTDClient(self.config)

        self.running = False
        self.enforcement_count = 0
        self.enforcement_success = 0
        self.enforcement_failed = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def start(self):
        """Start the policy enforcer"""
        logger.info("Starting Policy Enforcer...")
        self.running = True

        # Health checks
        if not self.redis_client.health_check():
            logger.error("Redis health check failed")
            sys.exit(1)

        if not self.ftd_client.health_check():
            logger.warning("FTD Integration Service health check failed (may not be running)")

        # Main processing loop
        try:
            while self.running:
                loop_start = time.time()

                # Process SQS messages
                self._process_sqs_messages()

                # Log stats periodically
                if self.enforcement_count % 10 == 0 and self.enforcement_count > 0:
                    self._log_stats()

                # Sleep to maintain interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.config.enforcement_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Enforcer error: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _process_sqs_messages(self):
        """Process enforcement requests from SQS"""
        messages = self.sqs_client.receive_messages()

        for message in messages:
            parsed = self.sqs_client.parse_message(message)
            if not parsed:
                continue

            event_type = parsed['event_type']
            msisdn = parsed['msisdn']
            private_ip = parsed['private_ip']
            policies = parsed['policies']

            logger.info(f"Processing {event_type} for {msisdn}")

            # Handle different event types
            if event_type == 'SESSION_START':
                success = self._enforce_policies(msisdn, private_ip, policies)
            elif event_type == 'IP_CHANGE':
                success = self._handle_ip_change(msisdn, private_ip, policies)
            elif event_type == 'SESSION_END':
                success = self._cleanup_rules(msisdn)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                success = False

            # Delete message if successful
            if success:
                self.sqs_client.delete_message(parsed['receipt_handle'])
            else:
                # Make message visible again after 60 seconds for retry
                self.sqs_client.change_message_visibility(parsed['receipt_handle'], 60)

    def _enforce_policies(self, msisdn: str, private_ip: str, policies: List[Dict]) -> bool:
        """Enforce policies by creating FTD rules"""
        all_success = True

        for policy in policies:
            blocked_apps = policy.get('blockedApps', [])
            parent_email = policy.get('parentEmail', '')

            for app in blocked_apps:
                app_name = app['appName']
                ports = app.get('ports', [])

                # Create FTD block rule
                result = self.ftd_client.create_block_rule(
                    private_ip=private_ip,
                    app_name=app_name,
                    ports=ports,
                    msisdn=msisdn
                )

                if result:
                    rule_id = result.get('ruleId', '')
                    rule_name = result.get('ruleName', '')

                    # Save FTD rule mapping
                    self.dynamodb_client.save_ftd_rule_mapping(
                        msisdn=msisdn,
                        rule_id=rule_id,
                        rule_name=rule_name,
                        private_ip=private_ip,
                        app_name=app_name,
                        policy_id=policy['policyId'],
                        ftd_device_id=result.get('deviceId')
                    )

                    # Log success
                    self.dynamodb_client.log_enforcement(
                        msisdn=msisdn,
                        action='block',
                        app_name=app_name,
                        private_ip=private_ip,
                        status='success',
                        rule_id=rule_id,
                        ftd_response=result
                    )

                    # Increment metrics
                    self.dynamodb_client.increment_blocked_metric(
                        msisdn=msisdn,
                        app_name=app_name,
                        parent_email=parent_email
                    )

                    self.enforcement_success += 1
                    logger.info(f"Enforced block for {app_name} on {msisdn}")
                else:
                    # Log failure
                    self.dynamodb_client.log_enforcement(
                        msisdn=msisdn,
                        action='block',
                        app_name=app_name,
                        private_ip=private_ip,
                        status='failed',
                        error_message='Failed to create FTD rule'
                    )

                    self.enforcement_failed += 1
                    all_success = False
                    logger.error(f"Failed to enforce block for {app_name} on {msisdn}")

                self.enforcement_count += 1

        return all_success

    def _handle_ip_change(self, msisdn: str, new_private_ip: str, policies: List[Dict]) -> bool:
        """Handle IP address change by updating FTD rules"""
        logger.info(f"Handling IP change for {msisdn} to {new_private_ip}")

        # Get existing FTD rules for this phone number
        existing_rules = self.dynamodb_client.get_ftd_rules_for_phone(msisdn)

        all_success = True

        for rule in existing_rules:
            rule_id = rule['ruleId']
            old_ip = rule['privateIP']

            # Update rule with new IP
            result = self.ftd_client.update_block_rule(
                rule_id=rule_id,
                new_private_ip=new_private_ip,
                msisdn=msisdn
            )

            if result:
                # Update mapping with new IP
                self.dynamodb_client.save_ftd_rule_mapping(
                    msisdn=msisdn,
                    rule_id=rule_id,
                    rule_name=rule['ruleName'],
                    private_ip=new_private_ip,
                    app_name=rule['appName'],
                    policy_id=rule['policyId'],
                    ftd_device_id=rule.get('ftdDeviceId')
                )

                # Log success
                self.dynamodb_client.log_enforcement(
                    msisdn=msisdn,
                    action='update',
                    app_name=rule['appName'],
                    private_ip=new_private_ip,
                    status='success',
                    rule_id=rule_id
                )

                logger.info(f"Updated rule {rule_id}: {old_ip} -> {new_private_ip}")
            else:
                all_success = False
                logger.error(f"Failed to update rule {rule_id} for {msisdn}")

        return all_success

    def _cleanup_rules(self, msisdn: str) -> bool:
        """Clean up FTD rules when session ends"""
        logger.info(f"Cleaning up rules for {msisdn}")

        # Get all FTD rules for this phone number
        rules = self.dynamodb_client.get_ftd_rules_for_phone(msisdn)

        all_success = True

        for rule in rules:
            rule_id = rule['ruleId']

            # Delete FTD rule
            success = self.ftd_client.delete_block_rule(rule_id, msisdn)

            if success:
                # Delete mapping
                self.dynamodb_client.delete_ftd_rule_mapping(msisdn, rule_id)

                # Log cleanup
                self.dynamodb_client.log_enforcement(
                    msisdn=msisdn,
                    action='unblock',
                    app_name=rule['appName'],
                    private_ip=rule['privateIP'],
                    status='success',
                    rule_id=rule_id
                )

                logger.info(f"Deleted rule {rule_id} for {msisdn}")
            else:
                all_success = False
                logger.error(f"Failed to delete rule {rule_id} for {msisdn}")

        return all_success

    def _log_stats(self):
        """Log statistics"""
        logger.info(
            f"Stats - Total: {self.enforcement_count}, "
            f"Success: {self.enforcement_success}, "
            f"Failed: {self.enforcement_failed}"
        )

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Policy Enforcer...")
        self._log_stats()
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    # Configure logging
    log_level = load_config().log_level
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=" * 80)
    logger.info("Policy Enforcement Service")
    logger.info("Cisco Parental Control - FTD Rule Orchestrator")
    logger.info("=" * 80)

    try:
        enforcer = PolicyEnforcer()
        enforcer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
