# AVS Gateway — FAQ & Objections

> **Version:** 1.0.0  
> **Status:** Launch-ready  
> **Last updated:** 2025-01-22  
> **Purpose:** Answer the questions users will actually ask. Honest, specific, no hand-waving.

---

## Table of Contents

- [Section 1: Top 10 FAQs](#section-1-top-10-faqs)
- [Section 2: Technical FAQs](#section-2-technical-faqs)
- [Section 3: Objections and Responses](#section-3-objections-and-responses)
- [Section 4: Honest Comparisons](#section-4-honest-comparisons)
- [Section 5: Design Partner FAQ](#section-5-design-partner-faq)

---

## Section 1: Top 10 FAQs

### 1. What is AVS Gateway?

AVS Gateway is a runtime permission layer for AI agents. It intercepts agent actions — tool calls, file writes, API requests, deployments — before they execute, evaluates them against declarative policies, and returns one of four decisions: ALLOW, DENY, REQUIRE_APPROVAL, or QUARANTINE. Every decision produces a cryptographically signed receipt and an immutable audit entry.

```python
from avs_gateway import governed_tool

@governed_tool
async def deploy_to_production(image: str):
    # AVS intercepts this call, evaluates policy, returns a decision
    # Only then does execution proceed
    ...
```

### 2. How is this different from LangSmith / observability tools?

LangSmith traces what your agent *did* — after the fact. It answers "what happened?" AVS decides whether your agent *may* act — before it happens. It answers "should this be allowed?" You can use both: AVS for enforcement, LangSmith for tracing. They are complementary.

### 3. How is this different from Guardrails AI?

Guardrails AI validates outputs — checking that LLM responses conform to structure, type, or content constraints. AVS validates actions — checking whether a tool call, file access, or deployment should be permitted. Guardrails protects against bad outputs; AVS protects against bad actions. Both can be used together.

### 4. How is this different from OPA / policy engines?

OPA is a general-purpose policy engine. AVS is purpose-built for agent actions. OPA evaluates JSON against Rego; AVS evaluates agent actions (tool calls, file access, deployments) against YAML rules with built-in risk scoring, trust decay, and cryptographic receipts. You can use OPA as one of AVS's policy backends if you prefer Rego.

### 5. Does it work with my framework?

Yes. AVS is framework-agnostic. For any Python function, use the `@governed_tool` decorator. For LangChain, use `AVSGovernedTool` as a drop-in replacement. CrewAI, AutoGen, and custom agents can call the AVS API directly. If your agent calls Python functions, AVS can intercept them.

```python
# LangChain
from avs_gateway.langchain import AVSGovernedTool
from langchain.tools import tool as lc_tool

@lc_tool
def delete_database():
    ...

governed = AVSGovernedTool.wrap(delete_database)
```

### 6. Does it require cloud / online access?

No. AVS runs entirely locally. No API keys, no cloud service, no network calls. Policies load from YAML files on disk. Receipts are stored locally. This is intentional: your permission layer should not have a network dependency.

### 7. What license? Can I use it commercially?

Apache 2.0. Yes, you can use it commercially, modify it, embed it in proprietary products, and redistribute it. See the LICENSE file in the repository.

### 8. How mature is it? Is it production-ready?

AVS is alpha software. It has 470+ tests with zero failures, but the API may change, edge cases exist, and documentation is still growing. We recommend starting with non-critical agents or running AVS in `REQUIRE_APPROVAL` mode (where it asks before acting rather than auto-deciding) until you're confident in your policy setup.

### 9. How do I get started? (5-minute path)

```bash
git clone https://github.com/avs-gateway/avs.git
cd avs
pip install -e .
avs demo
```

The demo runs a local policy engine with sample rules and shows you four decisions in action. Then read `docs/QUICKSTART.md` to add `@governed_tool` to your first agent function.

### 10. Where can I get help?

- **GitHub Issues:** Bug reports and feature requests — https://github.com/avs-gateway/avs/issues
- **GitHub Discussions:** Questions, architecture help, show-and-tell — https://github.com/avs-gateway/avs/discussions
- **Discussions preferred for questions** — Issues are for bugs and features only.

---

## Section 2: Technical FAQs

### 11. What decisions can AVS make?

Four outcomes, returned as a `Decision` object:

| Decision | Meaning | Use case |
|----------|---------|----------|
| `ALLOW` | Action permitted | Low-risk, trusted pattern |
| `DENY` | Action blocked | Policy violation, high risk |
| `REQUIRE_APPROVAL` | Human must confirm | Medium risk, unfamiliar pattern |
| `QUARANTINE` | Action isolated for review | Suspicious, needs investigation |

```python
result = await governed_tool.call(args)
if result.decision == Decision.DENY:
    logger.warning(f"Blocked: {result.reason}")
```

### 12. How does the policy engine work?

Policies are declarative YAML files. The engine evaluates rules in priority order and returns the first match. A typical policy file:

```yaml
policies:
  - name: block_destructive_sql
    priority: 1
    match:
      action_type: "database.write"
    decision: DENY
    reason: "Destructive writes require explicit approval"

  - name: allow_trusted_read
    priority: 2
    match:
      action_type: "database.read"
      risk_score: "< 0.3"
      trust_score: "> 0.7"
    decision: ALLOW
```

Rules are evaluated top-down. Priority 1 is checked before priority 2. The first matching rule wins.

### 13. What are receipts?

Every AVS decision produces a receipt: a JSON document containing the action details, the decision, the policy that triggered it, a timestamp, and an Ed25519 cryptographic signature. The signature is produced by a keypair generated on your machine — AVS does not hold your keys.

```json
{
  "receipt_id": "rec_2025-01-22_001",
  "action": "filesystem.write",
  "target": "/etc/passwd",
  "decision": "DENY",
  "policy": "block_sensitive_files",
  "timestamp": "2025-01-22T14:30:00Z",
  "signature": "ed25519:abc123..."
}
```

### 14. How does the audit chain work?

Each receipt's SHA-256 hash is included in the next receipt, forming a linked hash chain. If any receipt is altered, the chain breaks and tampering is detectable. The chain is append-only — receipts are never deleted or modified in place. Store the chain in a write-once location (WORM storage, append-only log) for maximum integrity.

```
Receipt 1: hash = SHA-256(receipt_1_data)
Receipt 2: hash = SHA-256(receipt_2_data + Receipt_1.hash)
Receipt 3: hash = SHA-256(receipt_3_data + Receipt_2.hash)
```

### 15. What is fail-closed design?

If anything goes wrong — policy file is corrupt, engine crashes, signature key unavailable — AVS defaults to DENY. An agent action blocked due to an AVS error is inconvenient. An agent action allowed because of an AVS error could be catastrophic. Fail-closed means errors fail safe.

### 16. Can I add custom policies?

Yes. Two ways:

**YAML:** Add new `.yaml` files to the policies directory. AVS loads them on startup.

**Programmatic:** Register custom policy functions:

```python
from avs_gateway.policies import register_policy

@register_policy("my_custom_check")
def check_business_hours(action, context):
    if not is_business_hours():
        return Decision.REQUIRE_APPROVAL
    return None  # Let other policies decide
```

### 17. Does it slow down my agent?

The policy evaluation adds ~1-5ms per intercepted call for typical rulesets (our benchmarks with 23 rules). Receipt generation and signing add ~2-3ms. For most agent workflows — where tool calls themselves take 100ms-seconds — this is negligible. You can disable receipt generation in development if needed.

### 18. How do I test my policies?

AVS includes a dry-run mode that evaluates actions without executing them:

```python
from avs_gateway.testing import PolicyTester

tester = PolicyTester(policies_dir="./policies")
result = tester.evaluate(action_type="filesystem.delete", target="/important")
assert result.decision == Decision.DENY
```

Run the full test suite: `pytest tests/ -v` (470+ tests, all passing).

### 19. Can AVS be bypassed?

Not if properly integrated. The `@governed_tool` decorator wraps the function at the Python level — calling the function without going through the wrapper requires intentional code modification. For LangChain, `AVSGovernedTool` replaces the tool in the agent's tool list. If an agent has a path to execute actions outside governed tools, that is a deployment issue, not an AVS issue. Defense in depth matters.

### 20. What about async / concurrent agents?

AVS is fully async-native (`async/await`). Each call is evaluated independently, so concurrent agents do not block each other. Receipts are written with atomic operations to prevent corruption under concurrency. Shared state (trust scores, policy caches) uses thread-safe/async-safe data structures.

**Current state:** Async and concurrent execution are fully supported.  
**On the roadmap:** Distributed policy enforcement across multiple agent nodes (for multi-agent swarms).

---

## Section 3: Objections and Responses

### 21. "This is alpha. I'm not trusting my production agents to it."

**Fair.** We wouldn't either.

Run AVS in `REQUIRE_APPROVAL` mode first. This means AVS flags risky actions but asks a human before doing anything. Your agent keeps running, but nothing destructive happens without your say-so. Once you've seen AVS make correct decisions for your workload for a week, switch individual policies to `ALLOW`/`DENY` auto-mode. Start with read-only agents, then graduate to write-capable ones.

### 22. "I can just write my own permission checks."

You can, and many do. The question is whether you want to maintain that code.

A typical DIY permission layer starts with `if action == "delete": raise PermissionError()`. Then you need risk scoring, then policy files, then audit logging, then you need tamper-evident logs, then you need to handle edge cases... We've done that work. AVS gives you 23+ built-in policy types, 8-dimension risk scoring, cryptographic receipts, and an audit chain — all tested, documented, and maintained as a community project.

If your needs are simple, DIY may be fine. If you're building multiple agents or want an audit trail, AVS saves weeks of work.

### 23. "Another dependency to maintain."

AVS has zero runtime dependencies beyond Python standard library + PyYAML. No cloud services, no API keys, no subscription. If we disappeared tomorrow, your installed version keeps working. The codebase is ~3,000 lines of Python — small enough to fork and maintain yourself if needed.

### 24. "My agents are internal-only, I don't need this."

Internal agents often have the broadest access — they read from production databases, write to shared drives, and deploy to internal services. The "internal-only" assumption is exactly why most agent incidents happen inside the firewall. AVS is particularly valuable for internal agents because they touch sensitive systems by design.

### 25. "This adds complexity I don't have time for."

Adding `@governed_tool` to a function takes 30 seconds. The `REQUIRE_APPROVAL` mode means AVS asks before risky actions — it does not change how your agent works, it adds a safety check. Start with one tool, one policy. Complexity scales with your needs, not the other way around.

### 26. "LangChain / Anthropic will build this into their framework."

Maybe. Frameworks tend to add safety features over time. But framework-agnostic permission layers have value regardless: you may switch frameworks, use multiple frameworks, or build custom agents. AVS works with LangChain today, but does not depend on it. If LangChain adds native permissions, you can use both — or migrate. We're not betting against frameworks; we're building something that works across all of them.

### 27. "I already have OPA / authorization. Why do I need AVS?"

If OPA covers your agent actions, you may not need AVS. AVS adds three things OPA does not provide out of the box: (1) agent-action-specific risk scoring with time-weighted trust decay, (2) cryptographically signed receipts with linked hash chains, and (3) framework-native decorators that make integration a one-liner. If you just need policy evaluation, OPA is excellent. If you need agent-specific enforcement with audit trails, AVS fills that gap.

### 28. "How do I know the receipts are actually tamper-evident?"

Verify them yourself:

```python
from avs_gateway.receipts import verify_receipt

# Returns True if signature valid and chain intact
assert verify_receipt(receipt, public_key) is True
```

The Ed25519 signatures use standard cryptography (libsodium). The linked hash chain is the same mechanism used in certificate transparency logs and blockchain structures. The code is open source — audit it, run the tests, verify the math.

### 29. "What if AVS has a bug and blocks legitimate actions?"

Two safeguards: (1) Per-policy bypass — you can disable individual policies without shutting AVS down. (2) Emergency bypass — set `AVS_MODE=permissive` to log-but-not-block, allowing all actions through while keeping the audit trail. Both are documented in `docs/EMERGENCY_PROCEDURES.md`.

```bash
# Emergency: log but do not block
export AVS_MODE=permissive
python my_agent.py
```

### 30. "Who's behind this? Is this a real project or a side project?"

AVS Gateway is an open-source project started by engineers who build production AI agents and got tired of having no permission layer. It is not backed by a venture-funded company. It is a real project with real maintainers, real tests, and a real commitment to keeping it maintained. The best way to judge is to look at the code, run the tests, and check the commit history.

---

## Section 4: Honest Comparisons

### AVS vs. LangSmith

| Question | AVS Gateway | LangSmith |
|----------|-------------|-----------|
| **What it does** | Permission enforcement for agent actions | Tracing and observability for LLM calls |
| **When it acts** | Before execution (intercept) | After execution (trace) |
| **Decisions** | ALLOW, DENY, REQUIRE_APPROVAL, QUARANTINE | N/A (observation only) |
| **Receipts / audit** | Ed25519-signed, tamper-evident receipts | Execution traces, not signed |
| **Integration** | `@governed_tool` decorator, `AVSGovernedTool` | `@traceable` decorator |
| **Framework support** | Any Python function / any framework | LangChain-focused |
| **Self-hosted** | Yes, fully local | Cloud service (self-hosted available in enterprise) |
| **Best for** | Enforcing permission boundaries on agent actions | Debugging and monitoring LLM application performance |
| **Can use together?** | Yes — AVS for enforcement, LangSmith for tracing | Yes — complementary |

### AVS vs. Guardrails AI

| Question | AVS Gateway | Guardrails AI |
|----------|-------------|---------------|
| **What it validates** | Agent actions (tool calls, file access, deployments) | LLM outputs (structure, type, content) |
| **When it acts** | Before tool execution | After LLM response generation |
| **Input** | Tool call + context + risk profile | LLM output text |
| **Decisions** | ALLOW, DENY, REQUIRE_APPROVAL, QUARANTINE | Pass / Fail / Retry |
| **Focus** | Action permission | Output quality |
| **Best for** | Stopping dangerous agent actions | Ensuring LLM responses are well-formed |
| **Can use together?** | Yes — AVS for actions, Guardrails for outputs | Yes — complementary |

### AVS vs. OPA (Open Policy Agent)

| Question | AVS Gateway | OPA |
|----------|-------------|-----|
| **Scope** | Purpose-built for AI agent actions | General-purpose policy engine |
| **Policy language** | YAML (declarative, readable) | Rego (purpose-built, powerful) |
| **Agent-specific features** | Risk scoring, trust decay, framework decorators | None (generic) |
| **Receipts / audit** | Built-in Ed25519-signed receipts | Generic decision logs |
| **Deployment** | Python library, pip install | Sidecar / service |
| **Best for** | Agent permission with audit trails | General microservice authorization |
| **Can use together?** | Yes — OPA as a policy backend for AVS | Yes — AVS can call OPA for evaluation |

### AVS vs. Lakera

| Question | AVS Gateway | Lakera |
|----------|-------------|--------|
| **What it does** | Runtime permission layer for agent actions | AI security platform (prompt injection, PII, etc.) |
| **Focus** | Action interception and policy enforcement | Input/output security scanning |
| **Deployment** | Self-hosted, open source | Cloud API service |
| **Receipts** | Cryptographically signed, local | Cloud-dashboard based |
| **Best for** | Controlling what agents can *do* | Protecting against prompt attacks and data leakage |
| **Can use together?** | Yes — Lakera for input security, AVS for action control | Yes — layers of defense |

### AVS vs. E2B

| Question | AVS Gateway | E2B |
|----------|-------------|-----|
| **What it does** | Permission layer for agent actions | Sandboxed execution environment for AI agents |
| **Approach** | Intercept and decide (allow/deny) | Isolate in sandbox (let it run, but contained) |
| **Threat model** | Prevent bad actions from executing | Contain damage from any action |
| **Deployment** | Library integrated with agent code | Cloud sandbox service |
| **Best for** | Fine-grained permission control per action | Running untrusted code safely |
| **Can use together?** | Yes — AVS decides, E2B contains | Yes — defense in depth |

---

## Section 5: Design Partner FAQ

### 31. What does being a design partner mean?

You use AVS with your agents, give us honest feedback on what works and what doesn't, and help shape the roadmap. You're not a customer — you're a collaborator. We build what you actually need, not what we think you need.

### 32. What's the time commitment?

~30 minutes per week for 4 weeks. A 15-minute kickoff call, weekly async check-ins (GitHub Discussions or Slack), and a 30-minute retrospective at the end. No mandatory meetings beyond the kickoff.

### 33. What do I get?

- Early access to new features (you see them before public release)
- Direct access to maintainers (fast responses, architecture discussions)
- Influence on the roadmap (your use case gets priority)
- Public recognition as a design partner (optional, only if you want)
- A working permission layer for your agents

### 34. What do you need from me?

- Your use case: what kind of agents you're building, what actions they take
- Honest feedback: what's confusing, what's missing, what doesn't work
- Bug reports when you find them
- A testimonial at the end (optional, but appreciated)

### 35. Is there a cost?

No. AVS is Apache 2.0 — free for everyone. Design partnership is free. There is no paid tier, no enterprise license, no upsell. We're building an open-source project, not a sales funnel.

---

## Quick Reference Card

| I want to... | See this... |
|-------------|-------------|
| Get started in 5 minutes | `docs/QUICKSTART.md` |
| Add AVS to my LangChain agent | `docs/LANGCHAIN_INTEGRATION.md` |
| Write custom policies | `docs/POLICIES.md` |
| Understand receipts and audit | `docs/RECEIPTS.md` |
| Run in REQUIRE_APPROVAL mode | `docs/SAFE_DEPLOYMENT.md` |
| Report a bug | GitHub Issues |
| Ask a question | GitHub Discussions |
| Become a design partner | Open a Discussion with "Design Partner" in the title |

---

*This document is a living file. It will be updated based on actual questions received post-launch. If you see a question that's not answered here, open a Discussion and we'll add it.*
