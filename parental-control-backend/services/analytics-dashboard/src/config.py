"""
Configuration for Analytics Dashboard Service
"""
import os
from dataclasses import dataclass


@dataclass
class DynamoDBConfig:
    region: str
    table_policies: str
    table_metrics: str
    table_history: str


@dataclass
class Config:
    dynamodb: DynamoDBConfig
    log_level: str
    api_port: int
    cors_origins: str


def load_config() -> Config:
    """Load configuration from environment variables"""

    dynamodb_config = DynamoDBConfig(
        region=os.getenv('AWS_REGION', 'ap-south-1'),
        table_policies=os.getenv('DYNAMODB_TABLE_POLICIES', 'ParentalPolicies'),
        table_metrics=os.getenv('DYNAMODB_TABLE_METRICS', 'BlockedRequestMetrics'),
        table_history=os.getenv('DYNAMODB_TABLE_HISTORY', 'EnforcementHistory')
    )

    return Config(
        dynamodb=dynamodb_config,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        api_port=int(os.getenv('API_PORT', '8000')),
        cors_origins=os.getenv('CORS_ORIGINS', '*')
    )
