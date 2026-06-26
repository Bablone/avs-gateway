# AVS Gateway: Honest Alpha Status

**Version:** v0.4.0-alpha  
**Date:** 2026-06-25

---

## What AVS Gateway Actually Is

AVS Gateway is an early-stage open-source runtime permission layer for AI agents that call tools through MCP (Model Context Protocol). Its strongest built feature is cryptographically signed ASR-1 execution receipts.

---

## What Is Genuinely Built and Working

| Feature | Status | Evidence |
|---------|--------|----------|
| Four-outcome decision model (ALLOW, DENY, REQUIRE_APPROVAL, QUARANTINE) | Real | 626+ tests |
| Rule-based policy engine with YAML loading | Real | 626+ tests |
| Heuristic risk scoring across 8 dimensions | Real | 415 lines, keyword matching |
| Trust memory with exponential decay | Real | Time-weighted scoring |
| ASR-1 receipts with Ed25519 signing | Real | 18 receipt-specific tests |
| Receipt chain verification | Real | Chain integrity tests |
| Audit chain with SQLite storage | Real | Full CRUD tests |
| Approval lifecycle (pending->approved->executed) | Real | Replay protection tests |
| LangChain tool adapter | Real | Pydantic v2 compatible |
| MCP Guard v0.4.0-alpha | Real | 17 action classes, 47 tests |
| Path traversal prevention | Real | Adversarial tests |
| IP-based SSRF blocking | Real | Network sandbox tests |
| Credential header stripping | Real | HTTP sandbox tests |

---

## What Is NOT Built (despite claims in some materials)

| Feature | Status | Reality |
|---------|--------|---------|
| ML-powered risk scoring | Not built | Heuristic keyword matching only |
| ~40M parameter transformer | Not built | Never existed |
| AutoGen adapter | Not built | Only LangChain |
| CrewAI adapter | Not built | Only LangChain |
| LlamaIndex adapter | Not built | Only LangChain |
| Slack HITL integration | Not built | Console only |
| PagerDuty integration | Not built | Console only |
| Teams integration | Not built | Console only |
| Jira integration | Not built | Console only |
| ServiceNow integration | Not built | Console only |
| 85% production auto-approval | Not real | No production deployment data |
| DNS pre-resolution (rebinding-safe) | Not working | Known vulnerability SEC-001 |
| TOCTOU-safe file operations | Not working | Known vulnerability SEC-002 |
| FedRAMP compliance | Not claimed | FIPS 140-2/140-3 not implemented |
| Performance benchmarks | Not built | latency_ms hardcoded to 0.0 |

---

## Known Vulnerabilities

See [SECURITY_STATUS.md](SECURITY_STATUS.md) for full details. 7 vulnerabilities: 2 CRITICAL, 3 HIGH, 2 MEDIUM.

---

## What "Alpha" Means Here

- The core receipt system is solid and well-tested.
- The policy engine works for basic scenarios.
- The MCP Guard handles 17 action classes deterministically.
- The security sandbox has known gaps (documented above).
- **This is suitable for:** evaluation, evaluation proof-of-concepts, proof-of-concepts.
- **This is NOT suitable for:** production deployment with real data, regulated environments, high-security scenarios.

---

## The Honest Pitch

**Instead of:** "Production-grade autonomous agent security platform"

**Say:** "Early runtime permission layer with signed execution receipts. We're building the evidence layer for agent actions. Currently in alpha -- suitable for evaluation and design partnerships."

---

## Roadmap

| Version | Focus | Target Items |
|---------|-------|-------------|
| v0.4.1-alpha | Security fix pack | DNS pinning (SEC-001), TOCTOU fix (SEC-002), HITL timeout (SEC-004), trust hardening (SEC-003) |
| v0.4.2 | Evidence hardening | Explainable scoring, policy conflict visibility (SEC-005) |
| v0.4.3 | Content provenance | Prompt injection defense (SEC-007), session tagging |
| v0.5.0 | Production backend | PostgreSQL backend, performance benchmarks, chaos engineering tests |

