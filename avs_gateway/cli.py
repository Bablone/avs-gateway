"""
cli.py -- AVS Gateway Command-Line Interface (v0.3.4)

Usage:
    avs version        Show AVS version
    avs demo           Run a 30-second demo of AVS governance
    avs quickstart     List available quickstart examples

Installs as console script via pyproject.toml:
    avs = avs_gateway.cli:main
"""

import sys
import os
import subprocess

# Package version
__version__ = "0.3.4"


def _get_repo_root() -> str:
    """Return the repository root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cmd_version(_args):
    """Print AVS version and basic info."""
    print(f"AVS Gateway {__version__}")
    print("Runtime Permission Layer for AI Agents")
    print("Every agent action gets a receipt.")
    print(f"\nPython: {sys.version.split()[0]}")
    print(f"Path:   {_get_repo_root()}")


def cmd_demo(_args):
    """Run a 30-second deterministic demo of AVS governance.

    Shows three decisions:
        1. ALLOW  -- safe file read
        2. DENY   -- dangerous delete
        3. PENDING -- production deployment (requires approval)

    No external APIs. No LLM keys. Works 100% offline.
    """
    # We run the demo inline to avoid subprocess complexity
    from avs_gateway.core.gateway_core import Gateway
    from avs_gateway.models.action_request import create_action_request, ActionType
    from avs_gateway.core.policy_engine import PolicyEngine
    from avs_gateway.core.risk_engine import RiskEngine
    from avs_gateway.core.trust_memory import TrustMemory
    from avs_gateway.core.receipt_generator import ReceiptGenerator
    from avs_gateway.core.audit_chain import AuditChain

    SEP = "=" * 58

    print(SEP)
    print("  AVS Gateway Demo - Runtime Permission Layer")
    print(SEP)
    print()

    pe = PolicyEngine()
    try:
        pe.load_policies("avs_gateway/config/default_policies.yaml")
    except Exception:
        pass  # Policies may not be found in all install contexts

    gateway = Gateway(
        pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain(),
    )

    # --- Scenario 1: ALLOW ---
    action1 = create_action_request(
        agent_id="demo_agent",
        action_type=ActionType.FILE,
        tool_name="file_read",
        operation="read",
        parameters={"path": "sandbox/report.txt"},
    )
    d1 = gateway.intercept(action1)
    r1 = gateway.record(action1, d1)

    print(f"  [ALLOW]  file_read sandbox/report.txt")
    print(f"           Decision : {d1.decision_type.value}")
    print(f"           Reason   : {d1.reason}")
    print(f"           Receipt  : {r1.receipt_hash[:24]}...")
    print()

    # --- Scenario 2: DENY ---
    action2 = create_action_request(
        agent_id="demo_agent",
        action_type=ActionType.FILE,
        tool_name="file_delete",
        operation="delete",
        parameters={"path": "/etc/passwd"},
    )
    d2 = gateway.intercept(action2)
    r2 = gateway.record(action2, d2)

    print(f"  [DENY]   file_delete /etc/passwd")
    print(f"           Decision : {d2.decision_type.value}")
    print(f"           Reason   : {d2.reason}")
    print(f"           Receipt  : {r2.receipt_hash[:24]}...")
    print(f"           -> Tool did NOT execute")
    print()

    # --- Scenario 3: REQUIRE_APPROVAL ---
    action3 = create_action_request(
        agent_id="demo_agent",
        action_type=ActionType.API,
        tool_name="deploy_to_production",
        operation="deploy_prod",
        parameters={"manifest": "payment-processor.yaml"},
        context={"environment": "production"},
    )
    d3 = gateway.intercept(action3)
    r3 = gateway.record(action3, d3)

    print(f"  [PENDING] deploy_to_production payment-processor.yaml")
    print(f"           Decision : {d3.decision_type.value}")
    print(f"           Reason   : {d3.reason}")
    print(f"           Receipt  : {r3.receipt_hash[:24]}...")
    print(f"           -> Queued for human approval")
    print()

    # --- Evidence summary ---
    stats = gateway.get_stats()
    print(SEP)
    print("  Evidence Summary")
    print(SEP)
    print(f"    Total intercepts : {stats['total_intercepts']}")
    for dt, count in stats["decisions"].items():
        print(f"    {dt:18s} : {count}")
    print(f"    Audit chain      : {gateway.audit_chain.length()} entries")
    print()
    print("  Every agent action gets a receipt.")
    print("  No action executes without AVS deciding first.")
    print(SEP)


def cmd_quickstart(_args):
    """List available quickstart examples."""
    root = _get_repo_root()
    examples_dir = os.path.join(root, "examples", "quickstart")

    print("AVS Gateway Quickstart Examples")
    print("=" * 50)
    print()

    if not os.path.isdir(examples_dir):
        print(f"Examples directory not found: {examples_dir}")
        print("Clone the AVS repository to access examples:")
        print("  git clone https://github.com/avsgateway/avs-gateway")
        return

    examples = [
        ("01_gateway_basics.py", "Gateway intercept, decision, receipt"),
        ("02_governed_tool.py",  "@governed_tool decorator"),
        ("03_langchain_tool.py", "LangChain adapter (optional dep)"),
        ("04_custom_action.py",  "Custom business action + approval"),
    ]

    for filename, description in examples:
        path = os.path.join(examples_dir, filename)
        status = "[OK]" if os.path.isfile(path) else "[FAIL]"
        print(f"  {status} {filename:30s} - {description}")

    print()
    print("Run any example:")
    print(f"  cd {root}")
    print("  python examples/quickstart/01_gateway_basics.py")


def main():
    """Entry point for the `avs` console script."""
    if len(sys.argv) < 2:
        print("AVS Gateway - Runtime Permission Layer for AI Agents")
        print("Every agent action gets a receipt.")
        print()
        print("Usage: avs <command>")
        print()
        print("Commands:")
        print("  version     Show AVS version")
        print("  demo        Run 30-second governance demo")
        print("  quickstart  List available quickstart examples")
        print()
        print("Install:")
        print("  pip install -e .")
        print()
        print("Quick start:")
        print("  avs demo")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "version": cmd_version,
        "demo": cmd_demo,
        "quickstart": cmd_quickstart,
    }

    func = commands.get(command)
    if func is None:
        print(f"Unknown command: {command}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    try:
        func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
