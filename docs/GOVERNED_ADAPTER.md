# AVS Gateway v0.3.1-beta -- Governed Adapter

## What It Is

The `@governed_tool` decorator turns any Python function into an AVS-governed tool.

No framework dependency. No tool rewrites. One decorator.

```python
from avs_gateway.adapters import governed_tool
from avs_gateway.models.action_request import ActionType

@governed_tool(
    tool_name="file_write",
    action_type=ActionType.FILE,
    operation="write",
)
def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)
    return {"bytes_written": len(content)}

# Every call is intercepted by AVS
result = write_file("sandbox/output.txt", "hello")
# result.executed = True/False
# result.decision = "allow" / "deny" / "require_approval" / "quarantine"
# result.reason = why AVS decided that
# result.receipt_hash = cryptographic proof of the decision
```

## How It Works

```
Developer calls write_file("sandbox/output.txt", "hello")
    |
    v
@governed_tool decorator builds ActionRequest
    |
    v
Gateway.intercept(action_request) -> Decision
    |
    +-- ALLOW   -> execute write_file(), return GovernedResult with receipt
    +-- DENY    -> do NOT execute, return GovernedResult with reason
    +-- REQUIRE_APPROVAL -> do NOT execute, return GovernedResult
    +-- QUARANTINE -> do NOT execute, return GovernedResult
```

## Configuration

### Per-decorator Gateway

```python
from avs_gateway.core.gateway_core import Gateway

gw = Gateway(...)  # your configured gateway

@governed_tool(tool_name="...", action_type=..., operation="...", gateway=gw)
def my_tool(...):
    ...
```

### Global default Gateway

```python
from avs_gateway.adapters import set_default_gateway

set_default_gateway(gw)

# Now all @governed_tool decorators without gateway= use this one
@governed_tool(tool_name="...", action_type=..., operation="...")
def my_tool(...):
    ...
```

## Result Structure

```python
result = my_tool(...)

result.executed        # bool: did the function actually runWARNING
result.decision        # str: "allow", "deny", "require_approval", "quarantine"
result.reason          # str: human-readable explanation
result.risk_score      # int: 0-100
result.trust_score     # int: 0-100
result.function_result # any: return value of the function (if executed)
result.function_error  # str: exception message (if function raised)
result.receipt_hash    # str: cryptographic receipt (if executed+recorded)
result.latency_ms      # float: decision latency in milliseconds

# Serialize for logging/APIs
json_str = json.dumps(result.to_dict())
```

## Introspection

```python
from avs_gateway.adapters import is_governed, get_governed_metadata

assert is_governed(my_tool) is True
meta = get_governed_metadata(my_tool)
# meta = {"tool_name": "...", "action_type": ..., "operation": "..."}
```

## Policy Rule Priority Note

When adding custom allow rules for `file.write`, set priority **above 20** (after `file_write_production` at priority 20). Otherwise your allow rule will match before the production rule, and production file writes will be allowed instead of requiring approval:

```python
# CORRECT: priority 25 matches AFTER file_write_production (priority 20)
pe.add_rule(PolicyRule(
    name="file_write_general_allow",
    priority=25,  # > 20 so production rule wins first
    condition={"action_type": "file", "operation": "write"},
    decision=DecisionType.ALLOW,
    ...
))
```

The default policies have these file-related priorities:
| Rule | Priority | Decision |
|------|----------|----------|
| `file_read` | 10 | ALLOW |
| `file_write_production` | 20 | REQUIRE_APPROVAL (matches `tool_name: .*production.*`) |
| `file_delete` | 5 | DENY |

First matching rule wins. Lower priority number = evaluated first.

## Limitations in v0.3.1-beta

- The decorator captures the function result but does not yet stream it
- Async functions (async def) are not yet supported
- Class methods require passing self explicitly in parameters
- Receipt recording requires the Gateway to have a ReceiptGenerator configured

## Migration Path

### From simulated tools (v0.2.x)

Before:
```python
from avs_gateway.tools.simulated_tools import FileTool

tool = FileTool()
result = tool.execute(action_request)
```

After:
```python
from avs_gateway.adapters import governed_tool
from avs_gateway.models.action_request import ActionType

@governed_tool(tool_name="file_write", action_type=ActionType.FILE, operation="write")
def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)

result = write_file("sandbox/output.txt", "hello")
```

### To LangChain (v0.3.2)

The `@governed_tool` decorator is the primitive. The LangChain adapter
(v0.3.2) will internally use this decorator to wrap LangChain tools
without the developer needing to change their tool definitions.
