"""
Analytics Client - Retrieves metrics from DynamoDB and session data from Redis
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import boto3
from boto3.dynamodb.conditions import Key
import redis
from redis.connection import ConnectionPool, SSLConnection

from .config import Config

logger = logging.getLogger(__name__)


class AnalyticsClient:
    """Client for retrieving parental control analytics"""

    def __init__(self, config: Config):
        self.config = config
        self.dynamodb = boto3.resource('dynamodb', region_name=config.dynamodb.region)

        self.policies_table = self.dynamodb.Table(config.dynamodb.table_policies)
        self.metrics_table = self.dynamodb.Table(config.dynamodb.table_metrics)
        self.history_table = self.dynamodb.Table(config.dynamodb.table_history)

        # Initialize Redis client for session data
        self.redis_client = self._create_redis_client()

    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pooling"""
        pool_kwargs = {
            'host': self.config.redis.host,
            'port': self.config.redis.port,
            'db': self.config.redis.db,
            'decode_responses': self.config.redis.decode_responses,
            'socket_timeout': self.config.redis.socket_timeout,
            'max_connections': self.config.redis.max_connections
        }

        if self.config.redis.password:
            pool_kwargs['password'] = self.config.redis.password

        if self.config.redis.ssl:
            pool_kwargs['connection_class'] = SSLConnection
            pool_kwargs['ssl_cert_reqs'] = None

        pool = ConnectionPool(**pool_kwargs)
        client = redis.Redis(connection_pool=pool)

        # Test connection
        try:
            client.ping()
            logger.info(f"Connected to Redis: {self.config.redis.host}:{self.config.redis.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        return client

    def get_children_for_parent(self, parent_email: str) -> List[Dict]:
        """Get all children managed by a parent"""
        try:
            response = self.policies_table.query(
                IndexName='ParentEmailIndex',
                KeyConditionExpression=Key('parentEmail').eq(parent_email)
            )

            # Deduplicate by phone number
            children = {}
            for policy in response.get('Items', []):
                phone = policy['childPhoneNumber']
                if phone not in children:
                    children[phone] = {
                        'phoneNumber': phone,
                        'name': policy.get('childName', 'Unknown'),
                        'status': policy.get('status', 'unknown')
                    }

            return list(children.values())
        except Exception as e:
            logger.error(f"Failed to get children for parent: {e}")
            return []

    def get_daily_summary(self, child_phone: str, date: str) -> Dict:
        """Get daily blocked requests summary for a child"""
        try:
            response = self.metrics_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(child_phone)
                                     & Key('dateApp').begins_with(date)
            )

            items = response.get('Items', [])

            # Aggregate metrics
            total_blocked = sum(item.get('blockedCount', 0) for item in items)

            apps_breakdown = {}
            hourly_breakdown = defaultdict(int)

            for item in items:
                app_name = item.get('appName', 'Unknown')
                blocked_count = item.get('blockedCount', 0)

                apps_breakdown[app_name] = blocked_count

                # Aggregate hourly data
                hourly = item.get('hourly', {})
                for hour, count in hourly.items():
                    hourly_breakdown[hour] += count

            return {
                'date': date,
                'childPhoneNumber': child_phone,
                'totalBlocked': total_blocked,
                'appBreakdown': apps_breakdown,
                'hourlyBreakdown': dict(hourly_breakdown)
            }
        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}")
            return {}

    def get_weekly_summary(self, child_phone: str) -> Dict:
        """Get 7-day summary for a child"""
        try:
            # Get last 7 days
            daily_summaries = []
            total_weekly_blocked = 0

            for i in range(7):
                date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
                summary = self.get_daily_summary(child_phone, date)

                daily_summaries.append(summary)
                total_weekly_blocked += summary.get('totalBlocked', 0)

            # Calculate app totals
            app_totals = defaultdict(int)
            for summary in daily_summaries:
                for app, count in summary.get('appBreakdown', {}).items():
                    app_totals[app] += count

            return {
                'childPhoneNumber': child_phone,
                'period': '7days',
                'totalBlocked': total_weekly_blocked,
                'dailySummaries': daily_summaries,
                'topApps': dict(sorted(app_totals.items(), key=lambda x: x[1], reverse=True)[:5])
            }
        except Exception as e:
            logger.error(f"Failed to get weekly summary: {e}")
            return {}

    def get_enforcement_history(self, child_phone: str, limit: int = 50) -> List[Dict]:
        """Get recent enforcement history for a child"""
        try:
            response = self.history_table.query(
                KeyConditionExpression=Key('childPhoneNumber').eq(child_phone),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )

            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to get enforcement history: {e}")
            return []

    def get_parent_dashboard(self, parent_email: str) -> Dict:
        """Get complete dashboard data for a parent"""
        try:
            # Get all children
            children = self.get_children_for_parent(parent_email)

            # Get today's summary for each child
            today = datetime.utcnow().strftime('%Y-%m-%d')

            children_stats = []
            for child in children:
                phone = child['phoneNumber']

                daily = self.get_daily_summary(phone, today)
                weekly = self.get_weekly_summary(phone)

                children_stats.append({
                    'childName': child['name'],
                    'phoneNumber': phone,
                    'status': child['status'],
                    'todayBlocked': daily.get('totalBlocked', 0),
                    'weeklyBlocked': weekly.get('totalBlocked', 0),
                    'topBlockedApp': max(daily.get('appBreakdown', {}).items(),
                                       key=lambda x: x[1], default=('None', 0))[0]
                })

            # Calculate totals
            total_today = sum(c['todayBlocked'] for c in children_stats)
            total_weekly = sum(c['weeklyBlocked'] for c in children_stats)

            return {
                'parentEmail': parent_email,
                'childrenCount': len(children),
                'totalBlockedToday': total_today,
                'totalBlockedWeekly': total_weekly,
                'children': children_stats
            }
        except Exception as e:
            logger.error(f"Failed to get parent dashboard: {e}")
            return {}

    def get_detailed_report(self, child_phone: str, start_date: str, end_date: str) -> Dict:
        """Get detailed report for a date range"""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            daily_data = []
            total_blocked = 0
            app_totals = defaultdict(int)

            current_dt = start_dt
            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                summary = self.get_daily_summary(child_phone, date_str)

                daily_data.append(summary)
                total_blocked += summary.get('totalBlocked', 0)

                for app, count in summary.get('appBreakdown', {}).items():
                    app_totals[app] += count

                current_dt += timedelta(days=1)

            return {
                'childPhoneNumber': child_phone,
                'startDate': start_date,
                'endDate': end_date,
                'totalBlocked': total_blocked,
                'dailyData': daily_data,
                'appBreakdown': dict(app_totals),
                'topApps': dict(sorted(app_totals.items(), key=lambda x: x[1], reverse=True))
            }
        except Exception as e:
            logger.error(f"Failed to get detailed report: {e}")
            return {}

    def get_current_session(self, phone_number: str) -> Optional[Dict]:
        """Get current active session for a phone number from Redis"""
        try:
            # Query Redis for phone number key
            key = f"phone:{phone_number}"
            data = self.redis_client.get(key)

            if data:
                session = json.loads(data)
                logger.info(f"Found active session for {phone_number}")
                return {
                    'phoneNumber': phone_number,
                    'status': 'active',
                    'privateIP': session.get('privateIP'),
                    'publicIP': session.get('publicIP'),
                    'imsi': session.get('imsi'),
                    'sessionId': session.get('sessionId'),
                    'timestamp': session.get('timestamp'),
                    'sessionStatus': session.get('status')
                }
            else:
                logger.info(f"No active session found for {phone_number}")
                return None

        except Exception as e:
            logger.error(f"Failed to get current session for {phone_number}: {e}")
            return None

    def get_session_by_ip(self, ip_address: str) -> Optional[Dict]:
        """Get session by IP address (reverse lookup)"""
        try:
            # Query Redis for IP key
            key = f"ip:{ip_address}"
            data = self.redis_client.get(key)

            if data:
                session = json.loads(data)
                logger.info(f"Found session for IP {ip_address}")
                return {
                    'ipAddress': ip_address,
                    'phoneNumber': session.get('msisdn'),
                    'imsi': session.get('imsi'),
                    'sessionId': session.get('sessionId'),
                    'timestamp': session.get('timestamp')
                }
            else:
                logger.info(f"No session found for IP {ip_address}")
                return None

        except Exception as e:
            logger.error(f"Failed to get session for IP {ip_address}: {e}")
            return None

    def get_active_sessions_count(self) -> int:
        """Get count of all active sessions"""
        try:
            count = self.redis_client.scard('active_sessions')
            logger.info(f"Active sessions count: {count}")
            return count
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0
