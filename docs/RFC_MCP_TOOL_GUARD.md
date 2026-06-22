# RFC: AVS MCP Tool Guard (v0.4.0)

**Status:** Proposed  
**Version:** 0.4.0  
**Target Release:** AVS Gateway v0.4.0  
**RFC Date:** 2026-06-10  
**Author:** AVS Core Team  
**References:** MCPSHIELD (arXiv:2604.05969), ASR-1 Receipt Spec (v0.3.6), AgentIdentity (v0.3.6), ToolManifest (v0.3.6)

---

## 1. Abstract

AVS MCP Tool Guard is a proposed extension to the AVS Gateway that governs MCP-based tool calls through policy enforcement, identity attestation, and verifiable receipt generation. It intercepts every MCP tool invocation, classifies the action type (read, write, destructive, administrative), validates arguments against declared policies, scans for PII exposure, evaluates network and file-system boundaries, checks privilege levels, and produces an ASR-1 receipt enriched with MCP-specific metadata. The goal is to close the 66% coverage gap identified in the MCPSHIELD threat landscape (arXiv:2604.05969) by providing tool-call governance that is policy-driven, evidence-producing, and developer-transparent.

---

## 2. Motivation

### 2.1 The MCPSHIELD Findings

The MCPSHIELD paper (April 2026, arXiv:2604.05969) systematically analyzed the MCP (Model Context Protocol) ecosystem and identified **7 threat categories** comprising **23 distinct attack vectors**. The paper's central finding: **no single existing defense covers more than 34% of the MCP threat landscape**, and **66% of attack vectors remain unaddressed** by current tooling.

### 2.2 Why MCP Before Payments

The AVS strategic roadmap prioritizes MCP Tool Guard ahead of Payment Guard for four reasons:

1. **Adoption velocity** — Agents call tools via MCP every day. File reads, API calls, database queries, and shell commands are the primary interface between agents and the external world. The surface area is massive and growing.
2. **Developer pain is immediate** — Tools touch sensitive resources (files, credentials, databases, internal APIs) without standardized oversight. Developers feel this pain now and need a governance layer they can trust.
3. **Foundation for payments** — Payment authorization is a specialized form of tool governance. Solving the general tool-governance problem first creates the policy engine, receipt infrastructure, and identity framework that Payment Guard will inherit.
4. **Market timing** — The MCPSHIELD paper has catalyzed awareness of MCP security gaps. Being the first governance layer with verifiable receipts positions AVS as the infrastructure of choice.

### 2.3 Real Developer Pain

- An agent reads `/etc/passwd` because no one told it not to.
- A tool call passes a private key as a string argument because there's no PII scanner at the boundary.
- A "file reader" tool silently has a `delete_file` sub-command that no policy engine catches.
- An MCP server is swapped out mid-session, and the agent never knows the tool it trusts now talks to a different backend.
- A multi-tool sequence chains 5 reads into a single destructive action, and no single checkpoint stops it.

AVS MCP Tool Guard addresses each of these scenarios with a unified policy + receipt framework.

---

## 3. Threat Model

The following table maps the 7 MCPSHIELD threat categories to AVS MCP Tool Guard coverage:

| MCPSHIELD Category | Threat Description | AVS Coverage |
|---|---|---|
| **TC1: Tool Poisoning** | Malicious or altered tool definitions injected into the tool manifest | Tool manifest verification against registered `MCPToolManifest` entries; hash-based integrity checks; manifest update logging |
| **TC2: Data Exfiltration** | Unauthorized extraction of sensitive data via tool arguments or return values | Context tracking on all argument values; PII scanning before transmission; approval routing for outbound data |
| **TC3: Prompt Injection** | Manipulation of tool context or hidden instructions embedded in tool descriptions | Action boundary control — tool classification limits what a tool can do regardless of prompt content; classification overrides description semantics |
| **TC4: Tool Hijacking** | Unauthorized substitution or invocation of tools outside the agent's scope | Tool identity attestation via `MCPToolManifest` registry; each tool call must match a registered, verified manifest entry |
| **TC5: Privilege Escalation** | Gradual or sudden expansion of an agent's capabilities beyond granted scope | Privilege-level checks against `AgentIdentity` roles; session-level escalation detection; read-to-write-to-delete progression tracking |
| **TC6: Server Compromise** | Compromise of an MCP server causing it to serve malicious tools or data | Network boundary checks ensuring tool calls target only permitted domains/IPs; server identity validation via known endpoints |
| **TC7: Cross-Tool Chaining** | Sequences of benign tool calls that compose into an attack | Receipt chain linking — each tool call receipt references the prior receipt in the session, enabling sequence-level analysis and rate-based anomaly detection |

