"""
Policy data models
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class PortRule:
    """Port and protocol rule"""
    port: int
    protocol: str  # TCP, UDP, ICMP


@dataclass
class TimeWindow:
    """Time-based enforcement window"""
    start_time: str  # HH:MM format (24-hour)
    end_time: str    # HH:MM format (24-hour)
    days: List[str]  # MON, TUE, WED, THU, FRI, SAT, SUN


@dataclass
class BlockedApp:
    """Blocked application definition"""
    app_name: str
    ports: List[PortRule]
    domains: Optional[List[str]] = None
    ip_ranges: Optional[List[str]] = None


@dataclass
class ParentalPolicy:
    """Parental control policy"""
    child_phone_number: str  # Partition key
    policy_id: str           # Sort key
    child_name: str
    parent_email: str
    blocked_apps: List[BlockedApp]
    time_windows: List[TimeWindow]
    status: str  # active, inactive, suspended
    created_at: str
    updated_at: str
    notes: Optional[str] = None

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item format"""
        return {
            'childPhoneNumber': self.child_phone_number,
            'policyId': self.policy_id,
            'childName': self.child_name,
            'parentEmail': self.parent_email,
            'blockedApps': [
                {
                    'appName': app.app_name,
                    'ports': [
                        {'port': p.port, 'protocol': p.protocol}
                        for p in app.ports
                    ],
                    'domains': app.domains or [],
                    'ipRanges': app.ip_ranges or []
                }
                for app in self.blocked_apps
            ],
            'timeWindows': [
                {
                    'startTime': tw.start_time,
                    'endTime': tw.end_time,
                    'days': tw.days
                }
                for tw in self.time_windows
            ],
            'status': self.status,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'notes': self.notes or ''
        }

    @classmethod
    def from_dynamodb_item(cls, item: Dict) -> 'ParentalPolicy':
        """Create from DynamoDB item"""
        blocked_apps = [
            BlockedApp(
                app_name=app['appName'],
                ports=[
                    PortRule(port=p['port'], protocol=p['protocol'])
                    for p in app.get('ports', [])
                ],
                domains=app.get('domains'),
                ip_ranges=app.get('ipRanges')
            )
            for app in item.get('blockedApps', [])
        ]

        time_windows = [
            TimeWindow(
                start_time=tw['startTime'],
                end_time=tw['endTime'],
                days=tw['days']
            )
            for tw in item.get('timeWindows', [])
        ]

        return cls(
            child_phone_number=item['childPhoneNumber'],
            policy_id=item['policyId'],
            child_name=item['childName'],
            parent_email=item['parentEmail'],
            blocked_apps=blocked_apps,
            time_windows=time_windows,
            status=item['status'],
            created_at=item['createdAt'],
            updated_at=item['updatedAt'],
            notes=item.get('notes')
        )


@dataclass
class ApplicationInfo:
    """Application registry information"""
    app_name: str  # Partition key
    app_category: str
    default_ports: List[PortRule]
    domains: List[str]
    ip_ranges: List[str]
    description: Optional[str] = None

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item"""
        return {
            'appName': self.app_name,
            'appCategory': self.app_category,
            'defaultPorts': [
                {'port': p.port, 'protocol': p.protocol}
                for p in self.default_ports
            ],
            'domains': self.domains,
            'ipRanges': self.ip_ranges,
            'description': self.description or ''
        }


@dataclass
class EnforcementHistory:
    """Enforcement history record"""
    child_phone_number: str  # Partition key
    timestamp: str           # Sort key (ISO format)
    action: str              # block, unblock, update
    app_name: str
    private_ip: str
    rule_id: Optional[str] = None
    status: str = 'pending'  # pending, success, failed
    error_message: Optional[str] = None
    ftd_response: Optional[Dict] = None

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item"""
        return {
            'childPhoneNumber': self.child_phone_number,
            'timestamp': self.timestamp,
            'action': self.action,
            'appName': self.app_name,
            'privateIP': self.private_ip,
            'ruleId': self.rule_id or '',
            'status': self.status,
            'errorMessage': self.error_message or '',
            'ftdResponse': self.ftd_response or {}
        }


@dataclass
class BlockedRequestMetric:
    """Metrics for blocked requests (for parent dashboard)"""
    child_phone_number: str
    parent_email: str
    date: str  # YYYY-MM-DD
    app_name: str
    blocked_count: int
    timestamp_first: str
    timestamp_last: str

    def to_dynamodb_item(self) -> Dict:
        """Convert to DynamoDB item"""
        return {
            'childPhoneNumber': self.child_phone_number,
            'date': self.date,
            'parentEmail': self.parent_email,
            'appName': self.app_name,
            'blockedCount': self.blocked_count,
            'timestampFirst': self.timestamp_first,
            'timestampLast': self.timestamp_last
        }
