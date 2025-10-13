"""
Session Manager - Handles 5G session lifecycle
"""
import uuid
import random
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import logging

from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a 5G session"""
    session_id: str
    imsi: str
    msisdn: str  # Phone number
    private_ip: str
    public_ip: str
    apn: str
    rat_type: str
    slice_id: str
    qci: int
    created_at: datetime
    expires_at: datetime
    status: str  # active, terminated

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data


class IPAddressPool:
    """Manages IP address allocation"""

    def __init__(self, start_ip: str, end_ip: str):
        self.start = ipaddress.IPv4Address(start_ip)
        self.end = ipaddress.IPv4Address(end_ip)
        self.allocated: Dict[str, str] = {}  # IP -> session_id
        self.available: List[str] = []

        # Pre-generate pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Generate list of available IPs"""
        current = self.start
        while current <= self.end:
            self.available.append(str(current))
            current += 1
        random.shuffle(self.available)
        logger.info(f"IP pool initialized with {len(self.available)} addresses")

    def allocate(self, session_id: str) -> Optional[str]:
        """Allocate an IP address"""
        if not self.available:
            logger.warning("IP pool exhausted, reusing addresses")
            # Reuse a random allocated IP (simulate IP recycling)
            return random.choice(list(self.allocated.keys()))

        ip = self.available.pop()
        self.allocated[ip] = session_id
        return ip

    def release(self, ip: str):
        """Release an IP address"""
        if ip in self.allocated:
            del self.allocated[ip]
            self.available.append(ip)

    def change_ip(self, old_ip: str, session_id: str) -> str:
        """Change IP for an existing session"""
        self.release(old_ip)
        return self.allocate(session_id)


