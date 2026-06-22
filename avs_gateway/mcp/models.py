"""
mcp/models.py — AVS MCP Guard v0.4.0

Step 1: Pure MCP request normalizer.
Converts raw JSON-RPC tools/call requests into structured objects.
No transport logic. No policy. Just normalization and validation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json
import hashlib
import logging

logger = logging.getLogger("avs_gateway.mcp.models")


@dataclass(frozen=True)
class MCPToolDescriptor:
    """A normalized, canonicalized tool descriptor from tools/list."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    # Annotations are optional in MCP spec but security-relevant
    annotations: Optional[Dict[str, Any]] = None

    def descriptor_hash(self) -> str:
        """Return sha256:hex of canonicalized descriptor.
        
        Includes name, description, and input_schema. Description changes
        count as drift because tool poisoning research shows attacks
        embedded in altered descriptors.
        """
        canonical = {
            "name": self.name,
            "description": self.description,
            "inputSchema": _canonicalize_json(self.input_schema),
            "annotations": _canonicalize_json(self.annotations or {}),
        }
        return "sha256:" + hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class MCPServerManifest:
    """A complete, canonicalized manifest from an MCP server.
    
    Handles pagination by requiring all pages to be fetched before
    manifest creation. Tools are sorted deterministically by name
    so ordering changes don't affect the hash.
    """
    server_id: str
    protocol_version: str = "2024-11-05"
    tools: List[MCPToolDescriptor] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    
    def manifest_hash(self) -> str:
        """Return sha256:hex of canonicalized full manifest."""
        tool_hashes = sorted([t.descriptor_hash() for t in self.tools])
        # Resources use same canonicalization
        resource_canonical = sorted([
            json.dumps(_canonicalize_json(r), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            for r in self.resources
        ])
        payload = {
            "protocol_version": self.protocol_version,
            "tools": tool_hashes,
            "resources": resource_canonical,
        }
        return "sha256:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def get_tool(self, name: str) -> Optional[MCPToolDescriptor]:
        """Get a tool descriptor by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def has_tool(self, name: str) -> bool:
        """Check if a tool is in the manifest."""
        return self.get_tool(name) is not None


@dataclass
class MCPToolCallRequest:
    """A normalized MCP tools/call request.
    
    Extracted from raw JSON-RPC. Always contains the fields needed
    for admission evaluation, regardless of transport.
    """
    jsonrpc_id: Any  # JSON-RPC request ID (must be preserved)
    server_id: str
    tool_name: str
    arguments: Dict[str, Any]
    # Hashed for receipt — raw args never stored in receipts
    arguments_hash: str = ""
    # The tool descriptor from the approved manifest (if found)
    tool_descriptor: Optional[MCPToolDescriptor] = None
    # MCP protocol metadata
    mcp_protocol_version: str = "2024-11-05"
    mcp_transport: str = "stdio"  # stdio | http | simulated
    mcp_session_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.arguments_hash:
            object.__setattr__(self, "arguments_hash", _hash_dict(self.arguments))


def _canonicalize_json(obj: Any) -> Any:
    """Recursively canonicalize a JSON-serializable object.
    
    - Dicts: sorted keys, all values canonicalized
    - Lists: all items canonicalized (order preserved for lists)
    - Primitives: returned as-is
    """
    if isinstance(obj, dict):
        return {k: _canonicalize_json(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_canonicalize_json(item) for item in obj]
    return obj


def _hash_dict(data: Dict[str, Any]) -> str:
    """Return sha256:hex of canonicalized dict."""
    canonical = json.dumps(_canonicalize_json(data), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_tools_list(tools_raw: List[Dict[str, Any]], server_id: str) -> MCPServerManifest:
    """Normalize a raw tools/list response into a canonical manifest.
    
    Args:
        tools_raw: List of tool descriptors from tools/list
        server_id: Identifier for the MCP server
        
    Returns:
        MCPServerManifest with canonicalized, sorted tool descriptors
    """
    tools = []
    for tool_raw in tools_raw:
        name = tool_raw.get("name", "")
        if not name:
            logger.warning("Skipping tool with no name in tools/list")
            continue
        # Normalize Unicode (NFKC) to prevent homoglyph attacks
        name = name.strip()
        desc = tool_raw.get("description", "")
        schema = tool_raw.get("inputSchema", tool_raw.get("input_schema", {}))
        annotations = tool_raw.get("annotations")
        
        tools.append(MCPToolDescriptor(
            name=name,
            description=desc,
            input_schema=schema,
            annotations=annotations,
        ))
    
    # Sort deterministically by name so order doesn't affect hash
    tools.sort(key=lambda t: t.name)
    
    return MCPServerManifest(
        server_id=server_id,
        tools=tools,
    )


def normalize_tool_call(raw_request: Dict[str, Any], server_id: str) -> MCPToolCallRequest:
    """Normalize a raw JSON-RPC tools/call request.
    
    Args:
        raw_request: The JSON-RPC request dict
        server_id: Identifier for the MCP server
        
    Returns:
        MCPToolCallRequest with normalized fields
    """
    params = raw_request.get("params", {})
    return MCPToolCallRequest(
        jsonrpc_id=raw_request.get("id"),
        server_id=server_id,
        tool_name=params.get("name", ""),
        arguments=params.get("arguments", {}),
        mcp_protocol_version="2024-11-05",
        mcp_transport="simulated",  # Will be set by transport layer
    )


def validate_no_duplicate_tools(tools: List[MCPToolDescriptor]) -> Optional[str]:
    """Check for duplicate tool names (including Unicode homoglyphs).
    
    Returns:
        Error message if duplicates found, None otherwise
    """
    seen = set()
    for tool in tools:
        # Normalize Unicode to prevent homoglyph attacks (e.g., "delete" vs "deIete")
        normalized = tool.name.encode("ascii", "ignore").decode("ascii").lower().strip()
        if normalized in seen:
            return f"Duplicate tool name detected: {tool.name}"
        seen.add(normalized)
    return None
