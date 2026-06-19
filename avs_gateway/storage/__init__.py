"""
AVS Gateway Storage Package.

Provides SQLite persistence for approval requests, decisions,
trust events, and audit events.
"""

from avs_gateway.storage.sqlite_store import SqliteStore

__all__ = ["SqliteStore"]
