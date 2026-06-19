"""
governed.py -- Framework-agnostic @governed_tool decorator for AVS Gateway v0.3.1-beta.

Turns any Python function into an AVS-governed tool:

    @governed_tool(
        tool_name="file_write",
        action_type=ActionType.FILE,
        operation="write",
    )
    def write_file(path: str, content: str):
        ...

AVS intercepts every call, decides allow/deny/approval/quarantine,
and only executes the function on ALLOW.

No LangChain. No CrewAI. No framework dependency.
Just a decorator around ordinary Python functions.
"""

import functools
import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    create_action_request,
)
from avs_gateway.core.gateway_core import Gateway

logger = logging.getLogger("avs_gateway.adapters.governed")


@dataclass(frozen=True)
class GovernedResult:
    """Result from a governed tool execution.

    Contains everything a developer needs:
    - Whether the function executed
    - The AVS decision and reason
    - The function result (if executed)
    - Receipt hash for audit
    """
    executed: bool
    decision: str           # "allow", "deny", "require_approval", "quarantine"
    reason: str
    risk_score: int
    trust_score: int
    function_result: Any = None
    function_error: Optional[str] = None
    receipt_hash: Optional[str] = None
    agent_id: str = "governed_agent"
    tool_name: str = ""
    operation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executed": self.executed,
            "decision": self.decision,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "trust_score": self.trust_score,
            "function_result": self.function_result,
            "function_error": self.function_error,
            "receipt_hash": self.receipt_hash,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "operation": self.operation,
            "latency_ms": round(self.latency_ms, 3),
        }


