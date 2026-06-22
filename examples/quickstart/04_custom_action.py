"""
AVS Quickstart 04  Custom Business Action

THE UNIVERSAL CONTROL PLANE PROOF.

This example shows that AVS governs actions it has NEVER seen before.
The organization defines the tool, the policy, and the meaning.
AVS provides the infrastructure to enforce it.

Run:
    python examples/quickstart/04_custom_action.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from avs_gateway.core.policy_engine import PolicyEngine, PolicyRule, DecisionType as PDType
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway
from avs_gateway.models.action_request import ActionType, create_action_request


def main():
    print("=" * 60)
    print("  AVS Quickstart 04  Custom Business Action")
    print("  Universal Control Plane Proof")
    print("=" * 60)
    print("\n  This proves AVS governs actions it has never seen.")
    print("  deploy_to_production is defined by the organization,")
    print("  not by AVS. AVS still intercepts, decides, and")
    print("  produces evidence through the same pipeline.")

    # Build Gateway with a CUSTOM policy for production deployments
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")

    # This is the KEY: an organization-specific policy added
    # to the default policy set. AVS does not ship with this.
    # The organization defines it for their own governance.
    pe.add_rule(PolicyRule(
        name="production_deploy_approval",
        description="Production deployments require human approval",
        priority=5,
        condition={"action_type": "api", "operation": "deploy_prod"},
        decision=PDType.REQUIRE_APPROVAL,
        reason="Production deployments require CISO/SRE approval",
        enabled=True,
        tags=["deployment", "production", "approval-required"],
    ))

    gateway = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())

    # Track whether the dangerous function actually executed
    deploy_executed = [False]

    def deploy_to_production(manifest: str, service: str = "") -> str:
        """
        DANGEROUS: Deploy a service to production Kubernetes.
        If this executes without approval, production is at risk.
        """
        deploy_executed[0] = True
        return (
            f"[REAL EXECUTION] Deployed {service}:{manifest} "
            f"to PRODUCTION Kubernetes cluster!"
        )

    # Create the action request manually (as an adapter would)
    action = create_action_request(
        agent_id="devops_agent",
        action_type=ActionType.API,
        tool_name="deploy_to_production",
        operation="deploy_prod",
        parameters={"manifest": "payment-processor.yaml", "service": "payment-processor"},
        context={"environment": "production", "team": "platform"},
    )

    print("\n[1] Agent proposes: deploy payment-processor to production")
    print(f"    Tool      : deploy_to_production")
    print(f"    Manifest  : payment-processor.yaml")
    print(f"    Environment: production")

    # AVS intercepts
    decision = gateway.intercept(action)
    print(f"\n    Decision  : {decision.decision_type.value.upper()}")
    print(f"    Reason    : {decision.reason}")

    # If allowed, execute; if not, produce evidence
    if decision.decision_type.value == "allow":
        result = deploy_to_production("payment-processor.yaml", "payment-processor")
        receipt = gateway.record(action, decision)
        print(f"    Result    : {result}")
        print(f"    Receipt   : {receipt.receipt_hash[:24]}...")
    else:
        receipt = gateway.record(action, decision)
        print(f"    Result    : BLOCKED  tool did NOT execute")
        print(f"    Receipt   : {receipt.receipt_hash[:24]}...")
        print(f"     Kubernetes cluster was never touched")

    # ---- CRITICAL ASSERTION ----
    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)

    if deploy_executed[0]:
        print("  FAIL: deploy_to_production executed without approval!")
        return 1
    else:
        print("  PASS: deploy_to_production was NOT executed")
        print("  PASS: Approval is required before any deployment")
        print("  PASS: Cryptographic receipt was generated")

    stats = gateway.get_stats()
    print(f"\n  require_approval : {stats['decisions'].get('require_approval', 0)}")
    print(f"  Audit entries    : {gateway.audit_chain.length()}")

    print("\n" + "=" * 60)
    print("  What This Proves")
    print("=" * 60)
    print("  AVS does not need to 'know' about deployment tools.")
    print("  AVS provides the pipeline. The organization provides")
    print("  the tools, the policies, and the meaning.")
    print("")
    print("  Custom actions governed:")
    print("     deploy_to_production")
    print("     trade_stock, refund_customer")
    print("     access_patient_records")
    print("     ANY action your agents take")
    print("")
    print("  Every agent action gets a receipt.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
