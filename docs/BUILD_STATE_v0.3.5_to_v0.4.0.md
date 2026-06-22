# AVS Build State: v0.3.5 → v0.3.6 → v0.4.0
## What is done. What is next. What to build.

**Date:** 2026-06-22
**Status:** v0.3.5 released. v0.3.6 branch active. v0.4.0 spec complete.

---

## v0.3.5 — RELEASED AND LOCKED

```
[=======] 100% — DO NOT TOUCH
```

| Component | Status |
|-----------|--------|
| Runtime permission layer | Shipped |
| Policy engine (23+ rules) | Shipped |
| Risk engine (8 dimensions) | Shipped |
| Trust memory | Shipped |
| File sandbox | Shipped |
| Network sandbox (HTTP egress) | Shipped |
| @governed_tool decorator | Shipped |
| LangChain adapter | Shipped |
| CLI (version, demo, quickstart) | Shipped |
| README + launch assets | Shipped |
| 496 tests | Passing |
| Version 0.3.5 (all 3 files) | Locked |

**Archive:** `avs-gateway-v0.3.5-public-launch-readiness-pack-fixed2.zip`

---

## v0.3.6 — BUILT (needs verification)

```
[=======>] 90% — BRANCH ACTIVE
```

| Component | Status | File |
|-----------|--------|------|
| ASR-1 receipt generation | Built | `receipts/asr1.py` |
| ASR-1 signing (Ed25519) | Built | `receipts/asr1.py` |
| ASR-1 verification | Built | `receipts/asr1.py` |
| ASR-1 chain verification | Built | `receipts/asr1.py` |
| AgentIdentity model | Built | `identity/agent_identity.py` |
| ToolManifest registration | Built | `tools/tool_manifest.py` |
| CLI receipt verify | Built | `cli.py` |
| 85 new tests | Written | `test_asr1_*.py`, etc. |
| 4 example receipts | Created | `examples/receipts/*.json` |
| JSON schema | Created | `schemas/asr_1_receipt.schema.json` |
| RAILS/OWASP/MCPSHIELD mapping | Added | `docs/ASR_1_RECEIPT_STANDARD.md` |

### What needs to happen before merge:
- [ ] Windows verification (your machine)
- [ ] README updated to "Agent Admission Controller"
- [ ] 2+ design partners validate receipt shape
- [ ] All tests pass (581)

---

## v0.4.0 — SPEC COMPLETE (ready to build)

```
[>        ] 0% — SPEC WRITTEN, BUILD NOT STARTED
```

### The Complete Spec
**Document:** `docs/v0.4.0_MCP_GUARD_COMPLETE_SPEC.md` (580+ lines)

**What v0.4.0 proves:**
> AVS can govern MCP tool calls before execution.

### Architecture (4 layers)

| Layer | Module | Purpose |
|-------|--------|---------|
| 1: Inventory | `mcp/manifest.py` | Server fingerprinting, manifest drift detection |
| 2: Classification | `mcp/classifier.py` | Deterministic action classification (13 classes) |
| 3: Policy | `mcp/policy.py` | Admission decisions (allow/deny/approve/quarantine) |
| 4: Proxy | `mcp/proxy.py` | JSON-RPC MitM proxy (HTTP/SSE) |

### Hardening (from 5-document synthesis)

| Hardening | Source | Impact |
|-----------|--------|--------|
| Server fingerprinting + manifest drift | File 4 (Shadow MCP) | Critical — detects trojan servers |
| JSON-RPC Proxy-in-the-Middle | File 4 + File 5 | Critical — transparent interception |
| Shadow Tool deny rule | File 5 | High — prevents hidden tool execution |
| Sampling hole default deny | File 5 | High — prevents prompt injection |
| Schema validation defense | File 5 | High — prevents argument injection |
| Session Data Tags (exfiltration guard) | File 5 | High — catches read-then-exfiltrate |
| Approval UX (MCP error format) | File 5 | Critical — doesn't break protocol |

### Policy Packs (3 files created)

| Pack | Use Case | File |
|------|----------|------|
| Default | Normal developers | `docs/v0.4.0_policy_packs/mcp_default_policy.yaml` |
| Strict | Enterprise/production | `docs/v0.4.0_policy_packs/mcp_strict_policy.yaml` |
| Dev | Local demos | `docs/v0.4.0_policy_packs/mcp_dev_policy.yaml` |

### Demo Scenario

**Title:** "One agent. Six MCP tools. AVS decides what gets admitted."

