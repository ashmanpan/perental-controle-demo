"""
DynamoDB Client for Policy Enforcer
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

from config import Config

logger = logging.getLogger(__name__)


class DynamoDBClient:
    """DynamoDB client for policies, history, and metrics"""

    def __init__(self, config: Config):
        self.config = config
        self.dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)

        self.policies_table = self.dynamodb.Table(config.dynamodb.table_policies)
        self.app_registry_table = self.dynamodb.Table(config.dynamodb.table_app_registry)
        self.history_table = self.dynamodb.Table(config.dynamodb.table_enforcement_history)
        self.ftd_mapping_table = self.dynamodb.Table(config.dynamodb.table_ftd_rule_mapping)
        self.metrics_table = self.dynamodb.Table(config.dynamodb.table_blocked_metrics)

    def get_active_policies(self, msisdn: str) -> List[Dict]:
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

    def get_app_details(self, app_name: str) -> Optional[Dict]:
        """Get application details from registry"""
        try:
            response = self.app_registry_table.get_item(Key={'appName': app_name})
            if 'Item' in response:
                return response['Item']
            return None
        except Exception as e:
            logger.error(f"Failed to get app details for {app_name}: {e}")
            return None

    def log_enforcement(self,
                       msisdn: str,
                       action: str,
                       app_name: str,
                       private_ip: str,
                       status: str,
                       rule_id: Optional[str] = None,
                       error_message: Optional[str] = None,
                       ftd_response: Optional[Dict] = None) -> bool:
        """Log enforcement action to history table"""
        try:
            timestamp = datetime.utcnow().isoformat() + 'Z'

            # Calculate TTL (90 days from now)
            ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())

            item = {
                'childPhoneNumber': msisdn,
                'timestamp': timestamp,
                'action': action,
                'appName': app_name,
                'privateIP': private_ip,
                'ruleId': rule_id or '',
                'status': status,
                'errorMessage': error_message or '',
                'ftdResponse': ftd_response or {},
                'ttl': ttl
            }

            self.history_table.put_item(Item=item)
            logger.debug(f"Logged enforcement: {action} {app_name} for {msisdn}")
            return True
        except Exception as e:
            logger.error(f"Failed to log enforcement: {e}")
            return False

    def save_ftd_rule_mapping(self,
                             msisdn: str,
                             rule_id: str,
                             rule_name: str,
                             private_ip: str,
                             app_name: str,
                             policy_id: str,
                             ftd_device_id: Optional[str] = None) -> bool:
        """Save FTD rule mapping for tracking"""
        try:
            timestamp = datetime.utcnow().isoformat() + 'Z'

            # Calculate TTL (24 hours from now - will be refreshed if session continues)
            ttl = int((datetime.utcnow() + timedelta(hours=24)).timestamp())

            item = {
                'childPhoneNumber': msisdn,
                'ruleId': rule_id,
                'ruleName': rule_name,
                'privateIP': private_ip,
                'appName': app_name,
                'policyId': policy_id,
                'ftdDeviceId': ftd_device_id or '',
                'status': 'active',
                'createdAt': timestamp,
                'lastVerified': timestamp,
                'ttl': ttl
            }

            self.ftd_mapping_table.put_item(Item=item)
            logger.debug(f"Saved FTD rule mapping: {rule_id} for {msisdn}")
            return True
        except Exception as e:
            logger.error(f"Failed to save FTD rule mapping: {e}")
            return False

    def get_ftd_rules_for_phone(self, msisdn: str) -> List[Dict]:
        """Get all FTD rules for a phone number"""
        try:
            response = self.ftd_mapping_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(msisdn)
            )

            rules = response.get('Items', [])
            logger.debug(f"Found {len(rules)} FTD rules for {msisdn}")
            return rules
        except Exception as e:
            logger.error(f"Failed to get FTD rules for {msisdn}: {e}")
            return []

    def delete_ftd_rule_mapping(self, msisdn: str, rule_id: str) -> bool:
        """Delete FTD rule mapping"""
        try:
            self.ftd_mapping_table.delete_item(
                Key={
                    'childPhoneNumber': msisdn,
                    'ruleId': rule_id
                }
            )
            logger.debug(f"Deleted FTD rule mapping: {rule_id} for {msisdn}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete FTD rule mapping: {e}")
            return False

    def increment_blocked_metric(self,
                                msisdn: str,
                                app_name: str,
                                parent_email: str) -> bool:
        """Increment blocked request counter for metrics"""
        try:
            now = datetime.utcnow()
            date = now.strftime('%Y-%m-%d')
            hour = now.strftime('%H')
            timestamp = now.isoformat() + 'Z'

            # Calculate TTL (1 year from now)
            ttl = int((datetime.utcnow() + timedelta(days=365)).timestamp())

            # Update or create metric record
            response = self.metrics_table.update_item(
                Key={
                    'childPhoneNumber': msisdn,
                    'dateApp': f"{date}#{app_name}"
                },
                UpdateExpression='''
                    SET
                        #date = :date,
                        appName = :appName,
                        parentEmail = :parentEmail,
                        timestampLast = :timestamp,
                        #ttl = :ttl
                    ADD
                        blockedCount :inc,
                        hourly.#hour :inc
                ''',
                ExpressionAttributeNames={
                    '#date': 'date',
                    '#hour': hour,
                    '#ttl': 'ttl'
                },
                ExpressionAttributeValues={
                    ':date': date,
                    ':appName': app_name,
                    ':parentEmail': parent_email,
                    ':timestamp': timestamp,
                    ':inc': 1,
                    ':ttl': ttl
                },
                ReturnValues='NONE'
            )

            logger.debug(f"Incremented blocked metric for {msisdn} - {app_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to increment blocked metric: {e}")
            return False

    def get_daily_metrics(self, msisdn: str, date: str) -> List[Dict]:
        """Get daily metrics for a phone number"""
        try:
            response = self.metrics_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(msisdn)
                                     & Key('dateApp').begins_with(date)
            )

            metrics = response.get('Items', [])
            return metrics
        except Exception as e:
            logger.error(f"Failed to get daily metrics: {e}")
            return []
