"""
Integration tests for the full Gateway pipeline.

Tests cover end-to-end flows: action request -> gateway intercept ->
policy evaluation -> risk scoring -> trust check -> decision ->
receipt generation -> audit chain recording. Includes tiered tests for
payment sizes, API methods, database operations, email routing,
chain integrity, trust updates, receipt verification, and thread safety.
"""



import pytest
import threading
import time

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.gateway_core import Gateway, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator, MerkleTree
from avs_gateway.core.audit_chain import AuditChain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gateway():
    """Return a fully configured Gateway with default policies."""
    policy_engine = PolicyEngine()
    policy_engine.load_policies(
        "avs_gateway/config/default_policies.yaml"
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
    """Return a Gateway with fresh subsystems."""
    policy_engine = PolicyEngine()
    policy_engine.load_policies(
        "avs_gateway/config/default_policies.yaml"
    )
    return Gateway(
        policy_engine=policy_engine,
        risk_engine=RiskEngine(),
        trust_memory=TrustMemory(),
        receipt_generator=ReceiptGenerator(),
        audit_chain=AuditChain(),
    )


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestFullPipelineAllow:
    """Full pipeline: ALLOW flow."""

    def test_full_pipeline_allow_file_read(self, gateway):
        """File read -> ALLOW -> signed receipt -> audit chain entry."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
        )
        # Intercept produces decision
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW

        # Record produces signed receipt and updates audit chain
        signed = gateway.record(request, decision)
        assert signed is not None
        assert gateway.receipt_generator.verify(signed) is True
        assert gateway.audit_chain.length() == 1

        # Trust should be updated
        trust = gateway.trust_memory.get_score("agent-001")
        assert trust.total_actions == 1
        assert trust.success_rate == 1.0


class TestFullPipelineDeny:
    """Full pipeline: DENY flow."""

    def test_full_pipeline_deny_file_delete(self, gateway):
        """File delete -> DENY -> signed receipt -> audit chain entry."""
        request = create_action_request(
            agent_id="agent-002",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="delete",
            parameters={"path": "/tmp/test.txt"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY

        signed = gateway.record(request, decision)
        assert gateway.receipt_generator.verify(signed) is True
        assert gateway.audit_chain.length() == 1

        trust = gateway.trust_memory.get_score("agent-002")
        assert trust.total_actions == 1
        assert trust.success_rate == 0.0


class TestFullPipelineQuarantine:
    """Full pipeline: QUARANTINE flow."""

    def test_full_pipeline_quarantine_large_payment(self, gateway):
        """Payment $5K -> QUARANTINE -> signed receipt."""
        request = create_action_request(
            agent_id="agent-003",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 5000, "to_account": "ACC-B", "from_account": "ACC-A"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.QUARANTINE

        signed = gateway.record(request, decision)
        assert gateway.receipt_generator.verify(signed) is True
        assert gateway.audit_chain.length() == 1

        trust = gateway.trust_memory.get_score("agent-003")
        assert trust.total_actions == 1  # quarantine counts as an action


class TestFullPipelineRequireApproval:
    """Full pipeline: REQUIRE_APPROVAL flow."""

    def test_full_pipeline_require_approval_api_post(self, gateway):
        """API POST -> REQUIRE_APPROVAL -> signed receipt but trust not updated."""
        request = create_action_request(
            agent_id="agent-004",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/users", "body": {"name": "test"}},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.requires_human() is True

        signed = gateway.record(request, decision)
        assert gateway.receipt_generator.verify(signed) is True

        # Trust should NOT be updated for require_approval
        trust = gateway.trust_memory.get_score("agent-004")
        assert trust.total_actions == 0


# ---------------------------------------------------------------------------
# Payment size tiers
# ---------------------------------------------------------------------------

class TestPaymentSizeTiers:
    """Tests for payment amounts across all tiers."""

    def test_payment_small_50(self, gateway):
        """Small payment ($50) -> ALLOW."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 50, "to_account": "B", "from_account": "A"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "payment_small"

    def test_payment_medium_500(self, gateway):
        """Medium payment ($500) -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 500, "to_account": "B", "from_account": "A"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "payment_medium"

    def test_payment_large_5000(self, gateway):
        """Large payment ($5000) -> QUARANTINE."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 5000, "to_account": "B", "from_account": "A"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.QUARANTINE
        assert decision.matched_policy == "payment_large"

    def test_payment_extreme_100k(self, gateway):
        """Extreme payment ($100K) -> DENY."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 100000, "to_account": "B", "from_account": "A"},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.DENY
        assert decision.matched_policy == "payment_extreme"


# ---------------------------------------------------------------------------
# API method tiers
# ---------------------------------------------------------------------------

class TestAPIMethodTiers:
    """Tests for all API HTTP methods."""

    def test_api_get(self, gateway):
        """API GET -> ALLOW."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.API,
            tool_name="api_tool", operation="GET", parameters={"endpoint": "/users"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.ALLOW

    def test_api_post(self, gateway):
        """API POST -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.API,
            tool_name="api_tool", operation="POST", parameters={"endpoint": "/users"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.REQUIRE_APPROVAL

    def test_api_put(self, gateway):
        """API PUT -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.API,
            tool_name="api_tool", operation="PUT", parameters={"endpoint": "/users/1"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.REQUIRE_APPROVAL

    def test_api_delete(self, gateway):
        """API DELETE -> DENY."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.API,
            tool_name="api_tool", operation="DELETE", parameters={"endpoint": "/users/1"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.DENY

    def test_api_patch(self, gateway):
        """API PATCH -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.API,
            tool_name="api_tool", operation="PATCH", parameters={"endpoint": "/users/1"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# Database operation tiers
# ---------------------------------------------------------------------------

class TestDatabaseOperationTiers:
    """Tests for all database operations."""

    def test_database_select(self, gateway):
        """SELECT -> ALLOW."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.DATABASE,
            tool_name="db_tool", operation="SELECT", parameters={"table": "users"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.ALLOW

    def test_database_insert(self, gateway):
        """INSERT -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.DATABASE,
            tool_name="db_tool", operation="INSERT", parameters={"table": "users", "data": {"name": "x"}},
        )
        assert gateway.intercept(request).decision_type == DecisionType.REQUIRE_APPROVAL

    def test_database_update(self, gateway):
        """UPDATE -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.DATABASE,
            tool_name="db_tool", operation="UPDATE", parameters={"table": "users", "data": {}, "where": {}},
        )
        assert gateway.intercept(request).decision_type == DecisionType.REQUIRE_APPROVAL

    def test_database_delete(self, gateway):
        """DELETE -> DENY."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.DATABASE,
            tool_name="db_tool", operation="DELETE", parameters={"table": "users", "where": {"id": "1"}},
        )
        assert gateway.intercept(request).decision_type == DecisionType.DENY

    def test_database_drop(self, gateway):
        """DROP -> DENY."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.DATABASE,
            tool_name="db_tool", operation="DROP", parameters={"table": "users"},
        )
        assert gateway.intercept(request).decision_type == DecisionType.DENY


# ---------------------------------------------------------------------------
# Email routing
# ---------------------------------------------------------------------------

class TestEmailRouting:
    """Tests for internal vs external email routing."""

    def test_email_internal_allows(self, gateway):
        """Internal email (external=False) -> ALLOW."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.EMAIL,
            tool_name="email_tool", operation="send",
            parameters={"to": "internal@company.com", "subject": "test", "body": "hello", "external": False},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.ALLOW
        assert decision.matched_policy == "email_send_internal"

    def test_email_external_requires_approval(self, gateway):
        """External email (external=True) -> REQUIRE_APPROVAL."""
        request = create_action_request(
            agent_id="agent-001", action_type=ActionType.EMAIL,
            tool_name="email_tool", operation="send",
            parameters={"to": "external@gmail.com", "subject": "test", "body": "hello", "external": True},
        )
        decision = gateway.intercept(request)
        assert decision.decision_type == DecisionType.REQUIRE_APPROVAL
        assert decision.matched_policy == "email_send_external"


# ---------------------------------------------------------------------------
# Audit chain integrity
# ---------------------------------------------------------------------------

class TestAuditChainIntegrity:
    """Tests for audit chain integrity after multiple decisions."""

    def test_audit_chain_integrity_after_10_decisions(self, gateway):
        """After 10 decisions, the audit chain verifies correctly."""
        actions = [
            (ActionType.FILE, "file_tool", "read", {}),
            (ActionType.FILE, "file_tool", "delete", {"path": "/tmp/x"}),
            (ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 50, "to_account": "B", "from_account": "A"}),
            (ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 5000, "to_account": "B", "from_account": "A"}),
            (ActionType.API, "api_tool", "GET", {"endpoint": "/users"}),
            (ActionType.API, "api_tool", "POST", {"endpoint": "/users"}),
            (ActionType.DATABASE, "db_tool", "SELECT", {"table": "users"}),
            (ActionType.DATABASE, "db_tool", "INSERT", {"table": "users", "data": {}}),
            (ActionType.EMAIL, "email_tool", "send", {"to": "test@test.com", "subject": "s", "body": "b", "external": False}),
            (ActionType.SECURITY_SCAN, "scan_tool", "run_scan", {"target": "localhost"}),
        ]

        for action_type, tool_name, operation, params in actions:
            request = create_action_request(
                agent_id="agent-001",
                action_type=action_type,
                tool_name=tool_name,
                operation=operation,
                parameters=params,
            )
            decision = gateway.intercept(request)
            gateway.record(request, decision)

        assert gateway.audit_chain.length() == 10
        valid, errors = gateway.audit_chain.verify()
        assert valid is True, f"Chain integrity errors: {errors}"
        assert errors == []


