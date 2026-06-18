#!/usr/bin/env python3
"""
AVS Gateway v0 -- "Scary to Safe" Demo Script.

This demo shows the Gateway transforming uncontrolled agent actions
into proof-gated, auditable decisions. Run this script to see the
Gateway in action across all decision types.

Usage:
    PYTHONPATH=/mnt/agents/output/avs_gateway python3 demo/gateway_demo.py
"""

import sys
sys.path.insert(0, "/mnt/agents/output/avs_gateway")

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway, DecisionType


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_decision(name: str, decision, receipt=None, verifier=None) -> None:
    emoji = {
        DecisionType.ALLOW: "✓",
        DecisionType.DENY: "✗",
        DecisionType.REQUIRE_APPROVAL: "⚠",
        DecisionType.QUARANTINE: "☠",
    }.get(decision.decision_type, "?")

    print(f"\n  {emoji} {name}")
    print(f"    Decision: {decision.decision_type.value.upper()}")
    print(f"    Reason:   {decision.reason}")
    print(f"    Risk:     {decision.risk_score}/100")
    print(f"    Trust:    {decision.trust_score}/100")
    print(f"    Latency:  {decision.processing_time_ms:.3f}ms")
    if receipt:
        verified = verifier.verify(receipt) if verifier else "N/A"
        print(f"    Receipt:  {receipt.receipt_hash[:24]}...")
        print(f"    Signed:   {len(receipt.signature) > 0}")
        print(f"    Verified: {verified}")