**Coverage Claim:** AVS MCP Tool Guard targets **66%** of the 23 MCPSHIELD attack vectors. The remaining 34% (primarily server-internal compromises and client-side prompt-injection variants that bypass the tool layer) require complementary controls outside AVS scope.

---

## 4. Core Objects

This section defines the data model for AVS MCP Tool Guard. All objects are interface definitions — they specify **what** the system must represent, not **how** it is implemented.

---

### 4.1 MCPToolManifest

**Purpose:** Extends the base `ToolManifest` (from v0.3.6) with MCP-specific metadata for identity attestation and capability declaration.

| Field | Type | Description |
|---|---|---|
| `manifest_id` | `string` (UUID) | Unique identifier for this manifest entry |
| `tool_name` | `string` | Canonical name of the MCP tool (e.g., `filesystem_read`) |
| `mcp_server_id` | `string` | Identifier of the MCP server that hosts this tool |
| `mcp_server_endpoint` | `string` (URL) | Resolved endpoint URL for the MCP server |
| `version` | `string` (semver) | Semantic version of the tool definition |
| `classification` | `ToolActionClassification` | Declared action classification (see 4.3) |
| `arguments` | `ArgumentPolicy[]` | Array of argument-level policy constraints (see 4.4) |
| `required_privilege_level` | `string` | Minimum privilege level required to invoke |
| `network_boundaries` | `string[]` | Allowed target domains / IP ranges (empty = no outbound) |
| `file_scope` | `string[]` | Allowed file path prefixes (empty = no file access) |
| `hash_sha256` | `string` | SHA-256 hash of the canonical tool definition JSON |
| `registered_at` | `timestamp` | When this manifest was registered |
| `registered_by` | `AgentIdentity` | Identity of the agent/operator that registered it |

**Relationship:** `MCPToolManifest` references `ToolActionClassification` (4.3) and `ArgumentPolicy` (4.4). It is looked up by `MCPToolCallRequest` (4.2) during the tool identity verification check.

---

### 4.2 MCPToolCallRequest

**Purpose:** Wraps an incoming MCP tool call as an `ActionRequest` for processing by the AVS policy engine.

| Field | Type | Description |
|---|---|---|
| `request_id` | `string` (UUID) | Unique identifier for this tool call request |
| `session_id` | `string` (UUID) | Session identifier linking related tool calls |
| `agent_identity` | `AgentIdentity` | Identity of the calling agent (from v0.3.6) |
| `mcp_server_id` | `string` | Target MCP server identifier |
| `tool_name` | `string` | Name of the tool being invoked |
| `arguments` | `map<string, any>` | Key-value argument map passed to the tool |
| `timestamp` | `timestamp` | Invocation time |
| `preceding_receipt_id` | `string` (UUID, optional) | Receipt ID of the prior tool call in this session (enables chain linking) |

**Relationship:** `MCPToolCallRequest` is matched against `MCPToolManifest` by (`mcp_server_id`, `tool_name`). Its `arguments` are validated against the manifest's `ArgumentPolicy[]`. Its `agent_identity` is checked against the manifest's `required_privilege_level`.

---

### 4.3 ToolActionClassification

**Purpose:** Categorizes the nature of a tool action to enable appropriate policy enforcement and approval routing.

| Field | Type | Description |
|---|---|---|
| `primary_class` | `enum` | One of: `READ`, `WRITE`, `DESTRUCTIVE`, `ADMINISTRATIVE` |
| `description` | `string` | Human-readable description of what the classification means for this tool |
| `auto_approvable` | `boolean` | Whether this classification can proceed without human approval under normal policy |
| `escalation_matrix` | `string[]` | Ordered list of approval roles for actions that require human review |

**Classification Definitions:**