class SessionManager:
    """Manages all active sessions"""

    def __init__(self):
        self.config = get_config()
        self.sessions: Dict[str, Session] = {}

        # IP pools
        self.private_ip_pool = IPAddressPool(
            self.config.ip_pool.private_start,
            self.config.ip_pool.private_end
        )
        self.public_ip_pool = IPAddressPool(
            self.config.ip_pool.public_start,
            self.config.ip_pool.public_end
        )

        # User mappings
        self.imsi_to_session: Dict[str, str] = {}
        self.phone_to_session: Dict[str, str] = {}

        # Statistics
        self.total_sessions_created = 0
        self.total_sessions_terminated = 0
        self.total_ip_changes = 0

    def create_session(self, imsi: str, msisdn: str) -> Session:
        """Create a new session"""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # Allocate IPs
        private_ip = self.private_ip_pool.allocate(session_id)
        public_ip = self.public_ip_pool.allocate(session_id)

        if not private_ip or not public_ip:
            raise RuntimeError("Failed to allocate IP addresses")

        # Random duration
        duration_seconds = random.randint(
            self.config.simulation.session_duration_min,
            self.config.simulation.session_duration_max
        )

        # Random 5G parameters
        slice = random.choice(self.config.five_g.slices)
        qos = random.choice(self.config.five_g.qos_profiles)

        session = Session(
            session_id=session_id,
            imsi=imsi,
            msisdn=msisdn,
            private_ip=private_ip,
            public_ip=public_ip,
            apn=self.config.five_g.apn,
            rat_type=self.config.five_g.rat_type,
            slice_id=slice['slice_id'],
            qci=qos['qci'],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=duration_seconds),
            status='active'
        )

        # Store session
        self.sessions[session_id] = session
        self.imsi_to_session[imsi] = session_id
        self.phone_to_session[msisdn] = session_id

        self.total_sessions_created += 1

        logger.info(
            f"Session created: {session_id} for {msisdn} "
            f"(IMSI: {imsi}, IP: {private_ip})"
        )

        return session

    def terminate_session(self, session_id: str) -> Optional[Session]:
        """Terminate a session"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        # Release IPs
        self.private_ip_pool.release(session.private_ip)
        self.public_ip_pool.release(session.public_ip)

        # Update status
        session.status = 'terminated'

        # Clean up mappings
        if session.imsi in self.imsi_to_session:
            del self.imsi_to_session[session.imsi]
        if session.msisdn in self.phone_to_session:
            del self.phone_to_session[session.msisdn]

        # Remove from active sessions
        del self.sessions[session_id]

        self.total_sessions_terminated += 1

        logger.info(f"Session terminated: {session_id}")

        return session

    def change_session_ip(self, session_id: str) -> Optional[tuple]:
        """Change IP for an active session (simulates handover/reconnect)"""
        session = self.sessions.get(session_id)
        if not session or session.status != 'active':
            return None

        old_private_ip = session.private_ip
        old_public_ip = session.public_ip

        # Allocate new IPs
        new_private_ip = self.private_ip_pool.change_ip(old_private_ip, session_id)
        new_public_ip = self.public_ip_pool.change_ip(old_public_ip, session_id)

        # Update session
        session.private_ip = new_private_ip
        session.public_ip = new_public_ip

        self.total_ip_changes += 1

        logger.info(
            f"IP changed for session {session_id}: "
            f"{old_private_ip} -> {new_private_ip}"
        )

        return (old_private_ip, new_private_ip, old_public_ip, new_public_ip)

    def get_expired_sessions(self) -> List[Session]:
        """Get all sessions that have expired"""
        now = datetime.utcnow()
        expired = []

        for session in list(self.sessions.values()):
            if session.status == 'active' and session.expires_at <= now:
                expired.append(session)

        return expired

    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        return [s for s in self.sessions.values() if s.status == 'active']

    def get_session_by_phone(self, msisdn: str) -> Optional[Session]:
        """Get session by phone number"""
        session_id = self.phone_to_session.get(msisdn)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def get_session_by_imsi(self, imsi: str) -> Optional[Session]:
        """Get session by IMSI"""
        session_id = self.imsi_to_session.get(imsi)
        if session_id:
            return self.sessions.get(session_id)
        return None

    def get_stats(self) -> Dict:
        """Get session statistics"""
        return {
            'active_sessions': len(self.sessions),
            'total_created': self.total_sessions_created,
            'total_terminated': self.total_sessions_terminated,
            'total_ip_changes': self.total_ip_changes,
            'private_ips_available': len(self.private_ip_pool.available),
            'public_ips_available': len(self.public_ip_pool.available)
        }


class UserDatabase:
    """Simulated user database with IMSI to phone number mapping"""

    def __init__(self, num_users: int = 50):
        self.config = get_config()
        self.users: Dict[str, str] = {}  # IMSI -> phone number
        self._generate_users(num_users)

    def _generate_users(self, count: int):
        """Generate test users"""
        for i in range(count):
            imsi = self._generate_imsi()
            phone = self._generate_phone_number()
            self.users[imsi] = phone

        logger.info(f"Generated {count} test users")

    def _generate_imsi(self) -> str:
        """Generate a random IMSI"""
        prefix = self.config.imsi_pool.prefix
        msin = random.randint(
            self.config.imsi_pool.range_start,
            self.config.imsi_pool.range_end
        )
        return f"{prefix}{msin}"

    def _generate_phone_number(self) -> str:
        """Generate a random phone number"""
        country_code = self.config.phone_pool.country_code
        area_code = random.choice(self.config.phone_pool.area_codes)
        exchange = random.randint(100, 999)
        subscriber = random.randint(1000, 9999)
        return f"{country_code}{area_code}{exchange}{subscriber}"

    def get_random_user(self) -> tuple:
        """Get a random user (IMSI, phone)"""
        imsi = random.choice(list(self.users.keys()))
        return imsi, self.users[imsi]

    def get_phone_number(self, imsi: str) -> Optional[str]:
        """Get phone number for IMSI"""
        return self.users.get(imsi)

    def add_user(self, imsi: str, phone: str):
        """Add a new user"""
        self.users[imsi] = phone
