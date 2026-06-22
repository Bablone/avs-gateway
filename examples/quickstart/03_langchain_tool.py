"""
AVS Quickstart 03 LangChain Tool Adapter

Shows: wrap a LangChain tool with AVS governance.
LangChain is optional if not installed, prints instructions.

Install LangChain first:
  pip install -r requirements-langchain.txt

Then run:
  python examples/quickstart/03_langchain_tool.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Check if LangChain is available
try:
  from langchain_core.tools import BaseTool
  LANGCHAIN_AVAILABLE = True
except ImportError:
  LANGCHAIN_AVAILABLE = False


def main():
  print("=" * 60)
  print(" AVS Quickstart 03 LangChain Tool Adapter")
  print("=" * 60)

  if not LANGCHAIN_AVAILABLE:
    print("\n  LangChain is not installed.")
    print("\n To run this example:")
    print("  pip install -r requirements-langchain.txt")
    print(" or:")
    print("  pip install langchain-core langchain")
    print("\n Then re-run this script.")
    return 0

  # LangChain IS available proceed with demo
  from avs_gateway.core.policy_engine import PolicyEngine
  from avs_gateway.core.risk_engine import RiskEngine
  from avs_gateway.core.trust_memory import TrustMemory
  from avs_gateway.core.receipt_generator import ReceiptGenerator
  from avs_gateway.core.audit_chain import AuditChain
  from avs_gateway.core.gateway_core import Gateway
  from avs_gateway.models.action_request import ActionType
  from avs_gateway.adapters.langchain_adapter import govern_langchain_tool

  # Build Gateway
  pe = PolicyEngine()
  pe.load_policies("avs_gateway/config/default_policies.yaml")
  gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())

  # Define a mock LangChain tool
  class MockSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information"

    def _run(self, query: str) -> str:
      return f"Search results for '{query}': [mock data]"

  # Wrap with AVS governance
  governed_search = govern_langchain_tool(
    tool=MockSearchTool(),
    gateway=gateway,
    action_type=ActionType.API,
    operation="GET",
  )

  print("\n[1] Calling governed_search.run('weather today')")
  result1 = governed_search._run("weather today")
  print(f"  Result  : {result1[:60]}...")

  # Evidence
  print("\n" + "=" * 60)
  print(" Summary")
  print("=" * 60)
  stats = gateway.get_stats()
  print(f" Total intercepts : {stats['total_intercepts']}")
  print(f" Audit entries  : {gateway.audit_chain.length()}")
  print("\n The LangChain tool executed through AVS.")
  print(" Every tool call gets a receipt.")
  print("=" * 60)

  return 0


if __name__ == "__main__":
  sys.exit(main())
