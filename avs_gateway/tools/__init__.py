"""
AVS Gateway Tools Package.

Provides simulated tools (v0.1-v0.2) and real sandbox tools (v0.3+).
"""

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
from avs_gateway.tools.file_sandbox import (
    FileSandbox,
    SandboxResult,
    SandboxSecurityError,
)
from avs_gateway.tools.http_sandbox import (
    HTTPSandbox,
    HTTPSandboxResult,
    HTTPSandboxSecurityError,
)
from avs_gateway.tools.real_tool_registry import (
    RealToolRegistry,
    ToolNotFoundError,
)

__all__ = [
    # Simulated tools (v0.1-v0.2)
    "ToolResult",
    "SimulatedTool",
    "FileTool",
    "EmailTool",
    "APITool",
    "PaymentTool",
    "DatabaseTool",
    "SecurityScanTool",
    "ToolRegistry",
    # Real sandbox tools (v0.3+)
    "FileSandbox",
    "SandboxResult",
    "SandboxSecurityError",
    "HTTPSandbox",
    "HTTPSandboxResult",
    "HTTPSandboxSecurityError",
    "RealToolRegistry",
    "ToolNotFoundError",
]
