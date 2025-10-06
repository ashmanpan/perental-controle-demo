"""
Session data models
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict


@dataclass
class SessionData:
    """5G Session data model"""
    session_id: str
    imsi: str
    msisdn: str
    private_ip: str
    public_ip: str
    apn: str
    rat_type: str
    slice_id: Optional[str] = None
    qci: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: str = 'active'

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data

    def to_redis_value(self) -> Dict:
        """Convert to Redis storage format"""
        return {
            'sessionId': self.session_id,
            'privateIP': self.private_ip,
            'publicIP': self.public_ip,
            'msisdn': self.msisdn,
            'imsi': self.imsi,
            'status': self.status,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }


@dataclass
class SessionEvent:
    """Session event (Kafka message)"""
    event_type: str  # SESSION_START, SESSION_END, IP_CHANGE
    timestamp: str
    session_id: str
    imsi: str
    msisdn: str
    private_ip: str
    public_ip: str
    apn: Optional[str] = None
    rat_type: Optional[str] = None
    old_private_ip: Optional[str] = None
    old_public_ip: Optional[str] = None
    duration: Optional[float] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
