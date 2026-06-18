"""
simulated_tools.py -- Simulated tool implementations for Gateway v0.

These tools mimic real external tools but run in-memory.
They are used for testing and demonstration purposes.
No real side effects.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import time
import json

logger = logging.getLogger("avs_gateway.tools")


@dataclass(frozen=True)
class ToolResult:
    """Immutable result of a simulated tool execution.

    Attributes:
        tool_name: Name of the tool that was executed.
        operation: Specific operation performed.
        success: Whether the operation succeeded.
        result: The operation result data.
        error: Error message if the operation failed.
        execution_time_ms: Wall-clock execution time in milliseconds.
        metadata: Additional metadata about the execution.
    """

    tool_name: str
    operation: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the result to a dictionary."""
        return {
            "tool_name": self.tool_name,
            "operation": self.operation,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }

    def is_success(self) -> bool:
        """Return True if the operation succeeded."""
        return self.success


class SimulatedTool:
    """Abstract base class for simulated tools.

    All simulated tools inherit from this class and implement
    the execute() method. Tools run entirely in-memory with
    no real side effects.
    """

    def __init__(self, name: str, description: str) -> None:
        """Initialize the simulated tool.

        Args:
            name: Unique tool name identifier.
            description: Human-readable tool description.
        """
        self.name: str = name
        self.description: str = description

    def execute(self, action_request) -> ToolResult:
        """Execute the tool for the given action request.

        Args:
            action_request: The action request containing tool parameters.

        Returns:
            A ToolResult with the execution outcome.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError("Subclasses must implement execute()")

    def validate_params(self, action_request) -> bool:
        """Validate that the action request has required parameters.

        Args:
            action_request: The action request to validate.

        Returns:
            True if params are valid, False otherwise.
        """
        if not action_request or not action_request.params:
            return False
        return True

    def _make_result(
        self,
        operation: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Create a ToolResult with standard fields populated.

        Args:
            operation: The operation name.
            success: Whether the operation succeeded.
            result: The result data.
            error: Error message if failed.
            metadata: Additional metadata.

        Returns:
            A ToolResult instance.
        """
        return ToolResult(
            tool_name=self.name,
            operation=operation,
            success=success,
            result=result,
            error=error,
            metadata=metadata or {},
        )


