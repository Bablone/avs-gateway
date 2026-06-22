# The Complete Agentic Landscape Map — 2026
## AVS Checkpoint Analysis: v0.3.5 Released, v0.3.6 Branch Active

**Date:** 2026-06-26
**Purpose:** Full-spectrum intelligence from AVS's current position
**Sources:** 3 research agents, 50+ sources, 23 competitors analyzed, 7 verticals evaluated

---

## Executive Summary

The market is moving from "agents can pay" to "agents need permission, identity, spend limits, evidence, and clearing before they can safely act." This is strongly favorable for AVS. But the category is getting crowded fast — 23 competitors identified, with 4 at HIGH or CRITICAL threat level.

The winning positioning remains:
> **AVS is not a payment rail. AVS is the runtime permission and proof layer before autonomous actions touch payment rails, tools, APIs, files, or regulated workflows.**

The full stack is becoming:
```
Model → Agent → AVS → Tool/Payment Rail → ASR-1 Receipt → Clearing/Dispute/Compliance
```

Mastercard, Visa, AWS, Stripe, Google, Coinbase, and Catena validate the payment side. Microsoft validates the governance side. The research community validates the risk side. AVS occupies the intersection.

---

## Part 1: The Competitive Battlefield

### CRITICAL Threat: Pipelock / PipeLab

| Field | Detail |
|-------|--------|
| **What** | Open-source Ed25519-signed receipt format with hash chains, conformance mediators, multi-language verifiers, and conformance corpus |
| **Status** | Shipped — actively seeking standardization through CoSAI / IETF / OASIS |
| **Threat** | **CRITICAL** |
| **Why** | Most direct competitor to AVS's ASR-1. They have signed receipts, hash chains, multi-language support, AND are pursuing standards bodies. If they get IETF adoption first, ASR-1 becomes secondary. |

**AVS response:** Ship ASR-1 spec publicly immediately. Multi-language verifier (TypeScript minimum). Start standards engagement now, not later.

### HIGH Threats (8 competitors)

**1. Cerbos** — Authorization management with AI agent MCP boundary control, runtime PDPs, audit logs. Shipped. **Threat: HIGH.** They do runtime policy enforcement across 11 agent frameworks. If they add receipts, they match AVS's core.

**2. Prefactor** — Runtime governance: block/throttle/sandbox/escalate at execution layer, framework-agnostic. Nearly identical positioning to AVS. **Threat: HIGH.** Direct feature overlap.

**3. t54 labs** — x402-secure: pre-payment risk checks, policy enforcement, agent-native credit. Built specifically for x402 hardening. **Threat: HIGH.** If x402 becomes dominant, t54 owns the governance layer.

**4. Aletheia Core** — HMAC-SHA256 signed audit receipts with runtime enforcement. **Threat: HIGH.** Signed receipts + enforcement = AVS's exact positioning.

**5. CertNode** — ES256-JWS receipts, RFC 3161 timestamping, Bitcoin anchoring, FRE 902 legal standard. **Threat: HIGH.** Legally-structured receipts for court admissibility. AVS doesn't have this.

**6. Microsoft Agent Governance Toolkit** — 7-package toolkit, MIT license, 9,500+ tests, 11 framework integrations, OWASP/NIST/EU AI Act compliance. **Threat: HIGH.** Microsoft can commoditize basic governance. BUT: no clearing layer, no payment-aware policies. AVS's differentiation is receipts + clearing.

**7. Microsoft Entra Agent ID + Agent 365** — Enterprise agent identity, policy enforcement, tool controls, cost management. **Threat: HIGH.** Microsoft will own enterprise default. AVS must be the open, portable alternative.

**8. Saviynt + LangChain** — Runtime enforcement inside LangChain middleware, identity, audit. **Threat: HIGH.** If LangChain integrates Saviynt as default governance, AVS needs adapter parity.

### MEDIUM Threats (6 competitors)

**Nevermined** — Visa+x402 integration for delegated agent spending. MCP: MEDIUM. Could extend into governance.

