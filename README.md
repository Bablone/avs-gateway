# AVS Gateway  Runtime Permission Layer for AI Agents

> **Every agent action gets a receipt.**

AVS Gateway is a runtime permission layer for AI agents. It enables proof-gated
action: agents can act, but only when policy, risk, trust, identity, and
evidence checks justify execution. Payment rails like Mastercard AP4M and x402
handle money movement. AVS governs whether the action itself  file access, API
calls, deployments, database queries, emails, or payments  should be allowed.
Every decision creates a verifiable ASR-1 receipt.

---

## What Is Proof-Gated ActionWARNING

Proof-gated action is the middle path between unsafe autonomy and passivity.

| Mode | Description | Risk |
|------|-------------|------|
| **Unsafe Autonomy** | Agents act without sufficient evidence | Damage, runaway decisions |
| **Passivity** | Blocking all automation because risk is too high | Missed opportunities, stagnation |
| **Proof-Gated Action** | Agents act only when explicit checks pass | Safe, auditable action |

In AVS, those checks include policy, risk score, trust score, approval status,
agent identity, tool manifest registration, and ASR-1 receipt generation.

---

## Install

```bash
pip install -e .
```

Or with LangChain support:

```bash
pip install -e ".[langchain]"
```

Verify:

```bash
avs version
```

---

## 30-Second Demo

```bash
avs demo
```

You will see:

```
AVS Gateway v0.3.6  Runtime Permission Layer
================================================

[ALLOW]   Safe file read  executed, receipt generated
[DENY]    Dangerous delete  blocked, reason logged
[PENDING] Production deploy  queued for human approval

Every action produced a cryptographic receipt.
No agent action executes without AVS deciding first.
```

---

## Quick Start (5 Minutes)

### 1. Gateway basics  intercept any action

```bash
python examples/quickstart/01_gateway_basics.py
```

```python
from avs_gateway.core.gateway_core import Gateway
from avs_gateway.models.action_request import create_action_request, ActionType

gateway = Gateway()

action = create_action_request(
    agent_id="my_agent",
    action_type=ActionType.FILE,
    tool_name="file_delete",
    operation="delete",
    parameters={"path": "/etc/passwd"},
)

decision = gateway.intercept(action)
print(f"Decision: {decision.decision_type.value}")   # "deny"
print(f"Reason:   {decision.reason}")                  # "Policy denied"

receipt = gateway.record(action, decision)
print(f"Receipt:  {receipt.receipt_hash}")             # sha256...
```

### 2. Govern a Python function  one decorator

```bash
python examples/quickstart/02_governed_tool.py
```

```python
from avs_gateway.adapters.governed import governed_tool
from avs_gateway.models.action_request import ActionType

@governed_tool(
    tool_name="send_email",
    action_type=ActionType.EMAIL,
    operation="send",
)
def send_email(to: str, subject: str, body: str) -> dict:
    # Your original code  unchanged
    smtp.send(to, subject, body)
    return {"status": "sent"}

# Call it normally  AVS intercepts automatically
result = send_email("user@example.com", "Hello", "World")
# Returns: GovernedResult(decision="allow", receipt=..., ...)
```

### 3. Govern a LangChain tool  wrap and go

```bash
python examples/quickstart/03_langchain_tool.py
```

```python
from avs_gateway.adapters.langchain_adapter import govern_langchain_tool
from avs_gateway.models.action_request import ActionType

governed_search = govern_langchain_tool(
    tool=original_search_tool,
    gateway=gateway,
    action_type=ActionType.API,
    operation="GET",
)

# Pass to your LangChain agent  AVS controls execution
agent = create_react_agent(llm, tools=[governed_search])
```

### 4. Govern a custom business action  any action, any domain

```bash
python examples/quickstart/04_custom_action.py
```

