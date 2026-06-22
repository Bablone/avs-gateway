# ASR-1 Receipt Standard (Draft)

> **ASR-1 is an experimental draft receipt format for AI agent action decisions.**
>
> It is NOT an official external standard.
> It is an AVS-native receipt profile.
> It is designed for agent action decisions.

---

## What is ASR-1WARNING

ASR-1 (Action Standard Receipt) is a deterministic, portable, redaction-safe
evidence object for AI agent action decisions.

The words matter:

| Word | Meaning |
|------|---------|
| **Deterministic** | Same input produces the same hash |
| **Portable** | Can be exported to SIEM, observability, compliance, dashboards |
| **Redaction-safe** | No secrets, raw PII, PHI, payment data, or prompt contents |
| **Evidence object** | Structured enough for audits, investigations, replay |
| **Action decisions** | Captures what was decided *before* execution |

ASR-1 captures the full action governance path:

```
actor -> intent -> policy -> decision -> execution outcome -> evidence chain
```

---

## Why ASR-1WARNING

As AI agents move from text generation into real execution, the critical
enterprise question becomes:

- What did the agent attemptWARNING
- Who or what was the accountable actorWARNING
- Which policy appliedWARNING
- What decision was madeWARNING
- Did execution happenWARNING
- Can the evidence be verified laterWARNING

ASR-1 answers all six questions in a single structured object.

---

## Receipt Structure

An ASR-1 receipt has five sections:

```json
{
  "asr_version": "1.0-draft",
  "receipt_id": "uuid",
  "request_id": "uuid",
  "timestamp_ns": 1718870400000000000,
  "agent_identity": { ... },
  "action": { ... },
  "tool_manifest": { ... },
  "governance": { ... },
  "execution": { ... },
  "ledger": { ... }
}
```

### Header

| Field | Type | Description |
|-------|------|-------------|
| `asr_version` | string | "1.0-draft" |
| `receipt_id` | UUID | Unique identifier for this receipt |
| `request_id` | UUID | Identifier of the original action request |
| `timestamp_ns` | integer | Nanoseconds since epoch |

### Agent Identity

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique agent identifier |
| `agent_type` | string | Classification (coding, deployment, support) |
| `environment` | string | dev, staging, prod |
| `privilege_level` | string | read_only, standard, privileged, admin |
| `public_key_fingerprint` | string (optional) | SHA-256 of Ed25519 public key |

### Action (Intent)

| Field | Type | Description |
|-------|------|-------------|
| `action_type` | string | file, api, email, payment, database, security_scan |
| `tool_name` | string | Name of the tool |
| `operation` | string | Operation being performed |
| `parameter_hash` | sha256:hex | Hash of parameters (not raw values) |
| `context_hash` | sha256:hex | Hash of execution context |

### Tool Manifest

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string (optional) | Registered tool name |
| `module_path` | string (optional) | Python module path |
| `function_name` | string (optional) | Function name |
| `source_hash` | sha256:hex (optional) | Best-effort source hash (informational) |
| `registered_at` | ISO 8601 (optional) | Registration timestamp |
| `registered_by` | string (optional) | Who registered |
| `policy_binding` | string (optional) | Bound policy set |

### Governance (Decision)

| Field | Type | Description |
|-------|------|-------------|
| `policy_ids_evaluated` | [string] | Policies that were checked |
| `winning_policy_id` | string (optional) | Policy that determined the outcome |
| `risk_score` | number (0-100) | Risk at decision time |
| `trust_score` | number (0-100) | Trust at decision time |
| `decision` | string | allow, deny, require_approval, quarantine |
| `decision_reason` | string | Human-readable explanation |

### Execution (Outcome)

| Field | Type | Description |
|-------|------|-------------|
| `executed` | boolean | Whether the action ran |
| `status` | string | executed, blocked, blocked_pending_approval, quarantined |
| `latency_ms` | number | Processing time |
| `human_approver_id` | string (optional) | Who approved/denied |

### Ledger (Evidence Chain)

| Field | Type | Description |
|-------|------|-------------|
| `previous_receipt_hash` | sha256:hex | Hash of previous receipt |
| `receipt_hash` | sha256:hex | Hash of this receipt |
| `gateway_signature` | string (optional) | Ed25519 signature |

---

## Design Rules

### 1. No Raw Secrets

ASR-1 receipts NEVER contain:
- API keys
- Customer PII
- Payment card details
- Raw PHI
- Database queries with sensitive data
- Private prompt contents

Instead, store:
- `parameter_hash`  SHA-256 of the canonical parameters
- `context_hash`  SHA-256 of the execution context
- Classification labels
- Evidence pointers

### 2. Deterministic Hashing

Receipt hashes use deterministic canonical JSON
(`json.dumps(sort_keys=True, separators=(',', ':'))`).

This ensures:
- Same receipt content produces the same hash across runs
- Same hash across Python environments
- Verifiable integrity

Future versions may adopt JCS (RFC 8785) for cross-language
determinism once the draft stabilizes.

### 3. Linked Chain

Each receipt's `previous_receipt_hash` links to the previous receipt.
Tampering with any receipt breaks the chain.

---

## Verification

### Hash Verification

```python
from avs_gateway.receipts.asr1 import verify_receipt

receipt = ASR1Receipt.from_json(json_string)
valid = verify_receipt(receipt)
# True = hash matches content
# False = tampering detected
```

### Chain Verification

```python
from avs_gateway.receipts.asr1 import verify_chain

receipts = [receipt1, receipt2, receipt3]
valid = verify_chain(receipts)
# True = chain is intact
# False = a receipt was removed, reordered, or tampered
```

### CLI Verification

```bash
avs receipt verify examples/receipts/allow_receipt.json
```

---

## Example Receipts

Four example receipts are provided:

| File | Decision | Description |
|------|----------|-------------|
| `examples/receipts/allow_receipt.json` | ALLOW | Safe file read |
| `examples/receipts/deny_receipt.json` | DENY | Dangerous file delete |
| `examples/receipts/require_approval_receipt.json` | REQUIRE_APPROVAL | Production deploy |
| `examples/receipts/quarantine_receipt.json` | QUARANTINE | Suspicious query |

---

## JSON Schema

The JSON Schema for validation is at:

```
schemas/asr_1_receipt.schema.json
```

---

## Relationship to Other Standards

ASR-1 is NOT a replacement for these standards. It is designed to
interoperate with them:

| Standard | Relationship |
|----------|-------------|
| **CloudEvents** | ASR-1 can be wrapped as a CloudEvent for transport |
| **OpenTelemetry** | ASR-1 can be exported as OTel log events |
| **W3C Verifiable Credentials** | Future profile for VC-compatible receipts |
| **Sigstore** | Future profile for transparency log publishing |
| **SLSA/in-toto** | Future profile for tool supply-chain attestation |
| **SPIFFE/SPIRE** | Agent identity maps to workload identity patterns |
| **OPA/Cedar** | Policy evaluation can interoperate with policy engines |

---

## Roadmap

| Version | Feature |
|---------|---------|
| v0.3.6 (current) | ASR-1 draft schema, generation, verification |
| v0.4.0 | Signed agent actions (agent keys sign requests) |
| v0.4.1 | Tool manifest integrity enforcement |
| v0.4.2 | CloudEvents / OpenTelemetry export profiles |
| v0.5.0 | SIEM integration, compliance mappings |

---

> **Every agent action gets a receipt.**
>
> ASR-1  Action Standard Receipt (Draft)
