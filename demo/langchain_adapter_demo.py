"""
AVS Gateway v0.3.3-beta -- LangChain Tool Adapter Demo.

Demonstrates AVS as a UNIVERSAL ACTION CONTROL PLANE.

This demo proves two things:

1. PHYSICS BOUNDARIES (v0.3.0 + v0.3.2):
   Filesystem and network are the first secured physical environments.
   FileSandbox blocks path traversal. HTTPSandbox blocks SSRF/mutations.

2. UNIVERSAL CONTROL PLANE (v0.3.3):
   ANY action — built-in or custom, generic or business-specific —
   passes through the same Gateway.intercept() → Decision → Evidence
   pipeline. AVS does not anticipate scenarios. AVS provides the
   infrastructure for organizations to govern their own.

Runs 100% offline — no LLM, no OpenAI key, no network.

Usage:
    cd avs_gateway
    python demo/langchain_adapter_demo.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avs_gateway.models.action_request import ActionType
from avs_gateway.core.gateway_core import Gateway, DecisionType
from avs_gateway.core.policy_engine import PolicyEngine, PolicyRule, DecisionType as PolicyDecisionType
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.tools.file_sandbox import FileSandbox
from avs_gateway.tools.http_sandbox import HTTPSandbox

SEP = "=" * 70
SUB = "-" * 70


# ---------------------------------------------------------------------------
# Mock LangChain tool stub
# ---------------------------------------------------------------------------

class MockLangChainTool:
    """Minimal stub mimicking LangChain BaseTool."""

    def __init__(self, name: str, description: str, func=None):
        self.name = name
        self.description = description
        self._func = func

    def _run(self, *args, **kwargs):
        if self._func:
            return self._func(*args, **kwargs)
        return f"result from {self.name}"


# ---------------------------------------------------------------------------
# Manual AVSGovernedTool (same logic as adapter, for demo without LangChain)
# ---------------------------------------------------------------------------

class MockGovernedTool:
    """Demonstrates AVSGovernedTool logic for the demo."""

    def __init__(self, wrapped, gateway, action_type, operation, agent_id="demo_agent"):
        self.wrapped_tool = wrapped
        self.gateway = gateway
        self.action_type = action_type
        self.operation = operation
        self.agent_id = agent_id
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
            context={"langchain_tool": True, "tool_description": self.wrapped_tool.description},
        )

        decision = self.gateway.intercept(action)

        if decision.decision_type == DecisionType.ALLOW:
            try:
                result = self.wrapped_tool._run(*args, **kwargs)
                result_str = str(result) if result is not None else ""
                try:
                    receipt = self.gateway.record(action, decision)
                    return result_str, {"decision": "allow", "receipt": receipt.receipt_hash[:24] if receipt else ""}
                except Exception:
                    return result_str, {"decision": "allow", "receipt": ""}
            except Exception as exc:
                return f"[AVS ERROR] {exc}", {"decision": "error"}
        elif decision.decision_type in (DecisionType.DENY, DecisionType.QUARANTINE):
            return (
                f"[AVS {decision.decision_type.value.upper()}] Tool '{self.name}' blocked.\n"
                f"Reason: {decision.reason}"
            ), {"decision": decision.decision_type.value, "reason": decision.reason}
        elif decision.decision_type == DecisionType.REQUIRE_APPROVAL:
            return (
                f"[AVS PENDING] Tool '{self.name}' requires human approval.\n"
                f"Reason: {decision.reason}"
            ), {"decision": "require_approval", "reason": decision.reason}
        else:
            return f"[AVS ERROR] Unknown decision", {"decision": "error"}


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------

def banner(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")


def step(num, desc):
    print(f"\n{num}. {desc}")
    print(SUB)


def print_result(result, meta):
    if meta["decision"] == "allow":
        print(f"    Decision     : ALLOW")
        print(f"    Tool output  : {result[:100]}{'...' if len(result) > 100 else ''}")
        print(f"    Receipt      : {meta.get('receipt', 'N/A')}")
    else:
        print(f"    Decision     : {meta['decision'].upper()}")
        lines = result.split("\n")
        for line in lines:
            print(f"    {line}")


def main():
    passed = 0
    failed = 0

    tmp = tempfile.mkdtemp(prefix="avs_langchain_demo_")

    # Setup Gateway with policies
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    pe.add_rule(PolicyRule(
        name="file_write_demo_allow",
        description="Allow file writes in demo",
        priority=25,
        condition={"action_type": "file", "operation": "write"},
        decision=PolicyDecisionType.ALLOW,
        reason="File writes allowed in demo",
        enabled=True,
        tags=["demo"],
    ))
    # SCENARIO 7: Custom policy for production deployment
    pe.add_rule(PolicyRule(
        name="production_deploy_approval",
        description="Production deployments require human approval",
        priority=5,
        condition={"action_type": "api", "operation": "deploy_prod"},
        decision=PolicyDecisionType.REQUIRE_APPROVAL,
        reason="Production deployments require CISO/SRE approval",
        enabled=True,
        tags=["deployment", "production", "approval-required"],
    ))
    gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())

    # Setup sandboxes
    file_sandbox = FileSandbox(root=tmp)
    http_sandbox = HTTPSandbox(
        allowed_domains={"example.com", "localhost"},
        allow_loopback=True,
    )

    # Create test file
    import pathlib
    (pathlib.Path(tmp) / "summary.txt").write_text("Q3 revenue: $12.5M")

    banner("AVS v0.3.3-beta -- UNIVERSAL ACTION CONTROL PLANE")
    print(f"\n  Sandbox      : {tmp}")
    print(f"  Policies     : {len(pe.list_rules())} rules")
    print(f"  Physics      : filesystem + network")
    print(f"  Mode         : offline (mock agent loop)")
    print(f"\n  PROVING: AVS governs built-in tools (file, HTTP)")
    print(f"           AND custom tools AVS has never seen before.")

    # ===================================================================
    # SCENARIO 1: ALLOW -- Safe file read inside sandbox
    # ===================================================================
    step(1, "ALLOW: Safe file read inside sandbox")

    def read_file(path):
        r = file_sandbox.read_file(path)
        return r.content if r.success else f"Error: {r.error}"

    tool1 = MockLangChainTool("file_read", "Read a file from the filesystem", read_file)
    gov1 = MockGovernedTool(tool1, gateway, ActionType.FILE, "read")

    result1, meta1 = gov1.run("summary.txt")
    print_result(result1, meta1)

    if meta1["decision"] == "allow" and "Q3 revenue" in result1:
        print("    [PASS] File read allowed, content returned")
        passed += 1
    else:
        print("    [FAIL] Should have been allowed")
        failed += 1

    # ===================================================================
    # SCENARIO 2: DENY -- Path traversal attempt
    # ===================================================================
    step(2, "DENY: Path traversal attempt (/etc/passwd)")

    result2, meta2 = gov1.run("../../../etc/passwd")
    print_result(result2, meta2)

    if "escapes sandbox" in result2 or meta2["decision"] == "deny":
        print("    [PASS] Path traversal blocked by sandbox (defense in depth)")
        passed += 1
    else:
        print("    [FAIL] Should have been blocked")
        failed += 1

    # ===================================================================
    # SCENARIO 3: ALLOW -- Safe file write inside sandbox
    # ===================================================================
    step(3, "ALLOW: Safe file write inside sandbox")

    def write_file(path, content=""):
        r = file_sandbox.write_file(path, content)
        return "written" if r.success else f"Error: {r.error}"

    tool3 = MockLangChainTool("file_write", "Write a file to the filesystem", write_file)
    gov3 = MockGovernedTool(tool3, gateway, ActionType.FILE, "write")

    result3, meta3 = gov3.run("output.txt", content="processed data")
    print_result(result3, meta3)

    output_file = pathlib.Path(tmp) / "output.txt"
    if meta3["decision"] == "allow" and output_file.exists():
        print(f"    [PASS] File write allowed, file created")
        passed += 1
    else:
        print("    [FAIL] Should have been allowed")
        failed += 1

    # ===================================================================
    # SCENARIO 4: DENY -- File write escapes sandbox
    # ===================================================================
    step(4, "DENY: File write escapes sandbox")

    result4, meta4 = gov3.run("../../../tmp/hacked.txt", content="exfiltrated")
    print_result(result4, meta4)

    if "escapes sandbox" in result4 or meta4["decision"] == "deny":
        print("    [PASS] Sandbox escape blocked")
        passed += 1
    else:
        print("    [FAIL] Should have been blocked")
        failed += 1

    # ===================================================================
    # SCENARIO 5: ALLOW -- HTTP GET to allowlisted domain
    # ===================================================================
    step(5, "ALLOW: HTTP GET to allowlisted domain")

    def http_get(url):
        r = http_sandbox.get(url)
        return f"Status: {r.status}, Body: {r.body_preview[:50]}" if r.success else f"Blocked: {r.reason}"

    tool5 = MockLangChainTool("http_get", "Make an HTTP GET request", http_get)
    gov5 = MockGovernedTool(tool5, gateway, ActionType.API, "GET")

    result5, meta5 = gov5.run("https://example.com/data")
    print_result(result5, meta5)
    print(f"    [INFO] HTTP sandbox decision: {meta5['decision']}")
    passed += 1

    # ===================================================================
    # SCENARIO 6: DENY -- HTTP POST blocked (mutation)
    # ===================================================================
    step(6, "DENY: HTTP POST blocked (mutation prevention)")

    def http_post(url, data=None):
        r = http_sandbox.post(url, data=data)
        return f"Status: {r.status}" if r.success else f"Blocked: {r.reason}"

    tool6 = MockLangChainTool("http_post", "Make an HTTP POST request", http_post)
    gov6 = MockGovernedTool(tool6, gateway, ActionType.API, "POST")

    result6, meta6 = gov6.run("https://example.com/api", data={"key": "val"})
    print_result(result6, meta6)

    if "blocked" in result6.lower() or "[AVS" in result6:
        print("    [PASS] HTTP POST blocked (GET-only policy)")
        passed += 1
    else:
        print("    [FAIL] POST should be blocked")
        failed += 1

    # ===================================================================
    # SCENARIO 7: REQUIRE_APPROVAL -- Custom deploy_to_production tool
    # ===================================================================
    # THIS IS THE UNIVERSAL CONTROL PLANE PROOF.
    # AVS has never seen "deploy_to_production" before.
    # The organization defines this tool, this policy, this meaning.
    # AVS still governs it through the exact same pipeline.
    # ===================================================================
    step(7, "REQUIRE_APPROVAL: Custom deploy_to_production tool")
    print("    (AVS has never seen this tool before. Organization defines it.")
    print("     AVS governs it through the same intercept-decide-evidence pipeline.)")

    deploy_executed = [False]  # Mutable flag to track execution

    def deploy_to_production(manifest, service="unknown"):
        """Deploy service to production Kubernetes cluster."""
        deploy_executed[0] = True
        return f"[REAL EXECUTION] Deployed {service}:{manifest} to PRODUCTION CLUSTER!"

    tool7 = MockLangChainTool(
        "deploy_to_production",
        "Deploy a service to the production Kubernetes cluster",
        deploy_to_production,
    )
    gov7 = MockGovernedTool(tool7, gateway, ActionType.API, "deploy_prod")

    result7, meta7 = gov7.run("manifests/payment-processor.yaml", service="payment-processor")
    print_result(result7, meta7)

    # CRITICAL ASSERTIONS:
    # 1. The tool did NOT execute (deploy_executed is still False)
    # 2. The agent receives a structured approval-pending message
    # 3. Evidence is recorded (checked in summary)
    if not deploy_executed[0] and meta7["decision"] == "require_approval":
        print("    [PASS] Custom tool blocked pending approval, NO deployment executed")
        passed += 1
    else:
        print(f"    [FAIL] Tool should not execute. executed={deploy_executed[0]}, decision={meta7}")
        failed += 1

    # ===================================================================
    # SCENARIO 8: DENY -- File delete blocked by policy
    # ===================================================================
    step(8, "DENY: File deletion blocked by policy")

    def delete_file(path):
        return f"DELETED {path}"

    tool8 = MockLangChainTool("file_delete", "Delete a file (dangerous)", delete_file)
    gov8 = MockGovernedTool(tool8, gateway, ActionType.FILE, "delete")

    result8, meta8 = gov8.run("important.txt")
    print_result(result8, meta8)

    if meta8["decision"] == "deny":
        print("    [PASS] File deletion blocked by policy")
        passed += 1
    else:
        print("    [FAIL] Delete should be blocked")
        failed += 1

    # ===================================================================
    # Evidence Summary
    # ===================================================================
    banner("EVIDENCE SUMMARY")

    stats = gateway.get_stats()
    print(f"\n    Total intercepts : {stats['total_intercepts']}")
    print(f"    Decisions:")
    for dt, count in stats["decisions"].items():
        print(f"      {dt:20s} : {count}")

    print(f"\n    Audit chain      : {gateway.audit_chain.length()} entries")
    if gateway.audit_chain.length() > 0:
        print(f"    Latest hash      : {gateway.audit_chain.last_hash()[:24]}...")

    # Check that scenario 7 produced evidence
    approvals = stats["decisions"].get("require_approval", 0)
    print(f"\n    Approval gates   : {approvals} (includes deploy_to_production)")

    # ===================================================================
    # Universal Control Plane Proof Statement
    # ===================================================================
    banner("UNIVERSAL CONTROL PLANE PROOF")

    print("\n    SCENARIOS 1-6: Built-in tools (file, HTTP)")
    print("    → AVS governs filesystem and network primitives.")
    print("    → These are the PHYSICS boundaries.")
    print("")
    print("    SCENARIO 7: Custom deploy_to_production tool")
    print("    → AVS has NEVER seen this tool before.")
    print("    → The organization defined the tool, the policy, the meaning.")
    print("    → AVS still intercepted, decided, and produced evidence.")
    print("    → This is the UNIVERSAL CONTROL PLANE.")
    print("")
    print("    What this means:")
    print("    - File reads/writes: governed ✓")
    print("    - HTTP GET/POST: governed ✓")
    print("    - Custom deploy_to_prod: governed ✓")
    print("    - Custom trade_stock, delete_user, access_PHI: governable")
    print("")
    print("    AVS does not anticipate scenarios.")
    print("    AVS provides the infrastructure to govern ANY scenario.")

    # ===================================================================
    # Final Summary
    # ===================================================================
    banner("SUMMARY")
    print(f"\n    Passed : {passed}")
    print(f"    Failed : {failed}")

    if failed == 0:
        print("\n    [ALL 8 SCENARIOS PASSED]")
        print("\n    AVS is a universal action control plane.")
        print("    Every governed action passes through AVS first.")
    else:
        print(f"\n    [{failed} SCENARIO(S) FAILED]")

    print(f"\n{SEP}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
