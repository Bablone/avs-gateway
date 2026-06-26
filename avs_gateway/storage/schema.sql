-- AVS Gateway v0.2 — SQLite schema
-- Approval loop, audit, and trust persistence

-- Approval requests: actions waiting for human review
CREATE TABLE IF NOT EXISTS approval_requests (
    approval_id     TEXT PRIMARY KEY,
    action_id       TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    operation       TEXT NOT NULL,
    parameters_json TEXT NOT NULL DEFAULT '{}',
    context_json    TEXT NOT NULL DEFAULT '{}',
    risk_score      REAL NOT NULL,
    trust_score     REAL NOT NULL,
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'denied', 'executed', 'expired')),
    created_at_ns   INTEGER NOT NULL,
    decided_at_ns   INTEGER,
    decided_by      TEXT,
    decision_reason TEXT,
    executed_at_ns  INTEGER,
    execution_result_json TEXT,
    receipt_hash    TEXT
);

-- Approval decisions: human decisions on approval requests
CREATE TABLE IF NOT EXISTS approval_decisions (
    decision_id     TEXT PRIMARY KEY,
    approval_id     TEXT NOT NULL REFERENCES approval_requests(approval_id),
    decision        TEXT NOT NULL CHECK (decision IN ('approved', 'denied')),
    decided_by      TEXT NOT NULL,
    reason          TEXT NOT NULL,
    timestamp_ns    INTEGER NOT NULL
);

-- Trust events: trust score changes from behavior and approvals
CREATE TABLE IF NOT EXISTS trust_events (
    event_id        TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    delta           REAL NOT NULL,
    reason          TEXT NOT NULL,
    approval_id     TEXT REFERENCES approval_requests(approval_id),
    timestamp_ns    INTEGER NOT NULL
);

-- Audit events: gateway-level events for dashboard timeline
CREATE TABLE IF NOT EXISTS audit_events (
    event_id        TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL CHECK (
                        event_type IN (
                            'approval_created', 'approval_approved',
                            'approval_denied', 'approval_executed',
                            'approval_replay_blocked', 'approval_expired', 'trust_updated',
                            'gateway_intercept', 'gateway_decision'
                        )
                    ),
    agent_id        TEXT,
    action_id       TEXT,
    approval_id     TEXT REFERENCES approval_requests(approval_id),
    details_json    TEXT NOT NULL DEFAULT '{}',
    timestamp_ns    INTEGER NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_agent ON approval_requests(agent_id);
CREATE INDEX IF NOT EXISTS idx_approval_created ON approval_requests(created_at_ns);
CREATE INDEX IF NOT EXISTS idx_decision_approval ON approval_decisions(approval_id);
CREATE INDEX IF NOT EXISTS idx_trust_agent ON trust_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_approval ON audit_events(approval_id);
