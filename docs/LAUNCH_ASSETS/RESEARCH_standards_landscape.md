# Standards Landscape Research Brief: ASR-1 Action Standard Receipt

**Research Date:** 2025-07-15
**Researcher:** Technical Standards Researcher
**Scope:** Audit Receipt & Agent Identity Standards Landscape for AVS Gateway's ASR-1

---

## Executive Summary

The standards landscape for cryptographically signed, machine-actionable "action receipts" for AI agent governance is **nascent and underspecified**. While foundational building blocks exist across identity (SPIFFE), tamper-evident logging (Certificate Transparency, SCITT), verifiable credentials (W3C VC 2.0), and cloud audit formats (CloudTrail, CEF), **no existing standard directly addresses the specific problem ASR-1 solves**: a JSON-structured, cryptographically signed receipt that proves an AI agent action was intercepted, evaluated by policy, and either allowed, denied, or queued.

Key findings:
1. **W3C VC 2.0** (May 2025) provides a viable data model foundation but is not purpose-built for action attestation.
2. **IETF SCITT** (draft stage) is the closest parallel -- supply chain transparency receipts using COSE/Merkle trees -- but focuses on software artifacts, not agent actions.
3. **Cloud audit formats** (CloudTrail, Azure Activity Logs, Google Cloud Audit Logs) provide structural inspiration but lack cryptographic signatures and are not designed for cross-system agent action attestation.
4. **OWASP Agentic AI** is highly active and represents the best immediate standardization venue for ASR-1 contribution.
5. **SPIFFE** is the leading candidate for agent identity but requires extension for unique agent instance attribution.
6. **No existing standard** called "action receipt" or "execution receipt" was found. This is a greenfield standardization opportunity.

---

## Q1: W3C Verifiable Credentials (VC) Data Model

### Status: **Exists and Adopted** (v2.0 W3C Recommendation, May 15, 2025)

### Key Findings

The W3C published Verifiable Credentials Data Model v2.0 as a **W3C Recommendation on May 15, 2025**, along with six companion specifications: VC Data Integrity 1.0, EdDSA Cryptosuites v1.0, ECDSA Cryptosuites v1.0, Securing VCs using JOSE and COSE, Controlled Identifiers v1.0, and Bitstring Status List v1.0. This represents the first major update since v1.1 (2022) and is backward-compatible with v1.1.

VC 2.0 defines a three-party ecosystem (issuer, holder, verifier) for expressing cryptographically secure, privacy-respecting, machine-verifiable claims. The data model is extensible and supports JSON-LD serialization with multiple securing mechanisms (Data Integrity proofs, JWT/SD-JWT, COSE).

For "action attestation," VC's extensibility allows defining custom credential types that could prove a specific action was taken and governed. The `credentialSubject` block can contain arbitrary claims about an action (what, when, by whom, result). The `evidence` field (Section 5.6) can link to supporting documentation. However, **VCs are designed for identity assertions, not real-time action receipts**. The verification model assumes the credential is presented to a verifier, not that it is produced as an audit artifact.

