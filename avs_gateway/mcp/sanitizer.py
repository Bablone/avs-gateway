"""
mcp/sanitizer.py — AVS MCP Guard v0.4.0

Argument and output scanner.
Separates schema validation (shape) from semantic validation (safety).
"""

import re
import ipaddress
import logging
from typing import Dict, Any, Tuple, Optional

from avs_gateway.mcp.constants import MCPActionClass, MCPReasonCode, SENSITIVE_PATH_PATTERNS, CLOUD_METADATA_ENDPOINTS

logger = logging.getLogger("avs_gateway.mcp.sanitizer")


def validate_schema(arguments: Dict[str, Any], input_schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate that arguments match the tool's inputSchema (shape check).
    
    This is NOT a full JSON Schema validator. It checks:
    - Required fields are present
    - No unexpected fields (if additionalProperties: false)
    - Basic type consistency
    
    Returns:
        (valid: bool, error_message: str or None)
    """
    if not input_schema:
        return True, None  # No schema to validate against
    
    schema_props = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    additional = input_schema.get("additionalProperties", True)
    
    # Check required fields
    for field_name in required:
        if field_name not in arguments:
            return False, f"Missing required field: {field_name}"
    
    # Check for unexpected fields
    if not additional:
        for field_name in arguments:
            if field_name not in schema_props:
                return False, f"Unexpected field: {field_name}"
    
    # Basic type checks
    for field_name, value in arguments.items():
        if field_name in schema_props:
            prop_schema = schema_props[field_name]
            expected_type = prop_schema.get("type")
            if expected_type and not _check_type(value, expected_type):
                return False, f"Field '{field_name}': expected {expected_type}, got {type(value).__name__}"
    
    return True, None


def validate_semantics(
    arguments: Dict[str, Any],
    action_class: MCPActionClass,
    config: Dict[str, Any],
) -> Tuple[bool, Optional[MCPReasonCode]]:
    """Validate argument safety under policy (semantic check).
    
    Checks path traversal, private IPs, PII, etc.
    This is separate from schema validation.
    
    Returns:
        (safe: bool, reason_code: MCPReasonCode or None)
    """
    # Flatten arguments for scanning
    flat = _flatten_dict(arguments)
    
    for key, value in flat.items():
        if not isinstance(value, str):
            continue
        
        # Path traversal check
        if action_class in (MCPActionClass.FILESYSTEM_READ, MCPActionClass.FILESYSTEM_WRITE, MCPActionClass.DESTRUCTIVE):
            if _has_path_traversal(value):
                return False, MCPReasonCode.MCP_PATH_TRAVERSAL
            if _escapes_workspace(value, config):
                return False, MCPReasonCode.MCP_WORKSPACE_ESCAPE
        
        # Network safety check
        if action_class == MCPActionClass.NETWORK:
            if _is_private_ip(value):
                return False, MCPReasonCode.MCP_PRIVATE_IP_QUARANTINED
            if _is_cloud_metadata(value):
                return False, MCPReasonCode.MCP_CLOUD_METADATA_BLOCKED
        
        # Secret-like value check
        if _looks_like_secret(value):
            return False, MCPReasonCode.MCP_SECRET_LIKE_CONTENT_SEEN
    
    return True, None


def _check_type(value: Any, expected: str) -> bool:
    """Basic type check for schema validation."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected_types = type_map.get(expected, ())
    return isinstance(value, expected_types)


def _flatten_dict(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten a nested dict for scanning."""
    items = {}
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, new_key))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.update(_flatten_dict(item, f"{new_key}[{i}]"))
                else:
                    items[f"{new_key}[{i}]"] = item
        else:
            items[new_key] = v
    return items


def _has_path_traversal(value: str) -> bool:
    """Check for path traversal patterns."""
    dangerous = ["../", "..\\", "/..", "\\..", "~", "/etc/passwd", "/etc/shadow"]
    return any(pattern in value for pattern in dangerous)


def _escapes_workspace(value: str, config: Dict[str, Any]) -> bool:
    """Check if a path escapes the configured workspace.
    
    Only flags paths that are explicitly absolute or use parent traversal.
    Relative paths without traversal (e.g., "test.txt") are allowed.
    """
    # Skip if it's a URL
    if value.startswith(("http://", "https://", "ftp://")):
        return False
    
    # Only check paths that are explicitly dangerous
    if value.startswith("/"):  # Absolute path
        workspace = config.get("workspace_root", "./workspace")
        import os
        try:
            resolved = os.path.abspath(value)
            workspace_abs = os.path.abspath(workspace)
            return not resolved.startswith(workspace_abs)
        except (OSError, ValueError):
            return True
    
    if "../" in value or "..\\" in value:  # Parent traversal
        return True
    
    return False  # Relative paths without traversal are OK


def _is_private_ip(value: str) -> bool:
    """Check if a string contains a private IP address."""
    # Extract potential IP from URL or bare IP
    ip_match = re.search(r'(?:https?://)?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', value)
    if not ip_match:
        return False
    try:
        ip = ipaddress.ip_address(ip_match.group(1))
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def _is_cloud_metadata(value: str) -> bool:
    """Check if value points to cloud metadata endpoint."""
    return any(endpoint in value for endpoint in CLOUD_METADATA_ENDPOINTS)


def _looks_like_secret(value: str) -> bool:
    """Check if a string looks like a secret (API key, password, etc.)."""
    if len(value) < 16:
        return False
    # High entropy heuristic
    import string
    printable = set(string.printable)
    if not all(c in printable for c in value):
        return True  # Non-printable chars = likely binary/encoded secret
    # Base64-like pattern
    if re.match(r'^[A-Za-z0-9+/=]{32,}$', value):
        return True
    return False
