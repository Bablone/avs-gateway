"""
agent_identity.py — Agent Identity Model.

An accountable non-human actor profile.

Agent Identity answers:
- Who is this agent?
- What environment does it belong to?
- What public key represents it?
- What privileges does it have?
- Is the key active, rotated, or revoked?

v0.3.6: Identity model + key fingerprint generation (draft).
v0.4.0: Signed ActionRequests, signature verification, key rotation.

Design note: this model borrows from SPIFFE/SPIRE workload identity
patterns but is scoped to AVS's needs. It maps to enterprise IAM
later, not replaces it.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import hashlib
import time
import uuid
import logging

logger = logging.getLogger("avs_gateway.identity")


class AgentStatus(str, Enum):
    """Agent key status lifecycle."""
    ACTIVE = "active"
    REVOKED = "revoked"
    ROTATED = "rotated"


class AgentPrivilegeLevel(str, Enum):
    """Agent privilege tiers."""
    READ_ONLY = "read_only"
    STANDARD = "standard"
    PRIVILEGED = "privileged"
    ADMIN = "admin"


@dataclass(frozen=True)
class AgentIdentity:
    """An accountable non-human actor profile.

    Represents an agent as a verifiable principal — not just a string
    label. Includes identity metadata, public key fingerprint, and
    trust state.

    The public_key field holds an Ed25519 public key as a hex string.
    The key_fingerprint is derived deterministically from the public key
    and can be referenced in ASR-1 receipts without exposing the key.
    """

    agent_id: str
    display_name: str = ""
    agent_type: str = "generic"          # "coding" | "deployment" | "support" | "generic"
    environment: str = "dev"             # "dev" | "staging" | "prod"
    privilege_level: str = "standard"    # "read_only" | "standard" | "privileged" | "admin"
    public_key: Optional[str] = None     # Ed25519 public key (hex string)
    key_fingerprint: Optional[str] = None  # sha256:hex — derived from public_key
    status: str = "active"               # "active" | "revoked" | "rotated"
    created_at: str = ""
    last_seen_at: str = ""
    parent_agent_id: Optional[str] = None   # For spawned agents
    human_owner_id: Optional[str] = None    # Human on whose behalf agent acts
    trust_score: float = 0.5

    def __post_init__(self):
        # Auto-generate key_fingerprint from public_key if not set
        if self.public_key and not self.key_fingerprint:
            fp = _compute_key_fingerprint(self.public_key)
            # Cannot set frozen field directly — use object.__setattr__
            object.__setattr__(self, "key_fingerprint", fp)

    def is_active(self) -> bool:
        """Return True if the agent's key is active."""
        return self.status == AgentStatus.ACTIVE.value

    def is_revoked(self) -> bool:
        """Return True if the agent's key has been revoked."""
        return self.status == AgentStatus.REVOKED.value

    def can_act_in(self, environment: str) -> bool:
        """Return True if the agent is permitted to act in *environment*."""
        return self.environment == environment and self.is_active()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "agent_type": self.agent_type,
            "environment": self.environment,
            "privilege_level": self.privilege_level,
            "public_key": self.public_key,
            "key_fingerprint": self.key_fingerprint,
            "status": self.status,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "parent_agent_id": self.parent_agent_id,
            "human_owner_id": self.human_owner_id,
            "trust_score": self.trust_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentIdentity":
        """Reconstruct from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            display_name=data.get("display_name", ""),
            agent_type=data.get("agent_type", "generic"),
            environment=data.get("environment", "dev"),
            privilege_level=data.get("privilege_level", "standard"),
            public_key=data.get("public_key"),
            key_fingerprint=data.get("key_fingerprint"),
            status=data.get("status", "active"),
            created_at=data.get("created_at", ""),
            last_seen_at=data.get("last_seen_at", ""),
            parent_agent_id=data.get("parent_agent_id"),
            human_owner_id=data.get("human_owner_id"),
            trust_score=data.get("trust_score", 0.5),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_key_fingerprint(public_key_hex: str) -> str:
    """Compute a deterministic ``sha256:<hex>`` fingerprint from a public key.

    The fingerprint is stable across runs and can be referenced in
    ASR-1 receipts without exposing the full public key.
    """
    try:
        key_bytes = bytes.fromhex(public_key_hex)
    except ValueError:
        # May already include a prefix
        key_bytes = public_key_hex.encode("utf-8")
    return "sha256:" + hashlib.sha256(key_bytes).hexdigest()


def create_agent_identity(
    agent_id: str,
    display_name: str = "",
    agent_type: str = "generic",
    environment: str = "dev",
    privilege_level: str = "standard",
    public_key: Optional[str] = None,
    parent_agent_id: Optional[str] = None,
    human_owner_id: Optional[str] = None,
    trust_score: float = 0.5,
) -> AgentIdentity:
    """Factory for creating an AgentIdentity with sensible defaults.

    If *public_key* is provided, the key_fingerprint is computed
    automatically.

    Args:
        agent_id: Unique identifier for the agent.
        display_name: Human-readable name.
        agent_type: Classification (coding, deployment, support, etc.).
        environment: Dev/staging/prod.
        privilege_level: read_only/standard/privileged/admin.
        public_key: Ed25519 public key as hex string (optional).
        parent_agent_id: Parent agent if spawned (optional).
        human_owner_id: Human on whose behalf agent acts (optional).
        trust_score: Initial trust score 0.0-1.0.

    Returns:
        A new AgentIdentity instance.
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return AgentIdentity(
        agent_id=agent_id,
        display_name=display_name or agent_id,
        agent_type=agent_type,
        environment=environment,
        privilege_level=privilege_level,
        public_key=public_key,
        status=AgentStatus.ACTIVE.value,
        created_at=now,
        last_seen_at=now,
        parent_agent_id=parent_agent_id,
        human_owner_id=human_owner_id,
        trust_score=trust_score,
    )
