"""
Firewall rule models for Cisco FTD
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class NetworkObject:
    """Network object (IP/subnet)"""
    type: str  # Host, Network, Range
    value: str  # IP address or CIDR


@dataclass
class PortObject:
    """Port object"""
    protocol: str  # TCP, UDP
    port: str      # Port number or range (e.g., "443" or "8000-8100")


@dataclass
class FTDAccessRule:
    """Cisco FTD Access Control Rule"""
    name: str
    action: str  # ALLOW, BLOCK, TRUST
    enabled: bool
    source_networks: List[NetworkObject]
    destination_networks: Optional[List[NetworkObject]] = None
    destination_ports: Optional[List[PortObject]] = None
    source_zones: Optional[List[str]] = None
    destination_zones: Optional[List[str]] = None
    priority: int = 100
    log_begin: bool = False
    log_end: bool = True
    description: Optional[str] = None

    def to_fmc_api_payload(self) -> Dict:
        """Convert to FMC (Firepower Management Center) API payload"""
        payload = {
            'name': self.name,
            'action': self.action,
            'enabled': self.enabled,
            'type': 'AccessRule',
            'logBegin': self.log_begin,
            'logEnd': self.log_end,
        }

        if self.description:
            payload['description'] = self.description

        # Source networks
        if self.source_networks:
            payload['sourceNetworks'] = {
                'objects': [
                    {'type': net.type, 'value': net.value}
                    for net in self.source_networks
                ]
            }

        # Destination networks
        if self.destination_networks:
            payload['destinationNetworks'] = {
                'objects': [
                    {'type': net.type, 'value': net.value}
                    for net in self.destination_networks
                ]
            }

        # Destination ports
        if self.destination_ports:
            payload['destinationPorts'] = {
                'objects': [
                    {'type': 'ProtocolPortObject', 'protocol': port.protocol, 'port': port.port}
                    for port in self.destination_ports
                ]
            }

        # Zones
        if self.source_zones:
            payload['sourceZones'] = {
                'objects': [{'type': 'SecurityZone', 'name': zone} for zone in self.source_zones]
            }

        if self.destination_zones:
            payload['destinationZones'] = {
                'objects': [{'type': 'SecurityZone', 'name': zone} for zone in self.destination_zones]
            }

        return payload

    def to_cli_commands(self, acl_name: str = 'PARENTAL_CONTROL_ACL') -> List[str]:
        """Generate CLI commands for FTD"""
        commands = []

        # Build access-list command
        action = 'deny' if self.action == 'BLOCK' else 'permit'

        for port in (self.destination_ports or []):
            for src_net in self.source_networks:
                cmd = f"access-list {acl_name} extended {action} "
                cmd += f"{port.protocol.lower()} "

                # Source
                if src_net.type == 'Host':
                    cmd += f"host {src_net.value} "
                else:
                    cmd += f"{src_net.value} "

                # Destination (any if not specified)
                cmd += "any "

                # Port
                cmd += f"eq {port.port}"

                commands.append(cmd)

        return commands


@dataclass
class FTDRuleMetadata:
    """Metadata for tracking FTD rules"""
    rule_id: str              # FMC rule ID
    rule_name: str
    child_phone_number: str
    private_ip: str
    app_name: str
    created_at: str
    ftd_device_id: Optional[str] = None
    access_policy_id: Optional[str] = None
    status: str = 'active'    # active, deleted, failed

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FTDDeployment:
    """FTD deployment job"""
    deployment_id: str
    device_ids: List[str]
    started_at: str
    status: str  # pending, in_progress, completed, failed
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
