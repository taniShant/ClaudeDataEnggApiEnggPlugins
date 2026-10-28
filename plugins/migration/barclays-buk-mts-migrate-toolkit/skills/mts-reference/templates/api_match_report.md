# API Match Report Template

Each `docs/mts/api-match-<ServiceName>-<method>.md` file MUST follow this 6-section structure.
Section headers use `## N. Title` pattern exactly. No `§` symbols. No em dashes in titles.

---

### GOLDEN EXAMPLE REPORT (copy this structure EXACTLY)

The following is a complete, correct report. Your output MUST follow this structure character-for-character (except for the actual data values). If your output differs in structure from this example, it WILL fail downstream parsing.

```markdown
# API Match Report: CustomerGateway.findByPrimaryKey

**Generated:** YYYY-MM-DD
**MTS Service:** CustomerGateway.findByPrimaryKey()
**Transport:** mainframe-mq
**Winner:** ODS Retail Customer Enquiry API (sodscustenq v4) — 95% (Strong match)
**Endpoint:** `GET /sodscustenq/4/v4/customers/{customerId}`
**Confluence:** [ODS Retail Customer Enquiry API](https://confluence.barcapint.com/spaces/pcbcooiit/pages/879235084/ODS+Retail+Customer+Enquiry+API)
**Agent:** MTS API Match Agent

---

## 1. Candidate Summary

| # | Candidate | Endpoint | Score | Band | Recommendation | Links |
|---|-----------|----------|-------|------|----------------|-------|
| 1 | ODS Retail Customer Enquiry API (sodscustenq v4) (source: seed-catalogue) | GET /sodscustenq/4/v4/customers/{customerId} | 95% | Strong match | **WINNER** | [Confluence](https://confluence.barcapint.com/spaces/pcbcooiit/pages/879235084/ODS+Retail+Customer+Enquiry+API) / [GitLab](barclays/ods-apis/app/sodscustenq) |
| 2 | ODS Product Holding and Account Data Enquiry API v4 (PHAD v4) (source: seed-catalogue) | GET /sodsproductsenq/v4/customers/{customerId}/productHoldings | 57% | Partial match | Eliminated — missing TDLBARH/TDLCCAX table; no TDLQCU transaction reference | [Confluence](https://confluence.barcapint.com/spaces/pcbcooiit/pages/3818258575) / [GitLab](barclays/ods-apis/app/sodsproductsenq) |
| 3 | Customer Product Holdings API (custprodholding-api) (source: backstage-catalogue) | Unknown (metadata-only) | 5% | Unlikely match | Eliminated — metadata-only, no documented TDL or transaction references | [Confluence](https://confluence.barcapint.com/spaces/pcbcooiit/pages/1228557435) |

**Score breakdown (winner):** TDL 100%×0.35 + Txn 100%×0.25 + Response 93%×0.20 + Request 67%×0.10 + Source 100%×0.10 = 95%

---

## 2. Request Mapping

| # | MTS Field | MTS Type | ODS Parameter | ODS Type | Match | Notes |
|---|-----------|----------|---------------|----------|-------|-------|
| 1 | customerPk.customerId | Long | {customerId} (path) | Long | exact | Direct path parameter mapping; maps to WMID-CUS-IDR-NUM |
| 2 | dataGroups | CustomerDataGroup[] | ukbaProductHoldings, miscellaneousProductHoldings, cardAccountHoldings, barclayBankCardHoldings (query params) | String (Y/N/ALL) | transformed | Each DataGroup enum value maps to a named ODS query parameter; see Section 3 |
| 3 | fullRetrieve | boolean | — | — | **MISSING** | No direct ODS equivalent; ODS uses Y/ALL values on individual query params to control open vs open+closed; partial workaround via ALL value but not a single boolean flag |
| 4 | requestType | String | — | — | **MISSING** | Gateway dispatch parameter — excluded from scoring; selects ExtendedRequest vs CustomerRequest overload internally |

---

## 3. Query Parameter Mapping

| MTS DataGroup | TDL Table | ODS Query Param | Match |
|---------------|-----------|-----------------|-------|
| UKBA_PRODUCT_HOLDINGS | TDLBAHO | ukbaProductHoldings=Y (active only) / ukbaProductHoldings=ALL (open+closed, @since 4.12) | Y |
| MISCELLANEOUS_PRODUCT_HOLDINGS | TDLMAHO | miscellaneousProductHoldings=Y (active only) / miscellaneousProductHoldings=ALL (open+closed, @since 4.12) | Y |
| CARD_ACCOUNT_HOLDINGS | TDLCAHO | cardAccountHoldings=Y (active only) / cardAccountHoldings=ALL (open+closed, @since 4.12) | Y |
| BARCLAYBANK_CARD_HOLDINGS | TDLBARH | barclayBankCardHoldings=Y (TDLCCAX equivalent; card number masked v4.11+) | Y |

---

## 4. Response Field Mapping

#### Origin Legend

| Code | Meaning | In Scope? |
|------|---------|-----------|
| `gw` | gateway-response — field populated directly from gateway method's MTS response | Yes |
| `dl` | derived-local — field derived locally from gateway response data | Yes |
| `fr` | full-retrieval-only — field from a full-retrieval code path calling a DIFFERENT service | No |
| `es` | external-service — field from a separate external service call | No |
| `cl` | controller-layer — field set by controller from HTTP request context | No |
| `rc` | request-context — field from authentication/session context | No |
| `er` | error-from-non-gateway-call — error from catch block around a non-gateway call | No |

**Match values:** `exact` | `renamed` | `transformed` | `data-group` | **`MISSING`**

| # | MTS Field | MTS Type | Origin | ODS Field | ODS Type | Match | Notes |
|---|-----------|----------|--------|-----------|----------|-------|-------|
| 1 | holdingCounters[ALL_PRODUCTS] | Integer | dl | ukbaProductHoldingDataList[], miscellaneousProductHoldingDataList[], cardAccountHoldingDataList[], barclayBankCardHoldings[] | Array | data-group | Count total entries across all 4 arrays (BAHO + MAHO + CAHO + CCAX) |
| 2 | holdingCounters[CURRENT_ACCOUNTS] | Integer | dl | ukbaProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code = "CU" from TDLBAHO |
| 3 | holdingCounters[SAVING_ACCOUNTS] | Integer | dl | ukbaProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code = "SV" from TDLBAHO |
| 4 | holdingCounters[LOANS] | Integer | dl | miscellaneousProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code in {"LN","LO"} from TDLMAHO |
| 5 | holdingCounters[MORTGAGES] | Integer | dl | ukbaProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code in {"MO","WM"} from TDLBAHO |
| 6 | holdingCounters[CREDIT_CARDS] | Integer | dl | cardAccountHoldingDataList[], ukbaProductHoldingDataList[].classificationCode.code, miscellaneousProductHoldingDataList[].classificationCode.code | Array | data-group | Count all TDLCAHO entries plus CA-classified entries from BAHO and MAHO |
| 7 | holdingCounters[INVESTMENTS] | Integer | dl | miscellaneousProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code in {"DI","DA","ID"} from TDLMAHO |
| 8 | holdingCounters[INSURANCES] | Integer | es | N/A | — | **MISSING** | Depends on InsuranceTypeService external reference data; out of scope |
| 9 | holdingCounters[SOLD] | Integer | dl | miscellaneousProductHoldingDataList[].classificationCode.code | String | data-group | Count where classificationCode.code = "GT" from TDLMAHO |
| 10 | holdingCounters[OTHER] | Integer | es | N/A | — | **MISSING** | Depends on InsuranceTypeService.isInsuranceProductCover(); out of scope |
| 11 | holdingCounters[ADDITIONAL] | Integer | dl | N/A | — | **MISSING** | TDLADPR not available in sodscustenq; no equivalent data source |
| 12 | holdingCounters[DIGITAL_FIRST] | Integer | dl | ukbaProductHoldingDataList[].productKey.genericProductCode, miscellaneousProductHoldingDataList[].productKey.genericProductCode | Long | data-group | Count entries matching digital-first lookup via DigitalFirstTypeService (NGCB config); apply same lookup against ODS genericProductCode |
| 13 | holdingCounters[CLOSED] | Integer | dl | ukbaProductHoldingDataList[].endDate, miscellaneousProductHoldingDataList[].endDate, cardAccountHoldingDataList[].endDate, barclayBankCardHoldings[].dateRange | Date | data-group | Count entries where endDate != null across all arrays; requires ALL query param |
| 14 | holdingsLimitExceeded | boolean | gw | N/A | — | transformed | ODS returns HTTP 206 on truncation; consumer can derive from response status code |
| 15 | open | ProductHoldings | fr | N/A | — | **MISSING** | Full-retrieval-only; populated from a different service call path; out of scope |
| 16 | closed | ProductHoldings | fr | N/A | — | **MISSING** | Full-retrieval-only; out of scope |
| 17 | misc | ProductHoldings | fr | N/A | — | **MISSING** | Full-retrieval-only; out of scope |
| 18 | additional | ProductHoldings | fr | N/A | — | **MISSING** | Full-retrieval-only; out of scope |
| 19 | holdingsType | HoldingsType | es | N/A | — | **MISSING** | Depends on full-retrieval open/closed data from external service path |
| 20 | barclayCardErrorMessage | String | er | N/A | — | **MISSING** | Error from catch block around non-gateway call |
| 21 | findProductHoldingErrorMessage | String | er | N/A | — | **MISSING** | Error from catch block around non-gateway call |
| 22 | reservedAccountMsg | String | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 23 | closedMtsBarclaycards | int | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 24 | solusRestriction | boolean | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 25 | bpfSolusCustomer | boolean | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 26 | noOpenOrClosedBarclayCards | boolean | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 27 | accountDataKey | String | rc | N/A | — | **MISSING** | Request-context field; no ODS equivalent |
| 28 | accountData | JSONObject | cl | N/A | — | **MISSING** | Controller-layer field; no ODS equivalent |
| 29 | launchMcas | List<LaunchMca> | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 30 | barclayCardIDVLvlRestriction | boolean | es | N/A | — | **MISSING** | External service call; no ODS equivalent |
| 31 | fraudDesktopAlerts | List<Notification> | es | N/A | — | **MISSING** | External service call; no ODS equivalent |

---

## 5. Data Gaps & Risks

### 5.1 Missing Fields

| # | MTS Field | Type | Impact | Action |
|---|-----------|------|--------|--------|
| 1 | holdingCounters[ADDITIONAL] | Integer | Medium | TDLADPR not in sodscustenq; investigate whether PHAD v4 or a separate ODS endpoint covers TDLADPR |
| 2 | holdingsLimitExceeded | boolean | Low | ODS returns HTTP 206 when limits exceeded; derive from response status code — requires client-side transformation |
| 3 | fullRetrieve | boolean | Medium | MTS single boolean; ODS requires per-query-param ALL/Y values; migration must map fullRetrieve=true to all params set to ALL |

### 5.2 Constraints

| Constraint | Detail |
|------------|--------|
| Closed account data integrity | MTS reads closed-account records directly from TDL; ODS closed-account data may be absent or stale if the ODS data pipeline excludes closed accounts or applies retention policies. Verify ODS data completeness for closed accounts before migration. The ALL query param value (@since 4.12) must be used to retrieve open+closed records. |
| Card number masking | ODS v4.11+ masks all card digits except last 4 in CAHO and CCAX arrays; MTS TDL reads return unmasked card numbers. Consuming services that use card numbers for downstream processing will be affected. |
| Record limits and truncation | ODS enforces per-group record limits (BAHO=40, MAHO=60, CAHO=10, CCAX=25); MTS has no such hard limits. Customers with high product counts may receive truncated results; HTTP 206 signals truncation. |
| MAHO Joint Indicator staleness | ODS MAHO Joint Indicator is batch-updated and may lag up to 24 hours; MTS reads directly from TDL in real time. |
| ODS data heartbeat fallback | ODS sodscustenq falls back to z/OS API when the ODS data heartbeat flag is false; the fallback path must be tested to ensure response shape parity. |

### 5.3 Migration Feasibility

**Counter-path: FEASIBLE** — 13/14 in-scope fields matched (93%). 1 gap (holdingCounters[ADDITIONAL]) requires supplementary data source investigation. holdingsLimitExceeded requires client-side transformation from HTTP 206. Classification logic for INSURANCES and DIGITAL_FIRST must be reimplemented client-side using ODS genericProductCode.

**Full-retrieval: OUT OF SCOPE** — The open, closed, misc, additional ProductHoldings objects come from a separate full-retrieval service path not covered by sodscustenq.

**External service fields: OUT OF SCOPE** — 11 fields populated by external services or controller-layer context require independent migration assessment.

### 5.4 ODS API Reference

| Resource | Link |
|----------|------|
| ODS API Confluence Page | [ODS Retail Customer Enquiry API LLD](https://confluence.barcapint.com/spaces/pcbcooiit/pages/879235084/ODS+Retail+Customer+Enquiry+API) |
| E2E Field Mapping | [E2E Mapping](https://confluence.barcapint.com/spaces/pcbcooiit/pages/631400141/ODS+Customer+Enquiry+sAPI+E2E+Mapping) |
| OpenAPI / Swagger Spec | Not available |

---

## 6. Example Request & Response

> Examples extracted from API specification. Source noted per candidate.

### 6.1 ODS Retail Customer Enquiry API (sodscustenq v4) — #1

#### Request

```
GET /sodscustenq/4/v4/customers/100000001
    ?ukbaProductHoldings=Y
    &miscellaneousProductHoldings=Y
    &cardAccountHoldings=Y
    &barclayBankCardHoldings=Y
