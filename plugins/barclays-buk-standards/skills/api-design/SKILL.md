---
name: api-design
description: BUK API design standards. Covers DAF architecture principles, authorization layers, header contract, OpenAPI, versioning, error handling, and caching. Use when generating or reviewing DAF API specifications or service interfaces.
user-invocable: false
---

# BUK API Design Standards

> Source: Digital API Framework (DAF) documentation — authoritative for all BUK digital channel APIs.

---

## Section 1: What is a DAF API

A DAF API is a microservice built using the Digital API Framework that:

- Is deployed on **Service Mesh** (VINZ)
- Is exposed **only** via the **SDF-approved Edge Gateway**
- Uses the **DAF contract headers** (`STRATDF:daf-v4`)
- Is documented with **OAS (OpenAPI Specification)**
- Is **cross-channel**: supports all digital channels from a single API (no channel forks)

**Non-DAF**: Any API not using the DAF library, not deployed on Service Mesh, or not used with SDF Edge Gateway and Digital Registry **must not be labelled DAF**, even if consumed by Edge Gateway.

---

## Section 2: Architecture Principles

| Principle | Rule |
|---|---|
| Presentation logic | All presentation logic is orchestrated in the DAF API — **never in the UI layer** |
| One API for all channels | A single DAF API serves all digital channels (cross-channel) |
| Data-oriented | APIs are data-oriented and context-aware; keep UI as simple as possible |
| No passthrough | DAF APIs **must not** act as a passthrough or proxy for a domain API |
| No direct internet exposure | DAF APIs **must not** be exposed directly to the internet — always behind Edge Gateway |
| Java | The programming language for DAF APIs is **Java** |

---

## Section 3: Authorization Layers

Three layers handle authorization — each has a distinct, non-overlapping responsibility:

| Layer | Responsibility |
|---|---|
| **Edge Gateway** | Authenticated session; validates request authorization for specific API and path; validates incoming data in internet-facing environment |
| **Service Mesh (VINZ)** | System-to-system authentication/authorization; validates incoming data for the API |
| **DAF API** | Ensures request validity in user session context; validates **customer-specific authorization** (e.g. account ownership) |

The DAF API is responsible for BOLA/IDOR checks — verifying the authenticated customer is authorized to access the specific resource in the request. This must be enforced per request, not assumed from session state.

---

## Section 4: DAF Header Contract

All DAF APIs must use the standard DAF contract headers. Custom headers not in the DAF contract are **not permitted**. Changes to DAF headers require written CSO support.

### Required Headers (all APIs)

| Header | Purpose |
|---|---|
| `Correlation-ID` | UUID linking log entries across all layers for support/incident investigation. Mandatory for all APIs. |
| `CustomerContext` | Primary customer identifier — `customerPk.id` (Customer System ID) + `type` (e.g. `CUS_ID`) |
| `SessionContext` | Session ID, journey tracking UUID, auth type, and (BAPP only) reg method |
| `ChannelContext` | Channel identifier — `channelId` values: `BMB` (Barclays App), `ROLB`, `Intermediary` |
| `LoggingContext` | Dynamic log level for RTB incident investigation |
| `EnvironmentContext` | Environment label from Edge Gateway (e.g. `AWSLIVE`) |
| `LocaleContext` | ISO 639-1 language code (currently always `en`) |

### Optional / Channel-Specific Headers

| Header | Purpose | Channels |
|---|---|---|
| `AccountContext` | Array of accounts with `productIdentifier` + `productClass` (e.g. `CU`, `SV`) | All |
| `ClientContext` | Client version, OS name/version, AID, client IP | BAPP (full), ROLB (IP only) |
| `ClientUserAgent` | URL-encoded User-Agent string — only send to APIs that require it | All |
| `ProfileContext` | ProfileId, personaId/type, partyId/type, personaOrg (mortgages), profileType | All |
| `TestContext` | Non-production only — testbed and labels for SV/testing; must be optional | Non-prod |
| `PermissionsContext` | **Tactical only** — products/segments. Not for general use; requires DAF/SA approval | Limited |

