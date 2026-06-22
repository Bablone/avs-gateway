# Design Partner Outreach Email Templates

> **Purpose:** Recruit design partners for AVS Gateway v0.3.4 Developer Release 
> **Audience:** AI team leads, CISOs, AI startup founders 
> **Tone:** Concrete, respectful, honest about alpha stage. No hype. 
> **Rules:** No "first to" / "only" claims. No competitor bashing. No nuclear metaphors.

---

## Template A: AI Team Lead

**Subject:** {{company_name}} permission layer for your agent toolsWARNING

**Body:**

Hi {{first_name}},

I noticed {{company_name}} is building with agents that touch real systems likely file access, API calls, maybe deployments. A pattern we keep seeing: teams give their agents broad tool access because there's no clean way to gate individual actions at runtime. When something goes sideways, there's no trail of what was attempted, what was allowed, and why.

AVS Gateway is an open-source runtime permission layer for Python-based agents. One decorator (`@governed_tool`) wraps any function. Before execution, it checks policy, scores risk, and returns ALLOW, DENY, REQUIRE_APPROVAL, or QUARANTINE. Every decision produces a cryptographically signed receipt. That's the entire integration for most teams.

We're in alpha (v0.3.4, 470+ tests passing, Apache 2.0). We're looking for three teams running internal agents who want execution governance without rebuilding their stack.

**Could we do a 15-minute call this weekWARNING** I'll share exactly where we fit in your toolchain and where we don't.

 {{sender_name}}

**P.S.** We work offline, no cloud dependency. Policy is declarative YAML your security team can read it without learning your framework.

---

## Template B: CISO

**Subject:** Audit receipts for agent actions at {{company_name}}

**Body:**

Hi {{first_name}},

{{company_name}} is experimenting with AI agents, and I imagine a question coming up in your security reviews: *"What evidence do we have of what the agent tried to do, what was allowed, and who approved itWARNING"* Right now, most agent frameworks log output after the fact. They don't produce tamper-evident records of the decision chain.

AVS Gateway is an open-source runtime permission layer that sits between an agent's intent and its actions. Every tool call is intercepted, evaluated against declarative policy, and logged with an Ed25519-signed receipt plus a SHA-256 audit chain. You get an immutable record of every decision not just what executed, but what was attempted and denied.

We're pre-launch (Apache 2.0, local-first, no vendor lock-in). We're talking to three security-minded companies who need governance evidence for agent tool access.

**Worth a 15-minute conversationWARNING** I'll show you the receipt format and policy structure no product pitch.

 {{sender_name}}

**P.S.** Policy is YAML. Risk scoring is transparent (8 dimensions, inspectable). No black-box model decisions.

---

## Template C: AI Startup Founder

**Subject:** Ship agent features faster with guardrails

**Body:**

Hi {{first_name}},

You're building fast at {{company_name}}. The tension I hear from founding engineers: every new agent capability (file access, API calls, deployments) means a security review that slows shipping. Either you build guardrails yourself weeks of work or you ship carefully and slowly.

AVS Gateway is an open-source runtime permission layer you drop in with a decorator. It gates every agent action at runtime: policy check, risk score, then ALLOW / DENY / REQUIRE_APPROVAL. Your agent can't accidentally delete a customer file or call a production API without passing the gate. Every action gets a signed receipt for audit.

One decorator. No rewrites. Works with LangChain, plain Python, or custom tools. We're at v0.3.4, Apache 2.0, and looking for two early teams who want to ship fast without sacrificing governance.

**Got 15 minutes this weekWARNING** I'll send you a working example with your stack before we even talk.

 {{sender_name}}

**P.S.** The trust model uses time-weighted decay permissions tighten automatically if an agent hasn't been used recently. No cron jobs required.

---

## Follow-up Sequence

### Day 3 The Bump

**Subject:** Re: {{original_subject_line}}

Hi {{first_name}},

Quick bump know you're busy. The 15-min call is genuinely low-pressure. I'm not pitching a partnership. I want to show you where AVS fits and get your read on whether the permission model matches what you're seeing in production.

