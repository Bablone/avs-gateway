# AVS Gateway v0.3.6 — Build Strategy & Synthesis

## Research Date: 2026-06-20
## Status: v0.3.5 (distribution assets) LOCKED. Ready to build v0.3.6.

---

## I. Executive Summary

Four research agents + four strategic documents have been synthesized. The verdict is clear:

**ASR-1 (Action Standard Receipt) is a genuinely novel standardization opportunity.**
No competitor has shipped cryptographically signed agent action receipts. The only public attempt (AAR v1.0) has 4 GitHub stars and 1 contributor. The standardization race is wide open.

**The user's roadmap is validated and refined:**
- v0.3.5 = Distribution (DONE — 9 launch assets, 720KB archive)
- v0.3.6 = ASR-1 Receipt Standard + Agent Identity Draft
- v0.4.0 = Verifiable Identity Runtime (signed actions)

---

## II. Research Findings Summary

### A. Standards Landscape — ASR-1 is Greenfield

| Standard | Status | Relevance to ASR-1 |
|----------|--------|-------------------|
| W3C Verifiable Credentials 2.0 | Published May 2025 | For identity claims, not real-time action audit receipts. Could be a future profile, not direct competition. |
| IETF SCITT WG | Draft (supply chain receipts) | Closest parallel. ASR-1 could align with SCITT for supply-chain provenance of agent actions. |
| RFC 6962/9162 (Cert Transparency) | Published | Merkle tree primitives already in AVS audit chain. Confirms architectural correctness. |
| CloudTrail / Azure / GCP Audit | Production, mature | Structural patterns to借鉴. None are cryptographically signed. None are cross-system. |
| OpenTelemetry GenAI Semantics | Experimental | Covers observability, not cryptographic attestation. Complementary, not competitive. |
| OWASP Agentic AI 2026 | Highly active | **Best immediate venue.** No specific receipt format proposed yet. ASR-1 can fill this gap. |
| SPIFFE/SPIRE | CNCF incubating | Being extended to AI agents. Complementary — SPIFFE for identity, ASR-1 for action receipts. |
| AAR v1.0 (existing attempt) | 4 stars, 1 contributor | Only public "action receipt" attempt. Effectively a non-competitor. |

**Key insight:** Every cloud audit format logs actions. None produce cryptographically signed, cross-system, tamper-evident receipts. ASR-1 occupies a gap that no one else has identified as valuable.

### B. Competitive Intelligence — Receipts Are the Moat

The agent governance market has three layers. AVS is the only product that spans all three:

```
Layer 1: OBSERVABILITY (post-hoc tracing)
  LangSmith, Langfuse, Helicone
  → "We recorded what the agent did."
  → No enforcement. No receipts.

Layer 2: RUNTIME ENFORCEMENT (action interception)
  Guardrails AI, PointGuard AI, Singulr AI, DeepInspect, ICME Preflight
  → "We blocked the dangerous action."
  → Enforcement without evidence. No receipts.

Layer 3: EVIDENCE (cryptographic receipts/attestation)
  Pipelock (OSS, Ed25519-signed receipts), AAR spec (4 stars)
  → "We proved what happened."
  → Receipts without enforcement pipeline.

AVS: ALL THREE LAYERS
  → "We intercepted, decided, and proved."
  → Intercept + Evaluate + Receipt = complete pipeline
```

**Closest threats:**
| Competitor | Threat | Why |
|-----------|--------|-----|
| PointGuard AI | HIGH | Runtime enforcement + agent identity for MCP. Well-funded. |
| Singulr AI | HIGH | Agent identity + runtime controls. Could add receipts quickly. |
| ICME Preflight | MEDIUM | Cryptographic proofs but no runtime interception. |
| Pipelock | MEDIUM | OSS with Ed25519 receipts but no enforcement pipeline. |

**Critical window:** PointGuard and Singulr have enforcement + identity. Neither has shipped a receipt standard. If AVS ships ASR-1 first and gets adoption, the receipt format becomes the lock-in mechanism (switching costs = format migration pain).

### C. License — Keep Apache 2.0

Research finding is definitive:

| License Model | Pre-Launch Adoption | Enterprise Revenue | Community Growth | Verdict |
|--------------|--------------------|--------------------|-----------------|---------|
| Apache 2.0 + proprietary EE | Excellent | Excellent | Excellent | **OPTIMAL for AVS** |
| BSL 1.1 | Poor (forks, backlash) | Mixed (HashiCorp acquired below IPO) | Poor | WRONG for pre-launch |
| FSL | Mixed (too new) | Unknown | Mixed | WRONG for pre-launch |
| SSPL | Poor (severe forks) | Elastic growth DECLINED post-change | Poor | WRONG |

