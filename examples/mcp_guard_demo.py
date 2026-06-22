"""
MCP Guard Demo — AVS v0.4.0

"One agent. Six MCP tools. AVS decides what gets admitted."

This demo runs end-to-end WITHOUT a real MCP proxy.
It simulates JSON-RPC tool calls and shows AVS admission decisions.

Run: python examples/mcp_guard_demo.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from avs_gateway.mcp import (
    MCPToolDescriptor, MCPServerManifest, MCPToolCallRequest,
    normalize_tool_call, classify_tool, guard_tool_call, approve_manifest,
    SessionContext, MCPDecision, MCPGuardMode,
    DEFAULT_MCP_GUARD_CONFIG,
)
from avs_gateway.mcp.receipts import receipt_to_mcp_dict


def demo():
    print("=" * 60)
    print("AVS MCP Guard Demo v0.4.0")
    print("One agent. Six MCP tools. AVS decides what gets admitted.")
    print("=" * 60)
    
    # Step 1: Create fake MCP server manifest
    tools = [
        MCPToolDescriptor(name="get_weather", description="Get weather for a location", input_schema={"properties": {"location": {"type": "string"}}, "required": ["location"]}),
        MCPToolDescriptor(name="read_file", description="Read a file from the workspace", input_schema={"properties": {"path": {"type": "string"}}, "required": ["path"]}),
        MCPToolDescriptor(name="write_file", description="Write content to a file", input_schema={"properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
        MCPToolDescriptor(name="delete_file", description="Delete a file permanently", input_schema={"properties": {"path": {"type": "string"}}, "required": ["path"]}),
        MCPToolDescriptor(name="fetch_url", description="Fetch content from a URL", input_schema={"properties": {"url": {"type": "string"}}, "required": ["url"]}),
        MCPToolDescriptor(name="send_email", description="Send an email", input_schema={"properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "body"]}),
    ]
    manifest = MCPServerManifest(server_id="demo_server", tools=tools)
    approved = approve_manifest(manifest)
    
    print(f"\n[1] Server manifest fingerprinted")
    print(f"    Hash: {approved.approved_hash[:32]}...")
    print(f"    Tools: {len(tools)}")
    
    # Step 2: Simulate agent tool calls
    calls = [
        ("get_weather", {"location": "New York"}, "ALLOW"),
        ("read_file", {"path": "report.txt"}, "ALLOW"),
        ("write_file", {"path": "output.txt", "content": "hello"}, "REQUIRE_APPROVAL"),
        ("delete_file", {"path": "important.txt"}, "DENY"),
        ("fetch_url", {"url": "http://169.254.169.254/latest/meta-data/"}, "DENY"),
        ("send_email", {"to": "team@company.com", "body": "Update"}, "REQUIRE_APPROVAL"),
        ("run_shell", {"command": "rm -rf /"}, "DENY"),  # Shadow tool
    ]
    
    session = SessionContext(session_id="demo_session", agent_id="demo_agent", server_id="demo_server")
    
    print(f"\n[2] Agent makes {len(calls)} tool calls:")
    print("-" * 60)
    
    results = []
    for tool_name, args, expected in calls:
        raw = {"jsonrpc": "2.0", "id": len(results), "method": "tools/call", "params": {"name": tool_name, "arguments": args}}
        req = normalize_tool_call(raw, "demo_server")
        decision, response, receipt = guard_tool_call(req, approved, session=session)
        
        # ASR-1 receipt is a dataclass — access fields directly
        action_class = receipt.decision_reason  # Use decision_reason as proxy for action class display
        reason = receipt.decision_reason
        risk = int(receipt.risk_score)

        status = "PASS" if decision.value == expected.lower() else "FAIL"
        icon = {"allow": "  OK", "deny": "  BLOCK", "require_approval": "  PENDING", "quarantine": "  ALERT"}.get(decision.value, "  ?")

        print(f"{icon} {tool_name:20s} → {decision.value:18s} (risk: {risk:2d}) [{status}]")
        print(f"     reason: {reason}")

        results.append({
            "tool": tool_name,
            "decision": decision.value,
            "expected": expected.lower(),
            "reason": reason,
            "receipt_id": receipt.receipt_id,
            "receipt_hash": receipt.receipt_hash,
        })
    
    # Step 3: Receipt verification
    print(f"\n[3] Receipt verification:")
    print("-" * 60)
    all_pass = all(r["decision"] == r["expected"] for r in results)
    print(f"    All decisions correct: {all_pass}")
    print(f"    Total receipts: {len(results)}")
    print(f"    Receipts with hashes: {sum(1 for r in results if r['receipt_hash'].startswith('sha256:'))}")

    # Step 4: Show ASR-1 receipt example
    print(f"\n[4] Sample ASR-1 receipt (delete_file denial):")
    print("-" * 60)
    deny_receipt = next(r for r in results if r["tool"] == "delete_file")
    print(f"    receipt_id: {deny_receipt['receipt_id']}")
    print(f"    decision: {deny_receipt['decision']}")
    print(f"    reason: {deny_receipt['reason']}")
    print(f"    hash: {deny_receipt['receipt_hash'][:40]}...")
    
    # Step 5: Observe mode demo
    print(f"\n[5] Observe mode (truthful reporting):")
    print("-" * 60)
    observe_config = DEFAULT_MCP_GUARD_CONFIG.copy()
    observe_config["mode"] = MCPGuardMode.OBSERVE
    raw = {"jsonrpc": "2.0", "id": 99, "method": "tools/call", "params": {"name": "delete_file", "arguments": {"path": "test.txt"}}}
    req = normalize_tool_call(raw, "demo_server")
    decision, response, receipt = guard_tool_call(req, approved, config=observe_config)
    print(f"    Would have: {decision.value}")  # The actual decision that was recorded truthfully
    print(f"    Reported as: {receipt.decision}")
    print(f"    Enforced: False")
    
    print(f"\n{'=' * 60}")
    print(f"Demo complete. {len(results)} tool calls evaluated.")
    print(f"All decisions: {'CORRECT' if all_pass else 'MISMATCHES FOUND'}")
    print(f"{'=' * 60}")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(demo())
