"""
mcp/receipts.py -- AVS MCP Guard v0.4.0 (ASR-1 Integrated)

Step 4: ASR-1 receipt generation for MCP tool calls.
Uses the real ASR-1 infrastructure: ASR1ReceiptGenerator for signing,
ASR1Receipt dataclass for structure. Receipts produced here are
verifiable via `avs receipt verify`.
"""

import time
import uuid
import hashlib
import json
import logging
from types import SimpleNamespace
from typing import Dict, Any, Optional

from avs_gateway.mcp.constants import MCPDecision, MCPReasonCode, MCPGuardMode
from avs_gateway.mcp.models import MCPToolCallRequest, MCPToolDescriptor
from avs_gateway.mcp.session import SessionContext

# Real ASR-1 infrastructure
from avs_gateway.receipts.asr1 import (
    ASR1ReceiptGenerator,
    ASR1Receipt,
    verify_receipt,
    hash_payload,
)

logger = logging.getLogger("avs_gateway.mcp.receipts")


class _MCPReceiptGenerator:
    """Per-server MCP receipt generator wrapping ASR1ReceiptGenerator.

    Each server gets its own generator instance so receipt chains
    are server-scoped (prevents cross-server hash chain pollution).
    """

    _instances: Dict[str, "_MCPReceiptGenerator"] = {}

    def __init__(self, server_id: str) -> None:
        self.server_id = server_id
        self._generator = ASR1ReceiptGenerator()

    @classmethod
    def for_server(cls, server_id: str) -> "_MCPReceiptGenerator":
        if server_id not in cls._instances:
            cls._instances[server_id] = cls(server_id)
        return cls._instances[server_id]

    @classmethod
    def reset_all(cls) -> None:
        cls._instances.clear()

    @property
    def generator(self) -> ASR1ReceiptGenerator:
        return self._generator


def _action_request_for_generate(
    request: MCPToolCallRequest,
    agent_id: str,
) -> SimpleNamespace:
    """Build a SimpleNamespace that satisfies ASR1ReceiptGenerator.generate()."""
    action_type_ns = SimpleNamespace(value="mcp.tool_call")
    return SimpleNamespace(
        action_id=str(request.jsonrpc_id) if request.jsonrpc_id is not None else f"mcp_{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        action_type=action_type_ns,
        tool_name=request.tool_name,
        operation="tools/call",
        parameters=request.arguments,
        context={"server_id": request.server_id, "mcp_transport": request.mcp_transport},
    )


def _decision_for_generate(
    decision: MCPDecision,
    reason: MCPReasonCode,
    risk_score: int,
    action_class: str = "",
) -> SimpleNamespace:
    """Build a SimpleNamespace that satisfies ASR1ReceiptGenerator.generate()."""
    decision_type_ns = SimpleNamespace(value=decision.value)
    return SimpleNamespace(
        decision_type=decision_type_ns,
        reason=reason.value,
        matched_policy=None,
        risk_score=float(risk_score),
        trust_score=0.0,
        action_class=action_class,
    )


def _tool_manifest_for_generate(
    tool: Optional[MCPToolDescriptor],
    manifest_hash: str,
) -> Optional[SimpleNamespace]:
    """Build a SimpleNamespace for ASR-1 tool manifest fields."""
    if tool is None:
        return None
    return SimpleNamespace(
        tool_name=tool.name,
        module_path="",
        function_name=tool.name,
        source_hash=tool.descriptor_hash(),
        registered_at="",
        registered_by="system",
        policy_binding=manifest_hash,
    )


def generate_mcp_receipt(
    request: MCPToolCallRequest,
    tool: Optional[MCPToolDescriptor],
    decision: MCPDecision,
    reason: MCPReasonCode,
    risk_score: int,
    mode: MCPGuardMode,
    session: Optional[SessionContext] = None,
    manifest_hash: str = "",
    enforcement_active: bool = True,
    agent_id: str = "agent_default",
    action_class: str = "",
) -> ASR1Receipt:
    """Generate a properly signed ASR-1 receipt for an MCP tool call.

    This receipt is a real ASR-1 receipt: it uses ASR1ReceiptGenerator for
    Ed25519 signing and can be verified via `avs receipt verify`.

    Args:
        request: The normalized tool call request
        tool: The tool descriptor (None if unknown tool)
        decision: The admission decision
        reason: The reason code
        risk_score: Risk score 0-100
        mode: Guard mode (observe/soft_gate/hard_gate)
        session: Optional session context
        manifest_hash: Hash of the approved manifest
        enforcement_active: Whether the decision was actually enforced
        agent_id: The agent making the request
        action_class: The classified action class

    Returns:
        ASR1Receipt -- a signed, verifiable receipt
    """
    gen = _MCPReceiptGenerator.for_server(request.server_id)

    # Observe mode: truthfully report what WOULD have happened
    effective_decision = decision
    if mode == MCPGuardMode.OBSERVE and not enforcement_active:
        effective_decision = MCPDecision.WOULD_DENY

    # Bridge objects for the ASR-1 generator
    action_req = _action_request_for_generate(request, agent_id)
    decision_ns = _decision_for_generate(effective_decision, reason, risk_score, action_class)
    tool_manifest = _tool_manifest_for_generate(tool, manifest_hash)

    # Generate the signed receipt via real ASR-1 infrastructure
    receipt = gen.generator.generate_and_sign(
        action_request=action_req,
        decision=decision_ns,
        latency_ms=0.0,
        previous_receipt_hash=None,  # uses generator's internal chain
    )

    return receipt


def verify_mcp_receipt(receipt: ASR1Receipt) -> bool:
    """Verify an MCP receipt's integrity.

    Wrapper around ASR-1 verify_receipt for MCP context.

    Args:
        receipt: The ASR1Receipt to verify

    Returns:
        True if the receipt hash and signature are valid
    """
    return verify_receipt(receipt)


def receipt_to_mcp_dict(receipt: ASR1Receipt) -> Dict[str, Any]:
    """Convert an ASR1Receipt to a flat dict with MCP-specific fields.

    This is the format returned to callers who need the legacy dict
    shape (e.g., the demo script, API responses).

    Args:
        receipt: The ASR1Receipt to convert

    Returns:
        Dict with ASR-1 fields + MCP enrichment
    """
    d = receipt.to_dict()
    # Flatten nested structure for backward compatibility
    flat = {
        "asr_version": receipt.asr_version,
        "receipt_id": receipt.receipt_id,
        "request_id": receipt.request_id,
        "timestamp_ns": receipt.timestamp_ns,
        "agent_id": receipt.agent_id,
        "action_type": receipt.action_type,
        "tool_name": receipt.tool_name,
        "parameter_hash": receipt.parameter_hash,
        "context_hash": receipt.context_hash,
        "decision": receipt.decision,
        "decision_reason": receipt.decision_reason,
        "risk_score": receipt.risk_score,
        "trust_score": receipt.trust_score,
        "executed": receipt.executed,
        "execution_status": receipt.execution_status,
        "latency_ms": receipt.latency_ms,
        "receipt_hash": receipt.receipt_hash,
        "gateway_signature": receipt.gateway_signature,
        "previous_receipt_hash": receipt.previous_receipt_hash,
        # Nested sections for detail
        "agent_identity": d.get("agent_identity", {}),
        "action": d.get("action", {}),
        "tool_manifest": d.get("tool_manifest", {}),
        "governance": d.get("governance", {}),
        "execution": d.get("execution", {}),
        "ledger": d.get("ledger", {}),
    }
    return flat
