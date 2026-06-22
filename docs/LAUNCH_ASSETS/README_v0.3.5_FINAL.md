# AVS Gateway a Runtime Permission Layer for AI Agents

> **Every agent action gets a receipt.**

**AVS is to agent actions what OAuth is to user logins:** the permission layer that
decides what executes and proves what happened.

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
AVS Gateway v0.3.5 a Runtime Permission Layer
================================================

[ALLOW]  Safe file read a executed, receipt generated
[DENY]  Dangerous delete a blocked, reason logged
[PENDING] Production deploy a queued for human approval

Every action produced a cryptographic receipt.
No agent action executes without AVS deciding first.
```

---

## Quick Start (5 Minutes)

### 1. Gateway basics a intercept any action

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
print(f"Decision: {decision.decision_type.value}")  # "deny"
print(f"Reason:  {decision.reason}")         # "Policy denied"

receipt = gateway.record(action, decision)
print(f"Receipt: {receipt.receipt_hash}")       # sha256...
```

### 2. Govern a Python function a one decorator

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
  # Your original code a unchanged
  smtp.send(to, subject, body)
  return {"status": "sent"}

# Call it normally a AVS intercepts automatically
result = send_email("user@example.com", "Hello", "World")
# Returns: GovernedResult(decision="allow", receipt=..., ...)
```

### 3. Govern a LangChain tool a wrap and go

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

# Pass to your LangChain agent a AVS controls execution
agent = create_react_agent(llm, tools=[governed_search])
```

### 4. Govern a custom business action a any action, any domain

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

# AVS returns REQUIRE_APPROVAL a tool does NOT execute
# until a human approves it through the dashboard.
```

---

## How It Works

```
Agent proposes action
    |
    v
+---------------------+   +------------------+
| Framework Adapter |   | @governed_tool |
| (LangChain, etc.) |   | (any function) |
+----------+----------+   +--------+---------+
      |              |
      +------------+--------------+
            |
            v
      +-----------------------+
      |  ActionRequest     |
      |  (tool, operation,   |
      |  context, params)   |
      +-----------+-----------+
            |
            v
      +-----------------------+
      |  AVS Gateway      |
      |             |
      | Policy Engine  ---- |
      | Risk Engine   ---- |----> ALLOW
      | Trust Memory   ---- |----> DENY
      | Approval Service ---- |----> REQUIRE_APPROVAL
      +-----------+-----------+   QUARANTINE
            |
            v
      +-----------------------+
      |  Decision Enforced   |
      |  (execute or block)  |
      +-----------+-----------+
            |
            v
      +-----------------------+
      |  Cryptographic Receipt |
      |  Immutable Audit Chain |
      |  Dashboard Timeline  |
      +-----------------------+
```

Every action a file, API, database, deployment, custom business logic a flows
through the same pipeline. The Gateway does not care what the action is. It
cares whether the action should be allowed, based on policy, risk, trust, and
human approval.

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
| **LangSmith** | Observability a logs what agents did | LangSmith observes after the fact. AVS **controls** whether actions execute in the first place. |
| **Guardrails AI** | Output validation a checks LLM responses | Guardrails validates text outputs. AVS governs **runtime actions** (tool calls, file access, APIs). |
| **Prompt Firewall** | Input/output filtering a inspects prompts | Prompt firewalls inspect text. AVS gates **execution** (tools, files, APIs). |
| **OPA/Gatekeeper** | Policy engine a makes authorization decisions | OPA makes policy decisions. AVS adds agent-aware adapters, cryptographic receipts, audit chains, and approval workflows. |
| **Lakera/HiddenLayer** | AI security a prompt injection, data loss prevention | AI security tools focus on model-layer threats. AVS is a **runtime constraint engine** for agent actions. |

---

## What Is Included

```
v0.1.0 Core Gateway
    aaa Intercept a Decide a Record pipeline
    aaa Four decisions: allow, deny, require_approval, quarantine
    aaa Policy engine (23 declarative rules, YAML/JSON)
    aaa Risk engine (8-dimension scoring)
    aaa Trust memory (time-weighted decay)
    aaa Ed25519 cryptographic receipts
    aaa Immutable SHA-256 audit chain

v0.2.0 Persistent Approval Loop
    aaa SQLite-backed approval queue
    aaa Human approve/deny workflow
    aaa REST API (FastAPI)
    aaa Timeline visualization

v0.3.0 Filesystem Physics
    aaa Path canonicalization (prevents traversal)
    aaa Sandboxed read/write/delete
    aaa Real file I/O with security boundaries

v0.3.1 Developer Adoption
    aaa @governed_tool decorator
    aaa Zero-friction: one line, no rewrites
    aaa Bring-your-own-tools model

v0.3.2 Network Physics
    aaa HTTP GET allowlist
    aaa SSRF prevention (metadata, private IPs)
    aaa POST/mutation blocking
    aaa Redirect severance
    aaa Response size caps + timeout

v0.3.3 LangChain Integration
    aaa AVSGovernedTool wrapper
    aaa Optional dependency (no bloat)
    aaa Universal control plane proof

v0.3.4 Developer Release Foundation
    aaa pip install -e .
    aaa avs demo CLI
    aaa 4 quickstart examples
    aaa README + architecture docs
    aaa Apache 2.0 license
    aaa CI (GitHub Actions)

v0.3.5 Public Launch Readiness Pack a CURRENT
    aaa README polish, launch assets
    aaa Show HN post, outreach templates
    aaa FAQ, competitive positioning
    aaa 470 tests, zero failures
```

---

## Architecture: The Universal Control Plane

AVS separates governance into two layers:

### The Law (Gateway)

Universal semantic intercept. Every action becomes an `ActionRequest`:

```python
ActionRequest(
  action_type=ActionType.API,      # file, api, payment, deployment...
  tool_name="deploy_to_production",   # any tool name
  operation="deploy_prod",       # any operation
  parameters={...},           # any parameters
  context={"environment": "production"}, # any context
)
```

The Gateway evaluates policy, risk, and trust. It returns a decision.
**It does not care what the tool does.** It cares whether the action should
be allowed.

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
v0.3.5 Public Launch Readiness Pack    a CURRENT
    README polish, launch assets,
    Show HN post, outreach templates,
    FAQ, competitive positioning

v0.3.6 Dashboard Mission Control
    Unified event view across all adapters
    Approval queue for LangChain/custom actions
    Real-time timeline

v0.4.0 Design Partner Staging
    First real company, real workflow
    Pilot report + testimonial

v0.4.1 Production Connectors
    Slack, Stripe (test mode), database examples

v0.5.0 Enterprise Hardening
    Auth, RBAC, multi-tenancy
    Compliance evidence export (future roadmap)
    Policy packs
    SIEM integrations
```

Enterprise features will be proprietary/commercial add-ons. The open-source
core remains free under Apache 2.0.

---

## License

**Core**: [Apache License 2.0](LICENSE) a free for commercial and
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
> AVS Gateway a Runtime Permission Layer for AI Agents

