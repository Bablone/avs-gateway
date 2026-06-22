# Why AVS Exists Now

**A Founder Thesis on Governed Execution for the Agentic Economy**

*Internal Use  Investor Conversations  Design Partner Discussions*
*June 2026*

---

## 1. The Transition

The world is undergoing a structural shift in who interacts with software.

**From:** Humans using software tools directly  clicking buttons, filling forms, reviewing outputs, making decisions.

**To:** Agents using tools on behalf of humans  proposing actions, calling APIs, moving money, deploying code, screening tenants, processing claims  at machine speed and machine scale.

This transition creates a new missing layer in the technology stack. It is not intelligence  large language models handle that, and intelligence is now a commodity (DeepSeek V4-Flash delivers frontier capability at $0.28 per million output tokens, a ~600,000x price decline in six years). It is not wallets  payment rails are being built for agents as we speak. It is not checkout  commerce protocols exist. It is not monitoring  observability platforms trace and log.

The missing layer is **governed execution**: a system that decides whether an agent's proposed action should happen *before* it happens, produces verifiable evidence of that decision, and maintains a trust record over time.

Every action an agent takes is a delegation. Every delegation needs verification. Currently, that verification is manual, ad hoc, or absent entirely. AVS exists to make it automated, cryptographic, and scalable.

---

## 2. Why Now (Market Timing)

The moment is not theoretical. The infrastructure convergence is happening in mid-2026, and it is measurable:

| Signal | Date | What It Means |
|--------|------|---------------|
| **Mastercard AP4M** | June 2026 | 30+ partners building machine-to-machine payments. Payment rails for agents are now operational infrastructure, not research. |
| **AWS AgentCore Payments** | May 2026 | Agents transacting autonomously with Coinbase and Stripe. The largest cloud provider is embedding agent payments into its stack. |
| **Google Pay.sh** | May 2026 | Agents paying per API request. Pay-as-you-go agent economics requires per-action verification. |
| **x402 security paper** | May 2026 | 97.76% information leakage rate proves optimistic execution is dangerously insecure. Fail-open agent architectures are not viable. |
| **RAILS paper** | June 2026 | "Payment is not clearing" demonstrates that payment protocols alone cannot verify agent authority. An evidence layer is required between intent and settlement. |
| **OWASP Agentic AI Top 10** | 2026 | Agent actions recognized as a distinct security problem category, separate from traditional application security. |
| **Circle Nanopayments** | April 2026 | $0.000001 payments on 11 chains. Agent micro-transactions are now economically viable at scale. |
| **Admission-control papers** | 2026 | Multiple academic papers (UC Berkeley, Stanford, CMU) validate intercept-before-execute as the correct architecture for agent governance. |

**The pattern:** 2025 created protocols (MCP, A2A, payment standards). 2026 turned those protocols into operational infrastructure. The control layer  the system that intercepts agent actions before they reach tools, APIs, files, and payment rails  is the obvious next gap.

We are not building ahead of the market. We are building at the exact moment the market proves it needs us.

---

## 3. The Problem

Companies want autonomous agents. They do not want autonomous damage.

When an agent can:

- Delete production files
- Call external APIs with customer data
- Deploy code to production environments
- Query sensitive databases
- Send emails to clients
- Initiate payment transfers
- Process insurance claims
- Screen rental tenants
- Update legal documents
- Modify access controls

Every action has consequences. Some are reversible. Many are not. A payment sent cannot be unsent. An email delivered cannot be undelivered. A tenant denied housing based on an agent's screening cannot have that decision erased.

Someone  something  must decide whether the action should happen *before* it happens.

Currently, that decision is made by one of three inadequate mechanisms:

1. **Human review.** An engineer reviews agent outputs at the end of the day. At 50,000 actions per day, human review covers less than 0.1% of activity. It is governance theater, not governance.

2. **Prompt engineering.** "Please be careful" instructions to the model. This is not enforcement. It is a request, and requests can be ignored, hallucinated, or jailbroken.

3. **Post-hoc logging.** Recording what happened after it happened. Useful for investigation. Useless for prevention. The damage is already done.

What is needed is **interception, evaluation, and decision before execution**. Not after. Not alongside. Before.

