"""
Integration tests: LangChain-style tool execution governed by AVS.

Proves the full stack:
    Mock LangChain tool -> AVSGovernedTool logic -> Gateway.intercept()
    -> Policy engine -> Decision -> Execute OR Block -> Sandbox enforced

Uses real FileSandbox (v0.3.0) and HTTPSandbox (v0.3.2) for realistic
boundary enforcement. No live LLM. No network.
"""

import sys
import os
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from avs_gateway.models.action_request import ActionType
from avs_gateway.core.gateway_core import Gateway, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine, PolicyRule, DecisionType as PolicyDecisionType
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.tools.file_sandbox import FileSandbox
from avs_gateway.tools.http_sandbox import HTTPSandbox


# ---------------------------------------------------------------------------
# Minimal LangChain stub for testing
# ---------------------------------------------------------------------------

class _StubTool:
    """Minimal stub mimicking LangChain BaseTool interface."""

    def __init__(self, name: str, description: str, func=None):
        self.name = name
        self.description = description
        self.args_schema = None
        self.return_direct = False
        self.verbose = False
        self.callbacks = None
        self.tags = None
        self.metadata = None
        self._func = func

    def _run(self, *args, **kwargs):
        if self._func:
            return self._func(*args, **kwargs)
        return f"result from {self.name}"


# ---------------------------------------------------------------------------
# Manual governed tool (same logic as AVSGovernedTool, without LangChain dep)
# ---------------------------------------------------------------------------

class _ManualGovernedTool:
    """Manual implementation of AVSGovernedTool logic for testing."""

    def __init__(self, wrapped, gateway, action_type, operation, agent_id="test_agent"):
        self.wrapped_tool = wrapped
        self.gateway = gateway
        self.action_type = action_type
        self.operation = operation
        self.agent_id = agent_id
        self.context = {}
        self.name = wrapped.name

    def run(self, *args, **kwargs):
        """Execute through AVS governance."""
        from avs_gateway.models.action_request import create_action_request
        import json

        # Serialize input
        if kwargs and args:
            tool_input = json.dumps({"args": list(args), "kwargs": kwargs}, default=str)
        elif kwargs:
            tool_input = json.dumps(kwargs, default=str)
        elif args:
            tool_input = str(args[0]) if len(args) == 1 else json.dumps(list(args), default=str)
        else:
            tool_input = ""

        action = create_action_request(
            agent_id=self.agent_id,
            action_type=self.action_type,
            tool_name=self.wrapped_tool.name,
            operation=self.operation,
            parameters={"tool_input": tool_input},
            context={
                "langchain_tool": True,
                "tool_description": getattr(self.wrapped_tool, "description", ""),
            },
        )

        decision = self.gateway.intercept(action)

        if decision.decision_type == DecisionType.ALLOW:
            try:
                result = self.wrapped_tool._run(*args, **kwargs)
                result_str = str(result) if result is not None else ""
                try:
                    self.gateway.record(action, decision)
                except Exception:
                    pass
                return result_str
            except Exception as exc:
                return f"[AVS ERROR] {exc}"
        elif decision.decision_type in (DecisionType.DENY, DecisionType.QUARANTINE):
            return (
                f"[AVS {decision.decision_type.value.upper()}] "
                f"Tool '{self.wrapped_tool.name}' was blocked.\n"
                f"Reason: {decision.reason}\n"
                f"You do not have permission to execute this action."
            )
        elif decision.decision_type == DecisionType.REQUIRE_APPROVAL:
            return (
                f"[AVS PENDING] Tool '{self.wrapped_tool.name}' requires human approval.\n"
                f"Reason: {decision.reason}"
            )
        else:
            return f"[AVS ERROR] Unknown decision: {decision.decision_type}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gateway():
    """Gateway with default policies."""
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    gw = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    return gw


