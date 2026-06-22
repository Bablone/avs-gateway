# ROADMAP v0.4 — Agentic Payments Guard

> **Document Version:** 0.1-draft  
> **Status:** PLANNED — not implemented in v0.3.6  
> **Target Release:** v0.4.x series  
> **Last Updated:** 2026-07-07  
> **Module Name:** `avs_gateway.payments_guard`  

---

## 1. Overview

### What This Is

Agentic Payments Guard is a governance module that extends AVS's existing action-control framework to payment-aware actions. It treats payment as one action class among many — not a special case — and applies AVS's policy engine (identity verification, budget enforcement, counterparty allowlisting, replay protection, fail-closed settlement) before any payment intent reaches a settlement rail.

### What This Is NOT

It does NOT implement wallets, hold money, process transactions, or replace existing payment protocols (x402, AP4M, ACP, AP2, TAP). It is a **control plane** that governs whether a payment action may proceed, and produces tamper-evident receipts of that decision.

### Why It Exists

The market is moving fast:

| Player | Launch / Status | Gap AVS Fills |
|--------|----------------|---------------|
| Mastercard AP4M | June 2026, 30+ partners | No governance layer; trust-all model |
| x402 | Production, critical vulns (97.76% leakage) | No replay guard, no budget control, no PII filter |
| AWS AgentCore Payments | Operational | Vendor-locked, no open policy framework |
| Google Pay.sh | Operational | Same vendor-lock issue |
| Circle Nanopayments | Operational | Crypto-only, no unified governance |
| Catena | "Control plane for agent payments" | Money-movement only, not general action control |

**AVS's wedge:** The only open, protocol-agnostic **action control plane** — payment is one action class among many. We govern *all* actions, not just payments.

### Design Philosophy

> "Payment is one action class. AVS governs all action classes."

The Payment Guard module extends the existing `ActionRequest → Policy Engine → Decision` pipeline with payment-specific policy checks. It adds objects, checks, and enriched receipts. It does not fork the architecture.

---

## 2. Core Objects (Interfaces Defined, Not Implemented)

All objects are defined by their **interface** (purpose, fields, relationships). Implementation is deferred to v0.4.x development.

---

### 2.1 PaymentActionRequest

Extends the existing `ActionRequest` for actions that involve payment.

**Purpose:** Represents an agent's intent to perform a payment action. Wraps the standard action request with payment-specific context so the policy engine can apply payment-aware checks.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `base_request` | `ActionRequest` | The underlying action request (tool, parameters, agent identity) |
| `payment_rail` | `str` | Target rail: `x402`, `ap4m`, `acp`, `stripe`, `circle`, `custom` |
| `amount` | `Decimal` | Payment amount (arbitrary precision) |
| `currency` | `str` | ISO 4217 currency code or chain-native symbol |
| `counterparty_id` | `str` | Merchant, endpoint, or recipient identifier |
| `counterparty_endpoint` | `URL` | Resolved HTTPS endpoint for the payment |
| `resource_hash` | `ResourceBinding` | Hash binding payment to a specific resource (Section 2.4) |
| `idempotency_key` | `IdempotencyKey` | Unique key for this payment intent (Section 2.7) |
| `payment_metadata` | `dict[str, Any]` | Rail-specific metadata; scanned for PII leakage |
| `requested_at` | `datetime` | Timestamp of request (UTC) |
| `nonce` | `str` | Cryptographic nonce for replay detection (Section 2.8) |

**Relationship:** One `PaymentActionRequest` is evaluated by one `PolicyEngine` run. Embeds `ActionRequest`, `ResourceBinding`, `IdempotencyKey`.

---

### 2.2 BudgetPolicy

Spending limits scoped by agent, tool, counterparty, and time period.

**Purpose:** Defines how much an agent is permitted to spend, under what conditions, over what window. Enforces hard caps and produces pre/post budget state for receipts.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `policy_id` | `UUID` | Unique policy identifier |
| `agent_id` | `str` | Agent this policy applies to; `*` for default |
| `tool_id` | `str` | Tool this policy applies to; `*` for all payment tools |
| `counterparty_id` | `str` | Merchant this policy applies to; `*` for all |
| `max_amount_per_tx` | `Decimal` | Single-transaction limit |
| `max_amount_per_day` | `Decimal` | Rolling 24-hour window limit |
| `max_amount_per_month` | `Decimal` | Rolling 30-day window limit |
| `currency_scope` | `str` | Currency this policy applies to; `*` for any |
| `period_reset` | `str` | `rolling_24h`, `rolling_30d`, `calendar_day`, `calendar_month` |
| `current_daily_spend` | `Decimal` | Mutable: accumulated spend in current period |
| `current_monthly_spend` | `Decimal` | Mutable: accumulated spend in current month window |
| `last_tx_at` | `datetime` | Timestamp of last evaluated transaction |
| `policy_hash` | `str` | SHA-256 of canonicalized policy fields (for receipt verification) |

**Relationship:** Many `BudgetPolicy` entries may apply to one `PaymentActionRequest`. The most specific matching policy wins (agent_id + tool_id + counterparty_id > agent_id + tool_id > agent_id > default).

---

### 2.3 CounterpartyPolicy

Merchant/endpoint allowlists, risk scores, and trust tiers.

