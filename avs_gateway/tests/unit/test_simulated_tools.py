"""
Unit tests for simulated tools (FileTool, EmailTool, APITool, PaymentTool,
DatabaseTool, SecurityScanTool) and ToolRegistry.

Tests cover CRUD operations, tool routing, result creation, and edge cases.
Note: SimulatedTool classes expect action_request with .params, .get_operation(),
.get_tool_name() interface, so we use a MockActionRequest wrapper.
"""



import pytest

from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.tools.simulated_tools import (
    ToolResult,
    SimulatedTool,
    FileTool,
    EmailTool,
    APITool,
    PaymentTool,
    DatabaseTool,
    SecurityScanTool,
    ToolRegistry,
)


# ---------------------------------------------------------------------------
# Mock action request wrapper
# ---------------------------------------------------------------------------

class MockActionRequest:
    """Wrapper that adapts ActionRequest to SimulatedTool interface."""

    def __init__(self, action_request):
        self._request = action_request
        self.params = action_request.parameters
        self.action_type = action_request.action_type
        self.tool_name = action_request.tool_name
        self.operation = action_request.operation

    def get_operation(self):
        return self.operation.lower()

    def get_tool_name(self):
        return self.tool_name


def _make_request(action_type, tool_name, operation, parameters=None, context=None):
    """Helper to create a MockActionRequest."""
    ar = create_action_request(
        agent_id="agent-001",
        action_type=action_type,
        tool_name=tool_name,
        operation=operation,
        parameters=parameters or {},
        context=context or {},
    )
    return MockActionRequest(ar)


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------

class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_tool_result_creation(self):
        """ToolResult can be created with all fields."""
        result = ToolResult(
            tool_name="test_tool",
            operation="test_op",
            success=True,
            result="data",
            error=None,
            execution_time_ms=1.5,
            metadata={"key": "value"},
        )
        assert result.tool_name == "test_tool"
        assert result.operation == "test_op"
        assert result.success is True
        assert result.result == "data"
        assert result.error is None
        assert result.execution_time_ms == 1.5
        assert result.metadata == {"key": "value"}

    def test_tool_result_defaults(self):
        """ToolResult uses sensible defaults."""
        result = ToolResult(tool_name="test", operation="op", success=True)
        assert result.result is None
        assert result.error is None
        assert result.execution_time_ms == 0.0
        assert result.metadata == {}

    def test_tool_result_is_success(self):
        """is_success() returns the success field."""
        success = ToolResult(tool_name="test", operation="op", success=True)
        failure = ToolResult(tool_name="test", operation="op", success=False)
        assert success.is_success() is True
        assert failure.is_success() is False

    def test_tool_result_to_dict(self):
        """to_dict() produces a dictionary representation."""
        result = ToolResult(
            tool_name="test", operation="op", success=True,
            result="data", metadata={"key": "val"},
        )
        d = result.to_dict()
        assert d["tool_name"] == "test"
        assert d["success"] is True
        assert d["result"] == "data"
        assert d["metadata"] == {"key": "val"}


# ---------------------------------------------------------------------------
# FileTool
# ---------------------------------------------------------------------------

