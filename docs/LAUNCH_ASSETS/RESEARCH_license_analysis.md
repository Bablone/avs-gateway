# Open-Source License Analysis for AVS Gateway

**Date:** June 2026  
**Context:** AVS Gateway is Apache 2.0 licensed, pre-launch, targeting both developers (free) and enterprises (paid). Evaluating license strategy for a "Runtime Permission Layer" category-defining product.  
**Researcher:** License Impact Analyst  

---

## Q1: BSL 1.1 Precedents — What Happened?

### Key Finding
HashiCorp's switch to BSL 1.1 in August 2023 triggered the most severe community backlash of any license change in the 2018-2024 wave. Within days, a consortium of 40+ companies (including AWS, Google Cloud, Cloudflare, Gruntwork, Harness, Spacelift, env0) formed to fork Terraform as OpenTofu under Linux Foundation governance. Financially, HashiCorp's revenue growth slowed dramatically (from 30%+ to <2% QoQ), the company never achieved profitability, and it was ultimately acquired by IBM for $6.4 billion in February 2025 — below its IPO valuation of ~$13 billion. The BSL change did not demonstrably improve HashiCorp's financial trajectory, and the OpenTofu fork now commands ~12% market share among IaC practitioners with 27% of teams planning to evaluate it.

### Data Points
| Event | Date | Detail |
|-------|------|--------|
| HashiCorp BSL announcement | Aug 10, 2023 | Switched from MPL 2.0 to BSL 1.1 for all products |
| OpenTofu fork announced | Aug 25, 2023 | 40+ companies pledged support |
| OpenTofu 1.6 release | Jan 2024 | First release under Linux Foundation governance |
| IBM acquisition announced | Apr 24, 2024 | $6.4 billion at $35/share (below ~$13B IPO valuation) |
| IBM acquisition closed | Feb 27, 2025 | HashiCorp now operates as division of IBM Software |
| HashiCorp FY2024 revenue | Jan 31, 2024 | $583.1M (growth slowing, not accelerating post-BSL) |
| OpenTofu market share | Apr 2026 | ~12% adoption among IaC practitioners; 27% planning evaluation |
| Terraform market share | Apr 2026 | 33-62% depending on measurement methodology |

### Fork Precedents Post-License Changes
| Original | Fork | Date | Backers | Outcome |
|----------|------|------|---------|---------|
| Terraform (BSL) | OpenTofu | Aug 2023 | Linux Foundation, 40+ companies | 12% market share, active development |
| Redis (SSPL) | Valkey | Mar 2024 | Linux Foundation, AWS, Google, Oracle | 19.8K GitHub stars in year 1; 16-37% faster than Redis 8.0 |
| Elasticsearch (SSPL) | OpenSearch | Jan 2021 | AWS, Linux Foundation | AWS-managed; significant adoption |

### Sources
- https://www.infoq.com/news/2023/08/hashicorp-adopts-bsl/
- https://opentofu.org/
- https://medium.com/@surbhi19/terraform-vs-opentofu-in-2026-6653dd4fa1c0
- https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp
- https://www.hashicorp.com/en/blog/hashicorp-joins-ibm
- https://www.softwareseni.com/the-open-source-license-change-pattern-mongodb-to-redis-timeline-2018-to-2026-and-what-comes-next/

---

## Q2: FSL (Functional Source License) — Alternative?

### Key Finding
FSL is Sentry's streamlined evolution of BSL, designed to fix BSL's two major flaws: (1) excessive variability due to the "Additional Use Grant" making every BSL essentially a different license, and (2) the 4-year non-compete period being too long. FSL standardizes a 2-year conversion to Apache 2.0 or MIT, removes the Additional Use Grant entirely, and replaces it with a clear "Permitted Purpose" definition. Sentry has been the primary adopter and champion. The company brands FSL as part of the "Fair Source" movement. As of August 2024, Sentry passed $100M ARR and 100,000 cloud customers — but this growth trajectory began under BSL, not FSL specifically. FSL is too new (November 2023) to have independent financial outcome data. Community reception was mixed: compliance departments appreciated the standardization, but FOSS purists (including OSI leadership) criticized it as another departure from true open source.

