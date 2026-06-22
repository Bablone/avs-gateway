"""
test_agent_identity.py — Test AgentIdentity model.

Tests key fingerprint generation, serialization, and status management.
"""

import pytest

from avs_gateway.identity.agent_identity import (
    AgentIdentity,
    AgentStatus,
    AgentPrivilegeLevel,
    create_agent_identity,
    _compute_key_fingerprint,
)


class TestAgentIdentityCreation:

    def test_create_identity_with_all_fields(self):
        identity = create_agent_identity(
            agent_id="agent_001",
            display_name="Deployment Agent",
            agent_type="deployment",
            environment="production",
            privilege_level="admin",
        )
        assert identity.agent_id == "agent_001"
        assert identity.display_name == "Deployment Agent"
        assert identity.agent_type == "deployment"
        assert identity.environment == "production"
        assert identity.privilege_level == "admin"
        assert identity.status == "active"
        assert identity.created_at
        assert identity.last_seen_at

    def test_create_identity_defaults(self):
        identity = create_agent_identity(agent_id="agent_002")
        assert identity.display_name == "agent_002"
        assert identity.agent_type == "generic"
        assert identity.environment == "dev"
        assert identity.privilege_level == "standard"
        assert identity.status == "active"
        assert identity.trust_score == 0.5

    def test_key_fingerprint_generation_is_deterministic(self):
        identity = create_agent_identity(
            agent_id="agent_003",
            public_key="a" * 64,
        )
        fp1 = identity.key_fingerprint
        fp2 = _compute_key_fingerprint("a" * 64)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_key_fingerprint_changes_when_public_key_changes(self):
        identity1 = create_agent_identity(agent_id="a1", public_key="a" * 64)
        identity2 = create_agent_identity(agent_id="a2", public_key="b" * 64)
        assert identity1.key_fingerprint != identity2.key_fingerprint

    def test_key_fingerprint_without_public_key_is_none(self):
        identity = create_agent_identity(agent_id="agent_004")
        assert identity.public_key is None
        assert identity.key_fingerprint is None

    def test_serialization_roundtrip(self):
        identity = create_agent_identity(
            agent_id="agent_005",
            display_name="Test Agent",
            agent_type="coding",
            environment="staging",
            privilege_level="privileged",
            public_key="c" * 64,
            parent_agent_id="parent_001",
            human_owner_id="human_001",
            trust_score=0.75,
        )
        d = identity.to_dict()
        restored = AgentIdentity.from_dict(d)
        assert restored.agent_id == identity.agent_id
        assert restored.display_name == identity.display_name
        assert restored.agent_type == identity.agent_type
        assert restored.environment == identity.environment
        assert restored.privilege_level == identity.privilege_level
        assert restored.public_key == identity.public_key
        assert restored.key_fingerprint == identity.key_fingerprint
        assert restored.parent_agent_id == identity.parent_agent_id
        assert restored.human_owner_id == identity.human_owner_id
        assert restored.trust_score == identity.trust_score

    def test_is_active(self):
        active = create_agent_identity(agent_id="a1")
        assert active.is_active() is True
        assert active.is_revoked() is False

    def test_is_revoked(self):
        revoked = AgentIdentity(
            agent_id="a2",
            status=AgentStatus.REVOKED.value,
            created_at="2026-01-01T00:00:00Z",
            last_seen_at="2026-01-01T00:00:00Z",
        )
        assert revoked.is_active() is False
        assert revoked.is_revoked() is True

    def test_can_act_in_environment(self):
        identity = create_agent_identity(agent_id="a1", environment="production")
        assert identity.can_act_in("production") is True
        assert identity.can_act_in("staging") is False

    def test_revoked_agent_cannot_act(self):
        revoked = AgentIdentity(
            agent_id="a2",
            status=AgentStatus.REVOKED.value,
            environment="production",
            created_at="2026-01-01T00:00:00Z",
            last_seen_at="2026-01-01T00:00:00Z",
        )
        assert revoked.can_act_in("production") is False


class TestAgentStatusEnum:

    def test_status_values(self):
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.REVOKED.value == "revoked"
        assert AgentStatus.ROTATED.value == "rotated"


class TestAgentPrivilegeEnum:

    def test_privilege_values(self):
        assert AgentPrivilegeLevel.READ_ONLY.value == "read_only"
        assert AgentPrivilegeLevel.STANDARD.value == "standard"
        assert AgentPrivilegeLevel.PRIVILEGED.value == "privileged"
        assert AgentPrivilegeLevel.ADMIN.value == "admin"


class TestComputeKeyFingerprint:

    def test_deterministic_output(self):
        fp1 = _compute_key_fingerprint("deadbeef" * 8)
        fp2 = _compute_key_fingerprint("deadbeef" * 8)
        assert fp1 == fp2

    def test_different_keys_different_fingerprints(self):
        fp1 = _compute_key_fingerprint("a" * 64)
        fp2 = _compute_key_fingerprint("b" * 64)
        assert fp1 != fp2

    def test_output_format(self):
        fp = _compute_key_fingerprint("c" * 64)
        assert fp.startswith("sha256:")
        assert len(fp) == 64 + 7

    def test_with_hex_prefix(self):
        """Key with sha256: prefix should still work."""
        fp = _compute_key_fingerprint("sha256:somekey")
        assert fp.startswith("sha256:")
