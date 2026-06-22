# AVS Strategic Positioning: Agentic Payments 2026

**Document Type:** Internal Strategy
**Classification:** Confidential -- Positioning Reasoning for Roadmap and Investor Communications
**Date:** June 2026
**Purpose:** Preserve positioning reasoning so future roadmap decisions and investor language do not drift. This document is not public-facing.

---

## 1. Executive Summary

### Locked Positioning

**AVS is the proof-gated action layer for autonomous agents.**

The agentic economy requires more than payment rails. It requires a layer that decides whether an autonomous agent should be permitted to act at all -- before value moves, before state mutates, before consequences become irreversible. That layer is AVS.

**The core insight:** Payment rails move value. AVS governs whether value-moving actions should happen. This is not a subtle distinction. Every payment rail in the market -- Stripe, Mastercard AP4M, Circle nanopayments, Solana Pay.sh -- assumes the decision to pay has already been made. AVS sits upstream of that decision. We do not compete with rails. We make rails safe to use.

**The future stack is not model → wallet.**

The naive architecture treats the LLM as the decision-maker and the wallet as the execution point. This is dangerous and incomplete. The correct stack:

```
Model → Agent → AVS → Tool / Payment Rail → Receipt → Clearing
```

Each arrow represents a trust boundary. AVS is the gate at the most critical boundary: the point where intent becomes irrevocable action.

**Catena is the payment control plane. AVS is the action control plane.**

Catena governs money movement: identity, policy, approvals, spending limits, auditability for financial transactions. This is a real and defensible market position. AVS governs all autonomous consequences -- payments, yes, but also database writes, API calls, infrastructure mutations, code deployments, and any other action an agent might take that changes the state of the world. AVS has broader scope. Catena has deeper payment-specific features. Both can coexist; neither replaces the other.

---

## 2. Corrected Timeline: Protocols 2025, Operational Rails 2026

The agentic payment market evolved in two distinct phases. Recognizing this pattern is essential for predicting where AVS fits and where the competitive threats actually lie.

### Phase 1: Protocol Definition (2025)

The first phase was about standards -- agreements on how agents should identify themselves, request authorization, and communicate intent to merchants and payment processors.

| Date | Event | Significance |
|------|-------|-------------|
| **September 2025** | **Google AP2 (Agent Payments Protocol)** | Mandates explicit user authorization before agent-initiated purchases. Establishes that the agent cannot act as a fully autonomous purchaser without human consent. This validates the need for an admission-control layer upstream of payment. |
| **October 2025** | **Visa TAP (Trusted Agent Protocol)** | Introduces agent identity verification for merchants. Agents must present cryptographically verifiable credentials proving they are authorized to act on behalf of a user. Creates the identity fabric but does not solve the action-governance problem. |
| **Late 2025** | **Stripe / OpenAI / Meta ACP (Agentic Commerce Protocol)** | Standardizes the checkout flow for agents: discovery, negotiation, authorization, execution. ACP is a merchant-facing protocol. It handles how the merchant receives and processes an agent's payment request. It does not handle whether the agent should have made the request. |

These three protocols collectively established that agent payments require new infrastructure. But they are all protocols -- agreements on message formats, credential types, and handshake sequences. They are not operational systems.

### Phase 2: Operational Infrastructure (2026)

The second phase saw real infrastructure come online -- systems that process actual transactions at scale.

| Date | Event | Significance |
|------|-------|-------------|
| **April 2026** | **Circle Nanopayments → mainnet** | Gas-free USDC transfers across 11 chains. Removes the cost barrier for micro-transactions. Enables agent-to-agent and agent-to-machine payments at sub-cent scale. This is a rail -- it moves money cheaply. It does not decide whether the money should move. |
| **May 2026** | **Solana + Google Pay.sh** | API-per-request payment model. Developers can charge per API call using Solana's settlement layer. Creates a transactional mesh where every agent action can have an attached cost. Again: a rail, not a governance layer. |
| **May 2026** | **AWS AgentCore Payments** | Coinbase + Stripe partnership integrated into AWS's agent hosting platform. Enterprise-grade payment plumbing for agents deployed on AWS. Validates that the major cloud providers treat agent payments as first-class infrastructure. |
| **June 2026** | **Mastercard AP4M** | The most significant operational launch. Guaranteed multi-rail settlement with 30+ partners. Combines traditional card rails, blockchain settlement, and real-time payment networks into a single abstraction for machine payments. See Section 3 for full analysis. |

### Pattern Recognition

The market matured organically: protocols first, then operational rails. This is a familiar pattern:

- **TCP/IP (protocol) → Cisco routers (infrastructure)**
- **HTTP (protocol) → AWS / Cloudflare (infrastructure)**
- **AP2/TAP/ACP (protocols) → AP4M / Circle / Pay.sh (infrastructure)**

The protocol phase proved the need. The operational phase proved the economics. What neither phase addresses is the governance question: **should this action happen at all?**