**Purpose:** Prevents payments to unauthorized or high-risk counterparties. Learns from settlement outcomes to adjust risk scores dynamically.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `counterparty_id` | `str` | Unique merchant/endpoint identifier |
| `endpoint_url` | `URL` | Verified HTTPS endpoint |
| `status` | `str` | `ALLOWED`, `BLOCKED`, `REQUIRE_APPROVAL`, `PENDING_REVIEW` |
| `risk_score` | `float` | 0.0 (trusted) to 1.0 (high risk); computed from history |
| `trust_tier` | `str` | `T1` (verified enterprise), `T2` (known partner), `T3` (community), `T4` (unverified) |
| `first_seen_at` | `datetime` | First observed interaction timestamp |
| `total_tx_count` | `int` | Number of settled transactions with this counterparty |
| `total_failure_count` | `int` | Number of failed/reversed transactions |
| `failure_rate` | `float` | `total_failure_count / total_tx_count` or 0.0 |
| `domains` | `list[str]` | Verified domain names associated with this counterparty |
| `certificate_pin` | `str` | Expected TLS certificate fingerprint |
| `added_by` | `str` | `ADMIN`, `AUTO_DISCOVERY`, `AGENT_REQUEST` |

**Relationship:** Referenced by `PaymentActionRequest.counterparty_id`. Used by the `merchant_allowed` and `settlement_capacity_available` checks.

---

### 2.4 ResourceBinding

Binds a payment intent to a specific resource, preventing cross-resource substitution attacks.

**Purpose:** Ensures that a payment approved for Resource A cannot be replayed against Resource B. The payment is cryptographically bound to the intended resource.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `resource_type` | `str` | `api_endpoint`, `file_download`, `compute_slot`, `data_stream`, `service_call` |
| `resource_uri` | `str` | Canonical URI identifying the resource |
| `resource_hash` | `str` | SHA-256 of `resource_uri + resource_params + counterparty_endpoint` |
| `binding_parameters` | `dict[str, Any]` | Resource-specific parameters (e.g., API method, file ID, compute spec) |
| `bound_at` | `datetime` | When the binding was established |
| `expires_at` | `datetime` | Binding expiration; payment must settle before this |

**Relationship:** Embedded in `PaymentActionRequest`. The `resource_hash_matches` check (Section 3) verifies that the resource hash in the request matches the resource being accessed. Prevents the attack where an approved payment for a cheap API call is substituted for an expensive one.

---

### 2.5 PaymentIntentHash

Deterministic hash of the complete payment intent, used for idempotency and evidence.

**Purpose:** Creates a tamper-evident fingerprint of the payment intent. Two identical intents produce identical hashes. Any change (amount, counterparty, resource) produces a different hash.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `hash_algorithm` | `str` | Always `sha3-256` |
| `canonical_input` | `str` | Ordered, serialized representation of all payment fields |
| `intent_hash` | `str` | Hex digest of `sha3-256(canonical_input)` |
| `computed_at` | `datetime` | When the hash was generated |

**Canonical Input Ordering (deterministic):**
```
canonical_input = ordered_json({
    "agent_id": <agent_id>,
    "owner_id": <owner_id>,
    "tool_id": <tool_id>,
    "payment_rail": <rail>,
    "amount": str(amount),          # Decimal as string
    "currency": <currency>,
    "counterparty_id": <counterparty_id>,
    "counterparty_endpoint": str(endpoint),
    "resource_hash": <resource_hash>,
    "nonce": <nonce>,
    "requested_at": requested_at.isoformat()
})
```

**Relationship:** Produced during `PaymentActionRequest` construction. Stored in the `IdempotencyKey` and `ASR-1 Receipt` for verification.

---

### 2.6 SettlementState

Tracks the lifecycle of a payment through settlement.

**Purpose:** Maintains state machine for settlement. Enables fail-closed behavior when settlement rails are degraded.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `state` | `str` | `PENDING`, `SUBMITTED`, `CONFIRMED`, `FAILED`, `REVERSED`, `TIMEOUT` |
| `rail_status` | `str` | Last-known status from the payment rail |
| `submitted_at` | `datetime` | When payment was submitted to rail |
| `confirmed_at` | `datetime` | When confirmation was received |
| `failed_at` | `datetime` | When failure was detected |
| `failure_reason` | `str` | Human-readable failure description |
| `retry_count` | `int` | Number of retry attempts |
| `rail_latency_ms` | `int` | Round-trip time to rail (if available) |
| `degraded_threshold_ms` | `int` | Threshold above which rail is considered degraded |

**State Transitions:**
```
PENDING → SUBMITTED → CONFIRMED  (success path)
PENDING → SUBMITTED → FAILED     (hard failure)
PENDING → SUBMITTED → TIMEOUT    (soft failure, retry)
PENDING → SUBMITTED → REVERSED   (chargeback / reversal)
```

**Relationship:** Updated by the settlement adapter (outside AVS). The `settlement_capacity_available` check reads `SettlementState.state` to decide whether to ALLOW or DENY new payments.

---

### 2.7 IdempotencyKey

Prevents replay attacks by ensuring each payment intent is processed exactly once.

**Purpose:** Direct countermeasure to the x402 replay vulnerability (97.76% leakage demonstrated in independent research). Once an idempotency key is seen, any subsequent request with the same key is rejected regardless of signatures or proofs.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `key_value` | `str` | UUIDv4 or deterministic key derived from intent |
| `intent_hash` | `str` | `PaymentIntentHash.intent_hash` — binds key to specific intent |
| `status` | `str` | `UNUSED`, `PENDING`, `COMMITTED`, `ROLLED_BACK` |
| `first_seen_at` | `datetime` | When this key was first observed |
| `committed_at` | `datetime` | When the key transitioned to COMMITTED |
| `agent_id` | `str` | Agent that submitted this key |
| `owner_id` | `str` | Owner (human) responsible for this agent |

