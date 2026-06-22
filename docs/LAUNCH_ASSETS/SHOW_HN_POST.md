# Show HN: AVS Gateway  Runtime Permission Layer for AI Agents

**TL;DR:** AVS puts a decision gate between an AI agent's intent and real-world action. Every intercepted call gets evaluated against policy, scored for risk, and logged with a cryptographic receipt. One decorator (`@governed_tool`), zero rewrites.

---

## The Problem

Your AI agent can delete production databases, send emails to customers, charge credit cards, and deploy infrastructure  and by default, none of those actions ask permission before executing. When something goes wrong, you have no evidence trail showing what was attempted, what was blocked, and why.

## What AVS Does

AVS Gateway intercepts agent actions (tool calls, file access, API calls, deployments) **before** they execute. It evaluates each action against 23+ declarative YAML policy rules, scores it across 8 risk dimensions, applies time-weighted trust decay, and returns one of four decisions: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, or `QUARANTINE`. Every decision produces an Ed25519 cryptographically signed receipt with an immutable SHA-256 audit chain.

The `@governed_tool` decorator wraps any Python function. The `AVSGovernedTool` adapter works with LangChain. No framework lock-in.

## Without AVS vs. With AVS

| Without AVS | With AVS |
|---|---|
| Agent calls tool  executes immediately | Agent calls tool  intercepted, evaluated, decision recorded |
| Policy scattered across prompts | 23+ declarative YAML rules, version-controlled |
| No evidence of what was attempted | Ed25519 signed receipts + SHA-256 audit chain |
| Runtime errors may allow execution | Fail-closed: any error  DENY |
| Framework-specific instrumentation | `@governed_tool` decorator  one line, any function |
| Requires cloud services | Local-first: works offline, no API keys |

## Key Facts

- **470+ tests**, zero failures
- **4 quickstart examples** (CLI, Python decorator, LangChain, policy authoring)
- **Fail-closed by design**: any policy engine error, misconfiguration, or adapter failure returns DENY  never ALLOW
- **Framework-agnostic**: LangChain, CrewAI, custom tools  AVS doesn't care
- **Apache 2.0** open core
- **Alpha stage**: seeking design partners running real agent workloads

## Try It (60 seconds)

```bash
pip install avs-gateway
avs version
avs demo
```

`avs demo` runs 3 sample tool calls through the permission layer and shows you the decisions (ALLOW, DENY, REQUIRE_APPROVAL) plus the receipts.

## Code

```python
from avs_gateway import governed_tool

@governed_tool(policy_rules="file_access.yaml")
def delete_file(path: str):
    ...

# The agent calls delete_file("/etc/passwd")
# AVS intercepts, evaluates, returns DENY with a signed receipt.
# The function never executes.
```

## Links

- GitHub: https://github.com/avs-gateway/avs-gateway
- Docs: https://docs.avs-gateway.io
- `avs demo` runs locally, no API keys, no cloud dependency.

## What I'm Looking For

Design partners running real AI agents in production or staging. I need feedback on: (1) policy rule expressiveness  are the 23 built-in rules covering your use cases or are you hitting gapsWARNING (2) adapter ergonomics  does `@governed_tool` actually drop into your codebase without frictionWARNING (3) receipt utility  are the signed receipts useful for your compliance/audit needs, and what's missingWARNING Reply here or email hello@avs-gateway.io.

---

AVS is the execution governance layer between agent intent and real-world action. Every agent action gets a receipt.
