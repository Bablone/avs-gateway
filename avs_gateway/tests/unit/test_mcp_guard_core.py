"""
test_mcp_guard_core.py -- AVS MCP Guard v0.4.0 (ASR-1 Integrated)

Tests for the core MCP Guard modules:
- models (normalization)
- manifest (hashing, drift detection)
- classifier (deterministic classification)
- policy (decision evaluation)
- sanitizer (schema + semantic validation)
- session (data-flow tags)
- guard (end-to-end orchestration)
- receipts (ASR-1 integration -- real signed receipts)
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from avs_gateway.mcp import (
    MCPToolDescriptor, MCPServerManifest, MCPToolCallRequest,
    normalize_tools_list, normalize_tool_call,
    classify_tool,
    evaluate_mcp_policy,
    guard_tool_call, approve_manifest,
    SessionContext,
    MCPActionClass, MCPDecision, MCPReasonCode, MCPGuardMode,
    DEFAULT_MCP_GUARD_CONFIG,
)
from avs_gateway.receipts.asr1 import ASR1Receipt, verify_receipt
from avs_gateway.mcp.receipts import receipt_to_mcp_dict, _MCPReceiptGenerator


# -- Fixtures --

@pytest.fixture
def sample_manifest():
    tools = [
        MCPToolDescriptor(name="get_weather", description="Get weather for a location", input_schema={"properties": {"location": {"type": "string"}}, "required": ["location"]}),
        MCPToolDescriptor(name="read_file", description="Read a file from the workspace", input_schema={"properties": {"path": {"type": "string"}}, "required": ["path"]}),
        MCPToolDescriptor(name="write_file", description="Write content to a file", input_schema={"properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
        MCPToolDescriptor(name="delete_file", description="Delete a file permanently", input_schema={"properties": {"path": {"type": "string"}}, "required": ["path"]}),
        MCPToolDescriptor(name="fetch_url", description="Fetch content from a URL", input_schema={"properties": {"url": {"type": "string"}}, "required": ["url"]}),
        MCPToolDescriptor(name="send_email", description="Send an email", input_schema={"properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "body"]}),
    ]
    return MCPServerManifest(server_id="test_server", tools=tools)


@pytest.fixture
def approved_manifest(sample_manifest):
    return approve_manifest(sample_manifest)


@pytest.fixture
def default_config():
    return DEFAULT_MCP_GUARD_CONFIG.copy()


# -- Model Tests --

class TestModels:
    def test_tool_descriptor_hash_is_stable(self, sample_manifest):
        tool = sample_manifest.tools[0]
        h1 = tool.descriptor_hash()
        h2 = tool.descriptor_hash()
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_descriptor_hash_changes_with_description(self, sample_manifest):
        tool1 = MCPToolDescriptor(name="test", description="Desc A", input_schema={})
        tool2 = MCPToolDescriptor(name="test", description="Desc B", input_schema={})
        assert tool1.descriptor_hash() != tool2.descriptor_hash()

    def test_manifest_hash_is_stable(self, sample_manifest):
        h1 = sample_manifest.manifest_hash()
        h2 = sample_manifest.manifest_hash()
        assert h1 == h2

    def test_manifest_hash_order_independent(self, sample_manifest):
        from avs_gateway.mcp.models import MCPServerManifest, MCPToolDescriptor
        tools_reordered = [
            MCPToolDescriptor(name="delete_file", description="Delete a file permanently", input_schema={}),
            MCPToolDescriptor(name="get_weather", description="Get weather for a location", input_schema={}),
            MCPToolDescriptor(name="read_file", description="Read a file from the workspace", input_schema={}),
        ]
        m1 = MCPServerManifest(server_id="test_server", tools=tools_reordered)
        m2 = MCPServerManifest(server_id="test_server", tools=list(reversed(tools_reordered)))
        assert m1.manifest_hash() == m2.manifest_hash()

    def test_normalize_tool_call(self):
        raw = {"jsonrpc": "2.0", "id": 42, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"location": "NYC"}}}
        req = normalize_tool_call(raw, "test_server")
        assert req.tool_name == "get_weather"
        assert req.arguments == {"location": "NYC"}
        assert req.arguments_hash.startswith("sha256:")
        assert req.jsonrpc_id == 42


# -- Manifest Tests --

class TestManifest:
    def test_drift_detect_no_change(self, approved_manifest, sample_manifest):
        from avs_gateway.mcp.manifest import detect_manifest_drift
        report = detect_manifest_drift(approved_manifest, sample_manifest)
        assert not report.drift_detected

    def test_drift_detect_added_tool(self, approved_manifest, sample_manifest):
        from avs_gateway.mcp.manifest import detect_manifest_drift
        new_tools = list(sample_manifest.tools) + [MCPToolDescriptor(name="run_shell", description="Run a shell command", input_schema={})]
        current = MCPServerManifest(server_id="test_server", tools=new_tools)
        report = detect_manifest_drift(approved_manifest, current)
        assert report.drift_detected
        assert "run_shell" in report.added_tools

    def test_drift_detect_description_change(self, approved_manifest, sample_manifest):
        from avs_gateway.mcp.manifest import detect_manifest_drift
        import copy
        current = copy.deepcopy(sample_manifest)
        current.tools[0] = MCPToolDescriptor(name="get_weather", description="HACKED", input_schema=current.tools[0].input_schema)
        report = detect_manifest_drift(approved_manifest, current)
        assert report.drift_detected
        assert "get_weather" in report.changed_tools

    def test_call_time_manifest_tool_exists(self, approved_manifest):
        from avs_gateway.mcp.manifest import check_call_time_manifest
        tool = approved_manifest.manifest.tools[0]
        passed, decision, reason = check_call_time_manifest("get_weather", tool.descriptor_hash(), {}, approved_manifest)
        assert passed

    def test_call_time_manifest_unknown_tool(self, approved_manifest):
        from avs_gateway.mcp.manifest import check_call_time_manifest
        passed, decision, reason = check_call_time_manifest("evil_tool", "sha256:fake", {}, approved_manifest)
        assert not passed
        assert decision == MCPDecision.DENY
        assert reason == MCPReasonCode.MCP_UNKNOWN_TOOL


# -- Classifier Tests --

class TestClassifier:
    def test_classify_read_only(self):
        tool = MCPToolDescriptor(name="get_weather", description="Get weather", input_schema={})
        assert classify_tool(tool) == MCPActionClass.READ_ONLY

    def test_classify_filesystem_read(self):
        tool = MCPToolDescriptor(name="read_file", description="Read a file", input_schema={})
        assert classify_tool(tool) == MCPActionClass.FILESYSTEM_READ

    def test_classify_filesystem_write(self):
        tool = MCPToolDescriptor(name="write_file", description="Write to a file", input_schema={})
        assert classify_tool(tool) == MCPActionClass.FILESYSTEM_WRITE

    def test_classify_destructive(self):
        tool = MCPToolDescriptor(name="delete_file", description="Delete a file", input_schema={})
        assert classify_tool(tool) == MCPActionClass.DESTRUCTIVE

    def test_classify_code_execution(self):
        tool = MCPToolDescriptor(name="run_shell", description="Execute shell commands", input_schema={})
        assert classify_tool(tool) == MCPActionClass.CODE_EXECUTION

    def test_classify_network(self):
        tool = MCPToolDescriptor(name="fetch_url", description="Fetch a URL", input_schema={})
        assert classify_tool(tool) == MCPActionClass.NETWORK

    def test_classify_message_send(self):
        tool = MCPToolDescriptor(name="send_email", description="Send email", input_schema={})
        assert classify_tool(tool) == MCPActionClass.MESSAGE_SEND

    def test_classify_credential_access(self):
        tool = MCPToolDescriptor(name="read_credentials", description="Read stored credentials", input_schema={})
        assert classify_tool(tool) == MCPActionClass.CREDENTIAL_ACCESS

    def test_classify_payment(self):
        tool = MCPToolDescriptor(name="pay_invoice", description="Process payment", input_schema={})
        assert classify_tool(tool) == MCPActionClass.PAYMENT_TRIGGER

    def test_classify_override(self):
        tool = MCPToolDescriptor(name="get_weather", description="Get weather", input_schema={})
        result = classify_tool(tool, overrides={"get_weather": "destructive"})
        assert result == MCPActionClass.DESTRUCTIVE

    def test_classify_financial_mutation(self):
        tool = MCPToolDescriptor(name="transfer_funds", description="Transfer funds between accounts", input_schema={})
        assert classify_tool(tool) == MCPActionClass.FINANCIAL_MUTATION

    def test_classify_infrastructure_mutation(self):
        tool = MCPToolDescriptor(name="update_firewall", description="Update firewall rules", input_schema={})
        assert classify_tool(tool) == MCPActionClass.INFRASTRUCTURE_MUTATION

    def test_classify_code_mutation(self):
        tool = MCPToolDescriptor(name="merge_pull_request", description="Merge a pull request", input_schema={})
        assert classify_tool(tool) == MCPActionClass.CODE_MUTATION

    def test_classify_repository_write(self):
        tool = MCPToolDescriptor(name="npm_publish", description="Publish package to npm registry", input_schema={})
        assert classify_tool(tool) == MCPActionClass.REPOSITORY_WRITE


# -- Policy Tests --

class TestPolicy:
    def test_allow_read_only(self, sample_manifest):
        tool = sample_manifest.tools[0]  # get_weather
        req = MCPToolCallRequest(jsonrpc_id=1, server_id="test", tool_name="get_weather", arguments={"location": "NYC"})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.READ_ONLY, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.ALLOW

    def test_write_requires_approval(self, sample_manifest):
        tool = sample_manifest.tools[2]  # write_file
        req = MCPToolCallRequest(jsonrpc_id=1, server_id="test", tool_name="write_file", arguments={"path": "test.txt", "content": "hello"})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.FILESYSTEM_WRITE, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.REQUIRE_APPROVAL

    def test_delete_denied(self, sample_manifest):
        tool = sample_manifest.tools[3]  # delete_file
        req = MCPToolCallRequest(jsonrpc_id=1, server_id="test", tool_name="delete_file", arguments={"path": "test.txt"})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.DESTRUCTIVE, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.DENY


# -- Sanitizer Tests --

class TestSanitizer:
    def test_path_traversal_detected(self):
        from avs_gateway.mcp.sanitizer import validate_semantics
        valid, reason = validate_semantics({"path": "../../../etc/passwd"}, MCPActionClass.FILESYSTEM_READ, {})
        assert not valid
        assert reason == MCPReasonCode.MCP_PATH_TRAVERSAL

    def test_private_ip_blocked(self):
        from avs_gateway.mcp.sanitizer import validate_semantics
        valid, reason = validate_semantics({"url": "http://169.254.169.254/latest/meta-data/"}, MCPActionClass.NETWORK, {})
        assert not valid

    def test_schema_validation(self):
        from avs_gateway.mcp.sanitizer import validate_schema
        schema = {"properties": {"location": {"type": "string"}}, "required": ["location"]}
        valid, error = validate_schema({"location": "NYC"}, schema)
        assert valid
        valid, error = validate_schema({}, schema)
        assert not valid
        assert "Missing required field" in error


# -- Session Tests --

class TestSession:
    def test_session_tag_adds_and_checks(self):
        sess = SessionContext(session_id="s1", agent_id="a1", server_id="srv1")
        sess.add_tag("test_tag", "receipt_1", severity="high")
        assert sess.has_sensitive_tags()
        assert sess.has_tag("test_tag")

    def test_session_tag_expires(self):
        sess = SessionContext(session_id="s1", agent_id="a1", server_id="srv1")
        sess.add_tag("test_tag", "receipt_1", severity="high", ttl=0)  # Expires immediately
        import time
        time.sleep(0.1)
        assert not sess.has_tag("test_tag")

    def test_sensitive_read_triggers_tag(self):
        sess = SessionContext(session_id="s1", agent_id="a1", server_id="srv1")
        added = sess.tag_from_tool_call("read_file", {"path": "/workspace/.env"}, "receipt_1")
        assert added
        assert sess.has_sensitive_tags()


# -- Guard End-to-End Tests --

class TestGuardEndToEnd:
    def test_allow_weather(self, approved_manifest):
        req = MCPToolCallRequest(jsonrpc_id=1, server_id="test_server", tool_name="get_weather", arguments={"location": "NYC"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        assert decision == MCPDecision.ALLOW
        # receipt is a real ASR1Receipt -- check fields directly
        assert receipt.decision == "allow"
        assert receipt.tool_name == "get_weather"
        assert receipt.agent_id == "agent_default"

    def test_deny_delete(self, approved_manifest):
        req = MCPToolCallRequest(jsonrpc_id=2, server_id="test_server", tool_name="delete_file", arguments={"path": "test.txt"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        assert decision == MCPDecision.DENY
        assert receipt.decision == "deny"
        assert receipt.decision_reason == MCPReasonCode.MCP_DESTRUCTIVE_ACTION_DENIED.value

    def test_require_approval_write(self, approved_manifest):
        req = MCPToolCallRequest(jsonrpc_id=3, server_id="test_server", tool_name="write_file", arguments={"path": "test.txt", "content": "hello"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        assert decision == MCPDecision.REQUIRE_APPROVAL
        assert response["isError"] == True

    def test_deny_unknown_tool(self, approved_manifest):
        req = MCPToolCallRequest(jsonrpc_id=4, server_id="test_server", tool_name="evil_tool", arguments={})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        assert decision == MCPDecision.DENY
        assert receipt.decision == "deny"
        assert receipt.decision_reason == MCPReasonCode.MCP_UNKNOWN_TOOL.value

    def test_observe_mode_truthfulness(self, approved_manifest):
        config = DEFAULT_MCP_GUARD_CONFIG.copy()
        config["mode"] = MCPGuardMode.OBSERVE
        req = MCPToolCallRequest(jsonrpc_id=5, server_id="test_server", tool_name="delete_file", arguments={"path": "test.txt"})
        decision, response, receipt = guard_tool_call(req, approved_manifest, config=config)
        # In observe mode, the effective decision is would_deny
        assert receipt.decision == "would_deny"

    def test_receipt_is_real_asr1_with_signature(self, approved_manifest):
        """The receipt must be a real ASR-1 receipt with a valid hash and signature."""
        req = MCPToolCallRequest(jsonrpc_id=6, server_id="test_server", tool_name="get_weather", arguments={"location": "NYC"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        # Must be ASR1Receipt instance
        assert isinstance(receipt, ASR1Receipt)
        # Must have receipt_hash
        assert receipt.receipt_hash.startswith("sha256:")
        # Must have gateway_signature (signed by Ed25519 or mock)
        assert receipt.gateway_signature is not None
        assert receipt.gateway_signature.startswith("ed25519:") or receipt.gateway_signature.startswith("mock:")
        # Must pass ASR-1 verification
        assert verify_receipt(receipt) == True

    def test_receipt_can_be_serialized_and_verified(self, approved_manifest):
        """Receipt must round-trip through JSON and still verify."""
        req = MCPToolCallRequest(jsonrpc_id=7, server_id="test_server", tool_name="get_weather", arguments={"location": "NYC"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        # Serialize to JSON
        json_str = receipt.to_json()
        # Reconstruct
        receipt2 = ASR1Receipt.from_json(json_str)
        # Must still verify
        assert verify_receipt(receipt2) == True
        # Key fields preserved
        assert receipt2.receipt_id == receipt.receipt_id
        assert receipt2.decision == receipt.decision

    def test_receipt_cli_verify(self, approved_manifest):
        """Receipt must be verifiable via `avs receipt verify` CLI."""
        req = MCPToolCallRequest(jsonrpc_id=8, server_id="test_server", tool_name="get_weather", arguments={"location": "NYC"})
        decision, response, receipt = guard_tool_call(req, approved_manifest)
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(receipt.to_json(indent=2))
            temp_path = f.name
        try:
            # Run CLI verify
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "avs_gateway.cli", "receipt", "verify", temp_path],
                capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[3])
            )
            # CLI should report valid (exit code 0 and "valid" in output)
            assert result.returncode == 0, f"CLI failed: {result.stdout}\n{result.stderr}"
            assert "valid" in result.stdout.lower(), f"Expected 'valid' in output: {result.stdout}"
        finally:
            os.unlink(temp_path)

    def test_session_exfiltration_upgrade(self, approved_manifest):
        session = SessionContext(session_id="s1", agent_id="a1", server_id="test_server")
        # First: read sensitive file
        req1 = MCPToolCallRequest(jsonrpc_id=7, server_id="test_server", tool_name="read_file", arguments={"path": "/workspace/.env"})
        guard_tool_call(req1, approved_manifest, session=session)
        # Then: send email (should be upgraded to require_approval)
        req2 = MCPToolCallRequest(jsonrpc_id=8, server_id="test_server", tool_name="send_email", arguments={"to": "a@b.com", "body": "test"})
        decision, response, receipt = guard_tool_call(req2, approved_manifest, session=session)
        # The session tag should cause the email to require approval
        assert session.has_sensitive_tags()

    def test_financial_mutation_requires_approval(self, sample_manifest):
        """Financial mutation (transfer) requires approval."""
        tool = MCPToolDescriptor(name="transfer_funds", description="Transfer funds", input_schema={"properties": {"amount": {"type": "number"}}, "required": ["amount"]})
        req = MCPToolCallRequest(jsonrpc_id=20, server_id="test", tool_name="transfer_funds", arguments={"amount": 1000})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.FINANCIAL_MUTATION, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.REQUIRE_APPROVAL
        assert reason == MCPReasonCode.MCP_FINANCIAL_MUTATION_REQUIRES_APPROVAL

    def test_infrastructure_mutation_requires_approval(self, sample_manifest):
        """Infrastructure mutation (firewall) requires approval."""
        tool = MCPToolDescriptor(name="update_firewall", description="Update firewall rules", input_schema={"properties": {"rule": {"type": "string"}}, "required": ["rule"]})
        req = MCPToolCallRequest(jsonrpc_id=21, server_id="test", tool_name="update_firewall", arguments={"rule": "allow all"})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.INFRASTRUCTURE_MUTATION, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.REQUIRE_APPROVAL
        assert reason == MCPReasonCode.MCP_INFRASTRUCTURE_MUTATION_REQUIRES_APPROVAL

    def test_code_mutation_requires_approval(self, sample_manifest):
        """Code mutation (merge PR) requires approval."""
        tool = MCPToolDescriptor(name="merge_pr", description="Merge pull request", input_schema={"properties": {"pr_number": {"type": "integer"}}, "required": ["pr_number"]})
        req = MCPToolCallRequest(jsonrpc_id=22, server_id="test", tool_name="merge_pr", arguments={"pr_number": 42})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.CODE_MUTATION, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.REQUIRE_APPROVAL
        assert reason == MCPReasonCode.MCP_CODE_MUTATION_REQUIRES_APPROVAL

    def test_repository_write_requires_approval(self, sample_manifest):
        """Repository write (publish package) requires approval."""
        tool = MCPToolDescriptor(name="publish_package", description="Publish package to registry", input_schema={"properties": {"version": {"type": "string"}}, "required": ["version"]})
        req = MCPToolCallRequest(jsonrpc_id=23, server_id="test", tool_name="publish_package", arguments={"version": "1.0.0"})
        decision, reason, risk = evaluate_mcp_policy(req, MCPActionClass.REPOSITORY_WRITE, tool, DEFAULT_MCP_GUARD_CONFIG)
        assert decision == MCPDecision.REQUIRE_APPROVAL
        assert reason == MCPReasonCode.MCP_REPOSITORY_WRITE_REQUIRES_APPROVAL

    def test_mutation_classes_escalate_on_sensitive_session(self, approved_manifest):
        """Financial mutation escalates when sensitive session tags exist."""
        session = SessionContext(session_id="s2", agent_id="a2", server_id="test_server")
        # Tag session with sensitive read
        session.add_tag("credential_file_accessed", "receipt_10", severity="critical")
        # Financial mutation should escalate to require_approval
        tools = list(approved_manifest.manifest.tools)
        tools.append(MCPToolDescriptor(name="transfer_funds", description="Transfer funds", input_schema={"properties": {"amount": {"type": "number"}}}))
        from avs_gateway.mcp.models import MCPServerManifest
        manifest = MCPServerManifest(server_id="test_server", tools=tools)
        from avs_gateway.mcp.guard import approve_manifest
        approved = approve_manifest(manifest)
        req = MCPToolCallRequest(jsonrpc_id=24, server_id="test_server", tool_name="transfer_funds", arguments={"amount": 500})
        decision, response, receipt = guard_tool_call(req, approved, session=session)
        assert decision == MCPDecision.REQUIRE_APPROVAL
