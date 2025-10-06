"""
Configuration for FTD Integration Service
"""
import os
from dataclasses import dataclass


@dataclass
class FTDConfig:
    host: str
    username: str
    password: str
    api_port: int
    ssh_port: int
    verify_ssl: bool
    domain: str  # FMC domain (default: Global)
    access_policy_name: str


@dataclass
class Config:
    ftd: FTDConfig
    log_level: str
    api_port: int
    workers: int


def load_config() -> Config:
    """Load configuration from environment variables"""

    ftd_config = FTDConfig(
        host=os.getenv('FTD_HOST', 'ftd.example.com'),
        username=os.getenv('FTD_USERNAME', 'admin'),
        password=os.getenv('FTD_PASSWORD', ''),
        api_port=int(os.getenv('FTD_API_PORT', '443')),
        ssh_port=int(os.getenv('FTD_SSH_PORT', '22')),
        verify_ssl=os.getenv('FTD_VERIFY_SSL', 'false').lower() == 'true',
        domain=os.getenv('FTD_DOMAIN', 'Global'),
        access_policy_name=os.getenv('FTD_ACCESS_POLICY', 'ParentalControlPolicy')
    )

    return Config(
        ftd=ftd_config,
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        api_port=int(os.getenv('API_PORT', '5000')),
        workers=int(os.getenv('WORKERS', '4'))
    )