**Relationship:** Created from `PaymentActionRequest`. Checked by the `nonce_unused` policy check. Stored in the `ReplayGuard` registry.

---

### 2.8 ReplayGuard

Nonce-based replay detection registry.

**Purpose:** Maintains the global set of seen idempotency keys and nonces. Prevents replay across all payment rails and all agents.

**Key Fields (Registry Entry):**

| Field | Type | Description |
|-------|------|-------------|
| `nonce` | `str` | Cryptographic nonce from the request |
| `idempotency_key` | `str` | Reference to `IdempotencyKey.key_value` |
| `timestamp` | `datetime` | When the nonce was consumed |
| `window_start` | `datetime` | Start of the replay-detection window |
| `window_end` | `datetime` | End of the replay-detection window |
| `source_agent` | `str` | Agent that submitted this nonce |

**Key Methods (Interface):**

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `check_nonce(nonce, agent_id, timestamp)` | nonce string, agent ID, timestamp | `OK` or `REPLAY_DETECTED` | Verifies nonce has not been seen within the window |
| `commit_nonce(nonce, idempotency_key)` | nonce, key | `COMMITTED` or `CONFLICT` | Atomically records nonce as consumed |
| `get_window(agent_id)` | agent ID | `(window_start, window_end)` | Returns current replay window for agent |
| `prune_expired(before)` | cutoff timestamp | count removed | Removes entries older than threshold |

**Relationship:** Referenced by `PaymentActionRequest.nonce`. Checked by `nonce_unused` policy check. Writes to persistent store on `commit_nonce`.

---

### 2.9 ApprovalTicket

Human-in-the-loop approval for high-value or high-risk payments.

**Purpose:** When policy evaluation produces `REQUIRE_APPROVAL`, an `ApprovalTicket` is created. The payment action is held in `PENDING_APPROVAL` state until a human owner approves or denies.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | `UUID` | Unique approval ticket identifier |
| `payment_request` | `PaymentActionRequest` | The request awaiting approval |
| `policy_trigger` | `str` | Which policy triggered approval requirement |
| `trigger_reason` | `str` | Human-readable explanation |
| `risk_score` | `float` | Computed risk score at time of request |
| `requested_at` | `datetime` | When the ticket was created |
| `expires_at` | `datetime` | Ticket expiration (auto-deny if not resolved) |
| `status` | `str` | `PENDING`, `APPROVED`, `DENIED`, `EXPIRED` |
| `resolved_by` | `str` | Owner ID who resolved the ticket |
| `resolved_at` | `datetime` | When the ticket was resolved |
| `resolution_comment` | `str` | Optional human comment |

**Relationship:** Created by the `human_approval_required_above_threshold` check. Referenced in the ASR-1 receipt when status is `REQUIRE_APPROVAL`.

---

### 2.10 ASR-1 Receipt (Enriched)

The existing ASR-1 receipt format from v0.3.6, extended with payment-specific fields.

**Purpose:** Tamper-evident evidence of the AVS decision for a payment action. Already exists in v0.3.6; v0.4.x enriches it with payment fields.

**Existing Fields (v0.3.6):**
- `receipt_id`, `timestamp`, `agent_id`, `owner_id`, `intent_id`
- `tool_id`, `action_params_hash`, `decision`, `reasons`
- `policy_version`, `audit_hash`, `signature`

**Payment Enrichment Fields (v0.4.x):**

| Field | Type | Description |
|-------|------|-------------|
| `payment_rail` | `str` | Target payment rail |
| `amount` | `str` | Payment amount (as string for precision) |
| `currency` | `str` | Currency code |
| `counterparty_id` | `str` | Merchant/recipient identifier |
| `counterparty_endpoint` | `str` | Resolved endpoint URL |
| `resource_hash` | `str` | `ResourceBinding.resource_hash` |
| `payment_intent_hash` | `str` | `PaymentIntentHash.intent_hash` |
| `policy_hash` | `str` | Hash of all applicable policies |
| `budget_remaining_before` | `str` | Budget before this tx (for relevant policy) |
| `budget_remaining_after` | `str` | Budget after this tx (only if ALLOW) |
| `settlement_state` | `str` | `SettlementState.state` at time of decision |
| `idempotency_key` | `str` | `IdempotencyKey.key_value` |
| `nonce` | `str` | Consumed nonce |
| `risk_score` | `float` | Computed composite risk score (0.0–1.0) |
| `approval_ticket` | `str` | `ApprovalTicket.ticket_id` if `REQUIRE_APPROVAL` |
| `counterparty_risk_score` | `float` | `CounterpartyPolicy.risk_score` at time of decision |
| `counterparty_trust_tier` | `str` | `CounterpartyPolicy.trust_tier` |
| `pii_scan_result` | `str` | `CLEAN`, `LEAK_DETECTED`, `SCAN_FAILED` |
| `replay_check` | `str` | `PASSED` or `REPLAY_DETECTED` |

**Relationship:** Produced by the AVS Gateway after policy evaluation. Verified by `avs receipt verify`. Serves as legal evidence of the governance decision.

---

## 3. Policy Checks

Each check is evaluated by the Policy Engine in a defined order. All checks must pass for ALLOW. Any check may produce DENY, QUARANTINE, or REQUIRE_APPROVAL.

### 3.1 agent_identity_verified

