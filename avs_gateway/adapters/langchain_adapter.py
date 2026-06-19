"""
langchain_adapter.py -- LangChain Tool Adapter for AVS Gateway v0.3.3-beta.

Wraps LangChain BaseTool objects with AVS governance, intercepting tool
execution at the BaseTool layer. The LLM sees the original tool's schema;
AVS controls whether the tool actually executes.

Architecture:
    LangChain Agent decides tool call
        ↓
    AVSGovernedTool._run() intercepts
        ↓
    AVS Gateway.intercept(ActionRequest) → Decision
        ↓
    ALLOW → wrapped tool executes, receipt recorded
    DENY / QUARANTINE / REQUIRE_APPROVAL → tool blocked, structured error returned
        ↓
    LangChain receives result or block message
        ↓
    AVS audit evidence retained

Usage:
    from avs_gateway.adapters.langchain_adapter import govern_langchain_tool

    governed_search = govern_langchain_tool(
        tool=original_search_tool,
        gateway=gateway,
        action_type=ActionType.API,
        operation="GET",
        agent_id="my_agent",
    )

    # Pass governed_search to LangChain agent — AVS controls execution

LangChain is an OPTIONAL dependency. If not installed, helper functions
raise ImportError with clear installation instructions.
"""

import functools
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger("avs_gateway.adapters.langchain")

# ---------------------------------------------------------------------------
# Optional dependency: langchain-core
# ---------------------------------------------------------------------------

try:
    from langchain_core.tools import BaseTool
    from langchain_core.callbacks import CallbackManagerForToolRun

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = None  # type: ignore[misc,assignment]
    CallbackManagerForToolRun = None  # type: ignore[misc,assignment]

# AVS imports (always available)
from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    create_action_request,
)
from avs_gateway.core.gateway_core import DecisionType, Gateway


# ---------------------------------------------------------------------------
# Stubs when LangChain is not installed
# ---------------------------------------------------------------------------

if not LANGCHAIN_AVAILABLE:

    def govern_langchain_tool(*args, **kwargs) -> Any:
        """Stub: raises ImportError with installation instructions."""
        raise ImportError(
            "LangChain is required to use the AVS LangChain adapter.\n"
            "Install with:  pip install -r requirements-langchain.txt\n"
            "Or:           pip install langchain-core langchain"
        )

    def govern_langchain_tools(*args, **kwargs) -> List[Any]:
        """Stub: raises ImportError with installation instructions."""
        raise ImportError(
            "LangChain is required to use the AVS LangChain adapter.\n"
            "Install with:  pip install -r requirements-langchain.txt\n"
            "Or:           pip install langchain-core langchain"
        )

    # Expose availability flag for conditional logic
    __all__ = [
        "govern_langchain_tool",
        "govern_langchain_tools",
        "LANGCHAIN_AVAILABLE",
    ]