- **READ** — Reads data without modification (e.g., file read, database SELECT)
- **WRITE** — Creates or modifies data (e.g., file write, database INSERT/UPDATE)
- **DESTRUCTIVE** — Deletes, drops, or irreversibly alters data (e.g., file delete, database DROP)
- **ADMINISTRATIVE** — Changes configuration, permissions, or system state (e.g., chmod, grant privileges)

**Relationship:** `ToolActionClassification` is embedded in `MCPToolManifest` (4.1) and referenced in `MCPBoundaryDecision` (4.6) and `MCPToolReceipt` (4.7).

---

### 4.4 ArgumentPolicy

**Purpose:** Defines constraints on a single tool argument at the policy level.

| Field | Type | Description |
|---|---|---|
| `arg_name` | `string` | Name of the argument as declared in the tool schema |
| `arg_type` | `enum` | Expected type: `STRING`, `NUMBER`, `BOOLEAN`, `ARRAY`, `OBJECT`, `PATH`, `URL` |
| `required` | `boolean` | Whether the argument must be present |
| `allowed_pattern` | `string` (regex, optional) | Regex pattern the argument value must match |
| `allowed_range` | `[min, max]` (number, optional) | Numeric range constraint |
| `allowed_values` | `any[]` (optional) | Enumerated set of permitted values |
| `max_length` | `integer` (optional) | Maximum string length |
| `pii_sensitive` | `boolean` | Whether this argument should be PII-scanned |
| `sandboxed_path` | `boolean` | If `arg_type == PATH`, whether the path must resolve within the file sandbox |
| `allowed_domains` | `string[]` (optional) | If `arg_type == URL`, permitted target domains |

**Relationship:** `ArgumentPolicy` is an array element within `MCPToolManifest` (4.1). It is consumed by the argument validation checks (Section 5) during policy evaluation.

---

### 4.5 PIIScanResult

**Purpose:** Records the outcome of PII scanning on tool arguments.

| Field | Type | Description |
|---|---|---|
| `scan_triggered` | `boolean` | Whether a PII scan was performed on this request |
| `pii_found` | `boolean` | Whether any PII was detected |
| `found_types` | `string[]` | List of PII types detected (e.g., `SSN`, `EMAIL`, `PHONE`, `CREDIT_CARD`, `API_KEY`) |
| `affected_arguments` | `string[]` | Names of arguments that contained detected PII |
| `redacted_count` | `integer` | Number of PII instances redacted |
| `redaction_method` | `enum` | `HASH`, `MASK`, `BLOCK`, or `NONE` |
| `scan_confidence` | `float` | Aggregate confidence score across all findings (0.0–1.0) |

**Relationship:** `PIIScanResult` is produced by the PII scan check (Section 5) and embedded in `MCPBoundaryDecision` (4.6) and `MCPToolReceipt` (4.7).

---

### 4.6 MCPBoundaryDecision

**Purpose:** The aggregate decision produced by the MCP Tool Guard policy engine for a single tool call.

| Field | Type | Description |
|---|---|---|
| `decision_id` | `string` (UUID) | Unique identifier for this decision |
| `request_id` | `string` (UUID) | References the `MCPToolCallRequest` |
| `verdict` | `enum` | One of: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `QUARANTINE` |
| `tool_identity_verified` | `boolean` | Check 1: tool found in manifest |
| `tool_classification_allowed` | `boolean` | Check 2: classification permitted for this agent |
| `argument_type_valid` | `boolean` | Check 3: arguments match expected types |
| `argument_range_valid` | `boolean` | Check 4: arguments within allowed ranges |
| `pii_detected` | `boolean` | Check 5: PII scan result |
| `network_boundary_allowed` | `boolean` | Check 6: target within allowed network boundaries |
| `file_scope_allowed` | `boolean` | Check 7: file path within sandbox |
| `privilege_level_sufficient` | `boolean` | Check 8: agent has required privileges |
| `approval_required` | `boolean` | Check 9: destructive action approval needed |
| `rate_limit_exceeded` | `boolean` | Check 10: agent within rate limits |
| `reasons` | `string[]` | Human-readable list of all check failures (empty if all pass) |
| `pii_scan_result` | `PIIScanResult` | Detailed PII scan output |
| `timestamp` | `timestamp` | Decision time |

**Decision Semantics:**

