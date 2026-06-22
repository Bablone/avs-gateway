# AVS Gateway v0.3.6 — Build Execution Plan
## ASR-1 Proof-of-Action Foundation

**Status:** v0.3.5 distribution assets LOCKED. Building v0.3.6 now.
**Core Thesis:** Agent Identity + Tool Manifest + Action Receipt = Proof of Action
**Category:** Verifiable action receipts for AI agents (not "agent governance")

---

## Key Decisions (Locked)

| Decision | Value |
|----------|-------|
| License | Apache 2.0 (unchanged) |
| Positioning | "Proof-of-action layer" not "sovereign" |
| ASR-1 status | Experimental draft, AVS-native profile, NOT official standard |
| Receipt signing | Ed25519 via PyNaCl in v0.3.6 |
| ActionRequest signing | v0.4.0 ONLY — NOT in v0.3.6 |
| Canonical JSON | JCS (RFC 8785) preferred, fallback to json.dumps(sort_keys=True, separators=(',', ':')) |
| Tool integrity | Manifest-based, NOT source hashing |
| Existing tests | All 496 must pass |
| New tests | 25-40 |

---

## Build Stages

### Stage 1: Dependencies + Directory Structure
- Add jcs, PyNaCl to pyproject.toml
- Create directories: receipts/, identity/
- Verify existing tests still pass

### Stage 2: Core ASR-1 Implementation (receipts/asr1.py)
- ASR-1 dataclass/schema
- generate_asr1_receipt() — creates receipt from gateway decision
- canonical_json() — JCS or deterministic fallback
- hash_receipt_payload() — SHA-256 of canonical JSON
- sign_receipt() — Ed25519 gateway signature
- verify_asr1_receipt() — full verification (hash + signature)
- verify_chain() — linked hash chain integrity

### Stage 3: Agent Identity (identity/agent_identity.py)
- AgentIdentity dataclass
- key_fingerprint() — deterministic from public key
- serialization/deserialization
- Status management (active/revoked/rotated)

### Stage 4: Tool Manifest (tools/tool_manifest.py)
- ToolManifest dataclass
- register_tool() — create manifest from function
- Best-effort source_hash, bytecode_hash (informational)
- Manifest hash for tamper detection prep

### Stage 5: Example Receipts + JSON Schema
- 4 example JSON receipts (allow, deny, require_approval, quarantine)
- JSON Schema for validation
- docs/ASR_1_RECEIPT_STANDARD.md

### Stage 6: Tests (25-40 tests)
- test_asr1_receipt_generation.py
- test_asr1_receipt_verification.py
- test_asr1_tamper_detection.py
- test_agent_identity.py
- test_tool_manifest.py

### Stage 7: CLI (avs receipt verify)
- Low-risk addition only
- Verify receipt from JSON file
- ASCII-safe output

### Stage 8: Integration + Archive
- Verify 496 existing tests pass
- Verify new tests pass
- Update README (minimal — mention ASR-1 draft in roadmap)
- Create archive

---

## ASR-1 Receipt Structure (v1.0-draft)

```json
{
  "asr_version": "1.0-draft",
  "receipt_id": "uuid",
  "request_id": "uuid",
  "timestamp_ns": 1718870400000000000,
  "agent_identity": {
    "agent_id": "...",
    "agent_type": "...",
    "environment": "...",
    "privilege_level": "...",
    "public_key_fingerprint": "sha256:..."
  },
  "action": {
    "action_type": "...",
    "tool_name": "...",
    "operation": "...",
    "parameter_hash": "sha256:...",
    "context_hash": "sha256:..."
  },
  "tool_manifest": {
    "tool_name": "...",
    "tool_type": "...",
    "module_path": "...",
    "function_name": "...",
    "source_hash": "sha256:...",
    "registered_at": "...",
    "registered_by": "...",
    "policy_binding": "..."
  },
  "governance": {
    "policy_ids_evaluated": ["..."],
    "winning_policy_id": "...",
    "risk_score": 0.0,
    "trust_score": 0.0,
    "decision": "...",
    "decision_reason": "..."
  },
  "execution": {
    "executed": false,
    "status": "...",
    "latency_ms": 0,
    "human_approver_id": null
  },
  "ledger": {
    "previous_receipt_hash": "sha256:...",
    "receipt_hash": "sha256:...",
    "gateway_signature": "ed25519:..."
  }
}
```

## What v0.3.6 Does NOT Do
- Does NOT require signed ActionRequests
- Does NOT quarantine unsigned actions
- Does NOT enforce key rotation/revocation
- Does NOT enforce tool tamper detection
- Does NOT claim ASR-1 is official industry standard
- Does NOT claim "world's first"
- Does NOT store raw secrets in receipts
