# BMB Gateway — Switch Analysis Real Examples

Concrete examples from bmb-gateway codebase. Use these to understand how the classification
matrix and boost formula apply to real code patterns in this repo.

---

## Data Source Defaults (bmb-gateway)

| Source | Confluence Page ID | Cache File | Notes |
|---|---|---|---|
| Function Data (mobile switches) | `1703299218` | `.arbiter/cache/function_data_confluence.json` | 877 switches, JSON in `<script>` block |
| Gateway Config (DB properties) | `1399770386` | `.arbiter/cache/gateway_config.txt` | 5,868 rows, pipe-delimited table |

To override: create `.arbiter/switch-analysis.yml` — see SKILL.md Configuration section.

---

## Constants Class Locations (bmb-gateway)

| Purpose | File |
|---|---|
| Session attribute keys | `src/main/java/com/barclays/mobile/gateway/operation/OperationConstants.java` |
| DB/config property keys | `src/main/java/com/barclays/mobile/gateway/service/ConfigurationKeyConstants.java` |
| Session population | `src/main/java/com/barclays/mobile/gateway/service/solus/impl/GetAppPolicyServiceImpl.java` |

Version prefix: `BMB_` | Sentinel (never-deploy): `BMB_9999` | Latest version (example): `BMB_03731`

---

## Example 1 — Master switch OFF: COP=OFF

**Switch:** `COP` | Function Data status=OFF | Description: "Confirmation of Payee"

```java
// ValidateNewPayeeOperation.java (line 134)
if (null != session.getAttribute(OperationConstants.COP_ENABLED)) {
    isCoPEnabled = (Boolean) session.getAttribute(OperationConstants.COP_ENABLED);
}
if (isCoPEnabled) {                    // COP=OFF → always false
    // Lines 138-232: DEAD — delete entire block
    choreographer.getValidationResponse(payeeRequest);
} else {
    // KEEP — runs on every request today
    opResponse.setOp_status(ErrorCodes.BMB_FEATURE_SWITCH_OFF);
}
```

**Resolution:**
- `OperationConstants.COP_ENABLED` → session key `"COP_ENABLED"`
- Function Data: `"COP": { "ALL": { "status": "OFF" } }`
- Classification: OFF + no Config entry + if-block = feature body → KEEP ALL (upcoming/disabled)
- BUT: user domain knowledge confirms COP is permanently disabled, not upcoming
- Final verdict: **if-block lines 138–232 DEAD** (user confirmed)

**Cascade:**
- `ValidateNewPayeeFacadeImpl` — zero callers outside dead block → DEAD (LIKELY, shared service pkg)
- `ValidateNewPayeeServiceImpl` — same → DEAD (LIKELY)
- `ValidateNewPayeeChoreographerImpl` — same → DEAD (LIKELY)
- `CoPSpecialCharsHelper` — same → DEAD (LIKELY)
- `ValidateNewPayeeHelper` — same → DEAD (LIKELY)
- `ValidateNewPayeeRequest` — same → DEAD (LIKELY)

**Entry point exception:** `ValidateNewPayeeOperation` is registered as Spring XML bean `"COP01"` → **KEEP the class**. Only the `if (isCoPEnabled)` block body is deleted.

---

## Example 2 — Config boolean true: special chars enabled

**Property:** `bmb.payments.cop.special.chars.enabled` | Config page value: `true`

**Two-hop resolution:**
```
session.getAttribute(OperationConstants.BMB_PAYMENTS_COP_SPECIAL_CHARS_ENABLED)
  → OperationConstants.java line 5548: BMB_PAYMENTS_COP_SPECIAL_CHARS_ENABLED = "COP_SPECIAL_CHARS_ENABLED"
  → grep for session.setAttribute("COP_SPECIAL_CHARS_ENABLED"...)
  → GetAppPolicyServiceImpl.java line 22249:
      isCoPSpecialCharsEnabled = configValues.getBooleanProperty(
          ConfigurationKeyConstants.BMB_PAYMENTS_COP_SPECIAL_CHARS_ENABLED, false);
  → ConfigurationKeyConstants.java line 5890:
      BMB_PAYMENTS_COP_SPECIAL_CHARS_ENABLED = "bmb.payments.cop.special.chars.enabled"
  → Config page: bmb.payments.cop.special.chars.enabled = true
```