- **ALLOW** — All required checks passed; tool call may proceed.
- **DENY** — One or more hard-failure checks failed; tool call is blocked.
- **REQUIRE_APPROVAL** — Tool call requires human approval before proceeding (typically for DESTRUCTIVE or ADMINISTRATIVE classifications, or privilege escalation detected).
- **QUARANTINE** — PII or other sensitive content was detected; the call is held for review and may be redacted rather than blocked outright.

**Relationship:** `MCPBoundaryDecision` is produced by the policy engine (Section 5) and consumed by the receipt generator (Section 8). A single decision is produced per `MCPToolCallRequest`.

---

### 4.7 MCPToolReceipt

**Purpose:** An ASR-1 receipt enriched with MCP-specific fields, providing a verifiable, immutable record of a governed tool call.

| Field | Type | Description |
|---|---|---|
| `receipt_id` | `string` (UUID) | Unique receipt identifier |
| `asr1_base` | `ASR1Receipt` | The base ASR-1 receipt structure (from v0.3.6) |
| `mcp_tool_name` | `string` | Name of the invoked MCP tool |
| `mcp_server_id` | `string` | MCP server identifier |
| `mcp_server_endpoint` | `string` (URL) | Resolved server endpoint |
| `tool_classification` | `ToolActionClassification` | Classification applied to this invocation |
| `argument_types` | `map<string, string>` | Map of argument names to their type hashes (SHA-256 of canonical type signatures) |
| `pii_scan_result` | `PIIScanResult` | PII scan findings for this call |
| `network_boundary_check` | `object` | `{ passed: boolean, target_domain: string, allowed: boolean }` |
| `file_scope_check` | `object` | `{ passed: boolean, resolved_path: string, allowed: boolean }` |
| `privilege_check` | `object` | `{ passed: boolean, required_level: string, agent_level: string }` |
| `rate_limit_status` | `object` | `{ current_calls: integer, max_calls: integer, window_seconds: integer }` |
| `decision` | `MCPBoundaryDecision` (reference) | The decision ID that produced this receipt |
| `preceding_receipt_id` | `string` (UUID, optional) | Chain link to the prior receipt in the session |
| `gateway_version` | `string` | AVS Gateway version that produced this receipt |

**Relationship:** `MCPToolReceipt` extends the base `ASR1Receipt` (v0.3.6). It embeds `PIIScanResult` (4.5) and references `MCPBoundaryDecision` (4.6). Receipts can be verified via `avs receipt verify`.

---

## 5. Policy Checks

For every `MCPToolCallRequest`, the MCP Tool Guard evaluates the following checks in order. Each check contributes to the final `MCPBoundaryDecision`. Checks are ordered so that hard-failure checks (identity, classification) run before expensive checks (PII scan, boundary validation).

### Check 1: `tool_identity_verified`

**Question:** Is the tool (`tool_name`) registered in the `MCPToolManifest` for the target `mcp_server_id`?

**Pass:** Manifest entry found, version matches, SHA-256 hash verifies.  
**Fail (hard):** Tool not found, version mismatch, or hash mismatch → **DENY**.  
**Addresses:** TC1 (Tool Poisoning), TC4 (Tool Hijacking).

### Check 2: `tool_classification_allowed`

**Question:** Is the tool's declared classification permitted for the calling agent's role?

**Pass:** Classification is in the agent's permitted set.  
**Fail (hard):** Classification exceeds agent's role scope → **DENY**.  
**Addresses:** TC3 (Prompt Injection — overrides), TC5 (Privilege Escalation).

### Check 3: `argument_type_valid`

**Question:** Do the provided arguments match the types declared in the tool's `ArgumentPolicy`?

**Pass:** All provided arguments conform to declared types; all required arguments present.  
**Fail (hard):** Type mismatch or missing required argument → **DENY**.  
**Addresses:** TC1 (Tool Poisoning — schema validation).

### Check 4: `argument_range_valid`

**Question:** Are numeric arguments within allowed ranges, and string arguments within allowed lengths/patterns?

**Pass:** All range, length, and pattern constraints satisfied.  
**Fail (hard):** Range or pattern violation → **DENY**.  
**Addresses:** TC1 (Tool Poisoning — constraint validation).

### Check 5: `pii_detected_in_arguments`

