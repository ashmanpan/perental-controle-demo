"""
Cisco FTD SSH CLI Client
Fallback option when REST API is not available
"""
import logging
from typing import Optional, List
import paramiko
import time

from config import Config

logger = logging.getLogger(__name__)


class FTDSSHClient:
    """FTD SSH CLI Client"""

    def __init__(self, config: Config):
        self.config = config
        self.host = config.ftd.host
        self.username = config.ftd.username
        self.password = config.ftd.password
        self.port = config.ftd.ssh_port

        self.client = None
        self.shell = None

    def connect(self) -> bool:
        """Connect to FTD via SSH"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )

            # Invoke shell
            self.shell = self.client.invoke_shell()
            time.sleep(1)

            # Clear initial output
            if self.shell.recv_ready():
                self.shell.recv(65535)

            logger.info(f"Connected to FTD via SSH: {self.host}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect via SSH: {e}")
            return False

    def execute_command(self, command: str, wait_time: float = 2.0) -> str:
        """Execute a CLI command"""
        if not self.shell:
            logger.error("SSH shell not initialized")
            return ""

        try:
            # Send command
            self.shell.send(command + '\n')
            time.sleep(wait_time)

            # Receive output
            output = ""
            if self.shell.recv_ready():
                output = self.shell.recv(65535).decode('utf-8')

            logger.debug(f"Command output: {output[:200]}")
            return output

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return ""

    def create_access_list_rule(self,
                               acl_name: str,
                               rule_name: str,
                               source_ip: str,
                               protocol: str,
                               port: int) -> bool:
        """Create an access-list rule via CLI"""
        if not self.shell:
            if not self.connect():
                return False

        try:
            # Enter config mode
            self.execute_command('enable')
            self.execute_command(self.password)  # Enable password
            self.execute_command('configure terminal')

            # Create access-list rule
            command = f"access-list {acl_name} extended deny {protocol.lower()} host {source_ip} any eq {port}"
            output = self.execute_command(command)

            # Save config
            self.execute_command('write memory')

            # Exit config mode
            self.execute_command('exit')

            logger.info(f"Created ACL rule via SSH: {rule_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create ACL rule via SSH: {e}")
            return False

    def delete_access_list_rule(self, acl_name: str, rule_line_number: int) -> bool:
        """Delete an access-list rule via CLI"""
        if not self.shell:
            if not self.connect():
                return False

        try:
            # Enter config mode
            self.execute_command('enable')
            self.execute_command(self.password)
            self.execute_command('configure terminal')

            # Delete ACL rule
            command = f"no access-list {acl_name} line {rule_line_number}"
            output = self.execute_command(command)

            # Save config
            self.execute_command('write memory')

            # Exit config mode
            self.execute_command('exit')

            logger.info(f"Deleted ACL rule via SSH: line {rule_line_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete ACL rule via SSH: {e}")
            return False

    def show_access_list(self, acl_name: str) -> str:
        """Show access-list configuration"""
        if not self.shell:
            if not self.connect():
                return ""

        try:
            command = f"show access-list {acl_name}"
            output = self.execute_command(command)
            return output

        except Exception as e:
            logger.error(f"Failed to show ACL: {e}")
            return ""

    def disconnect(self):
        """Disconnect SSH session"""
        try:
            if self.shell:
                self.shell.close()
            if self.client:
                self.client.close()
            logger.info("Disconnected from FTD SSH")
        except Exception as e:
            logger.error(f"Error disconnecting SSH: {e}")

    def __del__(self):
        """Cleanup on object destruction"""
        self.disconnect()