| Attribute | Value |
|-----------|-------|
| **Name** | `agent_identity_verified` |
| **Description** | Verifies the agent's cryptographic identity (DID or attestation) is valid, not revoked, and matches the request. |
| **Prevents** | Spoofed or stolen agent credentials submitting payment requests. |
| **Decision on Failure** | `DENY` — unverified agents cannot make payment requests. |
| **Implementation Note** | Delegates to existing `AgentIdentity.verify()` from v0.3.6. |

---

### 3.2 user_intent_bound

| Attribute | Value |
|-----------|-------|
| **Name** | `user_intent_bound` |
| **Description** | Confirms the payment action is bound to a valid, non-expired user authorization (AP2-style mandate). The user has explicitly authorized this agent to make payments on their behalf. |
| **Prevents** | Rogue agent payments without human authorization; en AP2 mandate model. |
| **Decision on Failure** | `DENY` — no mandate, no payment. |
| **Implementation Note** | Checks `ActionRequest.authorization` field (AP2 mandate token or equivalent). |

---

### 3.3 amount_within_budget

| Attribute | Value |
|-----------|-------|
| **Name** | `amount_within_budget` |
| **Description** | Evaluates the payment amount against all applicable `BudgetPolicy` entries. Checks per-tx, daily, and monthly limits. Updates budget state atomically. |
| **Prevents** | Budget exhaustion attacks; agents spending beyond authorized limits. |
| **Decision on Failure** | `DENY` — hard budget cap, no exceptions. |
| **Implementation Note** | Uses policy-specific matching (most specific wins). Budget update is atomic with decision to prevent race-condition overdrafts. |

---

### 3.4 merchant_allowed

| Attribute | Value |
|-----------|-------|
| **Name** | `merchant_allowed` |
| **Description** | Checks the counterparty against `CounterpartyPolicy`. Verifies status is `ALLOWED` or `REQUIRE_APPROVAL`, endpoint matches, TLS certificate pins. |
| **Prevents** | Payments to unknown, blocked, or typosquatted merchants. |
| **Decision on Failure** | `QUARANTINE` if counterparty is unknown (new discovery); `DENY` if blocked. |
| **Implementation Note** | For `REQUIRE_APPROVAL` status, triggers `ApprovalTicket` creation. |

---

### 3.5 resource_hash_matches

| Attribute | Value |
|-----------|-------|
| **Name** | `resource_hash_matches` |
| **Description** | Recomputes the resource hash from the request context and compares it to the `resource_hash` in the payment request. |
| **Prevents** | Cross-resource substitution: approved payment for cheap resource replayed against expensive resource. |
| **Decision on Failure** | `DENY` — hash mismatch means the payment is not for the intended resource. |
| **Implementation Note** | Canonical hash computation must be deterministic across implementations. |

---

### 3.6 nonce_unused

| Attribute | Value |
|-----------|-------|
| **Name** | `nonce_unused` |
| **Description** | Queries `ReplayGuard.check_nonce()` to verify the nonce has not been consumed within the detection window. |
| **Prevents** | **Replay attacks** — the critical x402 vulnerability where a valid payment proof is replayed to extract multiple payments. |
| **Decision on Failure** | `QUARANTINE` — replayed payment is isolated for investigation, not silently processed. |
| **Implementation Note** | `ReplayGuard.commit_nonce()` is called atomically with the ALLOW decision. If decision is not ALLOW, nonce remains available. |

---

### 3.7 settlement_capacity_available

| Attribute | Value |
|-----------|-------|
| **Name** | `settlement_capacity_available` |
| **Description** | Checks `SettlementState` for the target rail. If rail is in `FAILED`, `TIMEOUT`, or showing degraded latency, denies new payments. |
| **Prevents** | Payments submitted to broken rails (guaranteed failure); double-submission during rail degradation. |
| **Decision on Failure** | `DENY` — **fail-closed** design. Degraded rails reject new payments rather than risk loss. |
| **Implementation Note** | Reads from settlement adapter health check. Does not wait for confirmation — makes decision on current known state. |

---

### 3.8 pii_not_leaking_in_metadata

| Attribute | Value |
|-----------|-------|
| **Name** | `pii_not_leaking_in_metadata` |
| **Description** | Scans `PaymentActionRequest.payment_metadata` for PII patterns: email addresses, phone numbers, SSN, credit card numbers, names, addresses. |
| **Prevents** | **PII leakage in payment metadata** — the x402 demonstrated vulnerability where 97.76% of payment flows leaked sensitive data in unencrypted metadata. |
| **Decision on Failure** | `DENY` or `REQUIRE_APPROVAL` based on severity classification. |
| **Implementation Note** | Uses regex + ML-based PII detection. Results recorded in receipt `pii_scan_result`. |

---

### 3.9 human_approval_required_above_threshold

| Attribute | Value |
|-----------|-------|
| **Name** | `human_approval_required_above_threshold` |
| **Description** | If the composite risk score (from counterparty risk, amount, agent history, metadata scan) exceeds a configurable threshold, requires human approval. |
| **Prevents** | High-value/high-risk payments without human oversight. |
| **Decision on Trigger** | `REQUIRE_APPROVAL` — creates `ApprovalTicket`, payment held pending. |
| **Implementation Note** | Composite risk score formula is configurable per deployment. Default: `risk = 0.4 * counterparty_risk + 0.3 * amount_risk + 0.2 * agent_history_risk + 0.1 * metadata_risk`. |

---

### 3.10 fail_closed_on_settlement_uncertainty

