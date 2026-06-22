# Competitive Intelligence Brief: Agent Governance & Receipt Landscape

**Research Date:** 2026-07-09
**AVS Gateway Context:** v0.3.4 "Runtime Permission Layer for AI Agents"  intercepts agent actions, evaluates policy/risk/trust, produces cryptographic receipts. Next milestone: ASR-1 (Action Standard Receipt) + Agent Identity.

---

## Executive Summary

The agent governance market is fragmenting into three distinct layers: **observability** (post-hoc tracing), **runtime enforcement** (action interception), and **evidence** (cryptographic receipts/attestation). Most competitors occupy only one layer. No competitor has shipped a complete "intercept-evaluate-receipt" pipeline equivalent to AVS Gateway. The closest threats are: **ICME Preflight** (cryptographic proofs but no runtime interception), **DeepInspect** (network-layer enforcement with signed audits), and **PointGuard AI** (agent identity + runtime controls for MCP). The emerging **Agent Action Receipt (AAR)** spec on GitHub is the only public attempt at a cross-platform receipt format  it has 4 stars and 1 contributor, suggesting the standardization race is wide open.

---

## Q1: LangSmith / Langfuse  Are They Building ReceiptsWARNING

### LangSmith (by LangChain)

| Field | Detail |
|-------|--------|
| **Name** | LangSmith |
| **Status** | Shipped |
| **What they do** | Full observability platform for LLM applications. End-to-end tracing of LLM calls, tool invocations, reasoning steps. Custom dashboards, evaluation, annotation queues, human-in-the-loop (LangGraph interrupt primitive). EU AI Act compliance support (tracing for Articles 9, 12, 13, 14). |
| **Receipt/Identity capability** | **No receipts.** Traces capture what happened (inputs, outputs, timestamps, token usage) but are application-plane logs, not cryptographically signed. Tracing is asynchronous SDK callbacks  if the app skips the SDK call, no trace exists. No agent identity system. No action attestation. No policy decision evidence. |
| **Threat to AVS** | **Low**  LangSmith is an observability/debugging tool, not an enforcement layer. They trace; AVS intercepts. Complementary rather than competitive. However, their EU AI Act marketing may confuse buyers into thinking tracing = compliance. |
| **Source** | https://www.langchain.com/blog/langsmith-langchain-oss-eu-ai-act, https://www.langchain.com/langsmith/observability |

**Key insight:** LangSmith's traces are the gold standard for debugging but produce no tamper-evident evidence. A DeepInspect comparison notes: "Langfuse records [the violation] but the data has already left the model." The enforcement-vs-observation gap is structural.

---

### Langfuse

| Field | Detail |
|-------|--------|
| **Name** | Langfuse |
| **Status** | Shipped (Open Source, MIT) |
| **What they do** | Open-source LLM engineering platform. Traces, prompt management, evaluations, datasets, LLM playground. Self-hostable in minutes. OpenTelemetry-based. Integrates with 50+ frameworks. |
| **Receipt/Identity capability** | **No receipts.** Same architectural limitation as LangSmith  traces are post-hoc observability records, not cryptographically signed action receipts. No policy enforcement. No runtime interception. No agent identity. An arXiv paper on "Governance-Aware Agent Telemetry" explicitly calls out Langfuse as treating "governance as a downstream analytics concern, not a real-time enforcement target." |
| **Threat to AVS** | **Low**  Langfuse is the open-source observability leader. It records; AVS enforces. No receipt format, no identity, no attestation. |
| **Source** | https://github.com/langfuse/langfuse, https://langfuse.com/docs/observability/overview, arXiv:2604.05119v1 |

**Key insight:** The GAAT (Governance-Aware Agent Telemetry) paper from April 2026 positions Langfuse/OpenTelemetry as baseline telemetry that "captures dependencies without enforcing anything"  an "observe-but-do-not-act gap."

---

## Q2: Guardrails AI  Runtime Enforcement or Just ValidationWARNING

### Guardrails AI (the company)