**Kite AI** — Kite Passport: budgets/permissions/scope. MCP: MEDIUM. "Verify every action before money moves." Adjacent positioning.

**Shopify** — UCP commerce governance + MCP data access. MCP: MEDIUM. Could extend into tool governance.

**Amex ACE** — Intent-driven transactions + purchase protection. MCP: MEDIUM. Trust layer positioning.

**OPA for Agents** — Enterprises may build in-house. MCP: MEDIUM. Open source, extensible.

**Cloudflare x402** — x402 at CDN layer. MCP: MEDIUM. Could add governance at edge.

### LOW Threat / Opportunity (9 players)

Tempo (settlement rail), BVNK (stablecoin infra, being acquired by Mastercard), Fiserv (legacy), AgentOps (observability), Langfuse (observability), Simbian (security ops), Sierra (customer service). These are complementary, not competitive.

---

## Part 2: The Technology Landscape — Standards, Papers, Frameworks

### Microsoft Agent Governance Toolkit (April 2026)

Microsoft shipped a 7-package open-source toolkit with 9,500+ tests, 11 framework integrations, and deterministic sub-ms policy enforcement. MIT license.

| Package | What | AVS Equivalent |
|---------|------|----------------|
| Agent OS | Policy engine (<0.1ms) | PolicyEngine |
| Agent Mesh | DIDs, trust scoring | AgentIdentity |
| Agent Runtime | Privilege rings, kill switch | GatewayCore |
| Agent SRE | SLOs, circuit breakers | Not in AVS |
| Agent Compliance | OWASP/EU AI Act mapping | Future |
| Agent Marketplace | Plugin security | ToolManifest |
| Agent Lightning | Training governance | Not in AVS |

**Key insight:** AGT validates the category. Microsoft's entry confirms this is real. AGT does NOT address clearing — this is AVS's wedge. AGT's Decision BOM could feed into AVS's Evidence Envelope. They are complementary, not competitive.

### MCPSHIELD Paper (April 2026)

7 threat categories, 23 attack vectors across 4 MCP surfaces. No single defense covers >34%.

**The 7 categories:**
1. Tool Poisoning — malicious tool definitions
2. Data Exfiltration — unauthorized data access
3. Prompt Injection via MCP — context manipulation
4. Tool Execution Hijacking — unauthorized tool calls
5. Privilege Escalation — scope expansion
6. Server Compromise — MCP server takeover
7. Cross-Tool Chaining — multi-tool attack sequences

**AVS coverage:** ToolManifest addresses #1 (tool identity). PolicyEngine addresses #2-5. Network sandbox addresses #6. Audit chain addresses #7 traceability. Gap: AVS does not have native MCP gateway functionality.

**Opportunity:** AVS MCP Tool Guard — tool identity attestation, action classification, read/write/destructive separation, argument-level policy, PII scan, ASR-1 receipt per invocation.

### OWASP Agentic AI Top 10 (December 2025)

Published. 10 risk categories: ASI01-ASI10.

Three categories are entirely new and strongly favor AVS:
- **ASI07: Inter-Agent Communication Risks** — agents talking to agents without governance
- **ASI08: Cascading Failures** — one agent's failure causing chain reactions
- **ASI10: Rogue Agents** — agents acting outside their mandate

AVS's fail-closed design, agent identity, and receipt chain directly address ASI07-ASI10.

### RAILS Paper (June 2026) — The Most Important Paper for AVS

Defines the "agentic clearing problem" with 7 primitives:

| RAILS Primitive | AVS Mapping |
|-----------------|-------------|
| Obligation Object | ActionRequest |
| Evidence Envelope | ASR-1 Receipt |
| Verification Mesh | Receipt.verify() + chain.verify() |
| Clearing Decision | ALLOW/DENY/REQUIRE_APPROVAL/QUARANTINE |
| Settlement Instruction | Execution outcome |
| Clearing Passport | AgentIdentity |
| Finality Rules | Policy engine |