| Attribute | Value |
|-----------|-------|
| **Name** | `fail_closed_on_settlement_uncertainty` |
| **Description** | If any settlement-state query returns an error, timeout, or ambiguous result, the check fails. |
| **Prevents** | Payments approved based on stale or unknown settlement state. |
| **Decision on Failure** | `DENY` — **fail-closed by design**. Uncertainty is treated as "unsafe." |
| **Implementation Note** | This is the final check in the chain. It ensures the pipeline fails safely even when dependencies are unavailable. |

---

### Check Evaluation Order

```
1. agent_identity_verified          → DENY if fail
2. user_intent_bound                → DENY if fail
3. nonce_unused                     → QUARANTINE if fail
4. pii_not_leaking_in_metadata      → DENY or REQUIRE_APPROVAL if fail
5. merchant_allowed                 → DENY or QUARANTINE or REQUIRE_APPROVAL if fail
6. amount_within_budget             → DENY if fail
7. resource_hash_matches            → DENY if fail
8. settlement_capacity_available    → DENY if fail
9. human_approval_required_above_threshold → REQUIRE_APPROVAL if triggered
10. fail_closed_on_settlement_uncertainty  → DENY if fail
```

> **Rationale for order:** Identity and intent are verified first (cheap, deterministic). Replay detection comes early to prevent wasting resources on known-bad requests. Budget check is after merchant check so that budget is not consumed for blocked merchants. Settlement checks are late because they depend on external state. Human approval is the final gating step before ALLOW.

---

## 4. Demo Scenarios

| # | Scenario | Setup | Expected AVS Decision | What It Proves |
|---|----------|-------|----------------------|----------------|
| 1 | Approved agent pays £0.03 for API data | Agent: verified, £100/day budget; Counterparty: T1 trusted; Amount: £0.03; Rail: healthy | `ALLOW` | Normal payment flow — baseline happy path |
| 2 | Agent pays approved agent for service | Agent A (buyer): verified; Agent B (seller): verified, T2 trust; Amount: £5.00 | `ALLOW` | Agent-to-agent payment — extends to multi-agent economies |
| 3 | Agent exceeds daily budget | Agent: £10.00/day spent, requesting £5.00 when limit is £10.00/day | `DENY` | **Budget policy enforcement** — hard cap, no exceptions |
| 4 | Agent replays old payment proof | Same idempotency key and nonce as a previous ALLOWED payment | `QUARANTINE` | **Replay attack prevention** — x402 vulnerability countermeasure |
| 5 | Agent hits unregistered merchant endpoint | Counterparty: not in `CounterpartyPolicy` registry | `QUARANTINE` | **Counterparty policy** — unknown merchants isolated, not silently processed |
| 6 | Settlement rail unavailable | Rail status: `TIMEOUT`, latency > degraded threshold | `DENY` | **Fail-closed design** — broken rails reject payments, not accept them |
| 7 | Payment metadata leaks PII | Metadata contains email address `user@example.com` | `DENY` or `REQUIRE_APPROVAL` | **Privacy guard** — x402 PII leakage countermeasure |

### Scenario Execution Matrix

| Check | Scenario 1 | Scenario 2 | Scenario 3 | Scenario 4 | Scenario 5 | Scenario 6 | Scenario 7 |
|-------|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|:----------:|
| agent_identity_verified | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| user_intent_bound | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| nonce_unused | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| pii_not_leaking | ✅ | ✅ | ✅ | — | — | — | ❌ |
| merchant_allowed | ✅ | ✅ | ✅ | — | ❌ | ✅ | — |
| amount_within_budget | ✅ | ✅ | ❌ | — | — | ✅ | — |
| resource_hash_matches | ✅ | ✅ | — | — | — | ✅ | — |
| settlement_capacity | ✅ | ✅ | — | — | — | ❌ | — |
| **Decision** | **ALLOW** | **ALLOW** | **DENY** | **QUARANTINE** | **QUARANTINE** | **DENY** | **DENY** |

> ❌ = check failure (first failure determines outcome). — = not reached (short-circuit).

---

## 5. Evidence Output (Enriched ASR-1 Receipt)

When the Policy Engine evaluates a `PaymentActionRequest`, it produces an enriched ASR-1 receipt. Below is the complete receipt format for payment actions.

### Top-Level Receipt Structure

```json
{
  "receipt_version": "ASR-1.1",
  "receipt_id": "uuid",
  "timestamp": "2026-07-07T12:00:00Z",
  
  "agent_id": "agent_abc123",
  "owner_id": "user_xyz789",
  "intent_id": "intent_def456",
  
  "tool_id": "tool_api_payment",
  "action_params_hash": "sha256(params)",
  
  "decision": "ALLOW | DENY | REQUIRE_APPROVAL | QUARANTINE",
  "reasons": ["check_name: result"],
  
  "payment_context": {
    "payment_rail": "x402 | ap4m | acp | stripe | circle | custom",
    "amount": "0.03",
    "currency": "GBP",
    "counterparty_id": "merchant_api_corp",
    "counterparty_endpoint": "https://api.merchant.com/v1/pay",
    "counterparty_risk_score": 0.05,
    "counterparty_trust_tier": "T1"
  },
  
  "integrity": {
    "resource_hash": "sha256(resource)",
    "payment_intent_hash": "sha3-256(canonical_intent)",
    "policy_hash": "sha256(applicable_policies)",
    "idempotency_key": "uuid_key",
    "nonce": "cryptographic_nonce",
    "replay_check": "PASSED | REPLAY_DETECTED"
  },
  
  "budget_state": {
    "policy_id": "policy_uuid",
    "budget_remaining_before": "10.00",
    "budget_remaining_after": "9.97",
    "currency": "GBP"
  },
  
  "settlement_state": "PENDING | SUBMITTED | CONFIRMED | FAILED | REVERSED | TIMEOUT",
  
  "risk": {
    "risk_score": 0.12,
    "risk_breakdown": {
      "counterparty_risk": 0.05,
      "amount_risk": 0.01,
      "agent_history_risk": 0.03,
      "metadata_risk": 0.03
    }
  },
  
  "approval": {
    "required": false,
    "approval_ticket": null,
    "resolved_by": null
  },
  
  "privacy": {
    "pii_scan_result": "CLEAN | LEAK_DETECTED | SCAN_FAILED",
    "pii_findings": []
  },
  
  "policy_version": "v0.4.0",
  "audit_hash": "sha256(full_receipt)",
  "signature": "ed25519_signature"
}
```

