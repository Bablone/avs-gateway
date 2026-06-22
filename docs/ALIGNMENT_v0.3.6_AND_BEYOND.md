# AVS Alignment: v0.3.6 Active, v0.4.0+ Forward Plan

**Date:** 2026-06-22 (real), brief is forward-dated to 2026-06-26
**Status:** v0.3.5 released and locked. v0.3.6 branch active. Looking forward only.

---

## 1. What Does NOT Get Touched

v0.3.5 is released, tagged, archived, pushed to GitHub. It is locked.
Unless a critical bug is found, no changes to v0.3.5.

---

## 2. Fact-Checked Competitive Corrections

| My Claim | Fact-Check Result | Corrected Position |
|----------|-------------------|--------------------|
| Pipelock pursuing IETF/OASIS | **Overclaimed.** IETF draft is from Veritas Acta, not Pipelock | Pipelock is real threat (MCP/egress/receipts). Veritas Acta is the standards threat. Track separately. |
| Cerbos "11 agent frameworks" | **Unverified.** No source found | Cerbos is HIGH threat for policy layer. Framework count not confirmed. |
| Microsoft AGT "9,500+ tests, 11 integrations" | **Secondary commentary.** Not verified from Microsoft directly | AGT is HIGH/platform threat. Use only verified claims from Microsoft GitHub/docs. |
| "Agent Admission Controller" unclaimed | **Partially confirmed.** Agent Control Protocol paper uses same logic | Own the term NOW before Microsoft/Prefactor/Cerbos does. |

---

## 3. The Corrected Category Phrase

**v0.3.5 phrase:** "Runtime Permission Layer for AI Agents"
**v0.3.6+ phrase:** "Agent Admission Controller for autonomous systems"

Why the change:
- Kubernetes developers immediately understand "admission controller"
- Agent Control Protocol paper (March 2026) independently validates the logic
- More specific than "runtime permission layer"
- More defensible than "runtime governance" (Prefactor is using that)
- Cuts across payment/tool/file/API verticals

The sentence:
> **"Before an agent mutates the world, AVS decides whether the action is allowed — and proves why."**

---

## 4. The Corrected Vertical Priority

| Priority | Market | Why | Timing |
|----------|--------|-----|--------|
| **P0** | Global developer infrastructure | AI coding teams, MCP developers, agent framework builders, platform engineers | NOW |
| **P1** | MCP Tool Guard | MCP has broad adoption, clear risk (MCPSHIELD: 66% uncovered), faster adoption than payments | v0.4.0 |
| **P2** | Agentic Payments Guard | Strategically hot but crowded (x402, AP4M, Catena). Framed as policy pack, not whole company | v0.4.1 |
| **P3** | Enterprise evidence/compliance receipts | The moat layer (CertNode, Veritas Acta, RAILS prove the race is real) | v0.5+ |
| **P4** | TrustNamba/PropertyFlow vertical | Future vertical proof, domain moat, NOT front-facing in global messaging | Post-v0.5 |

Key correction: **MCP Guard comes before Payment Guard.** MCP is where developers already feel pain. Payments are a strong narrative but MCP/tool governance is the faster adoption wedge.

---

## 5. The Corrected Threat Matrix

| Level | Players | Why |
|-------|---------|-----|
| **Critical watch** | Microsoft Agent 365/AGT, Pipelock, Veritas Acta/IETF drafts | Platform default + receipt standard race |
| **High** | Prefactor, Cerbos, Aletheia Core, t54/x402-secure, CertNode, Saviynt+LangChain | Direct overlap in governance, policy, receipts, payment-risk |
| **Medium** | Catena, Nevermined, Kite, Shopify UCP, Amex ACE, Cloudflare/x402 | Payment/commerce adjacency, not full AVS scope |
| **Low** | AgentOps, Langfuse, Simbian, Sierra, Tempo, BVNK | Observability, vertical apps, payment rails |

**Biggest correction:** Microsoft is a bigger threat than Catena. Microsoft threatens the default enterprise governance layer. Catena only threatens the payment-control narrative.

---

## 6. The Three Receipt Models (New Insight from Sello Paper)

