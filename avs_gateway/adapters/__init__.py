"""
AVS Gateway Adapters Package.

Provides framework adapters and the @governed_tool decorator.
"""

from avs_gateway.adapters.base_adapter import BaseAdapter, AdapterRegistry
from avs_gateway.adapters.openclaw_adapter import OpenClawAdapter
from avs_gateway.adapters.governed import (
    governed_tool,
    GovernedResult,
    set_default_gateway,
    is_governed,
    get_governed_metadata,
)

__all__ = [
    "BaseAdapter",
    "AdapterRegistry",
    "OpenClawAdapter",
    "governed_tool",
    "GovernedResult",
    "set_default_gateway",
    "is_governed",
    "get_governed_metadata",
]
