"""
Configuration for Policy Enforcement Service
"""
import os
from dataclasses import dataclass


@dataclass
class RedisConfig:
    host: str
    port: int
    db: int
    password: str
    ssl: bool
    decode_responses: bool
    socket_timeout: int
    max_connections: int


@dataclass
class DynamoDBConfig:
    region: str
    table_policies: str
    table_app_registry: str
    table_enforcement_history: str
    table_ftd_rule_mapping: str
    table_blocked_metrics: str
    stream_arn: str


@dataclass
class SQSConfig:
    queue_url: str
    max_messages: int
    wait_time_seconds: int
    visibility_timeout: int


@dataclass
class FTDConfig:
    service_url: str  # URL of FTD Integration Service
    api_timeout: int
    max_retries: int


@dataclass
class Config:
    redis: RedisConfig
    dynamodb: DynamoDBConfig
    sqs: SQSConfig
    ftd: FTDConfig
    log_level: str
    aws_region: str
    enforcement_interval: int  # Seconds between enforcement checks


def load_config() -> Config:
    """Load configuration from environment variables"""

    redis_config = RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD', ''),
        ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
        decode_responses=True,
        socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
        max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    )

    dynamodb_config = DynamoDBConfig(
        region=os.getenv('AWS_REGION', 'ap-south-1'),
        table_policies=os.getenv('DYNAMODB_TABLE_POLICIES', 'ParentalPolicies'),
        table_app_registry=os.getenv('DYNAMODB_TABLE_APP_REGISTRY', 'ApplicationRegistry'),
        table_enforcement_history=os.getenv('DYNAMODB_TABLE_HISTORY', 'EnforcementHistory'),
        table_ftd_rule_mapping=os.getenv('DYNAMODB_TABLE_FTD_MAPPING', 'FTDRuleMapping'),
        table_blocked_metrics=os.getenv('DYNAMODB_TABLE_METRICS', 'BlockedRequestMetrics'),
        stream_arn=os.getenv('DYNAMODB_STREAM_ARN', '')
    )

    sqs_config = SQSConfig(
        queue_url=os.getenv('SQS_ENFORCEMENT_QUEUE_URL', ''),
        max_messages=int(os.getenv('SQS_MAX_MESSAGES', '10')),
        wait_time_seconds=int(os.getenv('SQS_WAIT_TIME', '20')),
        visibility_timeout=int(os.getenv('SQS_VISIBILITY_TIMEOUT', '300'))
    )

    ftd_config = FTDConfig(
        service_url=os.getenv('FTD_SERVICE_URL', 'http://localhost:5000'),
        api_timeout=int(os.getenv('FTD_API_TIMEOUT', '30')),
        max_retries=int(os.getenv('FTD_MAX_RETRIES', '3'))
    )

    return Config(
        redis=redis_config,
        dynamodb=dynamodb_config,
        sqs=sqs_config,
        ftd=ftd_config,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        aws_region=os.getenv('AWS_REGION', 'ap-south-1'),
        enforcement_interval=int(os.getenv('ENFORCEMENT_INTERVAL', '5'))
    )