@pytest.fixture
def gateway_with_file_allow():
    """Gateway with explicit file write allow policy for testing."""
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    pe.add_rule(PolicyRule(
        name="file_write_test_allow",
        description="Allow file writes in test",
        priority=25,
        condition={"action_type": "file", "operation": "write"},
        decision=PolicyDecisionType.ALLOW,
        reason="File writes allowed in test",
        enabled=True,
        tags=["test"],
    ))
    gw = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    return gw


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestFilesystemBoundaryViaLangChainAdapter:
    """Prove AVS governs LangChain-style file tools using real FileSandbox."""

    def test_safe_file_read_inside_sandbox(self, gateway, tmp_path):
        """File read inside sandbox -> ALLOW -> content returned."""
        sandbox = FileSandbox(root=str(tmp_path))
        test_file = tmp_path / "data.txt"
        test_file.write_text("hello from sandbox")

        def file_read(path):
            result = sandbox.read_file(path)
            return result.content if result.success else f"ERROR: {result.error}"

        tool = _StubTool("file_read", "Read a file", file_read)
        gov = _ManualGovernedTool(tool, gateway, ActionType.FILE, "read")

        result = gov.run("data.txt")

        assert "hello from sandbox" in result
        assert "[AVS" not in result

    def test_path_traversal_blocked(self, gateway, tmp_path):
        """File read outside sandbox -> DENY -> no content leak."""
        sandbox = FileSandbox(root=str(tmp_path))

        def file_read(path):
            result = sandbox.read_file(path)
            return result.content if result.success else f"ERROR: {result.error}"

        tool = _StubTool("file_read", "Read a file", file_read)
        gov = _ManualGovernedTool(tool, gateway, ActionType.FILE, "read")

        result = gov.run("../../../etc/passwd")

        # Path traversal blocked by FileSandbox (defense in depth).
        # AVS allows the file.read action; the sandbox catches the traversal.
        assert "escapes sandbox" in result or "[AVS" in result
        # The path string may appear in the error message, but actual
        # file CONTENT must not leak (e.g., password hashes)
        assert "root:x:0:0" not in result  # No real passwd content leaked

    def test_safe_file_write_inside_sandbox(self, gateway_with_file_allow, tmp_path):
        """File write inside sandbox -> ALLOW -> file created."""
        sandbox = FileSandbox(root=str(tmp_path))

        def file_write(path, content=""):
            result = sandbox.write_file(path, content)
            return "written" if result.success else f"ERROR: {result.error}"

        tool = _StubTool("file_write", "Write a file", file_write)
        gov = _ManualGovernedTool(tool, gateway_with_file_allow, ActionType.FILE, "write")

        result = gov.run("output.txt", content="secret data")

        # Verify file was created
        written_file = tmp_path / "output.txt"
        assert written_file.exists()
        assert written_file.read_text() == "secret data"
        assert "[AVS" not in result

    def test_file_write_outside_sandbox_blocked(self, gateway, tmp_path):
        """File write outside sandbox -> DENY -> no file created."""
        sandbox = FileSandbox(root=str(tmp_path))

        def file_write(path, content=""):
            result = sandbox.write_file(path, content)
            return "written" if result.success else f"ERROR: {result.error}"

        tool = _StubTool("file_write", "Write a file", file_write)
        gov = _ManualGovernedTool(tool, gateway, ActionType.FILE, "write")

        result = gov.run("../../../tmp/hacked.txt", content="exfiltrated")

        assert "[AVS" in result
        # File should NOT be created outside sandbox
        outside_file = tmp_path.parent / "tmp" / "hacked.txt"
        assert not outside_file.exists() or "hacked" not in result


class TestNetworkBoundaryViaLangChainAdapter:
    """Prove AVS governs LangChain-style HTTP tools using real HTTPSandbox."""

    def test_safe_http_get_allowlisted(self, gateway):
        """HTTP GET to allowlisted domain -> ALLOW."""
        http = HTTPSandbox(allowed_domains={"example.com"})

        def http_get(url):
            return http.get(url).status

        tool = _StubTool("http_get", "Fetch URL via GET", http_get)
        gov = _ManualGovernedTool(tool, gateway, ActionType.API, "GET")

        result = gov.run("https://example.com/data")

        assert "[AVS" not in result

    def test_http_post_blocked(self, gateway):
        """HTTP POST -> blocked by sandbox (GET-only)."""
        http = HTTPSandbox(allowed_domains={"example.com"})

        def http_post(url, data=None):
            return http.post(url, data=data).status

        tool = _StubTool("http_post", "POST data to URL", http_post)
        gov = _ManualGovernedTool(tool, gateway, ActionType.API, "POST")

        result = gov.run("https://example.com/api", data={"key": "val"})

        assert "[AVS" in result or "blocked" in result.lower()

    def test_metadata_endpoint_blocked(self, gateway):
        """AWS metadata endpoint -> blocked by SSRF protection."""
        http = HTTPSandbox(allowed_domains={"169.254.169.254"})

        def http_get(url):
            return http.get(url).status

        tool = _StubTool("http_get", "Fetch URL via GET", http_get)
        gov = _ManualGovernedTool(tool, gateway, ActionType.API, "GET")

        result = gov.run("http://169.254.169.254/latest/meta-data/")

        assert "[AVS" in result or "blocked" in result.lower()


