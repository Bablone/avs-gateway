"""
base_adapter.py -- Abstract base class for framework adapters.

All adapters (OpenClaw, Cursor, OpenAI SDK, etc.) inherit from BaseAdapter.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List

from avs_gateway.models.action_request import ActionRequest
from avs_gateway.core.gateway_core import Decision


class BaseAdapter(ABC):
    """Abstract base class for all framework adapters.

    Adapters bridge between external AI agent frameworks and the AVS Gateway.
    They normalize framework-specific action representations into canonical
    ActionRequest objects and convert Gateway Decisions back to framework-
    specific response formats.

    Subclasses must implement:
      - normalize(): Convert framework action to canonical ActionRequest
      - forward(): Convert AVS Decision to framework response
      - get_name(): Return the adapter name string

    Attributes:
        None (pure interface).
    """

    @abstractmethod
    def normalize(self, raw_action: Any) -> ActionRequest:
        """Convert a framework-specific action into a canonical ActionRequest.

        This is the inbound conversion: the framework produces some representation
        of an action (e.g., a dict, a custom object, a tool call) and this method
        converts it into the Gateway's canonical ActionRequest format.

        Args:
            raw_action: The framework-specific action object. Type varies by adapter.

        Returns:
            A fully populated ActionRequest ready for Gateway.intercept().

        Raises:
            ValueError: If the raw_action cannot be normalized.
        """

    @abstractmethod
    def forward(self, decision: Decision, tool_result: Optional[Any] = None) -> Any:
        """Convert an AVS Gateway Decision into a framework-specific response.

        This is the outbound conversion: after the Gateway renders a decision,
        this method converts it into whatever format the calling framework
        expects (e.g., a dict, a custom response object).

        Args:
            decision: The Decision from Gateway.intercept().
            tool_result: Optional tool execution result to include in the response.

        Returns:
            A framework-specific response object.
        """

    @abstractmethod
    def get_name(self) -> str:
        """Return the human-readable adapter name.

        Returns:
            A string identifier for this adapter (e.g., "openclaw", "cursor").
        """

    def is_supported(self, action_type: str) -> bool:
        """Check whether this adapter supports the given action type.

        Override this method in subclasses to indicate which action types
        the adapter can handle. The default implementation returns True for
        all action types.

        Args:
            action_type: The action type string to check.

        Returns:
            True if this adapter supports the action type, False otherwise.
        """
        return True


class AdapterRegistry:
    """Registry for managing framework adapters.

    The AdapterRegistry provides a central place to register, retrieve,
    and list all available adapters. This enables dynamic adapter lookup
    based on framework name.

    Usage::
        registry = AdapterRegistry()
        registry.register(OpenClawAdapter())
        adapter = registry.get("openclaw")
        adapter_names = registry.list_adapters()
    """

    def __init__(self) -> None:
        """Initialize an empty adapter registry."""
        self._adapters: Dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        """Register an adapter in the registry.

        The adapter is keyed by its name (from get_name()). If an adapter
        with the same name is already registered, it will be overwritten.

        Args:
            adapter: The BaseAdapter instance to register.

        Raises:
            TypeError: If adapter is not a BaseAdapter subclass.
        """
        if not isinstance(adapter, BaseAdapter):
            raise TypeError(f"Expected BaseAdapter, got {type(adapter).__name__}")
        name = adapter.get_name()
        self._adapters[name] = adapter

    def get(self, name: str) -> Optional[BaseAdapter]:
        """Retrieve an adapter by name.

        Args:
            name: The adapter name to look up.

        Returns:
            The BaseAdapter if found, None otherwise.
        """
        return self._adapters.get(name)

    def list_adapters(self) -> List[str]:
        """List all registered adapter names.

        Returns:
            A list of registered adapter name strings.
        """
        return list(self._adapters.keys())

    def unregister(self, name: str) -> bool:
        """Remove an adapter from the registry.

        Args:
            name: The adapter name to remove.

        Returns:
            True if the adapter was found and removed, False otherwise.
        """
        if name in self._adapters:
            del self._adapters[name]
            return True
        return False

    def clear(self) -> None:
        """Remove all adapters from the registry."""
        self._adapters.clear()

    def __len__(self) -> int:
        """Return the number of registered adapters."""
        return len(self._adapters)

    def __contains__(self, name: str) -> bool:
        """Check if an adapter name is registered."""
        return name in self._adapters
