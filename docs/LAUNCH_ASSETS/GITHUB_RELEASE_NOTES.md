# AVS Gateway v0.3.4  Developer Release Foundation

## Overview

v0.3.4 is the foundation release for developers. It contains the full permission layer, policy engine, risk scorer, trust model, cryptographic receipts, CLI, and framework adapters  stable enough to evaluate, early enough to shape.

**Status:** Alpha. Seeking design partners running real agent workloads.

---

## What's New in v0.3.4

- **Complete policy engine**: 23+ declarative YAML rules with boolean composition (`AND`, `OR`, `NOT`)
- **8-dimension risk scoring**: Action sensitivity, data access, network exposure, financial impact, irreversibility, blast radius, compliance scope, trust tier
- **Time-weighted trust decay**: Agent trust score decays based on time since last verified action
- **4 decision outcomes**: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `QUARANTINE`
- **Ed25519 signed receipts**: Every decision produces a cryptographically signed receipt
- **SHA-256 audit chain**: Immutable chain linking receipts for tamper evidence
- **Fail-closed design**: Any policy engine error, misconfiguration, or adapter failure returns DENY
- **Local-first operation**: No cloud dependency, no API keys, works offline
- **`@governed_tool` decorator**: One-line Python decorator for any function
- **LangChain adapter**: `AVSGovernedTool` wraps LangChain tools without rewrites
- **CLI commands**: `avs version`, `avs demo`, `avs policy validate`, `avs receipt verify`
- **4 quickstart examples**: CLI walkthrough, Python decorator, LangChain integration, policy authoring
- **470+ tests**, zero failures

---

## Version Tree

```
v0.1.0   Core interception layer, basic ALLOW/DENY decisions
v0.1.5   YAML policy engine, declarative rule definitions
v0.2.0   Risk scoring engine (4 dimensions)
v0.2.5   Ed25519 cryptographic receipts, SHA-256 audit chain
v0.3.0   Trust decay model, REQUIRE_APPROVAL / QUARANTINE decisions
v0.3.2   LangChain adapter (AVSGovernedTool)
v0.3.3   CLI (avs version, avs demo, avs policy validate)
v0.3.4   Full risk model (8 dimensions), 23+ rules, 470+ tests, fail-closed hardening
```

---

## Install

```bash
pip install avs-gateway==0.3.4
```

Requires Python 3.10+.

---

## Quick Start (5 min)

### 1. Install and verify

```bash
pip install avs-gateway
avs version
#  AVS Gateway v0.3.4
```

### 2. Run the demo

```bash
avs demo
```

This executes 3 sample tool calls through the permission layer and prints decisions plus receipts.

### 3. Try the decorator

```python
from avs_gateway import governed_tool

@governed_tool(policy_rules="rules.yaml")
def send_email(to: str, body: str):
    ...
```

### 4. Validate your policy

```bash
avs policy validate rules.yaml
```

### 5. Verify a receipt

```bash
avs receipt verify receipt.json --public-key avs.pub
```

Full quickstart: https://docs.avs-gateway.io/quickstart

---

## What's Included

| Component | Status | Notes |
|---|---|---|
| Permission engine | Stable | Core ALLOW/DENY/REQUIRE_APPROVAL/QUARANTINE |
| Policy engine (YAML) | Stable | 23+ rules, boolean composition |
| Risk scorer | Stable | 8 dimensions, weighted scoring |
| Trust model | Stable | Time-weighted decay |
| Receipt signing (Ed25519) | Stable | Cryptographic proof per decision |
| Audit chain (SHA-256) | Stable | Tamper-evident receipt linking |
| `@governed_tool` decorator | Stable | Python function wrapper |
| LangChain adapter | Stable | `AVSGovernedTool` class |
| CLI | Stable | version, demo, policy validate, receipt verify |
| CrewAI adapter | Planned | Q3 2025 |
| OpenAPI endpoint filter | Planned | Q3 2025 |
| Policy rule builder (UI) | Planned | Q4 2025 |
| Web dashboard | Planned | Q4 2025 |

---

## Breaking Changes

None. v0.3.4 is backward-compatible with all v0.3.x configurations. If you are upgrading from v0.2.x:

- Policy YAML schema has a new optional `trust_threshold` field. Existing policies without it default to the previous behavior.
- The `AVSGovernedTool` constructor signature added optional `risk_weights`. Existing calls are unaffected.

---

## Known Limitations

- **Alpha stage**: AVS has not yet been battle-tested in production environments with high-throughput agent workloads. The permission engine is stable; the policy library will expand based on real-world feedback.
- **Single-node only**: No distributed consensus for policy updates across multiple agent instances. Each instance loads policy independently.
- **Receipt storage**: Receipts are written to local filesystem by default. No built-in aggregation or centralized audit log yet.
- **Framework coverage**: LangChain and raw Python supported. CrewAI, AutoGen, and other frameworks need community adapters.
- **Policy rules**: 23 built-in rules cover common cases (file access, network calls, financial operations, PII). Niche domains (medical devices, industrial control) may need custom rule development.
- **No managed service**: Self-hosted only. No cloud dashboard, no hosted policy distribution.

---

## Next Up

| Milestone | Target | Scope |
|---|---|---|
| v0.4.0 | July 2025 | CrewAI adapter, OpenAPI endpoint filtering, async support |
| v0.5.0 | August 2025 | Policy hot-reload, receipt aggregation API, performance benchmarks |
| v0.6.0 | September 2025 | Web dashboard (local), policy rule builder UI |
| v1.0.0 | Q4 2025 | Production-stable API, managed service option, SOC 2 mapping |

---

## Stats

- 470+ tests, zero failures
- 4 quickstart examples
- 100% local  no API keys, no cloud dependency
- Apache 2.0 licensed

---

## Feedback

Open an issue: https://github.com/avs-gateway/avs-gateway/issues  
Email: hello@avs-gateway.io

---

*AVS is the execution governance layer between agent intent and real-world action. Every agent action gets a receipt.*