**Question:** Do any arguments marked `pii_sensitive` contain detectable PII?

**Pass:** No PII detected, or PII detected and successfully redacted with confidence >= threshold.  
**Fail (soft):** PII detected and cannot be safely redacted → **QUARANTINE**.  
**Addresses:** TC2 (Data Exfiltration).

### Check 6: `network_boundary_allowed`

**Question:** If the tool targets a network resource, is the target domain/URL within the allowed set?

**Pass:** Target resolves to an allowed domain or IP range.  
**Fail (hard):** Target outside permitted boundaries → **DENY**.  
**Addresses:** TC6 (Server Compromise), TC2 (Data Exfiltration — outbound).

### Check 7: `file_scope_allowed`

**Question:** If the tool accesses the file system, does the resolved path fall within the declared sandbox?

**Pass:** Path resolves within an allowed prefix; no path traversal detected.  
**Fail (hard):** Path escapes sandbox or path traversal detected → **DENY**.  
**Addresses:** TC2 (Data Exfiltration — file access), TC5 (Privilege Escalation).

### Check 8: `privilege_level_sufficient`

**Question:** Does the calling agent's privilege level (from `AgentIdentity`) meet or exceed the tool's `required_privilege_level`?

**Pass:** Agent level >= required level.  
**Fail (hard):** Insufficient privileges → **DENY**.  
**Addresses:** TC5 (Privilege Escalation).

### Check 9: `approval_required_for_destructive`

**Question:** If the tool classification is `DESTRUCTIVE` or `ADMINISTRATIVE`, or if a privilege escalation pattern is detected, is human approval required?

**Pass:** Action is not destructive/administrative, or approval has been granted.  
**Fail (soft):** Destructive/administrative action without prior approval → **REQUIRE_APPROVAL**.  
**Addresses:** TC5 (Privilege Escalation), TC7 (Cross-Tool Chaining — escalation sequences).

### Check 10: `rate_limit_not_exceeded`

**Question:** Is the calling agent within its per-session and per-window rate limits?

**Pass:** Call count within limits.  
**Fail (soft):** Rate limit exceeded → **ALLOW** with rate-limit warning (does not block, but flags for analysis).  
**Addresses:** TC7 (Cross-Tool Chaining — rapid sequences).

---

## 6. Demo Scenarios

The following scenarios demonstrate MCP Tool Guard behavior across the decision spectrum. Each scenario specifies the input conditions and the expected decision.

| # | Scenario | Expected Decision | What It Proves |
|---|---|---|---|
| 1 | Agent calls `filesystem_read` with path `/sandbox/docs/report.txt`. Tool is registered. Classification is READ. Agent has read privileges. Path resolves within sandbox. No PII in arguments. | **ALLOW** | Normal read operation proceeds without friction |
| 2 | Agent calls `filesystem_write` with path `/sandbox/output/result.json`. Tool is registered. Classification is WRITE. Agent has write privileges. Path within sandbox. No PII. | **ALLOW** | Normal write operation proceeds; file-scope check confirms sandbox containment |
| 3 | Agent calls `filesystem_delete` with path `/sandbox/docs/old.txt`. Tool is registered. Classification is DESTRUCTIVE. Agent has delete privileges. All hard checks pass. | **REQUIRE_APPROVAL** | Destructive actions require human approval even when all hard checks pass |
| 4 | Agent calls `unregistered_tool` on a known MCP server. No manifest entry exists for this tool name. | **DENY** | Tool identity enforcement blocks unregistered tools regardless of server trust |
| 5 | Agent calls `send_email` with `recipient="alice@example.com"`, `body="SSN: 123-45-6789"`. Argument `body` is marked `pii_sensitive`. PII scanner detects SSN pattern. | **QUARANTINE** | PII detection quarantines calls with sensitive data that cannot be safely redacted |
| 6 | Agent calls `api_request` with `url="https://evil.com/steal"`. Tool is registered, but `evil.com` is not in the manifest's `allowed_domains`. | **DENY** | Network boundary enforcement blocks calls to non-permitted domains |
| 7 | Agent chains 5 tool calls (`read`, `read`, `read`, `read`, `read`) within 10 seconds on the same session. Each call individually passes all checks. Rate limit: 10 calls/minute. | **ALLOW** (with rate note) | Rate limiting tracks cross-tool chaining; call proceeds but receipt flags rapid sequence |
| 8 | Agent calls `filesystem_read` (ALLOW), then in the same session calls `filesystem_delete` (same path). Session-level escalation from READ → DESTRUCTIVE detected. | **REQUIRE_APPROVAL** | Privilege escalation detection triggers approval for destructive actions following reads in the same session |