**No production deployments** of VCs for machine-actionable audit receipts of AI agent actions were found. Current VC use cases focus on human identity (driver's licenses, diplomas, eIDAS 2.0 EUDI wallets, supply chain traceability). The UN Trade Policy (UNTP) uses VCs for trade credentials and traceability events, which is conceptually adjacent but not the same as agent action receipts.

### Implication for ASR-1

ASR-1 could adopt the VC 2.0 data model as its JSON serialization foundation, using the `credentialSubject` to express action details and the `proof` field for cryptographic signing. This would provide immediate standards credibility and alignment with EU eIDAS 2.0. However, the three-party (issuer/holder/verifier) model does not cleanly map to the agent action governance model (interceptor/evaluator/receipt-consumer). A VC profile specific to action receipts would need to be defined.

### Sources

- W3C VC Data Model 2.0 Recommendation: https://www.w3.org/TR/vc-data-model-2.0/ (published 2025-05-15)
- W3C Press Release: https://www.w3.org/press-releases/2025/verifiable-credentials-2-0/
- W3C VC Overview: https://www.w3.org/TR/vc-overview/
- EU Digital Identity Wallet reference: https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/issues/115
- UNTP VC Profile: https://untp.unece.org/docs/0.6.0/specification/VerifiableCredentials/

---

## Q2: IETF / Internet Standards for Audit Receipts

### Status: **Building Blocks Exist; No Direct Standard**

### Key Findings

**Tamper-Evident Logs (Certificate Transparency):**
- **RFC 6962** (Certificate Transparency, June 2013, Experimental) -- defines append-only logs of TLS certificates using Merkle trees, signed certificate timestamps (SCTs), and inclusion proofs. Enables anyone to audit CA activity.
- **RFC 9162** (Certificate Transparency Version 2.0, December 2021, Experimental) -- obsoletes RFC 6962. Adds hash/signature algorithm agility, precertificate format changes, TransItem structure, unified leaf format, and the `transparency_info` TLS extension. Widely implemented by CAs and browsers (Chrome requires CT compliance).

These standards provide the **cryptographic primitives** for tamper-evident logging (Merkle trees, inclusion proofs, signed timestamps) but are specific to TLS certificates, not general-purpose action receipts.

**OAuth / JWT Authentication (RFC 7523):**
- **RFC 7523** (May 2015, Standards Track) -- defines using JWT as both an authorization grant and client authentication mechanism in OAuth 2.0. Enables machine-to-machine authentication without shared secrets (private_key_jwt). Required claims: `iss`, `sub`, `aud`, `exp`. Supports optional `jti` for replay protection.
- This is relevant for ASR-1's signing layer: JWTs with the required claims map naturally to receipt fields (issuer = gateway, subject = action ID, audience = recipient, expiration = receipt validity).

**Supply Chain Integrity (SCITT) -- Closest Parallel:**
- **IETF SCITT Working Group** (Supply Chain Integrity, Transparency, and Trust) -- active WG with multiple drafts:
  - `draft-ietf-scitt-architecture` -- defines architecture for transparency services maintaining append-only logs of signed statements (claims) about artifacts
  - `draft-ietf-scitt-receipts` -- defines **cryptographic receipts** (COSE-based) issued by transparency services proving a claim was registered
  - `draft-ietf-scitt-scrapi` -- SCITT Reference APIs (Waiting for AD Go-Ahead, Proposed Standard)
  - `draft-ietf-scitt-receipts-ccf-profile` -- CCF Profile for COSE Receipts
  - `draft-scitt-eu-ai-act-receipts` -- **A SCITT Profile for EU AI Act Article 50 Transparency Receipts** (2026-05)

SCITT receipts use COSE envelopes and Merkle tree inclusion proofs. They are "offline, universally-verifiable proof that a claim is recorded in the registry." Microsoft's Signing Transparency service is a production implementation using SCITT-compliant COSE envelopes.

**No IETF drafts** specifically titled "action receipt" or "audit receipt" for agent actions were found. SCITT's EU AI Act receipt profile is the most adjacent active work.

### Implication for ASR-1

ASR-1 should leverage SCITT's receipt concept and COSE signing envelope as a reference for its cryptographic layer. The IETF SCITT WG, particularly the EU AI Act receipts draft, represents a viable path for future standardization of action receipts. RFC 7523's JWT profile provides a simpler, more widely implemented signing alternative to COSE. ASR-1 could offer both JWT (for simplicity) and COSE (for SCITT alignment) signing options.

### Sources

- RFC 6962: https://datatracker.ietf.org/doc/html/rfc6962
- RFC 9162: https://datatracker.ietf.org/doc/html/rfc9162
- RFC 7523: https://datatracker.ietf.org/doc/html/rfc7523
- IETF SCITT WG: https://datatracker.ietf.org/wg/scitt/
- SCITT Architecture draft: https://datatracker.ietf.org/doc/html/draft-ietf-scitt-architecture-22
- SCITT Receipts: https://datatracker.ietf.org/doc/draft-ietf-scitt-receipts/
- EU AI Act SCITT Receipts: https://datatracker.ietf.org/doc/draft-scitt-eu-ai-act-receipts/
- Microsoft Signing Transparency: https://azure.microsoft.com/en-us/blog/enhancing-software-supply-chain-security-with-microsofts-signing-transparency/

---

## Q3: Cloud-Native / Industry Audit Formats

### Status: **Multiple Mature Formats; None Cryptographically Signed**

### Key Findings

**SIEM Event Formats:**
- **CEF (Common Event Format)** -- Open log management standard originally developed by ArcSight (now OpenText). Format: `CEF:Version|Device Vendor|Device Product|Device Version|Device Event Class ID|Name|Severity|[Extension]` where Extension is key-value pairs. Extension dictionary includes predefined keys (src, dst, suser, duser, filePath, etc.) plus custom extensions. Widely adopted across SIEM vendors.
- **LEEF (Log Event Extended Format)** -- Proprietary format for IBM QRadar. Header: `LEEF:Version|Vendor|Product|Version|EventID|` with tab-separated key-value attributes. Predefined attributes include src, dst, usrName, devTime, sev (severity 1-10), cat (category). Less widely adopted than CEF.
- **STIX/TAXII** -- OASIS-managed standards for cyber threat intelligence sharing. STIX (Structured Threat Information eXpression) defines JSON-based threat objects (indicators, TTPs, threat actors). TAXII (Trusted Automated eXchange of Intelligence Information) defines HTTPS-based transport protocols. Used by governments, ISACs, CERTs. Not directly applicable to agent action receipts but provides a model for structured, machine-readable security event exchange.

**Cloud Provider Audit Log Formats:**

*AWS CloudTrail:*
```json
{
  "eventTime": "2024-01-01T00:00:00Z",
  "eventName": "PutObject",
  "eventSource": "s3.amazonaws.com",
  "awsRegion": "us-east-1",
  "sourceIPAddress": "1.2.3.4",
  "userAgent": "...",
  "userIdentity": { "type": "IAMUser", "principalId": "...", "arn": "..." },
  "requestParameters": { ... },
  "responseElements": { ... }
}
```
Key fields: eventTime, eventName, eventSource, awsRegion, sourceIPAddress, userAgent, userIdentity (type, principalId, ARN, accountId), requestParameters, responseElements. Not cryptographically signed. Designed for AWS-internal API call auditing.

*Google Cloud Audit Logs:*
```json
{
  "protoPayload": {
    "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
    "serviceName": "compute.googleapis.com",
    "methodName": "beta.compute.instances.insert",
    "resourceName": "projects/.../zones/.../instances/...",
    "authenticationInfo": { "principalEmail": "..." },
    "authorizationInfo": [{ "permission": "...", "granted": true }],
    "requestMetadata": { "callerIp": "...", "callerSuppliedUserAgent": "..." },
    "status": { "code": 0 }
  },
  "timestamp": "...",
  "severity": "NOTICE"
}
```
Key fields: serviceName, methodName, resourceName, authenticationInfo (principalEmail), authorizationInfo (permission, granted), requestMetadata (callerIp, callerSuppliedUserAgent), status, timestamp. Uses Protocol Buffer serialization. Not cryptographically signed.

*Azure Activity Logs:*
```json
{
  "authorization": { "action": "...", "scope": "..." },
  "caller": "user@contoso.com",
  "correlationId": "...",
  "eventDataId": "...",
  "eventName": { "value": "EndRequest", "localizedValue": "End request" },
  "category": { "value": "Administrative", "localizedValue": "Administrative" },
  "eventTimestamp": "...",
  "operationName": { "value": "Microsoft.Network/networkSecurityGroups/write" },
  "resourceId": "...",
  "status": { "value": "Succeeded" },
  "properties": { "statusCode": "Created" }
}
```
Key fields: authorization (action, scope), caller, correlationId, eventDataId, eventName, category, eventTimestamp, operationName, resourceId, status, properties. Categories include Administrative, ServiceHealth, ResourceHealth, Alert, Autoscale, Recommendation, Security, Policy. Not cryptographically signed.

**OpenTelemetry GenAI Semantic Conventions:**
The OpenTelemetry GenAI SIG (since April 2024) has developed semantic conventions for LLM observability. As of v1.41 (May 2026), the conventions remain in **Development/Experimental** status. Key agent-relevant span types:
- `invoke_agent` -- agent task invocation (CLIENT for remote, INTERNAL for local)
- `execute_tool` -- tool execution with tool name in span name
- `invoke_workflow` -- predefined workflow execution
- MCP (Model Context Protocol) semantic conventions (v1.39) for trace context propagation

Attributes include: `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.agent.name`, `gen_ai.tool.name`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`. These are for **observability telemetry**, not cryptographic attestation.

### Implication for ASR-1

Cloud audit formats provide excellent structural templates for ASR-1's JSON schema. The common patterns across CloudTrail, Google Cloud Audit Logs, and Azure Activity Logs (who, what, when, where, result, authorization context) should inform ASR-1's field design. However, none of these formats are cryptographically signed or designed for cross-system attestation. ASR-1's key differentiator is the cryptographic signature + policy decision record, which none of these formats provide. ASR-1 could potentially embed within CEF's extension dictionary or define a CEF-compatible adapter for SIEM ingestion.

### Sources

- CEF Implementation Standard: https://www.microfocus.com/documentation/arcsight/arcsight-smartconnectors-8.3/cef-implementation-standard/
- LEEF Format Guide: https://www.ibm.com/docs/SS42VS_DSM/pdf/b_Leef_format_guide.pdf
- STIX/TAXII Overview: https://www.cloudflare.com/learning/security/what-is-stix-and-taxii/
- AWS CloudTrail Event Reference: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference.html
- Google Cloud Audit Log Format: https://docs.cloud.google.com/logging/docs/reference/audit/auditlog/rest/Shared.Types/AuditLog
- Azure Activity Log Event Schema: https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log-schema
- OpenTelemetry GenAI Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OpenTelemetry Agent Spans: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/

---

## Q4: OWASP Agentic AI Project

### Status: **Highly Active; Standards Being Developed**

### Key Findings

The OWASP GenAI Security Project is the most active industry initiative focused on agentic AI security. Key deliverables as of mid-2025:

1. **OWASP Top 10 for Agentic Applications 2026** (published November 2025) -- peer-reviewed framework identifying critical security risks for autonomous/agentic AI systems, developed with 100+ industry contributors. Covers agent goal hijacking, tool misuse, insecure communication, etc.

2. **OWASP Agentic Skills Top 10 (AST10)** -- documents top 10 security risks in agentic AI skills across platforms (OpenClaw/SKILL.md YAML, Claude Code/skill.json, Cursor/Codex/manifest.json, VS Code/package.json). Focuses on the "behavior layer" between MCP (tool layer) and the application.

3. **A Practical Guide for Secure MCP Server Development** (February 2026) -- actionable guidance for securing Model Context Protocol servers.

4. **OWASP AIBOM Generator** (December 2025) -- open-source tool for generating AI Bills of Materials (AIBOMs) for AI supply chain transparency.

5. **Threat Defense COMPASS 1.0** (September 2025) -- unified AI threat resilience strategy dashboard consolidating threats, vulnerabilities, defenses, and mitigations.

6. **FinBot Agentic AI CTF** (August 2025) -- hands-on capture-the-flag application for understanding agentic AI risks.

7. **Regular Summits** -- Agentic AI Summit Europe (London, December 2025), RSAC 2026 Summit (March 2026), Infosec Europe Summit (June 2026).

**Opportunity for ASR-1 Contribution:** The OWASP GenAI Security Project is actively developing standards, taxonomies, and reference implementations but has **no specific output format for agent action auditing**. ASR-1 could be contributed as:
- A reference output format for agent action audit trails
- An integration point for the OWASP AIBOM (agent actions as part of the AI supply chain)
- An enforcement mechanism for the OWASP Top 10 for Agentic Applications (e.g., producing receipts for security-critical agent actions)

### Implication for ASR-1

OWASP represents the best immediate standardization venue. ASR-1 should be proposed as an output format standard within the OWASP GenAI Security Project. The alignment with OWASP Top 10 for Agentic Applications provides immediate use cases, and the AIBOM work provides supply chain context. The regular summit schedule provides venues for presentation and community building.

### Sources

- OWASP GenAI Security Project: https://genai.owasp.org/
- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resources/ (published 2025-11-04)
- OWASP Agentic Skills Top 10: https://owasp.org/www-project-agentic-skills-top-10/
- Resources Archive: https://genai.owasp.org/resources/
- Events: https://genai.owasp.org/events/

---

## Q5: Existing "Action Receipt" or "Execution Receipt" Standards

### Status: **Nothing Found** -- Greenfield Opportunity

### Key Findings

**No standard called "action receipt" or "execution receipt" exists.** Comprehensive searches across IETF, W3C, OASIS, ISO, and industry sources found no standard specifically designed for cryptographically signed receipts of individual action evaluations.

**Adjacent but not equivalent efforts:**

1. **Asqav** (commercial product, jagmarques/asqav-langchain on GitHub) -- produces signed `tool:start`, `tool:end`, and `tool:error` events through LangChain's `BaseCallbackHandler` (`on_tool_start`, `on_tool_end`, `on_tool_error`). Uses NIST FIPS 204 ML-DSA cryptography server-side. Fail-open design. This is a **product, not a standard**, but validates the market need for signed agent action records.

2. **OpenTelemetry GenAI Semantic Conventions** (experimental) -- standardizes observability spans for agent actions (`invoke_agent`, `execute_tool`) but focuses on **telemetry/tracing**, not cryptographic attestation. The `execute_tool` span naming requires the tool name (v1.41). No policy decision or signature concepts.

3. **No proposals from major AI labs** -- No published action receipt format proposals from LangChain, Anthropic, or OpenAI were found. LangChain has callback handlers for observation but no signed receipt standard. Anthropic has no public action receipt specification. OpenAI has no action attestation format.

4. **No "ASR" (Action Standard Receipt)** -- The exact term "Action Standard Receipt" or "ASR-1" is not used by any existing standard.

### Implication for ASR-1

ASR-1 occupies a **genuinely novel standardization niche**. The absence of any direct competitor or equivalent standard gives AVS Gateway first-mover advantage in defining the category. However, this also means there is no existing ecosystem to leverage -- adoption will require building a community from scratch. The existence of Asqav (commercial product) validates the need. OpenTelemetry's experimental agent spans could serve as a schema reference for action fields.

### Sources

- Asqav LangChain integration: https://github.com/jagmarques/asqav-langchain
- OpenTelemetry Agent Spans: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
- OpenTelemetry GenAI SIG: https://github.com/open-telemetry/semantic-conventions-genai
- OTel Agentic AI Proposal (GitHub Issue #35): https://github.com/open-telemetry/semantic-conventions-genai/issues/35

---

## Q6: SPIFFE/SPIRE for Agent Identity

### Status: **Exists and Adopted; Being Extended for Agents**

### Key Findings

**SPIFFE** (Secure Production Identity Framework For Everyone) is a CNCF incubating project that defines a standard for workload identity. At its core:
- **SPIFFE ID** -- a URI (`spiffe://trust-domain/workload-identifier`) giving a unique, platform-agnostic identity
- **SVID** (SPIFFE Verifiable Identity Document) -- short-lived X.509 certificate or JWT encoding the SPIFFE ID
- **SPIRE** -- the reference implementation providing attestation, identity issuance, and automatic rotation

**Agent Identity Use Cases:**
Multiple vendors and practitioners are actively exploring SPIFFE for AI agent identity:

1. **CyberArk** -- documents authenticating AI agents to Secrets Manager using JWT SVIDs. Defines workload type "AI Agent" in Conjur. SPIFFE ID in `sub` claim: `spiffe://<domain>/<workload-id>`.

2. **Solo.io** (Christian Posta) -- explores extending SPIFFE for unique agent instances: `spiffe://acme.com/ns/trading/sa/trading-agent-sa/instance/001`. Argues that Kubernetes replica-based identity (all replicas share one SPIFFE ID) is insufficient for non-deterministic agents. Each agent instance needs unique identity for accountability.

3. **HashiCorp** -- positions SPIFFE as "battle-tested identity framework" for non-human actors and agentic AI. SPIFFE provides workload identity, federated trust, and dynamic credentialing.

4. **Riptides** -- builds on SPIFFE at the kernel level (kTLS) for zero-code-change agent identity. Issues SPIFFE-compliant SVIDs directly in kernel memory.

5. **Sakura Sky** -- provides a complete Python gRPC example of agent-to-agent mTLS using SPIFFE SVIDs. Shows non-repudiable auditing: "Every action an agent takes can be logged with its cryptographic SPIFFE ID."

**Challenges for Agent Identity:**
- Kubernetes replica model treats all instances as identical; agents are non-deterministic and need unique instance identity
- SPIRE requires pre-registration of workloads; dynamic agent spawning creates operational challenges
- SPIRE attests at startup, not continuously; agent behavior may diverge post-attestation
- SPIRE focuses on identity issuance, not policy enforcement ("who" not "what they're allowed to do")

**RFC 7523** (JSON Web Token Profile for OAuth 2.0) provides the JWT-based authentication mechanism that complements SPIFFE. JWT SVIDs can be used as `client_assertion` for OAuth client authentication, enabling agent-to-service auth without shared secrets.

### Implication for ASR-1

SPIFFE should be the recommended identity standard for agents in the ASR-1 ecosystem. The SPIFFE ID should be the `agent_id` field in ASR-1 receipts. ASR-1 should recommend extending SPIFFE IDs with instance granularity (`/instance/{uuid}`) for unique agent attribution. The combination of SPIFFE (identity) + ASR-1 (action receipt) provides a complete identity-and-auditing stack for agent governance. RFC 7523 provides the authentication mechanism for agents submitting receipts to verification services.

### Sources

- SPIFFE Specification: https://spiffe.io/docs/latest/spiffe-about/overview/
- CyberArk AI Agent SPIFFE Auth: https://docs.cyberark.com/secrets-manager-saas/latest/en/content/operations/authn/authenticate-ai-spiffe.htm
- Solo.io "Can SPIFFE Work for AgentsWARNING": https://www.solo.io/blog/agent-identity-and-access-management-can-spiffe-work
- HashiCorp SPIFFE for Agentic AI: https://www.hashicorp.com/en/blog/spiffe-securing-the-identity-of-agentic-ai-and-non-human-actors
- Sakura Sky Agent Identity & Attestation: https://www.sakurasky.com/blog/missing-primitives-for-trustworthy-ai-part-3/
- Riptides SPIFFE for AI Agents: https://riptides.io/blog/how-to-deliver-spiffe-identity-to-ai-agents/
- RFC 7523: https://datatracker.ietf.org/doc/html/rfc7523

---

## Strategic Recommendations for ASR-1

### 1. Standards Positioning
ASR-1 should position itself as:
- A **new category** of standard: "Action Receipt" or "Governance Receipt"
- Aligned with but distinct from: W3C VC (data model), IETF SCITT (receipt concept), SPIFFE (identity), OpenTelemetry (observability fields)
- Targeting the OWASP GenAI Security Project as the primary standards development venue

### 2. Architectural Alignment
| ASR-1 Layer | Standards Reference |
|-------------|-------------------|
| Data Model (JSON) | W3C VC 2.0 (optional profile), CloudTrail/Google Audit (field patterns) |
| Signing (Cryptographic) | JWT (RFC 7523) for simplicity, COSE (SCITT) for advanced use |
| Identity (Agent) | SPIFFE ID with instance granularity |
| Transport/Storage | CEF-compatible adapter for SIEM ingestion |
| Receipt Verification | SCITT-inspired Merkle inclusion (future) |

### 3. Standardization Path
1. **Phase 1 (Now):** Develop ASR-1 spec internally with OWASP alignment
2. **Phase 2 (Q3 2025):** Submit ASR-1 as OWASP GenAI Security Project contribution
3. **Phase 3 (2026):** Propose IETF draft (possibly in SCITT WG or new WG) for action receipt standard
4. **Phase 4 (2027+):** W3C Community Group or IETF WG for formal standardization

### 4. Competitive Differentiation
- **Cloud audit logs** record what happened; ASR-1 proves what was evaluated and decided
- **OpenTelemetry** traces actions for debugging; ASR-1 attests actions for compliance
- **SCITT** receipts verify supply chain claims; ASR-1 receipts verify governance decisions
- **VCs** prove identity attributes; ASR-1 proves action governance outcomes

---

## Appendix: Standards Maturity Matrix

| Standard | Maturity | Relevance to ASR-1 | Cryptographic Signing | Agent-Specific |
|----------|----------|-------------------|----------------------|----------------|
| W3C VC 2.0 | W3C Rec (2025) | Medium | Yes (DI/JOSE/COSE) | No |
| RFC 6962/9162 (CT) | IETF Experimental | Low (primitives) | Yes (Merkle/SCT) | No |
| RFC 7523 (JWT OAuth) | IETF Standards Track | High | Yes (JWT) | No |
| SCITT (draft) | IETF Draft | High | Yes (COSE) | No |
| CEF | De facto standard | Medium (transport) | No | No |
| LEEF | Vendor (IBM) | Low | No | No |
| STIX/TAXII | OASIS standard | Low (model ref) | No | No |
| CloudTrail | AWS proprietary | Medium (schema ref) | No | No |
| Google Cloud Audit | Google proprietary | Medium (schema ref) | No | No |
| Azure Activity Logs | Microsoft proprietary | Medium (schema ref) | No | No |
| OTel GenAI SemConv | Experimental | Medium (field ref) | No | Yes (partial) |
| SPIFFE/SPIRE | CNCF Incubating | High (identity) | Yes (SVID) | Yes (emerging) |
| OWASP Top 10 Agentic | Community Standard | High (venue) | No | Yes |
| **ASR-1** | **Proposed** | **N/A** | **Yes (JWT/COSE)** | **Yes (purpose-built)** |

---

*Research completed 2025-07-15. All sources verified as of research date.*