def governed_tool(
    tool_name: str,
    action_type: ActionType,
    operation: str,
    gateway: Optional[Gateway] = None,
    agent_id: str = "governed_agent",
    policy_context: Optional[Dict[str, Any]] = None,
    parameter_map: Optional[Dict[str, str]] = None,
):
    """Decorator that AVS-governs an ordinary Python function.

    The function is only executed if AVS returns ALLOW.
    On DENY/QUARANTINE/REQUIRE_APPROVAL, a structured
    GovernedResult is returned without calling the function.

    Args:
        tool_name: Semantic tool name (e.g., "file_write", "api_call").
        action_type: ActionType enum value (e.g., ActionType.FILE).
        operation: Operation string (e.g., "write", "read").
        gateway: Gateway instance. If None, uses a lazily-created default.
        agent_id: Identifier for the governed agent.
        policy_context: Extra context passed to the Gateway (permissions, etc.)
        parameter_map: Maps function arg names to ActionRequest parameter keys.
                       e.g., {"path": "target_path"} renames the arg.

    Returns:
        Decorated function that returns GovernedResult.

    Example:
        @governed_tool(
            tool_name="file_write",
            action_type=ActionType.FILE,
            operation="write",
        )
        def write_file(path: str, content: str):
            with open(path, "w") as f:
                f.write(content)
            return {"bytes_written": len(content)}

        result = write_file("sandbox/output.txt", "hello")
        # result.executed = True/False
        # result.decision = "allow" / "deny"
        # result.function_result = {"bytes_written": 5}  (if executed)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> GovernedResult:
            start_ms = time.time() * 1000.0

            # Resolve Gateway (default or provided)
            gw = gateway or _default_gateway()

            # Build parameters from function call
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            params: Dict[str, Any] = {}
            for name, value in bound.arguments.items():
                key = parameter_map.get(name, name) if parameter_map else name
                params[key] = value

            # Build ActionRequest
            action = create_action_request(
                agent_id=agent_id,
                action_type=action_type,
                tool_name=tool_name,
                operation=operation,
                parameters=params,
                context=policy_context or {},
            )

            # AVS intercept
            try:
                decision = gw.intercept(action)
            except Exception as exc:
                logger.error("Gateway intercept failed: %s", exc)
                latency = time.time() * 1000.0 - start_ms
                return GovernedResult(
                    executed=False,
                    decision="deny",
                    reason=f"Gateway intercept exception: {exc}",
                    risk_score=100,
                    trust_score=0,
                    function_error=str(exc),
                    tool_name=tool_name,
                    operation=operation,
                    latency_ms=latency,
                )

            latency = time.time() * 1000.0 - start_ms

            # If not ALLOW, return blocked result without executing
            if decision.decision_type.value != "allow":
                logger.info(
                    "Governed tool %s.%s -> %s (not executing)",
                    tool_name, operation, decision.decision_type.value,
                )
                return GovernedResult(
                    executed=False,
                    decision=decision.decision_type.value,
                    reason=decision.reason,
                    risk_score=decision.risk_score,
                    trust_score=decision.trust_score,
                    tool_name=tool_name,
                    operation=operation,
                    latency_ms=latency,
                )

            # ALLOW -> execute the wrapped function
            func_result = None
            func_error = None
            try:
                func_result = func(*args, **kwargs)
            except Exception as exc:
                func_error = str(exc)
                logger.error("Governed function %s raised: %s", func.__name__, exc)

            # Generate receipt
            receipt = None
            try:
                receipt = gw.record(action, decision)
            except Exception as exc:
                logger.warning("Receipt generation failed: %s", exc)

            return GovernedResult(
                executed=True,
                decision="allow",
                reason=decision.reason,
                risk_score=decision.risk_score,
                trust_score=decision.trust_score,
                function_result=func_result,
                function_error=func_error,
                receipt_hash=receipt.receipt_hash if receipt else None,
                tool_name=tool_name,
                operation=operation,
                latency_ms=latency,
            )

        # Attach metadata for introspection
        wrapper._avs_governed = True  # type: ignore
        wrapper._avs_tool_name = tool_name  # type: ignore
        wrapper._avs_action_type = action_type  # type: ignore
        wrapper._avs_operation = operation  # type: ignore

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Default gateway singleton (lazy creation)
# ---------------------------------------------------------------------------

_default_gateway_instance: Optional[Gateway] = None


def _default_gateway() -> Gateway:
    """Create or return a default Gateway with standard policies."""
    global _default_gateway_instance
    if _default_gateway_instance is None:
        from avs_gateway.core.policy_engine import PolicyEngine
        from avs_gateway.core.risk_engine import RiskEngine
        from avs_gateway.core.trust_memory import TrustMemory
        from avs_gateway.core.receipt_generator import ReceiptGenerator
        from avs_gateway.core.audit_chain import AuditChain

        pe = PolicyEngine()
        try:
            pe.load_policies("avs_gateway/config/default_policies.yaml")
        except FileNotFoundError:
            logger.warning("Default policies not found, using empty policy set")

        _default_gateway_instance = Gateway(
            policy_engine=pe,
            risk_engine=RiskEngine(),
            trust_memory=TrustMemory(),
            receipt_generator=ReceiptGenerator(),
            audit_chain=AuditChain(),
        )
        logger.info("Default Gateway created for @governed_tool")

    return _default_gateway_instance


def set_default_gateway(gateway: Gateway) -> None:
    """Set the global default Gateway used by @governed_tool decorators.

    Call this at app startup to configure the Gateway once,
    then all @governed_tool decorators use it automatically.
    """
    global _default_gateway_instance
    _default_gateway_instance = gateway
    logger.info("Default Gateway set explicitly")


def is_governed(func: Callable) -> bool:
    """Check if a function is AVS-governed."""
    return getattr(func, "_avs_governed", False)


def get_governed_metadata(func: Callable) -> Optional[Dict[str, Any]]:
    """Return AVS metadata for a governed function, or None."""
    if not is_governed(func):
        return None
    return {
        "tool_name": getattr(func, "_avs_tool_name", None),
        "action_type": getattr(func, "_avs_action_type", None),
        "operation": getattr(func, "_avs_operation", None),
    }