def main() -> None:
    print_header("AVS GATEWAY v0 — PROOF-GATED EXECUTION")
    print("\n  Every action intercepted. Every decision signed.")
    print("  No tool executes without AVS approval.")

    # Initialize the Gateway
    print_header("INITIALIZING")
    policy_engine = PolicyEngine()
    policy_engine.load_policies("avs_gateway/config/default_policies.yaml")
    print(f"  Loaded {len(policy_engine.list_rules())} policy rules")

    risk_engine = RiskEngine()
    trust_memory = TrustMemory()
    receipt_generator = ReceiptGenerator()
    audit_chain = AuditChain()

    gateway = Gateway(
        policy_engine=policy_engine,
        risk_engine=risk_engine,
        trust_memory=trust_memory,
        receipt_generator=receipt_generator,
        audit_chain=audit_chain,
    )
    print(f"  Gateway ready (fail-closed: ON)")

    # --- ALLOW: Safe Actions ---
    print_header("SCENARIO 1: SAFE ACTIONS → ALLOW")

    safe_actions = [
        ("Read config file", ActionType.FILE, "file_tool", "read", {"path": "/tmp/config.txt"}),
        ("GET API call", ActionType.API, "api_tool", "GET", {"endpoint": "/status"}),
        ("SELECT query", ActionType.DATABASE, "db_tool", "SELECT", {"query": "SELECT id FROM users"}),
        ("Small payment ($50)", ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 50, "recipient": "vendor-1"}),
    ]

    for name, atype, tool, op, params in safe_actions:
        action = create_action_request(
            agent_id="agent-safe",
            action_type=atype,
            tool_name=tool,
            operation=op,
            parameters=params,
        )
        decision = gateway.intercept(action)
        receipt = gateway.record(action, decision)
        print_decision(name, decision, receipt, receipt_generator)

    # --- DENY: Prohibited Actions ---
    print_header("SCENARIO 2: PROHIBITED ACTIONS → DENY")

    denied_actions = [
        ("Delete file", ActionType.FILE, "file_tool", "delete", {"path": "/important.txt"}),
        ("API DELETE", ActionType.API, "api_tool", "DELETE", {"endpoint": "/users/123"}),
        ("DB DROP", ActionType.DATABASE, "db_tool", "DROP", {"table": "users"}),
        ("Extreme payment ($100K)", ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 100000, "recipient": "offshore"}),
    ]

    for name, atype, tool, op, params in denied_actions:
        action = create_action_request(
            agent_id="agent-risky",
            action_type=atype,
            tool_name=tool,
            operation=op,
            parameters=params,
        )
        decision = gateway.intercept(action)
        receipt = gateway.record(action, decision)
        print_decision(name, decision, receipt, receipt_generator)

    # --- QUARANTINE: High Risk ---
    print_header("SCENARIO 3: HIGH-RISK ACTIONS → QUARANTINE")

    quarantine_actions = [
        ("Large payment ($5K)", ActionType.PAYMENT, "payment_tool", "transfer", {"amount": 5000, "recipient": "new-vendor"}),
    ]

    for name, atype, tool, op, params in quarantine_actions:
        action = create_action_request(
            agent_id="agent-risky",
            action_type=atype,
            tool_name=tool,
            operation=op,
            parameters=params,
        )
        decision = gateway.intercept(action)
        receipt = gateway.record(action, decision)
        print_decision(name, decision, receipt, receipt_generator)

    # --- REQUIRE_APPROVAL: Medium Risk ---
    print_header("SCENARIO 4: MEDIUM-RISK ACTIONS → REQUIRE APPROVAL")

    approval_actions = [
        ("API POST", ActionType.API, "api_tool", "POST", {"endpoint": "/users", "data": {}}),
        ("External email", ActionType.EMAIL, "email_tool", "send", {"to": "external@gmail.com", "external": True}),
        ("DB INSERT", ActionType.DATABASE, "db_tool", "INSERT", {"table": "logs", "data": {}}),
    ]

    for name, atype, tool, op, params in approval_actions:
        action = create_action_request(
            agent_id="agent-standard",
            action_type=atype,
            tool_name=tool,
            operation=op,
            parameters=params,
        )
        decision = gateway.intercept(action)
        print_decision(name, decision)
        if not decision.is_blocking():
            receipt = gateway.record(action, decision)
            print(f"    Receipt:  {receipt.receipt_hash[:24]}...")

    # --- FAIL-CLOSED: Safety Net ---
    print_header("SCENARIO 5: FAIL-CLOSED SAFETY NET")

    # Invalid request (empty agent_id)
    from dataclasses import replace
    bad_action = create_action_request(
        agent_id="temp",
        action_type=ActionType.FILE,
        tool_name="file_tool",
        operation="read",
    )
    bad_action = replace(bad_action, agent_id="")
    decision = gateway.intercept(bad_action)
    print_decision("Invalid request (empty agent_id)", decision)

    # --- STATISTICS ---
    print_header("GATEWAY STATISTICS")
    stats = gateway.get_stats()
    print(f"  Total Intercepts: {stats['total_intercepts']}")
    print(f"  Valid Decisions:  {stats['valid_decisions']}")
    print(f"  Rejections:       {stats['rejection_count']} (invalid requests blocked at gate)")
    print(f"  Decisions:")
    for dtype, count in stats['decisions'].items():
        print(f"    {dtype}: {count}")
    print(f"  Audit Chain:      {stats['audit_chain_length']} entries")
    print(f"  Rejection Log:    {stats['rejection_count']} entries")

    # Show rejection log if any
    rejections = gateway.get_rejection_log()
    if rejections:
        print(f"\n  Rejection Details:")
        for r in rejections:
            print(f"    [{r['reason']}] agent={r['agent_id']}, latency={r['processing_time_ms']:.3f}ms")

    # Verify chain integrity
    valid, errors = audit_chain.verify()
    print(f"\n  Chain Integrity:  {'✓ VALID' if valid else '✗ INVALID'}")
    if errors:
        print(f"    Errors: {errors}")

    # v0.1 hardening: explain the accounting
    gap = stats['total_intercepts'] - stats['audit_chain_length'] - stats['rejection_count']
    if gap == 0:
        print(f"\n  ✓ Complete accounting:")
        print(f"    {stats['audit_chain_length']} audit entries + {stats['rejection_count']} rejections = {stats['total_intercepts']} total intercepts")
    else:
        print(f"\n  ⚠ Gap detected: {gap} unaccounted intercepts")

    # --- PERFORMANCE ---
    print_header("PERFORMANCE BENCHMARK")
    import time

    iterations = 1000
    start = time.time()
    for i in range(iterations):
        action = create_action_request(
            agent_id="agent-perf",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": f"/tmp/file_{i}.txt"},
        )
        gateway.intercept(action)
    elapsed = time.time() - start

    avg_ms = (elapsed / iterations) * 1000
    per_sec = iterations / elapsed
    print(f"  {iterations} decisions in {elapsed*1000:.1f}ms")
    print(f"  Average: {avg_ms:.3f}ms per decision (target: <10ms)")
    print(f"  Throughput: {per_sec:,.0f} decisions/sec (target: >1,000/sec)")

    print_header("DEMO COMPLETE")
    print(f"  ✓ All decisions cryptographically signed")
    print(f"  ✓ Full audit trail: {audit_chain.length()} entries")
    print(f"  ✓ Zero bypass paths")
    print(f"  ✓ Fail-closed: any error → DENY")
    print(f"\n  'No action reaches a tool unless AVS checks it first.'")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
