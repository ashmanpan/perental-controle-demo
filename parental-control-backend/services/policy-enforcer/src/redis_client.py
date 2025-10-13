"""
Redis Client for Policy Enforcer
"""
import json
import logging
from typing import Dict, Optional
import redis
from redis.connection import ConnectionPool, SSLConnection

from .config import Config

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for session data retrieval"""

    def __init__(self, config: Config):
        self.config = config
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

    def get_ip_by_phone(self, msisdn: str) -> Optional[str]:
        """Get current private IP for a phone number"""
        try:
            key = f"phone:{msisdn}"
            data = self.redis_client.get(key)
            if data:
                session = json.loads(data)
                return session.get('privateIP')
            return None
        except Exception as e:
            logger.error(f"Failed to get IP for {msisdn}: {e}")
            return None

    def get_session_by_phone(self, msisdn: str) -> Optional[Dict]:
        """Get full session data by phone number"""
        try:
            key = f"phone:{msisdn}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session for {msisdn}: {e}")
            return None

    def get_phone_by_ip(self, private_ip: str) -> Optional[str]:
        """Get phone number by IP address (reverse lookup)"""
        try:
            key = f"ip:{private_ip}"
            data = self.redis_client.get(key)
            if data:
                session = json.loads(data)
                return session.get('msisdn')
            return None
        except Exception as e:
            logger.error(f"Failed to get phone for IP {private_ip}: {e}")
            return None

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False
