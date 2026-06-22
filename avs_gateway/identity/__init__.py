"""
Agent Identity Module — Verifiable Agent Principals.

Turns simple agent labels into accountable, non-human actor profiles.

Agent Identity should answer:
- Who is this agent?
- What environment does it belong to?
- What public key represents it?
- What privileges does it have?
- Is the key active, rotated, or revoked?

This is a draft model for v0.3.6. Signed ActionRequests come in v0.4.0.
"""

from avs_gateway.identity.agent_identity import (
    AgentIdentity,
    AgentStatus,
    AgentPrivilegeLevel,
    create_agent_identity,
)

__all__ = [
    "AgentIdentity",
    "AgentStatus",
    "AgentPrivilegeLevel",
    "create_agent_identity",
]