class FileTool(SimulatedTool):
    """Simulates file system operations (read, write, delete, append).

    File contents are stored in an in-memory dictionary.
    No real file system side effects.
    """

    def __init__(self) -> None:
        """Initialize the file tool with empty in-memory storage."""
        super().__init__(
            name="file",
            description="Simulated file operations (read, write, delete, append)",
        )
        self._files: Dict[str, str] = {}

    def execute(self, action_request) -> ToolResult:
        """Execute a file operation based on the action request.

        Args:
            action_request: Request with params including 'path' and optionally 'content'.

        Returns:
            ToolResult with the operation outcome.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        path: str = params.get("path", "")
        if not path:
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing 'path' parameter",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        result: ToolResult

        if "read" in operation:
            result = self._read(path)
        elif "write" in operation:
            content: str = params.get("content", "")
            result = self._write(path, content)
        elif "delete" in operation:
            result = self._delete(path)
        elif "append" in operation:
            content = params.get("content", "")
            result = self._append(path, content)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown file operation: {operation}",
            )

        # Inject execution time
        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        result = ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )
        return result

    def _read(self, path: str) -> ToolResult:
        """Read contents of a simulated file."""
        if path not in self._files:
            return self._make_result(
                operation="file_read",
                success=False,
                error=f"File not found: {path}",
            )
        return self._make_result(
            operation="file_read",
            success=True,
            result=self._files[path],
            metadata={"path": path, "size": len(self._files[path])},
        )

    def _write(self, path: str, content: str) -> ToolResult:
        """Write content to a simulated file."""
        self._files[path] = content
        logger.debug("File written: %s (%d bytes)", path, len(content))
        return self._make_result(
            operation="file_write",
            success=True,
            result=f"Written {len(content)} bytes to {path}",
            metadata={"path": path, "size": len(content)},
        )

    def _delete(self, path: str) -> ToolResult:
        """Delete a simulated file."""
        if path not in self._files:
            return self._make_result(
                operation="file_delete",
                success=False,
                error=f"File not found: {path}",
            )
        del self._files[path]
        logger.debug("File deleted: %s", path)
        return self._make_result(
            operation="file_delete",
            success=True,
            result=f"Deleted {path}",
            metadata={"path": path},
        )

    def _append(self, path: str, content: str) -> ToolResult:
        """Append content to a simulated file."""
        if path not in self._files:
            self._files[path] = ""
        self._files[path] += content
        logger.debug("File appended: %s (%d bytes)", path, len(content))
        return self._make_result(
            operation="file_append",
            success=True,
            result=f"Appended {len(content)} bytes to {path}",
            metadata={"path": path, "new_size": len(self._files[path])},
        )

    def list_files(self) -> List[str]:
        """Return a list of all simulated file paths.

        Returns:
            List of file paths in the in-memory store.
        """
        return list(self._files.keys())

    def get_file_contents(self) -> Dict[str, str]:
        """Return a copy of all file contents.

        Returns:
            Dictionary mapping file paths to content.
        """
        return dict(self._files)


class EmailTool(SimulatedTool):
    """Simulates email sending operations.

    Sent emails are stored in an in-memory list.
    No real emails are sent.
    """

    def __init__(self) -> None:
        """Initialize the email tool with empty sent mail storage."""
        super().__init__(
            name="email",
            description="Simulated email sending",
        )
        self._sent_emails: List[Dict[str, Any]] = []

    def execute(self, action_request) -> ToolResult:
        """Execute an email operation.

        Args:
            action_request: Request with params including 'to', 'subject', 'body'.

        Returns:
            ToolResult with the operation outcome.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        if "send" in operation:
            result = self._send(params)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown email operation: {operation}",
            )

        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        return ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )

    def _send(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate sending an email."""
        to_addr: str = params.get("to", "")
        subject: str = params.get("subject", "")
        body: str = params.get("body", "")

        if not to_addr:
            return self._make_result(
                operation="email_send",
                success=False,
                error="Missing 'to' address",
            )

        email_record = {
            "to": to_addr,
            "subject": subject,
            "body": body,
            "timestamp_ns": time.time_ns(),
        }
        self._sent_emails.append(email_record)
        logger.debug("Email sent to: %s, subject: %s", to_addr, subject)

        return self._make_result(
            operation="email_send",
            success=True,
            result=f"Email sent to {to_addr}",
            metadata={
                "to": to_addr,
                "subject": subject,
                "sent_count": len(self._sent_emails),
            },
        )

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """Return all sent emails.

        Returns:
            List of email record dictionaries.
        """
        return list(self._sent_emails)


class APITool(SimulatedTool):
    """Simulates HTTP API calls (GET, POST, PUT, DELETE, PATCH).

    Returns mock data for each HTTP method.
    No real network requests are made.
    """

    def __init__(self) -> None:
        """Initialize the API tool with mock response templates."""
        super().__init__(
            name="api",
            description="Simulated HTTP API calls (GET, POST, PUT, DELETE, PATCH)",
        )
        self._mock_data: Dict[str, Any] = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "items": [{"id": 101, "name": "Widget"}, {"id": 102, "name": "Gadget"}],
        }
        self._call_log: List[Dict[str, Any]] = []

    def execute(self, action_request) -> ToolResult:
        """Execute an API call based on the action request.

        Args:
            action_request: Request with params including 'endpoint', 'body'.

        Returns:
            ToolResult with mock API response.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        endpoint: str = params.get("endpoint", "/")
        body: Any = params.get("body")

        result: ToolResult

        if "get" in operation:
            result = self._get(endpoint)
        elif "post" in operation:
            result = self._post(endpoint, body)
        elif "put" in operation:
            result = self._put(endpoint, body)
        elif "delete" in operation:
            result = self._delete(endpoint)
        elif "patch" in operation:
            result = self._patch(endpoint, body)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown API operation: {operation}",
            )

        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        return ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )

    def _get(self, endpoint: str) -> ToolResult:
        """Simulate a GET request."""
        # Extract key from endpoint
        key = endpoint.strip("/").split("/")[0] if endpoint.strip("/") else ""
        data = self._mock_data.get(key, self._mock_data)

        self._call_log.append({"method": "GET", "endpoint": endpoint, "timestamp_ns": time.time_ns()})

        return self._make_result(
            operation="api_get",
            success=True,
            result=data,
            metadata={"method": "GET", "endpoint": endpoint, "status_code": 200},
        )

    def _post(self, endpoint: str, body: Any) -> ToolResult:
        """Simulate a POST request."""
        self._call_log.append({"method": "POST", "endpoint": endpoint, "body": body, "timestamp_ns": time.time_ns()})

        return self._make_result(
            operation="api_post",
            success=True,
            result={"created": True, "endpoint": endpoint, "body": body},
            metadata={"method": "POST", "endpoint": endpoint, "status_code": 201},
        )

    def _put(self, endpoint: str, body: Any) -> ToolResult:
        """Simulate a PUT request."""
        self._call_log.append({"method": "PUT", "endpoint": endpoint, "body": body, "timestamp_ns": time.time_ns()})

        return self._make_result(
            operation="api_put",
            success=True,
            result={"updated": True, "endpoint": endpoint, "body": body},
            metadata={"method": "PUT", "endpoint": endpoint, "status_code": 200},
        )

    def _delete(self, endpoint: str) -> ToolResult:
        """Simulate a DELETE request."""
        self._call_log.append({"method": "DELETE", "endpoint": endpoint, "timestamp_ns": time.time_ns()})

        return self._make_result(
            operation="api_delete",
            success=True,
            result={"deleted": True, "endpoint": endpoint},
            metadata={"method": "DELETE", "endpoint": endpoint, "status_code": 204},
        )

    def _patch(self, endpoint: str, body: Any) -> ToolResult:
        """Simulate a PATCH request."""
        self._call_log.append({"method": "PATCH", "endpoint": endpoint, "body": body, "timestamp_ns": time.time_ns()})

        return self._make_result(
            operation="api_patch",
            success=True,
            result={"patched": True, "endpoint": endpoint, "body": body},
            metadata={"method": "PATCH", "endpoint": endpoint, "status_code": 200},
        )

    def get_call_log(self) -> List[Dict[str, Any]]:
        """Return the log of all API calls made.

        Returns:
            List of API call record dictionaries.
        """
        return list(self._call_log)