### Receipt Verification

The `avs receipt verify` command (existing in v0.3.6) will verify:

1. **Signature validity** — Ed25519 signature over `audit_hash`
2. **Audit hash integrity** — SHA-256 of canonicalized receipt content
3. **Payment intent hash** — Recompute and compare `payment_intent_hash`
4. **Policy hash** — Verify against current policy (or historical policy at receipt timestamp)
5. **Idempotency key** — Verify key exists in `ReplayGuard` and is `COMMITTED`
6. **Budget consistency** — `budget_remaining_before - amount == budget_remaining_after` (for ALLOW)
7. **Nonce consumed** — Verify nonce is in `ReplayGuard` registry
8. **Decision consistency** — All `reasons` align with the final `decision`

### Receipt as Legal Evidence

The enriched ASR-1 receipt serves as:
- **Audit trail** — tamper-evident record of why a payment was allowed/denied
- **Dispute resolution** — evidence that governance rules were followed
- **Compliance proof** — demonstrates budget controls, counterparty checks, privacy scanning
- **Forensic artifact** — replay detection and quarantine records for incident investigation

---

## 6. Architecture

### Component Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Agent      │────▶│  ActionRequest   │────▶│    AVS Gateway      │
│  (any)       │     │  (existing)      │     │    (existing)       │
└──────────────┘     └──────────────────┘     └─────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │     Policy Engine       │
                                          │     (existing v0.3.6)   │
                                          │                         │
                                          │  ┌───────────────────┐  │
                                          │  │  Payment Guard    │  │
                                          │  │  Module (v0.4.x)  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │   Budget    │  │  │
                                          │  │  │   Policy    │  │  │
                                          │  │  │   Engine    │  │  │
                                          │  │  └─────────────┘  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │ Counterparty│  │  │
                                          │  │  │   Policy    │  │  │
                                          │  │  └─────────────┘  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │  Settlement │  │  │
                                          │  │  │   Monitor   │  │  │
                                          │  │  └─────────────┘  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │  ReplayGuard│  │  │
                                          │  │  │   (nonce)   │  │  │
                                          │  │  └─────────────┘  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │  PII Scanner│  │  │
                                          │  │  └─────────────┘  │  │
                                          │  │                   │  │
                                          │  │  ┌─────────────┐  │  │
                                          │  │  │   Approval  │  │  │
                                          │  │  │   Ticket    │  │  │
                                          │  │  │   Manager   │  │  │
                                          │  │  └─────────────┘  │  │
                                          │  └───────────────────┘  │
                                          └─────────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │    Decision (ALLOW/     │
                                          │    DENY/REQUIRE_        │
                                          │    APPROVAL/QUARANTINE) │
                                          └─────────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │  ASR-1 Receipt          │
                                          │  (enriched, signed)     │
                                          └─────────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │  Execute (if ALLOW)     │
                                          │  or Hold (if PENDING)   │
                                          └─────────────────────────┘
```

### Data Flow

```
1. Agent submits ActionRequest for payment tool
   ↓
2. AVS Gateway detects payment tool (via ToolManifest tags)
   ↓
3. Gateway wraps ActionRequest in PaymentActionRequest
   ↓
4. Policy Engine evaluates all 10 checks in order
   ↓
5. If ALLOW: commit nonce, update budget, produce receipt
   If DENY: produce receipt with failure reasons
   If REQUIRE_APPROVAL: create ApprovalTicket, produce receipt
   If QUARANTINE: produce receipt, alert security
   ↓
6. Receipt returned to agent
   ↓
7. If ALLOW: agent may proceed to payment rail
   If DENY: agent must not proceed
   If REQUIRE_APPROVAL: agent must wait for human approval
   If QUARANTINE: payment isolated for investigation
