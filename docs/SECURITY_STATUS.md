# AVS Gateway Security Status

**Version:** v0.4.0-alpha  
**Date:** 2026-06-25  
**Status:** ALPHA — NOT PRODUCTION HARDENED

---

## Summary

AVS Gateway v0.4.0-alpha is an early-stage runtime permission layer for AI agents. It is NOT production-hardened security infrastructure. This document lists known vulnerabilities, their severity, and planned fixes. We publish this because transparency about security limitations is more valuable than claiming protections that don't exist.

---

## Known Vulnerabilities

| ID | Vulnerability | Severity | Status | Target Fix |
|----|--------------|----------|--------|------------|
| SEC-001 | DNS rebinding in HTTPSandbox — DNS resolves to safe IP during validation but may resolve to private IP (169.254.169.254, localhost) during actual HTTP request | CRITICAL | Open | v0.4.1-alpha |
| SEC-002 | TOCTOU race in FileSandbox — symlink can be swapped between path.resolve() boundary check and actual file operation | CRITICAL | Open | v0.4.1-alpha |
| SEC-003 | Trust poisoning — agent can escalate trust through 15-20 benign actions then execute risky actions with elevated trust | HIGH | Open | v0.4.1-alpha |
| SEC-004 | No HITL timeout — pending approvals never expire, causing indefinite agent blockage | HIGH | Open | v0.4.1-alpha |
| SEC-005 | Policy conflicts resolved silently — first matching rule wins with no logging when multiple rules match | MEDIUM | Open | v0.4.2 |
| SEC-006 | SQLite backend not production-scale — 1,000-5,000 writes/sec limit | MEDIUM | Accepted (see ROADMAP) | v0.5.0 |
| SEC-007 | Prompt injection can bypass policy engine — compromised LLM generates tool calls that look legitimate | HIGH | Researching | v0.4.3 |

---

## Attack Scenarios

### SEC-001: DNS Rebinding Attack

**Attack chain:**

1. Attacker controls a domain (e.g., `evil.com`) with a DNS server configured to return TTL=0.
2. Attacker instructs the agent to make an HTTP request to `http://evil.com/metadata`.
3. During validation, `evil.com` resolves to a public IP (e.g., `8.8.8.8`). The HTTPSandbox permits the request.
4. The HTTP client issues the actual request. Due to TTL=0, it re-resolves `evil.com`.
5. The attacker's DNS server now returns `169.254.169.254` (AWS IMDS endpoint).
6. The HTTP client sends the request to `http://169.254.169.254/latest/meta-data/iam/security-credentials/`.
7. AWS returns temporary IAM credentials.
8. Attacker exfiltrates credentials and gains access to cloud resources.

**Why it works:** The sandbox validates the hostname at DNS resolution time, but the HTTP client may re-resolve before the actual TCP connection. The two resolutions are not guaranteed to return the same IP.

**Fix (planned for v0.4.1-alpha):** DNS pinning — resolve once, cache the IP, and connect to the cached IP directly, bypassing re-resolution. Validate the pinned IP against the blocklist at connection time.

---

### SEC-002: Symlink Race (TOCTOU) in FileSandbox

**Attack chain:**

1. Agent requests a file read at a path inside the sandbox, e.g., `/sandbox/data/file.txt`.
2. FileSandbox calls `path.resolve()` to canonicalize the path.
3. FileSandbox calls `check_boundary()` to verify the resolved path is within the sandbox root. This passes.
4. **Attack window opens.** Attacker (or another process) swaps `/sandbox/data/file.txt` from a regular file to a symlink pointing to `/etc/shadow`.
5. FileSandbox calls `open()` on the original path. The OS follows the new symlink.
6. FileSandbox reads `/etc/shadow` — a file outside the sandbox boundary.

**Why it works:** The boundary check and the file open are not atomic. The filesystem can change between them.

**Fix (planned for v0.4.1-alpha):** Open the file descriptor first with `O_NOFOLLOW`, then verify the opened fd's path is within the sandbox boundary using `realpath()` on `/proc/self/fd/<fd>`.

---

### SEC-003: Trust Poisoning / Slow-Burn Escalation

**Attack chain:**

1. Agent starts at `UNVERIFIED` trust tier. All risky actions require approval.
2. Agent performs 15 benign `file_read` operations within 60 seconds.
3. Trust memory scores these positively: frequent access, short time window, consistent action type.
4. Trust tier escalates from `UNVERIFIED` → `VERIFIED` → `TRUSTED`.
5. At `TRUSTED` tier, `database_write` actions are auto-approved (per policy defaults).
6. Agent executes `database_write` with a malicious payload: `INSERT INTO secrets SELECT * FROM credentials`.
7. The risky write is auto-approved due to elevated trust. Data is exfiltrated.

