"""
mcp/policy.py — AVS MCP Guard v0.4.0

Step 3 (continued): MCP-specific policy evaluation.
Evaluates classified tool calls against policy and produces decisions.
"""

import logging
from typing import Dict, Any, Optional, List

from avs_gateway.mcp.models import MCPToolDescriptor, MCPToolCallRequest
from avs_gateway.mcp.constants import (
    MCPDecision, MCPActionClass, MCPReasonCode, MCPGuardMode,
    DEFAULT_MCP_GUARD_CONFIG,
)
from avs_gateway.mcp.session import SessionContext

logger = logging.getLogger("avs_gateway.mcp.policy")


def evaluate_mcp_policy(
    request: MCPToolCallRequest,
    action_class: MCPActionClass,
    tool: MCPToolDescriptor,
    config: Dict[str, Any],
    session: Optional[SessionContext] = None,
) -> tuple:
    """Evaluate an MCP tool call against the admission policy.
    
    The policy engine uses a two-stage approach:
    1. Schema validation: does the argument match the tool's inputSchema?
    2. Semantic validation: is the argument safe under policy?
    
    Args:
        request: The normalized tool call request
        action_class: The classified action type
        tool: The approved tool descriptor
        config: Policy configuration (from YAML)
        session: Optional session context for tag-based decisions
        
    Returns:
        (decision: MCPDecision, reason: MCPReasonCode, risk_score: int)
    """
    # Get mode
    mode = config.get("mode", MCPGuardMode.HARD_GATE)
    
    # Check 1: Schema validation (shape check)
    from avs_gateway.mcp.sanitizer import validate_schema
    schema_valid, schema_error = validate_schema(request.arguments, tool.input_schema)
    if not schema_valid:
        return MCPDecision.DENY, MCPReasonCode.MCP_SCHEMA_INVALID, 100
    
    # Check 2: Semantic validation (safety check)
    from avs_gateway.mcp.sanitizer import validate_semantics
    semantic_valid, semantic_reason = validate_semantics(
        request.arguments, action_class, config
    )
    if not semantic_valid and semantic_reason:
        return MCPDecision.DENY, semantic_reason, 95
    
    # Check 3: Session tag escalation
    if session and session.has_sensitive_tags():
        escalation_classes = (
            MCPActionClass.NETWORK, MCPActionClass.MESSAGE_SEND, MCPActionClass.FILESYSTEM_WRITE,
            MCPActionClass.FINANCIAL_MUTATION, MCPActionClass.INFRASTRUCTURE_MUTATION,
            MCPActionClass.CODE_MUTATION, MCPActionClass.REPOSITORY_WRITE,
        )
        if action_class in escalation_classes:
            return MCPDecision.REQUIRE_APPROVAL, MCPReasonCode.MCP_SENSITIVE_SESSION_TAG, 85
    
    # Check 4: Action class policy
    action_classes = config.get("action_classes", {})
    class_config = action_classes.get(action_class.value, {})
    
    if class_config:
        decision_str = class_config.get("decision")
        if decision_str:
            decision = MCPDecision(decision_str)
            reason = _get_reason_for_class(action_class, decision)
            risk = class_config.get("max_risk_score", 50)
            return decision, reason, risk
    
    # Check 5: Default decision
    default = config.get("default_decision", MCPDecision.REQUIRE_APPROVAL)
    return default, MCPReasonCode.MCP_POLICY_MATCHED_ALLOW, 50