**This is AVS's architectural blueprint.** RAILS provides the theory; AVS is the implementation. No existing project fills the clearing layer gap.

### IETF / W3C / NIST Standards Work

| Body | Activity | Status |
|------|----------|--------|
| IETF | WIMSE working group — AI agent identity draft | Active |
| W3C | Agent Identity Community Group (launched Apr 2026) | Active |
| NIST | AI Agent Standards Initiative (Feb 2026) | Active |

**Implication:** AVS should build on WIMSE/SPIFFE for identity. Align with NIST direction. The window for ASR-1 to become a de facto standard is 12-18 months before formal standards emerge.

### x402 Foundation (April 2026)

Linux Foundation. Premier members: Google, Stripe, Visa, Mastercard, Amazon. 119M+ transactions on Base.

**AVS implication:** x402 is the default HTTP-native payment rail. AVS should treat it as the primary integration target for v0.4+. Consider Foundation membership to participate in governance.

---

## Part 3: The Vertical Opportunity Map

### P1: African PropTech — ATTACK FIRST

| Factor | Detail |
|--------|--------|
| Market | $4B (2025), 16.1% CAGR |
| Fraud | 27%+ tenant arrears, AI-powered scams, phantom listings |
| Regulation | Ghana REAC, SA PPRA, POPIA |
| AVS Fit | **HIGH** — founder expertise, identity verification, trust deficit |
| GTM | **EASY** — TrustNamba/PropertyFlow as beachhead |

**Why now:** Rental fraud epidemic, regulatory tailwinds, emerging market willingness to adopt new standards.

### P2: Insurance Claims — EXPAND NEXT

| Factor | Detail |
|--------|--------|
| Market | $63B AI insurance by 2032 |
| Adoption | 80% piloting, only 4% trust agentic AI |
| Regulation | NAIC Model Bulletin (2 dozen+ states) |
| AVS Fit | **HIGH** — governance before claims processing, evidence trail |
| GTM | **MEDIUM** — longer sales cycles, compliance requirements |

**Why now:** NAIC mandates governance. Deepfake fraud exploding (42% of insurers report AI-generated fraud). AVS can encode risk controls as operational policy.

### P2: Healthcare — EXPAND NEXT

| Factor | Detail |
|--------|--------|
| Market | $148B AI health by 2032 |
| Regulation | 2025 HIPAA Security Rule amendments — encryption now mandatory |
| AVS Fit | **HIGH** — PHI protection, agent identity, audit trail |
| GTM | **HARD** — HIPAA compliance, long procurement cycles |

**Why now:** HIPAA amendments create urgent compliance need. "System prompts are not HIPAA access controls." Only data-layer enforcement satisfies auditors.

### P3: Financial Services — SCALE INTO

| Factor | Detail |
|--------|--------|
| Market | $6.5B by 2035 |
| Regulation | EU AI Act (€35M penalties), MiCA, DORA |
| AVS Fit | HIGH — but crowded market |
| GTM | HARD — banks move slowly |

### P3: Customer Service — SCALE INTO

Easy GTM (Zendesk/ServiceNow integrations), EU AI Act high-risk for refund agents.

### P4: Supply Chain / DevOps — PARTNER INTO

Strategic positioning. Partner with existing players rather than direct sales.

---

## Part 4: Hidden Aspects Not Thought Of

### Hidden 1: The Receipt Standards Race is Already On

Pipelock is actively pursuing IETF/OASIS standardization. CertNode has legally-structured receipts (FRE 902). Aletheia Core has runtime-enforced receipts. AVS's ASR-1 is NOT the only receipt format in play.

**Window: 12-18 months** before a standard emerges. If AVS doesn't ship ASR-1 publicly and start standards engagement now, it risks being a follower, not a leader.

### Hidden 2: Microsoft is Seeking to Move AGT to a Foundation

Microsoft explicitly states aspiration to move the Agent Governance Toolkit into a foundation for community governance. If this happens, AGT becomes the "Kubernetes of agent governance" — the default that everyone builds on.