Happy to send a 2-minute Loom instead if scheduling is painful.

 {{sender_name}}

---

### Day 7 Value-Add Follow-up

**Subject:** Example: gating a file-deletion tool in 6 lines

Hi {{first_name}},

Wanted to share something concrete regardless of whether we talk. Here's what wrapping a tool looks like with AVS:

```python
from avs_gateway import governed_tool, ActionType

@governed_tool(
  name="delete_file",
  action_type=ActionType.FILE_DELETE,
  risk_score=0.85
)
def delete_file(path: str):
  # your existing function no logic changes
  pass
```

That's the integration. Policy decides whether it runs. A receipt is generated either way. Full example: [github.com/avs-gateway/examples](https://github.com/avs-gateway/examples)

Still happy to do a brief call if useful or just send me a one-line reply on whether this problem is real for you. Both help.

 {{sender_name}}

---

### Day 14 The Graceful Breakup

**Subject:** Closing the loop AVS design partners

Hi {{first_name}},

No pressure to reply closing out my outreach for this cycle. We're selecting 3 design partners and finalizing in the next two weeks.

If agent execution governance becomes a priority for {{company_name}} in the future, I'm happy to reconnect. The project is open-source (Apache 2.0) regardless, so you can always kick the tires without talking to me: [docs.avs-gateway.io](https://docs.avs-gateway.io)

Good luck with the agent work genuinely hope {{company_name}} ships something great.

 {{sender_name}}

**P.S.** If you know another team wrestling with "how do we let our agent touch production safely," I'd appreciate an intro. No finder's fee, just a shared problem.

---

## Tracking Spreadsheet

Use these columns to track outreach:

| Column | Description | Example |
|--------|-------------|---------|
| `Name` | Recipient full name | Jane Chen |
| `First Name` | For personalization | Jane |
| `Company` | Company name | Acme Corp |
| `Role` | Job title | VP Engineering |
| `Segment` | Template used | A (Team Lead), B (CISO), C (Founder) |
| `Source` | How you found them | LinkedIn, conference, referral |
| `Date Sent` | Initial email date | 2025-01-15 |
| `Subject` | Subject line used | Acme Corp permission layer... |
| `Status` | Current state | Sent / Replied / Call Scheduled / Call Done / Declined / No Reply |
| `Day 3 Sent` | Follow-up 1 date | 2025-01-18 |
| `Day 7 Sent` | Follow-up 2 date | 2025-01-22 |
| `Day 14 Sent` | Breakup date | 2025-01-29 |
| `Reply Content` | Key points from reply | "Not a priority Q1" |
| `Call Date` | If scheduled | 2025-01-25 |
| `Call Notes` | Outcomes from call | Wants RBAC, not ready |
| `Next Step` | Action item | Send RBAC roadmap, re-engage March |
| `Referral` | Intro to someone else | n/a |

### Status Definitions

- **Sent** Initial email delivered
- **Replied** Any reply received (track sentiment in Notes)
- **Call Scheduled** 15-min call on calendar
- **Call Done** Call completed, notes captured
- **Declined** Explicitly not interested
- **No Reply** No response after Day 14 breakup
- **Partner** Selected as design partner

### Targets

Goal: 20 outreach emails 5 replies 3 calls 2 design partners

| Metric | Target |
|--------|--------|
| Emails sent | 20 |
| Reply rate | 25% (5 replies) |
| Call conversion | 60% of replies (3 calls) |
| Partner conversion | 2 from calls |

---

## Quick Reference: Personalization Placeholders

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{{first_name}}` | LinkedIn, GitHub, company site | "Sarah" |
| `{{company_name}}` | Their company | "Tecton" |
| `{{sender_name}}` | You | "Alex Rivera" |
| `{{original_subject_line}}` | Subject of your first email | "Tecton permission layer..." |

---

*Last updated: v0.3.4 Developer Release Foundation* 
*Next review: after design partner cohort is full*
