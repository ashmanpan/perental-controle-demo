"""
SQS Client for Policy Enforcer
"""
import json
import logging
from typing import List, Dict, Optional
import boto3

from .config import Config

logger = logging.getLogger(__name__)


class SQSClient:
    """SQS client for receiving enforcement requests"""

    def __init__(self, config: Config):
        self.config = config
        self.sqs = boto3.client('sqs', region_name=config.aws_region)
        self.queue_url = config.sqs.queue_url

    def receive_messages(self) -> List[Dict]:
        """Receive messages from SQS queue"""
        if not self.queue_url:
            logger.warning("No SQS queue URL configured, skipping message receive")
            return []

        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.config.sqs.max_messages,
                WaitTimeSeconds=self.config.sqs.wait_time_seconds,
                VisibilityTimeout=self.config.sqs.visibility_timeout,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )

            messages = response.get('Messages', [])
            logger.debug(f"Received {len(messages)} messages from SQS")
            return messages
        except Exception as e:
            logger.error(f"Failed to receive SQS messages: {e}")
            return []

    def parse_message(self, message: Dict) -> Optional[Dict]:
        """Parse SQS message body"""
        try:
            body = json.loads(message['Body'])
            return {
                'receipt_handle': message['ReceiptHandle'],
                'message_id': message['MessageId'],
                'event_type': body.get('eventType'),
                'msisdn': body.get('msisdn'),
                'private_ip': body.get('privateIP'),
                'policies': body.get('policies', [])
            }
        except Exception as e:
            logger.error(f"Failed to parse SQS message: {e}")
            return None

    def delete_message(self, receipt_handle: str) -> bool:
        """Delete message from queue after successful processing"""
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.debug("Deleted message from SQS queue")
            return True
        except Exception as e:
            logger.error(f"Failed to delete SQS message: {e}")
            return False

    def change_message_visibility(self, receipt_handle: str, timeout: int) -> bool:
        """Change message visibility timeout (for retry logic)"""
        try:
            self.sqs.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=timeout
            )
            return True
        except Exception as e:
            logger.error(f"Failed to change message visibility: {e}")
            return False