---

## 7. Architecture

### 7.1 Component Flow

```
                    ┌─────────────────────────────────────────┐
                    │           MCP Client                    │
                    │  (Claude Desktop, Cursor, IDE, etc.)   │
                    └─────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │           MCP Server                    │
                    │  (stdio/SSE transport)                  │
                    └─────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │           AVS Gateway                   │
                    │  (intercepts tool_call messages)        │
                    └─────────────────┬───────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────┐
                    │        MCP Tool Guard                   │
                    │  ┌─────────────────────────────────┐    │
                    │  │  1. Tool Manifest Check           │    │
                    │  │     └─► Lookup MCPToolManifest    │    │
                    │  │         Verify hash + version     │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  2. Classification Check          │    │
                    │  │     └─► Match agent role to class │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  3. Argument Policy Check         │    │
                    │  │     └─► Type, range, pattern      │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  4. PII Scan                      │    │
                    │  │     └─► Scan pii_sensitive args   │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  5. Network Boundary Check        │    │
                    │  │     └─► Domain / URL allowlist    │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  6. File Scope Check              │    │
                    │  │     └─► Path sandbox resolution   │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  7. Privilege Check               │    │
                    │  │     └─► AgentIdentity vs required │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  8. Escalation Detection          │    │
                    │  │     └─► Session-level progression │    │
                    │  └─────────────────────────────────┘    │
                    │  ┌─────────────────────────────────┐    │
                    │  │  9. Rate Limit Check              │    │
                    │  │     └─► Per-session window        │    │
                    │  └─────────────────────────────────┘    │
                    │                                         │
                    │  ▼ Aggregate: MCPBoundaryDecision        │
                    └─────────────────┬───────────────────────┘
                                      │
                    ┌─────────────────┴───────────────────────┐
                    │                                         │
                    ▼                                         ▼
        ┌─────────────────────┐                   ┌─────────────────────┐
        │   ALLOW / DENY      │                   │  REQUIRE_APPROVAL   │
        │   ─────────────     │                   │  ────────────────   │
        │   Generate Receipt  │                   │  Hold for Human     │
        │   Forward to MCP    │                   │  Review             │
        │   Server            │                   │                     │
        └─────────────────────┘                   └─────────────────────┘
```

### 7.2 Key Design Principles

1. **Fail-closed** — Any check that cannot be evaluated (missing manifest, ambiguous classification) produces a DENY, not an ALLOW.
2. **Evidence-first** — Every check produces a structured result that is captured in the receipt, not just a boolean.
3. **Ordered evaluation** — Cheap checks (identity, classification) run before expensive checks (PII scan, path resolution).
4. **Chain-aware** — Receipts link to prior session receipts, enabling sequence-level analysis without maintaining full session state in the policy engine.
5. **Receipt-verifiable** — Every governed call produces a receipt that can be independently verified via `avs receipt verify`.

---

## 8. ASR-1 Receipt Enrichment

The MCP Tool Guard extends the base ASR-1 receipt (defined in v0.3.6) with MCP-specific fields. This section specifies the enrichment layer.

### 8.1 Enrichment Fields

The following fields are added to the ASR-1 receipt when the governed action is an MCP tool call:

| Field | Type | Source |
|---|---|---|
| `mcp_tool_name` | `string` | `MCPToolCallRequest.tool_name` |
| `mcp_server_id` | `string` | `MCPToolCallRequest.mcp_server_id` |
| `mcp_server_endpoint` | `string` | `MCPToolManifest.mcp_server_endpoint` |
| `tool_classification` | `ToolActionClassification` | `MCPToolManifest.classification` |
| `argument_types` | `map<string, string>` | SHA-256 hash of each argument's canonical type signature |
| `pii_scan_result` | `PIIScanResult` | Output of Check 5 (PII scan) |
| `network_boundary_check` | `object` | Output of Check 6 (network boundary) |
| `file_scope_check` | `object` | Output of Check 7 (file scope) |
| `privilege_check` | `object` | Output of Check 8 (privilege level) |
| `rate_limit_status` | `object` | Output of Check 10 (rate limit) |
| `decision_id` | `string` (UUID) | Reference to `MCPBoundaryDecision.decision_id` |
| `preceding_receipt_id` | `string` (UUID) | Chain link to prior session receipt |
| `gateway_version` | `string` | AVS Gateway version string |

