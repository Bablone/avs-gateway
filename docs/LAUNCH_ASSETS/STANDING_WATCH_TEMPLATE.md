# Standing Watch  AVS Gateway Post-Launch

> **Version:** 1.0.0  
> **Status:** Launch-ready  
> **Last updated:** 2025-01-22  
> **Purpose:** Daily and weekly procedures for monitoring AVS Gateway after public launch.  
> **Audience:** Maintainers, core contributors, community managers.

---

## Philosophy

Launch day is not the finish line  it is day one of a new phase. This document ensures someone is always watching, questions never go unanswered, and issues are caught before they become problems. The watch rotates; the procedures do not.

---

## Daily Checks (5 minutes)

Run these every morning. Do not skip. Set a recurring calendar reminder.

### GitHub

- [ ] **New issues**  Check https://github.com/avs-gateway/avs/issues
  - Target: Respond within 24 hours (even if just "acknowledged, looking into this")
  - Label new issues: `bug`, `feature-request`, `question`, `docs`, `good-first-issue`
  - If unlabelled for >12h, label them
- [ ] **New PRs**  Check https://github.com/avs-gateway/avs/pulls
  - Target: Initial review within 48 hours
  - Run CI checks; if failing, ask author to fix before review
  - Acknowledge receipt with a comment even if full review will come later
- [ ] **Stars count**  Record in tracking spreadsheet (see Metrics section)
- [ ] **Forks count**  Record in tracking spreadsheet
- [ ] **Discussion posts**  Check https://github.com/avs-gateway/avs/discussions
  - Answer questions; redirect to FAQ if already answered
  - Flag interesting use cases for the weekly digest

### Hacker News

- [ ] **Show HN post engagement**  Check the launch post
  - Respond to comments within 2 hours during the active period (first 6-12 hours)
  - Sort by "new" to catch late comments
  - Track sentiment (see Response Templates below)
- [ ] **Watch for reposts**  Search "AVS Gateway" on HN to catch reposts or discussions in other threads

### X / Twitter + LinkedIn

- [ ] **Mention notifications**  Check @ mentions, quote posts, and keyword searches for "AVS Gateway"
  - Respond to questions within 4 hours
  - Like and retweet positive mentions
  - Bookmark critical feedback for weekly review
- [ ] **Track impressions / engagement**  Screenshot or note key metrics if available

### Email

- [ ] **Design partner inquiries**  Respond within 24 hours
  - Send the Design Partner welcome email (see Response Templates)
  - Add to design partner tracking sheet
- [ ] **Press / analyst inquiries**  Forward to the designated press contact
  - Do not commit to interviews or quotes without checking
- [ ] **Bug reports via email**  Redirect to GitHub Issues with a template link

### CI / Tests

- [ ] **Check CI status**  https://github.com/avs-gateway/avs/actions
  - If main branch is red, investigate immediately
  - If a flaky test fails, file an issue and retry

---

## Weekly Checks (30 minutes)

Run these every Monday morning (or your chosen start-of-week day).

### Community Health

- [ ] **Star velocity**  Stars this week vs. last week vs. target
  - Record in tracking spreadsheet
  - If velocity drops >50% week-over-week, flag in maintainer chat
