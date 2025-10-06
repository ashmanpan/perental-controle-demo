"""
Cisco Firepower Management Center (FMC) REST API Client
"""
import logging
import requests
import urllib3
from typing import Dict, Optional, List
import time

from config import Config

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class FMCAPIClient:
    """FMC REST API Client"""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"https://{config.ftd.host}:{config.ftd.api_port}/api/fmc_platform/v1"
        self.username = config.ftd.username
        self.password = config.ftd.password
        self.verify_ssl = config.ftd.verify_ssl

        self.auth_token = None
        self.domain_uuid = None
        self.refresh_token = None
        self.token_expires_at = 0

        self._authenticate()

    def _authenticate(self) -> bool:
        """Authenticate and get access token"""
        try:
            url = f"{self.base_url}/auth/generatetoken"

            response = requests.post(
                url,
                auth=(self.username, self.password),
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()

            # Extract tokens from headers
            self.auth_token = response.headers.get('X-auth-access-token')
            self.refresh_token = response.headers.get('X-auth-refresh-token')
            self.domain_uuid = response.headers.get('DOMAIN_UUID')

            # Token expires in 30 minutes
            self.token_expires_at = time.time() + (30 * 60)

            logger.info(f"Successfully authenticated to FMC: {self.config.ftd.host}")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to authenticate to FMC: {e}")
            return False

    def _ensure_authenticated(self):
        """Ensure we have a valid auth token"""
        # Re-authenticate if token is about to expire (5 min buffer)
        if time.time() > (self.token_expires_at - 300):
            logger.info("Auth token expiring soon, re-authenticating...")
            self._authenticate()

    def _get_headers(self) -> Dict:
        """Get request headers with auth token"""
        return {
            'X-auth-access-token': self.auth_token,
            'Content-Type': 'application/json'
        }

    def get_access_policy(self, policy_name: str) -> Optional[Dict]:
        """Get access policy by name"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/policy/accesspolicies"

            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Find policy by name
            for policy in data.get('items', []):
                if policy['name'] == policy_name:
                    return policy

            logger.warning(f"Access policy not found: {policy_name}")
            return None

        except requests.RequestException as e:
            logger.error(f"Failed to get access policy: {e}")
            return None

    def create_access_rule(self,
                          policy_id: str,
                          rule_name: str,
                          source_ip: str,
                          dest_ports: List[Dict],
                          action: str = 'BLOCK') -> Optional[Dict]:
        """Create an access control rule"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/policy/accesspolicies/{policy_id}/accessrules"

            # Build rule payload
            payload = {
                'name': rule_name,
                'action': action,
                'enabled': True,
                'type': 'AccessRule',
                'logBegin': False,
                'logEnd': True,
                'sourceNetworks': {
                    'objects': [
                        {
                            'type': 'Host',
                            'value': source_ip
                        }
                    ]
                },
                'destinationPorts': {
                    'objects': [
                        {
                            'type': 'ProtocolPortObject',
                            'protocol': port['protocol'],
                            'port': str(port['port'])
                        }
                        for port in dest_ports
                    ]
                }
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Created access rule: {rule_name} (ID: {result.get('id')})")
            return result

        except requests.RequestException as e:
            logger.error(f"Failed to create access rule: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None

    def get_access_rule(self, policy_id: str, rule_id: str) -> Optional[Dict]:
        """Get an access control rule"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/policy/accesspolicies/{policy_id}/accessrules/{rule_id}"

            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to get access rule: {e}")
            return None

    def update_access_rule(self,
                          policy_id: str,
                          rule_id: str,
                          new_source_ip: str) -> Optional[Dict]:
        """Update an access control rule with new source IP"""
        self._ensure_authenticated()

        try:
            # First get the existing rule
            existing_rule = self.get_access_rule(policy_id, rule_id)
            if not existing_rule:
                return None

            # Update source IP
            url = f"{self.base_url}/domain/{self.domain_uuid}/policy/accesspolicies/{policy_id}/accessrules/{rule_id}"

            existing_rule['sourceNetworks']['objects'][0]['value'] = new_source_ip

            response = requests.put(
                url,
                headers=self._get_headers(),
                json=existing_rule,
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Updated access rule {rule_id} with new IP: {new_source_ip}")
            return result

        except requests.RequestException as e:
            logger.error(f"Failed to update access rule: {e}")
            return None

    def delete_access_rule(self, policy_id: str, rule_id: str) -> bool:
        """Delete an access control rule"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/policy/accesspolicies/{policy_id}/accessrules/{rule_id}"

            response = requests.delete(
                url,
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()

            logger.info(f"Deleted access rule: {rule_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to delete access rule: {e}")
            return False

    def deploy_policy(self, device_ids: List[str]) -> Optional[str]:
        """Deploy policy changes to FTD devices"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/deployment/deploymentrequests"

            payload = {
                'type': 'DeploymentRequest',
                'version': int(time.time()),
                'forceDeploy': False,
                'ignoreWarning': True,
                'deviceList': device_ids
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            deployment_id = result.get('metadata', {}).get('task', {}).get('id')

            logger.info(f"Initiated policy deployment: {deployment_id}")
            return deployment_id

        except requests.RequestException as e:
            logger.error(f"Failed to deploy policy: {e}")
            return None

    def get_deployment_status(self, deployment_id: str) -> Optional[Dict]:
        """Get deployment status"""
        self._ensure_authenticated()

        try:
            url = f"{self.base_url}/domain/{self.domain_uuid}/deployment/deploymentrequests/{deployment_id}"

            response = requests.get(
                url,
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to get deployment status: {e}")
            return None