```python
@governed_tool(
    tool_name="deploy_to_production",
    action_type=ActionType.API,
    operation="deploy_prod",
    context={"environment": "production"},
)
def deploy_to_prod(manifest: str) -> str:
    kubectl.apply(manifest)
    return "Deployed"

# AVS returns REQUIRE_APPROVAL  tool does NOT execute
# until a human approves it through the dashboard.
```

---

## How It Works

```
Agent proposes action
        |
        v
+---------------------+     +------------------+
|  Framework Adapter  |     |  @governed_tool  |
|  (LangChain, etc.)  |     |  (any function)  |
+----------+----------+     +--------+---------+
           |                           |
           +------------+--------------+
                        |
                        v
            +-----------------------+
            |   ActionRequest         |
            |   (tool, operation,     |
            |    context, params)     |
            +-----------+-----------+
                        |
                        v
            +-----------------------+
            |   AVS Gateway           |
            |                         |
            |  Policy Engine    ----  |
            |  Risk Engine      ----  |----> ALLOW
            |  Trust Memory     ----  |----> DENY
            |  Approval Service ----  |----> REQUIRE_APPROVAL
            +-----------+-----------+      QUARANTINE
                        |
                        v
            +-----------------------+
            |   Decision Enforced     |
            |   (execute or block)    |
            +-----------+-----------+
                        |
                        v
            +-----------------------+
            |   Cryptographic Receipt |
            |   Immutable Audit Chain |
            |   Dashboard Timeline    |
            +-----------------------+
```

Every action  file, API, database, deployment, custom business logic  flows
through the same pipeline. The Gateway does not care what the action is. It
cares whether the action should be allowed, based on policy, risk, trust,
identity, and evidence.

> **Analogy:** AVS is like a Kubernetes admission controller for autonomous
> systems: it intercepts agent intent before state mutation, validates identity,
> policy, and risk, then admits, denies, or escalates before execution.

---

## Before AVS / After AVS

| Without AVS | With AVS |
|-------------|----------|
| "My agent deleted production data. I don't know why." | "My agent tried to delete production data. AVS blocked it and I have a receipt." |
| "I added a new tool. Now I hope it's safe." | "I added a new tool. AVS intercepted it, scored it, and let me approve it first." |
| "I need to audit agent actions. Let me grep the logs." | "Every action has a cryptographic receipt. The audit chain is tamper-evident." |
| "This LangChain tool can do anything. I trust it." | "Every LangChain tool call goes through AVS policy before executing." |
| "I wrote a policy. I hope it's enforced." | "Policy is enforced at the execution layer. No bypass path." |

---

## Who AVS Is Not

AVS works alongside the tools you already use. It is the **execution governance
layer** that sits between agent intent and real-world action.

| Product | What It Does | How AVS Complements It |
|---------|-------------|------------------------|
| **LangSmith** | Observability  logs what agents did | LangSmith observes after the fact. AVS **controls** whether actions execute in the first place. |
| **Guardrails AI** | Output validation  checks LLM responses | Guardrails validates text outputs. AVS governs **runtime actions** (tool calls, file access, APIs). |
| **Prompt Firewall** | Input/output filtering  inspects prompts | Prompt firewalls inspect text. AVS gates **execution** (tools, files, APIs). |
| **OPA/Gatekeeper** | Policy engine  makes authorization decisions | OPA makes policy decisions. AVS adds agent-aware adapters, cryptographic receipts, audit chains, and approval workflows. |
| **Lakera/HiddenLayer** | AI security  prompt injection, data loss prevention | AI security tools focus on model-layer threats. AVS is a **runtime constraint engine** for agent actions. |

---

## What Is Included