- [ ] **Issue resolution rate**  (# closed issues this week) / (# opened issues this week)
  - Target: >70% resolution rate
  - If <50%, discuss prioritization in weekly sync
- [ ] **Top issues by engagement**  Sort by reactions + comments
  - Flag high-engagement issues for priority treatment
  - Consider converting popular feature requests into `good-first-issue`

### External Landscape

- [ ] **Competitor / landscape news scan**  10-minute scan
  - Search: "AI agent security", "agent permission", "AI governance"
  - Check LangChain, Guardrails AI, OPA release notes
  - Note anything that affects AVS positioning
  - Record findings in weekly log

### Documentation & Content

- [ ] **Update FAQ**  Add any new questions that came up 3+ times this week
- [ ] **Review docs issues**  Close any docs issues that were fixed
- [ ] **Draft weekly update**  2-3 sentence summary of the week for social / Discussions

### Metrics Dashboard

- [ ] **Update the metrics spreadsheet** with this week's numbers
- [ ] **Screenshot the dashboard** for the weekly maintainer sync
- [ ] **Flag any metric that is off-target** with proposed action

---

## Response Templates

Use these templates directly. Copy, customize, send. Do not rewrite from scratch each time.

### Issue Response  Bug Report

```
Hi @{{username}}, thanks for the bug report.

I can reproduce this on {{version}}. Let me look into it and get back to you within {{timeframe}}.

In the meantime, a workaround: {{workaround_if_known}}

Labelled as `bug`  tracking here.
```

### Issue Response  Feature Request

```
Hi @{{username}}, thanks for the thoughtful request.

{{acceptance_criteria_summary}} makes sense. A few questions to help us design it right:

1. What's your use case  what would this enableWARNING
2. Would you expect this to be a YAML policy, a Python API, or bothWARNING
3. Is this blocking you right now, or a nice-to-haveWARNING

Labelled as `feature-request` and `needs-design`. We'll discuss in the next maintainer sync and update this issue.
```

### Issue Response  Question (redirect to Discussions)

```
Hi @{{username}}, great question.

We use GitHub Discussions for questions and reserve Issues for bugs and feature requests. Could you repost this at https://github.com/avs-gateway/avs/discussionsWARNING That way more people can find and benefit from the answer.

(Quick answer: {{brief_answer}})

Closing this as a discussion topic, but happy to continue there!
```

### HN Comment Response  Positive / Curious

```
Thanks! Happy to answer any questions.

If you want to try it: `pip install -e .` then `avs demo`  takes about 5 minutes to see the first decisions in action.

Source: https://github.com/avs-gateway/avs
```

### HN Comment Response  Critical / Skeptical

```
Fair point. You're right that {{acknowledge_concern}}.

Our take: {{honest_response_with_evidence}}. That said, it's early days  we're tracking this at {{issue_link}} and would love your input if you have a specific use case in mind.
```

**Rules for HN responses:**
- Never get defensive. Acknowledge the concern first.
- Never claim "first" or "only."
- Always link to evidence (issue, doc, benchmark).
- If you don't know, say "That's a good question  I'll look into it and reply here."

### Design Partner Inquiry Response

```
Subject: AVS Gateway  Design Partnership

Hi {{name}},

Thanks for your interest in being a design partner!

Here's what that means:
- You use AVS with your agents for ~4 weeks
- We check in async weekly (GitHub Discussions or Slack  your choice)
- You get early access to features and direct maintainer access
- No cost, no commitment beyond the 4 weeks

To get started, I'd love to know:
1. What kind of agents are you buildingWARNING
2. What actions do they take (file access, API calls, deployments)WARNING
3. What's your biggest concern about agent safety right nowWARNING

Once I hear back, we'll schedule a 15-minute kickoff and get you set up.

Best,
{{maintainer_name}}
```

### Press Inquiry Response

```
Subject: Re: AVS Gateway Inquiry

Hi {{name}},

Thanks for reaching out. I'm forwarding your message to our press contact, who will get back to you within 24 hours.

In the meantime, here are resources:
- Repository: https://github.com/avs-gateway/avs
- README with overview and quickstart
- FAQ: {{faq_link}}

Best,
{{maintainer_name}}
```

### PR Review  First-time Contributor

```
Hi @{{username}}, thanks for your first contribution to AVS! Welcome.

{{specific_feedback_on_code}}

Could you also:
- Add a test for the new behavior
- Update the relevant doc if this changes user-facing behavior

Let me know if you need help with anything  happy to pair on the test if useful.
```

### PR Review  Core Contributor

```
{{specific_feedback}}

One question: {{question_about_approach_or_edge_case}}

Otherwise LGTM after {{specific_change}}.
```

---

## Escalation Procedures

### What Constitutes an EmergencyWARNING

An emergency is any of the following:

| Severity | Definition | Examples |
|----------|------------|----------|
| **P0  Critical** | AVS is actively causing data loss, security incidents, or complete agent failure | Receipt signature bypass, policy engine crash causing data corruption, critical vulnerability disclosed |
| **P1  High** | Major functionality broken, workaround not available | All tool calls denied incorrectly, receipts unverifiable, install broken on supported Python version |
| **P2  Medium** | Feature broken, workaround exists | Specific policy type not matching, decorator failing on certain function signatures |
| **P3  Low** | Docs wrong, cosmetic issues, feature requests | Typo in README, missing docstring, desired feature |

### Who RespondsWARNING

| Severity | Primary Responder | Response Time | Communication |
|----------|-------------------|---------------|---------------|
| P0 | On-call maintainer (rotating) | Within 2 hours | GitHub issue + maintainer chat + social post if security-related |
| P1 | Area owner (who wrote the code) | Within 6 hours | GitHub issue + maintainer chat |
| P2 | Any maintainer | Within 24 hours | GitHub issue |
| P3 | Community / backlog | Within 1 week | GitHub issue, labelled `p3` |

### Emergency Hotpath (P0)

1. Acknowledge the issue within 30 minutes with a comment: "Acknowledged. Investigating."
2. Reproduce locally within 2 hours
3. If reproducible: create a fix branch, write a test, open PR
4. If not reproducible: ask reporter for more details; do not close
5. After fix: cut a patch release (e.g., 0.1.1) within 24 hours
6. Post-mortem: write a brief retrospective within 48 hours, share with maintainers

### Security Incident Specifics

If a security vulnerability is reported:
1. Do NOT discuss in public issues
2. Email the security contact: `security@avs-gateway.dev`
3. Acknowledge receipt within 24 hours
4. Investigate and prepare a fix privately
5. Coordinate disclosure with the reporter
6. See `docs/SECURITY.md` for the full security response process

---

## Metrics to Track

Record these weekly in the tracking spreadsheet (link: `{{spreadsheet_url}}`).

| Metric | Baseline (Day 0) | Week 1 Target | Month 1 Target | How to Track | Owner |
|--------|-----------------|---------------|----------------|--------------|-------|
| GitHub stars | 0 | 100 | 500 | GitHub API / UI | {{owner}} |
| GitHub forks | 0 | 15 | 75 | GitHub API / UI | {{owner}} |
| GitHub watchers | 0 | 50 | 200 | GitHub API / UI | {{owner}} |
| Open issues | 0 | <20 | <30 | GitHub API / UI | {{owner}} |
| Issue resolution rate | N/A | >50% | >70% | (# closed / # opened) per week | {{owner}} |
| Avg issue response time | N/A | <24h | <12h | GitHub issue timestamps | {{owner}} |
| Avg PR review time | N/A | <48h | <24h | GitHub PR timestamps | {{owner}} |
| Discussion threads | 0 | 5 | 20 | GitHub Discussions UI | {{owner}} |
| Design partners enrolled | 0 | 3 | 10 | Internal tracking sheet | {{owner}} |
| External blog posts / mentions | 0 | 2 | 10 | Google Alerts + manual search | {{owner}} |
| HN front page appearance | N/A | 1 (launch) | N/A | HN UI | {{owner}} |
| PyPI downloads | 0 | 200 | 1000 | PyPI Stats API | {{owner}} |

### Spreadsheet Template

Create a Google Sheet with these tabs:

**Tab 1: Weekly Snapshot**
| Week | Date | Stars | Forks | Open Issues | Closed Issues | New Discussions | Design Partners | Notes |
|------|------|-------|-------|-------------|---------------|-----------------|-----------------|-------|
| 1 | 2025-01-22 | 0 | 0 | 0 | 0 | 0 | 0 | Launch day |

**Tab 2: Issue Log**
| Issue # | Title | Opened | Closed | Response Time | Resolution Time | Label | Satisfaction |
|---------|-------|--------|--------|---------------|-----------------|-------|--------------|

**Tab 3: Design Partners**
| Name | Org | Use Case | Enrolled | Weekly Check-ins | Status | Notes |
|------|-----|----------|----------|------------------|--------|-------|

**Tab 4: External Mentions**
| Date | Source | URL | Sentiment | Notes |
|------|--------|-----|-----------|-------|

---

## Weekly Maintainer Sync Agenda

Every Monday, 30 minutes. Standing agenda:

1. **Metrics review** (5 min)  Go through the metrics spreadsheet
2. **Top issues** (10 min)  Discuss open issues that need decisions
3. **Design partner updates** (5 min)  What's working, what's not
4. **Landscape scan** (5 min)  Any competitor or ecosystem newsWARNING
5. **Action items** (5 min)  Who does what this week

Rotate who runs the meeting. The person on watch that week runs it.

---

## Launch Week Special Procedures

Launch week (Day 0 through Day 7) has heightened watch:

| Day | Special Actions |
|-----|----------------|
| **Day 0 (Launch)** | Check GitHub, HN, social every 2 hours until midnight. Be in maintainer chat all day. |
| **Day 1** | Morning check + afternoon check. Respond to all issues within 6 hours. |
| **Day 2** | Morning check + afternoon check. Post first "week 1 update" in Discussions. |
| **Day 3-4** | Normal daily checks, but keep response time <12h. |
| **Day 5-6** | Prepare "launch week retrospective" for Monday sync. |
| **Day 7** | Run full weekly check. Write launch week summary for Discussions. |

### Launch Week Response Time Targets

| Channel | Target Response Time |
|---------|---------------------|
| GitHub Issues | <6 hours |
| GitHub Discussions | <6 hours |
| HN Comments | <2 hours (during waking hours) |
| X/Twitter mentions | <4 hours |
| Email (design partner) | <12 hours |
| Email (press) | <6 hours |

---

## Communication Channels

| Channel | Purpose | Check Frequency |
|---------|---------|----------------|
| GitHub Issues | Bugs, features | Daily |
| GitHub Discussions | Questions, show-and-tell, design partners | Daily |
| Hacker News | Launch post, community discussion | Daily (hourly during launch week) |
| X / Twitter | Mentions, community | Daily |
| LinkedIn | Professional mentions | Weekly |
| Maintainer Chat (Slack/Discord) | Internal coordination | As needed |
| Email | Private inquiries, press, security | Daily |
| PyPI | Download stats | Weekly |

---

## Post-Launch Calendar

| Date | Milestone | Action |
|------|-----------|--------|
| Day 0 | Launch | Execute launch week procedures |
| Day 3 | First pulse check | Review metrics, adjust if needed |
| Day 7 | End of launch week | Weekly sync + retrospective post |
| Day 14 | Two-week review | Evaluate if targets are realistic; adjust |
| Day 30 | Month-one review | Full metrics review; plan month 2 priorities |
| Day 60 | Two-month review | Assess sustainability; onboard new maintainers if growth justifies |
| Day 90 | Quarter review | Roadmap review; community health check |

---

## On-Call Rotation

| Week | Primary | Backup |
|------|---------|--------|
| Week 1 (Launch) | {{name}} | {{name}} |
| Week 2 | {{name}} | {{name}} |
| Week 3 | {{name}} | {{name}} |
| Week 4 | {{name}} | {{name}} |

**Primary responsibilities:** Daily checks, issue triage, HN/social responses.  
**Backup responsibilities:** Step in if primary is unavailable; handle P0 if primary doesn't respond within 1 hour.

Rotate weekly. Announce the rotation in maintainer chat every Sunday.

---

## Reminders & Quick Links

**Daily (5 min):**
- GitHub Issues: https://github.com/avs-gateway/avs/issues
- GitHub PRs: https://github.com/avs-gateway/avs/pulls
- GitHub Discussions: https://github.com/avs-gateway/avs/discussions
- HN Search: https://hn.algolia.com/WARNINGq=AVS+Gateway
- CI Status: https://github.com/avs-gateway/avs/actions

**Weekly (30 min):**
- Metrics spreadsheet: `{{url}}`
- Landscape scan: Google Alerts + manual search
- Weekly sync: `{{calendar_link}}`

---

*This document is a living file. Update it based on what actually happens. If a check is useless, remove it. If a new channel matters, add it. The goal is usefulness, not completeness.*
