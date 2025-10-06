"""
Configuration loader for P-Gateway Simulator
"""
import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path


@dataclass
class SimulationConfig:
    sessions_per_second: int
    session_duration_min: int
    session_duration_max: int
    early_termination_probability: float
    ip_change_probability: float
    test_users_count: int


@dataclass
class IMSIPoolConfig:
    prefix: str
    range_start: int
    range_end: int


@dataclass
class PhonePoolConfig:
    country_code: str
    area_codes: List[str]


@dataclass
class IPPoolConfig:
    private_subnet: str
    private_start: str
    private_end: str
    public_subnet: str
    public_start: str
    public_end: str


@dataclass
class FiveGConfig:
    apn: str
    rat_type: str
    slices: List[Dict[str, str]]
    qos_profiles: List[Dict[str, Any]]


@dataclass
class KafkaConfig:
    topic: str
    analytics_topic: str
    bootstrap_servers: str
    batch_size: int
    linger_ms: int
    compression_type: str
    acks: str
    retries: int
    security_protocol: str
    sasl_mechanism: str


@dataclass
class LoggingConfig:
    level: str
    format: str


@dataclass
class MonitoringConfig:
    enable_cloudwatch: bool
    cloudwatch_namespace: str
    metrics_interval: int
    metrics: List[str]


class Config:
    """Main configuration class"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config/simulator.yaml relative to this file
            base_path = Path(__file__).parent.parent
            config_path = base_path / "config" / "simulator.yaml"

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        # Override from environment variables
        self._apply_env_overrides()

        # Parse into dataclasses
        self.simulation = SimulationConfig(**self._config['simulation'])
        self.imsi_pool = IMSIPoolConfig(**self._config['imsi_pool'])
        self.phone_pool = PhonePoolConfig(**self._config['phone_pool'])
        self.ip_pool = IPPoolConfig(**self._config['ip_pool'])
        self.five_g = FiveGConfig(**self._config['five_g'])
        self.kafka = KafkaConfig(**self._config['kafka'])
        self.logging = LoggingConfig(**self._config['logging'])
        self.monitoring = MonitoringConfig(**self._config['monitoring'])

    def _apply_env_overrides(self):
        """Override configuration with environment variables"""
        # Kafka overrides
        if os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
            self._config['kafka']['bootstrap_servers'] = os.getenv('KAFKA_BOOTSTRAP_SERVERS')

        if os.getenv('KAFKA_TOPIC'):
            self._config['kafka']['topic'] = os.getenv('KAFKA_TOPIC')

        if os.getenv('KAFKA_ANALYTICS_TOPIC'):
            self._config['kafka']['analytics_topic'] = os.getenv('KAFKA_ANALYTICS_TOPIC')

        if os.getenv('KAFKA_SECURITY_PROTOCOL'):
            self._config['kafka']['security_protocol'] = os.getenv('KAFKA_SECURITY_PROTOCOL')

        # Simulation overrides
        if os.getenv('SESSIONS_PER_SECOND'):
            self._config['simulation']['sessions_per_second'] = int(os.getenv('SESSIONS_PER_SECOND'))

        # Logging
        if os.getenv('LOG_LEVEL'):
            self._config['logging']['level'] = os.getenv('LOG_LEVEL')

        # AWS Region
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')

    def get_raw(self, key: str, default=None):
        """Get raw config value by dot notation (e.g., 'kafka.topic')"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# Global config instance
_config_instance = None


def get_config() -> Config:
    """Get singleton config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