---

## 4. The Solution

AVS Gateway is a runtime permission layer that intercepts agent actions before execution, evaluates them against policy, risk, trust, and identity signals, and produces a verifiable receipt of the decision.

The core loop:

```
Agent proposes action
        |
        v
   AVS intercepts          (adapter normalizes action)
        |
        v
   AVS evaluates          (policy + risk + trust + identity)
        |
        v
   AVS decides            (ALLOW / DENY / REQUIRE_APPROVAL / QUARANTINE)
        |
        v
   Receipt created        (Ed25519-signed, hash-linked, portable)
        |
        v
   Action executes        (if ALLOWED) or is blocked (if DENIED)
```

**The four decisions:**

| Decision | Meaning | Applied When |
|----------|---------|--------------|
| **ALLOW** | Action proceeds | Low risk, within policy, trusted agent |
| **DENY** | Action blocked | Violates policy, exceeds risk threshold, critical risk |
| **REQUIRE_APPROVAL** | Escalated to human | Medium risk, policy mandates human review, untrusted agent |
| **QUARANTINE** | Isolated for review | Unknown risk, anomalous pattern, new tool first seen |

**The evidence:** Every decision produces an ASR-1 (Agent Security Receipt) containing:

- Agent identity and version
- Tool manifest (what tool, what operation, what parameters)
- Policy decision with matched rule name
- Risk score (0-100, with classification)
- Trust score (time-weighted agent behavior history)
- Receipt hash (SHA-256 of canonical decision record)
- Chain link (hash of previous receipt in the audit chain)
- Cryptographic signature (Ed25519, verifiable offline)

This is not a log line. It is structured proof. Portable, verifiable, admissible.

---

## 5. Why This Approach Wins

**Fail-closed design.** Any error in the gateway  policy engine crash, risk scorer timeout, signing key failure, validation exception  results in DENY. The system defaults to safe. This is the architectural answer to the x402 paper's finding that optimistic execution leaks 97.76% of sensitive information. AVS does not trust by default. It distrusts by default and requires explicit evidence to allow.

**Framework-agnostic.** One Python decorator (`@governed_tool`) wraps any function, any framework, any agent. No rewrites required. LangChain, OpenAI Agents SDK, Google ADK, CrewAI, AutoGen, custom agents  all route through the same gateway. The adapter layer normalizes every action into a canonical `ActionRequest`. The gateway does not care which framework proposed the action. It cares whether the action should be allowed.

**Local-first.** No cloud dependency. No API keys. No external service required. The gateway runs on the same machine as the agent. Receipts are stored locally. The customer controls when  or whether  to export or share evidence. This matters for: air-gapped environments, regulated data, offline operation, and customers who do not want their agent actions flowing through a third-party SaaS.

**Receipt-first.** Every decision creates a portable, verifiable evidence object. Not a log line in a proprietary format. A structured, signed, hash-linked receipt that can be exported, audited, presented to regulators, used in dispute resolution, and verified by anyone with the public key. The receipt format (ASR-1) is open and documented. The verifier is open source.

**Open core.** The gateway (Apache 2.0), the ASR-1 schema, the receipt verifier, and basic policy packs are free and open source. This drives adoption, builds trust, creates a standard, and establishes AVS as the default governance layer. Commercial revenue comes from enterprise add-ons: hosted dashboards, advanced policy packs, approval workflows, audit exports, SIEM integration, and compliance reporting.

---

## 6. The Market

**The buying trigger:**

> "We need our agents to act autonomously, but we cannot let them freely touch production systems, customer data, payment APIs, or external tools without some form of control."

This sentence describes every team building with agents in 2026. The moment they move from demo to production, they feel this problem.

**Target buyers:**

| Role | Pain | Where AVS Fits |
|------|------|----------------|
| **CTO / founder of AI agent startup** | Client asks "how do we know your agent is safeWARNING" | Signed evidence bundle + trust score |
| **Head of AI platform** | Too many agents with too much access | Policy-based gating + audit trail |
| **Security / platform engineer** | Shadow AI agents operating unsupervised | Discovery + interception of all agent actions |
| **Enterprise innovation team** | Compliance needs evidence of AI oversight | Tamper-proof receipts + redacted reports |
| **DevOps / software factory team** | Coding agents touching production | Proof-gated execution before deploy |

