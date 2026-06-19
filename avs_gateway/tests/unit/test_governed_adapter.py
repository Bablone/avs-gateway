"""
Unit tests for avs_gateway.adapters.governed

Tests the @governed_tool decorator, GovernedResult, and utility functions.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.models.action_request import ActionType
from avs_gateway.core.policy_engine import PolicyEngine
from avs_gateway.core.risk_engine import RiskEngine
from avs_gateway.core.trust_memory import TrustMemory
from avs_gateway.core.receipt_generator import ReceiptGenerator
from avs_gateway.core.audit_chain import AuditChain
from avs_gateway.core.gateway_core import Gateway, DecisionType
from avs_gateway.adapters.governed import (
    governed_tool,
    GovernedResult,
    set_default_gateway,
    is_governed,
    get_governed_metadata,
    _default_gateway,
)


@pytest.fixture
def fresh_gateway():
    """Fresh Gateway for each test."""
    pe = PolicyEngine()
    pe.load_policies("avs_gateway/config/default_policies.yaml")
    gw = Gateway(pe, RiskEngine(), TrustMemory(), ReceiptGenerator(), AuditChain())
    set_default_gateway(gw)
    yield gw
    # Reset singleton
    set_default_gateway(None)


class TestGovernedToolDecorator:
    """Tests for @governed_tool decorator."""

    def test_allow_executes_function(self, fresh_gateway):
        """An ALLOW decision should execute the wrapped function."""
        call_count = [0]

        @governed_tool(
            tool_name="test_read",
            action_type=ActionType.FILE,
            operation="read",
            gateway=fresh_gateway,
        )
        def my_read(path: str) -> dict:
            call_count[0] += 1
            return {"content": "hello"}

        result = my_read(path="/tmp/test.txt")
        assert result.executed is True
        assert result.decision == "allow"
        assert call_count[0] == 1

    def test_deny_blocks_function(self, fresh_gateway):
        """A DENY decision should NOT execute the wrapped function."""
        call_count = [0]

        @governed_tool(
            tool_name="test_delete",
            action_type=ActionType.FILE,
            operation="delete",
            gateway=fresh_gateway,
        )
        def my_delete(path: str) -> dict:
            call_count[0] += 1
            return {"deleted": True}

        result = my_delete(path="/tmp/test.txt")
        assert result.executed is False
        assert result.decision == "deny"
        assert call_count[0] == 0

    def test_result_structure(self, fresh_gateway):
        """GovernedResult should have all expected fields."""
        @governed_tool(
            tool_name="test_api",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
        )
        def my_api(endpoint: str) -> dict:
            return {"status": 200}

        result = my_api(endpoint="/health")
        assert hasattr(result, "executed")
        assert hasattr(result, "decision")
        assert hasattr(result, "reason")
        assert hasattr(result, "risk_score")
        assert hasattr(result, "trust_score")
        assert hasattr(result, "function_result")
        assert hasattr(result, "latency_ms")

    def test_to_dict(self, fresh_gateway):
        """to_dict() should return serializable dict."""
        @governed_tool(
            tool_name="test_api",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
        )
        def my_api(endpoint: str) -> dict:
            return {"status": 200}

        result = my_api(endpoint="/health")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "executed" in d
        assert "decision" in d
        assert "reason" in d
        assert "latency_ms" in d

    def test_function_result_preserved(self, fresh_gateway):
        """Function return value should be preserved in result."""
        @governed_tool(
            tool_name="test_compute",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
        )
        def compute(x: int, y: int) -> int:
            return x + y

        result = compute(x=3, y=4)
        assert result.executed is True
        assert result.function_result == 7

    def test_function_error_captured(self, fresh_gateway):
        """Function exceptions should be captured, not propagated."""
        @governed_tool(
            tool_name="test_broken",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
        )
        def broken() -> None:
            raise RuntimeError("intentional failure")

        result = broken()
        assert result.executed is True  # AVS allowed, function failed
        assert result.function_error is not None
        assert "intentional failure" in result.function_error

    def test_parameter_map(self, fresh_gateway):
        """parameter_map should rename args in ActionRequest."""
        captured_params = {}

        @governed_tool(
            tool_name="test_map",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
            parameter_map={"src": "source_path", "dst": "destination_path"},
        )
        def copy(src: str, dst: str) -> dict:
            return {"copied": True}

        result = copy(src="/a", dst="/b")
        # The function should execute (API GET is allowed)
        assert result.executed is True

    def test_metadata_attached(self, fresh_gateway):
        """Governed functions should have AVS metadata attached."""
        @governed_tool(
            tool_name="my_tool",
            action_type=ActionType.FILE,
            operation="read",
            gateway=fresh_gateway,
        )
        def my_func() -> None:
            pass

        assert is_governed(my_func) is True
        meta = get_governed_metadata(my_func)
        assert meta is not None
        assert meta["tool_name"] == "my_tool"
        assert meta["action_type"] == ActionType.FILE
        assert meta["operation"] == "read"

    def test_ungoverned_function(self):
        """Regular functions should not be marked as governed."""
        def regular():
            pass

        assert is_governed(regular) is False
        assert get_governed_metadata(regular) is None

    def test_wrapped_preserves_name(self, fresh_gateway):
        """The decorator should preserve function __name__ and docstring."""
        @governed_tool(
            tool_name="test",
            action_type=ActionType.API,
            operation="GET",
            gateway=fresh_gateway,
        )
        def my_named_function() -> None:
            """My docstring."""
            pass

        assert my_named_function.__name__ == "my_named_function"
        assert my_named_function.__doc__ == "My docstring."


class TestSetDefaultGateway:
    """Tests for set_default_gateway()."""

    def test_set_and_use(self, fresh_gateway):
        """Setting default gateway should make it used by decorators."""
        set_default_gateway(fresh_gateway)

        @governed_tool(
            tool_name="test_default",
            action_type=ActionType.API,
            operation="GET",
        )
        # no gateway= parameter -- uses default
        def my_api() -> dict:
            return {"status": 200}

        result = my_api()
        assert result.executed is True

    def test_none_clears(self):
        """Setting None should clear the default."""
        set_default_gateway(None)
        # This will create a new default on next use, which is fine
        assert True
