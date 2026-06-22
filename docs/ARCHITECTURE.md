# AVS Gateway Architecture

> **Every agent action gets a receipt.**

AVS is a universal action control plane for autonomous systems. It intercepts
agent actions before they execute, evaluates policy and risk, and produces
cryptographic evidence for every decision.

---

## The Two Layers

### Layer 1: The Law (Gateway)

The Gateway is the **universal semantic intercept**. It does not care what
the tool does. It cares whether the action should be allowed.

Every action, regardless of framework or tool type, becomes an
`ActionRequest`:

```
ActionRequest
 agent_id           who is acting
 action_type        category (file, api, payment, deployment...)
 tool_name          what tool
 operation          what operation
 parameters         inputs
 context            environment, role, classification
```

The Gateway evaluates through four engines:

| Engine | Purpose |
|--------|---------|
| **Policy Engine** | 23+ declarative rules (YAML/JSON) |
| **Risk Engine** | 8-dimension risk scoring |
| **Trust Memory** | Time-weighted agent trust decay |
| **Approval Service** | Human-in-the-loop workflow |

And returns a **Decision**:

| Decision | Meaning |
|----------|---------|
| **ALLOW** | Execute the action |
| **DENY** | Block the action |
| **REQUIRE_APPROVAL** | Queue for human review |
| **QUARANTINE** | Isolate for security review |

Every decision produces a **cryptographic receipt** (Ed25519-signed, SHA-256)
and is appended to an **immutable audit chain**.

### Layer 2: The Physics (Sandboxes)

Sandboxes are **domain-specific execution constraints** for the most
dangerous physical surfaces.

| Sandbox | Version | Protects Against |
|---------|---------|-----------------|
| **FileSandbox** | v0.3.0 | Path traversal, sandbox escape |
| **HTTPSandbox** | v0.3.2 | SSRF, metadata exfiltration, mutations |

For SaaS APIs (Stripe, Slack, Salesforce), the API provider **is** the
sandbox. AVS governs the **authorization decision**. The API enforces the
physical boundary.

---

## The Universal Pipeline

```
Agent proposes action
        |
        v
+----------------------------+
|  Framework Adapter Layer   |
|                            |
|  OpenClaw    ActionRequest|
|  @governed   ActionRequest|
|  LangChain   ActionRequest|
|  CrewAI      ActionRequest|   (future)
|  MCP         ActionRequest|   (future)
|  Custom      ActionRequest|
+-------------+--------------+
              |
              v
+----------------------------+
|      AVS Gateway           |
|                            |
|  Policy  + Risk + Trust   |
|                           |
|        Decision            |
|                           |
|    Receipt + Audit         |
+-------------+--------------+
              |
        +-----+-----+
        |           |
        v           v
    ALLOW       DENY/APPROVE
        |           |
        v           v
   Execute      Block
        |           |
        v           v
   Evidence    Evidence
```

**The key insight:** Every framework-specific call becomes a universal
`ActionRequest`. The Gateway does not need to know about LangChain,
CrewAI, or your custom tool. It only needs to evaluate the action.

---

## Adapters: Framework Integration

Adapters convert framework-specific tool calls into universal
`ActionRequest` objects.

### @governed_tool (v0.3.1)

For standalone Python functions:

```python
@governed_tool(tool_name="send_email", action_type=ActionType.EMAIL, operation="send")
def send_email(to, subject, body):
    # Original code  unchanged
    ...
```

### AVSGovernedTool (v0.3.3)

For LangChain BaseTool objects:

```python
governed_search = govern_langchain_tool(tool=search_tool, gateway=gateway, ...)
agent = create_react_agent(llm, tools=[governed_search])
```

### Future Adapters

The same pattern applies to any framework:

| Framework | Adapter Status |
|-----------|---------------|
| LangChain |  v0.3.3 |
| CrewAI | Planned |
| AutoGen | Planned |
| MCP (Model Context Protocol) | Planned |
| Custom | Always available via `@governed_tool` or direct `ActionRequest` |

---

## Receipts and Audit

Every decision produces a **Receipt**:

```python
Receipt
 receipt_hash       SHA-256 of the full decision record
 timestamp          when the decision was made
 action_request     what was requested
 decision           allow / deny / approval / quarantine
 reason             why the decision was made
 risk_score         numerical risk assessment
 trust_score        agent trust at decision time
 signature          Ed25519 cryptographic signature
```

Receipts are:
- **Cryptographically signed**  non-repudiable
- **Immutable**  tamper-evident via hash chain
- **Verifiable**  anyone can verify the signature

The **Audit Chain** is an append-only SHA-256 linked chain:

```
Block 0: genesis_hash
Block 1: hash(action_1 + genesis_hash)
Block 2: hash(action_2 + block_1_hash)
...
Block N: hash(action_N + block_N-1_hash)
```

Tampering with any block breaks the chain. The entire history is
verifiable.

---

## Policy Engine

Policies are **declarative rules** defined in YAML or JSON:

```yaml
rules:
  - name: block_file_deletion
    description: File deletion is prohibited by default
    priority: 10
    condition:
      action_type: file
      operation: delete
    decision: DENY
    reason: File deletion requires explicit approval
```

Rules are evaluated in priority order. First match wins. If no rule
matches, the **default decision is DENY** (fail-closed).

Organizations can add their own rules for custom actions:

```yaml
  - name: production_deploy_approval
    condition:
      action_type: api
      operation: deploy_prod
    decision: REQUIRE_APPROVAL
    reason: Production deployments require CISO approval
```

---

## Scaling: How New Actions Are Governed

When an organization adds a new tool, AVS does not need to change:

1. **Developer wraps the tool** with `@governed_tool` or an adapter
2. **Action becomes an ActionRequest** automatically
3. **Policy engine evaluates** the action type, operation, and context
4. **Decision is enforced**  allow, deny, or require approval
5. **Receipt is generated**  immutable evidence

AVS does not need to "know" about deployment, trading, healthcare, or
finance. It needs to know how to intercept, decide, and record evidence.
**The organization provides the tools, the policies, and the meaning.**

---

## Files and Modules

```
avs_gateway/
 __init__.py              # Package exports
 cli.py                   # avs demo / version / quickstart
 adapters/
    __init__.py
    base_adapter.py      # Adapter interface
    governed.py          # @governed_tool decorator
    langchain_adapter.py # LangChain BaseTool wrapper
    openclaw_adapter.py  # OpenClaw bridge
 core/
    gateway_core.py      # Central orchestrator
    policy_engine.py     # Declarative rule engine
    risk_engine.py       # Multi-dimension risk scoring
    trust_memory.py      # Time-weighted trust decay
    receipt_generator.py # Ed25519 receipt signing
    audit_chain.py       # Immutable SHA-256 chain
    approval_service.py  # Human approval workflow
 models/
    action_request.py    # Universal action representation
 tools/
    file_sandbox.py      # Filesystem physics (v0.3.0)
    http_sandbox.py      # Network physics (v0.3.2)
    real_tool_registry.py # Tool registration
    simulated_tools.py   # Mock tools for testing
 server/
    gateway_server.py    # FastAPI REST API
 storage/
    sqlite_store.py      # Persistent approval storage
 config/
    default_policies.yaml
    sandbox_policies.yaml
    network_policies.yaml
 tests/
     unit/
     integration/
```

---

## Design Principles

1. **Fail-closed.** Any error, missing policy, or unknown condition
   results in DENY, not allow.

2. **Receipts are non-negotiable.** Every decision produces evidence.
   There is no silent allow.

3. **Framework-agnostic.** The Gateway knows nothing about LangChain,
   CrewAI, or any framework. Adapters handle translation.

4. **Organization-extensible.** Custom tools, custom policies, custom
   action types  all pass through the same pipeline.

5. **Local-first.** No cloud dependency. No external API keys. Works
   offline. Customer-controlled keys.

---

## Further Reading

- [QUICKSTART.md](QUICKSTART.md)  Install and first steps
- [README.md](../README.md)  Project overview and positioning
- `docs/GOVERNED_ADAPTER.md`  @governed_tool usage guide
- `docs/LANGCHAIN_ADAPTER.md`  LangChain integration guide
- `docs/REAL_TOOL_SANDBOX.md`  Filesystem sandbox documentation
- `docs/NETWORK_BOUNDARY.md`  Network sandbox documentation
