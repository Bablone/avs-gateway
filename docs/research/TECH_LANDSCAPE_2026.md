# AVS Gateway Technology Landscape Research Brief — 2026

**Research Date:** July 2026
**Scope:** Standards, papers, and frameworks relevant to AVS Gateway v0.3.5/v0.3.6
**Status:** Comprehensive — 7 research targets covered

---

## Table of Contents

1. [Microsoft Agent Governance Toolkit (April 2026)](#1-microsoft-agent-governance-toolkit-april-2026)
2. [MCPSHIELD — MCP Security Framework Paper](#2-mcpshield--mcp-security-framework-paper)
3. [OWASP Agentic AI Top 10 (2026)](#3-owasp-agentic-ai-top-10-2026)
4. [RAILS Paper (June 2026)](#4-rails-paper-june-2026)
5. [IETF / W3C / NIST Standards Work](#5-ietf--w3c--nist-standards-work)
6. [Agent Control Protocol / Admission Control Papers](#6-agent-control-protocol--admission-control-papers)
7. [x402 Foundation Governance](#7-x402-foundation-governance)
8. [Cross-Cutting Analysis for AVS](#8-cross-cutting-analysis-for-avs)

---

## 1. Microsoft Agent Governance Toolkit (April 2026)

### What
The **Agent Governance Toolkit (AGT)** is an open-source, multi-language runtime security framework for AI agents, released by Microsoft on **April 2, 2026**. It is a comprehensive 7-package toolkit providing deterministic, sub-millisecond policy enforcement for autonomous AI agents. It claims to be the first toolkit to address all 10 OWASP Agentic AI risks with deterministic controls.

**Core packages:**
| Package | Function | Analogy |
|---------|----------|---------|
| **Agent OS** | Stateless policy engine (<0.1ms p99) | Kernel for AI agents |
| **Agent Mesh** | DIDs (Ed25519), IATP inter-agent trust, 0-1000 trust scoring | mTLS for agents |
| **Agent Runtime** | Execution privilege rings, saga orchestration, kill switch | Process isolation |
| **Agent SRE** | SLOs, error budgets, circuit breakers, chaos engineering | SRE for agents |
| **Agent Compliance** | OWASP verification, EU AI Act/SOC2/HIPAA mapping | Compliance-as-code |
| **Agent Marketplace** | Plugin lifecycle, Ed25519 signing, supply-chain security | Package manager security |
| **Agent Lightning** | RL training governance with violation penalties | Safe training guardrails |

**Additional capabilities:** MCP Security Gateway (tool poisoning detection), Shadow AI Discovery, Governance Dashboard, PromptDefense Evaluator (12-vector prompt injection audit), Contributor Reputation GitHub Action.

**Also announced at Build 2026 (June):**
- **ASSERT** — Adaptive Spec-driven Scoring for Evaluation and Regression Testing (policy-driven eval framework from Microsoft Research)
- **ACS (Agent Control Specification)** — portable runtime control standard, part of AGT

### Status
**SHIPPED** — Public Preview (production-quality, may have breaking changes before GA). First released April 2, 2026. v4.0.0 consolidated 45 packages into 5 distributions.

### Key Findings
- **License:** MIT (fully open source)
- **Languages:** Python (full stack), TypeScript, Rust, Go, .NET
- **Tests:** 9,500+ tests, 992 conformance tests across 10 formal RFC 2119 specs
- **Framework integrations:** LangChain, CrewAI, Google ADK, Microsoft Agent Framework, Semantic Kernel, AutoGen, OpenAI Agents SDK, Claude Code, LlamaIndex, Haystack, Mastra, Dify
- **Policy languages:** YAML, OPA Rego, Cedar
- **Identity:** SPIFFE/DID/mTLS with Ed25519 cryptographic identity
- **Audit:** Tamper-evident Merkle audit log with Decision BOM (Bill of Materials)
- **Standards compliance:** OWASP Agentic AI Top 10 (all 10), NIST AI RMF 1.0 (full GOVERN/MAP/MEASURE/MANAGE), EU AI Act, SOC 2, AARM Extended (R1-R9), ATF (all 5 elements)
- **SLSA-compatible** build provenance, OpenSSF Scorecard tracking, CodeQL, Dependabot, ClusterFuzzLite (7 fuzz targets)
- **Shift-left governance:** Pre-commit hooks for policy validation, plugin manifest validation, CI/CD governance gates
- **Governance model:** GOVERNANCE.md, CHARTER.md (LF Projects format), Microsoft is actively seeking to move to a foundation home
- **Microsoft explicitly states aspiration** to move AGT into a foundation for community governance

**Does it produce receipts/evidence?**
YES. AGT produces tamper-evident Decision Records with Merkle audit. The `agt verify` command generates OWASP compliance evidence. The Agent Compliance package maps to regulatory frameworks with automated evidence collection. However, these are primarily **policy compliance receipts** — not the financially material clearing receipts that RAILS defines.

### Comparison to AVS Policy Engine

| Dimension | Microsoft AGT | AVS Gateway |
|-----------|--------------|-------------|
| **License** | MIT | TBD (internal research) |
| **Scope** | Full-stack governance (policy + identity + runtime + SRE) | Receipts/verification-native clearing gateway |
| **Policy engine** | YAML/OPA/Cedar, sub-ms | TBD |
| **Identity** | DIDs (Ed25519), SPIFFE, IATP | AgentIdentity (v0.3.6 branch) |
| **Receipts** | Compliance evidence (Merkle audit) | ASR-1 receipts, Evidence Envelope (targeted) |
| **Clearing** | No clearing layer | Verification-native clearing (aligned with RAILS) |
| **Standards** | OWASP, NIST AI RMF, EU AI Act, SOC 2 | Aligned with RAILS, MCP, x402 |
| **Language** | Python/TS/Rust/Go/.NET | Likely Rust/Go |
| **MCP Gateway** | Built-in (tool poisoning detection) | ToolManifest (v0.3.6) |

**Key distinction:** AGT is a **governance toolkit** — it gives you components to assemble. AVS is positioned as a **verification-native clearing gateway** — it produces financially material settlement decisions. AGT ensures agents follow policies; AVS ensures settlements are backed by admissible evidence. These are **complementary**, not competitive.

### Implication for AVS
- AGT validates the entire governance category — Microsoft's entry confirms this is a real market
- AGT's MCP Security Gateway overlaps with AVS's ToolManifest functionality
- AGT's Agent Mesh identity system (DIDs + IATP) could be an upstream identity provider for AVS
- AGT does NOT address clearing — this is AVS's differentiation
- Consider: can AVS consume AGT's Decision BOM as evidence input? Can AGT's policy decisions feed into AVS's Evidence Envelope?
- AGT's open-source MIT license means components can be adopted/integrated

### Source
- GitHub: https://github.com/microsoft/agent-governance-toolkit
- Microsoft announcement: https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit/
- Build 2026: https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/
- Comparison (independent): https://systemprompt.io/guides/systemprompt-vs-microsoft-agent-governance

---

## 2. MCPSHIELD — MCP Security Framework Paper

### What
**MCPSHIELD** (arXiv:2604.05969, submitted April 7, 2026) by Nirajan Acharya and Gaurav Kumar Gupta is a comprehensive formal security framework for MCP-based AI agents. It makes four principal contributions:

1. Hierarchical threat taxonomy: **7 threat categories, 23 distinct attack vectors** across 4 attack surfaces
2. Formal verification model based on labeled transition systems with trust-boundary annotations
3. Comparative evaluation of 12 existing defense mechanisms identifying coverage gaps
4. Defense-in-depth reference architecture achieving 91% theoretical coverage

**Key finding:** No existing single defense covers more than **34%** of the threat landscape.

### The 7 Threat Categories and 23 Attack Vectors

| TC | Threat Category | Attack Vectors | Attack Surface |
|----|----------------|----------------|----------------|
| **TC1** | **Tool Poisoning** | TV1: Description injection; TV2: Schema manipulation; TV3: Return value poisoning; TV4: Tool shadowing | Tool Interface |
| **TC2** | **Rug Pull & Mutation** | TV5: Post-approval mutation; TV6: Version rollback; TV7: Capability escalation | Server |
| **TC3** | **Cross-Server Data Leakage** | TV8: Exfiltration via logging; TV9: Context bleed; TV10: Channel coercion; TV11: Sampling abuse | Composition/Transport |
| **TC4** | **Privilege Escalation** | TV12: Capability chaining; TV13: Consent bypass; TV14: Role confusion | Composition/Tool |
| **TC5** | **Server Trust Violations** | TV15: Impersonation; TV16: Supply chain compromise; TV17: Dependency hijacking | Server |
| **TC6** | **Context Manipulation** | TV18: Prompt injection via tool; TV19: Memory poisoning; TV20: Resource injection | Tool/Composition |
| **TC7** | **Protocol-Level Vulnerabilities** | TV21: Session hijacking; TV22: Replay attacks; TV23: Cross-protocol confusion | Transport/Composition |

**Four Attack Surfaces:**
1. **S_tool** — Tool Interface Surface (tool descriptions, parameter schemas, return values)
2. **S_transport** — Transport Surface (JSON-RPC messages, session state, TLS)
3. **S_server** — Server Surface (auth mechanisms, resource access, supply chain)
4. **S_compose** — Composition Surface (multi-server, multi-tool, multi-agent interactions)

### Status
**PUBLISHED** — arXiv preprint, April 7, 2026. Submitted to cs.CR (Cryptography and Security).

### Coverage Analysis for AVS

**AVS v0.3.6 likely addresses:**
- TV1-4 (Tool Poisoning) — via ToolManifest validation
- TV18 (Prompt injection via tool) — via ASR-1 receipts that capture tool behavior
- TV21-22 (Session/replay) — via cryptographic receipt anchoring
- TV12 (Capability chaining) — via delegation chain verification

**Gaps for AVS:**
- TV5-7 (Rug pull/mutation) — runtime behavior mutation after approval
- TV8-11 (Cross-server data leakage) — requires cross-server monitoring
- TV13-14 (Consent bypass, role confusion) — requires semantic policy engine
- TV15-17 (Server trust) — supply chain and dependency risks
- TV19 (Memory poisoning) — persistent memory attacks
- TV20 (Resource injection) — resource-level attacks
- TV23 (Cross-protocol confusion) — MCP/A2A boundary attacks

**Key insight for AVS:** MCPSHIELD's defense-in-depth architecture achieves 91% coverage by integrating: capability-based access control + cryptographic tool attestation + information flow tracking + runtime policy enforcement. AVS's receipt-based approach covers the "cryptographic attestation" dimension but should consider integration points for the other three.

### Implication for AVS
- The 23 attack vectors provide a structured threat model AVS should reference
- ToolManifest (v0.3.6) should aim to cover TC1 (Tool Poisoning) comprehensively
- Consider: ASR-1 receipts can serve as "cryptographic tool attestation" evidence in the MCPSHIELD framework
- Cross-protocol confusion (TV23) is particularly relevant as AVS bridges MCP, A2A, and x402
- MCPSHIELD's finding that no single defense covers >34% validates AVS's layered approach

### Source
- arXiv: https://arxiv.org/abs/2604.05969
- PDF: https://arxiv.org/pdf/2604.05969
- Authors: Nirajan Acharya, Gaurav Kumar Gupta

---

## 3. OWASP Agentic AI Top 10 (2026)

### What
The **OWASP Top 10 for Agentic Applications** (ASI01-ASI10) was published in **December 2025** by the OWASP GenAI Security Project. It is the first community-curated taxonomy of the ten most critical security risks for autonomous AI agents, developed with 100+ industry experts. It extends — does not replace — the OWASP Top 10 for LLM Applications.

**The Complete List:**

| ID | Risk | Description | New? |
|----|------|-------------|------|
| **ASI01** | **Agent Goal Hijack** | Attacker redirects agent's plan/objective via injection | Extension of LLM01+LLM06 |
| **ASI02** | **Tool Misuse & Exploitation** | Agent invokes tools unsafely through composition/recursion | Extension of LLM06 |
| **ASI03** | **Identity & Privilege Abuse** | Delegated authority misuse, cross-agent trust exploitation | Extension of LLM01+LLM02 |
| **ASI04** | **Agentic Supply Chain Vulnerabilities** | Runtime composition of malicious/tampered third-party components | Extension of LLM03 |
| **ASI05** | **Unexpected Code Execution** | Agent-generated code executes outside sandbox | Extension of LLM01+LLM05 |
| **ASI06** | **Memory & Context Poisoning** | Persistent memory shaped to mislead future decisions | Extension of LLM01+LLM04 |
| **ASI07** | **Insecure Inter-Agent Communication** | Spoofed/replayed/unauthenticated agent-to-agent messages | **NEW** |
| **ASI08** | **Cascading Failures** | Error in one agent fans out across the system | **NEW** |
| **ASI09** | **Human-Agent Trust Exploitation** | Humans over-trust or are deceived by agent outputs | Extension of LLM09 |
| **ASI10** | **Rogue Agents** | Agent operates outside policy — drift, collusion, compromise | **NEW** |

**Three entirely new risk classes** (not in LLM Top 10): ASI07 (Inter-Agent Communication), ASI08 (Cascading Failures), ASI10 (Rogue Agents).

### Status
**PUBLISHED** — Announced December 9, 2025. CC BY-SA 4.0 license. Voluntary — no legal status by itself but mapped to NIST AI RMF, ISO/IEC 42001, and EU AI Act.

### Mapping to AVS

| OWASP Risk | AVS v0.3.6 Coverage | Gap/Opportunity |
|------------|---------------------|-----------------|
| ASI01 Goal Hijack | Partial — ASR-1 receipts capture what happened post-hoc | Pre-hoc goal validation not addressed |
| ASI02 Tool Misuse | Yes — ToolManifest validates tool schemas and capabilities | Tool composition safety (chaining) |
| ASI03 Identity Abuse | Yes — AgentIdentity with delegation chains | Revocation and real-time trust scoring |
| ASI04 Supply Chain | Partial — Tool signing/attestation | Full supply chain dependency tracking |
| ASI05 Code Execution | No — execution sandboxing out of scope | Could integrate with external sandbox |
| ASI06 Memory Poisoning | No — persistent memory not in scope | Receipts could include memory checksums |
| ASI07 Inter-Agent Comms | Partial — A2A/MCP bridging | Full A2A security protocol |
| ASI08 Cascading Failures | Yes — receipt chain enables failure tracing | Circuit breaker integration |
| ASI09 Trust Exploitation | Partial — evidence-based settlement | Human-in-the-loop gates |
| ASI10 Rogue Agents | Partial — behavior captured in receipts | Real-time anomaly detection |

**Key insight:** ASI07 (Insecure Inter-Agent Communication) and ASI08 (Cascading Failures) are the most relevant "new" risks for AVS. Receipt-based clearing inherently addresses cascading failures by providing traceability. ASI10 (Rogue Agents) is where AVS's clearing layer provides unique value — no other control can detect and attribute rogue behavior as precisely as a clearing protocol with evidence envelopes.

### Implication for AVS
- AVS should reference ASI01-ASI10 in documentation and compliance materials
- The three "new" risks (ASI07, ASI08, ASI10) are where AVS has strongest differentiation
- Consider building an OWASP compliance verification mode into the gateway
- Microsoft AGT already covers all 10 — AVS should demonstrate complementary rather than overlapping coverage

### Source
- Official: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Announcement: https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications/
- License: CC BY-SA 4.0

---

## 4. RAILS Paper (June 2026)

### What
**RAILS** (Real-Time Agent Integrity & Ledger Settlement, arXiv:2606.08790, June 7, 2026) by Alex Bogdan and Adrian de Valois-Franklin introduces a **verification-native clearing protocol** for agentic commerce. It defines and solves the **"agentic clearing problem"** — the gap between what agents do and what should be settled.

**Core thesis:** "Autonomous-agent commerce cannot scale without a neutral mechanism that converts execution traces into admissible evidence, aggregates verifier outputs under explicit admissibility classes, and emits settlement instructions that are sound."

**The 7 Primitives:**

| Primitive | Function | AVS Mapping |
|-----------|----------|-------------|
| **Obligation Object (OO)** | Signed, machine-clearable contract compiling natural-language intent into structured terms (parties, scope, acceptance criteria, admissibility floor, settlement policy) | AVS **IntentRecord** — the structured mandate that defines what the agent is obligated to do |
| **Evidence Envelope (EE)** | Hash-anchored container of evidence items (git diffs, CI logs, scanner outputs, receipts, agent self-reports), each with provenance chain and admissibility tag | AVS **ASR-1 Receipt** + **ReceiptBundle** — the structured evidence container |
| **Verification Mesh** | Configured set of heterogeneous verifiers (constraint checkers, receipt verifiers, semantic judges, policy checkers, human arbiters) returning verdict + confidence + evidence basis | AVS **VerifierRegistry** — the set of registered verifiers the gateway can invoke |
| **Clearing Decision** | Structured verdict with performance status, policy status, fault assignment, loss estimate, evidence basis, aggregated confidence, finality status | AVS **ClearingResult** — the gateway's output decision |
| **Settlement Instruction** | Structured action list (fee_action, principal_action, collateral_action, claim_action, penalty_action, reputation_action) targeting a named execution rail | AVS **SettlementDirective** — the downstream instruction emitted to x402/escrow |
| **Clearing Passport** | Cross-transaction reliability record for agents/tools/providers; what they've cleared, what's disputed, where declared bases have drifted | AVS **AgentTrustScore** + **ReputationLedger** |
| **Finality Rules** | Predicate (admissibility floor met, confidence threshold met, appeal window expired) transitioning from PROVISIONAL to FINAL | AVS **FinalityEngine** — the binding arbitration logic |

**Key properties:**
- **Soundness:** No financially material settlement is supported by evidence below the obligation's admissibility floor
- **Falsifiable:** The soundness property can be tested against the specification
- **Positioned among existing protocols, not against them:** Consumes MCP tool traces, A2A subdelegation events, AP2 mandates; targets x402, escrow, enterprise ledgers

**Six separable questions** RAILS answers that no other protocol addresses:
1. Authorization (was the agent allowed?)
2. Execution (what did it actually do?)
3. Performance (did the action satisfy the obligation?)
4. Attribution (who caused the failure?)
5. Loss (what harm occurred?)
6. Settlement (what consequence follows?)

### Status
**PUBLISHED** — arXiv preprint, June 7, 2026. v1 with 3,270 KB. Authors: Alex Bogdan, Adrian de Valois-Franklin (Evolutionairy AI, Toronto).

### How RAILS Maps to AVS

The AVS Gateway v0.3.6 architecture (ASR-1 receipts, AgentIdentity, ToolManifest) appears to be building **exactly the primitives** RAILS specifies:

| RAILS Primitive | AVS v0.3.6 Component | Maturity |
|-----------------|----------------------|----------|
| Obligation Object | IntentRecord / PolicyManifest | In development |
| Evidence Envelope | ASR-1 Receipt format | v0.3.6 branch |
| Verification Mesh | External verifier plugins | Planned |
| Clearing Decision | Gateway clearing engine | Core function |
| Settlement Instruction | x402 adapter | Planned |
| Clearing Passport | Agent reputation store | Planned |
| Finality Rules | Finality arbitration | Planned |

**Critical insight:** RAILS defines the **protocol specification** that AVS should implement. The paper is not competition — it is the **requirements document** for AVS's clearing layer. The soundness property is the falsifiable claim AVS should be able to make.

### Implication for AVS
- RAILS is the **most important academic paper** for AVS — it specifies the clearing protocol AVS is building
- The seven primitives should be AVS's architectural blueprint
- The soundness property (no material settlement below admissibility floor) should be AVS's core guarantee
- RAILS's finding that MCP/A2A/x402/AP2 all assume but do not produce clearing decisions validates AVS's entire product thesis
- Consider formal verification of AVS's clearing engine using TLA+ (as RAILS suggests)
- RAILS Report Cards (public model-scope reliability ratings) are a natural product extension

### Source
- arXiv: https://arxiv.org/abs/2606.08790
- Full HTML: https://arxiv.org/html/2606.08790v1
- Analysis: https://www.neuralinsights.io/blog/rails-a-verification-native-approach-to-clearing-in-agentic-commerce

---

## 5. IETF / W3C / NIST Standards Work

### 5a. IETF

#### WIMSE Working Group
The **IETF WIMSE (Workload Identity in Multi-System Environments)** working group is the most concrete IETF effort relevant to agents. It is chartered to evolve SPIFFE concepts into IETF standards-track documents.

**Status:** Active working group, drafts include architecture document, workload credentials spec, workload identifier format, mutual TLS profile, and practices document. The architecture draft **explicitly includes AI agents as a use case**.

**Key draft:** `draft-ni-wimse-ai-agent-identity-02` (February 2026) — "WIMSE Applicability for AI Agents" — discusses establishing independent identities and credential management for AI agents. Expires September 2026.

**What WIMSE provides:** Cryptographically verifiable workload identity — short-lived credentials proving identity without shared secrets or long-lived API keys.

**What WIMSE does NOT provide:** Delegation authority, trust scoring, or clearing decisions. Identity only, not authorization or governance.

**Implication for AVS:** WIMSE is the identity layer AVS should build on. AgentIdentity (v0.3.6) should be compatible with WIMSE/SPIFFE identity formats. Treat WIMSE as complement, not substitute.

### 5b. W3C

#### Agent Identity Registry Protocol Community Group
Launched **April 24, 2026**. Develops open specifications for verifiable AI agent identity infrastructure.

**Scope:**
- DID method specification for agent identity resolution
- Agent credential format based on W3C Verifiable Credentials
- Trust negotiation protocol for cross-organizational agent interactions
- Trust level definitions and verification requirements
- Integration profiles (MCP, A2A, OAuth/OIDC, SPIFFE)
- Revocation and credential lifecycle management
- Post-quantum cryptographic requirements

**Key question being debated (Issue 37, 40+ comments):** Do agents get their own cryptographic identities or inherit credentials from human principals? Thread leaning toward **separate agent identity with delegated authority**.

**Coordination:** W3C CCG (Credentials Community Group), DIF (Decentralized Identity Foundation), OpenID Foundation AIIM Community Group, IETF WIMSE Working Group.

#### AI Agent Protocol Community Group
Launched earlier (August 2025). Focuses on inter-agent communication protocols, agent identity models, standardized metadata formats, security/privacy mechanisms, and protocol interoperability.

**Status:** Has produced a white paper draft and technical specification framework draft covering agent identity authentication, discovery/description protocols, inter-agent communication standards, and security mechanisms.

#### Agent-Specific DID Use Cases (GitHub issue)
W3C DID spec issue #926 (March 2026) discusses trust graphs, delegation, and behavioral attestation for agents.

**Implication for AVS:**
- W3C agent identity work is in Community Group phase — no standards yet, likely 12-18 months out
- AVS should use DIDs as the identity format for AgentIdentity (v0.3.6)
- The separate-vs-inherited identity debate (Issue 37) — AVS should implement **separate agent identity with delegation chains** (this is the winning direction)
- Monitor W3C CCG and DIF for emerging standards

### 5c. NIST

#### AI Agent Standards Initiative
Launched **February 17, 2026** by NIST's Center for AI Standards and Innovation (CAISI).

**Three pillars:**
1. **Industry-led standards** — U.S. leadership in international standards bodies (ISO/IEC JTC 1)
2. **Open-source protocols** — Community-led development (funded via NSF Pathways program)
3. **Security and identity research** — NIST research on authentication, identity, security evaluations

**Key deliverables/timeline:**
- March 9, 2026: RFI on AI agent security threats closed
- March 31, 2026: Draft on automated benchmark evaluations closed
- April 2, 2026: NCCoE concept paper on AI Agent Identity and Authorization closed
- April 2026: Sector-specific listening sessions (healthcare, finance, education)

**Six themes NIST is prioritizing:**
1. Agent identity and authentication (enterprise-grade identities, not just API keys)
2. Stricter authorization (least privilege, just-in-time, task-scoped)
3. Auditability and non-repudiation (what was allowed, what context, what decision)
4. Post-deployment monitoring (functionality, operations, security, compliance, human factors)
5. Prompt injection as control design problem (not model-quality issue)
6. Interoperability and protocol standardization

**Related standards being developed:**
- **COSAiS** (Community-Driven Open Source AI Security) — overlays for AI-specific controls, being finalized
- NIST AI RMF — already published, maps to agent governance
- Cyber AI Profile (CSF 2.0) — cybersecurity outcomes for AI

**Implication for AVS:**
- NIST's timing aligns well with AVS's development cycle
- NIST's six themes closely match AVS's capabilities — AVS should position as implementing NIST's direction
- The NCCoE concept paper on identity and authorization is directly relevant to AgentIdentity
- COSAiS overlays, when finalized, will provide specific control requirements AVS should meet
- Consider engaging with NIST RFI process or future stakeholder sessions

### Source
- IETF WIMSE: https://datatracker.ietf.org/doc/html/draft-ni-wimse-ai-agent-identity-02
- W3C Agent Identity CG: https://www.w3.org/community/agent-identity/
- W3C AI Agent Protocol CG: https://www.w3.org/community/agentprotocol/
- NIST Initiative: https://www.metricstream.com/blog/nists-ai-agent-standards-initiative.html
- OIDF response to NIST: https://openid.net/oidf-responds-to-nist-on-ai-agent-security/
- NIST overview: https://workos.com/blog/nist-ai-agent-standards-initiative-explained

---

## 6. Agent Control Protocol / Admission Control Papers

### What
Two significant admission-control papers for agents were identified:

#### 6a. ACP — Agent Control Protocol (March 2026)
**arXiv:2603.18829**, submitted March 19, 2026. By Marcelo Fernandez (TraslaIA).

ACP is a **temporal admission control protocol** enforcing behavioral properties over execution traces. It addresses the gap that stateless policy engines cannot catch harmful behavioral patterns from individually valid requests.

**Key contributions:**
- Stateful admission decisions (history-aware, not per-request)
- Deterministic risk scoring with anomaly accumulation and cooldown
- **LedgerQuerier abstraction** separating decision logic from state management
- Sub-microsecond decision latency (739-832ns p50, 1.72M req/s throughput)
- TLA+ model checking (11 invariants + 4 temporal properties, 0 violations across 4.29B states)
- 73 signed conformance test vectors (Ed25519 + SHA-256)
- ACP-RISK-3.0 eliminates cross-context state-mixing via PatternKey(agentID, capability, resource)

**Key security result:** Under a 500-request workload where every request is individually valid (RS=35), a stateless engine approves all 500; ACP limits autonomous execution to **2 out of 500 (0.4%)**, escalating after 3 actions and denying after 11.

**Five conformance levels (L1-L5):** 38 technical documents, Go reference implementation (23 packages), OpenAPI 3.1.0 spec (18 endpoints).

**12 explicitly prohibited behaviors** whose presence disqualifies conformance at any level.

**Paper is P1 of a 6-paper Agent Governance Series:** P0 (atomic decision boundaries), P2 (behavioral drift detection/IML), P3/4 (governance structure/fair allocation), P5 (runtime execution validity/RAM, arXiv:2604.22898), P6 (operationalization of RAM).

#### 6b. A-MAC — Adaptive Memory Admission Control (March 2026)
**arXiv:2603.04549**, submitted March 4, 2026. By Guilin Zhang et al. (Workday AI).

A-MAC treats **memory admission** as a structured decision problem. It scores candidate memories across five dimensions:
1. **Future Utility** — potential relevance for future tasks
2. **Factual Confidence** — supported by prior evidence (mitigates hallucination)
3. **Semantic Novelty** — prevents redundant storage
4. **Temporal Recency** — accounts for decay
5. **Content Type Prior** — domain knowledge about persistence value

Results: F1 of 0.583 (31% faster than LLM-native memory systems). Type Prior identified as most influential feature.

### Status
**PUBLISHED** — Both are arXiv preprints (March 2026).

### Implication for AVS
- **ACP is directly relevant** to AVS's admission control layer — its temporal admission approach should inform AVS gateway request gating
- ACP's LedgerQuerier abstraction provides a pattern for separating decision logic from state — similar to how AVS separates clearing logic from receipt storage
- ACP's finding that stateless engines cannot enforce behavioral properties validates AVS's stateful receipt-based approach
- ACP's 5 conformance levels (L1-L5) provide a maturity model AVS could adopt
- A-MAC is less directly relevant but its memory admission framework could inform how AVS decides which receipts/evidence to retain long-term
- The 6-paper Agent Governance Series (with P5 being Runtime Execution Validity/RAM) suggests a growing academic foundation for agent runtime governance

### Source
- ACP: https://arxiv.org/abs/2603.18829
- ACP spec: https://agentcontrolprotocol.xyz
- A-MAC: https://arxiv.org/abs/2603.04549
- A-MAC code: https://github.com/GuilinDev/Adaptive_Memory_Admission_Control_LLM_Agents

---

## 7. x402 Foundation Governance

### What
The **x402 Foundation** was launched on **April 2, 2026** at the MCP Dev Summit North America as a Linux Foundation project. It stewards the **x402 protocol**, an open standard for embedding payments directly into HTTP interactions (reviving HTTP 402 "Payment Required"). The protocol enables AI agents, APIs, and apps to transact value as seamlessly as they exchange data.

**Protocol flow:**
1. Client requests resource → `GET /resource`
2. Server returns `402 Payment Required` with `PAYMENT-REQUIRED` header (price, token, network, merchant address)
3. Client constructs signed payment payload
4. Client retries with `PAYMENT-SIGNATURE` header
5. Server verifies (directly or via facilitator)
6. Settlement happens on-chain
7. Server delivers resource with `PAYMENT-RESPONSE` header

**x402 V2** (December 2025) adds: unified payment interface (multi-chain), wallet-based identity with reusable sessions, automatic service discovery. Supports subscriptions, prepaid access, usage-based billing, multi-step agent workflows.

### Governance Model

**Legal structure:** "x402, a Series of LF Projects, LLC" — Linux Foundation governance framework. Neutral, non-profit, vendor-independent.

**Initial governing body:** Coinbase, Cloudflare, Stripe

**Premier members (13):** Adyen, Amazon Web Services, American Express, Circle, Cloudflare, Coinbase, Fiserv, Google, Mastercard, Shopify, Solana Foundation, Stripe, Visa

**Additional members:** Ampersend.ai, Base, KakaoPay, Merit Systems, Microsoft, Polygon Labs, PPRO, Sierra, thirdweb, and others.

**Key governance characteristics:**
- Business governance, membership, and strategy managed by the Foundation
- Technical contributions to spec and code are **open to the public**
- Coinbase recognized as founding contributor (donated IP)
- Cloudflare and Stripe on initial governing body
- Jim Zemlin (Linux Foundation CEO) provides executive oversight

**Who controls the spec:**
- The Foundation Board (governing body members) sets strategic direction
- Technical decisions made by participating contributors (open governance)
- Coinbase, Cloudflare, Stripe have outsized influence as founding/governing members
- Any vendor can propose changes — "vendor-neutral, community-driven"

**Specification:** https://www.x402.org/ — open standard, not tied to any specific network

### Status
**SHIPPED** — Active protocol with real transaction volume:
- Base: 119M+ cumulative transactions, $35M+ volume (as of March 2026)
- Solana: 38.6M cumulative transactions, $7.9M volume
- Weekly: Solana processing ~49-51% of all x402 transactions (roughly even with Base)
- Google integrated x402 into Agentic Payments Protocol (AP2) as default stablecoin rail
- Cloudflare provides native x402 support in Workers and AI Agents SDK
- Stripe describes x402 as "machine-to-machine payments" in official docs

### Implication for AVS
- x402 is the **primary settlement rail** AVS should target for Settlement Instructions
- AVS's clearing layer sits **between** x402 (payment execution) and the agent/tool layers — exactly the position RAILS defines
- The x402 Foundation's open governance model is one AVS should consider emulating
- x402's facilitator model (optional middleware for settlement) is analogous to AVS's gateway model
- Google's AP2 integration of x402 means AVS clearing decisions could flow through Google's agent payment infrastructure
- Consider x402 Foundation membership for AVS — being at the table shapes the protocol
- The coexistence of x402 (per-request, software-paying-software) and Stripe ACP (regulated commerce with human approval) suggests AVS needs to support both models

### Source
- Linux Foundation announcement: https://www.linuxfoundation.org/press/linux-foundation-is-launching-the-x402-foundation/
- x402.org: https://www.x402.org/
- Ecosystem: https://www.x402.org/ecosystem
- Cloudflare docs: https://developers.cloudflare.com/agents/tools/payments/x402/
- Galaxy Research analysis: https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments
- The Defiant: https://thedefiant.io/news/infrastructure/coinbase-x402-payment-protocol-moves-to-linux-foundation

---

## 8. Cross-Cutting Analysis for AVS

### 8.1 AVS Position in the Emerging Stack

The agentic infrastructure stack is crystallizing. RAILS (Section 4) provides the clearest architectural map:

```
[ Settlement Layer ]      x402, Stripe ACP, Visa/Mastercard agent protocols, enterprise ledgers
       ↑
[ CLEARING LAYER ]        ← AVS GATEWAY POSITION (RAILS clearing protocol)
       ↑                          - Obligation validation
[ Protocol Layer ]                - Evidence aggregation
  MCP (tools)                     - Verification mesh coordination
  A2A (inter-agent)               - Clearing decisions
  AP2 (mandates)                  - Settlement instructions
       ↑
[ Agent Layer ]
  Agent frameworks, models, tool calling
```

**AVS occupies the clearing layer** — the missing primitive that converts execution traces into admissible evidence and emits sound settlement instructions. This position is:
- **Above** the protocol layer (MCP, A2A, AP2 feed evidence into AVS)
- **Below** the settlement layer (x402, escrow, settlement-risk standards consume AVS's Settlement Instructions)
- **Complementary to** the governance layer (Microsoft AGT provides policy enforcement, AVS provides clearing decisions)
- **Built on** the identity layer (W3C DIDs, IETF WIMSE/SPIFFE provide agent identity)

### 8.2 What AVS Should Adopt

| Standard/Paper | Adoption Priority | Action |
|----------------|-------------------|--------|
| RAILS 7 primitives | **CRITICAL** | Architectural blueprint for v0.3.6+ |
| OWASP ASI01-ASI10 | **HIGH** | Compliance vocabulary, threat model reference |
| MCPSHIELD taxonomy | **HIGH** | Threat model for MCP gateway functionality |
| W3C Agent Identity CG | **HIGH** | DID-based AgentIdentity format |
| IETF WIMSE | **MEDIUM** | SPIFFE-compatible workload identity |
| NIST AI Agent Standards | **MEDIUM** | Position AVS as implementing NIST direction |
| Microsoft AGT | **MEDIUM** | Integration point for policy decisions |
| ACP admission control | **MEDIUM** | Inform gateway admission logic design |
| x402 protocol | **CRITICAL** | Primary settlement rail for Settlement Instructions |
| x402 Foundation | **HIGH** | Consider membership; align with governance model |

### 8.3 What AVS Should NOT Do

- **Do not build a policy engine** — Microsoft AGT (MIT license) already does this. Integrate with it.
- **Do not build agent runtime/sandboxing** — AGT's Agent Runtime handles this. AVS focuses on clearing.
- **Do not compete with x402 on payments** — x402 is the settlement rail; AVS produces the decisions it executes.
- **Do not compete with MCP on tool protocols** — MCP is the tool interface; AVS validates the traces it produces.
- **Do not wait for standards to finalize** — W3C/IETF/NIST processes are 12-24 months out. Build now, align as standards emerge.

### 8.4 Differentiation Thesis

AVS's unique position:

1. **Verification-native clearing** — Not just policies, not just payments, but the admissible-evidence layer between them
2. **Financially material soundness** — The "no settlement below admissibility floor" property that RAILS defines
3. **Cross-protocol** — Bridges MCP, A2A, and x402 rather than being tied to any single protocol
4. **Receipt-centric** — ASR-1 receipts as the Evidence Envelope format, enabling third-party verification
5. **Falsifiable claims** — Not "we make agents safe" but "we guarantee no settlement without admissible evidence"

### 8.5 Competitive Intelligence Summary

| Competitor/Alternative | What They Do | What They DON'T Do (AVS Opportunity) |
|------------------------|-------------|--------------------------------------|
| Microsoft AGT | Policy enforcement, identity, runtime governance | Clearing, settlement decisions, evidence grading |
| MCPSHIELD | Threat taxonomy, defense architecture | Runtime implementation, clearing protocol |
| RAILS (paper) | Protocol specification, formal model | Implementation, runtime gateway |
| x402 Foundation | Payment settlement rail | Clearing decisions, evidence verification |
| ACP (Agent Control Protocol) | Temporal admission control | Clearing, settlement, cross-protocol bridging |
| W3C/IETF/NIST | Standards development | Implementation |

**The gap AVS fills:** No existing project implements the RAILS clearing protocol as a production gateway. RAILS is the spec, AVS is the implementation.

### 8.6 Risk Factors

1. **Microsoft AGT could add clearing** — But their stated aspiration is foundation governance, not clearing. They complement rather than compete.
2. **RAILS authors could build an implementation** — But the paper positions as "protocol specification," not product. Potential partnership.
3. **x402 Foundation could add clearing** — But their scope is payment settlement. Clearing is an adjacent problem.
4. **Standards could diverge** — W3C and IETF may produce incompatible identity standards. AVS should design for protocol agility.
5. **Category definition risk** — "Agent clearing" is not yet a recognized category. AVS must educate the market.

---

## Appendix: Source Registry

| # | Source | URL | Date |
|---|--------|-----|------|
| 1 | Microsoft AGT GitHub | https://github.com/microsoft/agent-governance-toolkit | Apr 2026 |
| 2 | Microsoft AGT Announcement | https://opensource.microsoft.com/blog/2026/04/02/ | Apr 2026 |
| 3 | Microsoft Build 2026 | https://devblogs.microsoft.com/foundry/build-2026-open-trust-stack-ai-agents/ | Jun 2026 |
| 4 | MCPSHIELD arXiv | https://arxiv.org/abs/2604.05969 | Apr 2026 |
| 5 | OWASP Agentic Top 10 | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | Dec 2025 |
| 6 | RAILS arXiv | https://arxiv.org/abs/2606.08790 | Jun 2026 |
| 7 | IETF WIMSE AI Agent Identity | https://datatracker.ietf.org/doc/html/draft-ni-wimse-ai-agent-identity-02 | Feb 2026 |
| 8 | W3C Agent Identity CG | https://www.w3.org/community/agent-identity/ | Apr 2026 |
| 9 | W3C AI Agent Protocol CG | https://www.w3.org/community/agentprotocol/ | Aug 2025 |
| 10 | NIST AI Agent Standards | https://www.nist.gov/casi | Feb 2026 |
| 11 | ACP arXiv | https://arxiv.org/abs/2603.18829 | Mar 2026 |
| 12 | A-MAC arXiv | https://arxiv.org/abs/2603.04549 | Mar 2026 |
| 13 | x402 Foundation Launch | https://www.linuxfoundation.org/press/linux-foundation-is-launching-the-x402-foundation/ | Apr 2026 |
| 14 | x402 Protocol | https://www.x402.org/ | Ongoing |
| 15 | Cloudflare x402 Docs | https://developers.cloudflare.com/agents/tools/payments/x402/ | Jun 2026 |
| 16 | Galaxy x402 Research | https://www.galaxy.com/insights/research/x402-ai-agents-crypto-payments | Jun 2026 |
| 17 | IETF WIMSE WG Analysis | https://capisc.io/blog/what-ietf-wimse-oauth-and-owasp-actually-say-about-agent-authorization | May 2026 |
| 18 | NIST Initiative Overview | https://workos.com/blog/nist-ai-agent-standards-initiative-explained | Apr 2026 |
| 19 | OIDF NIST Response | https://openid.net/oidf-responds-to-nist-on-ai-agent-security/ | Mar 2026 |
| 20 | RAILS Analysis | https://www.neuralinsights.io/blog/rails-a-verification-native-approach-to-clearing-in-agentic-commerce | Jun 2026 |
| 21 | AGT vs SystemPrompt | https://systemprompt.io/guides/systemprompt-vs-microsoft-agent-governance | May 2026 |
| 22 | MCP Security Best Practices | https://labs.cloudsecurityalliance.org/agentic/agentic-mcp-security-best-practices-v1/ | May 2026 |
| 23 | W3C Agent Identity Debate | https://dev.to/t49qnsx7qtkpanks/the-agent-identity-debate-at-w3c-36g | May 2026 |
| 24 | ACP Spec Website | https://agentcontrolprotocol.xyz | Mar 2026 |

---

*Research compiled July 2026. All status classifications reflect publicly available information as of research date. Standards statuses are subject to rapid change.*
