"""
AVS Gateway v0 -- Proof-Gated Execution System.

Every agent action passes through Gateway.intercept() -> evaluate() -> decide() -> record().
Fail-closed: any unhandled exception results in a deny decision.
"""

__version__ = "0.4.1-alpha"

from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    FileOperation,
    EmailOperation,
    APIOperation,
    PaymentOperation,
    DatabaseOperation,
    SecurityScanOperation,
    create_action_request,
)

from avs_gateway.core.gateway_core import (
    Gateway,
    Decision,
    DecisionType,
)

from avs_gateway.core.policy_engine import (
    PolicyEngine,
    PolicyRule,
    PolicyResult,
)

from avs_gateway.core.risk_engine import (
    RiskEngine,
    RiskScore,
    RiskDimension,
    RiskClassification,
)

from avs_gateway.core.trust_memory import (
    TrustMemory,
    TrustScore as AgentTrustScore,
    TrustTier,
    AgentRecord,
)

from avs_gateway.core.receipt_generator import (
    ReceiptGenerator,
    Receipt,
    SignedReceipt,
    MerkleTree,
)

from avs_gateway.core.audit_chain import (
    AuditChain,
    ChainEntry,
)

from avs_gateway.tools.simulated_tools import (
    ToolResult,
    FileTool,
    EmailTool,
    APITool,
    PaymentTool,
    DatabaseTool,
    SecurityScanTool,
    ToolRegistry,
)

__all__ = [
    "Gateway",
    "Decision",
    "DecisionType",
    "ActionRequest",
    "ActionType",
    "create_action_request",
    "PolicyEngine",
    "PolicyRule",
    "PolicyResult",
    "RiskEngine",
    "RiskScore",
    "RiskDimension",
    "RiskClassification",
    "TrustMemory",
    "AgentTrustScore",
    "TrustTier",
    "ReceiptGenerator",
    "Receipt",
    "SignedReceipt",
    "MerkleTree",
    "AuditChain",
    "ChainEntry",
    "ToolResult",
    "FileTool",
    "EmailTool",
    "APITool",
    "PaymentTool",
    "DatabaseTool",
    "SecurityScanTool",
    "ToolRegistry",
]
