"""
Unit tests for avs_gateway.storage.sqlite_store

Tests CRUD operations, schema init, thread safety, and
the persistence contract (data survives close + reopen).
"""

import json
import os
import gc
import sys
import tempfile
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pytest

from avs_gateway.storage.sqlite_store import SqliteStore

DB_PATH = os.path.join(tempfile.gettempdir(), "avs_test_gateway.sqlite3")

def remove_db_with_retry(path: str, retries: int = 10, delay: float = 0.05) -> None:
    """Remove SQLite test DB on Windows even if handles close slightly late."""
    if not os.path.exists(path):
        return

    gc.collect()

    last_error = None
    for _ in range(retries):
        try:
            os.remove(path)
            return
        except PermissionError as exc:
            last_error = exc
            gc.collect()
            time.sleep(delay)

    raise last_error



@pytest.fixture
def store():
    """Fresh SqliteStore for each test."""
    if os.path.exists(DB_PATH):
        remove_db_with_retry(DB_PATH)
    s = SqliteStore(db_path=DB_PATH)
    s.init_schema()
    yield s
    s.close_all()
    if os.path.exists(DB_PATH):
        remove_db_with_retry(DB_PATH)


@pytest.fixture
def sample_action_dict():
    return {
        "action_id": "act-001",
        "agent_id": "agent-001",
        "action_type": "api",
        "tool_name": "api_tool",
        "operation": "POST",
        "parameters": {"endpoint": "/users"},
        "context": {"scope": "single"},
    }


@pytest.fixture
def sample_decision_dict():
    return {
        "risk_score": 35,
        "trust_score": 50,
        "reason": "Medium risk API call",
    }