**Budget sources:** AI platform budget, security budget, compliance/GRC budget, DevOps/platform engineering budget. AVS can be sold into any of these four budget lines, which matters when AI platform budgets are new and compliance budgets are old.

**Market size direction:** AI governance spend projected at $5.6-7.4B by 2030 (34-51% CAGR). Agent accountability is an emerging sub-category with no established vendor. Directional TAM: $5-10B by 2030 based on analogies to cloud observability growth and AI governance adoption curves.

---

## 7. The Competition

| Competitor | Their Wedge | AVS Differentiation |
|-----------|-------------|---------------------|
| **Catena** | Payment control plane for agent transactions | AVS governs all actions (files, APIs, deployments, data), not just payments. Payment is one action type among many. |
| **LangSmith / Langfuse** | Observability and tracing for LLM calls | AVS controls before execute. Observability records after execute. Prevention beats detection. |
| **Guardrails AI** | Output validation (text quality, format checking) | AVS governs runtime execution (should this action happenWARNING), not text output (is this text well-formedWARNING). |
| **OPA / Cedar** | Policy engines (evaluate rules, return decisions) | AVS adds action normalization, framework adapters, signed receipts, approval workflows, and trust scoring. OPA evaluates rules. AVS governs agents. |
| **Emerging security startups** | Agent runtime protection (input defense, prompt injection) | AVS is open source, portable, receipt-compatible, and framework-agnostic. Closed security stacks create vendor lock-in that AVS avoids. |

No competitor provides the combination of: interception, normalization, policy evaluation, risk scoring, trust scoring, four-way decision, signed receipt generation, and framework-agnostic operation. Each competitor does one piece. AVS does the full loop.

---

## 8. The Moat

The moat is not the code. The code is a Python gateway that a competent engineer could replicate in a month. The moat is what accumulates around the code:

1. **Receipt vocabulary (ASR-1 schema + verifier + examples).** The more organizations that use ASR-1 receipts, the more the format becomes a standard. Competitors must support ASR-1 to interoperate. Format dominance creates the same lock-in that PDF, JSON, and JWT enjoy.

2. **Adapter surface area.** Each framework adapter (LangChain, MCP, OpenAI Agents SDK, Google ADK, CrewAI, custom) represents integration work that compounds. A competitor starting from zero must build all adapters to achieve parity.

3. **Policy library.** Domain-specific policy packs (financial services, healthcare, property management, DevOps) accumulate domain knowledge that is non-transferable. A policy that correctly governs tenant screening in property management is worthless in payment processing.

4. **Approval and audit workflows.** The enterprise process layer  routing approval requests to the right humans, maintaining audit trails, generating compliance exports, integrating with SIEM  is sticky. Organizations build processes around these workflows. Switching means rebuilding process, not just swapping code.

5. **Trust graph over time.** As AVS records agent behavior, it builds a time-weighted trust history for each agent. This learned pattern data  which agents are reliable, which tools they use well, what risk profiles look like in practice  becomes more valuable the longer it accumulates. A competitor with no history cannot offer comparable trust scoring.

6. **Vertical proof.** TrustNamba and PropertyFlow provide a real-world vertical where agent governance is not theoretical. Tenant screening, landlord verification, payment authorization, and dispute evidence are live use cases that produce case studies, testimonials, and reference customers.

The moat strengthens with time, adoption, and evidence depth. It is not a single barrier. It is six interlocking barriers that compound.

---

## 9. The Business Model

Open core, commercial expansion:

| Tier | Price | What You Get |
|------|-------|-------------|
| **Free / Open Source** | $0 | Gateway SDK, CLI, local deployment, basic policies, ASR-1 format, community support |
| **Pro / Team** | $20-50/seat/month | Hosted dashboard, shared policy library, approval workflow, Slack/email alerts, audit export |
| **Enterprise** | Annual contract | Self-hosted deployment, SSO/RBAC, domain-specific policy packs, SIEM integration, compliance exports (SOC 2, GDPR, PCI evidence) |
| **Vertical Solutions** | Per-vertical pricing | Agentic software factories, agentic payments, property/identity verification, regulated API access |

