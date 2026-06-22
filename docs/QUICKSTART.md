# AVS Gateway Quickstart Guide

> **Every agent action gets a receipt.**

Get AVS running locally in under 10 minutes.

---

## Install

### Prerequisites

- Python 3.10+
- pip

### Install AVS

```bash
# Clone the repository
git clone https://github.com/avsgateway/avs-gateway
cd avs-gateway

# Install in editable mode
pip install -e .
```

### Verify

```bash
avs version
```

Expected output:
```
AVS Gateway 0.3.4
Runtime Permission Layer for AI Agents
Every agent action gets a receipt.
```

### Optional: LangChain Support

```bash
pip install -r requirements-langchain.txt
```

---

## 30-Second Demo

```bash
avs demo
```

You will see three decisions:

| # | Action | Decision | Meaning |
|---|--------|----------|---------|
| 1 | Read file from sandbox | **ALLOW** | Safe action  executed |
| 2 | Delete /etc/passwd | **DENY** | Dangerous  blocked |
| 3 | Deploy to production | **REQUIRE_APPROVAL** | Needs human review |

Each action produces a cryptographic receipt. No action executes without AVS
deciding first.

---

## Quickstart Examples

### Example 1: Gateway Basics

Intercept any action and get a decision + receipt.

```bash
python examples/quickstart/01_gateway_basics.py
```

**Expected output:**
```
[1] Safe file read (sandbox/report.txt)
    Decision : allow
    Reason   : Risk low
    Receipt  : 3f2a8b1c...

[2] Dangerous delete (/etc/passwd)
    Decision : deny
    Reason   : File deletion is not allowed by default
    Receipt  : 7e4d9f2a...
     Tool execution BLOCKED

[3] Production deployment (payment-processor)
    Decision : require_approval
    Reason   : Operation requires human approval
    Receipt  : 9c1b4e8d...
     Queued for human approval
```

**What you learn:** Every action produces a `Decision` and a `Receipt`.
The receipt is a SHA-256 hash that cryptographically proves the decision
was recorded.

---

### Example 2: @governed_tool Decorator

Wrap any Python function with one line. No rewrites.

```bash
python examples/quickstart/02_governed_tool.py
```

**Key code:**
```python
from avs_gateway.adapters.governed import governed_tool

@governed_tool(tool_name="read_config", action_type=ActionType.FILE, operation="read")
def read_config_file(path: str) -> str:
    return f"Contents of {path}: ..."

# Call normally  AVS intercepts automatically
result = read_config_file("settings.conf")
# result.decision = "allow"
# result.receipt_hash = "3f2a8b..."
```

**What you learn:** Your original code is unchanged. AVS adds the
permission layer around it.

---

### Example 3: LangChain Tool Adapter

Wrap a LangChain tool with AVS governance.

```bash
python examples/quickstart/03_langchain_tool.py
```

> If LangChain is not installed, the script prints clear install
> instructions and exits gracefully.

**Key code:**
```python
from avs_gateway.adapters.langchain_adapter import govern_langchain_tool

governed_search = govern_langchain_tool(
    tool=original_search_tool,
    gateway=gateway,
    action_type=ActionType.API,
    operation="GET",
)

# Pass to LangChain agent  AVS controls every tool call
agent = create_react_agent(llm, tools=[governed_search])
```

**What you learn:** LangChain tools work unchanged. AVS intercepts at
the tool execution layer.

---

### Example 4: Custom Business Action

**This is the Universal Control Plane proof.**

AVS governs actions it has never seen before. The organization defines
the tool, the policy, and the meaning.

```bash
python examples/quickstart/04_custom_action.py
```

**Key code:**
```python
# Organization defines a custom policy
policy_engine.add_rule(PolicyRule(
    name="production_deploy_approval",
    condition={"action_type": "api", "operation": "deploy_prod"},
    decision=DecisionType.REQUIRE_APPROVAL,
    reason="Production deployments require CISO approval",
))

# AVS intercepts the custom action
decision = gateway.intercept(action)
# decision = REQUIRE_APPROVAL
# Tool does NOT execute until approved
```

**What you learn:** AVS does not anticipate scenarios. AVS provides the
infrastructure for organizations to govern their own.

---

## Run the Test Suite

```bash
python -m pytest avs_gateway/tests -q
```

Expected: 470+ tests pass, 0 failures.

---

## Run All Demos

```bash
# Core demos
python demo/gateway_demo.py
python demo/governed_adapter_demo.py
python demo/real_tool_sandbox_demo.py

# Physics boundaries
python demo/network_boundary_demo.py

# Framework adapter
python demo/langchain_adapter_demo.py

# Approval workflow
python demo/dashboard_approval_loop_demo.py
```

---

## Next Steps

1. **Wrap your first tool** with `@governed_tool` or the LangChain adapter
2. **Define your policies** in YAML or Python
3. **Run the dashboard** to see the approval queue
4. **Read the architecture docs** at `docs/ARCHITECTURE.md`

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'avs_gateway'`

Make sure you installed with `pip install -e .` from the repo root.

### LangChain example fails

Install the optional dependency:
```bash
pip install -r requirements-langchain.txt
```

### Tests fail

Install test dependencies:
```bash
pip install pytest pytest-asyncio
```

---

## Support

- Issues: [github.com/avsgateway/avs-gateway/issues](https://github.com/avsgateway/avs-gateway/issues)
- Discussions: [github.com/avsgateway/avs-gateway/discussions](https://github.com/avsgateway/avs-gateway/discussions)