### FSL vs BSL Comparison
| Attribute | BSL 1.1 | FSL 1.1 |
|-----------|---------|---------|
| Non-compete period | 4 years (configurable) | 2 years (fixed) |
| Conversion license | Configurable | Apache 2.0 or MIT (fixed) |
| Additional Use Grant | Yes (custom per implementation) | No — replaced by "Permitted Purpose" |
| License variability | High — each implementation is different | Low — standardized terms |
| Compliance friendliness | Low — legal review required per project | Higher — can be blanket-approved |
| OSI approved | No | No |
| Adopters | HashiCorp, CockroachDB, MariaDB, Sentry (formerly) | Sentry, Codecov, GitButler, Keygen, PowerSync |

### Data Points
- Sentry raised $90M Series E in May 2022 at $3B+ valuation (under BSL at the time)
- Sentry passed $100M ARR and 100,000 cloud customers by August 2024 (after FSL transition)
- Sentry donated $500K to open-source maintainers in 2024
- FSL was developed openly on GitHub with participation from 10+ contributors over 2 months
- Thierry Carrez (OSI VP): criticized Sentry for "abandoning the model that made them successful"
- Peter Zaitsev (Percona founder): "Two years or Three Years — does not matter. What you tend to get is useless unsupported security bug-ridden code."

### Sources
- https://fsl.software/
- https://blog.sentry.io/introducing-the-functional-source-license-freedom-without-free-riding/
- https://blog.sentry.io/sentry-is-now-fair-source/
- https://www.infoq.com/news/2023/12/functional-source-license/
- https://techcrunch.com/2023/11/20/with-functional-source-license-sentry-wants-to-grant-developers-freedom-without-harmful-free-riding/

---

## Q3: Open Core Business Models — What Works?

### Key Finding
The open-core model — keeping the core product fully open-source under a permissive license while monetizing enterprise features separately — has the strongest track record for maximizing BOTH developer adoption AND enterprise revenue. GitLab is the canonical success story: MIT-licensed Community Edition drove massive adoption ($11B valuation, 50%+ of Fortune 100 as customers), while Enterprise Edition monetized compliance, security, and scale features. GitLab's public promise — "when a feature is open source, we won't move that feature to a paid tier" — became a key trust signal. MongoDB ($2B+ revenue) and Elastic ($1.48B revenue) both grew significantly, but their license changes to SSPL caused community damage that required management. Critically, RedMonk analysis found that "no evidence shows license changes improved revenue trajectories" — MongoDB's growth predated SSPL, Elastic's growth declined post-change, and HashiCorp was acquired rather than achieving independent growth.

### Model Comparison
| Company | Model | Core License | Enterprise | Revenue (Latest) | Outcome |
|---------|-------|------------|------------|------------------|---------|
| **GitLab** | Open Core | MIT (CE) | Proprietary EE features | ~$500M+ (2021 valuation $11B) | **Best practice exemplar** — max adoption + revenue |
| **Sentry** | BSL→FSL (all features) | FSL (converts to Apache 2.0 after 2yr) | SaaS hosting + support | $100M+ ARR | Strong revenue; "Fair Source" branding |
| **MongoDB** | SSPL (whole product) | SSPL (not OSI-approved) | MongoDB Atlas (managed) | $2.0B (FY2025) | Strong revenue; limited community damage (no major fork) |
| **Elastic** | SSPL + Elastic License | SSPL/Elastic License | Elastic Cloud | $1.48B (FY2025) | Growth declined post-change; reverted to add AGPL option in 2024 |
| **HashiCorp** | BSL (whole product) | BSL 1.1 | HCP (managed) + Enterprise | $583M (FY2024) | Acquired by IBM for $6.4B; OpenTofu fork at 12% share |
| **Redis** | SSPL + RSALv2 | Source-available | Redis Enterprise/Cloud | N/A (private) | Valkey fork with massive community backing |
| **CockroachDB** | BSL | BSL | CockroachDB Enterprise | N/A (private) | Strong technical reputation; smaller community |

### Critical Insight from RedMonk Analysis
> "While in our sample we see revenue grow post-license change, we don't see a notable change in the rate of growth. We also see very mixed results in company valuation, and there does not seem to be a clear link between moving from an open source to proprietary license and increasing the company's value." — Rachel Stephens, RedMonk, August 2024

