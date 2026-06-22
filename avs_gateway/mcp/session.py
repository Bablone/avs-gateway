"""
mcp/session.py — AVS MCP Guard v0.4.0

Session context with deterministic data-flow tags.
TTL-based expiration. Conservative — simple deterministic tags only.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from avs_gateway.mcp.constants import MCPSessionTagType, SENSITIVE_PATH_PATTERNS

logger = logging.getLogger("avs_gateway.mcp.session")

# Default TTL for session tags (seconds)
DEFAULT_TAG_TTL = 300  # 5 minutes


@dataclass
class SessionTag:
    """A single session tag with TTL and scope."""
    tag_type: str
    source_receipt_id: str
    created_at: float
    expires_at: float
    severity: str = "medium"  # low, medium, high, critical
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def is_sensitive(self) -> bool:
        return self.severity in ("high", "critical")


@dataclass
class SessionContext:
    """Session-wide context for data-flow tracking.
    
    Tracks what sensitive data has been accessed in this session
    so that later outbound actions can be upgraded.
    
    Session tags are:
    - Deterministic (not semantic/AI-based)
    - Scoped to the session only
    - TTL-based (expire after configured time)
    - Conservative (tag on suspicion, not certainty)
    """
    session_id: str
    agent_id: str
    server_id: str
    tags: List[SessionTag] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def add_tag(self, tag_type: str, receipt_id: str, severity: str = "medium", ttl: int = DEFAULT_TAG_TTL, metadata: Optional[Dict[str, str]] = None):
        """Add a tag to the session."""
        now = time.time()
        tag = SessionTag(
            tag_type=tag_type,
            source_receipt_id=receipt_id,
            created_at=now,
            expires_at=now + ttl,
            severity=severity,
            metadata=metadata or {},
        )
        self.tags.append(tag)
        logger.debug("Added session tag: %s (severity=%s, ttl=%ds)", tag_type, severity, ttl)
    
    def has_tag(self, tag_type: str) -> bool:
        """Check if a specific tag type is active (not expired)."""
        self._cleanup_expired()
        return any(t.tag_type == tag_type for t in self.tags)
    
    def has_sensitive_tags(self) -> bool:
        """Check if any sensitive (high/critical) tag is active."""
        self._cleanup_expired()
        return any(t.is_sensitive() for t in self.tags)
    
    def get_active_tags(self) -> List[SessionTag]:
        """Get all active (non-expired) tags."""
        self._cleanup_expired()
        return list(self.tags)
    
    def _cleanup_expired(self):
        """Remove expired tags."""
        self.tags = [t for t in self.tags if not t.is_expired()]
    
    def tag_from_tool_call(self, tool_name: str, arguments: Dict, receipt_id: str) -> bool:
        """Automatically tag session based on tool call patterns.
        
        Returns True if a tag was added.
        """
        tool_lower = tool_name.lower()
        added = False
        
        # Check for sensitive path reads
        if "read" in tool_lower or "file" in tool_lower:
            flat = _flatten_args(arguments)
            for val in flat.values():
                if isinstance(val, str):
                    for pattern in SENSITIVE_PATH_PATTERNS:
                        if pattern in val.lower():
                            self.add_tag(
                                MCPSessionTagType.SENSITIVE_PATH_READ.value,
                                receipt_id,
                                severity="high",
                                metadata={"path": val, "pattern": pattern}
                            )
                            added = True
                            break
        
        # Check for credential file access
        if "read" in tool_lower or "file" in tool_lower or "env" in tool_lower:
            flat = _flatten_args(arguments)
            for val in flat.values():
                if isinstance(val, str):
                    if ".env" in val or "secret" in val.lower() or "credential" in val.lower():
                        self.add_tag(
                            MCPSessionTagType.CREDENTIAL_FILE_ACCESSED.value,
                            receipt_id,
                            severity="critical",
                            metadata={"path": val}
                        )
                        added = True
        
        # Check for private key patterns
        if "read" in tool_lower or "ssh" in tool_lower or "key" in tool_lower:
            flat = _flatten_args(arguments)
            for val in flat.values():
                if isinstance(val, str):
                    if "id_rsa" in val or "id_dsa" in val or ".ssh" in val:
                        self.add_tag(
                            MCPSessionTagType.PRIVATE_KEY_PATTERN_SEEN.value,
                            receipt_id,
                            severity="critical",
                            metadata={"path": val}
                        )
                        added = True
        
        return added
    
    def calculate_risk_modifier(self, action_class: str) -> int:
        """Calculate risk score modifier based on active tags.
        
        Each sensitive tag adds to the risk of outbound actions.
        """
        self._cleanup_expired()
        modifier = 0
        for tag in self.tags:
            if tag.is_sensitive():
                modifier += {"low": 5, "medium": 15, "high": 30, "critical": 45}.get(tag.severity, 15)
        return min(modifier, 80)  # Cap at 80 to avoid always-deny


def _flatten_args(args: Dict) -> Dict[str, str]:
    """Flatten nested dict for scanning."""
    items = {}
    for k, v in args.items():
        if isinstance(v, dict):
            items.update(_flatten_args(v))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, (str, int, float)):
                    items[f"{k}[{i}]"] = str(item)
        else:
            items[k] = str(v)
    return items