**The AWS threat is not real for AVS.** AWS copies projects with millions of users and 5-10 years of history. AVS has zero GitHub stars. The far greater risk is that restrictive licensing suppresses adoption before AVS ever reaches AWS-threat scale.

**Decision: Keep Apache 2.0 for the core runtime.** Monetize enterprise features (control plane, hosted dashboard, compliance packs, policy packs, SIEM integrations) as proprietary add-ons. Revisit licensing only if/when AVS achieves scale where AWS competition becomes realistic — likely 5+ years away, if ever.

### D. Technical Feasibility — Manifest > Source Hashing

**Function body hashing in Python is fundamentally flawed:**
- `inspect.getsource()` fails for: C extensions, dynamically created functions, REPL, decorated functions
- `__code__.co_code` changes between Python 3.11/3.12/3.13
- **Critical:** Same source + bytecode with different closure contents = different behavior, SAME hash
- Python has NO native code signing mechanism

**Recommended approach for v0.3.6:**
1. **Tool Registration Manifest** (primary): Register tool metadata (name, module_path, package_version, registered_by, timestamp, policy_binding). Always works. No edge cases.
2. **Best-effort fingerprints** (optional): Source hash + bytecode hash when available, clearly marked as informational, not security-critical.
3. **Receipts**: Ed25519-signed with JCS (RFC 8785) canonical JSON.

**Dependencies to add:**
| Package | Size | Purpose |
|---------|------|---------|
| `jcs` | ~20KB | JCS canonical JSON (RFC 8785) — deterministic across languages |
| `PyNaCl` | ~1MB | Ed25519 signing/verification — fastest, well-maintained |

---

## III. Build Specification: v0.3.6

### Goal
Define and implement the first draft of AVS's verifiable action receipt standard: ASR-1. Add a minimal Agent Identity model that prepares the project for signed agent actions in v0.4.0.

### Files to Create

```
docs/ASR_1_RECEIPT_STANDARD.md          # Standard specification document
schemas/asr_1_receipt.schema.json       # JSON Schema for validation
examples/receipts/
  allow_receipt.json                    # Example: ALLOW decision
  deny_receipt.json                     # Example: DENY decision
  require_approval_receipt.json         # Example: REQUIRE_APPROVAL
  quarantine_receipt.json               # Example: QUARANTINE

avs_gateway/receipts/
  __init__.py
  asr1.py                               # Core ASR-1 implementation

avs_gateway/identity/
  __init__.py
  agent_identity.py                     # Agent identity model

avs_gateway/tools/
  tool_manifest.py                      # Tool registration manifest

tests/unit/
  test_asr1_receipt_generation.py       # Receipt generation tests
  test_asr1_receipt_verification.py     # Receipt verification tests
  test_asr1_tamper_detection.py         # Tamper detection tests
  test_agent_identity.py                # Agent identity tests
  test_tool_manifest.py                 # Tool manifest tests
```

### ASR-1 Receipt Schema (v1.0-draft)

```json
{
  "asr_version": "1.0-draft",
  "receipt_id": "uuid-v4",
  "request_id": "uuid-v4",
  "timestamp_ns": 1718870400000000000,
  "agent_identity": {
    "agent_id": "agent_001",
    "display_name": "Deployment Agent",
    "agent_type": "deployment",
    "environment": "production",
    "privilege_level": "standard",
    "public_key_fingerprint": "sha256:abc123..."
  },
  "action": {
    "action_type": "api",
    "tool_name": "deploy_to_production",
    "operation": "deploy_prod",
    "parameter_hash": "sha256:def456...",
    "context_hash": "sha256:ghi789..."
  },
  "tool_manifest": {
    "tool_name": "deploy_to_production",
    "module_path": "myapp.tools.deploy",
    "function_name": "deploy_to_prod",
    "registered_at": "2026-06-20T12:00:00Z",
    "registered_by": "admin"
  },
  "governance": {
    "policy_ids_evaluated": ["rule_01", "rule_05", "rule_12"],
    "winning_policy_id": "rule_12",
    "risk_score": 0.85,
    "trust_score": 0.72,
    "decision": "require_approval",
    "decision_reason": "Production deployments require CISO approval"
  },
  "execution": {
    "status": "blocked_pending_approval",
    "human_approver_id": null
  },
  "ledger": {
    "previous_receipt_hash": "sha256:0000000000000000...",
    "receipt_hash": "sha256:final_hash_of_this_receipt...",
    "gateway_signature": "ed25519:signature_hex..."
  }
}
```

