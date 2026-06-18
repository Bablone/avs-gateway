"""
action_request.py -- Canonical action representation.

All adapter outputs convert to ActionRequest before reaching the Gateway.
Immutable, hashable, serializable.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import hashlib
import json
import time
import uuid


class ActionType(Enum):
    """Enumeration of supported action types in the AVS Gateway."""

    FILE = "file"
    EMAIL = "email"
    API = "api"
    PAYMENT = "payment"
    DATABASE = "database"
    SECURITY_SCAN = "security_scan"


class FileOperation(Enum):
    """Enumeration of supported file operations."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    APPEND = "append"


class EmailOperation(Enum):
    """Enumeration of supported email operations."""

    SEND = "send"
    READ = "read"
    DELETE = "delete"


class APIOperation(Enum):
    """Enumeration of supported API HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class PaymentOperation(Enum):
    """Enumeration of supported payment operations."""

    TRANSFER = "transfer"
    REFUND = "refund"
    QUERY = "query"


class DatabaseOperation(Enum):
    """Enumeration of supported database SQL operations."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DROP = "DROP"


class SecurityScanOperation(Enum):
    """Enumeration of supported security scan operations."""

    RUN_SCAN = "run_scan"
    ACCESS_RESULTS = "access_results"


@dataclass(frozen=True)
class ActionRequest:
    """
    Canonical representation of an action request in the AVS Gateway.

    ActionRequest is the unified data structure that all adapter outputs
    are converted to before reaching the Gateway. It is immutable,
    hashable, and fully serializable to/from JSON.

    Attributes:
        agent_id: Unique identifier of the agent making the request.
        action_type: The category of action (file, email, api, etc.).
        tool_name: Name of the specific tool being invoked.
        operation: The operation being performed (e.g., "read", "POST").
        parameters: Dictionary of tool-specific parameters.
        context: Additional context about the execution environment.
        action_id: Unique identifier for this specific action request.
        agent_version: Version string of the agent software.
        timestamp_ns: Timestamp in nanoseconds since epoch.
        session_id: Optional session identifier for request grouping.
        parent_action_id: Optional reference to a parent action.
    """

    agent_id: str
    action_type: ActionType
    tool_name: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_version: Optional[str] = None
    timestamp_ns: int = field(default_factory=time.time_ns)
    session_id: Optional[str] = None
    parent_action_id: Optional[str] = None

    def validate(self) -> bool:
        """
        Validate that all required fields are present and of correct type.

        Returns:
            True if the action request is valid, False otherwise.
        """
        if not isinstance(self.action_id, str) or not self.action_id:
            return False
        if not isinstance(self.agent_id, str) or not self.agent_id:
            return False
        if not isinstance(self.action_type, ActionType):
            return False
        if not isinstance(self.tool_name, str) or not self.tool_name:
            return False
        if not isinstance(self.operation, str) or not self.operation:
            return False
        if not isinstance(self.parameters, dict):
            return False
        if not isinstance(self.timestamp_ns, int) or self.timestamp_ns <= 0:
            return False
        return True

    def validate_operation(self) -> bool:
        """
        Validate that the operation is allowed for the given action type.

        Returns:
            True if the operation is valid for the action type, False otherwise.
        """
        op_map = {
            ActionType.FILE: [e.value for e in FileOperation],
            ActionType.EMAIL: [e.value for e in EmailOperation],
            ActionType.API: [e.value for e in APIOperation],
            ActionType.PAYMENT: [e.value for e in PaymentOperation],
            ActionType.DATABASE: [e.value for e in DatabaseOperation],
            ActionType.SECURITY_SCAN: [e.value for e in SecurityScanOperation],
        }
        allowed = op_map.get(self.action_type, [])
        return self.operation in allowed

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the ActionRequest to a dictionary.

        Returns:
            Dictionary representation with enum values as strings.
        """
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "action_type": self.action_type.value,
            "tool_name": self.tool_name,
            "operation": self.operation,
            "parameters": self.parameters,
            "context": self.context,
            "timestamp_ns": self.timestamp_ns,
            "session_id": self.session_id,
            "parent_action_id": self.parent_action_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionRequest":
        """
        Deserialize an ActionRequest from a dictionary.

        Args:
            data: Dictionary containing the action request data.

        Returns:
            A new ActionRequest instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If action_type is not a valid ActionType.
        """
        return cls(
            action_id=data["action_id"],
            agent_id=data["agent_id"],
            agent_version=data.get("agent_version"),
            action_type=ActionType(data["action_type"]),
            tool_name=data["tool_name"],
            operation=data["operation"],
            parameters=data.get("parameters", {}),
            context=data.get("context", {}),
            timestamp_ns=data["timestamp_ns"],
            session_id=data.get("session_id"),
            parent_action_id=data.get("parent_action_id"),
        )

    def to_json(self) -> str:
        """
        Serialize the ActionRequest to a JSON string.

        Returns:
            Canonical JSON string with sorted keys.
        """
        return json.dumps(self.to_dict(), sort_keys=True, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "ActionRequest":
        """
        Deserialize an ActionRequest from a JSON string.

        Args:
            json_str: JSON string containing the action request data.

        Returns:
            A new ActionRequest instance.
        """
        return cls.from_dict(json.loads(json_str))

    def action_hash(self) -> str:
        """
        Compute a SHA-256 hash of the canonical JSON representation.

        Returns:
            Hex digest of the SHA-256 hash.
        """
        canonical = self.to_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __hash__(self) -> int:
        """
        Compute the hash value for use in sets and dicts.

        Returns:
            Integer hash based on the action hash.
        """
        return hash(self.action_hash())


def create_action_request(
    agent_id: str,
    action_type: ActionType,
    tool_name: str,
    operation: str,
    parameters: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    agent_version: Optional[str] = None,
) -> ActionRequest:
    """
    Factory function to create an ActionRequest with sensible defaults.

    Args:
        agent_id: Unique identifier of the agent.
        action_type: The category of action.
        tool_name: Name of the tool being invoked.
        operation: The operation being performed.
        parameters: Optional dictionary of tool-specific parameters.
        context: Optional dictionary of execution context.
        session_id: Optional session identifier.
        agent_version: Optional agent version string.

    Returns:
        A new ActionRequest instance.
    """
    return ActionRequest(
        agent_id=agent_id,
        action_type=action_type,
        tool_name=tool_name,
        operation=operation,
        parameters=parameters or {},
        context=context or {},
        session_id=session_id,
        agent_version=agent_version,
    )