```

### Integration Points

| External System | Integration Type | Direction | Data Exchanged |
|-----------------|-----------------|-----------|----------------|
| Payment Rails (x402, AP4M, etc.) | Settlement Adapter | Read-only (state queries) | `SettlementState` updates |
| Counterparty Registry | Policy Source | Read/Write | `CounterpartyPolicy` entries |
| Budget Store | State Store | Read/Write | `BudgetPolicy` mutable state |
| ReplayGuard Store | State Store | Write (commit) | Consumed nonces |
| Approval UI | Notification | Push | `ApprovalTicket` notifications |
| Audit Log | Event Stream | Append-only | All receipts and decisions |

---

## 7. Dependencies on v0.3.6

The Payment Guard module builds on v0.3.6 components. It does not replace them.

| v0.3.6 Component | How Payment Guard Uses It |
|-----------------|---------------------------|
| **ASR-1 Receipt** | Extends format with payment fields (Section 5). Existing verification logic handles base fields; payment extension adds 10 new verification steps. |
| **AgentIdentity** | `agent_identity_verified` check delegates to existing `AgentIdentity.verify()`. No changes to identity model. |
| **ToolManifest** | Payment tools are identified by tags in `ToolManifest`. A tool is "payment-aware" if its manifest includes `tag: "payment"`. |
| **Policy Engine** | Payment Guard registers as a policy module. The engine's check-evaluation pipeline is unchanged; Payment Guard adds 10 new checks. |
| **Fail-Closed Design** | Inherits the v0.3.6 principle: any error, timeout, or uncertainty produces DENY. Applied to settlement checks, replay checks, and PII scans. |
| **ActionRequest** | `PaymentActionRequest` wraps `ActionRequest`. All existing fields preserved. |
| **Authorization (AP2 mandate)** | `user_intent_bound` check uses the existing `ActionRequest.authorization` field. |

### Upgrade Path

```
v0.3.6 (locked)
    │
    ├── ASR-1 Receipt format extended (backward-compatible)
    ├── ToolManifest tags extended (backward-compatible)
    ├── Policy Engine plugin registration added
    │
    ▼
v0.4.0-alpha (Payment Guard module available, opt-in)
    │
    ├── Payment Guard can be enabled per-agent or globally
    ├── Without Payment Guard, behavior is identical to v0.3.6
    │
    ▼
v0.4.0 (Payment Guard default-enabled for payment tools)
    │
    ├── All payment tools automatically use Payment Guard
    ├── Non-payment tools unchanged
    │
    ▼
v0.4.x (iterative enhancement)
    ├── Additional payment rails
    ├── Additional policy check types
    └── Performance optimization