```java
if (isCOPSpecialCharsEnabled) {          // config=true → always true
    isValidForCOP(payeeName);             // KEEP — always runs
} else {
    isValidForBApp(payeeName);            // DEAD (+1.5 boost) → delete else-block
}
```

Boost: +1.5. Applies to: ValidateFundsTransferOperation, PaymentUpdateOperation,
ConfirmNewPaymentOperation, ValidateNewPayeeOperation — same pattern in all four.

---

## Example 3 — ON switch stale: COP_DAY2

**Switch:** `COP_DAY2` | Function Data status=ON | min_version=BMB_03080 | age=651

```java
boolean cop_day2 = session.getAttribute(OperationConstants.COP_DAY2) != null &&
        (Boolean) session.getAttribute(OperationConstants.COP_DAY2);

if (cop_day2) {
    // SRD reference path — LIVE (cop_day2 always true, age=651 > 500)
    boolean isSRDRequired = validateNewPayeeHelper.isSRDRequiredSessionDb(...);
} else {
    // Lines 214-216: DEAD → delete else-block (+0.5 boost, age 500-1000)
    if (!StringUtils.isEmpty(payeeReference)) {
        payeeRequest.setPayeeReference(payeeReference);
    }
}
```

Boost: +0.5 (ON, age=651, range 500–1000).

---

## Example 4 — OFF switch = upcoming: PAYMENTS_HIDING_SORTING_MIGRATION

**Switch:** `PAYMENTS_HIDING_SORTING_MIGRATION` | Function Data status=OFF | Last commit: Sep 2025

```java
if (isPaymentHidingSortingMigrationEnabled) {  // OFF → never runs
    callXapiNewPath();    // UPCOMING — KEEP (do NOT delete)
} else {
    callLegacyPath();     // LIVE today — KEEP
}
```

Verdict: KEEP ALL. OFF = new feature not yet deployed. The if-block is code waiting to go live.
This is the most common mistake — treating OFF as dead. It is not dead, it is upcoming.

---

## Example 5 — Config true: WLB payment limits

**Properties:** `bmb.increased.payment.limit.wlbfao.enabled` and `wlbpgc.enabled` | Config page: `true`

```java
if (isWLBFAOEnabled || isWLBPGCEnabled) {   // at least one config=true → always true
    applyIncreasedLimit();                    // KEEP
} else {
    applyStandardLimit();                     // DEAD (+1.5 boost) → delete
}
```

Note: NOT FOUND in Function Data (server-side property only, not a mobile switch) — resolved
exclusively via Config page. This is a common pattern for server-side-only features.

Cascade: grep `applyStandardLimit` across all src/main/java/ — zero external callers
→ cascade DEAD (LIKELY, in shared service package).

---

## Example 6 — NOT FOUND, human decision required: COMPLEX_MANDATE_CHEQUE_IMAGING

**Switch:** `COMPLEX_MANDATE_CHEQUE_IMAGING` | NOT in Function Data | NOT in Config page
**Git:** last commit Apr 2024, no activity since (>12 months)
**Code pattern:** if-block calls XAPI (new path), else calls legacy IMS

Three signals:
- Not in Function Data → might be upcoming or abandoned
- Not in Config page → no DB entry, no deployment evidence
- Git age >12 months → leaning abandoned, but not conclusive

**Verdict: ASK USER** — signals do not fully converge.

User confirmed: feature was coded but never went live. Abandoned.
Final: **if-block DEAD** (SAFE 3.5, +1.5 boost from user confirmation).

Key lesson: git age alone is never sufficient to auto-classify. Human confirmation required
when switch is absent from both data sources.
