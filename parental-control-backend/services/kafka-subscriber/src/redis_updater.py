"""
Redis Updater - Manages session data in Redis
"""
import json
import logging
from typing import Dict, Optional
import redis
from redis.connection import ConnectionPool

from config import Config

logger = logging.getLogger(__name__)


class RedisUpdater:
    """Updates Redis with session mappings"""

    def __init__(self, config: Config):
        self.config = config
        self.redis_client = self._create_redis_client()
        self.ttl = config.redis.ttl_seconds

        # Statistics
        self.updates_success = 0
        self.updates_failed = 0

    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pooling"""
        pool = ConnectionPool(
            host=self.config.redis.host,
            port=self.config.redis.port,
            db=self.config.redis.db,
            password=self.config.redis.password if self.config.redis.password else None,
            ssl=self.config.redis.ssl,
            decode_responses=self.config.redis.decode_responses,
            socket_timeout=self.config.redis.socket_timeout,
            socket_connect_timeout=self.config.redis.socket_connect_timeout,
            max_connections=self.config.redis.max_connections
        )

        client = redis.Redis(connection_pool=pool)

        # Test connection
        try:
            client.ping()
            logger.info(f"Connected to Redis: {self.config.redis.host}:{self.config.redis.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        return client

    def handle_session_start(self, event: Dict) -> bool:
        """Handle SESSION_START event"""
        try:
            imsi = event['imsi']
            msisdn = event['msisdn']
            private_ip = event['privateIP']
            public_ip = event['publicIP']
            session_id = event['sessionId']
            timestamp = event['timestamp']

            # Prepare session data
            session_data = {
                'privateIP': private_ip,
                'publicIP': public_ip,
                'msisdn': msisdn,
                'imsi': imsi,
                'sessionId': session_id,
                'timestamp': timestamp,
                'status': 'active'
            }

            # Use pipeline for atomic operations
            pipeline = self.redis_client.pipeline()

            # Set IMSI -> Session mapping
            imsi_key = f"imsi:{imsi}"
            pipeline.set(imsi_key, json.dumps(session_data))
            pipeline.expire(imsi_key, self.ttl)

            # Set Phone -> Session mapping
            phone_key = f"phone:{msisdn}"
            pipeline.set(phone_key, json.dumps(session_data))
            pipeline.expire(phone_key, self.ttl)

            # Set IP -> Session mapping (reverse lookup)
            ip_key = f"ip:{private_ip}"
            ip_data = {
                'imsi': imsi,
                'msisdn': msisdn,
                'sessionId': session_id,
                'timestamp': timestamp
            }
            pipeline.set(ip_key, json.dumps(ip_data))
            pipeline.expire(ip_key, self.ttl)

            # Add to active sessions set
            pipeline.sadd('active_sessions', session_id)

            # Execute pipeline
            pipeline.execute()

            self.updates_success += 1
            logger.debug(f"Session started: {msisdn} -> {private_ip}")
            return True

        except Exception as e:
            self.updates_failed += 1
            logger.error(f"Failed to handle session start: {e}")
            return False

    def handle_session_end(self, event: Dict) -> bool:
        """Handle SESSION_END event"""
        try:
            imsi = event['imsi']
            msisdn = event['msisdn']
            private_ip = event['privateIP']
            session_id = event['sessionId']

            # Use pipeline for atomic operations
            pipeline = self.redis_client.pipeline()

            # Delete mappings
            pipeline.delete(f"imsi:{imsi}")
            pipeline.delete(f"phone:{msisdn}")
            pipeline.delete(f"ip:{private_ip}")

            # Remove from active sessions
            pipeline.srem('active_sessions', session_id)

            # Execute pipeline
            pipeline.execute()

            self.updates_success += 1
            logger.debug(f"Session ended: {msisdn}")
            return True

        except Exception as e:
            self.updates_failed += 1
            logger.error(f"Failed to handle session end: {e}")
            return False

    def handle_ip_change(self, event: Dict) -> bool:
        """Handle IP_CHANGE event"""
        try:
            imsi = event['imsi']
            msisdn = event['msisdn']
            old_private_ip = event['oldPrivateIP']
            new_private_ip = event['newPrivateIP']
            new_public_ip = event['newPublicIP']
            session_id = event['sessionId']
            timestamp = event['timestamp']

            # Prepare updated session data
            session_data = {
                'privateIP': new_private_ip,
                'publicIP': new_public_ip,
                'msisdn': msisdn,
                'imsi': imsi,
                'sessionId': session_id,
                'timestamp': timestamp,
                'status': 'active'
            }

            # Use pipeline for atomic operations
            pipeline = self.redis_client.pipeline()

            # Delete old IP mapping
            pipeline.delete(f"ip:{old_private_ip}")

            # Update IMSI mapping
            imsi_key = f"imsi:{imsi}"
            pipeline.set(imsi_key, json.dumps(session_data))
            pipeline.expire(imsi_key, self.ttl)

            # Update Phone mapping
            phone_key = f"phone:{msisdn}"
            pipeline.set(phone_key, json.dumps(session_data))
            pipeline.expire(phone_key, self.ttl)

            # Create new IP mapping
            ip_key = f"ip:{new_private_ip}"
            ip_data = {
                'imsi': imsi,
                'msisdn': msisdn,
                'sessionId': session_id,
                'timestamp': timestamp
            }
            pipeline.set(ip_key, json.dumps(ip_data))
            pipeline.expire(ip_key, self.ttl)

            # Execute pipeline
            pipeline.execute()

            self.updates_success += 1
            logger.info(f"IP changed: {msisdn} {old_private_ip} -> {new_private_ip}")
            return True

        except Exception as e:
            self.updates_failed += 1
            logger.error(f"Failed to handle IP change: {e}")
            return False

    def get_session_by_phone(self, msisdn: str) -> Optional[Dict]:
        """Get session data by phone number"""
        try:
            key = f"phone:{msisdn}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session by phone: {e}")
            return None

    def get_session_by_imsi(self, imsi: str) -> Optional[Dict]:
        """Get session data by IMSI"""
        try:
            key = f"imsi:{imsi}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session by IMSI: {e}")
            return None

    def get_session_by_ip(self, ip: str) -> Optional[Dict]:
        """Get session data by IP address"""
        try:
            key = f"ip:{ip}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session by IP: {e}")
            return None

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        try:
            return self.redis_client.scard('active_sessions')
        except Exception as e:
            logger.error(f"Failed to get active session count: {e}")
            return 0

    def get_stats(self) -> Dict:
        """Get statistics"""
        return {
            'updates_success': self.updates_success,
            'updates_failed': self.updates_failed,
            'active_sessions': self.get_active_session_count()
        }

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False
