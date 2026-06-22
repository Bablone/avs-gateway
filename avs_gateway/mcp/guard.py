"""
mcp/guard.py -- AVS MCP Guard v0.4.0 (ASR-1 Integrated)

Main orchestration for MCP tool-call admission control.
Entry point: guard_tool_call() takes a request, evaluates it,
and returns the decision + MCP response + signed ASR-1 receipt.

The receipt is a real ASR-1 receipt (ASR1Receipt dataclass) signed
with Ed25519. It can be verified via `avs receipt verify`.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from avs_gateway.mcp.models import MCPToolCallRequest, MCPToolDescriptor, MCPServerManifest
from avs_gateway.mcp.manifest import ApprovedManifest, detect_manifest_drift, check_call_time_manifest
from avs_gateway.mcp.classifier import classify_tool
from avs_gateway.mcp.policy import evaluate_mcp_policy, build_policy_decision_response
from avs_gateway.mcp.receipts import (
    generate_mcp_receipt,
    receipt_to_mcp_dict,
    _MCPReceiptGenerator,
)
from avs_gateway.mcp.session import SessionContext
from avs_gateway.mcp.constants import MCPDecision, MCPReasonCode, MCPGuardMode, DEFAULT_MCP_GUARD_CONFIG

# Real ASR-1 type for return annotation
from avs_gateway.receipts.asr1 import ASR1Receipt

logger = logging.getLogger("avs_gateway.mcp.guard")


def guard_tool_call(
    request: MCPToolCallRequest,
    approved_manifest: ApprovedManifest,
    config: Optional[Dict[str, Any]] = None,
    session: Optional[SessionContext] = None,
    agent_id: str = "agent_default",
) -> Tuple[MCPDecision, Dict[str, Any], ASR1Receipt]:
    """Guard a single MCP tool call.

    The main entry point for MCP admission control. Evaluates:
    1. Call-time manifest check (strict adherence)
    2. Tool classification
    3. Policy evaluation (schema + semantic validation)
    4. Session tag escalation
    5. Receipt generation (signed ASR-1)

    Args:
        request: Normalized tool call request
        approved_manifest: The approved manifest for this server
        config: Policy configuration (uses default if not provided)
        session: Optional session context for data-flow tracking
        agent_id: The agent making the request

    Returns:
        (decision, mcp_response, receipt)
        - decision: MCPDecision enum
        - mcp_response: Dict for MCP response (tool result or error)
        - receipt: Signed ASR1Receipt (verifiable via avs receipt verify)
    """
    config = config or DEFAULT_MCP_GUARD_CONFIG
    mode = config.get("mode", MCPGuardMode.HARD_GATE)

    # Update agent_id on session
    if session:
        session.agent_id = agent_id

    # Observe mode: decisions are not enforced (truthful reporting)
    enforcement_active = (mode != MCPGuardMode.OBSERVE)

    # Step 1: Call-time manifest check (strict adherence)
    tool = approved_manifest.manifest.get_tool(request.tool_name)
    if tool:
        passed, fail_decision, fail_reason = check_call_time_manifest(
            request.tool_name,
            tool.descriptor_hash(),
            request.arguments,
            approved_manifest,
        )
        if not passed and fail_decision and fail_reason:
            receipt = generate_mcp_receipt(
                request=request,
                tool=tool,
                decision=fail_decision,
                reason=fail_reason,
                risk_score=100,
                mode=mode,
                session=session,
                manifest_hash=approved_manifest.approved_hash,
                agent_id=agent_id,
                enforcement_active=enforcement_active,
            )
            if mode == MCPGuardMode.OBSERVE:
                receipt = _patch_observe_receipt(receipt, fail_decision, mode)
            response = build_policy_decision_response(fail_decision, fail_reason, 100, receipt.receipt_id, mode)
            return fail_decision, response, receipt
    else:
        # Unknown tool (shadow tool)
        receipt = generate_mcp_receipt(
            request=request,
            tool=None,
            decision=MCPDecision.DENY,
            reason=MCPReasonCode.MCP_UNKNOWN_TOOL,
            risk_score=100,
            mode=mode,
            session=session,
            manifest_hash=approved_manifest.approved_hash,
            agent_id=agent_id,
            enforcement_active=enforcement_active,
        )
        if mode == MCPGuardMode.OBSERVE:
            receipt = _patch_observe_receipt(receipt, MCPDecision.DENY, mode)
        response = build_policy_decision_response(MCPDecision.DENY, MCPReasonCode.MCP_UNKNOWN_TOOL, 100, receipt.receipt_id, mode)
        return MCPDecision.DENY, response, receipt

    # Step 2: Tool classification
    overrides = config.get("tool_overrides", {})
    action_class = classify_tool(tool, overrides)

    # Step 3: Policy evaluation
    decision, reason, risk_score = evaluate_mcp_policy(
        request=request,
        action_class=action_class,
        tool=tool,
        config=config,
        session=session,
    )

    # Step 4: Session tagging (if read operation)
    if session:
        session.tag_from_tool_call(request.tool_name, request.arguments, f"asr_{request.tool_name}")

    # Step 5: Receipt generation (signed ASR-1)
    receipt = generate_mcp_receipt(
        request=request,
        tool=tool,
        decision=decision,
        reason=reason,
        risk_score=risk_score,
        mode=mode,
        session=session,
        manifest_hash=approved_manifest.approved_hash,
        agent_id=agent_id,
        action_class=action_class.value,
        enforcement_active=enforcement_active,
    )

    # Observe mode: patch execution status to reflect truth
    if mode == MCPGuardMode.OBSERVE:
        receipt = _patch_observe_receipt(receipt, decision, mode)

    # Build MCP response
    response = build_policy_decision_response(decision, reason, risk_score, receipt.receipt_id, mode)

    return decision, response, receipt


def _patch_observe_receipt(
    receipt: ASR1Receipt,
    actual_decision: MCPDecision,
    mode: MCPGuardMode,
) -> ASR1Receipt:
    """Patch receipt for observe-mode truthfulness.

    In observe mode, the receipt records what WOULD have happened
    while carrying the actual decision in metadata.

    Args:
        receipt: The generated ASR-1 receipt
        actual_decision: The real decision that was not enforced
        mode: Must be OBSERVE

    Returns:
        New ASR1Receipt with observe-mode annotations
    """
    from dataclasses import fields

    if mode != MCPGuardMode.OBSERVE:
        return receipt

    # Build a new receipt with truthful decision fields
    # The ASR-1 generator already set decision to WOULD_DENY
    # We just need to ensure the execution status reflects truth
    base = {f.name: getattr(receipt, f.name) for f in fields(ASR1Receipt) if f.name not in ("receipt_hash", "gateway_signature")}

    # Set truthful execution status
    if actual_decision == MCPDecision.ALLOW:
        base["executed"] = True
        base["execution_status"] = "executed"
    else:
        base["executed"] = False
        base["execution_status"] = "blocked"

    # Recreate with updated fields (no hash/signature yet)
    import hashlib
    import json
    updated = ASR1Receipt(**base)
    # Re-compute hash
    d = updated.to_dict()
    d.pop("ledger", None)
    new_hash = "sha256:" + hashlib.sha256(
        json.dumps(d, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    # Get the generator to sign the updated receipt
    gen = _MCPReceiptGenerator._instances.get(receipt.agent_id)
    if gen:
        unsigned = ASR1Receipt(**base, receipt_hash=new_hash)
        signed = gen.generator.sign(unsigned)
        return signed

    # Fallback: return updated with new hash but no re-signature
    return ASR1Receipt(**base, receipt_hash=new_hash)


def approve_manifest(manifest: MCPServerManifest, approved_by: str = "system") -> ApprovedManifest:
    """Approve a manifest for a server.

    This is the inventory-time approval step. The manifest hash is computed
    and stored. Any future changes trigger drift detection.

    Args:
        manifest: The server manifest to approve
        approved_by: Who approved the manifest

    Returns:
        ApprovedManifest object
    """
    import time
    return ApprovedManifest(
        server_id=manifest.server_id,
        manifest=manifest,
        approved_hash=manifest.manifest_hash(),
        approved_at=time.time(),
        approved_by=approved_by,
    )