# ---------------------------------------------------------------------------
# Trust score updates
# ---------------------------------------------------------------------------

class TestTrustScoreUpdates:
    """Tests for trust score changes after decisions."""

    def test_trust_score_increases_after_allow(self, gateway):
        """Trust score increases after ALLOW decisions."""
        for i in range(5):
            request = create_action_request(
                agent_id="agent-trust",
                action_type=ActionType.FILE,
                tool_name="file_tool",
                operation="read",
                
            )
            decision = gateway.intercept(request)
            assert decision.decision_type == DecisionType.ALLOW
            gateway.record(request, decision)

        trust = gateway.trust_memory.get_score("agent-trust")
        assert trust.value > 50
        assert trust.total_actions == 5
        assert trust.success_rate == 1.0

    def test_trust_score_decreases_after_deny(self, gateway):
        """Trust score decreases after DENY decisions."""
        for i in range(5):
            request = create_action_request(
                agent_id="agent-distrust",
                action_type=ActionType.FILE,
                tool_name="file_tool",
                operation="delete",
                parameters={"path": f"/tmp/{i}.txt"},
                
            )
            decision = gateway.intercept(request)
            assert decision.decision_type == DecisionType.DENY
            gateway.record(request, decision)

        trust = gateway.trust_memory.get_score("agent-distrust")
        assert trust.value < 50
        assert trust.total_actions == 5
        assert trust.success_rate == 0.0

    def test_trust_score_mixed_allow_deny(self, gateway):
        """Mixed allow/deny produces intermediate trust score."""
        # 3 allows
        for i in range(3):
            request = create_action_request(
                agent_id="agent-mixed",
                action_type=ActionType.FILE,
                tool_name="file_tool",
                operation="read",
                
            )
            decision = gateway.intercept(request)
            gateway.record(request, decision)
        # 3 denies
        for i in range(3):
            request = create_action_request(
                agent_id="agent-mixed",
                action_type=ActionType.FILE,
                tool_name="file_tool",
                operation="delete",
                parameters={"path": f"/tmp/{i}.txt"},
                
            )
            decision = gateway.intercept(request)
            gateway.record(request, decision)

        trust = gateway.trust_memory.get_score("agent-mixed")
        assert trust.total_actions == 6
        assert trust.success_rate == 0.5