else:
    # LangChain IS available — full implementation

    # -----------------------------------------------------------------------
    # AVSGovernedTool
    # -----------------------------------------------------------------------

    class AVSGovernedTool(BaseTool):
        """LangChain BaseTool wrapper that routes execution through AVS Gateway.

        Preserves the original tool's identity (name, description, args_schema)
        so the LLM can still decide when to invoke it. Execution is intercepted
        and governed by AVS.

        Attributes:
            wrapped_tool: The original LangChain BaseTool being governed.
            gateway: The AVS Gateway instance that makes decisions.
            action_type: AVS ActionType for policy routing.
            operation: Operation string for AVS (e.g., "read", "GET").
            agent_id: Identifier for the governing agent.
            context: Additional context passed to AVS policies.
        """

        wrapped_tool: BaseTool
        gateway: Gateway
        action_type: ActionType
        operation: str
        agent_id: str
        context: Optional[Dict[str, Any]]

        def __init__(
            self,
            wrapped_tool: BaseTool,
            gateway: Gateway,
            action_type: ActionType,
            operation: str,
            agent_id: str = "langchain_agent",
            context: Optional[Dict[str, Any]] = None,
        ) -> None:
            """Initialize AVSGovernedTool wrapping an existing LangChain tool.

            Args:
                wrapped_tool: The LangChain tool to govern.
                gateway: AVS Gateway instance for decision-making.
                action_type: AVS action type (e.g., ActionType.FILE).
                operation: Operation string (e.g., "read", "GET", "delete").
                agent_id: Agent identifier for AVS trust tracking.
                context: Optional extra context for policy evaluation.
            """
            # Preserve original tool's identity for the LLM
            super().__init__(
                name=wrapped_tool.name,
                description=wrapped_tool.description,
                args_schema=wrapped_tool.args_schema,
                return_direct=wrapped_tool.return_direct,
                verbose=wrapped_tool.verbose,
                callbacks=wrapped_tool.callbacks,
                tags=wrapped_tool.tags,
                metadata=wrapped_tool.metadata,
            )
            self.wrapped_tool = wrapped_tool
            self.gateway = gateway
            self.action_type = action_type
            self.operation = operation
            self.agent_id = agent_id
            self.context = context or {}

        # -- LangChain BaseTool interface ----------------------------------

        def _run(
            self,
            *args: Any,
            run_manager: Optional[Any] = None,
            **kwargs: Any,
        ) -> str:
            """Synchronous execution — intercepted by AVS.

            Flow:
                1. Build ActionRequest from tool call
                2. Gateway.intercept() → Decision
                3. ALLOW: execute wrapped tool, record receipt
                4. DENY/QUARANTINE/REQUIRE_APPROVAL: block, return error
            """
            return self._governed_execute(sync=True, *args, **kwargs)

        async def _arun(
            self,
            *args: Any,
            run_manager: Optional[Any] = None,
            **kwargs: Any,
        ) -> str:
            """Asynchronous execution — delegated to sync for v0.3.3."""
            # v0.3.3: async not yet supported. Return clear message.
            return (
                "[AVS] Async tool execution is not supported in v0.3.3. "
                "Use synchronous tools or upgrade to a future AVS version."
            )

        # -- Core governance logic -----------------------------------------

        def _governed_execute(
            self, sync: bool = True, *args: Any, **kwargs: Any
        ) -> str:
            """Execute tool through AVS governance layer.

            Args:
                sync: True for sync execution, False for async.
                *args: Positional args from LangChain.
                **kwargs: Keyword args from LangChain.

            Returns:
                Tool result (if allowed) or structured AVS block message.
            """
            # 1. Serialize tool input for ActionRequest
            tool_input = self._serialize_input(args, kwargs)

            # 2. Build ActionRequest
            action = create_action_request(
                agent_id=self.agent_id,
                action_type=self.action_type,
                tool_name=self.wrapped_tool.name,
                operation=self.operation,
                parameters={"tool_input": tool_input},
                context={
                    **self.context,
                    "langchain_tool": True,
                    "tool_description": self.wrapped_tool.description or "",
                    "sync": sync,
                },
            )

            # 3. Submit to AVS Gateway
            try:
                decision = self.gateway.intercept(action)
            except Exception as exc:
                logger.error("Gateway intercept failed: %s", exc)
                return self._format_error(
                    "Gateway intercept error", str(exc), receipt=None
                )

            # 4. Handle decision
            if decision.decision_type == DecisionType.ALLOW:
                return self._execute_allowed(action, decision, *args, **kwargs)
            elif decision.decision_type == DecisionType.DENY:
                return self._format_blocked(
                    "DENY", decision.reason, action, decision
                )
            elif decision.decision_type == DecisionType.QUARANTINE:
                return self._format_blocked(
                    "QUARANTINE", decision.reason, action, decision
                )
            elif decision.decision_type == DecisionType.REQUIRE_APPROVAL:
                return self._format_pending(decision, action)
            else:
                return self._format_error(
                    f"Unknown decision: {decision.decision_type}",
                    "AVS returned an unrecognized decision type",
                    receipt=None,
                )

        def _execute_allowed(
            self,
            action: ActionRequest,
            decision: Any,
            *args: Any,
            **kwargs: Any,
        ) -> str:
            """Execute the wrapped tool and record evidence."""
            try:
                # Execute the real tool
                result = self.wrapped_tool._run(*args, **kwargs)
                result_str = str(result) if result is not None else ""

                # Record receipt for audit
                try:
                    receipt = self.gateway.record(action, decision)
                    logger.debug(
                        "Tool %s executed. Receipt: %s",
                        self.wrapped_tool.name,
                        receipt.receipt_hash[:16] if receipt else "N/A",
                    )
                except Exception as exc:
                    logger.warning("Receipt recording failed: %s", exc)

                return result_str

            except Exception as exc:
                logger.error(
                    "Wrapped tool %s raised: %s", self.wrapped_tool.name, exc
                )
                return self._format_error(
                    f"Tool '{self.wrapped_tool.name}' execution failed",
                    str(exc),
                    receipt=None,
                )

        # -- Response formatting -------------------------------------------

        @staticmethod
        def _serialize_input(args: tuple, kwargs: dict) -> str:
            """Serialize tool input to a string for AVS ActionRequest."""
            if kwargs and args:
                return json.dumps({"args": list(args), "kwargs": kwargs}, default=str)
            elif kwargs:
                return json.dumps(kwargs, default=str)
            elif args:
                if len(args) == 1:
                    return str(args[0])
                return json.dumps(list(args), default=str)
            return ""

        def _format_blocked(
            self,
            block_type: str,
            reason: str,
            action: ActionRequest,
            decision: Any,
        ) -> str:
            """Format a structured block message for the LLM agent."""
            receipt_hash = ""
            try:
                receipt = self.gateway.record(action, decision)
                receipt_hash = receipt.receipt_hash[:24] if receipt else ""
            except Exception:
                pass

            return (
                f"[AVS {block_type}] Tool '{self.wrapped_tool.name}' was blocked.\n"
                f"Reason: {reason}\n"
                f"Receipt: {receipt_hash}\n"
                f"You do not have permission to execute this action. "
                f"Consider using a different tool or asking for assistance."
            )

        def _format_pending(self, decision: Any, action: ActionRequest) -> str:
            """Format a pending/approval-required message for the LLM agent."""
            receipt_hash = ""
            try:
                receipt = self.gateway.record(action, decision)
                receipt_hash = receipt.receipt_hash[:24] if receipt else ""
            except Exception:
                pass

            return (
                f"[AVS PENDING] Tool '{self.wrapped_tool.name}' requires human approval.\n"
                f"Reason: {decision.reason}\n"
                f"Receipt: {receipt_hash}\n"
                f"This action has been queued for review. "
                f"You cannot proceed until it is approved."
            )

        @staticmethod
        def _format_error(title: str, detail: str, receipt: Any = None) -> str:
            """Format an unexpected error message."""
            rh = receipt.receipt_hash[:24] if receipt else "N/A"
            return (
                f"[AVS ERROR] {title}.\n"
                f"Detail: {detail}\n"
                f"Receipt: {rh}\n"
                f"The action could not be completed due to an internal error."
            )

    # -----------------------------------------------------------------------
    # Helper functions
    # -----------------------------------------------------------------------

    def govern_langchain_tool(
        tool: BaseTool,
        gateway: Gateway,
        action_type: ActionType,
        operation: str,
        agent_id: str = "langchain_agent",
        context: Optional[Dict[str, Any]] = None,
    ) -> AVSGovernedTool:
        """Wrap a single LangChain tool with AVS governance.

        This is the primary API for LangChain integration.

        Args:
            tool: LangChain BaseTool to wrap.
            gateway: AVS Gateway instance for decision-making.
            action_type: AVS action type (e.g., ActionType.FILE, ActionType.API).
            operation: Operation string (e.g., "read", "GET", "delete").
            agent_id: Agent identifier for AVS trust tracking.
            context: Optional extra context for policy evaluation.

        Returns:
            AVSGovernedTool that wraps the original tool.

        Example:
            >>> governed_search = govern_langchain_tool(
            ...     tool=search_tool,
            ...     gateway=gateway,
            ...     action_type=ActionType.API,
            ...     operation="GET",
            ... )
        """
        return AVSGovernedTool(
            wrapped_tool=tool,
            gateway=gateway,
            action_type=action_type,
            operation=operation,
            agent_id=agent_id,
            context=context,
        )

    def govern_langchain_tools(
        tools: List[BaseTool],
        gateway: Gateway,
        action_type: ActionType,
        operation: str = "execute",
        agent_id: str = "langchain_agent",
        context: Optional[Dict[str, Any]] = None,
    ) -> List[AVSGovernedTool]:
        """Batch-wrap multiple LangChain tools with AVS governance.

        All tools share the same action_type and operation. For per-tool
        configuration, call govern_langchain_tool() individually.

        Args:
            tools: List of LangChain BaseTools to wrap.
            gateway: AVS Gateway instance.
            action_type: Shared AVS action type for all tools.
            operation: Shared operation string (default: "execute").
            agent_id: Agent identifier.
            context: Optional shared context.

        Returns:
            List of AVSGovernedTool instances.
        """
        return [
            govern_langchain_tool(
                tool=t,
                gateway=gateway,
                action_type=action_type,
                operation=operation,
                agent_id=agent_id,
                context=context,
            )
            for t in tools
        ]

    __all__ = [
        "AVSGovernedTool",
        "govern_langchain_tool",
        "govern_langchain_tools",
        "LANGCHAIN_AVAILABLE",
    ]
