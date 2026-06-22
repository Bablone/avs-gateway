# AVS Gateway — Runtime permission layer for AI agents (v0.3.6 with ASR-1 receipts)

**Every agent action gets a receipt.**

---

## The problem

Agents can now delete files, call APIs, deploy code, send emails, and make payments. But there is no permission layer that decides what should actually execute. Every action runs with implicit trust — if the agent decides to do it, it happens.

## What AVS does

AVS Gateway intercepts agent actions before they execute. It checks policy, risk, trust score, identity, and tool registration — then returns one of four decisions: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, or `QUARANTINE`. Every decision creates an ASR-1 receipt: a signed, verifiable record of what was evaluated, what policy applied, and what evidence was considered.

Think of it like a Kubernetes admission controller, but for autonomous agent actions.

## Why receipts matter

Payment rails like Mastercard AP4M and x402 handle money movement. AVS governs whether the action itself should happen — upstream from any payment. Receipts prove what was decided, by what policy, with what evidence, and when. They make agent decisions auditable.

## How to try it

```bash
pip install -e .
avs demo           # 30-second governance demo
avs receipt verify examples/receipts/allow_receipt.json
```

## What it looks like

```python
from avs_gateway import governed_tool, Gateway

gateway = Gateway()

@governed_tool(gateway=gateway)
def deploy_to_production(manifest: str):
    return f"Deployed {manifest}"

result = deploy_to_production("payment-service.yaml")
# AVS intercepts, evaluates policy, decides, executes or blocks
# Every decision creates a verifiable receipt
```

## What is included

- 581 tests, zero failures
- 4 quickstart examples
- File sandbox, network sandbox, HTTP egress control
- LangChain adapter (`@governed_tool`, `AVSGovernedTool`)
- ASR-1 receipt standard (draft) with signing + verification
- Agent identity model + tool manifest registration
- CLI: `avs demo`, `avs receipt verify`

## Ask HN

If you are building agents with tool access, I would like to know: what action types worry you most?

I am also looking for 3 design partners to validate ASR-1 receipts in real agent workflows — especially if you are working with payment-adjacent actions or multi-agent systems.