class TestFileTool:
    """Tests for FileTool CRUD operations."""

    def test_file_tool_write(self):
        """FileTool write creates a new file."""
        tool = FileTool()
        request = _make_request(ActionType.FILE, "file", "write", {"path": "/test/file.txt", "content": "hello"})
        result = tool.execute(request)
        assert result.success is True
        assert "Written" in result.result
        assert "/test/file.txt" in tool.list_files()

    def test_file_tool_read(self):
        """FileTool read returns file contents."""
        tool = FileTool()
        # Write first
        write_req = _make_request(ActionType.FILE, "file", "write", {"path": "/test/read.txt", "content": "hello world"})
        tool.execute(write_req)
        # Then read
        read_req = _make_request(ActionType.FILE, "file", "read", {"path": "/test/read.txt"})
        result = tool.execute(read_req)
        assert result.success is True
        assert result.result == "hello world"

    def test_file_tool_read_not_found(self):
        """FileTool read for missing file returns error."""
        tool = FileTool()
        request = _make_request(ActionType.FILE, "file", "read", {"path": "/nonexistent.txt"})
        result = tool.execute(request)
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_file_tool_append(self):
        """FileTool append adds content to existing file."""
        tool = FileTool()
        # Write first
        tool.execute(_make_request(ActionType.FILE, "file", "write", {"path": "/test/append.txt", "content": "hello"}))
        # Append
        result = tool.execute(_make_request(ActionType.FILE, "file", "append", {"path": "/test/append.txt", "content": " world"}))
        assert result.success is True
        # Read back
        read_result = tool.execute(_make_request(ActionType.FILE, "file", "read", {"path": "/test/append.txt"}))
        assert read_result.result == "hello world"

    def test_file_tool_append_creates_file(self):
        """FileTool append creates file if it doesn't exist."""
        tool = FileTool()
        result = tool.execute(_make_request(ActionType.FILE, "file", "append", {"path": "/test/new_append.txt", "content": "data"}))
        assert result.success is True
        read_result = tool.execute(_make_request(ActionType.FILE, "file", "read", {"path": "/test/new_append.txt"}))
        assert read_result.result == "data"

    def test_file_tool_delete(self):
        """FileTool delete removes a file."""
        tool = FileTool()
        tool.execute(_make_request(ActionType.FILE, "file", "write", {"path": "/test/del.txt", "content": "bye"}))
        result = tool.execute(_make_request(ActionType.FILE, "file", "delete", {"path": "/test/del.txt"}))
        assert result.success is True
        assert "/test/del.txt" not in tool.list_files()

    def test_file_tool_delete_not_found(self):
        """FileTool delete for missing file returns error."""
        tool = FileTool()
        result = tool.execute(_make_request(ActionType.FILE, "file", "delete", {"path": "/nonexistent.txt"}))
        assert result.success is False

    def test_file_tool_missing_path(self):
        """FileTool returns error when path is missing."""
        tool = FileTool()
        result = tool.execute(_make_request(ActionType.FILE, "file", "read", {}))
        assert result.success is False
        assert "path" in result.error.lower() or "Missing" in result.error

    def test_file_tool_list_files(self):
        """list_files returns all file paths."""
        tool = FileTool()
        tool.execute(_make_request(ActionType.FILE, "file", "write", {"path": "/a.txt", "content": "a"}))
        tool.execute(_make_request(ActionType.FILE, "file", "write", {"path": "/b.txt", "content": "b"}))
        files = tool.list_files()
        assert "/a.txt" in files
        assert "/b.txt" in files
        assert len(files) == 2

    def test_file_tool_get_contents(self):
        """get_file_contents returns all file contents."""
        tool = FileTool()
        tool.execute(_make_request(ActionType.FILE, "file", "write", {"path": "/x.txt", "content": "data"}))
        contents = tool.get_file_contents()
        assert contents["/x.txt"] == "data"


# ---------------------------------------------------------------------------
# EmailTool
# ---------------------------------------------------------------------------

class TestEmailTool:
    """Tests for EmailTool operations."""

    def test_email_tool_send(self):
        """EmailTool send stores an email record."""
        tool = EmailTool()
        request = _make_request(ActionType.EMAIL, "email", "send", {
            "to": "test@example.com", "subject": "Hello", "body": "World",
        })
        result = tool.execute(request)
        assert result.success is True
        assert "sent" in result.result.lower()
        assert len(tool.get_sent_emails()) == 1

    def test_email_tool_send_missing_to(self):
        """EmailTool send without 'to' address returns error."""
        tool = EmailTool()
        request = _make_request(ActionType.EMAIL, "email", "send", {"subject": "test", "body": "hello"})
        result = tool.execute(request)
        assert result.success is False
        assert "to" in result.error.lower() or "Missing" in result.error

    def test_email_tool_get_sent_emails(self):
        """get_sent_emails returns all sent emails."""
        tool = EmailTool()
        tool.execute(_make_request(ActionType.EMAIL, "email", "send", {"to": "a@a.com", "subject": "s1", "body": "b1"}))
        tool.execute(_make_request(ActionType.EMAIL, "email", "send", {"to": "b@b.com", "subject": "s2", "body": "b2"}))
        emails = tool.get_sent_emails()
        assert len(emails) == 2
        assert emails[0]["to"] == "a@a.com"
        assert emails[1]["to"] == "b@b.com"


# ---------------------------------------------------------------------------
# APITool
# ---------------------------------------------------------------------------

