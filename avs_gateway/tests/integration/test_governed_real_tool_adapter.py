"""
Integration tests: @governed_tool + real file sandbox.

Proves the full chain:
    @governed_tool decorator -> Gateway.intercept -> real file I/O
    Allowed actions create real files.
    Denied actions do not.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.models.action_request import ActionType
from avs_gateway.core.policy_engine import PolicyEngine, PolicyRule, DecisionType
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway
from avs_gateway.adapters.governed import governed_tool, set_default_gateway


@pytest.fixture
def gateway_with_sandbox():
    """Gateway configured for testing with a real temp sandbox."""
    tmp = tempfile.mkdtemp(prefix="avs_governed_integration_")

    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    # Add test-specific allow rule for file writes
    pe.add_rule(PolicyRule(
        name="file_write_test_allow",
        description="File writes allowed in test environment",
        priority=15,
        condition={"action_type": "file", "operation": "write"},
        decision=DecisionType.ALLOW,
        reason="File writes allowed in test environment",
        enabled=True,
        tags=["file", "write", "test"],
    ))
    gw = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    set_default_gateway(gw)

    yield gw, tmp

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestGovernedRealToolAdapter:
    """Integration: @governed_tool + actual filesystem I/O."""

    def test_governed_write_creates_real_file(self, gateway_with_sandbox):
        """An ALLOWed @governed write should create a real file."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="file_write",
            action_type=ActionType.FILE,
            operation="write",
            gateway=gw,
        )
        def write_hello(path: str, content: str) -> dict:
            with open(path, "w") as f:
                f.write(content)
            return {"written": True}

        target = os.path.join(tmp, "hello.txt")
        result = write_hello(path=target, content="world")

        assert result.executed is True
        assert result.decision == "allow"
        assert os.path.isfile(target)
        with open(target) as f:
            assert f.read() == "world"

    def test_governed_delete_blocked(self, gateway_with_sandbox):
        """A DENYed @governed delete should NOT remove the file."""
        gw, tmp = gateway_with_sandbox

        # Create a file first
        target = os.path.join(tmp, "preserve.txt")
        with open(target, "w") as f:
            f.write("keep me")

        @governed_tool(
            tool_name="file_delete",
            action_type=ActionType.FILE,
            operation="delete",
            gateway=gw,
        )
        def remove_file(path: str) -> dict:
            os.remove(path)
            return {"deleted": True}

        result = remove_file(path=target)

        assert result.executed is False
        assert result.decision == "deny"
        assert os.path.isfile(target)  # File still exists

    def test_governed_delete_blocked_by_policy(self, gateway_with_sandbox):
        """A DENYed @governed delete should be blocked at the policy layer."""
        gw, tmp = gateway_with_sandbox

        target = os.path.join(tmp, "preserve.txt")
        with open(target, "w") as f:
            f.write("keep me")

        @governed_tool(
            tool_name="file_delete",
            action_type=ActionType.FILE,
            operation="delete",
            gateway=gw,
        )
        def delete_any(path: str) -> dict:
            os.remove(path)
            return {"deleted": True}

        result = delete_any(path=target)

        assert result.executed is False
        assert result.decision == "deny"
        assert os.path.isfile(target)  # File still exists

    def test_governed_receipt_on_allow(self, gateway_with_sandbox):
        """An ALLOWed action should produce a receipt hash."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="file_write",
            action_type=ActionType.FILE,
            operation="write",
            gateway=gw,
        )
        def write_with_receipt(path: str, content: str) -> dict:
            with open(path, "w") as f:
                f.write(content)
            return {"done": True}

        target = os.path.join(tmp, "receipt_test.txt")
        result = write_with_receipt(path=target, content="x")

        assert result.executed is True
        assert result.receipt_hash is not None
        assert len(result.receipt_hash) > 0

    def test_governed_reason_on_deny(self, gateway_with_sandbox):
        """A DENYed action should include a human-readable reason."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="file_delete",
            action_type=ActionType.FILE,
            operation="delete",
            gateway=gw,
        )
        def delete_any(path: str) -> dict:
            os.remove(path)
            return {"deleted": True}

        target = os.path.join(tmp, "survivor.txt")
        with open(target, "w") as f:
            f.write("i survive")

        result = delete_any(path=target)

        assert result.executed is False
        assert result.reason  # Non-empty reason string
        assert len(result.reason) > 0

    def test_governed_api_call_allowed(self, gateway_with_sandbox):
        """An API GET through @governed should be allowed."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="api_get",
            action_type=ActionType.API,
            operation="GET",
            gateway=gw,
        )
        def fetch(endpoint: str) -> dict:
            return {"status": 200, "body": f"data from {endpoint}"}

        result = fetch(endpoint="/status")

        assert result.executed is True
        assert result.decision == "allow"
        assert result.function_result["status"] == 200

    def test_multiple_tools_same_gateway(self, gateway_with_sandbox):
        """Multiple @governed tools should share one Gateway correctly."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="file_write", action_type=ActionType.FILE,
            operation="write", gateway=gw,
        )
        def w(path: str, content: str) -> dict:
            with open(path, "w") as f:
                f.write(content)
            return {"w": True}

        @governed_tool(
            tool_name="file_read", action_type=ActionType.FILE,
            operation="read", gateway=gw,
        )
        def r(path: str) -> dict:
            with open(path) as f:
                return {"data": f.read()}

        f1 = os.path.join(tmp, "multi.txt")
        rw = w(path=f1, content="multi")
        rr = r(path=f1)

        assert rw.executed is True
        assert rr.executed is True
        assert rr.function_result["data"] == "multi"

    def test_to_dict_serializable(self, gateway_with_sandbox):
        """Result.to_dict() should be JSON-friendly."""
        gw, tmp = gateway_with_sandbox

        @governed_tool(
            tool_name="file_write",
            action_type=ActionType.FILE,
            operation="write",
            gateway=gw,
        )
        def w(path: str, content: str) -> dict:
            with open(path, "w") as f:
                f.write(content)
            return {"ok": True}

        import json
        result = w(path=os.path.join(tmp, "json.txt"), content="j")
        d = result.to_dict()

        # Should not raise when serializing
        json_str = json.dumps(d, default=str)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
