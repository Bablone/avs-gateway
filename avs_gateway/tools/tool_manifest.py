"""
tool_manifest.py — Tool Manifest Integrity.

Turns tool names into registered, attestable execution surfaces.

A Tool Manifest describes a tool that has been registered with AVS,
including metadata about where it lives, who registered it, and
best-effort integrity hashes.

v0.3.6: Registration and metadata only.
v0.4.1: Tamper detection and enforcement.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable
import hashlib
import inspect
import time
import uuid
import logging

logger = logging.getLogger("avs_gateway.tools.tool_manifest")


@dataclass(frozen=True)
class ToolManifest:
    """A registered tool manifest.

    Describes a tool that has been registered with AVS for governance.
    Contains metadata and best-effort integrity hashes (informational
    in v0.3.6, enforced in v0.4.1).
    """

    tool_name: str
    tool_type: str = "python_function"   # "python_function" | "langchain_tool" | "api_endpoint" | "sandboxed"
    module_path: str = ""
    function_name: str = ""
    source_hash: Optional[str] = None       # Best-effort SHA-256 of source (informational)
    bytecode_hash: Optional[str] = None     # Best-effort SHA-256 of bytecode (informational)
    dependency_lock_hash: Optional[str] = None  # Package lock hash (optional)
    registered_at: str = ""
    registered_by: str = ""
    policy_binding: Optional[str] = None    # Policy set bound to this tool
    allowed_operations: list = field(default_factory=list)
    risk_class: str = "standard"            # "low" | "standard" | "elevated" | "critical"

    def manifest_hash(self) -> str:
        """Return ``sha256:<hex>`` of the canonical manifest content.

        This hash covers the metadata fields (name, module, function,
        registered_at, registered_by, policy_binding) but NOT the
        best-effort source/bytecode hashes (which may vary across
        Python versions and installations).
        """
        import json
        payload = {
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "module_path": self.module_path,
            "function_name": self.function_name,
            "dependency_lock_hash": self.dependency_lock_hash,
            "registered_at": self.registered_at,
            "registered_by": self.registered_by,
            "policy_binding": self.policy_binding,
            "allowed_operations": sorted(self.allowed_operations),
            "risk_class": self.risk_class,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "module_path": self.module_path,
            "function_name": self.function_name,
            "source_hash": self.source_hash,
            "bytecode_hash": self.bytecode_hash,
            "dependency_lock_hash": self.dependency_lock_hash,
            "registered_at": self.registered_at,
            "registered_by": self.registered_by,
            "policy_binding": self.policy_binding,
            "allowed_operations": list(self.allowed_operations),
            "risk_class": self.risk_class,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolManifest":
        """Reconstruct from dictionary."""
        return cls(
            tool_name=data["tool_name"],
            tool_type=data.get("tool_type", "python_function"),
            module_path=data.get("module_path", ""),
            function_name=data.get("function_name", ""),
            source_hash=data.get("source_hash"),
            bytecode_hash=data.get("bytecode_hash"),
            dependency_lock_hash=data.get("dependency_lock_hash"),
            registered_at=data.get("registered_at", ""),
            registered_by=data.get("registered_by", ""),
            policy_binding=data.get("policy_binding"),
            allowed_operations=data.get("allowed_operations", []),
            risk_class=data.get("risk_class", "standard"),
        )


def _best_effort_source_hash(func: Callable) -> Optional[str]:
    """Best-effort SHA-256 of a function's source code.

    Returns None if source cannot be extracted (C extensions,
    dynamically created functions, decorated wrappers, etc.).

    This is INFORMATIONAL only — not a security guarantee.
    """
    try:
        source = inspect.getsource(func)
        # Basic canonicalisation: strip whitespace, remove comments
        lines = []
        for line in source.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
        clean = "\n".join(lines)
        return "sha256:" + hashlib.sha256(clean.encode("utf-8")).hexdigest()
    except (OSError, TypeError, AttributeError) as exc:
        logger.debug("Cannot extract source for %s: %s", getattr(func, "__name__", "<unknown>"), exc)
        return None


def _best_effort_bytecode_hash(func: Callable) -> Optional[str]:
    """Best-effort SHA-256 of a function's bytecode.

    Returns None if bytecode is not available.

    This is INFORMATIONAL only — bytecode changes between Python versions.
    """
    try:
        code = func.__code__.co_code
        return "sha256:" + hashlib.sha256(code).hexdigest()
    except (AttributeError, TypeError) as exc:
        logger.debug("Cannot extract bytecode for %s: %s", getattr(func, "__name__", "<unknown>"), exc)
        return None


def register_tool(
    func: Callable,
    tool_name: Optional[str] = None,
    tool_type: str = "python_function",
    registered_by: str = "system",
    policy_binding: Optional[str] = None,
    allowed_operations: Optional[list] = None,
    risk_class: str = "standard",
) -> ToolManifest:
    """Register a Python function as an AVS-governed tool.

    Creates a ToolManifest with best-effort integrity hashes.
    The manifest can be referenced in ASR-1 receipts.

    Args:
        func: The Python function to register.
        tool_name: Override name (defaults to function name).
        tool_type: Tool classification.
        registered_by: Who/what registered the tool.
        policy_binding: Policy set to bind to this tool.
        allowed_operations: List of permitted operations.
        risk_class: Risk classification.

    Returns:
        A ToolManifest describing the registered tool.
    """
    name = tool_name or getattr(func, "__name__", "unknown")
    module = getattr(func, "__module__", "")
    func_name = getattr(func, "__name__", "")

    # Best-effort hashes (informational)
    src_hash = _best_effort_source_hash(func)
    bc_hash = _best_effort_bytecode_hash(func)

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    manifest = ToolManifest(
        tool_name=name,
        tool_type=tool_type,
        module_path=module,
        function_name=func_name,
        source_hash=src_hash,
        bytecode_hash=bc_hash,
        registered_at=now,
        registered_by=registered_by,
        policy_binding=policy_binding,
        allowed_operations=allowed_operations or [],
        risk_class=risk_class,
    )

    logger.debug(
        "Registered tool %s (module=%s, source_hash=%s, manifest_hash=%s)",
        name, module, src_hash is not None, manifest.manifest_hash(),
    )
    return manifest
