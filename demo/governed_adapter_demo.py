"""
AVS Gateway v0.3.1-beta -- Governed Adapter Demo.

Demonstrates the @governed_tool decorator: any Python function
becomes AVS-governed with one decorator. No framework dependency.
No tool rewrites. Just a decorator.

Usage:
    $env:PYTHONPATH = (Get-Location).Path
    python .\\demo\\governed_adapter_demo.py
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avs_gateway.models.action_request import ActionType
from avs_gateway.core.policy_engine import PolicyEngine, PolicyRule, DecisionType
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway
from avs_gateway.adapters.governed import governed_tool, set_default_gateway, is_governed

SEP = "=" * 70
SUB = "-" * 70


def banner(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(f"{SEP}")


def step(num: int, desc: str) -> None:
    print(f"\n{num}. {desc}")
    print(SUB)


def print_result(r) -> None:
    print(f"    executed     : {r.executed}")
    print(f"    decision     : {r.decision}")
    print(f"    reason       : {r.reason}")
    print(f"    risk_score   : {r.risk_score}")
    print(f"    trust_score  : {r.trust_score}")
    print(f"    tool_name    : {r.tool_name}")
    print(f"    operation    : {r.operation}")
    print(f"    latency_ms   : {r.latency_ms:.3f}")
    if r.function_result is not None:
        print(f"    func_result  : {r.function_result}")
    if r.function_error:
        print(f"    func_error   : {r.function_error}")
    if r.receipt_hash:
        print(f"    receipt_hash : {r.receipt_hash[:24]}...")


def main() -> int:
    passed = 0
    failed = 0

    # Setup: create temp sandbox dir
    tmp = tempfile.mkdtemp(prefix="avs_governed_demo_")

    # Build Gateway
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    # Add demo allow rule for file writes (priority after file_write_production at 20)
    pe.add_rule(PolicyRule(
        name="file_write_demo_allow",
        description="File writes allowed in demo",
        priority=25,
        condition={"action_type": "file", "operation": "write"},
        decision=DecisionType.ALLOW,
        reason="File writes allowed in demo environment",
        enabled=True,
        tags=["file", "write", "demo"],
    ))
    gw = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    set_default_gateway(gw)

    banner("AVS GATEWAY v0.3.1-beta -- GOVERNED ADAPTER DEMO")
    print(f"\n  Sandbox: {tmp}")
    print(f"  Policies: {len(pe.list_rules())} rules loaded")

    # ------------------------------------------------------------------
    # Define governed tools (ordinary functions + one decorator)
    # ------------------------------------------------------------------

    @governed_tool(
        tool_name="file_write",
        action_type=ActionType.FILE,
        operation="write",
    )
    def write_file(path: str, content: str) -> dict:
        """An ordinary file write function. Nothing special about it."""
        with open(path, "w") as f:
            f.write(content)
        return {"bytes_written": len(content), "path": path}

    @governed_tool(
        tool_name="file_read",
        action_type=ActionType.FILE,
        operation="read",
    )
    def read_file(path: str) -> dict:
        """An ordinary file read function."""
        with open(path, "r") as f:
            data = f.read()
        return {"content": data, "bytes_read": len(data)}

    @governed_tool(
        tool_name="file_delete",
        action_type=ActionType.FILE,
        operation="delete",
    )
    def delete_file(path: str) -> dict:
        """An ordinary delete function. Should be blocked by AVS."""
        os.remove(path)
        return {"deleted": True}

    @governed_tool(
        tool_name="api_call",
        action_type=ActionType.API,
        operation="GET",
    )
    def api_get(endpoint: str) -> dict:
        """An ordinary API call function."""
        return {"status": 200, "body": f"mock response from {endpoint}"}

    # Verify all functions are marked as governed
    step(0, "Verify functions are AVS-governed")
    for fn in [write_file, read_file, delete_file, api_get]:
        governed = is_governed(fn)
        status = "PASS" if governed else "FAIL"
        print(f"    [{status}] {fn.__name__} governed={governed}")
        if governed:
            passed += 1
        else:
            failed += 1

    # ------------------------------------------------------------------
    step(1, "ALLOW: governed file write inside sandbox")
    # ------------------------------------------------------------------
    safe_path = os.path.join(tmp, "output.txt")
    r1 = write_file(safe_path, "Hello from governed adapter!")
    print_result(r1)

    file_exists = os.path.isfile(safe_path)
    if r1.executed and r1.decision == "allow" and file_exists:
        print("    [PASS] Function executed, file created")
        passed += 1
    else:
        print("    [FAIL] Function not executed or file missing")
        failed += 1

    # ------------------------------------------------------------------
    step(2, "ALLOW: governed file read inside sandbox")
    # ------------------------------------------------------------------
    r2 = read_file(safe_path)
    print_result(r2)

    if r2.executed and r2.function_result and r2.function_result.get("content") == "Hello from governed adapter!":
        print("    [PASS] Function executed, correct content")
        passed += 1
    else:
        print("    [FAIL] Read failed or content wrong")
        failed += 1

    # ------------------------------------------------------------------
    step(3, "REQUIRE_APPROVAL: production file write needs human approval")
    # ------------------------------------------------------------------
    @governed_tool(
        tool_name="production_file_write",
        action_type=ActionType.FILE,
        operation="write",
    )
    def write_production(path: str, content: str) -> dict:
        with open(path, "w") as f:
            f.write(content)
        return {"bytes_written": len(content), "path": path}

    prod_path = os.path.join(tmp, "production.txt")
    r3 = write_production(prod_path, "sensitive production data")
    print_result(r3)

    if (not r3.executed) and r3.decision == "require_approval" and not os.path.isfile(prod_path):
        print("    [PASS] Production write queued for approval, no file created")
        passed += 1
    else:
        print("    [FAIL] Production write should require approval")
        failed += 1

    # ------------------------------------------------------------------
    step(4, "DENY: governed file delete blocked by AVS policy")
    # ------------------------------------------------------------------
    r4 = delete_file(safe_path)
    print_result(r4)

    still_exists = os.path.isfile(safe_path)
    if (not r4.executed) and still_exists:
        print("    [PASS] Delete blocked, file preserved")
        passed += 1
    else:
        print("    [FAIL] Delete not blocked or file missing")
        failed += 1

    # ------------------------------------------------------------------
    step(5, "ALLOW: governed API GET (low risk)")
    # ------------------------------------------------------------------
    r5 = api_get(endpoint="/status")
    print_result(r5)

    if r5.executed and r5.decision == "allow" and r5.function_result:
        print("    [PASS] API GET executed")
        passed += 1
    else:
        print("    [FAIL] API GET not executed")
        failed += 1

    # ------------------------------------------------------------------
    step(6, "Result structure: all governed results have receipt + decision + reason")
    # ------------------------------------------------------------------
    all_results = [r1, r2, r3, r4, r5]
    structure_ok = all(
        r.decision in ("allow", "deny", "require_approval", "quarantine")
        and r.reason
        and r.tool_name
        and r.operation
        for r in all_results
    )
    if structure_ok:
        print("    [PASS] All results have decision, reason, tool_name, operation")
        passed += 1
    else:
        print("    [FAIL] Some results missing fields")
        failed += 1

    # ------------------------------------------------------------------
    step(7, "to_dict() works for programmatic access")
    # ------------------------------------------------------------------
    try:
        d = r1.to_dict()
        assert "executed" in d
        assert "decision" in d
        assert "reason" in d
        assert "latency_ms" in d
        print("    [PASS] to_dict() returns all expected keys")
        passed += 1
    except Exception as exc:
        print(f"    [FAIL] to_dict() failed: {exc}")
        failed += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    banner("SUMMARY")
    print(f"\n    Passed : {passed}")
    print(f"    Failed : {failed}")

    if failed == 0:
        print(f"\n    [ALL CHECKS PASSED]")
        print(f"\n    Proof: @governed_tool makes any Python function")
        print(f"    AVS-governed with one decorator.")
        print(f"\n    No framework dependency.")
        print(f"    No tool rewrites.")
        print(f"    Just a decorator.")
    else:
        print(f"\n    [{failed} CHECK(S) FAILED]")

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{SEP}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