### What Separates Winners from Losers
| Factor | Success Pattern | Failure Pattern |
|--------|----------------|-----------------|
| Governance | Clear feature boundary (what's free vs paid) | Ambiguous "competing use" definitions |
| Community trust | Public promise not to remove open features | Relicensing after years of open-source positioning |
| Enterprise value | Features that matter at scale (SSO, audit, compliance) | Gating basic functionality |
| Developer experience | Self-hosted works fully for small teams | Self-hosted is deliberately crippled |
| Foundation backing | Optional but stabilizing (CNCF, Linux Foundation) | Single-vendor control breeds fork risk |

### Sources
- https://redmonk.com/rstephens/2024/08/26/software-licensing-changes-and-their-impact-on-financial-outcomes/
- https://www.reo.dev/blog/the-open-source-moat-how-gitlabs-developer-community-drove-11b-in-value
- https://handbook.gitlab.com/handbook/company/stewardship/
- https://palark.com/blog/open-source-business-models/
- https://milvus.io/ai-quick-reference/what-are-opencore-business-models

---

## Q4: The "AWS Problem" — Is It Real for Early-Stage?

### Key Finding
The "AWS problem" is real but ONLY at significant scale. AWS does not copy small, early-stage open-source projects. Every documented case of AWS launching a competing managed service (DocumentDB for MongoDB, ElastiCache for Redis, OpenSearch for Elasticsearch) involved projects that had already achieved massive adoption (millions of users, tens of thousands of organizations) and were generating hundreds of millions in revenue. The typical timeline is 5-10 years from open-source launch to AWS competitive threat. For a pre-launch category creator like AVS Gateway, the AWS threat is near-zero for the first 3-5 years. The far greater risk is that restrictive licensing will suppress developer adoption and community formation — the very things needed to reach AWS-threat scale in the first place. Foundation-governed projects (PostgreSQL, Kubernetes) have never faced this issue; single-vendor control is the actual risk factor.

### Timeline of AWS "Copying" Events
| Year | Event | Target Scale at Time |
|------|-------|---------------------|
| 2018 | AWS DocumentDB launches (MongoDB-compatible) | MongoDB: $267M revenue, IPO'd, millions of users |
| 2019 | AWS OpenSearch fork (from Elasticsearch 7.10) | Elastic: ~$500M+ revenue, dominant search platform |
| 2021 | AWS Memorystore (Redis-compatible) | Redis: 15 years of BSD licensing, ubiquitous infrastructure |
| 2024 | AWS ElastiCache adds Valkey support | Redis: effectively replaced by Valkey fork |

### What AWS Actually Does
- AWS targets **infrastructure categories** with massive TAM (databases, search, caching, orchestration)
- AWS requires **proven market demand** — millions of users, enterprise adoption, ecosystem lock-in
- AWS rarely copies **application-layer** or **developer tools** — focuses on infrastructure primitives
- AWS contributed to the Valkey fork (2024) — showing they respond to license changes by forking, not paying

### The Real Risk Factors for License Changes
Per industry analysis, the consistent pattern for license changes shows:
1. **Single-company ownership** (>80% of commits)
2. **No independent foundation governance**
3. **Cloud provider managed services already competing**
4. **Recent VC funding** with growth expectations
5. **Public sustainability complaints**
6. **Declining external contributors**

For AVS Gateway (pre-launch, no stars, category-creating), **zero of these conditions apply**.

### Sources
- https://www.softwareseni.com/the-open-source-license-change-pattern-mongodb-to-redis-timeline-2018-to-2026-and-what-comes-next/
- https://www.linuxfoundation.org/blog/a-year-of-valkey
- https://redmonk.com/rstephens/2024/08/26/software-licensing-changes-and-their-impact-on-financial-outcomes/

---

## Q5: Developer Adoption Impact by License

### Key Finding
There is no quantitative survey data showing precise GitHub star growth differentials by license type. However, the qualitative evidence is overwhelming: every major license change from open-source to source-available (BSL/SSPL/RSALv2) triggered immediate fork creation, negative HackerNews sentiment, and ecosystem fragmentation. The most telling metric is that all four major license changes (MongoDB 2018, Elastic 2021, HashiCorp 2023, Redis 2024) produced forks with significant backing. Among the developer community, the "don't care" group is largest (per Stephen O'Grady, RedMonk), but the vocal minority who DO care are exactly the contributors, early adopters, and evangelists that a pre-launch project needs most. Sentry's FSL is explicitly designed to reduce compliance friction because "compliance departments at over 10,000 organizations" had to individually evaluate BSL terms.

### Developer Sentiment Patterns
| License Type | Developer Reception | Enterprise Reception |
|-------------|--------------------|---------------------|
| MIT / Apache 2.0 | Universally positive; no friction | Easy compliance approval; standard |
| BSD / ISC | Positive; minimal restrictions | Easy compliance approval |
| GPL / AGPL | Mixed — idealistic appeal; practical concerns about virality | Often blocked by legal departments |
| BSL | Negative — "bait and switch" perception; forks within days | Requires individual legal review per implementation |
| FSL | Mixed — better than BSL but still not OSI-approved | Better than BSL; standardized terms help |
| SSPL | Negative — seen as most restrictive | Often blocked; MongoDB/Elastic-specific exceptions |

### Key Evidence
- HashiCorp BSL: 40+ companies immediately joined OpenTofu consortium; "initial community reaction has primarily been negative" (InfoQ)
- Redis SSPL: 150+ contributors, 1000+ commits to Valkey within months; Aiven migrated 15,000 servers
- Elastic SSPL: AWS forked OpenSearch immediately; Elastic later added AGPL option (2024) due to community pressure
- MongoDB SSPL: No major fork emerged — suggesting SSPL was less offensive to community than BSL, or MongoDB's managed offering was strong enough
- > "By far the largest group is 'those that don't care'" — Stephen O'Grady, RedMonk, on license preferences

### The "Contributor Deterrence" Effect
| Project | External Contributors Pre-Change | Post-Change Trend |
|---------|----------------------------------|--------------------|
| HashiCorp Terraform | 1000+ ecosystem tools | Fragmented between Terraform and OpenTofu |
| Redis | Massive contributor base | Split between Redis and Valkey |
| Elasticsearch | Large ecosystem | Split between Elastic and OpenSearch |

### Sources
- https://victoriametrics.com/blog/bsl-is-short-term-fix-why-we-choose-open-source/
- https://medium.com/@fintanr/the-hashicorp-bsl-move-ee79659a0b54
- https://news.ycombinator.com/item?id=37239979
- https://www.infoq.com/news/2023/08/hashicorp-adopts-bsl/

---

## Q6: Optimal License Strategy for AVS Gateway

### Analysis of Options

#### Option A: Apache 2.0 core + proprietary enterprise add-ons (OPEN CORE)
**Mechanism:** Core runtime remains Apache 2.0. Enterprise features (control plane, policy packs, hosted dashboard, compliance mappings) are proprietary and distributed under a commercial license.  
**Precedent:** GitLab — MIT CE + proprietary EE = $11B valuation, 50%+ Fortune 100 customers.  
**Pros:** Maximum developer adoption; easy compliance; no fork risk; clear value proposition for enterprise upsell; community contributions to core; can build ecosystem.  
**Cons:** AWS could theoretically copy the open core (but only at scale, years away); need to maintain clear feature boundary.  
**Verdict:** STRONGEST OPTION.

#### Option B: BSL 1.1 everything
**Mechanism:** All code under BSL 1.1, converts to Apache 2.0 after 4 years. No proprietary add-ons.  
**Precedent:** HashiCorp — led to OpenTofu fork, IBM acquisition below IPO price, 12% market share loss to fork.  
**Pros:** Prevents AWS copying; all features visible.  
**Cons:** Compliance friction from day one; "source-available" not "open source" = reduced developer enthusiasm; fork risk if project becomes popular; 4-year delay is practically forever in software.  
**Verdict:** HIGH RISK for a pre-launch project. The HashiCorp outcome (acquired, below valuation, community fractured) is not a success model to emulate.

#### Option C: FSL everything
**Mechanism:** All code under FSL, converts to Apache 2.0 after 2 years.  
**Precedent:** Sentry — $100M+ ARR, but FSL is too new for independent outcome data.  
**Pros:** Better than BSL (shorter delay, standardized terms); compliance-friendlier; "Fair Source" branding.  
**Cons:** Still not OSI-approved; "source-available" not "open source"; 2 years is still a long competitive delay; pre-launch project needs maximum openness, not restrictions.  
**Verdict:** BETTER THAN BSL, but unnecessary restriction for a project that hasn't launched yet.

#### Option D: Apache 2.0 everything + dual-license enterprise
**Mechanism:** Everything open-source under Apache 2.0. Revenue from support, services, and optionally dual-licensing for enterprises that want a commercial agreement.  
**Precedent:** Red Hat — support/services model, acquired by IBM for $34B. Most "pure" open-source approach.  
**Pros:** Maximum trust; maximum adoption; easiest ecosystem building.  
**Cons:** Harder to monetize directly; relies on services/support revenue which scales linearly with headcount, not exponentially.  
**Verdict:** VIABLE but monetization may be harder for a developer tool category.

#### Option E: AGPL core + proprietary enterprise
**Mechanism:** Core under AGPL (strong copyleft), enterprise add-ons proprietary.  
**Precedent:** Ghost (blogging platform); some security tools.  
**Pros:** Strong protection against cloud providers not contributing back.  
**Cons:** AGPL is frequently blocked by corporate legal departments; dramatically reduces adoption; incompatible with many use cases; "viral" nature scares developers.  
**Verdict:** TOO RESTRICTIVE for a developer-facing infrastructure tool. Would suppress adoption significantly.

### Comparative Scoring Matrix (for AVS Gateway context)
| Criteria | Option A (Open Core) | Option B (BSL) | Option C (FSL) | Option D (Apache All) | Option E (AGPL) |
|----------|---------------------|----------------|----------------|----------------------|-----------------|
| Developer adoption | 5/5 | 2/5 | 3/5 | 5/5 | 1/5 |
| Enterprise revenue potential | 5/5 | 3/5 | 3/5 | 3/5 | 3/5 |
| AWS protection (near-term) | 2/5 | 4/5 | 4/5 | 1/5 | 4/5 |
| AWS protection (long-term) | 4/5 | 3/5 | 3/5 | 2/5 | 4/5 |
| Community trust / ecosystem | 5/5 | 1/5 | 2/5 | 5/5 | 1/5 |
| Compliance friction | 5/5 | 1/5 | 2/5 | 5/5 | 1/5 |
| Fork risk | 1/5 | 5/5 | 4/5 | 1/5 | 3/5 |
| Category creation support | 5/5 | 2/5 | 3/5 | 5/5 | 1/5 |
| **TOTAL** | **32/40** | **21/40** | **24/40** | **27/40** | **18/40** |

---

## RECOMMENDATION FOR AVS GATEWAY

### Recommended Strategy: Option A — Open Core (Apache 2.0 + Proprietary Enterprise)

#### Core Architecture
```
AVS Gateway Core (Apache 2.0):
  - Runtime permission engine
  - Basic policy language
  - Standalone deployment
  - Community SDKs and integrations
  - Core documentation

AVS Enterprise (Proprietary):
  - Control plane / management dashboard
  - Pre-built policy packs (SOC2, HIPAA, etc.)
  - Hosted/managed service option
  - Compliance mapping and reporting
  - SSO / RBAC / audit logging
  - Enterprise support (SLA)
  - Multi-cluster federation
```

#### Specific Recommendations

1. **Keep the runtime engine Apache 2.0.** This is the "category creator" — it needs maximum adoption. Every developer should be able to `docker run avs-gateway` with zero license concerns. The runtime IS the developer experience.

2. **Make the open-source core genuinely useful.** GitLab's success came because CE was a complete DevOps platform, not a toy. AVS core should handle real permission scenarios for small-to-medium deployments. Don't cripple it.

3. **Public commitment:** Publish a clear statement — "Features in the open-source core will never be moved to proprietary tiers." This is GitLab's exact playbook and it built enormous trust.

4. **Enterprise tier targets scale and compliance.** The decision to pay should be obvious at enterprise scale: multiple clusters, compliance requirements, centralized management, audit trails, SSO. These are inherently enterprise concerns, not developer concerns.

5. **Revisit licensing only if/when AWS threat materializes.** At that point (likely 5+ years away, if ever), the project will have enough momentum and enterprise customers that a license change would be a considered business decision — not a pre-launch gamble.

6. **Consider donating to a foundation after traction.** Once AVS has significant adoption, consider CNCF or similar foundation governance. This is the single strongest protection against both AWS copying AND community fork risk.

#### Why This Is the Right Choice for AVS Specifically

| AVS Attribute | Why Open Core Fits |
|---------------|-------------------|
| Pre-launch, no stars | Need maximum openness to attract first users and contributors |
| Category creator ("Runtime Permission Layer") | Need ecosystem to form; restrictive licensing suppresses ecosystem formation |
| Targeting developers (free) AND enterprises (paid) | Open Core explicitly serves both audiences |
| Design partner program | Enterprises will evaluate both open-source core and paid features; need both to be strong |
| No AWS threat yet | The problem that BSL/FSL solve does not exist for AVS today |

#### The Bottom Line

Every piece of evidence from the 2018-2024 "license change wave" points to the same conclusion: license changes from open-source to source-available do not improve revenue trajectories, damage community trust, and create fork risk. The projects that have maximized both developer adoption AND commercial success — GitLab being the clearest example — used open core with a permissive license for the core product.

For AVS Gateway specifically, the risk of suppressing early adoption with BSL/FSL restrictions far exceeds the theoretical risk of AWS copying a pre-launch project. The optimal strategy is to build the biggest possible open-source community around an Apache 2.0 core, monetize enterprise features separately, and only reconsider if the project achieves the scale where AWS competition becomes a realistic concern.

---

## SOURCES INDEX

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | HashiCorp Adopts BSL — InfoQ | https://www.infoq.com/news/2023/08/hashicorp-adopts-bsl/ | Q1 |
| 2 | OpenTofu Official Site | https://opentofu.org/ | Q1 |
| 3 | Terraform vs OpenTofu 2026 | https://medium.com/@surbhi19/terraform-vs-opentofu-in-2026-6653dd4fa1c0 | Q1 |
| 4 | IBM Completes HashiCorp Acquisition | https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp | Q1 |
| 5 | HashiCorp Joins IBM Blog | https://www.hashicorp.com/en/blog/hashicorp-joins-ibm | Q1 |
| 6 | FSL Official Site | https://fsl.software/ | Q2 |
| 7 | Sentry Introduces FSL | https://blog.sentry.io/introducing-the-functional-source-license-freedom-without-free-riding/ | Q2 |
| 8 | Sentry is Now Fair Source | https://blog.sentry.io/sentry-is-now-fair-source/ | Q2 |
| 9 | Sentry FSL — InfoQ | https://www.infoq.com/news/2023/12/functional-source-license/ | Q2 |
| 10 | Sentry FSL — TechCrunch | https://techcrunch.com/2023/11/20/with-functional-source-license-sentry-wants-to-grant-developers-freedom-without-harmful-free-riding/ | Q2 |
| 11 | License Changes & Financial Outcomes — RedMonk | https://redmonk.com/rstephens/2024/08/26/software-licensing-changes-and-their-impact-on-financial-outcomes/ | Q3 |
| 12 | GitLab's $11B Open Source Moat | https://www.reo.dev/blog/the-open-source-moat-how-gitlabs-developer-community-drove-11b-in-value | Q3 |
| 13 | GitLab Stewardship Handbook | https://handbook.gitlab.com/handbook/company/stewardship/ | Q3 |
| 14 | Open Core Business Models | https://palark.com/blog/open-source-business-models/ | Q3 |
| 15 | Open Core Models Explained | https://milvus.io/ai-quick-reference/what-are-opencore-business-models | Q3 |
| 16 | License Change Pattern 2018-2026 | https://www.softwareseni.com/the-open-source-license-change-pattern-mongodb-to-redis-timeline-2018-to-2026-and-what-comes-next/ | Q4 |
| 17 | Valkey — A Year Later (Linux Foundation) | https://www.linuxfoundation.org/blog/a-year-of-valkey | Q4 |
| 18 | BSL Is a Short-Term Fix | https://victoriametrics.com/blog/bsl-is-short-term-fix-why-we-choose-open-source/ | Q5 |
| 19 | The HashiCorp BSL Move Analysis | https://medium.com/@fintanr/the-hashicorp-bsl-move-ee79659a0b54 | Q5 |
| 20 | HN Discussion on HashiCorp BSL | https://news.ycombinator.com/item?id=37239979 | Q5 |
| 21 | MongoDB FY2025 Financial Results | https://www.prnewswire.com/news-releases/mongodb-inc-announces-fourth-quarter-and-full-year-fiscal-2025-financial-results-302393702.html | Q3 |
| 22 | Elastic FY2025 Financial Results | https://www.businesswire.com/news/home/20250529237845/en/Elastic-Reports-Fourth-Quarter-and-Fiscal-2025-Financial-Results | Q3 |
| 23 | Elastic Q1 FY2025 (AGPL announcement) | https://www.silicon.co.uk/press-release/elastic-reports-first-quarter-fiscal-2025-financial-results | Q3 |
| 24 | HashiCorp BSL Impact on Organizations | https://www.digitalcorner-wavestone.com/2023/09/how-hashicorps-license-change-impacts-organizations/ | Q1 |
| 25 | Open Source Business Models (Dev.to) | https://dev.to/ryandawsonuk/the-open-core-business-model-363n | Q3 |
| 26 | MongoDB 10-K FY2025 | https://www.tradingview.com/news/tradingview:549364ffdcbf9:0-mongodb-inc-sec-10-k-report/ | Q3 |

---

*Analysis compiled from public financial filings, industry reports, vendor announcements, community forums, and independent research. All financial data sourced from SEC filings or official company announcements.*