```
get_weather → ALLOW
read_file → ALLOW (if in workspace)
write_file → REQUIRE_APPROVAL
delete_file → DENY
fetch_url(169.254.169.254) → QUARANTINE
send_email → REQUIRE_APPROVAL
```

### Test Plan

| Category | Count | Examples |
|----------|-------|----------|
| Unit tests | 18+ | manifest hash, classification, policy, receipt |
| Integration tests | 8+ | observe mode, enforce mode, exfiltration |
| Adversarial tests | 8+ | trojan server, shadow tool, read-then-exfiltrate |
| **Total target** | **34+** | |

### Release Gates

1. tools/list inventory works
2. tools/call guard works in simulated MCP flow
3. All 4 decisions exercised
4. ASR-1 receipt per decision
5. Manifest + descriptor hash included
6. Path traversal + private-IP tests pass
7. Shadow tool attack test passes
8. Read-then-exfiltrate session tag test passes
9. Schema validation defense test passes
10. Receipt verify passes
11. Windows test suite clean
12. This spec document published

### What NOT to build in v0.4.0

- Full hosted control room (v0.5)
- LLM-based classifier (v0.5+)
- Full DLP engine (v0.5+)
- Payment settlement state (v0.4.1)
- Cross-org witness receipts (v0.5+)
- Standards submission (later)

---

## The File Inventory

### Documents (what exists now)

```
docs/
  ALIGNMENT_v0.3.6_AND_BEYOND.md              — Strategic alignment
  ASR_1_RECEIPT_STANDARD.md                    — Receipt standard (draft)
  RFC_MCP_TOOL_GUARD.md                        — MCP Guard RFC (v0.4 concept)
  v0.4.0_MCP_GUARD_COMPLETE_SPEC.md            — Hardened v0.4.0 specification
  BUILD_STATE_v0.3.5_to_v0.4.0.md             — This document
  research/
    HIDDEN_COMPETITORS.md                      — 23 competitors analyzed
    TECH_LANDSCAPE_2026.md                     — 7 standards/papers
    VERTICAL_OPPORTUNITIES.md                  — 7 vertical markets
    COMPLETE_LANDSCAPE_MAP_2026.md             — Full synthesis
  v0.4.0_policy_packs/
    mcp_default_policy.yaml                    — Default policy
    mcp_strict_policy.yaml                     — Strict policy
    mcp_dev_policy.yaml                        — Dev policy
```

### Code (what exists now)

```
avs_gateway/
  receipts/
    __init__.py
    asr1.py                                    — ASR-1 (v0.3.6)
  identity/
    __init__.py
    agent_identity.py                          — AgentIdentity (v0.3.6)
  tools/
    tool_manifest.py                           — ToolManifest (v0.3.6)
  mcp/                                         — DOES NOT EXIST YET (v0.4.0)
    # manifest.py, classifier.py, policy.py,
    # guard.py, proxy.py, sanitizer.py,
    # receipts.py, session.py — ALL TO BUILD
```

---

## The Roadmap

```
v0.3.5  [==========] DONE — Public release, locked
v0.3.6  [========>.] 90% — ASR-1 receipts, needs Windows verify + merge
v0.4.0  [>         ] 0% — MCP Guard, SPEC COMPLETE, ready for build
v0.4.1  [.         ] — Payment Action Guard (after MCP)
v0.5.0  [.         ] — Control Room (hosted dashboard)
v0.5.1  [.         ] — Audit Export (CSV/JSON/SIEM)
v0.6+   [.         ] — Learning Loop Analytics
```

---

## The Question

v0.4.0 spec is written. Policy packs are created. Test plan is defined. The architecture is hardened against 11 attack vectors.

**Do you want to start building v0.4.0 now?**

If yes, I will:
1. Create `avs_gateway/mcp/` module structure
2. Build `manifest.py` (server fingerprinting)
3. Build `classifier.py` (deterministic action classification)
4. Build `policy.py` (MCP-specific policy engine)
5. Build `guard.py` (main orchestration)
6. Build `proxy.py` (JSON-RPC HTTP/SSE proxy)
7. Build `sanitizer.py` (argument scanner)
8. Build `receipts.py` (ASR-1 MCP enrichment)
9. Build `session.py` (session tags, exfiltration guard)
10. Write 34+ tests
11. Create the demo

If no, the spec stays as reference until you're ready.

---

> **MCP gives agents hands. AVS decides when those hands are allowed to touch production.**