class PaymentTool(SimulatedTool):
    """Simulates payment operations (transfer, refund).

    Payments are recorded in an in-memory ledger.
    No real financial transactions occur.
    """

    def __init__(self) -> None:
        """Initialize the payment tool with empty ledger."""
        super().__init__(
            name="payment",
            description="Simulated payment transfers and refunds",
        )
        self._ledger: List[Dict[str, Any]] = []
        self._payment_counter: int = 0

    def execute(self, action_request) -> ToolResult:
        """Execute a payment operation.

        Args:
            action_request: Request with params including 'amount', 'to_account', 'from_account'.

        Returns:
            ToolResult with payment confirmation or error.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        result: ToolResult

        if "transfer" in operation:
            result = self._transfer(params)
        elif "refund" in operation:
            result = self._refund(params)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown payment operation: {operation}",
            )

        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        return ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )

    def _transfer(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a payment transfer."""
        amount: float = params.get("amount", 0.0)
        to_account: str = params.get("to_account", "")
        from_account: str = params.get("from_account", "")

        if amount <= 0:
            return self._make_result(
                operation="payment_transfer",
                success=False,
                error="Transfer amount must be greater than 0",
            )

        if not to_account or not from_account:
            return self._make_result(
                operation="payment_transfer",
                success=False,
                error="Missing 'to_account' or 'from_account'",
            )

        self._payment_counter += 1
        payment_id = f"PAY-{self._payment_counter:06d}"

        payment_record = {
            "payment_id": payment_id,
            "type": "transfer",
            "amount": amount,
            "to_account": to_account,
            "from_account": from_account,
            "status": "completed",
            "timestamp_ns": time.time_ns(),
        }
        self._ledger.append(payment_record)
        logger.debug("Payment transfer: %s ($%.2f) %s -> %s", payment_id, amount, from_account, to_account)

        return self._make_result(
            operation="payment_transfer",
            success=True,
            result={"payment_id": payment_id, "status": "completed"},
            metadata={
                "payment_id": payment_id,
                "amount": amount,
                "to_account": to_account,
                "from_account": from_account,
                "ledger_size": len(self._ledger),
            },
        )

    def _refund(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a payment refund."""
        payment_id: str = params.get("payment_id", "")

        if not payment_id:
            return self._make_result(
                operation="payment_refund",
                success=False,
                error="Missing 'payment_id' for refund",
            )

        # Find the original payment
        original = None
        for entry in self._ledger:
            if entry.get("payment_id") == payment_id:
                original = entry
                break

        if original is None:
            return self._make_result(
                operation="payment_refund",
                success=False,
                error=f"Payment not found: {payment_id}",
            )

        self._payment_counter += 1
        refund_id = f"REF-{self._payment_counter:06d}"

        refund_record = {
            "refund_id": refund_id,
            "type": "refund",
            "original_payment_id": payment_id,
            "amount": original.get("amount", 0.0),
            "status": "completed",
            "timestamp_ns": time.time_ns(),
        }
        self._ledger.append(refund_record)
        logger.debug("Payment refund: %s for original %s", refund_id, payment_id)

        return self._make_result(
            operation="payment_refund",
            success=True,
            result={"refund_id": refund_id, "status": "completed"},
            metadata={
                "refund_id": refund_id,
                "original_payment_id": payment_id,
                "amount": original.get("amount"),
                "ledger_size": len(self._ledger),
            },
        )

    def get_ledger(self) -> List[Dict[str, Any]]:
        """Return the payment ledger.

        Returns:
            List of all payment records.
        """
        return list(self._ledger)


class DatabaseTool(SimulatedTool):
    """Simulates database operations (SELECT, INSERT, UPDATE, DELETE, DROP).

    Tables are stored as dictionaries of rows in memory.
    DROP clears an entire table (with a warning logged).
    No real database side effects.
    """

    def __init__(self) -> None:
        """Initialize the database tool with empty in-memory tables."""
        super().__init__(
            name="database",
            description="Simulated database operations (SELECT, INSERT, UPDATE, DELETE, DROP)",
        )
        self._tables: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._row_counter: Dict[str, int] = {}

    def execute(self, action_request) -> ToolResult:
        """Execute a database operation.

        Args:
            action_request: Request with params including 'table', 'data', 'where'.

        Returns:
            ToolResult with query results or confirmation.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        result: ToolResult

        if "select" in operation:
            result = self._select(params)
        elif "insert" in operation:
            result = self._insert(params)
        elif "update" in operation:
            result = self._update(params)
        elif "drop" in operation:
            result = self._drop(params)
        elif "delete" in operation:
            result = self._delete_row(params)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown database operation: {operation}",
            )

        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        return ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )

    def _get_table(self, table_name: str) -> Dict[str, Dict[str, Any]]:
        """Get or create a table.

        Args:
            table_name: Name of the table.

        Returns:
            The table dictionary (rows keyed by row ID).
        """
        if table_name not in self._tables:
            self._tables[table_name] = {}
            self._row_counter[table_name] = 0
        return self._tables[table_name]

    def _select(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a SELECT query."""
        table_name: str = params.get("table", "")
        where: Dict[str, Any] = params.get("where", {})

        if not table_name:
            return self._make_result(
                operation="db_select",
                success=False,
                error="Missing 'table' parameter",
            )

        table = self._get_table(table_name)

        if not where:
            # Return all rows
            rows = list(table.values())
        else:
            # Filter rows matching WHERE clause
            rows = [
                row for row in table.values()
                if all(row.get(k) == v for k, v in where.items())
            ]

        return self._make_result(
            operation="db_select",
            success=True,
            result=rows,
            metadata={
                "table": table_name,
                "row_count": len(rows),
                "where": where,
            },
        )

    def _insert(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate an INSERT query."""
        table_name: str = params.get("table", "")
        data: Dict[str, Any] = params.get("data", {})

        if not table_name:
            return self._make_result(
                operation="db_insert",
                success=False,
                error="Missing 'table' parameter",
            )

        if not data:
            return self._make_result(
                operation="db_insert",
                success=False,
                error="Missing 'data' parameter",
            )

        table = self._get_table(table_name)
        self._row_counter[table_name] += 1
        row_id = str(self._row_counter[table_name])

        row = dict(data)
        row["_id"] = row_id
        table[row_id] = row

        return self._make_result(
            operation="db_insert",
            success=True,
            result={"inserted_id": row_id, "row": row},
            metadata={
                "table": table_name,
                "row_id": row_id,
                "table_size": len(table),
            },
        )

    def _update(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate an UPDATE query."""
        table_name: str = params.get("table", "")
        data: Dict[str, Any] = params.get("data", {})
        where: Dict[str, Any] = params.get("where", {})

        if not table_name:
            return self._make_result(
                operation="db_update",
                success=False,
                error="Missing 'table' parameter",
            )

        table = self._get_table(table_name)

        updated_count = 0
        for row_id, row in table.items():
            if all(row.get(k) == v for k, v in where.items()):
                row.update(data)
                updated_count += 1

        return self._make_result(
            operation="db_update",
            success=True,
            result=f"Updated {updated_count} row(s)",
            metadata={
                "table": table_name,
                "updated_count": updated_count,
                "where": where,
                "table_size": len(table),
            },
        )

    def _delete_row(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a DELETE query (delete rows)."""
        table_name: str = params.get("table", "")
        where: Dict[str, Any] = params.get("where", {})

        if not table_name:
            return self._make_result(
                operation="db_delete",
                success=False,
                error="Missing 'table' parameter",
            )

        table = self._get_table(table_name)

        if not where:
            return self._make_result(
                operation="db_delete",
                success=False,
                error="DELETE requires a WHERE clause for safety",
            )

        to_delete = [
            row_id for row_id, row in table.items()
            if all(row.get(k) == v for k, v in where.items())
        ]

        for row_id in to_delete:
            del table[row_id]

        return self._make_result(
            operation="db_delete",
            success=True,
            result=f"Deleted {len(to_delete)} row(s)",
            metadata={
                "table": table_name,
                "deleted_count": len(to_delete),
                "where": where,
                "table_size": len(table),
            },
        )

    def _drop(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a DROP TABLE query."""
        table_name: str = params.get("table", "")

        if not table_name:
            return self._make_result(
                operation="db_drop",
                success=False,
                error="Missing 'table' parameter",
            )

        logger.warning("DatabaseTool: DROP TABLE '%s' executed", table_name)

        if table_name in self._tables:
            row_count = len(self._tables[table_name])
            del self._tables[table_name]
            del self._row_counter[table_name]
        else:
            row_count = 0

        return self._make_result(
            operation="db_drop",
            success=True,
            result=f"Dropped table '{table_name}' ({row_count} rows)",
            metadata={
                "table": table_name,
                "dropped_rows": row_count,
            },
        )

    def get_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return all tables with their rows.

        Returns:
            Dictionary mapping table names to lists of rows.
        """
        return {name: list(rows.values()) for name, rows in self._tables.items()}


class SecurityScanTool(SimulatedTool):
    """Simulates security scanning operations.

    run_scan returns mock vulnerability data.
    access_results returns cached scan results.
    No real security scanning occurs.
    """

    def __init__(self) -> None:
        """Initialize the security scan tool."""
        super().__init__(
            name="security_scan",
            description="Simulated security vulnerability scanning",
        )
        self._scan_results: Dict[str, Dict[str, Any]] = {}
        self._scan_counter: int = 0

    def execute(self, action_request) -> ToolResult:
        """Execute a security scan operation.

        Args:
            action_request: Request with params including 'target'.

        Returns:
            ToolResult with scan results.
        """
        start_ns = time.time_ns()
        operation = action_request.get_operation()
        params = action_request.params

        if not self.validate_params(action_request):
            return self._make_result(
                operation=operation,
                success=False,
                error="Missing parameters",
                metadata={"execution_time_ms": (time.time_ns() - start_ns) / 1_000_000.0},
            )

        result: ToolResult

        if "scan" in operation:
            result = self._run_scan(params)
        elif "results" in operation or "access" in operation:
            result = self._access_results(params)
        else:
            result = self._make_result(
                operation=operation,
                success=False,
                error=f"Unknown security scan operation: {operation}",
            )

        exec_ms = (time.time_ns() - start_ns) / 1_000_000.0
        return ToolResult(
            tool_name=result.tool_name,
            operation=result.operation,
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time_ms=exec_ms,
            metadata=result.metadata,
        )

    def _run_scan(self, params: Dict[str, Any]) -> ToolResult:
        """Simulate a security scan."""
        target: str = params.get("target", "localhost")
        scan_type: str = params.get("scan_type", "full")

        self._scan_counter += 1
        scan_id = f"SCAN-{self._scan_counter:06d}"

        # Generate mock vulnerability data
        mock_vulns = [
            {"id": "CVE-2024-0001", "severity": "low", "description": "Information disclosure"},
            {"id": "CVE-2024-0002", "severity": "medium", "description": "Outdated dependency"},
        ]

        if scan_type == "full":
            mock_vulns.append({"id": "CVE-2024-0003", "severity": "high", "description": "Buffer overflow"})

        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for v in mock_vulns:
            severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1

        scan_result = {
            "scan_id": scan_id,
            "target": target,
            "scan_type": scan_type,
            "vulnerabilities": mock_vulns,
            "severity_counts": severity_counts,
            "total_vulnerabilities": len(mock_vulns),
            "timestamp_ns": time.time_ns(),
        }

        self._scan_results[scan_id] = scan_result
        logger.debug("Security scan completed: %s on %s, %d vulns found", scan_id, target, len(mock_vulns))

        return self._make_result(
            operation="security_scan",
            success=True,
            result=scan_result,
            metadata={
                "scan_id": scan_id,
                "target": target,
                "scan_type": scan_type,
                "vulnerability_count": len(mock_vulns),
            },
        )

    def _access_results(self, params: Dict[str, Any]) -> ToolResult:
        """Access cached scan results."""
        scan_id: str = params.get("scan_id", "")

        if not scan_id:
            return self._make_result(
                operation="access_results",
                success=False,
                error="Missing 'scan_id' parameter",
            )

        if scan_id not in self._scan_results:
            return self._make_result(
                operation="access_results",
                success=False,
                error=f"Scan not found: {scan_id}",
            )

        return self._make_result(
            operation="access_results",
            success=True,
            result=self._scan_results[scan_id],
            metadata={
                "scan_id": scan_id,
                "cached": True,
            },
        )

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Return all cached scan results.

        Returns:
            Dictionary mapping scan IDs to result dictionaries.
        """
        return dict(self._scan_results)


class ToolRegistry:
    """Registry for managing and routing to simulated tools.

    Provides a central mapping from tool names to SimulatedTool instances,
    enabling dynamic tool registration, lookup, and execution routing.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, SimulatedTool] = {}

    def register(self, tool: SimulatedTool) -> None:
        """Register a simulated tool.

        Args:
            tool: The SimulatedTool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, tool_name: str) -> Optional[SimulatedTool]:
        """Get a registered tool by name.

        Args:
            tool_name: Name of the tool to retrieve.

        Returns:
            The SimulatedTool instance, or None if not found.
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of registered tool name strings.
        """
        return list(self._tools.keys())

    def execute(self, action_request) -> ToolResult:
        """Route an action request to the correct tool and execute.

        Args:
            action_request: The action request containing tool name and params.

        Returns:
            ToolResult from the executed tool.
        """
        tool_name = action_request.get_tool_name()
        if not tool_name:
            return ToolResult(
                tool_name="unknown",
                operation=action_request.get_operation(),
                success=False,
                error=f"Could not determine tool name for action: {action_request.action_type}",
            )

        tool = self.get(tool_name)
        if tool is None:
            return ToolResult(
                tool_name=tool_name,
                operation=action_request.get_operation(),
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        return tool.execute(action_request)

    @staticmethod
    def create_default_registry() -> "ToolRegistry":
        """Factory method creating a registry with all 6 default tools.

        Returns:
            A ToolRegistry with FileTool, EmailTool, APITool, PaymentTool,
            DatabaseTool, and SecurityScanTool registered.
        """
        registry = ToolRegistry()
        registry.register(FileTool())
        registry.register(EmailTool())
        registry.register(APITool())
        registry.register(PaymentTool())
        registry.register(DatabaseTool())
        registry.register(SecurityScanTool())
        logger.info("Created default tool registry with %d tools", len(registry._tools))
        return registry