# ---------------------------------------------------------------------------
# Receipt verification
# ---------------------------------------------------------------------------

class TestReceiptVerification:
    """Tests that all receipts verify correctly."""

    def test_all_receipts_verify_correctly(self, gateway):
        """Every receipt generated and recorded verifies successfully."""
        actions = [
            (ActionType.FILE, "file_tool", "read", {}),
            (ActionType.FILE, "file_tool", "delete", {"path": "/tmp/x"}),
            (ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 5000, "to_account": "B", "from_account": "A"}),
            (ActionType.API, "api_tool", "POST", {"endpoint": "/users"}),
            (ActionType.DATABASE, "db_tool", "DROP", {"table": "users"}),
        ]

        receipts = []
        for action_type, tool_name, operation, params in actions:
            request = create_action_request(
                agent_id="agent-verify",
                action_type=action_type,
                tool_name=tool_name,
                operation=operation,
                parameters=params,
            )
            decision = gateway.intercept(request)
            signed = gateway.record(request, decision)
            receipts.append(signed)

        for signed in receipts:
            assert gateway.receipt_generator.verify(signed) is True

    def test_merkle_tree_over_receipt_hashes(self, gateway):
        """A Merkle tree built from receipt hashes has a valid root."""
        for i in range(4):
            request = create_action_request(
                agent_id="agent-merkle",
                action_type=ActionType.FILE,
                tool_name="file_tool",
                operation="read",
                
            )
            decision = gateway.intercept(request)
            gateway.record(request, decision)

        # Build Merkle tree from receipt hashes
        entries = gateway.audit_chain.get_all_entries()
        leaves = [e.signed_receipt["receipt_hash"] for e in entries]
        tree = MerkleTree(leaves)
        root = tree.root()
        assert len(root) == 64
        # Verify each leaf's inclusion proof
        for i in range(len(leaves)):
            proof = tree.proof(i)
            assert isinstance(proof, list)


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestConcurrentIntercepts:
    """Tests for thread safety of the Gateway."""

    def test_concurrent_intercepts(self, gateway):
        """5 threads, 20 actions each = 100 total intercepts."""
        num_threads = 5
        actions_per_thread = 20
        errors = []

        def worker(thread_id):
            try:
                for i in range(actions_per_thread):
                    request = create_action_request(
                        agent_id=f"agent-thread-{thread_id}",
                        action_type=ActionType.FILE,
                        tool_name="file_tool",
                        operation="read",
                        
                    )
                    decision = gateway.intercept(request)
                    gateway.record(request, decision)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert gateway.audit_chain.length() == num_threads * actions_per_thread

        valid, chain_errors = gateway.audit_chain.verify()
        assert valid is True, f"Chain integrity errors: {chain_errors}"

        stats = gateway.get_stats()
        assert stats["total_intercepts"] == num_threads * actions_per_thread

    def test_concurrent_mixed_actions(self, gateway):
        """Multiple threads with different action types."""
        num_threads = 4
        actions_per_thread = 10

        action_configs = [
            (ActionType.FILE, "file_tool", "read", {}),
            (ActionType.API, "api_tool", "GET", {"endpoint": "/users"}),
            (ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 50, "to_account": "B", "from_account": "A"}),
            (ActionType.DATABASE, "db_tool", "SELECT", {"table": "users"}),
        ]

        errors = []

        def worker(thread_id):
            try:
                action_type, tool_name, operation, params = action_configs[thread_id % len(action_configs)]
                for i in range(actions_per_thread):
                    request = create_action_request(
                        agent_id=f"mixed-agent-{thread_id}",
                        action_type=action_type,
                        tool_name=tool_name,
                        operation=operation,
                        parameters=params,
                        
                    )
                    decision = gateway.intercept(request)
                    gateway.record(request, decision)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert gateway.audit_chain.length() == num_threads * actions_per_thread
        valid, chain_errors = gateway.audit_chain.verify()
        assert valid is True