Accept: application/json
```

*Source: OpenAPI spec (GitLab — barclays/ods-apis/app/sodscustenq)*

#### Response

```json
{
  "customerData": {
    "customerId": 100000001,
    "customerType": "P"
  },
  "ukbaProductHoldingDataList": [
    {
      "accountKey": {
        "sortCode": 200000,
        "accountNumber": "12345678"
      },
      "productCode": "CHQ",
      "classificationCode": { "code": "CU", "decode": "Current Account" },
      "takenOutDate": "2010-01-15",
      "endDate": null,
      "tradingEntityIdentifier": "0001",
      "legalEntityIdentifier": "0001"
    }
  ],
  "miscellaneousProductHoldingDataList": [],
  "cardAccountHoldingDataList": [],
  "barclayBankCardHoldingDataList": []
}
```

*Source: OpenAPI spec example (GitLab) | HTTP 200 | ~8 top-level fields*

---

### 6.2 ODS Product Holding and Account Data Enquiry API v4 (PHAD v4) — #2

#### Request

```
GET /sodsproductsenq/v4/customers/100000001/productHoldings
    ?ukbaProductHoldings=Y
Accept: application/json
```

*Source: Confluence documentation snippet (page 3818258575)*

#### Response

```json
{
  "ukbaProductHoldingDataList": [
    {
      "sortCode": 200000,
      "accountNumber": "12345678",
      "genericProductCode": 1234,
      "classificationCode": { "code": "CU" },
      "startDate": "2010-01-15",
      "endDate": null,
      "tradingEntityIdentifier": "0001",
      "legalEntityIdentifier": "0001"
    }
  ],
  "miscellaneousProductHoldingDataList": [],
  "additionalProductHoldingDataList": []
}
```

*Source: Confluence documentation example | HTTP 200 | ~3 top-level arrays*

---

*Report generated by MTS API Match Agent — YYYY-MM-DD*
```
