"""
AVS Quickstart 02  @governed_tool Decorator

Shows: wrap any Python function with one line. AVS intercepts
automatically. Allowed functions execute. Denied functions are
blocked with structured evidence.

Run:
    python examples/quickstart/02_governed_tool.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from avs_gateway.models.action_request import ActionType
from avs_gateway.adapters.governed import governed_tool, set_default_gateway
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway


def main():
    print("=" * 60)
    print("  AVS Quickstart 02  @governed_tool Decorator")
    print("  One line. No rewrites. Full governance.")
    print("=" * 60)

    # Setup Gateway with policies that allow file reads, deny deletes
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    set_default_gateway(gateway)

    # ---- Define a tool and wrap it with @governed_tool ----
    @governed_tool(
        tool_name="read_config",
        action_type=ActionType.FILE,
        operation="read",
    )
    def read_config_file(path: str) -> str:
        """Read a configuration file."""
        return f"Contents of {path}: server=prod, port=8080"

    @governed_tool(
        tool_name="delete_database",
        action_type=ActionType.DATABASE,
        operation="drop",
    )
    def delete_database(name: str) -> str:
        """DANGEROUS: Delete a database."""
        return f"Database {name} DELETED"

    # ---- Call 1: ALLOWED ----
    print("\n[1] Calling read_config_file('settings.conf')")
    result1 = read_config_file("settings.conf")
    print(f"    Executed : {result1.executed}")
    print(f"    Decision : {result1.decision}")
    print(f"    Receipt  : {result1.receipt_hash[:24]}...")

    # ---- Call 2: DENIED ----
    print("\n[2] Calling delete_database('production')")
    result2 = delete_database("production")
    print(f"    Executed : {result2.executed}")
    print(f"    Decision : {result2.decision}")
    print(f"    Reason   : {result2.reason}")
    print(f"     The delete function NEVER ran. No data was lost.")

    # ---- Evidence ----
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Total intercepts : {gateway.get_stats()['total_intercepts']}")
    print(f"  Audit entries    : {gateway.audit_chain.length()}")
    print("\n  Your original code is unchanged.")
    print("  AVS adds the permission layer around it.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
