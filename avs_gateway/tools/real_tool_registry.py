"""
real_tool_registry.py -- Registry mapping semantic actions to real tool implementations.

This is the bridge between AVS Gateway decisions and actual tool execution.
It routes ALLOWed actions to real tools (file_sandbox) and returns
structured results for audit/timeline evidence.

Usage:
    registry = RealToolRegistry(sandbox_root=Path("./sandbox"))
    result = registry.execute("file_write", path="output.txt", content="hello")
    # result.status == "success" or "blocked"
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from avs_gateway.tools.file_sandbox import FileSandbox, SandboxResult
from avs_gateway.tools.http_sandbox import HTTPSandbox, HTTPSandboxResult

logger = logging.getLogger("avs_gateway.tools.real_tool_registry")


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not registered."""
    pass


class RealToolRegistry:
    """Registry of real tools that perform actual side effects.

    All tools are sandboxed. No tool can escape its configured boundary.
    """

    def __init__(self, sandbox_root=None, http_sandbox=None) -> None:
        if sandbox_root is None:
            sandbox_root = Path("./sandbox")
        elif isinstance(sandbox_root, str):
            sandbox_root = Path(sandbox_root)
        self._sandbox_root = sandbox_root
        self._file_sandbox = FileSandbox(root=self._sandbox_root)
        self._http_sandbox = http_sandbox or HTTPSandbox(
            allowed_domains=set(),  # deny-by-default; caller must configure
        )
        self._tools: Dict[str, Callable] = {}
        self._register_defaults()
        logger.info(
            "RealToolRegistry initialized with sandbox=%s http_domains=%d",
            self._sandbox_root.resolve(),
            len(self._http_sandbox.allowed_domains),
        )

    def _register_defaults(self) -> None:
        """Register built-in sandbox tools."""
        # Filesystem tools (v0.3.0)
        self.register("file_write", self._file_sandbox.write_file)
        self.register("file_read", self._file_sandbox.read_file)
        self.register("file_list", self._file_sandbox.list_files)
        self.register("file_delete", self._file_sandbox.delete_file)
        # HTTP tools (v0.3.2)
        self.register("http_get", self._http_sandbox.get)
        self.register("http_post", self._http_sandbox.post)

    def register(self, name: str, func: Callable) -> None:
        """Register a tool function."""
        self._tools[name] = func
        logger.debug("Registered tool: %s", name)

    def execute(self, tool_name: str, **kwargs: Any) -> SandboxResult:
        """Execute a tool by name with given parameters.

        Args:
            tool_name: Name of the tool (e.g., "file_write", "file_read").
            **kwargs: Tool-specific parameters.

        Returns:
            SandboxResult with status, raw path, resolved path, error info.

        Raises:
            ToolNotFoundError: If tool name not registered.
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(
                f"Tool '{tool_name}' not registered. "
                f"Available: {sorted(self._tools.keys())}"
            )
        return self._tools[tool_name](**kwargs)

    def list_tools(self) -> list[str]:
        """Return list of registered tool names."""
        return sorted(self._tools.keys())

    @property
    def file_sandbox(self) -> FileSandbox:
        """Return the underlying file sandbox instance."""
        return self._file_sandbox

    @property
    def http_sandbox(self) -> HTTPSandbox:
        """Return the underlying HTTP sandbox instance."""
        return self._http_sandbox

    @property
    def sandbox_root(self) -> Path:
        """Return the sandbox root path."""
        return self._file_sandbox.root