class TestSqliteStore:
    """Tests for SqliteStore persistence layer."""

    # -- Schema --

    def test_init_schema_creates_tables(self, store):
        """Schema init should create all required tables."""
        conn = store._conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [r[0] for r in tables]
        assert "approval_requests" in table_names
        assert "approval_decisions" in table_names
        assert "trust_events" in table_names
        assert "audit_events" in table_names

    # -- Approval requests --

    def test_create_and_get_approval(self, store, sample_action_dict, sample_decision_dict):
        """Creating an approval request should make it retrievable."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        assert isinstance(aid, str) and len(aid) > 0

        approval = store.get_approval_request(aid)
        assert approval is not None
        assert approval["agent_id"] == "agent-001"
        assert approval["status"] == "pending"
        assert approval["risk_score"] == 35
        assert approval["trust_score"] == 50
        assert approval["reason"] == "Medium risk API call"

    def test_list_pending_empty(self, store):
        """No approvals means empty pending list."""
        assert store.list_pending_approvals() == []

    def test_list_pending_filters(self, store, sample_action_dict, sample_decision_dict):
        """list_pending should only return pending approvals."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        pending = store.list_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["approval_id"] == aid

        # After approval, should not appear in pending
        store.update_approval_status(aid, "approved", decided_by="admin", decision_reason="ok")
        pending_after = store.list_pending_approvals()
        assert len(pending_after) == 0

    def test_update_approval_status(self, store, sample_action_dict, sample_decision_dict):
        """Updating status should work and return True."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        ok = store.update_approval_status(aid, "approved", decided_by="admin", decision_reason="ok")
        assert ok is True

        approval = store.get_approval_request(aid)
        assert approval["status"] == "approved"
        assert approval["decided_by"] == "admin"

    def test_update_approval_status_not_found(self, store):
        """Updating nonexistent approval should return False."""
        ok = store.update_approval_status("nonexistent-id", "approved")
        assert ok is False

    def test_record_execution_result(self, store, sample_action_dict, sample_decision_dict):
        """Execution result should be recorded and status set to executed."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        store.update_approval_status(aid, "approved")
        ok = store.record_execution_result(aid, json.dumps({"success": True}))
        assert ok is True

        approval = store.get_approval_request(aid)
        assert approval["status"] == "executed"
        assert "success" in approval["execution_result_json"]

    # -- Approval decisions --

    def test_record_decision(self, store, sample_action_dict, sample_decision_dict):
        """Decisions should be recordable and retrievable."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        did = store.record_approval_decision(aid, "approved", "admin_alice", "Verified")
        assert isinstance(did, str) and len(did) > 0

        decisions = store.get_decisions_for_approval(aid)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "approved"
        assert decisions[0]["decided_by"] == "admin_alice"

    # -- Trust events --

    def test_record_trust_event(self, store):
        """Trust events should be recordable and retrievable."""
        eid = store.record_trust_event("agent-001", 3.0, "human approved", None)
        assert isinstance(eid, str) and len(eid) > 0

        events = store.get_trust_events_for_agent("agent-001")
        assert len(events) == 1
        assert events[0]["delta"] == 3.0
        assert events[0]["reason"] == "human approved"

    # -- Audit events --

    def test_record_audit_event(self, store):
        """Audit events should be recordable and retrievable."""
        eid = store.record_audit_event(
            event_type="approval_created",
            agent_id="agent-001",
            approval_id=None,
            details={"tool_name": "api_tool"},
        )
        assert isinstance(eid, str) and len(eid) > 0

        events = store.get_audit_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "approval_created"

    def test_get_audit_for_approval(self, store, sample_action_dict, sample_decision_dict):
        """Audit events should be filterable by approval_id."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        store.record_audit_event(event_type="approval_approved", approval_id=aid)
        store.record_audit_event(event_type="approval_executed", approval_id=aid)
        store.record_audit_event(event_type="gateway_intercept")  # unrelated

        timeline = store.get_audit_events_for_approval(aid)
        assert len(timeline) == 2
        assert timeline[0]["event_type"] == "approval_approved"
        assert timeline[1]["event_type"] == "approval_executed"

    # -- Stats --

    def test_approval_stats(self, store, sample_action_dict, sample_decision_dict):
        """Stats should reflect the correct counts."""
        # Create 4 approvals with different statuses
        a1 = store.create_approval_request(sample_action_dict, sample_decision_dict)
        a2 = store.create_approval_request(sample_action_dict, sample_decision_dict)
        a3 = store.create_approval_request(sample_action_dict, sample_decision_dict)
        a4 = store.create_approval_request(sample_action_dict, sample_decision_dict)

        store.update_approval_status(a1, "approved")
        store.update_approval_status(a2, "approved")
        store.record_execution_result(a2, "{}")
        store.update_approval_status(a3, "denied")
        # a4 stays pending

        stats = store.get_approval_stats()
        assert stats["total"] == 4
        assert stats["pending"] == 1
        assert stats["approved"] == 2  # approved + executed
        assert stats["denied"] == 1
        assert stats["executed"] == 1

    # -- Persistence: close + reopen --

    def test_data_survives_reopen(self, store, sample_action_dict, sample_decision_dict):
        """Data must persist after close + reopen (restart simulation)."""
        aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
        store.close_all()

        # Reopen same DB file
        store2 = SqliteStore(db_path=DB_PATH)
        # No init_schema needed -- tables already exist
        approval = store2.get_approval_request(aid)
        assert approval is not None
        assert approval["agent_id"] == "agent-001"
        store2.close_all()

    # -- Thread safety --

    def test_concurrent_creates(self, store, sample_action_dict, sample_decision_dict):
        """Concurrent creates should not corrupt the database."""
        ids = []
        errors = []

        def worker():
            try:
                aid = store.create_approval_request(sample_action_dict, sample_decision_dict)
                ids.append(aid)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent creates: {errors}"
        assert len(ids) == 10
        # All unique
        assert len(set(ids)) == 10

    # -- Reset --

    def test_reset_clears_data(self, store, sample_action_dict, sample_decision_dict):
        """Reset should clear all data."""
        store.create_approval_request(sample_action_dict, sample_decision_dict)
        store.reset()
        assert store.list_pending_approvals() == []
        assert store.get_audit_events() == []