### ProfileContext Key Fields

- `partyId` — **mandatory** (defaults to customer ID if not set); the current resource/scope
- `personaId` — current authenticated user; preferred: `MEM_ID` → fallback: `CUS_ID` → legacy: `REG_ID`
- `personaType` / `partyType` — string type values: `REG_ID`, `MEM_ID`, `CUS_ID`
- `profileType` — can be set by DAF API via response headers (read by Edge Gateway and stored in session)

---

## Section 5: API Documentation

- Use **OAS (OpenAPI Specification)** for all API documentation
- Contract OAS: `https://app.gitlab.barcapint.com/barclays/daf-demo-management-api/digital-api-framework/-/tree/master/daf-contract/daf-oas`
- Every endpoint must be documented with request/response schemas, required headers, and error responses

---

## Section 6: Versioning

- Follow **semantic versioning**
- Maintain **backwards compatibility** — no breaking changes without a major version bump
- Support a maximum of **1–2 active major versions** at any time
- Breaking changes require a deprecation notice and migration path for consumers

---

## Section 7: Request Handling

| Rule | Requirement |
|---|---|
| Input validation | Must validate all input requests before processing |
| Authorization | Ensure Bearer token authorization on all requests |
| Bearer token propagation | May pass Bearer tokens to downstream services |
| No UI content | Must not serve UI content — focus on data needs only |
| Channel logic | Limit channel-specific logic to exceptions only (device-specific data needs) |

---

## Section 8: Error Handling and Resilience

| Practice | Guidance |
|---|---|
| Error mapping | Override/map functional and technical errors to customer-presentable messages |
| Alternative paths | Map alternative response paths and "what next" guidance |
| Circuit breaker | Follow circuit breaker pattern for fast failure on downstream dependencies |
| Failure reporting | Capture and report failure events; include context for debugging |

---

## Section 9: Caching

| Use case | Rule |
|---|---|
| Static reference data | Can be cached |
| Journey cache | Use Digital Service Session Management API or DAF Session Client |
| Custom cache | Any custom journey cache implementation requires **CSO review** |

---

## Section 10: Logging and Monitoring

- Integrate with the **consistent logging framework** for all data, exceptions, and errors
- **Mask PII and PCI data** in all log output — never log customer credentials, card numbers, or account identifiers in plaintext
- Capture `Correlation-ID` in every log entry
- Include customer context, logging context, and channel context from HTTP headers
- `LoggingContext.dynamicLogLevel` enables RTB to increase logging for incident investigation without a deployment

---

## Section 11: Data and Integration

- **Can** orchestrate downstream APIs
- **Can** perform data transformations for journey/device/channel context
- **Can** send device-specific or journey-specific configuration
- **Can** integrate with workflow applications — but DAF APIs are **not** designed as workflow APIs
- **Must not** be passthrough — apply transformation or orchestration value

---

## Section 12: Deployment

- Can deploy multiple instances on channel-specific clusters for latency reduction and resiliency
- Can have channel-specific context for operations
- All deployments must use Service Mesh — non-Service Mesh deployments are not approved as DAF

---

## Section 13: Design Checklist

Before submitting an API for review, verify:

- [ ] API documented with OAS
- [ ] All mandatory DAF contract headers implemented and validated
- [ ] `Correlation-ID` propagated through all downstream calls
- [ ] PII/PCI masked in all logging
- [ ] Customer-specific authorization (account ownership) checked at the DAF API layer — not delegated to Edge Gateway
- [ ] Bearer token validated; not bypassed
- [ ] Input validation on all request parameters
- [ ] Error responses are customer-presentable (not raw stack traces or internal codes)
- [ ] Circuit breaker pattern applied to downstream dependencies
- [ ] No passthrough / proxy behaviour
- [ ] Versioning strategy documented; backwards compatibility maintained
- [ ] No custom headers outside DAF contract
- [ ] `TestContext` header marked optional (non-production only)
- [ ] Any custom caching reviewed by CSO
- [ ] API not exposed directly to internet without Edge Gateway
