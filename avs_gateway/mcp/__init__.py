"""
mcp/__init__.py — AVS MCP Guard v0.4.0

Agent Admission Controller for MCP tool calls.

MCP gives agents hands. AVS decides when those hands are allowed to touch production.
"""

from avs_gateway.mcp.models import (
    MCPToolDescriptor,
    MCPServerManifest,
    MCPToolCallRequest,
    normalize_tools_list,
    normalize_tool_call,
)
from avs_gateway.mcp.manifest import (
    ApprovedManifest,
    ManifestDriftReport,
    detect_manifest_drift,
    check_call_time_manifest,
)
from avs_gateway.mcp.classifier import classify_tool
from avs_gateway.mcp.policy import evaluate_mcp_policy, build_policy_decision_response
from avs_gateway.mcp.guard import guard_tool_call, approve_manifest
from avs_gateway.mcp.receipts import generate_mcp_receipt
from avs_gateway.mcp.session import SessionContext, SessionTag
from avs_gateway.mcp.constants import (
    MCPActionClass,
    MCPDecision,
    MCPReasonCode,
    MCPResponseMode,
    MCPGuardMode,
    MCPSessionTagType,
    DEFAULT_MCP_GUARD_CONFIG,
)

__all__ = [
    # Models
    "MCPToolDescriptor",
    "MCPServerManifest",
    "MCPToolCallRequest",
    "normalize_tools_list",
    "normalize_tool_call",
    # Manifest
    "ApprovedManifest",
    "ManifestDriftReport",
    "detect_manifest_drift",
    "check_call_time_manifest",
    # Classification + Policy
    "classify_tool",
    "evaluate_mcp_policy",
    "build_policy_decision_response",
    # Guard
    "guard_tool_call",
    "approve_manifest",
    # Receipts
    "generate_mcp_receipt",
    # Session
    "SessionContext",
    "SessionTag",
    # Constants
    "MCPActionClass",
    "MCPDecision",
    "MCPReasonCode",
    "MCPResponseMode",
    "MCPGuardMode",
    "MCPSessionTagType",
    "DEFAULT_MCP_GUARD_CONFIG",
]
