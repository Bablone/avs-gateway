"""
AVS Quickstart 01 — Gateway Basics

Shows: intercept -> decide -> record -> receipt

Run:
    python examples/quickstart/01_gateway_basics.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from avs_gateway.core.gateway_core import Gateway
from avs_gateway.models.action_request import create_action_request, ActionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain


def main():
    print("=" * 60)
    print("  AVS Quickstart 01 — Gateway Basics")
    print("  Intercept -> Decide -> Record -> Receipt")
    print("=" * 60)

    # Build a fresh Gateway with default policies
    gateway = Gateway(
        PolicyEngine(),
        RiskEngine(),
        TrustMemory(),
        ReceiptGenerator(),
        AuditChain(),
    )

    # ---- Action 1: SAFE read -> ALLOW ----
    print("\n[1] Safe file read (sandbox/report.txt)")
    a1 = create_action_request(
        agent_id="agent_1",
        action_type=ActionType.FILE,
        tool_name="file_read",
        operation="read",
        parameters={"path": "sandbox/report.txt"},
    )
    d1 = gateway.intercept(a1)
    r1 = gateway.record(a1, d1)
    print(f"    Decision : {d1.decision_type.value}")
    print(f"    Reason   : {d1.reason}")
    print(f"    Receipt  : {r1.receipt_hash}")

    # ---- Action 2: DANGEROUS delete -> DENY ----
    print("\n[2] Dangerous delete (/etc/passwd)")
    a2 = create_action_request(
        agent_id="agent_1",
        action_type=ActionType.FILE,
        tool_name="file_delete",
        operation="delete",
        parameters={"path": "/etc/passwd"},
    )
    d2 = gateway.intercept(a2)
    r2 = gateway.record(a2, d2)
    print(f"    Decision : {d2.decision_type.value}")
    print(f"    Reason   : {d2.reason}")
    print(f"    Receipt  : {r2.receipt_hash}")
    print(f"    -> Tool execution BLOCKED")

    # ---- Action 3: Production deploy -> REQUIRE_APPROVAL ----
    print("\n[3] Production deployment (payment-processor)")
    a3 = create_action_request(
        agent_id="agent_1",
        action_type=ActionType.API,
        tool_name="deploy_to_production",
        operation="deploy_prod",
        parameters={"manifest": "payment-processor.yaml"},
        context={"environment": "production"},
    )
    d3 = gateway.intercept(a3)
    r3 = gateway.record(a3, d3)
    print(f"    Decision : {d3.decision_type.value}")
    print(f"    Reason   : {d3.reason}")
    print(f"    Receipt  : {r3.receipt_hash}")
    print(f"    -> Queued for human approval")

    # ---- Evidence summary ----
    print("\n" + "=" * 60)
    print("  Evidence Summary")
    print("=" * 60)
    stats = gateway.get_stats()
    print(f"  Total intercepts : {stats['total_intercepts']}")
    for dt, count in stats["decisions"].items():
        print(f"  {dt:18s} : {count}")
    print(f"  Audit chain      : {gateway.audit_chain.length()} entries")
    print(f"  Latency          : {gateway.get_stats().get('latency', {}).get('avg_ms', 0):.3f} ms avg")
    print("\n  Every agent action gets a receipt.")
    print("  No action executes without AVS deciding first.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
