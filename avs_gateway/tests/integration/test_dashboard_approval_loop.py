"""
Integration tests for AVS Gateway v0.2 dashboard approval loop.

Tests the full flow: intercept -> REQUIRE_APPROVAL -> persist ->
approve/deny -> execute once (or block) -> audit -> trust -> restart.
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

DB_PATH = os.path.join(tempfile.gettempdir(), "avs_test_integration.sqlite3")


@pytest.fixture
def gateway_with_approval():
    """Fresh Gateway with SQLite-backed approval service."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    store = SqliteStore(db_path=DB_PATH)
    store.init_schema()

    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    re = RiskEngine()
    tm = TrustMemory()
    rg = ReceiptGenerator()
    ac = AuditChain()
    approval = ApprovalService(store, trust_memory=tm)

    gw = Gateway(
        policy_engine=pe,
        risk_engine=re,
        trust_memory=tm,
        receipt_generator=rg,
        audit_chain=ac,
        approval_service=approval,
    )
    yield gw
    store.close_all()
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


class TestDashboardApprovalLoop:
    """Integration tests for the v0.2 approval lifecycle."""

    # -- Core invariants --

    def test_require_approval_creates_pending(self, gateway_with_approval):
        """REQUIRE_APPROVAL decision should create a pending approval request."""
        action = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/customers"},
        )
        decision = gateway_with_approval.intercept(action)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL

        pending = gateway_with_approval.approval_service.list_pending()
        assert len(pending) == 1
        assert pending[0]["agent_id"] == "agent-001"
        assert pending[0]["status"] == "pending"

    def test_pending_survives_restart(self, gateway_with_approval):
        """A pending approval must survive process restart (SQLite persistence)."""
        action = create_action_request(
            agent_id="agent-002",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="PUT",
            parameters={"endpoint": "/customers/123"},
        )
        decision = gateway_with_approval.intercept(action)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL

        # Get approval_id before close
        pending = gateway_with_approval.approval_service.list_pending()
        approval_id = pending[0]["approval_id"]

        # Close store (simulate restart)
        gateway_with_approval.approval_service.store.close_all()

        # Rebuild everything from same DB
        store2 = SqliteStore(db_path=DB_PATH)
        approval2 = ApprovalService(store2, trust_memory=TrustMemory())

        approval_after = approval2.get_approval(approval_id)
        assert approval_after is not None
        assert approval_after["status"] == "pending"
        store2.close_all()

    def test_approve_then_execute_once(self, gateway_with_approval):
        """Approved action should execute exactly once, replay blocked."""
        action = create_action_request(
            agent_id="agent-003",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/invoices"},
        )
        gateway_with_approval.intercept(action)

        pending = gateway_with_approval.approval_service.list_pending()
        aid = pending[0]["approval_id"]

        gateway_with_approval.approval_service.approve(aid, "admin", "ok")

        registry = ToolRegistry.create_default_registry()
        r1 = gateway_with_approval.approval_service.execute_approved_once(aid, registry)
        assert r1 is not None  # First execution succeeds

        r2 = gateway_with_approval.approval_service.execute_approved_once(aid, registry)
        assert r2 is None  # REPLAY BLOCKED

    def test_denied_never_executes(self, gateway_with_approval):
        """A denied action must never execute, even after restart."""
        action = create_action_request(
            agent_id="agent-004",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="PUT",
            parameters={"endpoint": "/customers/999"},
        )
        gateway_with_approval.intercept(action)

        pending = gateway_with_approval.approval_service.list_pending()
        aid = pending[0]["approval_id"]

        gateway_with_approval.approval_service.deny(aid, "admin", "Too risky PUT")

        registry = ToolRegistry.create_default_registry()
        result = gateway_with_approval.approval_service.execute_approved_once(aid, registry)
        assert result is None  # BLOCKED: was denied

    def test_cannot_execute_pending(self, gateway_with_approval):
        """A pending (not yet approved) action must not execute."""
        action = create_action_request(
            agent_id="agent-005",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="PATCH",
            parameters={"endpoint": "/customers/123"},
        )
        gateway_with_approval.intercept(action)

        pending = gateway_with_approval.approval_service.list_pending()
        aid = pending[0]["approval_id"]

        # Do NOT approve
        registry = ToolRegistry.create_default_registry()
        result = gateway_with_approval.approval_service.execute_approved_once(aid, registry)
        assert result is None  # BLOCKED: not approved yet

    # -- Trust impact --

    def test_approve_increases_trust(self, gateway_with_approval):
        """Human approval should increase the agent's trust score."""
        action = create_action_request(
            agent_id="agent-trust-test",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/safe"},
        )
        gateway_with_approval.intercept(action)

        before = gateway_with_approval.trust_memory.get_score("agent-trust-test")
        pending = gateway_with_approval.approval_service.list_pending()
        gateway_with_approval.approval_service.approve(pending[0]["approval_id"], "admin", "ok")
        after = gateway_with_approval.trust_memory.get_score("agent-trust-test")

        assert after.value > before.value

    def test_deny_decreases_trust(self, gateway_with_approval):
        """Human denial should decrease the agent's trust score."""
        action = create_action_request(
            agent_id="agent-trust-test-2",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/risky"},
        )
        gateway_with_approval.intercept(action)

        before = gateway_with_approval.trust_memory.get_score("agent-trust-test-2")
        pending = gateway_with_approval.approval_service.list_pending()
        gateway_with_approval.approval_service.deny(pending[0]["approval_id"], "admin", "no")
        after = gateway_with_approval.trust_memory.get_score("agent-trust-test-2")

        assert after.value < before.value

    # -- Audit persistence --

    def test_approval_audit_timeline(self, gateway_with_approval):
        """Full approval lifecycle should create a complete audit timeline."""
        action = create_action_request(
            agent_id="agent-audit",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/audit-test"},
        )
        gateway_with_approval.intercept(action)

        pending = gateway_with_approval.approval_service.list_pending()
        aid = pending[0]["approval_id"]

        gateway_with_approval.approval_service.approve(aid, "admin", "verified")
        registry = ToolRegistry.create_default_registry()
        gateway_with_approval.approval_service.execute_approved_once(aid, registry)

        timeline = gateway_with_approval.approval_service.get_approval_timeline(aid)
        event_types = [e["event_type"] for e in timeline]

        assert "approval_created" in event_types
        assert "approval_approved" in event_types
        assert "approval_executed" in event_types

    # -- Decision counts unaffected --

    def test_existing_gateway_decisions_unchanged(self, gateway_with_approval):
        """Adding approval service should not change existing decision semantics."""
        # ALLOW
        a_allow = create_action_request(
            agent_id="agent-010", action_type=ActionType.FILE,
            tool_name="file_tool", operation="read", parameters={"path": "/tmp/a.txt"},
        )
        d_allow = gateway_with_approval.intercept(a_allow)
        assert d_allow.decision_type == DecisionType.ALLOW

        # DENY
        a_deny = create_action_request(
            agent_id="agent-011", action_type=ActionType.FILE,
            tool_name="file_tool", operation="delete", parameters={"path": "/tmp/a.txt"},
        )
        d_deny = gateway_with_approval.intercept(a_deny)
        assert d_deny.decision_type == DecisionType.DENY

        # QUARANTINE
        a_quar = create_action_request(
            agent_id="agent-012", action_type=ActionType.PAYMENT,
            tool_name="payment_tool", operation="transfer", parameters={"amount": 5000},
        )
        d_quar = gateway_with_approval.intercept(a_quar)
        assert d_quar.decision_type == DecisionType.QUARANTINE

        stats = gateway_with_approval.get_stats()
        assert stats["total_intercepts"] >= 3

    # -- Multiple approvals in queue --

    def test_multiple_pending(self, gateway_with_approval):
        """Multiple actions can queue for approval simultaneously."""
        for i in range(5):
            action = create_action_request(
                agent_id=f"agent-multi-{i}",
                action_type=ActionType.API,
                tool_name="api_tool",
                operation="POST",
                parameters={"endpoint": f"/endpoint-{i}"},
            )
            gateway_with_approval.intercept(action)

        pending = gateway_with_approval.approval_service.list_pending()
        assert len(pending) == 5

        # Approve 2, deny 2, leave 1 pending
        gateway_with_approval.approval_service.approve(pending[0]["approval_id"], "admin", "ok")
        gateway_with_approval.approval_service.approve(pending[1]["approval_id"], "admin", "ok")
        gateway_with_approval.approval_service.deny(pending[2]["approval_id"], "admin", "no")
        gateway_with_approval.approval_service.deny(pending[3]["approval_id"], "admin", "no")
        # pending[4] stays pending

        stats = gateway_with_approval.approval_service.get_stats()
        assert stats["pending"] == 1
        assert stats["approved"] == 2
        assert stats["denied"] == 2
        assert stats["total"] == 5
