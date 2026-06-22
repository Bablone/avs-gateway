# AVS Market Map

## The Full Agentic Stack

```
+-------------------------------------------------------------+
|  MODELS                                                     |
|  OpenAI, Google, Anthropic, Meta, Llama, DeepSeek           |
|  -> Intelligence                                            |
|  AVS: Not competing                                         |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  AGENT FRAMEWORKS                                           |
|  LangChain, OpenAI Agents SDK, Google ADK, MCP, Cursor      |
|  -> Agent orchestration                                     |
|  AVS: Integrates via adapters                               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  AVS GATEWAY <--- YOU ARE HERE                              |
|                                                             |
|  Runtime permission layer for AI agents                     |
|  -> Intercept, evaluate, decide, prove                      |
|  -> Proof-gated action                                      |
|  -> ASR-1 receipts                                          |
|  -> Agent identity                                          |
|  -> Tool manifest                                           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  TOOL / PAYMENT RAILS                                       |
|  x402, Mastercard AP4M, Stripe ACP, Google AP2, Visa TAP    |
|  AWS AgentCore, Circle Nanopayments, Pay.sh                 |
|  -> Execution channels                                      |
|  AVS: Governs before they execute                           |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  EXECUTION                                                  |
|  File system, APIs, databases, deployments, emails,         |
|  payments, messages, infrastructure                         |
|  -> Real-world consequences                                 |
|  AVS: Decides whether to allow                              |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  EVIDENCE / CLEARING                                        |
|  ASR-1 receipts, RAILS clearing, compliance, audit,         |
|  insurance, dispute resolution                              |
|  -> Proof of what happened                                  |
|  AVS: Creates the receipt                                   |
+-------------------------------------------------------------+
```

AVS sits at the **Control Plane** layer -- between agent frameworks and execution channels. It is the only layer that can see the full context of an action, evaluate it against owner-defined policy, produce tamper-evident proof, and gate execution based on that proof.

---

## Function-Based Map

Each emerging player solves a piece of the puzzle. The gaps they leave exposed are what AVS fills.

| Function | Players | Solves | Gap |
|----------|---------|--------|-----|
| User intent / mandate | Google AP2, Visa TAP | Did the user authorize this agent? | Was the action safe in context? What if the mandate was co-opted? |
| Commerce interaction | Stripe ACP, OpenAI Commerce | Can agents complete purchases? | Should this specific transaction happen now, given the current context? |
| Agent identity | Visa TAP, Mastercard Verifiable Intent, MCP | Is this a recognized agent? | Is it behaving within its authorized policy? Is its identity consistent across tool calls? |
| Micropayment execution | x402, Pay.sh, Circle Nanopayments | Can agents pay per request? | Atomicity, replay protection, settlement drift, cross-rail consistency |
| Institutional settlement | Mastercard AP4M, bank rails | Can payments settle across rails? | Cross-tool governance -- who mediates when tool A and tool B disagree? |
| Observability | LangSmith, Langfuse, Arize | What did the agent do? | No interception -- it already happened. Reactive, not preventive. |
| Output validation | Guardrails AI, Lakera | Is the output safe / compliant? | No execution governance -- validates text, not actions. |
| Policy engine | OPA, Cedar | Is the action permitted by policy? | No action normalization, no adapters, no receipts, no proof of compliance. |
| **Control plane** | **Catena, AVS** | **Can owners set controls, intercept, and produce audit evidence?** | **Catena: payment-focused, closed-source. AVS: all actions, open-source, with receipts.** |

### The Key Insight

No existing player governs **all autonomous consequences** with **proof of what was decided and why**. That is the gap AVS occupies.

- Payment rails (AP2, TAP, x402) move money. They do not govern whether the action that triggered the payment was legitimate.
- Observability tools record. They do not prevent.
- Policy engines decide. They do not produce portable receipts or normalize actions across frameworks.
- Security tools detect. They do not gate execution with proof.

AVS is the **runtime permission layer** -- the only component that intercepts, evaluates, proves, and gates across the full stack.

---

## Competitive Matrix