def _get_reason_for_class(action_class: MCPActionClass, decision: MCPDecision) -> MCPReasonCode:
    """Get the canonical reason code for an action class + decision pair."""
    mapping = {
        (MCPActionClass.DESTRUCTIVE, MCPDecision.DENY): MCPReasonCode.MCP_DESTRUCTIVE_ACTION_DENIED,
        (MCPActionClass.FILESYSTEM_WRITE, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_WRITE_REQUIRES_APPROVAL,
        (MCPActionClass.CODE_EXECUTION, MCPDecision.DENY): MCPReasonCode.MCP_CODE_EXECUTION_DENIED,
        (MCPActionClass.CREDENTIAL_ACCESS, MCPDecision.DENY): MCPReasonCode.MCP_CREDENTIAL_ACCESS_DENIED,
        (MCPActionClass.PAYMENT_TRIGGER, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_PAYMENT_REQUIRES_APPROVAL,
        (MCPActionClass.DEPLOYMENT, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_DEPLOYMENT_REQUIRES_APPROVAL,
        (MCPActionClass.DATABASE_WRITE, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_DATABASE_WRITE_REQUIRES_APPROVAL,
        (MCPActionClass.MESSAGE_SEND, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_MESSAGE_SEND_REQUIRES_APPROVAL,
        # v0.4.0 — Sovereign execution control: mutation reason codes
        (MCPActionClass.FINANCIAL_MUTATION, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_FINANCIAL_MUTATION_REQUIRES_APPROVAL,
        (MCPActionClass.FINANCIAL_MUTATION, MCPDecision.DENY): MCPReasonCode.MCP_FINANCIAL_MUTATION_DENIED,
        (MCPActionClass.INFRASTRUCTURE_MUTATION, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_INFRASTRUCTURE_MUTATION_REQUIRES_APPROVAL,
        (MCPActionClass.INFRASTRUCTURE_MUTATION, MCPDecision.DENY): MCPReasonCode.MCP_INFRASTRUCTURE_MUTATION_DENIED,
        (MCPActionClass.CODE_MUTATION, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_CODE_MUTATION_REQUIRES_APPROVAL,
        (MCPActionClass.CODE_MUTATION, MCPDecision.DENY): MCPReasonCode.MCP_CODE_MUTATION_DENIED,
        (MCPActionClass.REPOSITORY_WRITE, MCPDecision.REQUIRE_APPROVAL): MCPReasonCode.MCP_REPOSITORY_WRITE_REQUIRES_APPROVAL,
        (MCPActionClass.REPOSITORY_WRITE, MCPDecision.DENY): MCPReasonCode.MCP_REPOSITORY_WRITE_DENIED,
    }
    return mapping.get((action_class, decision), MCPReasonCode.MCP_POLICY_MATCHED_ALLOW)


def build_policy_decision_response(
    decision: MCPDecision,
    reason: MCPReasonCode,
    risk_score: int,
    receipt_id: str,
    mode: MCPGuardMode,
) -> Dict[str, Any]:
    """Build the MCP response for a policy decision.
    
    Uses CallToolResult with isError: true for policy blocks.
    Only uses JSON-RPC protocol errors for actual protocol failures.
    """
    if mode == MCPGuardMode.OBSERVE:
        # Observe mode: truthful about what would have happened
        return {
            "content": [{
                "type": "text",
                "text": f"[AVS OBSERVE] Would have {decision.value}: {reason.value}. Risk: {risk_score}. Receipt: {receipt_id}"
            }],
            "isError": False,
            "_avs_meta": {
                "decision": decision.value,
                "would_have_decision": decision.value,
                "enforcement_mode": "observe",
                "enforcement_active": False,
                "reason": reason.value,
                "receipt_id": receipt_id,
            }
        }
    
    # Enforce mode: return tool result with isError: true
    decision_text = {
        MCPDecision.DENY: "blocked",
        MCPDecision.REQUIRE_APPROVAL: "requires human approval",
        MCPDecision.QUARANTINE: "quarantined",
    }.get(decision, "blocked")
    
    return {
        "content": [{
            "type": "text",
            "text": f"AVS {decision_text} this MCP tool call. Reason: {reason.value}. Receipt: {receipt_id}"
        }],
        "isError": True,
        "_avs_meta": {
            "avs_decision": decision.value,
            "avs_reason": reason.value,
            "avs_receipt_id": receipt_id,
            "avs_risk_score": risk_score,
        }
    }