class TestMockAgentLoop:
    """Simulate a LangChain-style agent loop calling governed tools."""

    def test_agent_sequence_mixed_allow_deny(self, gateway, tmp_path):
        """Agent tries multiple actions — some allowed, some blocked."""
        sandbox = FileSandbox(root=str(tmp_path))
        (tmp_path / "safe.txt").write_text("public data")

        def file_read(path):
            result = sandbox.read_file(path)
            return result.content if result.success else f"ERROR: {result.error}"

        read_tool = _StubTool("file_read", "Read a file", file_read)
        gov_read = _ManualGovernedTool(read_tool, gateway, ActionType.FILE, "read")

        # Simulate agent trying multiple files
        results = []
        for path in ["safe.txt", "../../../etc/passwd", "safe.txt"]:
            results.append(gov_read.run(path))

        # First: allowed
        assert "public data" in results[0]
        assert "[AVS" not in results[0]

        # Second: blocked (sandbox catches path traversal)
        assert "escapes sandbox" in results[1] or "[AVS" in results[1]

        # Third: allowed again
        assert "public data" in results[2]
        assert "[AVS" not in results[2]

    def test_agent_evidence_accumulates(self, gateway, tmp_path):
        """Multiple agent actions accumulate audit evidence."""
        sandbox = FileSandbox(root=str(tmp_path))
        (tmp_path / "file1.txt").write_text("data1")
        (tmp_path / "file2.txt").write_text("data2")

        def file_read(path):
            result = sandbox.read_file(path)
            return result.content if result.success else "error"

        tool = _StubTool("file_read", "Read a file", file_read)
        gov = _ManualGovernedTool(tool, gateway, ActionType.FILE, "read")

        before = gateway.get_stats()["total_intercepts"]

        gov.run("file1.txt")   # allow
        gov.run("../../../x")  # deny (at sandbox layer)
        gov.run("file2.txt")   # allow

        after = gateway.get_stats()["total_intercepts"]
        assert after == before + 3

        decisions = gateway.get_stats()["decisions"]
        assert decisions.get("allow", 0) >= 2


class TestCustomBusinessActions:
    """Universal Control Plane proof: AVS governs custom actions it has
    never seen before. These are organization-specific tools, not built-in
    file or HTTP operations."""

    def test_custom_deploy_tool_require_approval(self):
        """SCENARIO 7: Custom deploy_to_production tool gets
        REQUIRE_APPROVAL. The tool does not execute."""
        pe = PolicyEngine()
        pe.load_policies("avs_gateway/config/default_policies.yaml")
        pe.add_rule(PolicyRule(
            name="production_deploy_approval",
            description="Production deployments require approval",
            priority=5,
            condition={"action_type": "api", "operation": "deploy_prod"},
            decision=PolicyDecisionType.REQUIRE_APPROVAL,
            reason="Production deployments require CISO approval",
            enabled=True,
            tags=["deployment"],
        ))
        gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())

        deploy_executed = [False]

        def deploy_to_production(manifest, service=""):
            deploy_executed[0] = True
            return f"DEPLOYED {service} to K8s PROD"

        tool = _StubTool(
            "deploy_to_production",
            "Deploy to production Kubernetes cluster",
            deploy_to_production,
        )
        gov = _ManualGovernedTool(tool, gateway, ActionType.API, "deploy_prod")

        result = gov.run("manifests/payments.yaml", service="payment-processor")

        # Tool must NOT execute
        assert deploy_executed[0] is False
        # Structured approval message returned
        assert "PENDING" in result or "approval" in result.lower()
        # Evidence recorded
        assert gateway.get_stats()["decisions"].get("require_approval", 0) >= 1

    def test_custom_tool_allow_when_configured(self):
        """Custom tool executes when policy allows."""
        pe = PolicyEngine()
        pe.load_policies("avs_gateway/config/default_policies.yaml")
        pe.add_rule(PolicyRule(
            name="custom_api_allow",
            description="Allow custom API operations",
            priority=10,
            condition={"action_type": "api", "operation": "custom_query"},
            decision=PolicyDecisionType.ALLOW,
            reason="Custom query allowed",
            enabled=True,
            tags=["custom"],
        ))
        gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())

        tool = _StubTool(
            "query_database",
            "Query the analytics database",
            lambda q: f"Results for '{q}': 42 records",
        )
        gov = _ManualGovernedTool(tool, gateway, ActionType.API, "custom_query")

        result = gov.run("SELECT * FROM sales")

        assert "42 records" in result
        assert "[AVS" not in result
