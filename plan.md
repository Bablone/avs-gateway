# AVS Gateway v0.2 — Persistent Dashboard Approval Loop

## Current State
- v0.1.1: OpenClaw bridge, 307 tests pass, 4 decisions + adapter rejection proven
- Branch: ALEEZ
- Commit: 05ef60c
- REQUIRE_APPROVAL is a dead end: decision made, no execution, no persistence

## Objective
Turn REQUIRE_APPROVAL into a persisted human approval lifecycle:
persist → dashboard queue → human approve/deny → execute once or block → audit → trust update → survive restart

## Modules to Add

### 1. avs_gateway/storage/sqlite_store.py
- SqliteStore class using stdlib sqlite3
- Context managers, parameterized queries
- Tables: approval_requests, approval_decisions, trust_events, audit_events
- CRUD for all tables
- Schema creation from SQL file

### 2. avs_gateway/storage/schema.sql
- approval_requests: approval_id PK, action_id, agent_id, action_type, tool_name,
  operation, parameters_json, context_json, risk_score, trust_score, reason,
  status, created_at_ns, decided_at_ns, decided_by, decision_reason,
  executed_at_ns, execution_result_json, receipt_hash
- approval_decisions: decision_id PK, approval_id FK, decision, decided_by, reason, timestamp_ns
- trust_events: event_id PK, agent_id, delta, reason, approval_id, timestamp_ns
- audit_events: event_id PK, event_type, agent_id, action_id, approval_id, details_json, timestamp_ns

### 3. avs_gateway/core/approval_service.py
- ApprovalService class
- create_approval_request(action_request, decision) -> approval_id
- list_pending() -> list
- get_approval(approval_id) -> dict
- approve(approval_id, decided_by, reason) -> bool
- deny(approval_id, decided_by, reason) -> bool
- execute_approved_once(approval_id, tool_registry) -> result or None
- Replay protection: execute only if status == "approved", set to "executed"
- Trust updates on approve (+3), deny (-7)

### 4. Extend avs_gateway/server/gateway_server.py
- Add ApprovalService initialization
- POST /intercept: if REQUIRE_APPROVAL, persist approval request, return approval_id
- GET /approvals — list pending
- GET /approvals/{approval_id} — detail
- POST /approvals/{approval_id}/approve
- POST /approvals/{approval_id}/deny
- GET /approvals/{approval_id}/status

### 5. demo/dashboard_approval_loop_demo.py
- Submit action → REQUIRE_APPROVAL
- Show pending queue
- Human approves
- Execute once
- Attempt replay → blocked
- Evidence JSON export
- ASCII-only output

### 6. Tests
- avs_gateway/tests/unit/test_sqlite_store.py
- avs_gateway/tests/unit/test_approval_service.py
- avs_gateway/tests/integration/test_dashboard_approval_loop.py

## Invariants
- REQUIRE_APPROVAL cannot execute before approval
- Approved action executes once only
- Denied action never executes
- Pending approvals survive restart
- All approval decisions are persisted
- Existing 307 tests still pass
- No Linux-only paths, no Docker, no external services