### 8.2 Receipt Verification

Enriched receipts MUST be verifiable via the existing `avs receipt verify` command without modification to the verification CLI. The enrichment layer is additive — base ASR-1 fields retain their semantics, and MCP-specific fields are validated as an extension.

Verification checks:
- ASR-1 signature validity (base)
- Decision-receipt consistency (decision_id resolves to a known decision)
- Chain link validity (preceding_receipt_id exists and is in the same session)
- Manifest hash match (tool definition hash matches registered manifest)

### 8.3 Receipt Chain Linking

Receipts within the same session form a linked chain via `preceding_receipt_id`. This enables:

- **Sequence replay** — Reconstruct the exact order of tool calls in a session.
- **Escalation detection** — Identify when an agent progresses from lower-impact to higher-impact classifications.
- **Cross-tool chaining forensics** — Analyze whether a sequence of individually benign calls composes into an attack pattern.

---

## 9. Dependencies on v0.3.6

MCP Tool Guard is designed as an extension layer on top of existing v0.3.6 infrastructure. The following v0.3.6 components are required:

| Component | Status in v0.3.6 | Usage in v0.4.0 |
|---|---|---|
| **ASR-1 Receipt Format** | Released | Base receipt structure; MCP Tool Guard adds enrichment fields |
| **AgentIdentity** | Released | Provides agent roles and privilege levels for checks 2, 8, 9 |
| **ToolManifest** | Released | Base manifest structure; extended by `MCPToolManifest` for MCP specifics |
| **Policy Engine** | Released | Core policy evaluation framework; MCP checks are policy rules registered in the engine |
| **Network Sandbox** | Released | Provides domain/IP allowlist primitives for Check 6 |
| **File Sandbox** | Released | Provides path resolution and sandbox containment for Check 7 |

**New in v0.4.0:**

- `MCPToolManifest` (extends `ToolManifest`)
- `MCPToolCallRequest` (wraps MCP tool_call as `ActionRequest`)
- `ToolActionClassification` (new classification taxonomy)
- `ArgumentPolicy` (argument-level constraint specification)
- `PIIScanResult` (structured PII scan output)
- `MCPBoundaryDecision` (aggregate decision object)
- `MCPToolReceipt` (ASR-1 enriched receipt)
- PII scanner module (integration point — may delegate to external scanner)
- Session escalation tracker (lightweight state for Check 9)

---

## 10. What This Does NOT Do

To set clear boundaries and avoid scope creep, the following are explicitly **out of scope** for AVS MCP Tool Guard v0.4.0:

1. **Does NOT replace MCP security controls** — MCP Tool Guard complements, rather than replaces, server-side security measures implemented by MCP server authors. It adds a governance layer at the gateway, not at the server.

2. **Does NOT inspect MCP server internals** — AVS has no visibility into how an MCP server implements its tools. It validates the tool definition (manifest) and the tool call (arguments), not the server's internal logic.

3. **Does NOT replace network firewalls** — Network boundary checks (Check 6) are an application-layer gate, not a network-layer firewall. Standard network security (iptables, WAF, VPC) remains the responsibility of the operator.

4. **Does NOT prevent all 23 MCPSHIELD attack vectors** — The target coverage is **66%** of the 23 vectors (approximately 15 vectors). The remaining ~8 vectors (primarily server-internal compromises, client-side prompt injection that bypasses the tool layer, and physical/transport-layer attacks) require complementary controls.

5. **Does NOT implement a full IDS/IPS** — While receipt chain linking enables forensic analysis, real-time intrusion detection is not a goal. The focus is policy enforcement and evidence generation.

6. **Does NOT require MCP server modification** — MCP Tool Guard operates as a transparent intermediary. No changes are required to MCP servers, clients, or the MCP protocol itself.

