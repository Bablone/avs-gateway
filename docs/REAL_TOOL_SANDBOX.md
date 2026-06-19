# AVS Gateway v0.3.0-alpha -- Real Tool Sandbox

## Threat Model

### What v0.3.0-alpha proves

AVS can govern real filesystem side effects. An agent requests a file operation. AVS intercepts, evaluates the semantic risk, decides allow/deny/approval/quarantine, and ensures the machine obeys AVS rather than the agent.

### What v0.3.0-alpha does NOT prove

- Network boundary control (HTTP GET/POST) -- deferred to v0.3.1
- Framework integration (LangChain, CrewAI) -- deferred to v0.3.2+
- Production deployment -- deferred to v0.4.0+
- Multi-agent governance -- deferred to v0.5.0+

### Attack vectors mitigated

| Attack | Method | Defense |
|--------|--------|---------|
| Path traversal | `../../etc/passwd` | Canonicalization via `Path.resolve()` + `relative_to()` boundary check |
| Absolute path escape | `C:\Windows\evil.dll` or `/etc/passwd` | Absolute paths resolved then checked against sandbox root |
| Symlink escape | `sandbox/link -> /tmp` | `resolve()` follows symlinks; resolved target checked against sandbox root |
| Deep traversal | `sandbox/../../outside.txt` | Multiple `..` components collapsed by `resolve()` |
| File deletion | Any delete request | Explicitly not implemented in v0.3.0-alpha |
| Oversized write | >1MB content | Size check before write |
| Bad extension | `.exe`, `.dll`, `.sh` | Optional extension whitelist |

### Canonicalization algorithm

```
requested_path
    |
    v
if absolute: target = Path(requested_path)
else:         target = sandbox_root / requested_path
    |
    v
canonical = target.resolve()   # follows symlinks, removes .., makes absolute
    |
    v
canonical.relative_to(sandbox_root_resolve())
    |
    +-- succeeds  -> path is inside sandbox -> ALLOW (subject to policy)
    +-- ValueError -> path escapes sandbox -> BLOCK
```

**Critical**: We use `Path.relative_to()`, NOT string `startswith()`. `startswith` fails on paths like `/sandboxfoo/outside.txt` which starts with `/sandbox` but is outside it.

### Why `resolve()` not `abspath()`

- `abspath()` only makes the path absolute. It does NOT follow symlinks or collapse `..`.
- `resolve()` follows ALL symlinks and removes ALL `..` components, giving the true filesystem location.

Example:
```python
Path("sandbox/link_to_tmp/../../etc/passwd").resolve()
# -> Path("/etc/passwd")   (abspath would give something different)
```

### Receipt fields for blocked operations

When a sandbox operation is blocked, the result contains:

```python
{
    "status": "blocked",
    "operation": "write",
    "raw_requested_path": "../outside.txt",      # what the agent asked for
    "resolved_path": None,                        # blocked before resolve
    "success": False,
    "error": "Path escapes sandbox: ...",
    "bytes_handled": 0,
}
```

This enables the timeline to show both the agent's intent and AVS's response.

### Configuration

Sandbox root is configured at runtime:

```python
registry = RealToolRegistry(sandbox_root=Path("./sandbox"))
```

Default limits:
- Max file size: 1MB
- Allowed extensions: none (all allowed) -- set via `allowed_extensions={".txt", ".csv"}`
- No deletion

### Windows compatibility

All path handling uses `pathlib.Path` which is cross-platform. The `resolve()` method handles both forward slashes and backslashes correctly. Tests use `os.name` to select platform-appropriate absolute paths (`C:\...` on Windows, `/tmp/...` on Unix).
