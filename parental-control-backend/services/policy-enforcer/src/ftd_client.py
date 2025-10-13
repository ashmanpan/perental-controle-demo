"""
FTD Client for Policy Enforcer
Communicates with FTD Integration Service
"""
import logging
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config

logger = logging.getLogger(__name__)


class FTDClient:
    """Client for FTD Integration Service"""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.ftd.service_url
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.ftd.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def create_block_rule(self,
                         private_ip: str,
                         app_name: str,
                         ports: List[Dict],
                         msisdn: str) -> Optional[Dict]:
        """Create a firewall rule to block an app"""
        try:
            rule_name = f"PARENTAL_BLOCK_{msisdn.replace('+', '')}_{app_name}"

            payload = {
                'action': 'create',
                'ruleName': rule_name,
                'sourceIP': private_ip,
                'appName': app_name,
                'ports': ports,
                'msisdn': msisdn
            }

            response = self.session.post(
                f"{self.base_url}/api/v1/rules/block",
                json=payload,
                timeout=self.config.ftd.api_timeout
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Created block rule for {app_name} on {private_ip}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to create block rule: {e}")
            return None

    def delete_block_rule(self, rule_id: str, msisdn: str) -> bool:
        """Delete a firewall rule"""
        try:
            payload = {
                'action': 'delete',
                'ruleId': rule_id,
                'msisdn': msisdn
            }

            response = self.session.delete(
                f"{self.base_url}/api/v1/rules/{rule_id}",
                json=payload,
                timeout=self.config.ftd.api_timeout
            )

            response.raise_for_status()

            logger.info(f"Deleted block rule: {rule_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to delete block rule: {e}")
            return False

    def update_block_rule(self,
                         rule_id: str,
                         new_private_ip: str,
                         msisdn: str) -> Optional[Dict]:
        """Update a firewall rule with new IP address"""
        try:
            payload = {
                'action': 'update',
                'ruleId': rule_id,
                'newSourceIP': new_private_ip,
                'msisdn': msisdn
            }

            response = self.session.put(
                f"{self.base_url}/api/v1/rules/{rule_id}",
                json=payload,
                timeout=self.config.ftd.api_timeout
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Updated block rule {rule_id} with new IP: {new_private_ip}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to update block rule: {e}")
            return None

    def verify_rule(self, rule_id: str) -> bool:
        """Verify that a rule exists and is active"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/rules/{rule_id}",
                timeout=self.config.ftd.api_timeout
            )

            response.raise_for_status()
            result = response.json()

            return result.get('status') == 'active'
        except requests.RequestException as e:
            logger.error(f"Failed to verify rule: {e}")
            return False

    def health_check(self) -> bool:
        """Check FTD Integration Service health"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
