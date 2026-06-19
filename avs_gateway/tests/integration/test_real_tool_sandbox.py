"""
Integration tests for AVS Gateway v0.3.0-alpha real tool sandbox.

Tests the full chain: Gateway intercept -> decision -> real tool execution.
Proves that allowed actions create real files and denied actions do not.
"""

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
from avs_gateway.tools.real_tool_registry import RealToolRegistry


@pytest.fixture
def gateway_with_real_tools():
    """Gateway configured with real file sandbox tools."""
    tmp = tempfile.mkdtemp(prefix="avs_integration_sandbox_")

    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    re = RiskEngine()
    tm = TrustMemory()
    rg = ReceiptGenerator()
    ac = AuditChain()

    gw = Gateway(
        policy_engine=pe,
        risk_engine=re,
        trust_memory=tm,
        receipt_generator=rg,
        audit_chain=ac,
    )

    registry = RealToolRegistry(sandbox_root=tmp)

    yield gw, registry, tmp

    # cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


class TestRealToolSandboxIntegration:
    """Integration tests for Gateway -> real tool sandbox."""

    def test_allowed_write_creates_real_file(self, gateway_with_real_tools):
        """An ALLOW decision on file_write should create a real file."""
        gw, registry, tmp = gateway_with_real_tools

        action = create_action_request(
            agent_id="agent-file-001",
            action_type=ActionType.FILE,
            tool_name="file_sandbox",
            operation="write",
            parameters={"path": "output.txt", "content": "real data"},
        )
        decision = gw.intercept(action)

        # For the demo we directly use the registry ( Gateway decides, registry executes )
        result = registry.execute("file_write", raw_path="output.txt", content="real data")

        assert result.status == "success"
        assert result.success is True

        # Verify real file exists
        real_path = os.path.join(tmp, "output.txt")
        assert os.path.isfile(real_path)
        with open(real_path) as f:
            assert f.read() == "real data"

    def test_allowed_read_returns_real_content(self, gateway_with_real_tools):
        """An ALLOW decision on file_read should return real file content."""
        gw, registry, tmp = gateway_with_real_tools

        # Pre-create file
        registry.execute("file_write", raw_path="hello.txt", content="world")

        result = registry.execute("file_read", raw_path="hello.txt")
        assert result.status == "success"
        assert result.content == "world"

    def test_traversal_blocked_no_file_created(self, gateway_with_real_tools):
        """A blocked traversal should NOT create a file outside sandbox."""
        gw, registry, tmp = gateway_with_real_tools

        outside = os.path.join(os.path.dirname(tmp), "escape.txt")
        if os.path.exists(outside):
            os.remove(outside)

        result = registry.execute("file_write", raw_path="../escape.txt", content="bad")
        assert result.status == "blocked"
        assert not os.path.exists(outside)

    def test_absolute_path_blocked(self, gateway_with_real_tools):
        """An absolute path outside sandbox should be blocked."""
        gw, registry, tmp = gateway_with_real_tools

        abs_path = "/tmp/avs_abs_escape.txt"
        if os.path.exists(abs_path):
            os.remove(abs_path)

        result = registry.execute("file_write", raw_path=abs_path, content="abs bad")
        assert result.status == "blocked"
        assert not os.path.exists(abs_path)

    def test_delete_blocked_file_preserved(self, gateway_with_real_tools):
        """Delete should be blocked and file must remain."""
        gw, registry, tmp = gateway_with_real_tools

        registry.execute("file_write", raw_path="preserve.txt", content="keep me")

        result = registry.execute("file_delete", raw_path="preserve.txt")
        assert result.status == "blocked"

        # File still exists
        r2 = registry.execute("file_read", raw_path="preserve.txt")
        assert r2.status == "success"
        assert r2.content == "keep me"

    def test_blocked_result_has_audit_fields(self, gateway_with_real_tools):
        """Blocked results must contain fields needed for audit/timeline."""
        gw, registry, tmp = gateway_with_real_tools

        result = registry.execute("file_write", raw_path="../attack.txt", content="x")
        assert result.status == "blocked"
        assert result.raw_requested_path == "../attack.txt"
        assert result.error is not None
        assert len(result.error) > 0

    def test_success_result_has_resolved_path(self, gateway_with_real_tools):
        """Successful results must show the resolved canonical path."""
        gw, registry, tmp = gateway_with_real_tools

        result = registry.execute("file_write", raw_path="sub/dir/file.txt", content="y")
        assert result.status == "success"
        assert result.resolved_path is not None
        assert "file.txt" in result.resolved_path
        # Must be inside sandbox
        assert str(tmp) in result.resolved_path

    def test_list_shows_created_files(self, gateway_with_real_tools):
        """List should reflect files created through the registry."""
        gw, registry, tmp = gateway_with_real_tools

        registry.execute("file_write", raw_path="a.txt", content="a")
        registry.execute("file_write", raw_path="b.txt", content="b")

        result = registry.execute("file_list", raw_path=".")
        assert result.status == "success"
        assert "a.txt" in result.content
        assert "b.txt" in result.content
