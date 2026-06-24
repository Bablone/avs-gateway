# AVS Gateway

**Runtime permission layer for AI agents. Every agent action gets a receipt.**

AVS Gateway is an early open-source runtime permission layer for AI agents. It sits before agent tool execution, evaluates the requested action against policy, and produces signed receipts showing whether the action was allowed, denied, paused for approval, or blocked.

## Current Status

AVS Gateway v0.3.5 is a public baseline release.

It is suitable for:

* local demos
* research
* security review
* governed-tool experiments
* design-partner conversations
* agent-action risk reviews

It should not yet be treated as production-hardened security infrastructure without additional hardening, review, and deployment controls.

## Core Thesis

Before an agent mutates the world, AVS decides whether the action is allowed - and produces a receipt proving why.

## What Is Proof-Gated Action?

Proof-gated action is the middle path between unsafe autonomy and passivity.

Unsafe autonomy means agents act without sufficient checks, which can lead to damage or runaway decisions.

Passivity means blocking all automation because the risk is too high, which results in missed opportunities and stagnation.

Proof-gated action means agents act only when explicit checks pass, enabling safer and auditable action.

In AVS, those checks can include policy, risk score, trust score, approval status, agent identity, and receipt generation.

## What Is Built in This Baseline

* policy-based action decisions
* four decision outcomes: `allow`, `deny`, `require_approval`, and `quarantine`
* governed Python function support
* LangChain adapter support
* local approval workflow
* receipt and audit trail generation
* local demos and test coverage

## What Is Not Claimed Yet

AVS Gateway does not currently claim:

* production-grade enterprise security certification
* ML-powered risk scoring
* FedRAMP or FIPS compliance
* Slack, PagerDuty, Teams, Jira, or ServiceNow approval integrations
* production-scale storage guarantees
* complete prompt-injection protection
* full multi-framework agent support

## Install

```bash
pip install -e .
```

With optional LangChain support:

```bash
pip install -e ".[langchain]"
```

Verify:

```bash
avs version
```

## 30-Second Demo

```bash
avs demo
```

Example output:

```text
AVS Gateway v0.3.5 - Runtime Permission Layer
=============================================

[ALLOW]   Safe file read -> executed, receipt generated
[DENY]    Dangerous delete -> blocked, reason logged
[PENDING] Production deploy -> queued for human approval

Every governed action produced a receipt.
No governed agent action executes without AVS deciding first.
```

## Quick Start

Run the basic gateway example:

```bash
python examples/quickstart/01_gateway_basics.py
```

Run the governed tool example:

```bash
python examples/quickstart/02_governed_tool.py
```

Run the LangChain adapter example:

```bash
python examples/quickstart/03_langchain_tool.py
```

Run the custom action example:

```bash
python examples/quickstart/04_custom_action.py
```

## How It Works

```text
Agent proposes action
        |
        v
Framework adapter / governed tool
        |
        v
ActionRequest
        |
        v
AVS Gateway
  - Policy Engine
  - Risk Engine
  - Trust Memory
  - Approval Service
        |
        v
Decision: allow / deny / require_approval / quarantine
        |
        v
Receipt + audit trail
```

## Project Positioning

AVS is not a model, agent framework, or prompt firewall.

It is an execution governance layer for agent actions. It is designed to sit between agent intent and real-world side effects, then produce evidence of the decision that was made.

## Release Notes

* `v0.3.5` - public baseline release
* `v0.3.5.1` - superseded cleanup attempt
* `v0.3.5.2` - clean public baseline release with internal launch assets removed and README repositioned

## License

Apache License 2.0. See LICENSE.

## Contributing

This project is early. Issues, security review, and design feedback are welcome.

## Security Status

AVS Gateway is alpha software. Do not deploy it as production security infrastructure without independent review and additional hardening.

Known hardening areas include:

* network egress controls
* file sandbox race-condition hardening
* approval timeout handling
* content provenance and prompt-injection-aware session tagging
* production storage backends
* reproducible performance and security benchmarks

---

**Every agent action gets a receipt.**