**Why it works:** Trust scoring rewards frequency and recency without evaluating the semantic intent of the action sequence. An attacker can "farm" trust with harmless actions, then exploit the elevated tier.

**Fix (planned for v0.4.1-alpha):** Require action-type diversity for tier escalation (not just volume), add cooling-off periods between tier changes, and restrict auto-approval to a smaller subset of actions even at `TRUSTED`.

---

### SEC-004: HITL Approval Timeout Denial-of-Service

**Attack chain:**

1. Agent submits an action requiring human approval (e.g., `database_write`).
2. The action enters `PENDING` state. An approval request is sent (console or webhook).
3. The human reviewer does not respond. No timeout is configured.
4. The action remains `PENDING` indefinitely. The agent cannot proceed past this action.
5. If the agent is running a sequential workflow, the entire pipeline blocks.
6. If multiple actions enter `PENDING`, the queue grows without bound.
7. Alert fatigue sets in. Reviewers ignore notifications. The system is effectively down.

**Why it works:** The approval system has no `max_pending_duration`. There is no automatic escalation, no cancellation, and no queue depth limit.

**Fix (planned for v0.4.1-alpha):** Add a configurable timeout (default: 300 seconds) after which `PENDING` actions auto-cancel with `DENY`. Add a maximum queue depth. Add escalation hooks (e.g., secondary reviewer) after timeout.

---

### SEC-007: Prompt Injection Policy Bypass

**Attack chain:**

1. Attacker injects a malicious prompt into the agent's context (e.g., via user input, document content, or tool output).
2. The compromised LLM generates a tool call that appears legitimate: tool=`file_read`, path=`/app/logs/access.log`.
3. The heuristic risk scorer flags this as LOW risk (file_read is common, path is within allowed patterns).
4. The policy engine allows the action because the tool call structure matches a benign pattern.
5. The tool call is actually exfiltrating data — the path contains encoded sensitive data, or the LLM will chain this with subsequent calls.
6. The policy engine never sees the attacker's original prompt. It only sees the generated tool call, which looks fine.

**Why it works:** The policy engine evaluates tool call syntax, not LLM intent. A compromised LLM can generate syntactically valid calls that serve malicious purposes.

**Fix status:** Under research for v0.4.3. Candidates include content provenance tagging (tracing which prompt segments influenced tool call generation), out-of-band intent verification, and anomaly detection on tool call sequences.

---

## What IS Protected

The following protections are implemented and tested. They work as described.

- **Path traversal attacks** (`../etc/passwd`) — blocked by canonicalization (`path.resolve()` followed by prefix check).
- **Absolute path escapes** (`/etc/shadow` from a relative sandbox) — blocked by sandbox boundary check.
- **Direct IP literal SSRF** (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`) — blocked by IP blocklist checked before connection.
- **Credential headers in HTTP requests** (`Authorization`, `Cookie`, `X-Api-Key`) — stripped by the HTTP sandbox before the request is sent.
- **HTTP redirects** — blocked (`allow_redirects=False`). Redirect responses are not followed.
- **Large response body DoS** — capped at 100KB. Responses exceeding the limit are truncated or rejected.
- **Cloud metadata endpoints** (`169.254.169.254`) — blocked by hostname denylist (in addition to IP blocklist).
- **Replay attacks on approved actions** — blocked by execute-once enforcement. A receipt with a given `request_hash` can only be executed once.
- **Receipt tampering** — detected by SHA-256 hash verification. Any modification to receipt fields invalidates the hash.
- **Receipt forgery** — detected by Ed25519 signature verification. Receipts are signed at creation; verification fails if the private key does not match.
- **Receipt chain breaks** — detected by `previous_receipt_hash` verification. A gap or alteration in the sequence is detected when chaining.

---

## What is NOT Protected

The following are known gaps. Do not rely on AVS Gateway for these threats.

- **DNS rebinding attacks** (SEC-001) — an attacker can change DNS resolution between validation and connection.
- **Symlink race conditions** (SEC-002) — an attacker can swap a file for a symlink between the boundary check and the open operation.
- **Prompt injection policy bypass** (SEC-007) — a compromised LLM can generate tool calls that appear legitimate to the policy engine.
- **Slow-burn trust escalation** (SEC-003) — an attacker can farm trust with benign actions, then exploit elevated privileges.
- **Multi-agent trust propagation attacks** — trust scores are not shared across agents, but a shared backend could allow cross-agent trust manipulation (untested).
- **Advanced persistent threat scenarios** — no detection for long-term, low-volume compromise patterns.
- **Physical infrastructure compromise** — if the host is compromised, all bets are off. Receipt keys, SQLite database, and policy files are on disk.

---

## Reporting

If you find a security issue not listed here, email: **security@avsgateway.dev**

We will acknowledge receipt within 48 hours and provide a timeline for assessment within 7 days.
