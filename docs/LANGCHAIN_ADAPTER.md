# AVS LangChain Tool Adapter (v0.3.3-beta)

## The Universal Action Control Plane

AVS is not a filesystem monitor. AVS is not a network firewall. AVS is not a
LangChain plugin.

AVS is a **universal action control plane** for autonomous systems.

The LangChain adapter exists to prove this architecture: that any framework's
tool execution can be intercepted, converted into a universal `ActionRequest`,
evaluated by the AVS Gateway, and either allowed (with evidence) or blocked
(with a structured response to the agent).

**LangChain is the first framework adapter. CrewAI, AutoGen, and custom agents
will follow the same pattern.**

---

## Architecture: The Two Layers

AVS separates governance into two distinct layers:

### Layer 1: The Law (Gateway)

The Gateway is the **semantic intercept**. It is universal.

It receives an `ActionRequest` containing:
- **tool_name**  what tool is being invoked
- **operation**  what operation is being attempted
- **action_type**  the category (file, api, payment, deployment, anything)
- **context**  who, where, when, why

And returns a **Decision**: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `QUARANTINE`.

The Gateway does not care whether the action is `file.read`,
`stripe.charge`, `deploy_to_production`, or `access_patient_phi`.
**Any action can be expressed as an ActionRequest.**

This is the **"no governed action passes before AVS"** layer.

### Layer 2: The Physics (Sandboxes)

The Filesystem Sandbox (v0.3.0) and Network Sandbox (v0.3.2) are
**domain-specific execution constraints**.

They exist because for certain universal primitives (local disk, outbound
HTTP), **policy alone is not enough**. A bug or prompt injection could
bypass a policy and execute a raw `open()` call. The sandboxes ensure
that even if an agent tries to escape, the physical execution environment
mathematically prevents it.

For SaaS APIs (Stripe, Slack, Salesforce), the API provider **is** the
sandbox. AVS governs the **authorization decision** (should this agent be
allowed to ask Stripe to chargeWARNING). Stripe enforces the physical boundary.

---

## The Proof: Custom Business Actions

### What the built-in scenarios prove

Scenarios 1-6 (file read/write, HTTP GET/POST, path traversal, SSRF) prove
that AVS can govern **infrastructure primitives**. These are the PHYSICS.

### What Scenario 7 proves

Scenario 7 (`deploy_to_production`) proves that AVS can govern **actions it
has never seen before**, defined by the organization, not by AVS.

```python
# This is NOT a built-in AVS action type.
# This is a custom business action defined by the organization.

govern_langchain_tool(
    tool=DeployToProductionTool(),
    gateway=gateway,
    action_type=ActionType.API,        # Generic type
    operation="deploy_prod",           # Organization-specific operation
    context={"environment": "production", "service": "payment-processor"},
)
```

```yaml
# Organization-defined policy (not built into AVS)
policies:
  - action_type: "api"
    operation: "deploy_prod"
    decision: REQUIRE_APPROVAL
    reason: "Production deployments require CISO approval"
```

**Result:** The tool does not execute. The agent receives a structured
approval-pending message. A cryptographic receipt is generated.

This proves:
- AVS does not anticipate scenarios
- AVS provides the infrastructure for organizations to govern their own
- Custom enterprise tools pass through the same pipeline as built-in tools

---

## Usage

### Wrap a single tool

```python
from avs_gateway.adapters.langchain_adapter import govern_langchain_tool
from avs_gateway.models.action_request import ActionType

governed_search = govern_langchain_tool(
    tool=original_search_tool,
    gateway=gateway,
    action_type=ActionType.API,
    operation="GET",
    agent_id="my_agent",
)
```

### Wrap multiple tools

```python
from avs_gateway.adapters.langchain_adapter import govern_langchain_tools

governed_tools = govern_langchain_tools(
    tools=[search_tool, file_tool, deploy_tool],
    gateway=gateway,
    action_type=ActionType.API,
)
```

### Govern a custom business tool