# ---------------------------------------------------------------------------
# Stats accumulation
# ---------------------------------------------------------------------------

class TestStatsAccumulation:
    """Tests for gateway statistics across many decisions."""

    def test_stats_all_decision_types(self, gateway):
        """Stats correctly count all four decision types."""
        # ALLOW: file read
        for i in range(3):
            request = create_action_request(
                agent_id="agent-stats", action_type=ActionType.FILE,
                tool_name="file_tool", operation="read",
                
            )
            d = gateway.intercept(request)
            gateway.record(request, d)

        # DENY: file delete
        for i in range(2):
            request = create_action_request(
                agent_id="agent-stats", action_type=ActionType.FILE,
                tool_name="file_tool", operation="delete",
                parameters={"path": f"/tmp/{i}.txt"},
                
            )
            d = gateway.intercept(request)
            gateway.record(request, d)

        # QUARANTINE: large payment
        request = create_action_request(
            agent_id="agent-stats", action_type=ActionType.PAYMENT,
            tool_name="payment_tool", operation="transfer",
            parameters={"amount": 5000, "to_account": "B", "from_account": "A"},
            
        )
        d = gateway.intercept(request)
        gateway.record(request, d)

        # REQUIRE_APPROVAL: api post
        for i in range(4):
            request = create_action_request(
                agent_id="agent-stats", action_type=ActionType.API,
                tool_name="api_tool", operation="POST",
                parameters={"endpoint": "/users"},
                
            )
            d = gateway.intercept(request)
            gateway.record(request, d)

        stats = gateway.get_stats()
        assert stats["total_intercepts"] == 10
        assert stats["decisions"]["allow"] == 3
        assert stats["decisions"]["deny"] == 2
        assert stats["decisions"]["quarantine"] == 1
        assert stats["decisions"]["require_approval"] == 4