class TestAPITool:
    """Tests for APITool HTTP operations."""

    def test_api_tool_get(self):
        """APITool GET returns mock data."""
        tool = APITool()
        request = _make_request(ActionType.API, "api", "GET", {"endpoint": "/users"})
        result = tool.execute(request)
        assert result.success is True
        assert result.metadata["method"] == "GET"
        assert result.metadata["status_code"] == 200

    def test_api_tool_post(self):
        """APITool POST returns created response."""
        tool = APITool()
        request = _make_request(ActionType.API, "api", "POST", {"endpoint": "/users", "body": {"name": "test"}})
        result = tool.execute(request)
        assert result.success is True
        assert result.metadata["method"] == "POST"
        assert result.metadata["status_code"] == 201
        assert result.result["created"] is True

    def test_api_tool_put(self):
        """APITool PUT returns updated response."""
        tool = APITool()
        request = _make_request(ActionType.API, "api", "PUT", {"endpoint": "/users/1", "body": {"name": "updated"}})
        result = tool.execute(request)
        assert result.success is True
        assert result.metadata["status_code"] == 200
        assert result.result["updated"] is True

    def test_api_tool_delete(self):
        """APITool DELETE returns deleted response."""
        tool = APITool()
        request = _make_request(ActionType.API, "api", "DELETE", {"endpoint": "/users/1"})
        result = tool.execute(request)
        assert result.success is True
        assert result.metadata["status_code"] == 204
        assert result.result["deleted"] is True

    def test_api_tool_patch(self):
        """APITool PATCH returns patched response."""
        tool = APITool()
        request = _make_request(ActionType.API, "api", "PATCH", {"endpoint": "/users/1", "body": {"name": "patched"}})
        result = tool.execute(request)
        assert result.success is True
        assert result.metadata["status_code"] == 200
        assert result.result["patched"] is True

    def test_api_tool_get_call_log(self):
        """get_call_log returns all API calls made."""
        tool = APITool()
        tool.execute(_make_request(ActionType.API, "api", "GET", {"endpoint": "/users"}))
        tool.execute(_make_request(ActionType.API, "api", "POST", {"endpoint": "/items"}))
        log = tool.get_call_log()
        assert len(log) == 2
        assert log[0]["method"] == "GET"
        assert log[1]["method"] == "POST"


# ---------------------------------------------------------------------------
# PaymentTool
# ---------------------------------------------------------------------------

class TestPaymentTool:
    """Tests for PaymentTool operations."""

    def test_payment_tool_transfer(self):
        """PaymentTool transfer creates a payment record."""
        tool = PaymentTool()
        request = _make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 100.0, "to_account": "ACC-002", "from_account": "ACC-001",
        })
        result = tool.execute(request)
        assert result.success is True
        assert result.result["status"] == "completed"
        assert "payment_id" in result.result
        assert len(tool.get_ledger()) == 1

    def test_payment_tool_transfer_invalid_amount(self):
        """PaymentTool transfer with amount <= 0 returns error."""
        tool = PaymentTool()
        request = _make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 0, "to_account": "ACC-002", "from_account": "ACC-001",
        })
        result = tool.execute(request)
        assert result.success is False
        assert "amount" in result.error.lower() or "greater" in result.error.lower()

    def test_payment_tool_transfer_missing_accounts(self):
        """PaymentTool transfer with missing accounts returns error."""
        tool = PaymentTool()
        request = _make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 100.0, "to_account": "", "from_account": "ACC-001",
        })
        result = tool.execute(request)
        assert result.success is False

    def test_payment_tool_refund(self):
        """PaymentTool refund creates a refund record."""
        tool = PaymentTool()
        # First transfer
        tool.execute(_make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 100.0, "to_account": "ACC-002", "from_account": "ACC-001",
        }))
        payment_id = tool.get_ledger()[0]["payment_id"]
        # Then refund
        request = _make_request(ActionType.PAYMENT, "payment", "refund", {"payment_id": payment_id})
        result = tool.execute(request)
        assert result.success is True
        assert result.result["status"] == "completed"
        assert "refund_id" in result.result
        assert len(tool.get_ledger()) == 2

    def test_payment_tool_refund_not_found(self):
        """PaymentTool refund for non-existent payment returns error."""
        tool = PaymentTool()
        request = _make_request(ActionType.PAYMENT, "payment", "refund", {"payment_id": "NONEXISTENT"})
        result = tool.execute(request)
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_payment_tool_ledger(self):
        """get_ledger returns all payment records."""
        tool = PaymentTool()
        tool.execute(_make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 50.0, "to_account": "B", "from_account": "A",
        }))
        tool.execute(_make_request(ActionType.PAYMENT, "payment", "transfer", {
            "amount": 75.0, "to_account": "C", "from_account": "A",
        }))
        ledger = tool.get_ledger()
        assert len(ledger) == 2
        assert ledger[0]["amount"] == 50.0
        assert ledger[1]["amount"] == 75.0


