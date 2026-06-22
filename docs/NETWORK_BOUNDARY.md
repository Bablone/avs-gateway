# AVS Network Boundary Sandbox (v0.3.2-beta)

## Overview

The Network Boundary Sandbox governs all outbound HTTP requests from AI agents,
preventing data exfiltration, SSRF attacks, cloud metadata exploits, and
resource exhaustion.

This is the **third physics boundary** in AVS:

| Boundary | Version | What It Controls |
|----------|---------|-----------------|
| Filesystem | v0.3.0-alpha | Local file read/write |
| Function Execution | v0.3.1-beta | Which functions agents can call |
| **Network Egress** | **v0.3.2-beta** | **Outbound HTTP requests** |

## Security Model: 10-Layer Defense

Every HTTP request passes through 10 independent validation layers.
**If any layer fails, the request is blocked.**

```
Layer 1: Method validation        → Only GET allowed (configurable)
Layer 2: Scheme validation        → Only http:// and https://
Layer 3: Credential rejection     → No user:pass@ in URLs
Layer 4: Domain allowlist         → Explicit permit required
Layer 5: DNS + IP blocklist       → SSRF protection (RFC 1918, loopback, metadata)
Layer 6: Header stripping         → Auth/cookie headers removed
Layer 7: Redirect prevention      → allow_redirects=False
Layer 8: Response size cap        → Stream terminated at 100KB
Layer 9: Timeout enforcement      → 5-second ceiling
Layer 10: Redirect status block   → 300-399 responses treated as attacks
```

## Usage

### Basic (standalone)

```python
from avs_gateway.tools.http_sandbox import HTTPSandbox

sandbox = HTTPSandbox(allowed_domains={"api.example.com"})

# ALLOWED: domain is in allowlist
result = sandbox.get("https://api.example.com/data")
print(result.status)       # "success"
print(result.status_code)  # 200
print(result.resolved_ip)  # "93.184.216.34"

# BLOCKED: domain not allowlisted
blocked = sandbox.get("https://evil.com/exfil")
print(blocked.status)   # "blocked"
print(blocked.reason)   # "Domain 'evil.com' not in allowlist"

# BLOCKED: POST not allowed
blocked = sandbox.post("https://api.example.com/api", data={"key": "val"})
print(blocked.reason)   # "HTTP method POST not allowed"
```

### With YAML config

```python
sandbox = HTTPSandbox.from_config("avs_gateway/config/network_policies.yaml")
```

### With Gateway integration

```python
from avs_gateway.core.gateway_core import Gateway
from avs_gateway.models.action_request import ActionType, create_action_request
from avs_gateway.tools.http_sandbox import HTTPSandbox

# Create sandbox with allowed domains
http_sandbox = HTTPSandbox(allowed_domains={"api.trusted.com"})

# Create action request
action = create_action_request(
    agent_id="my_agent",
    action_type=ActionType.API,
    tool_name="http_get",
    operation="GET",
    parameters={"url": "https://api.trusted.com/data"},
)

# Gateway decides
result = gateway.intercept(action)
if result.decision_type.value == "allow":
    # Execute through sandbox (defense in depth)
    http_result = http_sandbox.get("https://api.trusted.com/data")
    receipt = gateway.record(action, result)
```

## SSRF Protection

The sandbox blocks all requests to private/reserved IP ranges:

| Range | Type |
|-------|------|
| 10.0.0.0/8 | Private Class A |
| 172.16.0.0/12 | Private Class B |
| 192.168.0.0/16 | Private Class C |
| 127.0.0.0/8 | Loopback |
| 169.254.0.0/16 | Link-local (AWS metadata!) |
| 100.64.0.0/10 | Carrier-grade NAT |
| ::1/128 | IPv6 loopback |
| fc00::/7 | IPv6 unique local |
| fe80::/10 | IPv6 link-local |

### Defense in Depth: Metadata Endpoints

Even if an operator accidentally adds `169.254.169.254` to the domain allowlist,
two independent protections still block it:

1. **IP blocklist**: 169.254.169.254 falls in 169.254.0.0/16 (link-local)
2. **Explicit metadata check**: Hardcoded block for known metadata endpoints

## Configuration

```yaml
# avs_gateway/config/network_policies.yaml
network:
  allowed_domains:
    - "api.example.com"
    - "data.public.org"

  allow_loopback_for_testing: false  # NEVER true in production

  max_response_bytes: 102400  # 100 KB
  timeout_seconds: 5

  allowed_methods:
    - "GET"
```

## Testing

```bash
# Unit tests (deterministic, no network)
pytest avs_gateway/tests/unit/test_http_sandbox.py -v

# Integration tests (local mock server)
pytest avs_gateway/tests/integration/test_http_boundary.py -v

# Demo (7 scenarios)
python demo/network_boundary_demo.py
```

## Threat Coverage

| Attack | Layer | Status |
|--------|-------|--------|
| Data exfiltration via POST | Layer 1 (method) | Blocked |
| FTP/file:// protocol abuse | Layer 2 (scheme) | Blocked |
| Credential leakage in URL | Layer 3 (credentials) | Blocked |
| Unknown domain access | Layer 4 (allowlist) | Blocked |
| Internal network probing | Layer 5 (IP blocklist) | Blocked |
| AWS metadata SSRF | Layer 5 + Layer 10 | Blocked |
| Auth header leakage | Layer 6 (header strip) | Blocked |
| Redirect to malicious site | Layer 7 + Layer 10 | Blocked |
| Response amplification DoS | Layer 8 (size cap) | Blocked |
| Slowloris / resource exhaustion | Layer 9 (timeout) | Blocked |

## Limitations

- **DNS rebinding**: v0.3.2 resolves DNS before the request. A sophisticated
  attacker could flip the DNS record between validation and execution.
  Full protection requires custom TCP-level handling (future work).
- **IPv6 literal URLs without brackets** (`https://::1/path`) are rejected
  by URL parsing, not by the sandbox. This is acceptable — valid IPv6 URLs
  must use brackets (`https://[::1]/path`).
