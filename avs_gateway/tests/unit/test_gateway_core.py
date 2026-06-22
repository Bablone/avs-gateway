"""
Unit tests for the Gateway core orchestration module.

Tests cover all decision types (ALLOW, DENY, QUARANTINE, REQUIRE_APPROVAL),
fail-closed behavior, trust memory updates, and statistics accumulation.
"""



from pathlib import Path
import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.gateway_core import Gateway, Decision, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gateway():
    """Return a fully configured Gateway instance with default policies."""
    policy_engine = PolicyEngine()
    policy_engine.load_policies(
        str(Path(__file__).resolve().parents[2] / "config" / "default_policies.yaml")
    )
    return Gateway(
        policy_engine=policy_engine,
        risk_engine=RiskEngine(),
        trust_memory=TrustMemory(),
        receipt_generator=ReceiptGenerator(),
        audit_chain=AuditChain(),
    )


@pytest.fixture
def fresh_gateway():
    """Return a Gateway with NO policies loaded (tests default behavior)."""
    return Gateway(
        policy_engine=PolicyEngine(),
        risk_engine=RiskEngine(),
        trust_memory=TrustMemory(),
        receipt_generator=ReceiptGenerator(),
        audit_chain=AuditChain(),
    )


# ---------------------------------------------------------------------------
# ALLOW decisions
# ---------------------------------------------------------------------------

