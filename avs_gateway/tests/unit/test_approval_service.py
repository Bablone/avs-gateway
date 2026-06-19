"""
Unit tests for avs_gateway.core.approval_service

Tests the approval state machine, replay protection,
approve/deny/trust integration, and the execute-once invariant.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.gateway_core import Gateway, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.approval_service import ApprovalService
from avs_gateway.storage.sqlite_store import SqliteStore
from avs_gateway.tools.simulated_tools import ToolRegistry

DB_PATH = os.path.join(tempfile.gettempdir(), "avs_test_approval.sqlite3")


@pytest.fixture
def fresh_service():
    """Fresh ApprovalService with empty SQLite store for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    store = SqliteStore(db_path=DB_PATH)
    store.init_schema()
    trust = TrustMemory()
    svc = ApprovalService(store, trust_memory=trust)
    yield svc
    store.close_all()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


@pytest.fixture
def sample_action():
    return create_action_request(
        agent_id="agent-test",
        action_type=ActionType.API,
        tool_name="api_tool",
        operation="POST",
        parameters={"endpoint": "/test"},
    )


@pytest.fixture
def sample_decision():
    """A REQUIRE_APPROVAL decision."""
    return type("FakeDecision", (), {
        "decision_type": DecisionType.REQUIRE_APPROVAL,
        "risk_score": 35,
        "trust_score": 50,
        "reason": "Medium risk API call",
        "matched_policy": "api_post",
        "is_blocking": lambda: False,
        "requires_human": lambda: True,
    })()


class TestApprovalService:
    """Tests for ApprovalService state machine."""

    def test_create_approval_request(self, fresh_service, sample_action, sample_decision):
        """Creating an approval request should return an ID and store it."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        assert isinstance(aid, str) and len(aid) > 0

        approval = fresh_service.get_approval(aid)
        assert approval is not None
        assert approval["status"] == "pending"

    def test_list_pending(self, fresh_service, sample_action, sample_decision):
        """list_pending should return only pending approvals."""
        assert fresh_service.list_pending() == []

        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        pending = fresh_service.list_pending()
        assert len(pending) == 1
        assert pending[0]["approval_id"] == aid

    def test_approve_changes_status(self, fresh_service, sample_action, sample_decision):
        """Approving should change status from pending to approved."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        ok = fresh_service.approve(aid, "admin_alice", "Verified")
        assert ok is True

        approval = fresh_service.get_approval(aid)
        assert approval["status"] == "approved"
        assert approval["decided_by"] == "admin_alice"

    def test_deny_changes_status(self, fresh_service, sample_action, sample_decision):
        """Denying should change status from pending to denied."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        ok = fresh_service.deny(aid, "admin_bob", "Suspicious")
        assert ok is True

        approval = fresh_service.get_approval(aid)
        assert approval["status"] == "denied"
        assert approval["decided_by"] == "admin_bob"

    def test_approve_not_found(self, fresh_service):
        """Approving nonexistent approval should return False."""
        assert fresh_service.approve("nonexistent", "admin") is False

    def test_approve_not_pending(self, fresh_service, sample_action, sample_decision):
        """Approving already-approved request should return False."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.approve(aid, "admin", "ok")
        assert fresh_service.approve(aid, "admin", "ok again") is False

    def test_deny_not_pending(self, fresh_service, sample_action, sample_decision):
        """Denying already-denied request should return False."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.deny(aid, "admin", "no")
        assert fresh_service.deny(aid, "admin", "no again") is False

    # -- Execute once (replay protection) --

    def test_execute_approved_once_succeeds(self, fresh_service, sample_action, sample_decision):
        """execute_approved_once should work on approved actions."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.approve(aid, "admin", "ok")

        registry = ToolRegistry.create_default_registry()
        result = fresh_service.execute_approved_once(aid, registry)
        assert result is not None

        approval = fresh_service.get_approval(aid)
        assert approval["status"] == "executed"

    def test_execute_approved_once_replay_blocked(self, fresh_service, sample_action, sample_decision):
        """Second execution of same approval must be blocked (replay protection)."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.approve(aid, "admin", "ok")

        registry = ToolRegistry.create_default_registry()
        r1 = fresh_service.execute_approved_once(aid, registry)
        assert r1 is not None

        r2 = fresh_service.execute_approved_once(aid, registry)
        assert r2 is None  # REPLAY BLOCKED

    def test_execute_denied_blocked(self, fresh_service, sample_action, sample_decision):
        """Executing a denied approval must be blocked."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.deny(aid, "admin", "no")

        registry = ToolRegistry.create_default_registry()
        result = fresh_service.execute_approved_once(aid, registry)
        assert result is None

    def test_execute_pending_blocked(self, fresh_service, sample_action, sample_decision):
        """Executing a pending (not yet approved) approval must be blocked."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        # Do NOT approve

        registry = ToolRegistry.create_default_registry()
        result = fresh_service.execute_approved_once(aid, registry)
        assert result is None

    def test_execute_not_found(self, fresh_service):
        """Executing nonexistent approval must return None."""
        registry = ToolRegistry.create_default_registry()
        assert fresh_service.execute_approved_once("nonexistent", registry) is None

    # -- Trust updates --

    def test_approve_updates_trust(self, fresh_service, sample_action, sample_decision):
        """Approving should update trust memory positively."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        before = fresh_service.trust_memory.get_score("agent-test")
        fresh_service.approve(aid, "admin", "ok")
        after = fresh_service.trust_memory.get_score("agent-test")
        assert after.value > before.value

    def test_deny_updates_trust_negative(self, fresh_service, sample_action, sample_decision):
        """Denying should update trust memory negatively."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        before = fresh_service.trust_memory.get_score("agent-test")
        fresh_service.deny(aid, "admin", "no")
        after = fresh_service.trust_memory.get_score("agent-test")
        assert after.value < before.value

    # -- Audit events --

    def test_audit_timeline_recorded(self, fresh_service, sample_action, sample_decision):
        """Approval lifecycle should create audit events."""
        aid = fresh_service.create_approval_request(sample_action, sample_decision)
        fresh_service.approve(aid, "admin", "ok")
        registry = ToolRegistry.create_default_registry()
        fresh_service.execute_approved_once(aid, registry)

        timeline = fresh_service.get_approval_timeline(aid)
        event_types = [e["event_type"] for e in timeline]
        assert "approval_created" in event_types
        assert "approval_approved" in event_types
        assert "approval_executed" in event_types

    # -- Stats --

    def test_stats_reflect_state(self, fresh_service, sample_action, sample_decision):
        """Stats should reflect the current state accurately."""
        # Create 3 approvals
        a1 = fresh_service.create_approval_request(sample_action, sample_decision)
        a2 = fresh_service.create_approval_request(sample_action, sample_decision)
        a3 = fresh_service.create_approval_request(sample_action, sample_decision)

        fresh_service.approve(a1, "admin", "ok")
        fresh_service.deny(a2, "admin", "no")
        # a3 stays pending

        stats = fresh_service.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["denied"] == 1
        assert stats["executed"] == 0
