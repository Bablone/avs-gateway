"""
openclaw_adapter.py -- Adapter for OpenClaw framework.

Normalizes OpenClaw tool calls to ActionRequests and
converts AVS decisions back to OpenClaw responses.
"""

from typing import Any, Optional, Dict, List
import logging

from avs_gateway.adapters.base_adapter import BaseAdapter
from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    create_action_request,
)
from avs_gateway.core.gateway_core import Decision

logger = logging.getLogger("avs_gateway.adapters.openclaw")


class OpenClawAdapter(BaseAdapter):
    """Adapter for the OpenClaw framework.

    Converts OpenClaw tool call dictionaries into canonical ActionRequest
    objects and converts AVS Gateway Decisions back to OpenClaw response
    dictionaries.

    Expected OpenClaw action format::
        {
            "tool_name": "file_tool",
            "operation": "read",
            "parameters": {"path": "/tmp/test.txt"},
            "agent_id": "agent_001",
            "action_type": "file",  # optional, defaults to "file"
            "context": {"permission_level": "user"},  # optional
            "session_id": "session_123",  # optional
            "agent_version": "1.0.0",  # optional
        }

    OpenClaw response format::
        {
            "decision": "allow",
            "decision_type": "allow",
            "reason": "Policy allowed: ...",
            "risk_score": 25,
            "trust_score": 50,
            "matched_policy": "file_read",
            "is_blocking": false,
            "requires_human": false,
            "tool_result": {...},  # if provided
        }
    """

    def get_name(self) -> str:
        """Return the adapter name.

        Returns:
            The string "openclaw".
        """
        return "openclaw"

    def normalize(self, raw_action: Dict[str, Any]) -> ActionRequest:
        """Convert an OpenClaw tool call dict to a canonical ActionRequest.

        Extracts the tool name, operation, parameters, agent_id, and other
        fields from the OpenClaw action dictionary and maps the action type
        to the corresponding ActionType enum.

        Args:
            raw_action: OpenClaw action dictionary with keys like tool_name,
                        operation, parameters, agent_id, etc.

        Returns:
            A fully populated ActionRequest.

        Raises:
            ValueError: If required fields are missing or action_type is invalid.
        """
        if not isinstance(raw_action, dict):
            raise ValueError(
                f"OpenClaw action must be a dict, got {type(raw_action).__name__}"
            )

        # Extract required fields
        tool_name: str = raw_action.get("tool_name", "")
        operation: str = raw_action.get("operation", "")
        parameters: Dict[str, Any] = raw_action.get("parameters", {})
        agent_id: str = raw_action.get("agent_id", "")

        if not tool_name:
            raise ValueError("OpenClaw action missing required field: 'tool_name'")
        if not operation:
            raise ValueError("OpenClaw action missing required field: 'operation'")
        if not agent_id:
            raise ValueError("OpenClaw action missing required field: 'agent_id'")

        # Map OpenClaw action type to ActionType enum
        action_type_str: str = raw_action.get("action_type", "file")
        try:
            action_type = ActionType(action_type_str.lower())
        except ValueError:
            valid_types = [at.value for at in ActionType]
            raise ValueError(
                f"Invalid action_type '{action_type_str}' for OpenClaw. "
                f"Valid values: {valid_types}"
            )

        # Optional fields
        context: Dict[str, Any] = raw_action.get("context", {})
        session_id: Optional[str] = raw_action.get("session_id")
        agent_version: Optional[str] = raw_action.get("agent_version")

        action_request = create_action_request(
            agent_id=agent_id,
            action_type=action_type,
            tool_name=tool_name,
            operation=operation,
            parameters=parameters if parameters else {},
            context=context if context else {},
            session_id=session_id,
            agent_version=agent_version,
        )

        logger.debug(
            "Normalized OpenClaw action to ActionRequest: %s", action_request.action_id
        )
        return action_request

    def forward(
        self, decision: Decision, tool_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Convert an AVS Gateway Decision to an OpenClaw response dict.

        Args:
            decision: The Decision from Gateway.intercept().
            tool_result: Optional tool execution result to include.

        Returns:
            An OpenClaw response dictionary with decision details.
        """
        response: Dict[str, Any] = {
            "decision": decision.decision_type.value,
            "decision_type": decision.decision_type.value,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "trust_score": decision.trust_score,
            "matched_policy": decision.matched_policy,
            "is_blocking": decision.is_blocking(),
            "requires_human": decision.requires_human(),
            "timestamp_ns": decision.timestamp_ns,
        }

        if tool_result is not None:
            if hasattr(tool_result, "to_dict"):
                response["tool_result"] = tool_result.to_dict()
            else:
                response["tool_result"] = tool_result

        logger.debug(
            "Forwarded Decision to OpenClaw response: %s", decision.decision_type.value
        )
        return response

    def is_supported(self, action_type: str) -> bool:
        """Check if this adapter supports the given action type.

        OpenClaw supports all action types defined in the ActionType enum.

        Args:
            action_type: The action type string to check.

        Returns:
            True if the action type is supported, False otherwise.
        """
        try:
            ActionType(action_type.lower())
            return True
        except ValueError:
            return False
