"""
Policy Checker - Checks for parental control policies in DynamoDB
"""
import logging
from typing import Dict, Optional, List
import boto3
from boto3.dynamodb.conditions import Key
import json

from .config import Config

logger = logging.getLogger(__name__)


class PolicyChecker:
    """Checks and retrieves parental control policies"""

    def __init__(self, config: Config):
        self.config = config
        self.dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
        self.policies_table = self.dynamodb.Table(config.dynamodb.table_policies)

        # SQS for policy enforcement queue (optional)
        self.sqs = boto3.client('sqs', region_name=config.aws_region)
        self.enforcement_queue_url = self._get_enforcement_queue_url()

        # Statistics
        self.policies_found = 0
        self.policies_not_found = 0
        self.enforcement_triggered = 0

    def _get_enforcement_queue_url(self) -> Optional[str]:
        """Get SQS queue URL for policy enforcement"""
        queue_name = 'parental-control-enforcement-queue'
        try:
            response = self.sqs.get_queue_url(QueueName=queue_name)
            url = response['QueueUrl']
            logger.info(f"Found enforcement queue: {url}")
            return url
        except Exception as e:
            logger.warning(f"Enforcement queue not found: {e}")
            return None

    def check_policy_exists(self, msisdn: str) -> bool:
        """Check if a policy exists for the given phone number"""
        try:
            response = self.policies_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(msisdn),
                Limit=1
            )

            exists = response['Count'] > 0
            if exists:
                self.policies_found += 1
            else:
                self.policies_not_found += 1

            return exists

        except Exception as e:
            logger.error(f"Failed to check policy for {msisdn}: {e}")
            return False

    def get_policies(self, msisdn: str) -> List[Dict]:
        """Get all active policies for a phone number"""
        try:
            response = self.policies_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(msisdn),
                FilterExpression='#status = :active',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':active': 'active'}
            )

            policies = response.get('Items', [])
            logger.debug(f"Found {len(policies)} active policies for {msisdn}")
            return policies

        except Exception as e:
            logger.error(f"Failed to get policies for {msisdn}: {e}")
            return []

    def trigger_policy_enforcement(self, msisdn: str, private_ip: str, event_type: str) -> bool:
        """Trigger policy enforcement by sending message to enforcement queue"""
        if not self.enforcement_queue_url:
            logger.warning("No enforcement queue configured, skipping enforcement trigger")
            return False

        try:
            # Get active policies
            policies = self.get_policies(msisdn)

            if not policies:
                logger.debug(f"No active policies for {msisdn}, skipping enforcement")
                return False

            # Prepare enforcement message
            message = {
                'eventType': event_type,  # SESSION_START, IP_CHANGE
                'msisdn': msisdn,
                'privateIP': private_ip,
                'policies': policies,
                'timestamp': None  # Will be set by consumer
            }

            # Send to SQS
            response = self.sqs.send_message(
                QueueUrl=self.enforcement_queue_url,
                MessageBody=json.dumps(message),
                MessageGroupId=msisdn,  # For FIFO queue (ensures ordering per user)
                MessageDeduplicationId=f"{msisdn}_{private_ip}_{event_type}"
            )

            self.enforcement_triggered += 1
            logger.info(
                f"Policy enforcement triggered for {msisdn} "
                f"(MessageId: {response['MessageId']})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to trigger enforcement for {msisdn}: {e}")
            return False

    def get_app_details(self, app_name: str) -> Optional[Dict]:
        """Get application details from ApplicationRegistry table"""
        try:
            app_table = self.dynamodb.Table(self.config.dynamodb.table_app_registry)
            response = app_table.get_item(Key={'appName': app_name})

            if 'Item' in response:
                return response['Item']
            return None

        except Exception as e:
            logger.error(f"Failed to get app details for {app_name}: {e}")
            return None

    def get_stats(self) -> Dict:
        """Get statistics"""
        return {
            'policies_found': self.policies_found,
            'policies_not_found': self.policies_not_found,
            'enforcement_triggered': self.enforcement_triggered
        }