| Capability | AVS | Catena | LangSmith | Guardrails AI | OPA |
|-----------|:---:|:------:|:---------:|:-------------:|:---:|
| Intercept actions before execution | YES | YES | NO | Partial | Partial |
| All action types (not just payments) | YES | NO | N/A | YES | YES |
| Payment action governance | Planned | YES | NO | NO | NO |
| Receipt format (ASR-1) | YES | NO | NO | NO | NO |
| Agent identity model | YES | Partial | NO | NO | NO |
| Tool manifest | YES | NO | NO | NO | NO |
| Tamper-evident receipts | YES | NO | NO | NO | NO |
| Framework adapters | YES | NO | N/A | N/A | N/A |
| Open source | YES | NO | Partial | Partial | YES |

### Detailed Breakdown

**AVS** -- The only open-source control plane that intercepts all action types, normalizes them across frameworks, evaluates against owner policy, produces tamper-evident ASR-1 receipts, and gates execution with proof. Designed for neutrality, portability, and auditability.

**Catena** -- Payment-focused control plane from Stripe's payment infrastructure heritage. Strong on money movement governance. Closed source. Does not govern non-payment actions (file writes, API calls, deployments). Competes directly on payment governance; AVS is broader.

**LangSmith / Langfuse** -- Observability platforms for LLM applications. They record traces, monitor latency, track token usage. They do not intercept or gate execution. Reactive by design.

**Guardrails AI** -- Output validation for LLMs. Checks text for PII, toxicity, factual accuracy. Does not govern tool execution or action consequences. A different problem space.

**OPA (Open Policy Agent)** -- General-purpose policy engine. Makes authorization decisions but has no concept of agent identity, tool manifests, action normalization, or receipt formats. AVS can embed OPA as a policy evaluator but adds the missing runtime layer.

---

## The AVS Wedge

One sentence per competitor category. No hype.

| Category | Incumbents | AVS Positioning |
|----------|-----------|----------------|
| **Payment control planes** | Catena | Catena governs money movement. AVS governs all autonomous consequences. |
| **Observability** | LangSmith, Langfuse, Arize | They record what happened. AVS controls whether it should happen. |
| **Output validation** | Guardrails AI, Lakera | They validate text. AVS governs execution. |
| **Policy engines** | OPA, Cedar | They make decisions. AVS adds action normalization, framework adapters, receipts, and proof-gated approvals. |
| **Security detection** | LayerX, HiddenLayer, Pillar | They detect anomalies. AVS decides before execution. |
| **Cloud platforms** | AWS AgentCore, Google Vertex | They lock you to their ecosystem. AVS is portable across clouds, frameworks, and rails. |
| **Payment protocols** | AP2, TAP, ACP, x402 | They enable transactions. AVS governs whether the transaction should execute. |
| **Agent identity** | Visa TAP, Mastercard Verifiable Intent | They identify the agent. AVS enforces what the agent is allowed to do and proves compliance. |

### Why AVS Wins Each Wedge

1. **vs. Catena:** Broader scope (all actions, not just payments), open-source, portable, evidence standard (ASR-1).
2. **vs. Observability:** Preventive, not reactive. Interception beats recording.
3. **vs. Output validation:** Execution governance > text validation. Actions have consequences; words are just tokens.
4. **vs. Policy engines:** OPA decides "yes/no." AVS decides "yes/no, and here is the proof, normalized across frameworks, with agent identity verified, and a tamper-evident receipt."
5. **vs. Security detection:** Detection has false positives. Interception is deterministic.
6. **vs. Cloud platforms:** Vendor lock-in is the #1 enterprise concern about AI infrastructure. AVS is the neutral Switzerland.
7. **vs. Payment protocols:** AVS sits above the rails and can govern across all of them simultaneously.
8. **vs. Agent identity:** Identity without enforcement is just a nametag. AVS binds identity to policy to proof.

---

## Time Horizon

Where the market is, where it is going, and where AVS sits.

