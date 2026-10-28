---
name: mts-example-project-walkthrough
description: Worked example of the full MTS 3-stage pipeline for a typical mainframe-mq service
type: reference
---

# Example Project Walkthrough

This document shows what a successful end-to-end run looks like for a typical `mainframe-mq` service. Use it to calibrate expectations when running on a new project.

## Project Characteristics

- **Type:** BUK Spring Boot monolith (fullserve or partialserve)
- **Transport:** `mainframe-mq` (most common)
- **Services:** ~15 doService calls
- **EBS JARs:** Present in Gradle cache (or compiled fallback available)

---

## Stage 1: `/mts-documentation`

### Discovery output (Phase 1)

After running `mts-discovery-agent`:

```
DISCOVERY_METADATA:
  project_name: fullserve-buk
  doservice_calls_found: 15
  transport_counts:
    mainframe-mq: 11
    soap-stub: 2
    oracle-db-direct: 1
    already-api-other: 1

DOSERVICE_CALLS:
  1. CustomerGateway.retrievePersonalCustomerFullDetails
     service_name: RETRIEVECUSTOMER
     method: GET_CUSTOMER_FULL
     transport: mainframe-mq
     ...
```

### Per-service doc (Phase 2 agent output)

Each `service-doc-CustomerGateway-retrievePersonalCustomerFullDetails.md` contains:
- Section 1: Quick Reference table with WMID, TDL tables, confidence
- Section 3: Mermaid call flow diagram (REST → Gateway → EBS → Mainframe)
- Section 5: End-to-End Field Mapping table with 6 columns
- Section 6: Backend Mappings with WMID-TDL rows

---

## Stage 2: `/api-replacement-match`

### Typical match result for `mainframe-mq` services

```
Winner: srv-custcore-api (pAPI)
Score: 0.87 (Strong match)
TDL overlap: 4/5 tables
Request fields: 2/3 mapped
Response fields: 47/52 mapped (5 gaps)
```

### Common gaps

- `accountStatus` field: MTS returns raw mainframe code, ODS returns decoded enum → transformation required
- `lastUpdateTimestamp` field: Not available in ODS → true gap (document in issues)

---

## Stage 3: `/mts-migrate CustomerGateway.retrievePersonalCustomerFullDetails`

### Strategy B (most common for existing microservices)

Input: local path to `customer-core-api` repo.

**Generated files:**

```
src/main/java/com/barclays/customercoreapi/
  controller/CustomerController.java         (new endpoint)
  client/OdsCustomerClient.java              (REST client)
  converter/OdsCustomerConverter.java        (field mapper)
  config/CustomerApiConfig.java              (bean config)

src/test/java/com/barclays/customercoreapi/
  controller/CustomerControllerTest.java
  client/OdsCustomerClientTest.java
  converter/OdsCustomerConverterTest.java

docs/mts/migrate-issues-CustomerGateway-retrievePersonalCustomerFullDetails.md
```

**Compilation:** Passes on first attempt (SDK3 ODS client dependency already in build.gradle).

**Test execution:** All 12 tests pass.

### Issues document highlights

```markdown
## 2. True Gaps
- lastUpdateTimestamp: Not available in ODS API — use null

## 4. Converter Bug Corrections
- accountStatus: Use AccountStatusEnum.fromCode(dto.getAccountStatus())
  NOT Boolean.parseBoolean() — this field is a code, not a boolean

## 7. Configuration Changes Needed
- Add to application.properties:
    ods.customer.base-url=${ODS_CUSTOMER_BASE_URL}
    ods.customer.timeout-ms=5000
```

---

## Key Takeaways

1. **Pre-flight is critical:** If Gradle cache is empty, compiled JAR fallback covers ~85% of services — but some TDL table correlations will be UNKNOWN.
2. **Phase 2 parallel launch:** All 15 per-service agents run simultaneously. On a typical run, this takes 3-5 minutes wall time despite 15x the work.
3. **API match scores:** Scores above 0.8 are reliable. Scores between 0.6-0.8 need manual review of the gaps section. Scores below 0.6 indicate significant data contract differences.
4. **Strategy C complexity:** In-place migration (Strategy C) generates significantly more complex code due to dual-path routing and feature flags. Expect more compilation iterations.
