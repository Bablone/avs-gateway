"""
Unit tests for ActionRequest dataclass, ActionType enum, and factory function.

Tests cover creation, validation, operation validation, deterministic hashing,
serialization roundtrips, immutability, and the factory function.
"""

import json
import pytest


from avs_gateway.models.action_request import (
    ActionRequest,
    ActionType,
    FileOperation,
    EmailOperation,
    APIOperation,
    PaymentOperation,
    DatabaseOperation,
    SecurityScanOperation,
    create_action_request,
)


class TestActionRequestCreation:
    """Tests for basic ActionRequest creation."""

    def test_action_request_creation_with_all_fields(self):
        """Creating an ActionRequest with all required fields succeeds."""
        # Arrange & Act
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
            context={"env": "test"},
            agent_version="1.0.0",
            session_id="session-abc",
            parent_action_id="parent-123",
        )

        # Assert
        assert request.agent_id == "agent-001"
        assert request.action_type == ActionType.FILE
        assert request.tool_name == "file_tool"
        assert request.operation == "read"
        assert request.parameters == {"path": "/tmp/test.txt"}
        assert request.context == {"env": "test"}
        assert request.agent_version == "1.0.0"
        assert request.session_id == "session-abc"
        assert request.parent_action_id == "parent-123"
        assert request.action_id is not None
        assert isinstance(request.timestamp_ns, int)
        assert request.timestamp_ns > 0

    def test_action_request_creation_with_defaults(self):
        """Creating an ActionRequest with minimal fields uses sensible defaults."""
        request = ActionRequest(
            agent_id="agent-002",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="GET",
        )

        assert request.agent_id == "agent-002"
        assert request.parameters == {}
        assert request.context == {}
        assert request.agent_version is None
        assert request.session_id is None
        assert request.parent_action_id is None


class TestActionRequestValidation:
    """Tests for ActionRequest.validate() method."""

    def test_valid_request_passes_validation(self):
        """A properly constructed request passes validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        assert request.validate() is True

    def test_empty_agent_id_fails_validation(self):
        """An empty agent_id fails validation."""
        request = ActionRequest(
            agent_id="",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        assert request.validate() is False

    def test_empty_tool_name_fails_validation(self):
        """An empty tool_name fails validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="",
            operation="read",
        )
        assert request.validate() is False

    def test_empty_operation_fails_validation(self):
        """An empty operation fails validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="",
        )
        assert request.validate() is False

    def test_invalid_action_type_fails_validation(self):
        """A non-ActionType action_type fails validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type="not_an_action_type",  # type: ignore[arg-type]
            tool_name="file_tool",
            operation="read",
        )
        assert request.validate() is False

    def test_non_dict_parameters_fails_validation(self):
        """Non-dict parameters fail validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters="not_a_dict",  # type: ignore[arg-type]
        )
        assert request.validate() is False

    def test_zero_timestamp_fails_validation(self):
        """A zero or negative timestamp fails validation."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            timestamp_ns=0,
        )
        assert request.validate() is False


class TestActionRequestOperationValidation:
    """Tests for ActionRequest.validate_operation() method."""

    def test_valid_file_read_operation(self):
        """File read is a valid operation for FILE action type."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        assert request.validate_operation() is True

    def test_valid_api_post_operation(self):
        """POST is a valid operation for API action type."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
        )
        assert request.validate_operation() is True

    def test_invalid_operation_for_action_type(self):
        """An operation not in the action type's allowed list fails."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="invalid_op",
        )
        assert request.validate_operation() is False

    def test_file_delete_valid_for_file_type(self):
        """File delete IS valid for FILE type (even if policy denies it)."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="delete",
        )
        assert request.validate_operation() is True

    def test_database_drop_valid_for_database_type(self):
        """DROP is a valid operation for DATABASE type."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.DATABASE,
            tool_name="db_tool",
            operation="DROP",
        )
        assert request.validate_operation() is True


class TestActionRequestHash:
    """Tests for deterministic hashing of ActionRequest."""

    def test_hash_is_deterministic(self):
        """Two requests with identical fields produce the same hash."""
        req1 = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
            action_id="fixed-id-123",
            timestamp_ns=1234567890,
        )
        req2 = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
            action_id="fixed-id-123",
            timestamp_ns=1234567890,
        )
        assert req1.action_hash() == req2.action_hash()

    def test_hash_changes_with_different_fields(self):
        """Different fields produce different hashes."""
        req1 = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="fixed-id-123",
            timestamp_ns=1234567890,
        )
        req2 = ActionRequest(
            agent_id="agent-002",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="fixed-id-123",
            timestamp_ns=1234567890,
        )
        assert req1.action_hash() != req2.action_hash()

    def test_hash_is_valid_sha256(self):
        """The hash is a valid 64-character hex SHA-256 digest."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        h = request.action_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_builtin_hash_uses_action_hash(self):
        """The builtin __hash__ is based on action_hash."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="fixed-id",
            timestamp_ns=1000,
        )
        assert hash(request) == hash(request.action_hash())


class TestActionRequestSerialization:
    """Tests for dict serialization roundtrip."""

    def test_to_dict_structure(self):
        """to_dict produces the expected structure."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
            action_id="test-id-123",
            timestamp_ns=1234567890,
        )
        d = request.to_dict()
        assert d["agent_id"] == "agent-001"
        assert d["action_type"] == "file"
        assert d["tool_name"] == "file_tool"
        assert d["operation"] == "read"
        assert d["parameters"] == {"path": "/tmp/test.txt"}
        assert d["action_id"] == "test-id-123"
        assert d["timestamp_ns"] == 1234567890

    def test_from_dict_roundtrip(self):
        """from_dict(to_dict()) reconstructs an equivalent request."""
        original = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
            parameters={"amount": 100, "to_account": "acc-1"},
            context={"source": "test"},
            action_id="roundtrip-id",
            agent_version="2.0.0",
            timestamp_ns=9876543210,
            session_id="sess-1",
            parent_action_id="parent-1",
        )
        d = original.to_dict()
        restored = ActionRequest.from_dict(d)

        assert restored.agent_id == original.agent_id
        assert restored.action_type == original.action_type
        assert restored.tool_name == original.tool_name
        assert restored.operation == original.operation
        assert restored.parameters == original.parameters
        assert restored.context == original.context
        assert restored.action_id == original.action_id
        assert restored.agent_version == original.agent_version
        assert restored.timestamp_ns == original.timestamp_ns
        assert restored.session_id == original.session_id
        assert restored.parent_action_id == original.parent_action_id