class TestAllowDecisions:
    """Tests for ALLOW decisions."""

    def test_allow_file_read(self, gateway):
        """A file read request results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "file_read"
        assert decision.is_blocking() is False
        assert decision.requires_human() is False

    def test_allow_api_get(self, gateway):
        """An API GET request results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="GET",
            parameters={"endpoint": "/users"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "api_get"

    def test_allow_database_select(self, gateway):
        """A database SELECT results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="SELECT",
            parameters={"table": "users"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "database_select"

    def test_allow_security_scan(self, gateway):
        """A security scan results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.SECURITY_SCAN,
            tool_name="scan_tool",
            operation="run_scan",
            parameters={"target": "localhost"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "security_scan_run"

    def test_allow_small_payment(self, gateway):
        """A small payment (<= $100) results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 50, "to_account": "acc-1", "from_account": "acc-2"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "payment_small"

    def test_allow_internal_email(self, gateway):
        """An internal email results in ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.EMAIL,
            tool_name="email_tool",
            operation="send",
            parameters={"to": "internal@company.com", "subject": "test", "body": "hello", "external": False},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "email_send_internal"


# ---------------------------------------------------------------------------
# DENY decisions
# ---------------------------------------------------------------------------

class TestDenyDecisions:
    """Tests for DENY decisions."""

    def test_deny_file_delete(self, gateway):
        """A file delete request results in DENY."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="delete",
            parameters={"path": "/tmp/test.txt"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert decision.is_blocking() is True
        assert decision.requires_human() is False

    def test_deny_api_delete(self, gateway):
        """An API DELETE results in DENY."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="DELETE",
            parameters={"endpoint": "/users/1"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert decision.matched_policy == "api_delete"

    def test_deny_database_delete(self, gateway):
        """A database DELETE results in DENY."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="DELETE",
            parameters={"table": "users", "where": {"id": "1"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert decision.matched_policy == "database_delete"

    def test_deny_database_drop(self, gateway):
        """A database DROP results in DENY (critical risk + policy)."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="DROP",
            parameters={"table": "users"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY

    def test_deny_extreme_payment(self, gateway):
        """An extreme payment (> $50K) results in DENY."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 100000, "to_account": "acc-1", "from_account": "acc-2"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert decision.matched_policy == "payment_extreme"


# ---------------------------------------------------------------------------
# QUARANTINE decisions
# ---------------------------------------------------------------------------

class TestQuarantineDecisions:
    """Tests for QUARANTINE decisions."""

    def test_quarantine_large_payment(self, gateway):
        """A large payment ($1K - $50K) results in QUARANTINE."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 5000, "to_account": "acc-1", "from_account": "acc-2"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.QUARANTINE
        assert decision.is_blocking() is True
        assert decision.requires_human() is False


# ---------------------------------------------------------------------------
# REQUIRE_APPROVAL decisions
# ---------------------------------------------------------------------------

class TestRequireApprovalDecisions:
    """Tests for REQUIRE_APPROVAL decisions."""

    def test_require_approval_medium_payment(self, gateway):
        """A medium payment ($100-$1K) results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 500, "to_account": "acc-1", "from_account": "acc-2"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.is_blocking() is False
        assert decision.requires_human() is True

    def test_require_approval_api_post(self, gateway):
        """An API POST results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/users", "body": {"name": "test"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "api_post"

    def test_require_approval_database_insert(self, gateway):
        """A database INSERT results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="INSERT",
            parameters={"table": "users", "data": {"name": "test"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL

    def test_require_approval_external_email(self, gateway):
        """An external email results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.EMAIL,
            tool_name="email_tool",
            operation="send",
            parameters={"to": "external@gmail.com", "subject": "test", "body": "hello", "external": True},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL

    def test_require_approval_api_put(self, gateway):
        """An API PUT results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="PUT",
            parameters={"endpoint": "/users/1", "body": {"name": "updated"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "api_put"

    def test_require_approval_api_patch(self, gateway):
        """An API PATCH results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="PATCH",
            parameters={"endpoint": "/users/1", "body": {"name": "patched"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "api_patch"

    def test_require_approval_payment_refund(self, gateway):
        """A payment refund results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="refund",
            parameters={"payment_id": "PAY-000001"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "payment_refund"

    def test_require_approval_database_update(self, gateway):
        """A database UPDATE results in REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="UPDATE",
            parameters={"table": "users", "data": {"name": "updated"}, "where": {"id": "1"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# Fail-closed behavior
# ---------------------------------------------------------------------------

class TestFailClosed:
    """Tests for fail-closed (safe default) behavior."""

    def test_fail_closed_invalid_request(self, gateway):
        """An invalid request (empty agent_id) results in DENY."""
        request = create_action_request(
            agent_id="",  # Invalid - empty agent_id
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert "validation" in decision.reason.lower()

    def test_fail_closed_exception(self, gateway):
        """An engine failure results in DENY (fail-closed)."""
        # Corrupt the policy engine to cause an exception
        gateway.policy_engine._rules = None  # This will cause evaluate() to crash
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert "exception" in decision.reason.lower() or "Unhandled" in decision.reason


# ---------------------------------------------------------------------------
# Record and trust updates
# ---------------------------------------------------------------------------

class TestRecordAndTrust:
    """Tests for record() and trust memory updates."""

    def test_record_updates_trust_on_allow(self, gateway):
        """Recording an ALLOW decision updates trust with success."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        signed_receipt = gateway.record(request, decision)
        assert signed_receipt is not None
        # Trust should have been updated
        trust_score = gateway.trust_memory.get_score("agent-001")
        assert trust_score.total_actions == 1
        assert trust_score.success_rate == 1.0

    def test_record_updates_trust_on_deny(self, gateway):
        """Recording a DENY decision updates trust with failure."""
        request = create_action_request(
            agent_id="agent-002",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="delete",
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        signed_receipt = gateway.record(request, decision)
        assert signed_receipt is not None
        trust_score = gateway.trust_memory.get_score("agent-002")
        assert trust_score.total_actions == 1
        assert trust_score.success_rate == 0.0

    def test_record_does_not_update_trust_on_require_approval(self, gateway):
        """Recording REQUIRE_APPROVAL does not update trust yet."""
        request = create_action_request(
            agent_id="agent-003",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/users"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        signed_receipt = gateway.record(request, decision)
        assert signed_receipt is not None
        # Trust should NOT have been updated for require_approval
        trust_score = gateway.trust_memory.get_score("agent-003")
        assert trust_score.total_actions == 0

    def test_record_appends_to_audit_chain(self, gateway):
        """Recording appends to the audit chain."""
        chain_len_before = gateway.audit_chain.length()
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        gateway.record(request, decision)
        assert gateway.audit_chain.length() == chain_len_before + 1

    def test_signed_receipt_verifies(self, gateway):
        """A recorded signed receipt can be verified."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        signed_receipt = gateway.record(request, decision)
        assert gateway.receipt_generator.verify(signed_receipt) is True


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestGetStats:
    """Tests for get_stats() method."""

    def test_get_stats_initial(self, gateway):
        """Initial stats show zero intercepts."""
        stats = gateway.get_stats()
        assert stats["total_intercepts"] == 0
        assert stats["audit_chain_length"] == 0
        assert stats["decisions"]["allow"] == 0
        assert stats["decisions"]["deny"] == 0
        assert stats["decisions"]["require_approval"] == 0
        assert stats["decisions"]["quarantine"] == 0

    def test_get_stats_after_intercepts(self, gateway):
        """Stats accumulate after multiple intercepts."""
        # ALLOW
        req1 = create_action_request(
            agent_id="agent-001", action_type=ActionType.FILE,
            tool_name="file_tool", operation="read",
        )
        gateway.intercept(req1)
        # DENY
        req2 = create_action_request(
            agent_id="agent-001", action_type=ActionType.FILE,
            tool_name="file_tool", operation="delete",
        )
        gateway.intercept(req2)
        # QUARANTINE
        req3 = create_action_request(
            agent_id="agent-001", action_type=ActionType.PAYMENT,
            tool_name="payment_tool", operation="transfer",
            parameters={"amount": 5000, "to_account": "a", "from_account": "b"},
        )
        gateway.intercept(req3)

        stats = gateway.get_stats()
        assert stats["total_intercepts"] == 3
        assert stats["decisions"]["allow"] == 1
        assert stats["decisions"]["deny"] == 1
        assert stats["decisions"]["quarantine"] == 1

    def test_processing_time_recorded(self, gateway):
        """Processing time is recorded in the decision."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        decision = gateway.intercept(request)
        assert decision.processing_time_ms >= 0.0