```

---

## 8. What This Does NOT Do

Explicit boundaries to prevent scope creep:

| Capability | Status | Why NOT in Payment Guard |
|-----------|--------|-------------------------|
| **Wallet implementation** | ❌ Out of scope | AVS does not hold funds. Wallets are the responsibility of agents or owner applications. |
| **Settlement processing** | ❌ Out of scope | AVS does not submit transactions to payment rails. It governs whether the agent *may* attempt settlement. |
| **Replace x402** | ❌ Out of scope | x402 is a payment rail. AVS governs actions that may use x402, but does not replace the protocol. |
| **Replace AP4M / ACP / AP2 / TAP** | ❌ Out of scope | These are payment protocols and standards. AVS is governance-agnostic — it can govern actions on any rail. |
| **Move money** | ❌ Out of scope | No money movement. No escrow. No payment processing. |
| **Implement a new payment protocol** | ❌ Out of scope | AVS is not a payment protocol. It is an action governance framework. |

### What It DOES Do

| Capability | Status | Description |
|-----------|--------|-------------|
| **Govern payment actions** | ✅ Core | Decides whether a payment action may proceed (ALLOW/DENY/REQUIRE_APPROVAL/QUARANTINE). |
| **Enforce budget policies** | ✅ Core | Hard spending limits per agent, per tool, per merchant, per period. |
| **Control counterparties** | ✅ Core | Allowlist/blocklist merchants; risk-score unknown counterparties. |
| **Prevent replay attacks** | ✅ Core | Nonce-based replay detection — direct countermeasure to x402 vulnerability. |
| **Fail-closed on settlement issues** | ✅ Core | Deny payments when settlement rails are degraded. |
| **Prevent PII leakage** | ✅ Core | Scan payment metadata for sensitive data. |
| **Require human approval** | ✅ Core | Hold high-risk payments for human review. |
| **Produce tamper-evident receipts** | ✅ Core | Enriched ASR-1 receipts with payment fields for audit and compliance. |

---

## 9. Success Criteria

### Demo Criteria

| # | Criterion | Target | Measurement |
|---|-----------|--------|-------------|
| 1 | All demo scenarios execute | 7/7 pass | Automated demo script produces correct decisions |
| 2 | Receipt verification | 100% pass | `avs receipt verify` succeeds on all payment receipts |
| 3 | Budget enforcement correctness | 100% | Every budget-exceeding request produces DENY |
| 4 | Replay prevention correctness | 100% | Every replayed payment produces QUARANTINE |
| 5 | Fail-closed behavior | 100% | Every degraded-rail scenario produces DENY |
| 6 | No regression | 581 tests pass | All v0.3.6 tests continue to pass |

### Performance Criteria

| Metric | Target | Notes |
|--------|--------|-------|
| Policy evaluation latency | < 50ms p99 | Per-payment policy evaluation, excluding settlement-state queries |
| Settlement state query timeout | < 200ms | Timeout for external settlement-state queries |
| Receipt generation | < 5ms | From decision to signed receipt |
| ReplayGuard lookup | < 10ms | Nonce existence check |
| Budget state update | < 10ms | Atomic budget read+update |

### Security Criteria

| Criterion | Target |
|-----------|--------|
| Replay attack prevention | 0% success rate for replayed payments |
| Budget overdraft prevention | 0 overdrafts under race conditions |
| PII detection rate | > 95% of known PII patterns detected |
| PII false positive rate | < 2% |
| Receipt tamper evidence | Any modification to receipt invalidates signature |

### Test Coverage Criteria

| Component | Minimum Coverage |
|-----------|-----------------|
| BudgetPolicy engine | 95% line coverage |
| CounterpartyPolicy engine | 95% line coverage |
| ReplayGuard | 95% line coverage |
| PII Scanner | 90% line coverage |
| SettlementState monitor | 90% line coverage |
| ApprovalTicket manager | 90% line coverage |
| Receipt enrichment | 95% line coverage |
| Integration (all checks) | 90% line coverage |

---

## 10. Relationship to Three-Moment Framework

The Payment Guard module fills the **"during action"** gap in the three-moment governance model:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    THREE-MOMENT FRAMEWORK                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BEFORE ACTION                DURING ACTION              AFTER      │
│  (v0.3.6)                     (v0.4.x)                   (v0.3.6)  │
│                                                                     │
│  ┌─────────────┐           ┌─────────────────┐       ┌──────────┐ │
│  │  Intent     │           │  Reservation    │       │  ASR-1   │ │
│  │  Validated  │           │  Locking        │       │  Receipt │ │
│  │  Identity   │──────────▶│  Idempotency    │──────▶│  Signed  │ │
│  │  Authorized │           │  Budget Check   │       │  Stored  │ │
│  │  Budget     │           │  Counterparty   │       │          │ │
│  │  Pre-check  │           │  Verified       │       │          │ │
│  └─────────────┘           │  Settlement OK  │       └──────────┘ │
│                            │  Nonce Fresh    │                    │
│                            │  PII Clean      │                    │
│                            │  Human OK       │                    │
│                            └─────────────────┘                    │
│                                                                     │
│  Decision:                    Decision:                 Record:   │
│  ALLOW / DENY /               ALLOW (with locks) /      Evidence  │
│  REQUIRE_APPROVAL /           DENY /                    of         │
│  QUARANTINE                   REQUIRE_APPROVAL /        governance │
│                               QUARANTINE                decision   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Moment-by-Moment Breakdown

#### Moment 1: BEFORE — AVS Decides (v0.3.6)

- Agent submits `ActionRequest`
- AVS validates identity, authorization, basic policies
- Decision: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, or `QUARANTINE`
- For non-payment tools: this is the complete pipeline
- For payment tools: if ALLOW, proceed to Moment 2

#### Moment 2: DURING — Payment Guard Manages (v0.4.x)

- Payment Guard takes the ALLOWed `PaymentActionRequest`
- Performs detailed checks: budget, counterparty, settlement, replay, PII, human approval
- Manages reservation and locking:
  - Reserves budget amount (prevents race-condition overdraft)
  - Consumes nonce in `ReplayGuard` (prevents replay)
  - Binds to resource hash (prevents substitution)
- If all checks pass: releases lock, produces enriched receipt
- If any check fails: rolls back reservations, produces receipt with failure reason

#### Moment 3: AFTER — ASR-1 Receipt Records Evidence (v0.3.6 + v0.4.x enrichment)

- Enriched ASR-1 receipt captures:
  - All decisions and reasons
  - Budget state (before/after)
  - Settlement state
  - Risk scores
  - Approval tickets
  - Replay check results
  - PII scan results
- Receipt is signed and stored
- `avs receipt verify` validates the complete chain of evidence

### Why Three Moments Matter for Payments

Payment actions have a unique property: they **mutate external state** (the ledger). Once a payment is submitted to a rail, it may be irreversible. The three-moment framework ensures:

1. **Before:** The payment intent is thoroughly validated before any external commitment.
2. **During:** Budgets are reserved, nonces are consumed, and settlement capacity is verified atomically.
3. **After:** The complete governance trail is recorded for audit, dispute resolution, and compliance.

This is why AVS's fail-closed design is critical: if any check in any moment fails, the payment does not proceed. There is no "optimistic execution" — uncertainty is always DENY.

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **AP2** | Agent Payment Protocol 2 — a mandate-based authorization model where users explicitly authorize agents to spend |
| **AP4M** | Mastercard's Agent Payments for Merchants — launched June 2026 with 30+ partners |
| **ACP** | Agent Commerce Protocol — another payment protocol for agent transactions |
| **ActionRequest** | AVS's core request object representing an agent's intent to perform an action |
| **ASR-1** | AVS Signed Receipt format — tamper-evident evidence of governance decisions |
| **Fail-closed** | Design principle: when uncertain, deny. Opposite of "fail-open" (when uncertain, allow). |
| **Payment rail** | An underlying system that actually moves money (x402, Stripe, Circle, etc.) |
| **Replay attack** | Reusing a valid payment proof/intent to extract multiple payments |
| **Resource binding** | Cryptographically binding a payment to a specific resource to prevent substitution |
| **TAP** | Trust Agent Protocol — another emerging payment standard |
| **x402** | A popular but vulnerable payment protocol; 97.76% leakage demonstrated in research |

## Appendix B: References

1. **x402 Security Analysis** — Independent research demonstrating 97.76% PII leakage and replay vulnerabilities in x402 implementations.
2. **Mastercard AP4M Launch** — June 2026, 30+ launch partners, protocol specification.
3. **AVS v0.3.6 Documentation** — Existing ASR-1, AgentIdentity, ToolManifest, PolicyEngine documentation.
4. **AP2 Mandate Model** — User authorization model where humans explicitly approve agent spending capabilities.
5. **Catena Platform** — "Control plane for agent payments" — positioned for money movement only.

---

*This document defines WHAT to build, not HOW to build it. Implementation is deferred to v0.4.x development cycles. No code has been written for this module.*