---

## 11. Success Criteria

The following criteria must be met for MCP Tool Guard to be considered complete for v0.4.0:

| # | Criterion | Metric |
|---|---|---|
| 1 | **Demo scenario correctness** | All 8 demo scenarios (Section 6) produce the expected `MCPBoundaryDecision` verdict |
| 2 | **Receipt verifiability** | 100% of generated `MCPToolReceipt` instances pass `avs receipt verify` |
| 3 | **MCPSHIELD gap coverage** | At least 66% of the 23 MCPSHIELD attack vectors are addressed by at least one policy check |
| 4 | **Regression safety** | All 581 existing AVS Gateway tests continue to pass without modification |
| 5 | **Integration demo** | End-to-end demo with at least one real MCP server (e.g., `filesystem` or `fetch` server from the MCP SDK) |
| 6 | **Performance baseline** | Policy evaluation for a single tool call completes in < 100ms (P99) under normal load |
| 7 | **Receipt chain integrity** | Chain-linked receipts within a session can be verified in sequence without gaps |
| 8 | **Documentation completeness** | All new objects (Section 4), checks (Section 5), and architecture (Section 7) are documented |

---

## 12. Future Extensions

The following capabilities are identified for post-v0.4.0 development. They are noted here to guide design decisions in v0.4.0 (e.g., extensibility points in the receipt format).

### 12.1 Witness-Signed Receipts

In addition to AVS Gateway signing receipts, the MCP server itself could co-sign as a witness. This would provide cryptographic evidence that the tool server acknowledged the call, not just that the gateway approved it. Requires: witness key registration protocol, multi-sig receipt format.

### 12.2 Cross-Session Tool Chaining Detection

Current escalation detection (Check 9) is session-scoped. Cross-session analysis would track an agent's tool usage patterns across multiple sessions to detect gradual privilege accumulation or reconnaissance behavior. Requires: lightweight agent behavior profile storage, anomaly scoring.

### 12.3 Learned Argument Patterns (Anomaly Detection)

Beyond static `ArgumentPolicy` constraints, ML-based anomaly detection could flag unusual argument values (e.g., a file read that always accesses `/sandbox/docs/` suddenly targeting `/etc/`). Requires: argument value frequency profiling, unsupervised anomaly model.

### 12.4 Vertical Policy Packs

Specialized policy packs for specific tool categories:
- **Database Guard** — SQL-aware query classification (SELECT vs. DROP), table-level access control
- **API Guard** — Endpoint-aware rate limiting, OAuth scope validation
- **Shell Guard** — Command-line argument parsing, dangerous-command detection (rm -rf, curl | bash)
- **Git Guard** — Repository-level access control, branch protection awareness

Each vertical pack would be a set of pre-built `MCPToolManifest` templates with tuned `ArgumentPolicy` defaults.

### 12.5 Human-in-the-Loop Approval UI

The `REQUIRE_APPROVAL` verdict currently implies an external approval mechanism. A built-in approval UI (web dashboard, Slack integration) would let operators review, approve, or deny pending destructive actions with full context from the `MCPBoundaryDecision`.

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **MCP** | Model Context Protocol — an open protocol for connecting AI agents to tool servers |
| **ASR-1** | AVS Standard Receipt v1 — the cryptographically signed receipt format used by AVS Gateway |
| **MCPSHIELD** | Research paper (arXiv:2604.05969) cataloging 7 threat categories and 23 attack vectors in the MCP ecosystem |
| **Tool Manifest** | A registered description of a tool's capabilities, arguments, and constraints |
| **Receipt Chain** | A linked sequence of receipts within a session, where each receipt references its predecessor |
| **Fail-Closed** | Security design principle where ambiguous or error conditions default to denial |

## Appendix B: References

1. MCPSHIELD: A Security Analysis of the Model Context Protocol. arXiv:2604.05969, April 2026.
2. AVS Gateway v0.3.5 Release Notes — ASR-1 receipt format, AgentIdentity, ToolManifest.
3. AVS Gateway v0.3.6 Branch Notes — Receipt verification CLI, policy engine extensions.
4. MCP Specification — https://modelcontextprotocol.io/specification

---

*End of RFC. Comments and feedback welcome. This document defines intent, not implementation.*