The value metric is not tokens processed. It is **verified actions**  the number of agent actions that passed through AVS governance and produced a receipt. This aligns pricing with the value delivered: trust, not compute.

---

## 10. The Stack

The future architecture of the agentic economy:

```
Model Layer          (OpenAI, Anthropic, DeepSeek, Google  intelligence)
      |
      v
Agent Framework      (LangChain, OpenAI SDK, Google ADK, CrewAI  orchestration)
      |
      v
  AVS Gateway        (interception, evaluation, decision, receipt  GOVERNANCE)
      |
      v
Tool / Payment Rail  (APIs, databases, files, Stripe, Visa, Mastercard  execution)
      |
      v
ASR-1 Receipt        (portable, signed, verifiable evidence  PROOF)
      |
      v
Clearing / Dispute   (audit, compliance, dispute resolution, regulatory review)
```

AVS sits between the agent and the world. It governs before money moves, before files change, before code deploys, before data is queried, before emails are sent. It proves after the decision. Payment protocols, observability systems, and compliance frameworks are downstream from AVS. AVS is the control point.

---

## 11. Why This Team

The founder has deep domain expertise in property, identity, and verification systems in African markets. This is not abstract. TrustNamba and PropertyFlow are live products where agent governance is not a nice-to-have  it is a requirement:

- **Tenant screening:** An agent evaluates a rental applicant. The decision affects housing access and legal compliance. Who authorized this screeningWARNING What criteria were appliedWARNING Can we prove the decision was fairWARNING
- **Landlord verification:** An agent confirms a landlord's identity and property ownership. Getting this wrong enables fraud. The receipt proves the verification happened and the evidence was intact.
- **Payment authorization:** An agent initiates rent collection. The payment must be within the tenant's authorized mandate. The receipt links the payment to the authorization.
- **Dispute evidence:** A tenant disputes a decision. The ASR-1 receipt provides the cryptographically signed evidence chain that proves what the agent did, why it did it, and who authorized it.

This vertical gives AVS three things most infrastructure startups lack: a live use case with real users, a regulatory environment where proof matters, and a customer who needs governance today  not in some hypothetical future.

The team understands both the technical problem (how do you intercept and evaluate agent actionsWARNING) and the human problem (how do you prove to a regulator, a judge, or a customer that an agent's decision was legitimateWARNING). Technical depth plus domain specificity is the combination that builds infrastructure companies.

---

## 12. The Ask

We are looking for three things right now:

1. **Three design partners** building with agents who need tool governance. We want teams that feel the problem today  agents touching production systems, payment APIs, customer data, or external tools  and want to be early users of governed execution. Design partners get free access, direct input on the product roadmap, and co-branding on case studies.

2. **Feedback on the ASR-1 receipt format.** We have published the schema and the verifier. We want security engineers, compliance officers, and infrastructure architects to review it, challenge it, and help us make it the standard for agent accountability evidence.

3. **Contributors to framework adapters.** We need engineers who know LangChain, MCP (Model Context Protocol), OpenAI Agents SDK, Google ADK, and CrewAI to build and maintain the adapter layer that makes AVS framework-agnostic.

**We are not looking for:**

- Investment yet. It is too early. We want product-market fit signals first.
- Enterprise sales. The product is not ready for procurement cycles.
- Standards body submissions. We need users before we seek standardization.

The sequence is: design partners  product feedback  iterate  open source adoption  commercial pilots  investment. Not the reverse.

---

## Closing

The agentic economy has a missing layer. Intelligence is abundant. Payment rails are operational. Observability exists. But the moment an agent proposes an action that affects the world  a file write, a payment, a deployment, a database query  there is no systematic, verifiable, scalable mechanism to decide whether that action should proceed.

That is the layer AVS builds.

Not after the fact. Not alongside. Before.

The evidence is in the market signals. The architecture is in the code. The need is in every production agent deployment that operates without governance.

If you are building with agents and feel this gap, we want to talk.

---

*Verification before delegation.*
*Evidence before autonomy.*
*Accountability before scale.*

**AVS  The Proof-Gated Action Layer**
