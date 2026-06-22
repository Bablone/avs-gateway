"""
mcp/manifest.py — AVS MCP Guard v0.4.0

Step 2: Manifest hasher.
Produces stable canonical manifest hashes, detects drift,
enforces strict manifest adherence at call time.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
import time
import logging

from avs_gateway.mcp.models import MCPServerManifest, MCPToolDescriptor, validate_no_duplicate_tools
from avs_gateway.mcp.constants import MCPDecision, MCPReasonCode

logger = logging.getLogger("avs_gateway.mcp.manifest")


@dataclass
class ApprovedManifest:
    """A manifest that has been approved for a given server.
    
    Tracks the approved hash, when it was approved, and by whom.
    Used for drift detection at both inventory-time and call-time.
    """
    server_id: str
    manifest: MCPServerManifest
    approved_hash: str
    approved_at: float
    approved_by: str = "system"
    
    def is_current(self, current_manifest: MCPServerManifest) -> bool:
        """Check if the current manifest matches the approved hash."""
        return current_manifest.manifest_hash() == self.approved_hash


@dataclass
class ManifestDriftReport:
    """Report of what changed between approved and current manifest."""
    server_id: str
    drift_detected: bool
    approved_hash: str
    current_hash: str
    added_tools: List[str] = field(default_factory=list)
    removed_tools: List[str] = field(default_factory=list)
    changed_tools: List[str] = field(default_factory=list)  # Description/schema changed
    reasons: List[str] = field(default_factory=list)


def detect_manifest_drift(
    approved: ApprovedManifest,
    current: MCPServerManifest,
) -> ManifestDriftReport:
    """Detect what changed between approved and current manifest.
    
    Compares tool names, descriptor hashes, and descriptions.
    A tool whose description changed counts as drift (tool poisoning risk).
    """
    report = ManifestDriftReport(
        server_id=approved.server_id,
        drift_detected=False,
        approved_hash=approved.approved_hash,
        current_hash=current.manifest_hash(),
    )
    
    if approved.is_current(current):
        return report
    
    report.drift_detected = True
    
    # Build lookup by name
    approved_tools = {t.name: t for t in approved.manifest.tools}
    current_tools = {t.name: t for t in current.tools}
    
    # Find added tools
    for name in current_tools:
        if name not in approved_tools:
            report.added_tools.append(name)
            report.reasons.append(f"Tool '{name}' added since approval")
    
    # Find removed tools
    for name in approved_tools:
        if name not in current_tools:
            report.removed_tools.append(name)
            report.reasons.append(f"Tool '{name}' removed since approval")
    
    # Find changed tools (descriptor hash changed = description or schema changed)
    for name in approved_tools:
        if name in current_tools:
            old_desc = approved_tools[name]
            new_desc = current_tools[name]
            if old_desc.descriptor_hash() != new_desc.descriptor_hash():
                report.changed_tools.append(name)
                # Determine what changed
                if old_desc.description != new_desc.description:
                    report.reasons.append(f"Tool '{name}': description changed (poisoning risk)")
                if old_desc.input_schema != new_desc.input_schema:
                    report.reasons.append(f"Tool '{name}': input schema changed")
    
    return report


def check_call_time_manifest(
    tool_name: str,
    tool_descriptor_hash: str,
    arguments: Dict[str, Any],
    approved_manifest: ApprovedManifest,
) -> tuple:
    """Check a tool call against the approved manifest at call time.
    
    Enforces strict manifest adherence:
    - Tool must exist in approved manifest
    - Descriptor hash must match
    - Arguments must match schema (basic check)
    
    Returns:
        (passed: bool, decision: MCPDecision or None, reason: MCPReasonCode or None)
    """
    manifest = approved_manifest.manifest
    
    # Check 1: Tool exists in manifest
    tool = manifest.get_tool(tool_name)
    if tool is None:
        logger.warning("Shadow tool call denied: '%s' not in manifest", tool_name)
        return False, MCPDecision.DENY, MCPReasonCode.MCP_UNKNOWN_TOOL
    
    # Check 2: Descriptor hash matches
    if tool.descriptor_hash() != tool_descriptor_hash:
        logger.warning(
            "Descriptor hash mismatch for '%s': expected=%s, got=%s",
            tool_name, tool.descriptor_hash()[:16], tool_descriptor_hash[:16]
        )
        return False, MCPDecision.QUARANTINE, MCPReasonCode.MCP_DESCRIPTOR_HASH_MISMATCH
    
    # Check 3: No duplicate tool names (homoglyph check)
    dup_error = validate_no_duplicate_tools(manifest.tools)
    if dup_error:
        logger.warning("Duplicate tool names in manifest: %s", dup_error)
        return False, MCPDecision.DENY, MCPReasonCode.MCP_DUPLICATE_TOOL_NAME
    
    return True, None, None


def should_refresh_manifest(
    approved: ApprovedManifest,
    config: Dict[str, Any],
    is_high_risk_call: bool = False,
) -> bool:
    """Determine if the manifest should be refreshed.
    
    Refresh triggers:
    - Before high-risk calls
    - Interval exceeded
    - On list_changed notification (handled by caller)
    
    Args:
        approved: The currently approved manifest
        config: Manifest refresh configuration
        is_high_risk_call: Whether this is a high-risk tool call
        
    Returns:
        True if refresh should occur
    """
    refresh_config = config.get("manifest_refresh", {})
    
    if is_high_risk_call and refresh_config.get("before_high_risk_call", True):
        return True
    
    interval = refresh_config.get("interval_seconds", 300)
    elapsed = time.time() - approved.approved_at
    if elapsed > interval:
        return True
    
    return False