```
2024          2025              2026 H1            2026 H2         2027            2028+
  |             |                  |                  |              |               |
  v             v                  v                  v              v               v
+--------+  +--------+       +-----------+      +-----------+  +-----------+   +-------------+
| AGENT  |  | PAYMENT|       |  RAILS    |      |  CONTROL  |  |  CONTROL  |   | EVIDENCE /  |
| FRAME- |  | PROTO- |       | OPERAT-   |      |  LAYER    |  |  PLANE    |   | CLEARING    |
| WORKS  |  | COLS   |       | IONAL     |      |  GAP      |  |  COMPET-  |   | MATURES     |
|        |  |        |       |           |      |  OBVIOUS  |  |  ITION    |   |             |
+--------+  +--------+       +-----------+      +-----------+  +-----------+   +-------------+
  |             |                  |                  |              |               |
  |  LangChain  |  AP2, TAP, ACP   |  AP4M, AgentCore |  x402 vulns  |  Catena +     |  ASR-1 or
  |  Agents SDK |  x402 defined    |  Pay.sh live     |  RAILS paper |  others       |  competing
  |  MCP        |                  |                  |              |               |  format
  |             |                  |                  |              |               |
  +-------------+------------------+------------------+--------------+---------------+
                                   |
                                   |   AVS IS HERE <--- YOU ARE HERE
                                   |   2026 H1 -> 2027 window
                                   |
                                   v

                    Early enough to define the category.
                    Late enough that the market has validated the need.
```

### Why This Timing Matters

- **2024 proved agents work.** LangChain, AutoGPT, MCP -- the infrastructure for agent orchestration arrived. Enterprises began deploying. Incidents happened.

- **2025 proved money would flow.** Stripe, Visa, Mastercard, Google -- every major payment player announced agent-payment protocols. The financial industry recognized that agents will transact autonomously.

- **2026 H1 proves the rails work.** Mastercard AP4M, AWS AgentCore, Pay.sh, Circle Nanopayments -- payment rails go live. Real money moves through real agent interactions.

- **2026 H2 proves the gap exists.** x402 replay vulnerabilities. RAILS paper on atomic settlement. Enterprises realize: rails move money, but nothing governs whether the movement was legitimate. The control layer gap becomes obvious.

- **2027 is when the market consolidates.** Catena enters. Cloud providers add control features. Enterprises demand open standards. The winner is whoever defined the category first with the best evidence format.

- **2028+ is clearing and compliance.** ASR-1 receipts or a competing format become the standard for audit, insurance, dispute resolution, and regulatory compliance.

**AVS is positioned at the 2026 H1 -> 2027 window.** We arrive when the market has validated the need (rails are live, gaps are obvious) but before the category is locked (Catena is the only named competitor, and they are narrower).

---

## Strategic Positioning Summary

### For Internal Use

AVS is the runtime permission layer for autonomous agents. We sit between agent frameworks and execution channels, intercepting every action, evaluating it against owner-defined policy, producing tamper-evident ASR-1 receipts, and gating execution with proof.

We are not competing with models, frameworks, payment rails, or cloud platforms. We complement all of them. We are the neutral Switzerland of the agentic stack -- portable, open-source, and framework-agnostic.

### For Investor Conversations

The autonomous agent market is forming in layers:

1. **Models** (solved -- OpenAI, Anthropic, Google)
2. **Frameworks** (solved -- LangChain, MCP, Cursor)
3. **Payment rails** (emerging -- AP4M, AgentCore, Pay.sh)
4. **Control plane** (empty -- this is AVS)
5. **Evidence / clearing** (future -- ASR-1)

AVS occupies layer 4, the control plane. This is the empty layer -- the only one with no incumbent and massive enterprise demand. Every enterprise deploying agents needs to answer: "How do I control what these things do?" AVS is the answer.

The market timing is precise. Payment rails go live in 2026 H1. The control gap becomes obvious in 2026 H2. AVS is building now to capture the 2027 market consolidation window. By the time Catena and cloud providers compete, AVS will have defined the category, the evidence format (ASR-1), and the open-source standard.

### The Moat

- **ASR-1 as the evidence standard** -- First-mover advantage in the receipt format. If ASR-1 becomes the standard for audit and compliance, AVS is the reference implementation.
- **Framework adapters** -- Deep integrations with LangChain, OpenAI Agents SDK, Google ADK, MCP. Each adapter increases switching costs.
- **Neutrality** -- Unlike Catena (Stripe heritage, payment-focused) or cloud providers (ecosystem-locked), AVS is the neutral, portable layer. Enterprises prefer neutral for infrastructure that gates all their actions.
- **Open source** -- AVS is open source. Catena is not. This creates a developer community, ecosystem trust, and enterprise adoption preference.
- **Tool manifest standard** -- If AVS defines how tools declare their capabilities and risks, we become the schema authority for the control layer.

---

*Last updated: 2025. Market positions reflect current public information and are subject to change as the ecosystem evolves.*
