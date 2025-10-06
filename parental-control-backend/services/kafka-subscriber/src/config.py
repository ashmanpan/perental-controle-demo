"""
Configuration for Kafka Subscriber Service
"""
import os
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    bootstrap_servers: str
    topic: str
    group_id: str
    auto_offset_reset: str
    enable_auto_commit: bool
    max_poll_records: int
    security_protocol: str
    sasl_mechanism: str


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int
    password: str
    ssl: bool
    decode_responses: bool
    socket_timeout: int
    socket_connect_timeout: int
    max_connections: int
    ttl_seconds: int  # Default TTL for keys


@dataclass
class DynamoDBConfig:
    region: str
    table_policies: str
    table_app_registry: str
    table_enforcement_history: str


@dataclass
class Config:
    kafka: KafkaConfig
    redis: RedisConfig
    dynamodb: DynamoDBConfig
    log_level: str
    aws_region: str


def load_config() -> Config:
    """Load configuration from environment variables"""

    kafka_config = KafkaConfig(
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        topic=os.getenv('KAFKA_TOPIC', 'session-data'),
        group_id=os.getenv('KAFKA_GROUP_ID', 'parental-control-subscriber'),
        auto_offset_reset=os.getenv('KAFKA_AUTO_OFFSET_RESET', 'earliest'),
        enable_auto_commit=os.getenv('KAFKA_ENABLE_AUTO_COMMIT', 'false').lower() == 'true',
        max_poll_records=int(os.getenv('KAFKA_MAX_POLL_RECORDS', '500')),
        security_protocol=os.getenv('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT'),
        sasl_mechanism=os.getenv('KAFKA_SASL_MECHANISM', 'AWS_MSK_IAM')
    )

    redis_config = RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD', ''),
        ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
        decode_responses=True,
        socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
        socket_connect_timeout=int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),
        max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
        ttl_seconds=int(os.getenv('REDIS_TTL_SECONDS', '86400'))  # 24 hours
    )

    dynamodb_config = DynamoDBConfig(
        region=os.getenv('AWS_REGION', 'us-east-1'),
        table_policies=os.getenv('DYNAMODB_TABLE_POLICIES', 'ParentalPolicies'),
        table_app_registry=os.getenv('DYNAMODB_TABLE_APP_REGISTRY', 'ApplicationRegistry'),
        table_enforcement_history=os.getenv('DYNAMODB_TABLE_HISTORY', 'EnforcementHistory')
    )

    return Config(
        kafka=kafka_config,
        redis=redis_config,
        dynamodb=dynamodb_config,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        aws_region=os.getenv('AWS_REGION', 'us-east-1')
    )