**Design rules:**
- No raw secrets or PII in receipts (parameter_hash, not parameters)
- Deterministic via JCS canonical JSON for hashing
- Ed25519 signatures for non-repudiation
- Linked hash chain (previous_receipt_hash) for tamper evidence
- agent_identity.public_key_fingerprint is optional in v0.3.6 (identity is draft, not enforced)

### Agent Identity Model (v0.3.6 — draft, not enforced)

```python
@dataclass
class AgentIdentity:
    agent_id: str                    # Unique identifier
    display_name: str                # Human-readable name
    agent_type: str                  # "coding" | "deployment" | "support" | custom
    environment: str                 # "dev" | "staging" | "prod"
    privilege_level: str             # "read_only" | "standard" | "privileged" | "admin"
    public_key: Optional[str]        # Ed25519 public key (hex)
    key_fingerprint: Optional[str]   # sha256:hex fingerprint
    status: str                      # "active" | "revoked" | "rotated"
    created_at: str                  # ISO 8601
    last_seen_at: str                # ISO 8601
    parent_agent_id: Optional[str]   # For spawned agents
    human_owner_id: Optional[str]    # Human on whose behalf agent acts
    trust_score: float               # 0.0 - 1.0
```

**v0.3.6 scope:**
- AgentIdentity dataclass exists
- Can produce key_fingerprint from public_key
- Can generate ASR-1 receipts with agent_identity section
- agent_identity.public_key_fingerprint is populated when available
- NO signature verification of ActionRequests yet (v0.4.0)
- NO key rotation/revocation enforcement yet (v0.4.0)

### Tool Registration Manifest

```python
@dataclass
class ToolManifest:
    tool_name: str                   # Registered tool name
    module_path: str                 # Python module path
    function_name: str               # Function name within module
    source_hash: Optional[str]       # Best-effort SHA-256 of source (informational)
    bytecode_hash: Optional[str]     # Best-effort SHA-256 of bytecode (informational)
    package_version: Optional[str]   # Package version at registration
    registered_at: str               # ISO 8601
    registered_by: str               # Who registered the tool
    policy_binding: Optional[str]    # Bound policy set
```

**v0.3.6 scope:**
- ToolManifest dataclass exists
- Can register tools and generate manifests
- source_hash and bytecode_hash are best-effort, clearly marked informational
- NO tamper detection enforcement yet (v0.4.1)

### Implementation Details

**Canonical JSON (JCS — RFC 8785):**
```python
import jcs

def canonical_json(obj: dict) -> bytes:
    """Return JCS-canonicalized JSON bytes."""
    return jcs.canonicalize(obj)

def hash_receipt_payload(payload: dict) -> str:
    """Return SHA-256 hash of canonical JSON."""
    canonical = canonical_json(payload)
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"
```

**Ed25519 Signing (PyNaCl):**
```python
from nacl.signing import SigningKey, VerifyKey

def sign_receipt(receipt_dict: dict, private_key_hex: str) -> str:
    """Sign canonical JSON of receipt."""
    message = canonical_json(receipt_dict)
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signed = signing_key.sign(message)
    return f"ed25519:{signed.signature.hex()}"

def verify_receipt_signature(receipt_dict: dict, signature_hex: str, public_key_hex: str) -> bool:
    """Verify Ed25519 signature."""
    # Remove signature field before verifying
    verify_payload = {k: v for k, v in receipt_dict.items() if k != "gateway_signature"}
    message = canonical_json(verify_payload)
    verify_key = VerifyKey(bytes.fromhex(public_key_hex))
    try:
        verify_key.verify(message, bytes.fromhex(signature_hex))
        return True
    except Exception:
        return False
```

### Tests to Write

1. **test_asr1_receipt_generation.py**
   - Generate receipt for ALLOW decision
   - Generate receipt for DENY decision
   - Generate receipt for REQUIRE_APPROVAL
   - Generate receipt for QUARANTINE
   - Verify receipt has all required fields
   - Verify receipt_id and request_id are UUIDs
   - Verify timestamp_ns is reasonable

2. **test_asr1_receipt_verification.py**
   - Valid receipt passes verification
   - Receipt with tampered decision field fails verification
   - Receipt with tampered agent_id fails verification
   - Receipt with tampered receipt_hash fails verification
   - Cross-language canonicalization consistency (JCS ensures this)