**Implication:** AVS should either integrate with AGT (consume its Decision BOM, provide clearing layer) or differentiate sharply on scope (AVS = all actions, not just policies).

### Hidden 3: The "Admission Controller" Term is Unclaimed

No competitor has claimed "agent admission controller" as their category name. Kubernetes developers immediately understand this concept. It is a stronger, more specific category than "runtime permission layer."

**Recommendation:** Own this term before Prefactor, Cerbos, or Microsoft does.

### Hidden 4: BVNK Mastercard Acquisition = $1.8B Validation

Mastercard acquiring BVNK for up to $1.8B signals that stablecoin settlement is going mainstream. This creates downstream demand for governance — every stablecoin payment needs a permission check.

### Hidden 5: EU MiCA + UK Stablecoin Rules = Jurisdiction-Aware Policy Demand

Regulatory uncertainty increases demand for configurable policy. AVS should not hardcode one legal interpretation. Jurisdiction-aware policy packs are a product opportunity.

### Hidden 6: The MCP Security Gap is 66% Uncovered

MCPSHIELD shows no single defense covers more than 34% of MCP attack vectors. The remaining 66% is unaddressed. AVS MCP Tool Guard could claim this gap.

### Hidden 7: PropertyFlow/TrustNamba is AVS's Real Differentiator

Every competitor builds horizontal infrastructure. AVS has a real-world vertical (African property/identity) where agent governance is not theoretical — it prevents fraud, saves money, and creates trust. This is a moat that horizontal competitors cannot copy.

### Hidden 8: The Three-Moment Framework is Validated by Multiple Papers

The "before/during/after" action framework maps to:
- RAILS: Obligation → Evidence → Clearing
- x402 paper: Authorization → Binding → Settlement
- ACP paper: Admission → Execution → Receipt

AVS owns "before" (strong) and "after" (strong). The "during" gap (budget reservation, settlement capacity check, two-phase commit) is the v0.4 opportunity.

---

## Part 5: Strategic Recommendations

### Immediate (This Week)

1. **Post Show HN** — point to v0.3.5 release
2. **Email 3 design partners** — mention v0.3.6 branch as preview
3. **Ship ASR-1 spec publicly** — publish docs/ASR_1_RECEIPT_STANDARD.md, even as draft

### Short-Term (Next 2 Weeks)

4. **Own "Agent Admission Controller"** — add to README, positioning docs, Show HN
5. **Verify v0.3.6 on Windows** — your verification, fix any issues
6. **Start TypeScript verifier** — even minimal, to show cross-language commitment
7. **Research Pipelock standardization path** — what IETF/OASIS working group? How to engage?

### Medium-Term (Next Month)

8. **MCP Tool Guard concept** — document the interface, not code. Post as RFC.
9. **Partner outreach to x402 Foundation** — express interest in governance integration
10. **PropertyFlow/TrustNamba integration concept** — show AVS preventing property fraud
11. **Merge v0.3.6 when** — 2+ design partners validate receipt format, tests pass

### Long-Term (3-6 Months)

12. **Standards engagement** — IETF WIMSE, W3C Agent Identity CG, or OASIS
13. **Multi-language verifier** — TypeScript + Rust minimum
14. **v0.4 roadmap** — Payment Guard + MCP Guard, documented not coded
15. **Enterprise add-ons** — only when design partners ask for them

---

## The Bottom Line

The market is converging on AVS's thesis from multiple directions:
- **Payment protocols** validate that agents need financial infrastructure
- **Security papers** validate that optimistic execution is dangerous
- **Academic research** validates the clearing/evidence layer
- **Competitors** validate that this is a real category
- **Regulators** validate that governance is becoming mandatory

AVS is positioned at the intersection. The risk is not that the market doesn't exist. The risk is that competitors define the category first.

The move: **Ship, position, and standardize faster than the field.**

---

> **Every agent action gets a receipt.**
>
> AVS Gateway — Agent Admission Controller for Autonomous Systems