| Field | Detail |
|-------|--------|
| **Name** | Guardrails AI |
| **Status** | Shipped |
| **What they do** | Developer-defined guardrails with runtime execution gating and post-action auditing. Uses Python hooks (`BeforeToolCallEvent`) that can cancel tool execution. Supports validation of inputs, outputs, and tool call parameters. |
| **Receipt/Identity capability** | **Partial receipts.** Can produce evidence of blocked actions via execution hooks. But enforcement is application-plane  hooks run inside the agent's process. No cryptographic signing. No agent identity system. No standardized receipt format. |
| **Threat to AVS** | **Low-Medium**  They have execution hooks (which is enforcement, not just validation), but the enforcement is in-process and co-tenanted with the agent. They block at the framework layer; AVS blocks at the permission/runtime layer. Their receipt capability is minimal  log entries, not signed artifacts. |
| **Source** | https://www.guardrailsai.com/, https://docs.guardrailsai.com/ |

**Key distinction:** Guardrails AI does have tool-call blocking via `BeforeToolCallEvent` hooks. This is actual runtime enforcement, not just output validation. However, it runs in the same process as the agent (ArmoSec's "Rung 4"  application-plane), so a compromised agent can bypass it.

---

### NVIDIA NeMo Guardrails

| Field | Detail |
|-------|--------|
| **Name** | NVIDIA NeMo Guardrails |
| **Status** | Shipped (Open Source, Apache 2.0) |
| **What they do** | Programmable guardrails using Colang (custom modeling language). Acts as a proxy between user and LLM. Supports topical rails (dialogue control), execution rails (custom actions), input/output moderation. Can invoke custom Python actions at runtime. |
| **Receipt/Identity capability** | **No receipts.** No cryptographic signing. No agent identity. Execution rails can call custom actions but the framework itself produces no attestation or signed evidence. Palo Alto Networks integrates it with their "AI Runtime Security API Intercept" for network-layer enforcement. |
| **Threat to AVS** | **Low**  NeMo Guardrails is a content/dialogue moderation framework, not an action-permission layer. It can block at the conversation level but has no concept of per-action policy evaluation or cryptographic receipts. |
| **Source** | https://docs.nvidia.com/nemo/guardrails/0.19.0/architecture/README.html, arXiv:2310.10501 |

---

## Q3: CrewAI / AutoGen  Do They Have Governance LayersWARNING

### CrewAI

| Field | Detail |
|-------|--------|
| **Name** | CrewAI |
| **Status** | Shipped (Enterprise governance features added 2025-2026) |
| **What they do** | Multi-agent orchestration framework. Enterprise tier now includes RBAC, structured audit logs, FedRAMP pursuit, built-in monitoring. Open-source core. |
| **Receipt/Identity capability** | **Audit logs but no receipts.** CrewAI produces structured audit logs capturing agent decisions, tool invocations, data access events. However, there is no built-in tool permission gating  open GitHub issue #6221 explicitly requests "deterministic tool permission gating" because "CrewAI agents have unrestricted access to any tool registered with them." Third-party Kevros Governance SDK adds pre-execution action verification and signed evidence records (using post-quantum ML-DSA-87). |
| **Threat to AVS** | **Low-Medium**  CrewAI is a framework, not an enforcement layer. Their governance features are enterprise compliance add-ons (logging, RBAC), not runtime permission enforcement. The Kevros SDK is the closest to AVS's model but is a third-party add-on, not core CrewAI. |
| **Source** | https://github.com/crewAIInc/crewAI/issues/6221, https://ienable.ai/blog/crewai-governance-vs-ienable-cross-platform-agent-governance-2026.html, https://github.com/ndl-systems/kevros-governance-sdk |

**Key insight:** CrewAI's governance gap is openly acknowledged. Issue #6221 states: "CrewAI agents have unrestricted access to any tool registered with them. There's no mechanism to say 'Agent A may use the Filesystem tool but not the Shell tool.'" This is exactly the gap AVS fills.

---

### AutoGen (Microsoft)

| Field | Detail |
|-------|--------|
| **Name** | AutoGen (Microsoft) |
| **Status** | Shipped |
| **What they do** | Multi-agent conversation framework. Supports human-in-the-loop as first-class primitive. Docker sandboxing for code execution. Bounded environments. Subagents can be spun up with human-off-the-loop or human-in-the-loop. |
| **Receipt/Identity capability** | **No receipts. No permission system.** AutoGen has human-in-the-loop capabilities but no deterministic tool permission model, no action attestation, no audit trail with cryptographic integrity. Researchers measuring AutoGen autonomy noted inter-rater agreement on "observability" was only k=0.47  meaning even experts couldn't consistently assess what agents logged vs. what was actionable. |
| **Threat to AVS** | **Low**  AutoGen is a conversation framework. It has no governance layer, no identity system, and no receipt infrastructure. |
| **Source** | arXiv:2502.15212v1 (Measuring AI Agent Autonomy), https://github.com/microsoft/autogen |

---

## Q4: OpenAI / Anthropic  Agent Safety Infrastructure

### OpenAI

| Field | Detail |
|-------|--------|
| **Name** | OpenAI |
| **Status** | Nothing Found for agent-specific governance |
| **What they do** | Provides moderation API endpoint (content classification for hate, violence, sexual content, self-harm). Agent builder platform (AgentKit) with optional guardrail modules. No built-in protections documented for agentic tool calling. |
| **Receipt/Identity capability** | **None.** No tool call receipts. No agent identity system. No action attestation. No runtime enforcement for agent actions. The moderation API is a content classifier, not an action governance layer. |
| **Threat to AVS** | **None**  OpenAI provides no agent governance infrastructure. They explicitly delegate guardrails to users. |
| **Source** | https://platform.openai.com/docs/guides/moderation, 2025 MIT AI Agent Index |

---

### Anthropic

| Field | Detail |
|-------|--------|
| **Name** | Anthropic |
| **Status** | Constitutional AI shipped (training-time); No runtime governance SDK |
| **What they do** | Constitutional AI: model is trained to evaluate/revise outputs against written principles. MCP (Model Context Protocol): open standard for tool-application integration. Claude Code with sandboxing. Agent-specific system cards for tool use risks. |
| **Receipt/Identity capability** | **None at runtime.** Constitutional AI is training-time alignment, not runtime enforcement. MCP is a protocol for tool access, not a governance or enforcement layer. No action receipts. No agent identity system. No policy engine for tool calls. No attestation of individual actions. |
| **Threat to AVS** | **None**  Anthropic's safety work is model-layer, not infrastructure-layer. They make the model less likely to generate harmful plans but provide no runtime controls for when it does. MCP standardizes tool access but doesn't govern it. |
| **Source** | https://www.anthropic.com/constitution, 2025 MIT AI Agent Index, Stanford TTLF Working Paper |

**Key insight:** Stanford's TTLF Working Paper notes: "Constitutional AI can reduce misalignment before the agent reaches the tool use stage... This does not solve runtime control, but it can make the model less likely to generate action plans that require unlawful or harmful tool use." Anthropic's safety is all upstream; AVS's is all downstream.

---

## Q5: Emerging Agent Security Startups

### PointGuard AI

| Field | Detail |
|-------|--------|
| **Name** | PointGuard AI |
| **Status** | Shipped |
| **What they do** | Agent Control Plane + MCP Security Gateway. Gives every agent a "verifiable cryptographic identity." Validates every action before execution at "sub-millisecond latency." Zero-trust authorization, granular tool permissions, sandboxing, kill switches. Runtime governance for MCP-driven workflows. |
| **Receipt/Identity capability** | **Yes  agent identity + runtime validation.** This is the closest competitor to AVS. They have: (1) verifiable cryptographic identity per agent, (2) action validation before execution, (3) runtime controls at the MCP layer. No explicit mention of signed receipts or action attestation format. |
| **Threat to AVS** | **High**  PointGuard is solving the same problem space: agent identity + runtime action governance + MCP security. Their positioning as "Agent Control Plane" overlaps significantly with AVS's "Runtime Permission Layer." Key differentiator: AVS has cryptographic receipts (ASR-1); PointGuard does not appear to have a receipt format. |
| **Source** | https://www.pointguardai.com/, https://www.pointguardai.com/agentic-ai-security |

---

### Singulr AI (Agent Pulse)

| Field | Detail |
|-------|--------|
| **Name** | Singulr AI (Agent Pulse) |
| **Status** | Shipped (Agent Pulse launched March 2026) |
| **What they do** | Unified AI Control Plane extending to autonomous agents and MCP servers. Four capabilities: agent discovery, Agent Risk Intelligence (AI red-teaming), Agent Governance (policy definition/enforcement), Agent Runtime Controls (real-time blocking of unauthorized access, prompt injection, data leakage). Integrates with CrewAI, LangGraph, n8n, Copilot Studio, Bedrock, etc. |
| **Receipt/Identity capability** | **Runtime enforcement + tamper-evident evidence.** "Audit & Tamper-Evident Evidence" is listed as a platform capability: "longitudinal, tamper-evident control performance records for regulators, auditors, and the board." Agent identity is implicit through discovery and topology mapping. No explicit standardized receipt format published. |
| **Threat to AVS** | **High**  Singulr is the most well-funded and comprehensive agent governance platform. They have runtime enforcement, tamper-evident audit, agent discovery, and MCP integration. Gartner-recognized. Their weakness vs. AVS: no standardized action receipt format, and their enforcement appears to be platform-centralized rather than cryptographically verifiable per-action. |
| **Source** | https://singulr.ai/, https://www.businesswire.com/news/home/20260309938690/en/, https://vmblog.com/news/singulr-ai-targets-governance-gap/ |

---

### ICME Labs (Preflight)

| Field | Detail |
|-------|--------|
| **Name** | ICME Labs  Preflight |
| **Status** | Shipped (API available) |
| **What they do** | Replaces model-based guardrails with formal verification. Every action gets a cryptographic proof verifiable in under a second. SAT = allowed, UNSAT = blocked. SMT-LIB solver-based. Policies written in plain English, compiled to formal logic. |
| **Receipt/Identity capability** | **Yes  cryptographic receipts.** Every decision produces "a cryptographic proof  tamper-proof, independently verifiable, shareable with any third party." This is a genuine receipt. However, it's a proof-of-policy-evaluation, not a proof-of-action-execution. No agent identity system. No action attestation linking proof to a specific agent action. |
| **Threat to AVS** | **Medium**  ICME is solving the guardrail-verification problem with cryptography, which is adjacent to AVS's receipt problem. Their receipts prove "the policy was evaluated correctly" not "this specific action was taken by this specific agent." No identity, no action binding. Their approach (SMT solvers) is also heavy for real-time agent workflows. |
| **Source** | https://docs.icme.io/, https://api.icme.io/v1/verifyPaid |

---

### DeepInspect

| Field | Detail |
|-------|--------|
| **Name** | DeepInspect |
| **Status** | Shipped |
| **What they do** | Runs BEFORE the request reaches the LLM. Policy decision blocks, rewrites, or passes based on identity, classification, and route. Audit record is "independent of the application's logging path and cryptographically signed." Lives at the network layer, outside the application's control plane. |
| **Receipt/Identity capability** | **Yes  cryptographically signed audit records.** "The audit record is independent of the application's logging path and cryptographically signed. The application cannot bypass the audit record by skipping a SDK call because the audit lives at the network layer." This is genuine runtime enforcement + signed evidence. |
| **Threat to AVS** | **Medium-High**  DeepInspect is a network-layer enforcement point with signed audits  structurally similar to AVS's interception model. Key differences: DeepInspect focuses on prompt/LLM-request mediation; AVS focuses on action/tool-call mediation. DeepInspect's receipts are audit records, not standardized action receipts. |
| **Source** | https://www.deepinspect.ai/blog/deepinspect-vs-langfuse |

---

### Pipelock

| Field | Detail |
|-------|--------|
| **Name** | Pipelock |
| **Status** | Shipped (Open Source) |
| **What they do** | Open-source AI agent firewall. Sits between agents and the network. Enforces: domain allowlists, DLP scanning, MCP tool policy, SSRF protection, prompt injection detection, rate limiting, human-in-the-loop, kill switch. |
| **Receipt/Identity capability** | **Yes  signed receipts + hash-chained audit logs.** "Flight recorder: hash-chained, tamper-evident JSONL audit log with Ed25519 signed checkpoints." Each action gets a signed receipt with "policy hash that was active at the time, the verdict, and the transport surface." Also: signed assessment reports, mediation envelope signing. |
| **Threat to AVS** | **Medium**  Pipelock is the closest open-source competitor to AVS. They have: network-layer enforcement, signed receipts (Ed25519), hash-chained audit logs, tamper-evident chains, MCP tool policy. Key differences: Pipelock is a network firewall; AVS is a permission layer. Pipelock's receipts are infrastructure-audit artifacts, not standardized cross-platform action receipts. |
| **Source** | https://pipelab.org/learn/ai-agent-compliance/, https://github.com/pipelab/pipelock |

---

### Aim Security (acquired by Cato Networks)

| Field | Detail |
|-------|--------|
| **Name** | Aim Security |
| **Status** | Acquired by Cato Networks (Sept 2025, ~$350M) |
| **What they do** | Enterprise AI security platform. AI Firewall, AI Security Posture Management (AI-SPM), Agentic Security. Secures employee use of public AI, private AI applications, and AI development lifecycles. Discovered "EchoLeak" zero-click vulnerability in Microsoft 365 Copilot. |
| **Receipt/Identity capability** | **No receipts.** Their focus is on DLP, prompt security, and AI-SPM. No action attestation, no agent identity for tool calls, no cryptographic receipts. Being integrated into Cato's SASE platform. |
| **Threat to AVS** | **Low**  Aim Security is an enterprise AI security company (DLP, firewall, posture management), not an agent governance/receipt platform. Their acquisition by Cato signals the cybersecurity incumbents are entering AI security but not specifically agent receipts. |
| **Source** | https://cyberscoop.com/cato-networks-acquires-ai-security-startup-aim-security/ |

---

### AIM Intelligence

| Field | Detail |
|-------|--------|
| **Name** | AIM Intelligence |
| **Status** | Shipped |
| **What they do** | AI security platform with two products: Stinger (automated AI vulnerability discovery/red teaming) and Starfort (real-time AI guardrails). Omni-modal support (text, image, audio, video, physical AI). Proxy-level blocking of malicious prompts, real-time PII masking. |
| **Receipt/Identity capability** | **No receipts.** Focus on red teaming + guardrails. No action attestation, no agent identity, no standardized receipt format. |
| **Threat to AVS** | **Low**  AIM Intelligence is a security testing + guardrail company, not a governance/receipt infrastructure provider. |
| **Source** | https://aim-intelligence.com/ |

---

### AgentOps (the company)

| Field | Detail |
|-------|--------|
| **Name** | AgentOps |
| **Status** | Shipped |
| **What they do** | Developer platform for building AI agents. Session replay, time-travel debugging, cost tracking, multi-agent interaction visualization. Integrates with OpenAI, CrewAI, AutoGen, 400+ LLMs. |
| **Receipt/Identity capability** | **No receipts.** Pure observability/debugging. Full data trail of logs and errors but no cryptographic signing, no policy enforcement, no action attestation. |
| **Threat to AVS** | **Low**  AgentOps is a developer tool. No enforcement, no receipts, no identity. |
| **Source** | https://www.agentops.ai/ |

---

## Q6: OPA (Open Policy Agent) + AI

### OPA for Agent Governance

| Field | Detail |
|-------|--------|
| **Name** | Open Policy Agent (OPA) + AI integrations |
| **Status** | Shipped (OPA); Multiple integrations emerging |
| **What they do** | OPA is the CNCF-graduated policy engine (Rego language). Multiple projects now integrate OPA with agent frameworks for runtime policy enforcement. Pattern: agent decides to call a tool -> OPA evaluates policy -> allow/deny -> tool executes or rejected. |
| **Receipt/Identity capability** | **Policy decisions but no receipts.** OPA produces decision logs (allow/deny with input/context), which serve as audit evidence. But no standardized receipt format, no cryptographic signing by default, no agent identity binding. |
| **Threat to AVS** | **Low-Medium**  OPA is a policy engine, not a receipt/identity system. It could become a *component* of AVS (policy evaluation backend) but doesn't solve the receipt/attestation problem. The GAAT paper (arXiv:2604.05119v1) proposes OPA-compatible rules for agent governance, achieving 98.3% violation prevention rate. |
| **Source** | https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-4/, https://gokhan-gokalp.com/runtime-governance-for-ai-agents-policy-as-code-with-opa/, arXiv:2604.05119v1 |

**Key integrations found:**
1. **Sakura Sky blog series**  Full architecture: SPIFFE for identity, OPA for policy, Audit/Attestation for accountability
2. **Gokhan Gokalp's implementation**  OPA middleware for Microsoft Agent Framework with tool-level RBAC
3. **GAAT paper**  Governance-Aware Agent Telemetry using OPA-compatible rules, 98.3% VPR, sub-200ms latency
4. **hoop.dev**  "AI Governance Made Simple with OPA" guide
5. **Codilime**  "Why Open Policy Agent is the Missing Guardrail for Your AI Agents"

---

## Q7: Has Anyone Proposed an "Action Receipt" FormatWARNING

### Agent Action Receipt (AAR) v1.0

| Field | Detail |
|-------|--------|
| **Name** | Agent Action Receipt (AAR) Specification |
| **Status** | Proposed (GitHub, March 2026) |
| **What they do** | RFC-style spec for a "lightweight, cryptographically signed receipt format for AI agent actions." Top-level fields: receiptId, agent (identity), principal (on whose behalf), action (type/target/method/result), scope (authorization), inputHash, outputHash, timestamp, cost, signature (Ed25519), metadata. Includes evidenceRef field for external proof artifacts. |
| **Receipt/Identity capability** | **Yes  this IS a receipt format.** Ed25519 signatures. Canonical JSON serialization (JCS). SHA-256 content hashing. Evidence references for layered trust. Designed for cross-platform auditing and machine verification. Complements x402 payment standard. |
| **Threat to AVS** | **Medium**  This is the closest thing to ASR-1 in the wild. Only 4 stars, 1 contributor, 1 fork. The spec is well-designed but has no adoption. AVS could: (a) adopt/extend AAR, (b) compete with ASR-1 as a more mature alternative, or (c) ignore it and risk AAR gaining traction first. |
| **Source** | https://github.com/Cyberweasel777/agent-action-receipt-spec |

**Key fields in AAR v1.0:**
```json
{
  "receiptId": "uuid",
  "agent": { "identity": "..." },
  "principal": { "identity": "..." },
  "action": { "type": "...", "target": "...", "method": "...", "result": "..." },
  "scope": { "authorization": "..." },
  "inputHash": { "alg": "sha256", "digest": "..." },
  "outputHash": { "alg": "sha256", "digest": "..." },
  "timestamp": "2026-03-05T00:00:00Z",
  "cost": { "amount": "...", "currency": "..." },
  "signature": { "alg": "Ed25519", "kid": "...", "sig": "..." },
  "evidenceRef": [...]
}
```

Also includes a **Session Continuity Certificate (SCC)** extension for multi-step workflow attestation.

---

### Academic Papers on Agent Governance & Receipts

| Paper | Key Finding |
|-------|-------------|
| **"Governance-Aware Agent Telemetry for Closed-Loop Enforcement"** (arXiv:2604.05119v1, Apr 2026) | GAAT architecture: Governance Telemetry Schema extending OpenTelemetry, real-time OPA-compatible policy engine, Governance Enforcement Bus with graduated interventions, Trusted Telemetry Plane with cryptographic provenance. 98.3% violation prevention rate. Explicitly calls out Langfuse/OpenTelemetry as "observe-but-do-not-act." |
| **"Governance-as-a-Service: A Multi-Agent Framework for AI System Compliance"** (arXiv:2508.18765v2, May 2025) | GaaS enforcement layer: declarative JSON policies, deterministic violation checker (not LLM-based), trust factor scoring, time-stamped audit trail. Outperformed keyword filters, OpenAI moderation, and Constitutional AI agents. Precision 95%, recall 90%. |
| **"Measuring AI Agent Autonomy"** (arXiv:2502.15212v1, Nov 2023) | Found AutoGen agents have human-in-the-loop but low observability agreement (k=0.47). Noted agents "spin up subagents that require human-in-the-loop as fallback." |

---

### OWASP Agentic AI Top 10 (Dec 2025)

The OWASP Top 10 for Agentic Applications was announced at Black Hat Europe 2025. It defines 10 risk categories (ASI01-ASI10) including Agent Goal Hijack, Tool Misuse, Identity/Privilege Abuse, Insecure Inter-Agent Communication, and Rogue Agents.

**Does it reference receipt formatsWARNING** **No.** The OWASP list defines risks and mitigations but does not specify any action receipt format, attestation standard, or cryptographic evidence requirement. The closest it comes is ASI09 (Human-Agent Trust Exploitation) which mentions "immutable logs" as a mitigation, and ASI07 which mentions "signing messages and hashing payload + context."

**Source:** https://www.promptfoo.dev/docs/red-team/owasp-agentic-ai/, https://owasp.org/www-project-agentic-skills-top-10/

---

## Competitive Threat Matrix

| Competitor | Enforcement Layer | Agent Identity | Cryptographic Receipts | Action Attestation | Status | Threat Level |
|------------|-------------------|---------------|----------------------|-------------------|--------|-------------|
| **LangSmith** | No (tracing only) | No | No | No | Shipped | Low |
| **Langfuse** | No (tracing only) | No | No | No | Shipped | Low |
| **Guardrails AI** | Yes (in-process hooks) | No | No | Partial (logs) | Shipped | Low-Med |
| **NeMo Guardrails** | Yes (dialogue proxy) | No | No | No | Shipped | Low |
| **CrewAI** | No (RBAC only) | No | No | Partial (audit logs) | Shipped | Low-Med |
| **AutoGen** | No (HITL only) | No | No | No | Shipped | Low |
| **OpenAI** | No | No | No | No | N/A | None |
| **Anthropic** | No (training-time only) | No | No | No | N/A | None |
| **PointGuard AI** | **Yes (runtime)** | **Yes (crypto)** | No | Partial | Shipped | **High** |
| **Singulr AI** | **Yes (runtime)** | Partial | Partial (tamper-evident) | Partial | Shipped | **High** |
| **ICME Preflight** | Yes (formal verification) | No | **Yes (proofs)** | No | Shipped | Medium |
| **DeepInspect** | **Yes (network layer)** | Partial | **Yes (signed audits)** | Partial | Shipped | Med-High |
| **Pipelock** | **Yes (firewall)** | No | **Yes (Ed25519 signed)** | Partial | Shipped (OSS) | Medium |
| **Aim Security** | Yes (DLP/firewall) | No | No | No | Acquired | Low |
| **AIM Intelligence** | Yes (guardrails) | No | No | No | Shipped | Low |
| **AgentOps** | No | No | No | No | Shipped | Low |
| **OPA + AI** | Yes (policy engine) | Via SPIFFE | No (decision logs) | No | Shipped | Low-Med |
| **AAR Spec** | N/A (format only) | Spec'd | **Yes (Ed25519)** | **Yes** | Proposed | N/A |

---

## Key Findings for AVS Gateway Strategy

### 1. The Receipt Standardization Race Is Wide Open
The AAR spec (4 stars, 1 contributor) is the only public attempt at an action receipt format. No IETF, W3C, or ISO standard exists. OWASP does not reference receipts. This is AVS's biggest opportunity  establishing ASR-1 as the de facto standard before a competitor or standards body does.

### 2. Runtime Enforcement Is Crowded; Receipts Are Not
At least 8+ vendors now offer some form of runtime enforcement (PointGuard, Singulr, DeepInspect, Pipelock, Guardrails AI, ICME, OPA integrations). But almost none produce cryptographically signed, standardized action receipts. AVS's differentiation is the **receipt**, not just the enforcement.

### 3. Agent Identity Is Emerging as a Convergent Need
PointGuard ("verifiable cryptographic identity"), Pipelock (per-agent profiles), SPIFFE/OPA integrations, and CrewAI RBAC all point to the same need: agents need identities. AVS's ASR-1 + Agent Identity milestone is well-timed.

### 4. The "Five Rungs" Framework Defines the Competitive Ladder
ArmoSec's "Five Rungs of AI Policy Enforceability" framework is becoming influential:
- Rung 1: Aspirational (principles)
- Rung 2: Documentary (committed)
- Rung 3: Attested (configuration)
- Rung 4: Application-plane enforced (in-process blocking)
- Rung 5: Two-plane verified (independent observation)

Most competitors (LangSmith, Langfuse, Guardrails AI, CrewAI) are at Rung 4 at best. AVS with cryptographic receipts and network-layer interception is positioned at Rung 5.

### 5. Open-Source Is a Distribution Advantage
Pipelock (open-source AI agent firewall) and the AAR spec (open spec) suggest the market values open infrastructure. AVS's open-source approach (implied by v0.3.4 versioning) aligns with this trend.

---

## Recommendations

1. **Accelerate ASR-1 specification publication**  the receipt format race is open and first-mover advantage is significant.
2. **Engage with the AAR spec author**  consider alignment, extension, or friendly competition rather than ignoring it.
3. **Differentiate on "receipt + identity" not just enforcement**  enforcement is becoming commoditized; receipts are not.
4. **Target the OPA ecosystem**  OPA is becoming the standard policy engine for AI. AVS could position as "OPA's receipt layer."
5. **Monitor PointGuard and Singulr closely**  these are the most credible competitors in the runtime governance space.