| Model | Who Signs | Strength | AVS Status |
|-------|-----------|----------|------------|
| 1. Agent-signed | The agent itself | Weak — compromised agent = compromised receipt | Not used |
| 2. Gateway/mediator-signed | AVS Gateway | Strong — independent from agent | **v0.3.6 (current)** |
| 3. Receiver/witness-signed | The tool/service receiving the action | Strongest for cross-party proof | **v0.4+ (roadmap)** |

Pipelock argues mediator receipts (#2) are stronger than agent-signed (#1). AVS's natural model is gateway-signed (#2). The roadmap should include witness/receiver attestations (#3).

---

## 7. The Corrected Roadmap

### v0.3.6 (active branch) — ASR-1 Evidence Direction
- [ ] Publish docs/ASR_1_RECEIPT_STANDARD.md as draft (not a promise)
- [ ] Phrase: "Draft receipt format for proof-gated agent actions"
- [ ] Expose JSON schema
- [ ] Include example receipts (allow, deny, require_approval, quarantine)
- [ ] Make `avs receipt verify` command obvious and working
- [ ] Explain gateway-signed vs future witness-signed receipts
- [ ] Map ASR-1 to OWASP Agentic AI Top 10
- [ ] Map ASR-1 to RAILS primitives
- [ ] Map ASR-1 to MCPSHIELD threat categories
- [ ] Merge to main only when: 2+ design partners validate receipt shape, all tests pass, Windows verification clean

### v0.4.0 — AVS MCP Tool Guard (NOT Payment Guard)
Core features:
- [ ] Tool manifest verification
- [ ] Tool identity attestation
- [ ] Read / write / destructive action classification
- [ ] Argument-level policy checks
- [ ] PII scan hook
- [ ] MCP request/response boundary control
- [ ] Approval routing for risky tool calls
- [ ] ASR-1 receipt for every tool invocation
- [ ] 66% MCPSHIELD gap coverage target

### v0.4.1 — Agentic Payments Guard
Core features:
- [ ] Budget reservation before payment
- [ ] Payment-intent hash (idempotency)
- [ ] Counterparty policy (merchant allowlist)
- [ ] Rail type: x402/AP2/AP4M/UCP/ACP/simulated
- [ ] Settlement state tracking
- [ ] Idempotency key / replay guard
- [ ] Fail-closed on settlement uncertainty
- [ ] ASR-1 receipt enriched with payment fields

### v0.5 — AVS Control Room
Hosted/team product:
- [ ] Dashboard
- [ ] Approval queue
- [ ] Policy packs (MCP, payment, file, API)
- [ ] Receipt vault
- [ ] Audit export (CSV/JSON/CloudEvents)
- [ ] SIEM/webhook integration
- [ ] Enterprise self-hosting

---

## 8. P0 Actions (This Week)

1. **Own "Agent Admission Controller" publicly**
   - README: add phrase in opening paragraph
   - Repo description: update
   - Show HN: use phrase
   - Launch copy: use phrase

2. **Publish ASR-1 as a draft, not a promise**
   - docs/ASR_1_RECEIPT_STANDARD.md is already written
   - Add "Draft receipt format for proof-gated agent actions" subtitle
   - Add gateway-signed vs witness-signed explanation
   - Add OWASP/RAILS/MCPSHIELD mapping section

3. **Add competitive positioning note internally**
   - Pipelock (MCP/egress/mediator receipts)
   - Veritas Acta (IETF receipt standard)
   - CertNode (legal receipt standard)
   - Aletheia Core (runtime-signed receipts)
   - Microsoft AGT (platform governance)
   - Prefactor (runtime governance language)
   - Cerbos (policy authorization)
   - t54 (x402 payment governance)

4. **Do not lead with Tanzania**
   - AVS is global
   - TrustNamba only when discussing vertical deployment or fraud/identity proof

---

## 9. P1 Actions (Next 2 Weeks)

1. **Build or expose minimal TypeScript verifier**
   - Receipt standards need cross-language trust
   - Even minimal: parse JSON, verify hash, check signature format

2. **Write docs/RFC_MCP_TOOL_GUARD.md**
   - This is more urgent than Payment Guard
   - Define interfaces, not implementation
   - Show how it covers MCPSHIELD's 66% gap

3. **Map ASR-1 to RAILS and OWASP**
   - Gives security/compliance buyers language they understand
   - Table format: ASR-1 field → RAILS primitive → OWASP risk

4. **Study Pipelock's mediator receipt model**
   - Decide: ASR-1 v0.3.6 gateway-signed only, or include witness-attestation extension?

---

## 10. P2 Actions (Next Month)

1. **Engage standards carefully**
   - IETF drafts are open
   - Do not rush into standards theatre
   - First: working draft + verifier + examples + design partner validation

2. **Design partner feedback before v0.3.6 merge**
   - Receipt shape must be validated by real builders
   - Target: 2+ design partners using ASR-1 in production workflows

3. **Document Payment Guard as v0.4.1, not immediate code**
   - Payment market validates AVS but should not hijack roadmap
   - MCP Guard is the faster wedge

---

## 11. What Has Already Been Done (Inventory)

### v0.3.5 (released, locked)
- [x] README polished with proof-gated action framing
- [x] Version bumped to 0.3.5 (all three files)
- [x] Cryptography warning silenced
- [x] 9 launch assets created
- [x] 496 tests pass
- [x] GitHub release published
- [x] avs version / python -m avs_gateway.cli version / import version all consistent

### v0.3.6 (branch, partially done)
- [x] `receipts/asr1.py` — ASR-1 receipt generation, signing, verification
- [x] `identity/agent_identity.py` — AgentIdentity model
- [x] `tools/tool_manifest.py` — ToolManifest registration
- [x] `cli.py` — `avs receipt verify` command
- [x] 85 new tests (581 total on Linux)
- [x] 4 example receipts (allow, deny, require_approval, quarantine)
- [x] JSON schema
- [x] docs/ASR_1_RECEIPT_STANDARD.md
- [ ] Windows verification (user's machine — pending)
- [ ] "Draft" framing (needs update — currently sounds too official)
- [ ] Gateway-signed vs witness-signed explanation (needs addition)
- [ ] OWASP/RAILS/MCPSHIELD mapping (needs addition)
- [ ] README update for "Agent Admission Controller" (needs update)
- [ ] Merge to main (pending design partner validation)

### Research (done)
- [x] Hidden competitors (23 found, fact-checked)
- [x] Technology landscape (7 targets analyzed)
- [x] Vertical opportunities (7 evaluated)
- [x] Complete landscape map (synthesized)

### Needs to be created (P0/P1)
- [ ] RFC_MCP_TOOL_GUARD.md (v0.4.0 concept document)
- [ ] ASR-1 mapping to OWASP/RAILS/MCPSHIELD
- [ ] Updated README with "Agent Admission Controller"
- [ ] TypeScript ASR-1 verifier (minimal)
- [ ] Competitive positioning note (fact-checked version)

---

## 12. The Refined Thesis

AVS is a global infrastructure play for high-adoption AI markets. Tanzania/TrustNamba/PropertyFlow are future vertical proof, not the main public category.

The market is converging around runtime governance, MCP security, cryptographic receipts, and clearing. But competitors are already moving into each sub-layer.

The only position that survives:

> **AVS Gateway is the Agent Admission Controller for autonomous systems.**
>
> **Before an agent mutates the world, AVS decides whether the action is allowed — and proves why.**

The stack:
```
Model → Agent → AVS (Agent Admission Controller) → Tool/Payment Rail → ASR-1 Receipt → Clearing/Dispute/Compliance
```

---

## 13. Deliverables to Create Now

| # | Deliverable | Priority | Purpose |
|---|-------------|----------|---------|
| 1 | ASR-1 framing update | P0 | Add "draft" label, gateway/witness receipt explanation, remove "standard" language |
| 2 | README update for v0.3.6 branch | P0 | Add "Agent Admission Controller" phrase |
| 3 | ASR-1 OWASP/RAILS/MCPSHIELD mapping | P0 | Security/compliance legitimacy |
| 4 | RFC_MCP_TOOL_GUARD.md | P1 | v0.4.0 concept — interfaces, not code |
| 5 | Fact-checked competitive positioning note | P1 | Internal reference with verified claims only |
| 6 | Minimal TypeScript verifier | P1 | Cross-language receipt validation |

---

> **Every agent action gets a receipt.**
>
> AVS Gateway — Agent Admission Controller for Autonomous Systems