That is AVS's position. The market has built the roads. AVS builds the traffic lights, stop signs, and inspection stations.

---

## 3. Mastercard AP4M Analysis

### What It Is

Mastercard AP4M (Agent Payments for Machines) is a guaranteed multi-rail settlement network designed specifically for machine-to-machine and agent-initiated payments. It abstracts multiple settlement layers -- traditional card networks, blockchain networks, real-time payment systems -- behind a single API, so that an agent can initiate a payment without knowing or caring which rail will ultimately carry the funds.

### Partner Ecosystem

The partner list reveals Mastercard's strategy: cover every layer of the payment stack.

| Partner | Role | Why They Matter |
|---------|------|----------------|
| **Aave** | DeFi lending / liquidity | On-chain credit and yield-bearing settlement |
| **Adyen** | Merchant acquiring | Global merchant acceptance infrastructure |
| **Alchemy** | Blockchain infrastructure | Node access and RPC for multi-chain operations |
| **Anchorage** | Institutional custody | Qualified custody for digital asset settlement |
| **BVNK** | Banking-as-a-service | Fiat on/off ramps for agent wallets |
| **Checkout.com** | Payment processing | Alternative processor to Stripe for global coverage |
| **Cloudflare** | Edge security | DDoS protection and edge-verified identity (potential AVS parallel) |
| **Coinbase** | Exchange / custody / Base L2 | USDC issuance, Base chain, institutional custody |
| **MoonPay** | Fiat on-ramp | Consumer and agent wallet funding |
| **OKX** | Exchange | Alternative venue for digital asset settlement |
| **Polygon** | L2 scaling | Low-cost EVM settlement for micro-payments |
| **Ripple** | Cross-border / RLUSD | International settlement and stablecoin rails |
| **Solana** | High-throughput L1 | Sub-second finality for high-frequency agent payments |
| **Stripe** | Payment processing | Dominant developer-facing payment APIs |
| **Turnkey** | Key management | Secure key custody for agent wallets |
| **Utila** | Wallet infrastructure | MPC wallets for institutional agent operations |
| *(30+ total partners)* | | Full coverage of identity, custody, rails, and settlement |

### Why It Matters

AP4M proves three things:

1. **Institutional trust fabric is real.** Mastercard has assembled a coalition of regulated, trusted entities to handle machine payments. This is not a speculative DeFi experiment. It is institutional-grade infrastructure.

2. **Credentialing + permissioning + controls are required.** AP4M includes identity verification, spending controls, and audit trails. Mastercard understands that agent payments need governance, not just rails.

3. **Multi-rail is the correct abstraction.** No single payment rail serves all agent use cases. AP4M's abstraction lets agents pay without choosing rails. This is the right architecture for a heterogeneous payment landscape.

### Why AP4M Does NOT Compete with AVS

This is the critical positioning distinction:

| Dimension | Mastercard AP4M | AVS |
|-----------|----------------|-----|
| **Primary function** | Moves money | Decides whether action should happen |
| **Scope** | Payments only | All autonomous actions (payments, DB writes, API calls, deployments) |
| **Position in stack** | Rail layer (execution) | Governance layer (admission control) |
| **Value proposition** | Guaranteed settlement | Proof-gated admission |
| **Question it answers** | "How do we pay?" | "Should we allow this action?" |

AP4M handles money movement. AVS handles action governance. AP4M ensures the payment completes. AVS ensures the payment should have been initiated. These are complementary functions, not overlapping ones.

In the future stack:

```
Model → Agent → AVS [should this happen?] → AP4M [execute payment] → Receipt → Clearing
```

AP4M is a potential integration target for AVS, not a competitor.

---

## 4. Catena Threat and AVS Differentiation

### Catena's Position

Catena is a participant in Mastercard AP4M. Their stated positioning:

> "The control plane: identity, policy, approvals, spending limits, auditability wherever agents move money."

This is the most direct competitive threat to AVS in the market today. Catena is not a payment rail. It is explicitly a control layer for agent payments. It overlaps with AVS in the admission-control function.

### The Competitive Overlap

| Capability | Catena | AVS v0.3.6 |
|------------|--------|------------|
| Identity verification | Yes (SPIFFE/OIDC integration) | Yes (agent identity via Agent Cards) |
| Policy enforcement | Yes (spending limits, merchant allowlists) | Yes (action policies, tool binding) |
| Approval workflows | Yes (multi-step approvals) | Yes (quarantine + human review) |
| Audit trail | Yes (transaction logging) | Yes (tamper-evident receipts) |
| Spending controls | Yes (budgets, limits) | Partial (budget tracking via v0.4) |
| **Scope** | **Payments only** | **All autonomous actions** |
| **Receipt system** | Transaction logs | Cryptographic ASR-1 receipts |
| **Academic validation** | None | RAILS paper + x402 vulnerability research |

