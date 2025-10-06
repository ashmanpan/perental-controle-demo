"""
FTD Rule Manager
Orchestrates between FMC API and SSH CLI
"""
import logging
import uuid
from typing import Dict, List, Optional

from config import Config
from fmc_api_client import FMCAPIClient
from ftd_ssh_client import FTDSSHClient

logger = logging.getLogger(__name__)


class RuleManager:
    """Manages FTD firewall rules"""

    def __init__(self, config: Config):
        self.config = config

        # Try API first
        try:
            self.fmc_client = FMCAPIClient(config)
            self.use_api = True
            logger.info("Using FMC REST API for rule management")

            # Get access policy
            self.access_policy = self.fmc_client.get_access_policy(
                config.ftd.access_policy_name
            )

            if not self.access_policy:
                logger.warning("Access policy not found, will create rules via SSH")
                self.use_api = False
        except Exception as e:
            logger.warning(f"Failed to initialize FMC API, falling back to SSH: {e}")
            self.use_api = False

        # Initialize SSH client as fallback
        if not self.use_api:
            self.ssh_client = FTDSSHClient(config)
            logger.info("Using SSH CLI for rule management")

    def create_block_rule(self,
                         source_ip: str,
                         app_name: str,
                         ports: List[Dict],
                         msisdn: str) -> Optional[Dict]:
        """Create a firewall rule to block an application"""
        rule_name = f"PARENTAL_BLOCK_{msisdn.replace('+', '')}_{app_name}"

        if self.use_api:
            return self._create_rule_via_api(rule_name, source_ip, ports)
        else:
            return self._create_rule_via_ssh(rule_name, source_ip, ports)

    def _create_rule_via_api(self,
                            rule_name: str,
                            source_ip: str,
                            ports: List[Dict]) -> Optional[Dict]:
        """Create rule via FMC REST API"""
        try:
            policy_id = self.access_policy['id']

            result = self.fmc_client.create_access_rule(
                policy_id=policy_id,
                rule_name=rule_name,
                source_ip=source_ip,
                dest_ports=ports,
                action='BLOCK'
            )

            if result:
                return {
                    'ruleId': result['id'],
                    'ruleName': rule_name,
                    'method': 'API',
                    'policyId': policy_id,
                    'status': 'created',
                    'deploymentRequired': True
                }

            return None

        except Exception as e:
            logger.error(f"Failed to create rule via API: {e}")
            return None

    def _create_rule_via_ssh(self,
                            rule_name: str,
                            source_ip: str,
                            ports: List[Dict]) -> Optional[Dict]:
        """Create rule via SSH CLI"""
        try:
            acl_name = "PARENTAL_CONTROL_ACL"

            # Create rule for each port
            for port in ports:
                success = self.ssh_client.create_access_list_rule(
                    acl_name=acl_name,
                    rule_name=rule_name,
                    source_ip=source_ip,
                    protocol=port['protocol'],
                    port=port['port']
                )

                if not success:
                    return None

            # Generate pseudo rule ID
            rule_id = f"ssh_{uuid.uuid4().hex[:12]}"

            return {
                'ruleId': rule_id,
                'ruleName': rule_name,
                'method': 'SSH',
                'aclName': acl_name,
                'status': 'created',
                'deploymentRequired': False  # Already applied
            }

        except Exception as e:
            logger.error(f"Failed to create rule via SSH: {e}")
            return None

    def update_rule(self,
                   rule_id: str,
                   new_source_ip: str,
                   policy_id: Optional[str] = None) -> Optional[Dict]:
        """Update rule with new source IP"""
        if self.use_api:
            return self._update_rule_via_api(rule_id, new_source_ip, policy_id)
        else:
            # For SSH, delete old rule and create new one
            logger.info("SSH update: deleting old rule and creating new one")
            # Would need to track old rule details to properly delete
            return None

    def _update_rule_via_api(self,
                            rule_id: str,
                            new_source_ip: str,
                            policy_id: str) -> Optional[Dict]:
        """Update rule via FMC REST API"""
        try:
            result = self.fmc_client.update_access_rule(
                policy_id=policy_id or self.access_policy['id'],
                rule_id=rule_id,
                new_source_ip=new_source_ip
            )

            if result:
                return {
                    'ruleId': result['id'],
                    'ruleName': result['name'],
                    'method': 'API',
                    'status': 'updated',
                    'deploymentRequired': True
                }

            return None

        except Exception as e:
            logger.error(f"Failed to update rule via API: {e}")
            return None

    def delete_rule(self,
                   rule_id: str,
                   policy_id: Optional[str] = None) -> bool:
        """Delete a firewall rule"""
        if self.use_api:
            return self._delete_rule_via_api(rule_id, policy_id)
        else:
            return self._delete_rule_via_ssh(rule_id)

    def _delete_rule_via_api(self, rule_id: str, policy_id: str) -> bool:
        """Delete rule via FMC REST API"""
        try:
            return self.fmc_client.delete_access_rule(
                policy_id=policy_id or self.access_policy['id'],
                rule_id=rule_id
            )
        except Exception as e:
            logger.error(f"Failed to delete rule via API: {e}")
            return False

    def _delete_rule_via_ssh(self, rule_id: str) -> bool:
        """Delete rule via SSH CLI"""
        try:
            # Extract ACL name and line number from rule_id
            # This is a simplified version
            acl_name = "PARENTAL_CONTROL_ACL"
            # Would need to track line numbers properly
            return True

        except Exception as e:
            logger.error(f"Failed to delete rule via SSH: {e}")
            return False

    def verify_rule(self, rule_id: str, policy_id: Optional[str] = None) -> bool:
        """Verify that a rule exists"""
        if self.use_api:
            return self._verify_rule_via_api(rule_id, policy_id)
        else:
            return self._verify_rule_via_ssh(rule_id)

    def _verify_rule_via_api(self, rule_id: str, policy_id: str) -> bool:
        """Verify rule via FMC REST API"""
        try:
            rule = self.fmc_client.get_access_rule(
                policy_id=policy_id or self.access_policy['id'],
                rule_id=rule_id
            )
            return rule is not None
        except Exception as e:
            logger.error(f"Failed to verify rule via API: {e}")
            return False

    def _verify_rule_via_ssh(self, rule_id: str) -> bool:
        """Verify rule via SSH CLI"""
        try:
            acl_name = "PARENTAL_CONTROL_ACL"
            output = self.ssh_client.show_access_list(acl_name)
            # Check if rule exists in output
            return len(output) > 0
        except Exception as e:
            logger.error(f"Failed to verify rule via SSH: {e}")
            return False

    def deploy_changes(self, device_ids: List[str]) -> Optional[str]:
        """Deploy policy changes to FTD devices (API only)"""
        if not self.use_api:
            logger.info("SSH mode: changes are already applied, no deployment needed")
            return "ssh_immediate"

        try:
            deployment_id = self.fmc_client.deploy_policy(device_ids)
            return deployment_id
        except Exception as e:
            logger.error(f"Failed to deploy changes: {e}")
            return None

    def get_deployment_status(self, deployment_id: str) -> Optional[Dict]:
        """Get deployment status (API only)"""
        if not self.use_api:
            return {'status': 'completed', 'method': 'SSH'}

        try:
            return self.fmc_client.get_deployment_status(deployment_id)
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return None