3. **test_asr1_tamper_detection.py**
   - Modify single character in receipt → verification fails
   - Swap two receipts → chain breaks
   - Add phantom receipt → chain breaks
   - Remove receipt from chain → chain breaks

4. **test_agent_identity.py**
   - Create identity with all fields
   - Key fingerprint generation is deterministic
   - Key fingerprint changes when public key changes
   - Identity serialization/deserialization

5. **test_tool_manifest.py**
   - Register tool, manifest has all fields
   - source_hash is generated when source is available
   - Manifest serialization round-trip

### Success Criteria
- All 496 existing tests still pass
- 25+ new ASR-1/identity/manifest tests pass
- Example receipts validate against JSON Schema
- Tampered receipt fails verification
- Agent identity produces stable key fingerprint
- README/doc makes clear ASR-1 is a draft, not an official external standard
- No new heavyweight dependencies beyond jcs (~20KB) and PyNaCl (~1MB)

---

## IV. The Strategic Arc (Updated)

```
v0.3.5  Public Launch Readiness Pack              ← DONE (June 2026)
        Distribution assets, README, launch posts

v0.3.6  ASR-1 Receipt Standard + Agent Identity Draft  ← BUILD NOW
        ├── ASR-1 schema defined
        ├── AVS generates ASR-1 receipts
        ├── Receipt verification (tamper detection)
        ├── Agent identity model (key fingerprint)
        ├── Tool registration manifest
        └── 520+ tests

v0.4.0  Verifiable Identity Runtime
        ├── Agent key generation (avs agent create)
        ├── Signed ActionRequest payloads
        ├── Signature verification (invalid → quarantine)
        ├── Agent registry (avs agent list)
        ├── Key rotation
        ├── Key revocation
        └── Signed ASR-1 receipts + receipt verifier CLI

v0.4.1  Tool Integrity Gate
        ├── Tool registry with manifest enforcement
        ├── Tamper detection (hash mismatch → deny/quarantine)
        └── Tool integrity receipt fields

v0.4.2  Audit Export
        ├── CSV export
        ├── JSON export
        ├── PDF summary
        └── Splunk/Datadog event-shape docs

v0.5.0  Enterprise Hardening
        ├── Auth + RBAC
        ├── Multi-tenancy
        ├── Hosted dashboard
        ├── Policy packs
        ├── SIEM integrations
        └── Managed retention
```

**The strategic sentence:**
> AVS starts as a runtime permission layer. ASR-1 turns its receipts into a portable evidence format. Agent Identity turns labels into verifiable actors. HiveMind later turns single-action governance into multi-agent governance.

---

## V. Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **License** | Keep Apache 2.0 | Open core beats BSL for pre-launch. AWS threat not real at this scale. Community growth > theoretical protection. |
| **Tool integrity** | Manifest-based, not source hash | Python function hashing is fundamentally flawed (decorators, closures, dynamic imports). Manifest is reliable. |
| **Canonical JSON** | JCS (RFC 8785) | Cross-language deterministic. Standard. Not homegrown. |
| **Signing library** | PyNaCl | Fastest, well-maintained, binary wheels available. |
| **Standards strategy** | OWASP first, IETF later | OWASP Agentic AI is active and needs a receipt format. IETF/W3C submission requires users first. |
| **Naming** | No "sovereign" publicly | Use "Verifiable Agent Identity," "ASR-1 Receipts," "Proof-Gated Execution." Keep "sovereign" internal only. |
| **Scope discipline** | No signing enforcement in v0.3.6 | Define the standard and objects. Enforce in v0.4.0. Don't try to build everything at once. |

---

## VI. Immediate Next Steps

1. **Add `jcs` and `PyNaCl` to pyproject.toml dependencies**
2. **Create directory structure** (receipts/, identity/, tool_manifest registration)
3. **Implement ASR-1 core** (asr1.py — generate, canonicalize, hash, verify)
4. **Implement AgentIdentity** (agent_identity.py — dataclass, fingerprint)
5. **Implement ToolManifest** (tool_manifest.py — registration, best-effort hashes)
6. **Write JSON Schema** (schemas/asr_1_receipt.schema.json)
7. **Write example receipts** (4 JSON files)
8. **Write 25+ tests**
9. **Write docs** (ASR_1_RECEIPT_STANDARD.md)
10. **Verify** — 496 existing tests still pass, new tests pass, receipts validate

---

> **Every agent action gets a receipt.**
>
> AVS Gateway — Runtime Permission Layer for AI Agents