```
v0.1.0  Core Gateway
         Intercept  Decide  Record pipeline
         Four decisions: allow, deny, require_approval, quarantine
         Policy engine (23 declarative rules, YAML/JSON)
         Risk engine (8-dimension scoring)
         Trust memory (time-weighted decay)
         Ed25519 cryptographic receipts
         Immutable SHA-256 audit chain

v0.2.0  Persistent Approval Loop
         SQLite-backed approval queue
         Human approve/deny workflow
         REST API (FastAPI)
         Timeline visualization

v0.3.0  Filesystem Physics
         Path canonicalization (prevents traversal)
         Sandboxed read/write/delete
         Real file I/O with security boundaries

v0.3.1  Developer Adoption
         @governed_tool decorator
         Zero-friction: one line, no rewrites
         Bring-your-own-tools model

v0.3.2  Network Physics
         HTTP GET allowlist
         SSRF prevention (metadata, private IPs)
         POST/mutation blocking
         Redirect severance
         Response size caps + timeout

v0.3.3  LangChain Integration
         AVSGovernedTool wrapper
         Optional dependency (no bloat)
         Universal control plane proof

v0.3.4  Developer Release Foundation
         pip install -e .
         avs demo CLI
         4 quickstart examples
         README + architecture docs
         Apache 2.0 license
         CI (GitHub Actions)

v0.3.5  Public Launch Readiness Pack
         README polish, launch assets
         Show HN post, outreach templates
         FAQ, competitive positioning
         Standing watch template

v0.3.6  ASR-1 Receipt Standard + Agent Identity Draft   CURRENT
         ASR-1 draft receipt format (portable, verifiable)
         AgentIdentity model (accountable principals)
         ToolManifest registration (execution surfaces)
         Receipt signing + verification CLI
         Tamper-evident linked hash chain
         581 tests, zero failures
         docs/ASR_1_RECEIPT_STANDARD.md
```

---

## Architecture: The Universal Control Plane

AVS separates governance into two layers:

### The Law (Gateway)

Universal semantic intercept. Every action becomes an `ActionRequest`:

```python
ActionRequest(
    action_type=ActionType.API,           # file, api, payment, deployment...
    tool_name="deploy_to_production",     # any tool name
    operation="deploy_prod",              # any operation
    parameters={...},                     # any parameters
    context={"environment": "production"}, # any context
)
```

The Gateway evaluates policy, risk, trust, identity, and tool manifest
registration. It returns a decision. **It does not care what the tool does.**
It cares whether the action should be allowed.

### The Physics (Sandboxes)

Domain-specific execution constraints for the most dangerous surfaces:

- **FileSandbox** (v0.3.0): Prevents path traversal and sandbox escapes
- **HTTPSandbox** (v0.3.2): Prevents SSRF, mutations, and exfiltration

For SaaS APIs (Stripe, Slack, Salesforce), the API provider is the sandbox.
AVS governs the **authorization decision**. The API enforces the physical
boundary.

### The Result

**AVS does not anticipate scenarios. AVS provides the infrastructure for
organizations to govern their own.**

---

## Roadmap

```
v0.3.6  ASR-1 Receipt Standard + Agent Identity Draft   CURRENT
        ASR-1 draft receipt format, AgentIdentity model,
        ToolManifest registration, receipt signing + verification CLI,
        tamper-evident linked hash chain, 581 tests

v0.4.0  Verifiable Identity Runtime (signed agent actions)
v0.4.1  Tool Manifest Integrity (tamper detection)
v0.4.2  Audit Export (CSV/JSON/CloudEvents/OpenTelemetry)
v0.5.0  Enterprise Control Room (dashboard, RBAC, policy packs)
```

Enterprise features will be proprietary/commercial add-ons. The open-source
core remains free under Apache 2.0.

**Status:** Alpha. AVS is production-grade code (581 tests, zero failures)
but the API and receipt format may change as we learn from real deployments.
We recommend starting with non-critical workflows.

---

## License

**Core**: [Apache License 2.0](LICENSE)  free for commercial and
non-commercial use, including an explicit patent license grant.

**Enterprise features** (future: hosted dashboard, SSO, compliance packs,
managed audit retention) will be offered under a proprietary commercial
license.

---

## Contributing

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for development setup.

All contributors must sign a Contributor License Agreement (coming soon).

---

> **Every agent action gets a receipt.**
>
> AVS Gateway  Runtime Permission Layer for AI Agents