### AVS Differentiation: Sharp Wedge

The distinction must be stated with absolute clarity:

> **Catena asks: "Should this agent move money?"**
> **AVS asks: "Should this agent be allowed to mutate the world?"**

This is not marketing language. It is an architectural truth.

Catena's scope is bounded to financial transactions. It governs wallets, budgets, merchant lists, and spending policies. This is valuable and defensible work. But it is a subset of the autonomous-action problem.

AVS governs every action an agent might take that has consequences:
- **Payments** (same as Catena)
- **Database writes** (data corruption, PII exposure)
- **API calls** (rate limit abuse, unauthorized endpoints)
- **Infrastructure mutations** (resource exhaustion, misconfigurations)
- **Code deployments** (supply chain attacks, bad releases)
- **File system operations** (data loss, unauthorized access)
- **Message sending** (social engineering, information leakage)

The payment-control market is a segment of the action-control market. Catena can expand into broader action governance, but that expansion requires fundamental architectural changes -- changes AVS has already made.

### Coexistence Scenario

The most likely market outcome is coexistence:

```
Model → Agent → AVS [general action governance] → Catena [payment-specific controls] → AP4M [settlement] → Receipt → Clearing
```

AVS handles the "should this action happen?" decision. For actions classified as payments, AVS delegates payment-specific controls (budget limits, merchant verification) to Catena. Catena returns a payment authorization decision. AVS incorporates that decision into its overall action verdict.

This is the Kubernetes model: AVS is the admission controller; Catena is a validating webhook for payment actions.

### The Competitive Risk

The primary risk is that Catena expands its scope beyond payments to become a general action-control layer. This would require:

1. **Action type generalization:** Moving from payment-specific policies to arbitrary action policies
2. **Tool binding:** Integrating with non-payment tools and APIs
3. **Receipt generalization:** Creating tamper-evident receipts for non-financial actions
4. **Academic credibility:** Publishing or adopting research validating general action governance

AVS mitigates this risk by:
- Maintaining category leadership in the "proof-of-action" space
- Publishing and engaging with academic research (RAILS paper, x402 analysis)
- Building the v0.4 payment-aware features before Catena can generalize
- Establishing developer mindshare as the "admission controller for agents"

---

## 5. x402 Vulnerabilities and Fail-Closed Validation

### The Paper