```python
# Your organization's custom tool
class DeployToProductionTool(BaseTool):
    name = "deploy_to_production"
    description = "Deploy to production Kubernetes cluster"

    def _run(self, manifest: str) -> str:
        kubectl.apply(manifest, cluster="prod")
        return "Deployed"

# Wrap with AVS  same API as any other tool
governed_deploy = govern_langchain_tool(
    tool=DeployToProductionTool(),
    gateway=gateway,
    action_type=ActionType.API,
    operation="deploy_prod",
    context={"environment": "production"},
)

# Agent uses it  AVS intercepts automatically
result = governed_deploy.run("manifests/app.yaml")
# If policy says REQUIRE_APPROVAL:
#  Tool does NOT execute
#  Returns: "[AVS PENDING] Tool 'deploy_to_production' requires approval..."
```

---

## How It Works

### Tool identity preserved

`AVSGovernedTool` inherits from LangChain's `BaseTool` and preserves:
- `name`  the LLM sees the original tool name
- `description`  the LLM sees the original description
- `args_schema`  the LLM generates correct arguments

The LLM decides **when** to call the tool. AVS decides **whether** it executes.

### Decision handling

| Decision | What happens |
|----------|-------------|
| **ALLOW** | Wrapped tool executes. Receipt recorded. Result returned. |
| **DENY** | Tool does NOT execute. Structured block message returned. |
| **REQUIRE_APPROVAL** | Tool queued for human approval. Pending message returned. |
| **QUARANTINE** | Tool isolated. Block message returned. |

### Block message format

When blocked, the agent receives a structured message designed to be fed
back into the LLM's context window:

```
[AVS DENY] Tool 'file_delete' was blocked.
Reason: File deletion is prohibited by default
Receipt: a1b2c3d4...
You do not have permission to execute this action.
Consider using a different tool or asking for assistance.
```

---

## Why Intercept at the Tool LayerWARNING

```
WRONG: Intercept at LLM/prompt layer
        Competes with AI firewalls (wrong category)
        Prompt injection cat-and-mouse

WRONG: Rewrite LangChain's agent loop
        Fragile (breaks on LangChain updates)
        High maintenance

RIGHT:  Intercept at BaseTool execution layer
        Stable API surface
        Same pattern works for CrewAI, AutoGen
        Minimal coupling
```

---

## Demo Scenarios

| # | Scenario | Type | What It Proves |
|---|----------|------|----------------|
| 1 | File read (sandbox) | Physics | v0.3.0 filesystem boundary |
| 2 | Path traversal | Physics | Path escape blocked |
| 3 | File write (sandbox) | Physics | Valid writes allowed |
| 4 | Sandbox escape | Physics | Write outside blocked |
| 5 | HTTP GET | Physics | v0.3.2 network boundary |
| 6 | HTTP POST | Physics | Mutations blocked |
| 7 | **Custom deploy tool** | **Universal** | **Any action is governable** |
| 8 | File delete | Policy | High-risk actions blocked |

**Scenario 7 is the proof that AVS is not limited to file and HTTP.**

---

## Testing

```bash
# All tests (langchain tests skip gracefully if dependency missing)
pytest avs_gateway/tests/ -q

# LangChain-specific tests
pytest avs_gateway/tests/unit/test_langchain_adapter.py -v
pytest avs_gateway/tests/integration/test_langchain_agent_adapter.py -v
```

---

## Limitations

- **Async**: `_arun()` returns a "not supported" message. Full async support
  is planned for a future release.
- **Streaming**: Tool output is captured as a string, not streamed.
- **LangChain dependency**: `langchain-core` and `langchain` are required
  for the adapter but NOT for AVS core.

---

## The Category-Defining Narrative

> AVS is a universal action control plane for autonomous systems.
> Agents may reason, plan, and select tools, but no governed action
> reaches execution until AVS converts it into a canonical ActionRequest,
> evaluates policy, risk, and trust, records cryptographic evidence,
> and returns an allow, deny, approval, or quarantine decision.
>
> Filesystem and network governance are the first secured physical
> boundaries. Custom tools and framework adapters route arbitrary
> organization-specific actions through the same decision and evidence
> pipeline.