class TestActionRequestJsonSerialization:
    """Tests for JSON serialization roundtrip."""

    def test_to_json_is_valid_json(self):
        """to_json produces a valid JSON string with sorted keys."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="test-id",
            timestamp_ns=1000,
        )
        json_str = request.to_json()
        parsed = json.loads(json_str)
        assert parsed["agent_id"] == "agent-001"
        assert parsed["action_type"] == "file"

    def test_from_json_roundtrip(self):
        """from_json(to_json()) reconstructs an equivalent request."""
        original = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="POST",
            parameters={"endpoint": "/users"},
            action_id="json-test-id",
            timestamp_ns=5555555555,
        )
        json_str = original.to_json()
        restored = ActionRequest.from_json(json_str)

        assert restored.agent_id == original.agent_id
        assert restored.action_type == original.action_type
        assert restored.tool_name == original.tool_name
        assert restored.operation == original.operation
        assert restored.parameters == original.parameters
        assert restored.action_id == original.action_id
        assert restored.timestamp_ns == original.timestamp_ns


class TestActionRequestImmutability:
    """Tests that ActionRequest is a frozen (immutable) dataclass."""

    def test_frozen_dataclass_raises_on_mutation(self):
        """Attempting to modify a frozen dataclass raises FrozenInstanceError."""
        request = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
        )
        with pytest.raises(Exception):
            request.agent_id = "agent-002"  # type: ignore[misc]

    def test_can_be_used_in_set(self):
        """Frozen dataclass instances can be added to a set."""
        req1 = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="id-1",
            timestamp_ns=1000,
        )
        req2 = ActionRequest(
            agent_id="agent-002",
            action_type=ActionType.API,
            tool_name="api_tool",
            operation="GET",
            action_id="id-2",
            timestamp_ns=2000,
        )
        s = {req1, req2}
        assert len(s) == 2
        assert req1 in s
        assert req2 in s

    def test_can_be_used_as_dict_key(self):
        """Frozen dataclass instances can be used as dictionary keys."""
        req = ActionRequest(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            action_id="id-1",
            timestamp_ns=1000,
        )
        d = {req: "value"}
        assert d[req] == "value"


class TestCreateActionRequestFactory:
    """Tests for the create_action_request factory function."""

    def test_factory_creates_valid_request(self):
        """Factory function creates a valid ActionRequest."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.FILE,
            tool_name="file_tool",
            operation="read",
            parameters={"path": "/tmp/test.txt"},
            context={"env": "test"},
            session_id="sess-1",
            agent_version="1.0.0",
        )
        assert isinstance(request, ActionRequest)
        assert request.agent_id == "agent-001"
        assert request.action_type == ActionType.FILE
        assert request.tool_name == "file_tool"
        assert request.operation == "read"
        assert request.parameters == {"path": "/tmp/test.txt"}
        assert request.context == {"env": "test"}
        assert request.session_id == "sess-1"
        assert request.agent_version == "1.0.0"
        assert request.validate() is True

    def test_factory_with_defaults(self):
        """Factory function works with only required parameters."""
        request = create_action_request(
            agent_id="agent-001",
            action_type=ActionType.PAYMENT,
            tool_name="payment_tool",
            operation="transfer",
        )
        assert isinstance(request, ActionRequest)
        assert request.parameters == {}
        assert request.context == {}
        assert request.session_id is None
        assert request.agent_version is None
        assert request.validate() is True

    def test_factory_validates_all_action_types(self):
        """Factory works for all action types."""
        for action_type in ActionType:
            request = create_action_request(
                agent_id="agent-001",
                action_type=action_type,
                tool_name=f"{action_type.value}_tool",
                operation="read",
            )
            assert request.validate() is True
