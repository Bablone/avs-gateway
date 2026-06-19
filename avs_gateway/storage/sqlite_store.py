"""
sqlite_store.py -- SQLite persistence layer for AVS Gateway v0.2.

Uses stdlib sqlite3. Thread-safe via check_same_thread=False + RLock.
All public methods accept/return plain dicts (no ORM).

DB path defaults to ./data/avs_gateway.sqlite3 (relative to cwd).
"""

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("avs_gateway.storage")

# Windows-compatible default path (relative, not hardcoded Linux)
DEFAULT_DB_PATH = os.path.join("data", "avs_gateway.sqlite3")

# SQL schema file is next to this module
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


class SqliteStore:
    """Thread-safe SQLite store for approval lifecycle persistence.

    Usage:
        store = SqliteStore()  # uses ./data/avs_gateway.sqlite3
        store.init_schema()    # creates tables if missing
        store.create_approval_request(...)
        pending = store.list_pending_approvals()
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.RLock()
        logger.info("SqliteStore initialized at %s", os.path.abspath(self.db_path))

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local sqlite3 connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None,  # autocommit mode; we use BEGIN/COMMIT
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create tables and indexes from schema.sql if they don't exist."""
        with self._lock:
            conn = self._conn()
            if not os.path.exists(SCHEMA_PATH):
                raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            logger.info("Schema initialized")

    def reset(self) -> None:
        """Drop all data (for testing). USE WITH CAUTION."""
        with self._lock:
            conn = self._conn()
            conn.execute("DELETE FROM approval_decisions")
            conn.execute("DELETE FROM trust_events")
            conn.execute("DELETE FROM audit_events")
            conn.execute("DELETE FROM approval_requests")
            logger.warning("All tables wiped (reset called)")

    # ------------------------------------------------------------------
    # Approval requests
    # ------------------------------------------------------------------

    def create_approval_request(
        self,
        action_request_dict: Dict[str, Any],
        decision_dict: Dict[str, Any],
    ) -> str:
        """Persist a REQUIRE_APPROVAL decision as a pending approval request.

        Returns:
            The generated approval_id (UUID4 string).
        """
        approval_id = str(uuid.uuid4())
        now_ns = time.time_ns()
        with self._lock:
            self._conn().execute(
                """
                INSERT INTO approval_requests (
                    approval_id, action_id, agent_id, action_type,
                    tool_name, operation, parameters_json, context_json,
                    risk_score, trust_score, reason, status, created_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    action_request_dict.get("action_id", ""),
                    action_request_dict.get("agent_id", ""),
                    action_request_dict.get("action_type", ""),
                    action_request_dict.get("tool_name", ""),
                    action_request_dict.get("operation", ""),
                    json.dumps(action_request_dict.get("parameters", {})),
                    json.dumps(action_request_dict.get("context", {})),
                    decision_dict.get("risk_score", 0),
                    decision_dict.get("trust_score", 0),
                    decision_dict.get("reason", ""),
                    "pending",
                    now_ns,
                ),
            )
            logger.debug("Created approval request %s", approval_id)
            return approval_id

    def get_approval_request(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single approval request by ID."""
        with self._lock:
            row = self._conn().execute(
                "SELECT * FROM approval_requests WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """Return all approval requests with status = 'pending'."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM approval_requests WHERE status = 'pending' ORDER BY created_at_ns ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def list_all_approvals(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Return all approval requests ordered by creation time."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM approval_requests ORDER BY created_at_ns DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_approval_status(
        self,
        approval_id: str,
        status: str,
        decided_by: Optional[str] = None,
        decision_reason: Optional[str] = None,
    ) -> bool:
        """Update approval status and decision metadata.

        Valid statuses: pending, approved, denied, executed, expired.
        Returns True if a row was updated, False if approval_id not found.
        """
        now_ns = time.time_ns()
        with self._lock:
            cur = self._conn().execute(
                """
                UPDATE approval_requests
                SET status = ?, decided_at_ns = ?, decided_by = ?, decision_reason = ?
                WHERE approval_id = ?
                """,
                (status, now_ns, decided_by, decision_reason, approval_id),
            )
            updated = cur.rowcount > 0
            if updated:
                logger.debug("Approval %s status -> %s", approval_id, status)
            return updated

    def record_execution_result(
        self,
        approval_id: str,
        result_json: str,
        receipt_hash: Optional[str] = None,
    ) -> bool:
        """Record that an approved action was executed, with result and receipt."""
        now_ns = time.time_ns()
        with self._lock:
            cur = self._conn().execute(
                """
                UPDATE approval_requests
                SET status = 'executed', executed_at_ns = ?,
                    execution_result_json = ?, receipt_hash = ?
                WHERE approval_id = ?
                """,
                (now_ns, result_json, receipt_hash, approval_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Approval decisions
    # ------------------------------------------------------------------

    def record_approval_decision(
        self,
        approval_id: str,
        decision: str,
        decided_by: str,
        reason: str,
    ) -> str:
        """Record a human decision (approved or denied) on an approval request.

        Returns:
            The generated decision_id.
        """
        decision_id = str(uuid.uuid4())
        now_ns = time.time_ns()
        with self._lock:
            self._conn().execute(
                """
                INSERT INTO approval_decisions (decision_id, approval_id, decision, decided_by, reason, timestamp_ns)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (decision_id, approval_id, decision, decided_by, reason, now_ns),
            )
            return decision_id

    def get_decisions_for_approval(self, approval_id: str) -> List[Dict[str, Any]]:
        """Return all decisions for a given approval request."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM approval_decisions WHERE approval_id = ? ORDER BY timestamp_ns ASC",
                (approval_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Trust events
    # ------------------------------------------------------------------

    def record_trust_event(
        self,
        agent_id: str,
        delta: float,
        reason: str,
        approval_id: Optional[str] = None,
    ) -> str:
        """Record a trust score change event.

        Returns:
            The generated event_id.
        """
        event_id = str(uuid.uuid4())
        now_ns = time.time_ns()
        with self._lock:
            self._conn().execute(
                """
                INSERT INTO trust_events (event_id, agent_id, delta, reason, approval_id, timestamp_ns)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, agent_id, delta, reason, approval_id, now_ns),
            )
            return event_id

    def get_trust_events_for_agent(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Return trust events for an agent, newest first."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM trust_events WHERE agent_id = ? ORDER BY timestamp_ns DESC LIMIT ?",
                (agent_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Audit events
    # ------------------------------------------------------------------

    def record_audit_event(
        self,
        event_type: str,
        agent_id: Optional[str] = None,
        action_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a gateway-level audit event.

        Returns:
            The generated event_id.
        """
        event_id = str(uuid.uuid4())
        now_ns = time.time_ns()
        with self._lock:
            self._conn().execute(
                """
                INSERT INTO audit_events (event_id, event_type, agent_id, action_id, approval_id, details_json, timestamp_ns)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, event_type, agent_id, action_id, approval_id, json.dumps(details or {}), now_ns),
            )
            return event_id

    def get_audit_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return recent audit events, newest first."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM audit_events ORDER BY timestamp_ns DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_audit_events_for_approval(self, approval_id: str) -> List[Dict[str, Any]]:
        """Return audit events for a specific approval request."""
        with self._lock:
            rows = self._conn().execute(
                "SELECT * FROM audit_events WHERE approval_id = ? ORDER BY timestamp_ns ASC",
                (approval_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_approval_stats(self) -> Dict[str, Any]:
        """Return aggregate stats for the dashboard."""
        with self._lock:
            conn = self._conn()
            total = conn.execute("SELECT COUNT(*) FROM approval_requests").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM approval_requests WHERE status = 'pending'"
            ).fetchone()[0]
            approved = conn.execute(
                "SELECT COUNT(*) FROM approval_requests WHERE status IN ('approved', 'executed')"
            ).fetchone()[0]
            denied = conn.execute(
                "SELECT COUNT(*) FROM approval_requests WHERE status = 'denied'"
            ).fetchone()[0]
            executed = conn.execute(
                "SELECT COUNT(*) FROM approval_requests WHERE status = 'executed'"
            ).fetchone()[0]
            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "denied": denied,
                "executed": executed,
            }

    def close_all(self) -> None:
        """Close the store and release resources."""
        self.close()
        logger.info("SqliteStore closed")
