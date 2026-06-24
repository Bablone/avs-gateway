# AVS Gateway

**Runtime permission layer for AI agents. Every agent action gets a receipt.**

AVS Gateway is an early open-source runtime permission layer for AI agents. It sits before agent tool execution, evaluates the requested action against policy, and produces signed ASR-1 receipts showing whether the action was allowed, denied, paused for approval, or blocked.

## Current Status

AVS Gateway is currently in alpha.

It is suitable for:

* local demos
* research
* security review
* MCP/tool-call governance experiments
* design-partner pilots
* agent-action risk reviews

It should not yet be treated as production-hardened security infrastructure without additional hardening, review, and deployment controls.

## Core Thesis

Before an agent mutates the world, AVS decides whether the action is allowed - and produces a signed receipt proving why.

## What Is Proof-Gated Action?

Proof-gated action is the middle path between unsafe autonomy and passivity.

| Mode               | Description                                      | Risk                             |
| ------------------ | ------------------------------------------------ | -------------------------------- |
| Unsafe autonomy    | Agents act without sufficient checks             | Damage, runaway decisions        |
| Passivity          | Blocking all automation because risk is too high | Missed opportunities, stagnation |
| Proof-gated action | Agents act only when explicit checks pass        | Safer, auditable action          |

In AVS, those checks can include policy, risk score, trust score, approval status, agent identity, tool manifest registration, and ASR-1 receipt generation.

## What Is Built

* Policy-based action decisions
* Four decision outcomes: `allow`, `deny`, `require_approval`, and `quarantine`
* ASR-1 signed action receipts
* Tamper-evident receipt and audit chain
* MCP Guard alpha for tool-call interception
* LangChain adapter support
* Local demos and test coverage

## What Is Not Claimed Yet

AVS Gateway does not currently claim:

* Production-grade enterprise security certification
* ML-powered risk scoring
* FedRAMP or FIPS compliance
* Slack, PagerDuty, Teams, Jira, or ServiceNow approval integrations
* Production-scale storage guarantees
* Complete prompt-injection protection
* Full multi-framework agent support

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
AVS Gateway v0.4.0-alpha - Runtime Permission Layer
===================================================

[ALLOW]   Safe file read -> executed, receipt generated
[DENY]    Dangerous delete -> blocked, reason logged
[PENDING] Production deploy -> queued for human approval

Every action produced a signed receipt.
No governed agent action executes without AVS deciding first.
```

## MCP Guard Alpha

The v0.4.0-alpha branch adds an MCP Guard proof path for governing tool calls before execution.

Example decision flow:

```text
get_weather -> allow -> executed
write_file  -> require_approval -> blocked pending approval
delete_file -> deny -> blocked
fetch_url   -> deny -> blocked for private/internal IP risk
run_shell   -> deny -> blocked as unknown/high-risk tool
```

## How It Works

```text
Agent proposes action
        |
        v
Framework adapter / MCP Guard / governed tool
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
Signed ASR-1 receipt + audit trail
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

Run the MCP Guard demo:

```bash
python examples/mcp_guard_demo.py
```

## Project Positioning

AVS is not a model, agent framework, or prompt firewall.

It is an execution governance layer for agent actions. It is designed to sit between agent intent and real-world side effects, then produce evidence of the decision that was made.

## Release Notes

* `v0.3.5` - public baseline release
* `v0.3.6` - ASR-1 receipt and agent identity foundation
* `v0.4.0-alpha` - MCP Guard alpha with signed ASR-1 receipt proof
* `v0.4.0-alpha.1` - clean public alpha release with internal launch/research assets removed

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Contributing

This project is early. Issues, security review, and design feedback are welcome.

## Security Status

AVS Gateway is alpha software. Do not deploy it as production security infrastructure without independent review and additional hardening.

Known hardening areas include:

* DNS pinning for network egress controls
* file sandbox race-condition hardening
* approval timeout handling
* content provenance and prompt-injection-aware session tagging
* production storage backends
* reproducible performance and security benchmarks

---

**Every agent action gets a receipt.**