# ---------------------------------------------------------------------------
# DatabaseTool
# ---------------------------------------------------------------------------

class TestDatabaseTool:
    """Tests for DatabaseTool operations."""

    def test_database_tool_insert(self):
        """DatabaseTool insert adds a row to a table."""
        tool = DatabaseTool()
        request = _make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice", "age": 30},
        })
        result = tool.execute(request)
        assert result.success is True
        assert "inserted_id" in result.result

    def test_database_tool_select_all(self):
        """DatabaseTool select without WHERE returns all rows."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice"},
        }))
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Bob"},
        }))
        request = _make_request(ActionType.DATABASE, "database", "SELECT", {"table": "users"})
        result = tool.execute(request)
        assert result.success is True
        assert len(result.result) == 2

    def test_database_tool_select_with_where(self):
        """DatabaseTool select with WHERE filters rows."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice", "role": "admin"},
        }))
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Bob", "role": "user"},
        }))
        request = _make_request(ActionType.DATABASE, "database", "SELECT", {
            "table": "users", "where": {"role": "admin"},
        })
        result = tool.execute(request)
        assert result.success is True
        assert len(result.result) == 1
        assert result.result[0]["name"] == "Alice"

    def test_database_tool_update(self):
        """DatabaseTool update modifies matching rows."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice", "role": "user"},
        }))
        request = _make_request(ActionType.DATABASE, "database", "UPDATE", {
            "table": "users", "data": {"role": "admin"}, "where": {"name": "Alice"},
        })
        result = tool.execute(request)
        assert result.success is True
        assert result.result == "Updated 1 row(s)"

    def test_database_tool_delete_row(self):
        """DatabaseTool delete removes matching rows."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice"},
        }))
        request = _make_request(ActionType.DATABASE, "database", "DELETE", {
            "table": "users", "where": {"name": "Alice"},
        })
        result = tool.execute(request)
        assert result.success is True
        assert result.result == "Deleted 1 row(s)"

    def test_database_tool_delete_row_no_where(self):
        """DatabaseTool delete without WHERE returns error."""
        tool = DatabaseTool()
        request = _make_request(ActionType.DATABASE, "database", "DELETE", {"table": "users"})
        result = tool.execute(request)
        assert result.success is False
        assert "WHERE" in result.error

    def test_database_tool_drop(self):
        """DatabaseTool drop removes a table."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice"},
        }))
        request = _make_request(ActionType.DATABASE, "database", "DROP", {"table": "users"})
        result = tool.execute(request)
        assert result.success is True
        assert "users" in result.result
        tables = tool.get_tables()
        assert "users" not in tables

    def test_database_tool_drop_missing_table(self):
        """DatabaseTool drop for missing table still succeeds."""
        tool = DatabaseTool()
        request = _make_request(ActionType.DATABASE, "database", "DROP", {"table": "nonexistent"})
        result = tool.execute(request)
        assert result.success is True

    def test_database_tool_get_tables(self):
        """get_tables returns all tables with rows."""
        tool = DatabaseTool()
        tool.execute(_make_request(ActionType.DATABASE, "database", "INSERT", {
            "table": "users", "data": {"name": "Alice"},
        }))
        tables = tool.get_tables()
        assert "users" in tables
        assert len(tables["users"]) == 1


# ---------------------------------------------------------------------------
# SecurityScanTool
# ---------------------------------------------------------------------------

class TestSecurityScanTool:
    """Tests for SecurityScanTool operations."""

    def test_security_scan_tool_run(self):
        """SecurityScanTool run_scan produces vulnerability data."""
        tool = SecurityScanTool()
        request = _make_request(ActionType.SECURITY_SCAN, "security_scan", "run_scan", {"target": "localhost"})
        result = tool.execute(request)
        assert result.success is True
        scan_result = result.result
        assert "scan_id" in scan_result
        assert "vulnerabilities" in scan_result
        assert "severity_counts" in scan_result
        assert scan_result["total_vulnerabilities"] > 0

    def test_security_scan_tool_run_full(self):
        """Full scan includes more vulnerabilities than quick scan."""
        tool = SecurityScanTool()
        full_req = _make_request(ActionType.SECURITY_SCAN, "security_scan", "run_scan", {
            "target": "localhost", "scan_type": "full",
        })
        result = tool.execute(full_req)
        assert result.result["total_vulnerabilities"] >= 3

    def test_security_scan_tool_access_results(self):
        """Accessing scan results returns cached data."""
        tool = SecurityScanTool()
        # Run scan first
        run_req = _make_request(ActionType.SECURITY_SCAN, "security_scan", "run_scan", {"target": "localhost"})
        run_result = tool.execute(run_req)
        scan_id = run_result.result["scan_id"]
        # Access results
        access_req = _make_request(ActionType.SECURITY_SCAN, "security_scan", "access_results", {"scan_id": scan_id})
        access_result = tool.execute(access_req)
        assert access_result.success is True
        assert access_result.result["scan_id"] == scan_id

    def test_security_scan_tool_access_results_not_found(self):
        """Accessing non-existent scan results returns error."""
        tool = SecurityScanTool()
        request = _make_request(ActionType.SECURITY_SCAN, "security_scan", "access_results", {"scan_id": "NONEXISTENT"})
        result = tool.execute(request)
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_security_scan_tool_get_all_results(self):
        """get_all_results returns all cached scan results."""
        tool = SecurityScanTool()
        tool.execute(_make_request(ActionType.SECURITY_SCAN, "security_scan", "run_scan", {"target": "host1"}))
        tool.execute(_make_request(ActionType.SECURITY_SCAN, "security_scan", "run_scan", {"target": "host2"}))
        results = tool.get_all_results()
        assert len(results) == 2


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry:
    """Tests for ToolRegistry factory and routing."""

    def test_tool_registry_create_default(self):
        """create_default_registry creates a registry with all 6 tools."""
        registry = ToolRegistry.create_default_registry()
        tools = registry.list_tools()
        assert len(tools) == 6
        assert "file" in tools
        assert "email" in tools
        assert "api" in tools
        assert "payment" in tools
        assert "database" in tools
        assert "security_scan" in tools

    def test_tool_registry_get(self):
        """get() returns the correct tool."""
        registry = ToolRegistry.create_default_registry()
        file_tool = registry.get("file")
        assert file_tool is not None
        assert file_tool.name == "file"

    def test_tool_registry_get_nonexistent(self):
        """get() returns None for unknown tools."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_tool_registry_register_duplicate_raises(self):
        """Registering a duplicate tool raises ValueError."""
        registry = ToolRegistry()
        registry.register(FileTool())
        with pytest.raises(ValueError):
            registry.register(FileTool())

    def test_tool_registry_execute(self):
        """execute() routes to the correct tool and returns a result."""
        registry = ToolRegistry.create_default_registry()
        request = _make_request(ActionType.FILE, "file", "write", {"path": "/reg/test.txt", "content": "hello"})
        result = registry.execute(request)
        assert result.success is True
        assert result.tool_name == "file"

    def test_tool_registry_execute_unknown_tool(self):
        """execute() with unknown tool returns error result."""
        registry = ToolRegistry()
        request = _make_request(ActionType.FILE, "unknown_tool", "read", {})
        result = registry.execute(request)
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_tool_registry_list_tools_empty(self):
        """An empty registry returns an empty list."""
        registry = ToolRegistry()
        assert registry.list_tools() == []

    def test_tool_registry_execute_routes_by_tool_name(self):
        """execute() correctly routes to different tools."""
        registry = ToolRegistry.create_default_registry()
        # Test file tool
        file_req = _make_request(ActionType.FILE, "file", "write", {"path": "/routed.txt", "content": "data"})
        file_result = registry.execute(file_req)
        assert file_result.tool_name == "file"

        # Test email tool
        email_req = _make_request(ActionType.EMAIL, "email", "send", {"to": "test@test.com", "subject": "s", "body": "b"})
        email_result = registry.execute(email_req)
        assert email_result.tool_name == "email"