**"Free-Riding in the AI Economy"**
- Authors: Researchers from Zhejiang University, City University of Hong Kong, Chinese University of Hong Kong
- Date: May 2026
- Subject: Security analysis of the x402 payment protocol (Coinbase's protocol for AI-to-service payments)

### Key Findings

The paper identifies three classes of vulnerability in x402, each rooted in the same architectural flaw: **the state synchronization gap between synchronous HTTP requests and asynchronous blockchain settlement.**

| Vulnerability | Attack Vector | Leakage Rate | Root Cause |
|---------------|---------------|--------------|------------|
| **Allowance overdraft** | 50 concurrent requests against a single allowance | **97.76%** | Race condition: multiple requests read the same allowance state before any write completes |
| **Denial of settlement** | Rate limit abuse preventing settlement tx from landing on-chain | **100%** | HTTP response is synchronous; settlement is async. Attacker gets service; settlement never completes |
| **Service duplication** | Race conditions in multi-step payment flows | **~6% success** (legitimate), rest fail or duplicate | Lack of atomicity across payment steps |

### The Root Cause

x402 operates on a simple model: the client (agent) sends a payment authorization with an HTTP request; the server validates the authorization and provides the service; settlement happens later on the blockchain.

The gap between millisecond-scale HTTP responses and second-scale (or minute-scale, on congested chains) blockchain settlement creates a fundamental race condition. The server must decide whether to provide service *before* knowing whether the payment will actually settle.

This is not a bug in x402's implementation. It is a structural limitation of any protocol that separates authorization from settlement across different time scales and consistency models.

### x402's Mitigation Proposals

The paper proposes six categories of mitigation:

1. **Request-bound signatures:** Each request carries a unique signature tied to that specific request, preventing replay attacks.

2. **Stateful nonce linearization:** Maintaining a nonce sequence to prevent concurrent requests from reading stale state.

3. **Pessimistic resource delivery:** Do not provide service until settlement is confirmed. This eliminates free-riding but introduces latency that may be unacceptable for real-time services.

4. **Two-phase locking:** Reserve funds in phase one; settle in phase two. Similar to database transaction protocols.

5. **Risk-adaptive authorization:** Dynamically adjust authorization requirements based on perceived risk (amount, client history, service value).

6. **Failure-closed design:** If any part of the authorization/settlement pipeline fails, default to denial. The system must be safe when uncertain.

### Independent Validation of AVS Architecture

The x402 vulnerability paper independently validates AVS's core architectural decisions:

| x402 Vulnerability | AVS Countermeasure | How It Works |
|-------------------|-------------------|--------------|
| Allowance overdraft (race conditions) | **Fail-closed admission control** | AVS decides *before* execution. No race condition because the action is gated synchronously at the admission boundary. |
| Denial of settlement (async gap) | **Receipt-based verification** | AVS requires a receipt for every action. Receipts are verified against expected outcomes. Settlement failures are detected post-action and flagged. |
| Service duplication (lack of atomicity) | **Cryptographic receipt binding** | Each ASR-1 receipt is cryptographically bound to a specific action request. Duplicates are detected via nonce/receipt collision. |
| General state sync gap | **Synchronous admission + async verification** | AVS accepts the reality of the sync/async gap. It handles it with a two-layer approach: synchronous admission control (Before) + asynchronous receipt verification (After). |

### The Paper's Conclusion

> *"The agentic web needs state-aware middleware to manage the gap between millisecond inference and second-level settlement."*

This sentence describes AVS's exact function. AVS is the "state-aware middleware" that bridges the inference/settlement gap by:

1. **Acting synchronously at the admission boundary** (millisecond-scale decision)
2. **Requiring cryptographic receipts** that bind actions to outcomes
3. **Verifying receipts asynchronously** against expected outcomes
4. **Maintaining tamper-evident audit trails** for dispute resolution

The x402 paper is not a critique of AVS. It is independent academic evidence that the problem AVS solves is real, that naive approaches fail catastrophically, and that failure-closed design is the correct architectural response.

---

## 6. RAILS Paper and the Evidence/Clearing Layer

### The Paper's Core Argument

The RAILS paper (Reference Architecture for Intelligent Ledger Settlement) makes a foundational distinction that underpins AVS's entire architecture:

> **"Payment is not clearing. Authorization is not clearing."**

These three concepts -- payment, authorization, and clearing -- are routinely conflated in both traditional finance and crypto. The RAILS paper argues they are distinct processes with different requirements, different time scales, and different trust assumptions.

| Concept | Definition | Time Scale | Trust Model |
|---------|-----------|------------|-------------|
| **Authorization** | Decision that a payment *should* proceed | Milliseconds | Policy-based, synchronous |
| **Payment** | Transfer of payment instructions | Seconds | Network-based, semi-synchronous |
| **Clearing** | Final determination of obligation satisfaction | Minutes to hours | Evidence-based, asynchronous |

Conflating these leads to the exact vulnerabilities the x402 paper documents: systems that assume authorization = payment = clearing, when in reality each is a separate step with separate failure modes.

### RAILS Architectural Components

The paper proposes seven architectural primitives for correct agentic payment processing:

| RAILS Primitive | Description |
|-----------------|-------------|
| **Obligation Object** | A structured representation of what the payer owes the payee: amount, currency, conditions, expiry |
| **Evidence Envelope** | A cryptographically signed container for all evidence related to an obligation: authorization proof, delivery confirmation, settlement reference |
| **Verification Mesh** | A distributed network of verifiers that check evidence against obligations without trusting a single party |
| **Clearing Decision** | The formal determination, based on evidence, that an obligation has been satisfied (or not) |
| **Settlement Instruction** | The command to move funds, issued only after a positive clearing decision |
| **Clearing Passport** | A portable, privacy-preserving credential that proves clearing history without revealing transaction details |
| **Finality Rules** | Explicit, configurable rules defining when a transaction is considered final and irreversible |

### Mapping RAILS to AVS

The RAILS primitives map directly to AVS constructs:

| RAILS Primitive | AVS Construct | Status |
|-----------------|---------------|--------|
| **Obligation Object** | **ActionRequest** | Implemented (v0.3.6) |
| **Evidence Envelope** | **ASR-1 (Agentic System Receipt)** | Implemented (v0.3.6) |
| **Verification Mesh** | **Receipt verification pipeline** | Implemented (v0.3.6) |
| **Clearing Decision** | **Outcome classification (PASS/FAIL/VIOLATION)** | Implemented (v0.3.6) |
| **Settlement Instruction** | *Delegated to payment rail* | Out of scope (by design) |
| **Clearing Passport** | **Agent reputation / historical compliance** | Partial (v0.4.x) |
| **Finality Rules** | **Policy-configurable finality** | Partial (v0.4.x) |

### Academic Legitimacy

The RAILS paper gives AVS independent academic legitimacy for the evidence/clearing layer. AVS was not designed to implement RAILS, but the architectural convergence is striking:

- Both treat **authorization and clearing as separate concerns**
- Both require **cryptographic evidence** for every transaction
- Both use **distributed verification** rather than single-party trust
- Both separate the **decision to act** from the **execution of payment**

This convergence means AVS can credibly claim to implement the RAILS reference architecture for the admission-control and evidence layers. This is a powerful positioning asset in enterprise and regulated markets, where academic validation carries significant weight.

### The Clearing Gap

The one RAILS primitive AVS does not implement is the **Settlement Instruction** -- and this is deliberate. AVS does not move money. It verifies that money-moving actions (and other actions) were properly authorized and produces evidence of the outcome. The actual settlement instruction is delegated to the payment rail (Stripe, AP4M, Circle, etc.).

This is not a missing feature. It is the architectural boundary that keeps AVS neutral and composable with any payment infrastructure.

---

## 7. Three-Moment Framework

Autonomous actions have three temporal phases. AVS's coverage across these phases defines its current capabilities and v0.4 priorities.

### The Framework

| Moment | Time | What Happens | AVS Coverage |
|--------|------|-------------|--------------|
| **Before action** | T-0 | Admission control: allow / deny / approve / quarantine | **Strong** (v0.3.6) |
| **During action** | T+0 to T+n | Locking, budget reservation, tool binding, settlement safety | **Gap** (v0.4.x target) |
| **After action** | T+n | Receipt, verification, clearing, liability, dispute trail | **Strong** (v0.3.6) |

### Before Action (T-0): Admission Control -- STRONG

AVS v0.3.6 provides comprehensive admission control:

- **Policy evaluation:** Action requests are evaluated against configurable policies (tool allowlists, rate limits, resource budgets, time windows)
- **Agent identity verification:** Agent Cards are validated for authenticity and authorization scope
- **Human-in-the-loop:** Quarantine mode holds suspicious actions for human review
- **Synchronous decision:** Verdict (allow / deny / quarantine) is returned before execution begins
- **Audit logging:** Every admission decision is logged with full context

This is AVS's strongest capability. The fail-closed architecture ensures that if any part of the admission pipeline cannot complete its evaluation, the default outcome is denial. This is the exact property the x402 paper identifies as necessary.

### During Action (T+0 to T+n): Active Controls -- GAP

This is AVS's primary gap and the focus of v0.4:

| Gap | Description | v0.4 Mitigation |
|-----|-------------|-----------------|
| **No budget reservation** | AVS approves an action but cannot reserve the budgeted amount during execution. Concurrent actions can exceed budgets via race conditions (same x402 vulnerability). | Reservation/commit semantics: hold budget on approval, release on completion |
| **No tool binding enforcement** | AVS approves action with Tool X, but cannot prevent the agent from calling Tool Y during execution. | Execution context binding: cryptographic linkage between approval and execution |
| **No settlement safety** | AVS approves a payment action but cannot verify that the payment rail is healthy, the merchant is reachable, or settlement is likely to succeed. | Payment rail health checks + merchant verification pre-approval |
| **No during-action monitoring** | Once execution begins, AVS has no visibility until completion. | Streaming execution telemetry (v0.4.x stretch) |

The during-action gap is the vulnerability window. An agent approved for a $10 payment could, in theory, issue 50 concurrent $10 requests before the first one settles. AVS v0.3.6 would approve all 50 (each individually within policy) because it has no reservation mechanism.

### After Action (T+n): Receipt and Verification -- STRONG

AVS v0.3.6 provides comprehensive post-action verification:

- **ASR-1 receipt generation:** Every action produces a cryptographically signed receipt
- **Receipt verification:** Receipts are verified against the original ActionRequest for consistency
- **Outcome classification:** Actions are classified as PASS, FAIL, or VIOLATION
- **Incident linkage:** Violations are linked to incidents for investigation and remediation
- **Compliance trail:** Full audit trail for regulatory and governance requirements
- **Tamper evidence:** Receipts are immutable; any modification is detectable

### v0.4 Priority: Close the During-Action Gap

The during-action gap is the highest-priority item for v0.4 because:

1. It is the only vulnerability window in AVS's coverage
2. It is the exact vulnerability class the x402 paper documents
3. It is where Catena (if it expands) or new competitors will attack
4. It requires fundamental architectural additions, not incremental features

---

## 8. Public Positioning Lines

The following lines are approved for public communications (website, pitch decks, conference talks, documentation). Each line is designed for a specific context and audience.

### Tagline

> **"Every agent action gets a receipt."**

Use: General audience, website hero, conference introductions.
Rationale: Concrete, memorable, defensible. A receipt is a universally understood concept. "Every agent action" establishes scope beyond payments.

### Primary Category

> **"Runtime permission layer for AI agents"**

Use: Investor pitches, category creation, Y Combinator / accelerator applications.
Rationale: "Runtime" distinguishes from design-time or deploy-time policy tools. "Permission layer" is accurate -- AVS grants or denies permission. "For AI agents" is the market.

### Doctrine

> **"Proof-gated action"**

Use: Internal decision-making, architecture discussions, team vocabulary.
Rationale: Short, principled, memorable. Every action must be gated by proof: proof of identity, proof of authorization, proof of policy compliance. This is the core design philosophy.

### Strategic Category

> **"Proof-of-action layer"**

Use: Long-term category creation, academic papers, thought leadership.
Rationale: Elevates AVS from a product to a category. "Proof-of-action" is the conceptual primitive that AVS instantiates. Other systems can be described as "proof-of-action" systems, with AVS as the reference implementation.

### Enterprise Promise

> **"Tamper-evident evidence for autonomous operations"**

Use: Enterprise sales, regulated industry pitches, compliance discussions.
Rationale: "Tamper-evident" is a precise technical claim (not "tamper-proof" -- that would be false). "Evidence" speaks to audit and legal requirements. "Autonomous operations" is the enterprise framing of agent actions.

### Developer Analogy

> **"Admission control for agent actions, like a Kubernetes admission controller"**

Use: Developer documentation, technical blog posts, conference talks.
Rationale: Kubernetes admission controllers are widely understood by the target developer audience. The analogy is architecturally accurate: both intercept requests before execution, apply policies, and can deny or mutate.

### Business Line

> **"Payment rails move value. AVS governs whether value-moving actions should happen."**

Use: Investor pitches, competitive positioning, partnership discussions.
Rationale: Sharp separation from payment infrastructure. Acknowledges the value of rails (they move value) while defining AVS's unique position (upstream governance).

### Category Line

> **"Runtime permission infrastructure for autonomous agents"**

Use: Analyst briefings, market mapping, competitive intelligence.
Rationale: "Infrastructure" signals that AVS is a platform layer, not an application. "Runtime permission" is the precise function. "Autonomous agents" is the market segment.

### The Stack

> **"The future stack is not model → wallet. It is model → agent → AVS → payment/tool rail → receipt → clearing."**

Use: Vision presentations, strategic planning, competitive differentiation.
Rationale: Defines the architectural future AVS is building toward. The "model → wallet" framing describes the naive, dangerous architecture. The corrected stack shows where AVS fits and why it is necessary.

### Usage Guidelines

| Context | Recommended Line |
|---------|-----------------|
| Website hero | "Every agent action gets a receipt." |
| Investor pitch (category) | "Runtime permission layer for AI agents" |
| Investor pitch (vision) | The stack line |
| Enterprise sales | "Tamper-evident evidence for autonomous operations" |
| Developer onboarding | Kubernetes analogy |
| Competitive differentiation | Business line |
| Academic / research | "Proof-of-action layer" |
| Internal team vocabulary | "Proof-gated action" |

---

## 9. v0.4 Roadmap Implications

The strategic positioning in this document directly shapes the v0.4 roadmap. Every feature listed below is justified by a positioning need, competitive threat, or market validation.

### Payment-Aware Policies

**What:** Policies that understand payment semantics: budget limits, merchant allowlists, spending category controls, transaction amount thresholds.

**Why:** Catena's primary differentiation is payment-specific policy controls. AVS v0.4 must match this capability to prevent Catena from owning the payment-control narrative. Mastercard AP4M's launch validates that payment-aware controls are a market requirement.

**Implementation:**
- Policy predicates for `payment.amount`, `payment.merchant`, `payment.currency`, `payment.category`
- Budget envelopes with time windows (per-agent, per-merchant, per-category)
- Merchant reputation scoring integration

### ActionType.PAYMENT

**What:** A dedicated action type for payment actions, distinct from generic API calls or tool invocations.

**Why:** Payment actions have unique requirements: they need budget reservation, merchant verification, settlement reference tracking, and financial regulatory considerations. A dedicated type allows AVS to apply payment-specific controls without polluting the general action pipeline.

**Implementation:**
- `ActionType.PAYMENT` enum value
- Payment-specific fields in ActionRequest (amount, currency, merchant_id, payment_rail)
- Payment-specific receipt enrichment

### Receipt Enrichment

**What:** Enhanced ASR-1 receipts with payment-specific metadata.

**Why:** The RAILS paper's Evidence Envelope requires settlement references and payment hashes. AVS receipts must capture this data to serve as evidence in clearing decisions.

**Implementation:**
- `settlement_reference`: Reference ID from the payment rail
- `payment_hash`: Blockchain transaction hash (if applicable)
- `budget_tracking`: Pre-action budget, reserved amount, post-action budget
- `merchant_verification`: Merchant identity and reputation at time of transaction
- `payment_rail`: Which rail was used (Stripe, AP4M, Circle, etc.)

### During-Action Controls

**What:** Reservation/commit semantics for budget and resource locking.

**Why:** This closes the during-action gap identified in Section 7 and directly addresses the x402 allowance overdraft vulnerability. Without reservation, concurrent actions can exceed budgets.

**Implementation:**
- **Reservation API:** On approval, reserve budget/resources for the expected action
- **Commit API:** On receipt, commit the reservation (convert to actual consumption)
- **Release API:** On failure/timeout, release the reservation
- **Two-phase locking:** Reservation → execution → commit/release
- **Pessimistic delivery option:** For high-risk actions, require commit before providing service

### Near-Miss Classification

**What:** A classification for actions that were technically within policy but exhibited risky characteristics.

**Why:** Financial actions require more nuanced classification than PASS/FAIL/VIOLATION. A payment just under a budget limit, to a new merchant, at an unusual time, is not a violation -- but it is a near-miss that deserves attention.

**Implementation:**
- Near-miss scoring: composite risk score based on policy proximity, merchant novelty, temporal anomaly, amount deviation from baseline
- Near-miss flag in ASR-1 receipts
- Near-miss dashboard for operators
- Configurable near-miss thresholds per policy

### Outcome Linkage

**What:** Explicit linkage between receipts and incidents/outcomes.

**Why:** The clearing layer requires evidence that an action's outcome was as expected. If a payment receipt shows $100 but the settlement was $1,000, that discrepancy must be detectable and linkable to an incident.

**Implementation:**
- Outcome verification: compare receipt data against actual outcomes (settlement amounts, API response codes, resource consumption)
- Automatic incident creation on outcome mismatch
- Receipt → incident linkage in the audit trail
- Dispute resolution support: receipts serve as evidence in payment disputes

### v0.4 Roadmap Summary Table

| Feature | Priority | Competitive Driver | Market Validation |
|---------|----------|-------------------|-------------------|
| Payment-aware policies | P0 | Catena differentiation | AP4M partner requirements |
| ActionType.PAYMENT | P0 | Payment-specific controls | ACP / TAP protocols |
| Receipt enrichment | P0 | RAILS Evidence Envelope | Academic / compliance needs |
| During-action controls | P0 | x402 vulnerability closure | "Free-Riding" paper |
| Near-miss classification | P1 | Financial risk management | Enterprise compliance |
| Outcome linkage | P1 | Clearing layer completeness | RAILS Clearing Decision |

---

## 10. What AVS Does NOT Do

Clarity about scope boundaries prevents competitive confusion, partnership friction, and internal scope creep. The following are explicit exclusions from AVS's scope.

### Does NOT Compete with Payment Rails

**Mastercard, Stripe, Coinbase, Circle, Adyen, Solana Pay.sh** -- these are all payment rails. They move value. AVS does not move value. AVS decides whether value-moving actions should be initiated.

**Why this matters:** If AVS appears to compete with payment rails, potential partners (Stripe, Coinbase, AP4M participants) will treat AVS as a threat rather than a complement. AVS must be positioned as a partner-enabling layer, not a rail alternative.

### Does NOT Move Money

AVS has no wallet. AVS has no settlement capability. AVS has no access to user funds. AVS cannot initiate, execute, or complete a financial transaction.

**What AVS does:** AVS approves or denies an action request that may involve a payment. The actual payment is executed by a payment rail that AVS has no control over and no access to.

**Why this matters:** Moving money requires licenses, regulatory compliance, banking relationships, and insurance. AVS avoids all of this by design. The architectural boundary between governance and execution is also a regulatory boundary.

### Does NOT Replace Observability

**LangSmith, Langfuse, Weights & Biases, Arize** -- these are observability platforms. They trace agent execution, measure performance, debug failures, and optimize prompts.

**What AVS does vs. observability:**

| Dimension | Observability (LangSmith, Langfuse) | AVS |
|-----------|-------------------------------------|-----|
| **Primary question** | "What happened and why?" | "Should this have happened?" |
| **Timing** | During and after execution | Before and after execution |
| **Decision authority** | None (observes only) | Yes (can deny execution) |
| **Scope** | LLM inference, prompt chains, tool calls | All agent actions (including non-LLM) |
| **Output** | Traces, spans, metrics | Receipts, verdicts, incidents |

AVS and observability are complementary. AVS decides whether to allow an action; observability traces what the agent did after approval. Both are necessary.

### Does NOT Replace Policy Engines

**Open Policy Agent (OPA), Cedar, AWS IAM Policy Engine** -- these are general-purpose policy engines. They evaluate policies against requests and return allow/deny decisions.

**What AVS does vs. policy engines:**

| Dimension | Policy Engine (OPA, Cedar) | AVS |
|-----------|---------------------------|-----|
| **Scope** | General policy evaluation | Agent action governance |
| **Identity model** | Generic (user, role, resource) | Agent-specific (Agent Cards, tool binding) |
| **Receipt system** | None | ASR-1 cryptographic receipts |
| **Post-action verification** | None | Receipt verification, outcome linkage |
| **Integration** | Embedded in service | External admission controller |

AVS could use OPA or Cedar as its internal policy evaluation engine. AVS wraps the policy engine with agent-specific identity, receipt generation, and post-action verification. The policy engine is a component; AVS is the system.

### Does NOT Replace Identity Systems

**SPIFFE/SPIRE, OIDC, OAuth 2.0, WebAuthn** -- these are identity and authentication systems. They prove who (or what) is making a request.

**What AVS does vs. identity systems:**

| Dimension | Identity System | AVS |
|-----------|----------------|-----|
| **Primary question** | "Who is this?" | "Should this action be allowed?" |
| **Output** | Identity assertion, credential | Action verdict (allow/deny/quarantine) |
| **Scope** | Authentication | Authorization + governance |
| **Action binding** | None | Cryptographic binding between identity, action, and receipt |

AVS depends on identity systems. AVS consumes identity assertions (SPIFFE SVIDs, OIDC tokens) as inputs to its admission decision. AVS does not issue identities; it consumes them.

### What AVS DOES: Governs All of the Above Before Execution

The positive statement of AVS's scope:

> **AVS is the governance layer that consumes inputs from identity systems, policy engines, and observability platforms; applies agent-specific admission control; and produces tamper-evident receipts that serve as evidence for the clearing layer.**

AVS is not a replacement for any existing system. It is a new layer that sits between the agent and the world, making decisions that no other system is positioned to make.

### Scope Boundary Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EXISTING SYSTEMS                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Identity │ │  Policy  │ │Observab. │ │ Payment  │        │
│  │  (OIDC,  │ │  (OPA,   │ │(LangSmith│ │  (Stripe,│        │
│  │ SPIFFE)  │ │  Cedar)  │ │ Langfuse)│ │  AP4M)   │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │            │            │            │               │
│       ▼            ▼            ▼            ▼               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                    AVS LAYER                         │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │          ADMISSION CONTROL                   │    │     │
│  │  │  Identity verification + Policy evaluation   │    │     │
│  │  │  + Agent-specific heuristics → Verdict       │    │     │
│  │  └─────────────────────────────────────────────┘    │     │
│  │                         │                            │     │
│  │                         ▼                            │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │         EXECUTION (delegated)                │    │     │
│  │  │  Tool call / Payment / API → External system │    │     │
│  │  └─────────────────────────────────────────────┘    │     │
│  │                         │                            │     │
│  │                         ▼                            │     │
│  │  ┌─────────────────────────────────────────────┐    │     │
│  │  │      RECEIPT + VERIFICATION                  │    │     │
│  │  │  ASR-1 receipt → Verification → Outcome      │    │     │
│  │  └─────────────────────────────────────────────┘    │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

AVS consumes from identity, policy, and observability systems. AVS produces receipts for the clearing layer. AVS delegates execution to tools and payment rails. AVS does not replace any system in the stack. It governs the handoffs between them.

---

## Appendix A: Competitive Positioning Matrix

| Competitor / Category | Primary Function | Overlap with AVS | AVS Differentiation |
|-----------------------|-----------------|-------------------|---------------------|
| **Catena** | Payment control plane | Admission control for payments | AVS scope is all actions, not just payments. AVS has cryptographic receipts; Catena has transaction logs. |
| **Mastercard AP4M** | Multi-rail settlement | None (execution layer) | AVS is upstream governance; AP4M is downstream execution |
| **x402 (Coinbase)** | Payment protocol | None (AVS could use x402 as a rail) | AVS mitigates x402's vulnerabilities via fail-closed admission |
| **Stripe / ACP** | Payment processing | None | AVS governs whether to initiate Stripe payments |
| **LangSmith / Langfuse** | Observability | Post-action visibility | AVS decides before execution; observability traces after |
| **OPA / Cedar** | Policy engine | Policy evaluation | AVS wraps policy engines with agent identity and receipts |
| **SPIFFE / OIDC** | Identity | Identity verification | AVS consumes identity; it does not issue it |
| **Cloudflare (edge)** | Edge security / identity | Potential overlap in agent verification | AVS is application-layer; Cloudflare is network-layer. Complementary. |

## Appendix B: Key External References

| Reference | Date | Significance for AVS |
|-----------|------|---------------------|
| Google AP2 (Agent Payments Protocol) | September 2025 | Validates need for admission control |
| Visa TAP (Trusted Agent Protocol) | October 2025 | Validates need for agent identity verification |
| Stripe/OpenAI/Meta ACP | Late 2025 | Standardizes agent checkout flow |
| "Free-Riding in the AI Economy" (x402 vulnerability paper) | May 2026 | Independently validates fail-closed architecture |
| RAILS Paper (Reference Architecture for Intelligent Ledger Settlement) | 2026 | Provides academic framework mapping to AVS constructs |
| Mastercard AP4M launch | June 2026 | Validates institutional market; creates partnership opportunity |
| Circle Nanopayments mainnet | April 2026 | Gas-free micro-transactions; AVS can govern usage |
| Solana + Google Pay.sh | May 2026 | Per-request payment model; admission control needed |
| AWS AgentCore Payments | May 2026 | Enterprise agent payments; AVS integrates at cloud layer |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | June 2026 | Strategy Team | Initial document |

**Next Review Date:** September 2026 (post-v0.4 release)
**Distribution:** Executive team, Product, Engineering leads, Investor relations

---

*This document is confidential and for internal use only. Do not distribute externally without executive approval.*
