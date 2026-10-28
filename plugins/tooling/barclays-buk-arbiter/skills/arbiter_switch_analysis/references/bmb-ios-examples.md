# BMB iOS — Switch Analysis Real Examples

Concrete examples from barclays-app iOS codebase. Use these to understand how the classification
matrix and boost formula apply to real Swift code patterns in this app.

---

## iOS Feature Flag Architecture

| Component | File | Purpose |
|---|---|---|
| Feature constants (base) | `BarclaysSharedCore/BarclaysSharedCore/BMBFeatureData.swift` | ~100+ switch key constants |
| Feature constants (Payments) | `Payments/Payments/BMBFeatureData.swift` | Module-specific extensions |
| Feature constants (BMB) | `BMB/BMBFeatureData+Extension.swift` | App-level extensions |
| Feature status helper | `BMB/BMBFeatureStatusHelper.swift` + `.m` | `isOn()` / `statusForFeature()` |
| Policy value helper | `BMB/BMBPolicyValueHelper.swift` | `isFeaturePolicyEnabled()` / `policyValue()` |
| Platform session | `BarclaysSharedCore/.../PlatformSession.swift` | Modern server-driven config |
| Policy types | `BarclaysSharedCore/.../BarclaysPolicyType.swift` | Policy key mappings |

### Resolution Chain (One-Hop)

```
BMBFeatureData.ConfirmationOfPayee
  → static let ConfirmationOfPayee = "COP"
  → Look up "COP" in Function Data page
  → Result: { "ALL": { "status": "OFF" } }
```

No intermediate session-attribute layer. iOS constants map directly to Confluence keys.

---

## Example 1 — Master Switch OFF: COP=OFF (KEEP ALL)

**Switch:** `COP` | Function Data status=OFF | Description: "Confirmation of Payee"

```swift
// PaymentFlowCoordinator.swift
let isCoPEnabled = BMBFeatureStatusHelper.sharedInstance().isOn(BMBFeatureData.ConfirmationOfPayee)

if isCoPEnabled {
    // COP feature flow — lines 85-142
    let copResult = copValidationService.validatePayee(payeeDetails)
    presentCoPConfirmation(result: copResult)
} else {
    // Standard flow — LIVE today, runs on every request
    presentStandardPayeeConfirmation(payeeDetails)
}
```

**Resolution:**
- `BMBFeatureData.ConfirmationOfPayee` → `"COP"`
- Function Data: `"COP": { "ALL": { "status": "OFF" } }`
- Classification: OFF → **KEEP ALL** (upcoming/disabled — NOT dead)

**Critical:** Do NOT delete the if-block. COP=OFF means the feature is not yet deployed, not that the code is abandoned. Both branches are KEEP.

**If user confirms COP is permanently abandoned** (not upcoming):
- Reclassify: if-block lines 85–142 → DEAD (+1.5 boost from user confirmation)
- Cascade: `CoPValidationService`, `CoPConfirmationViewController` — check if exclusively called from dead block

---

## Example 2 — Config Property True: BCard Balance Transfer Migration

**Property:** `BCard_BT_MT_Migration` | Config page: present (as app function, not DB property)
**Function Data:** `BCard_BT_MT_Migration` status=ON | min_version=BMB_03500 | age=850

```swift
// BMBOffersFeatureFlagConfigurations.swift
let useThinAPI = BMBFeatureStatusHelper.sharedInstance()
    .status(forFeature: BMBFeatureData.transferAndOffersAPIMigration) == .ON

if useThinAPI {
    // Modern thin-gateway API path — LIVE (switch ON, age=850)
    offersService.fetchOffersThinGateway(accountId: accountId) { result in
        self.handleThinGatewayResponse(result)
    }
} else {
    // Legacy SOAP/IMS path — DEAD (switch ON for 850 versions)
    offersService.fetchOffersLegacy(accountId: accountId) { result in
        self.handleLegacyResponse(result)
    }
}
```

**Resolution:**
- `BMBFeatureData.transferAndOffersAPIMigration` → `"BCard_BT_MT_Migration"`
- Function Data: ON, age=850 (range 500–1000)
- Classification: ON + age ≥ 500 + else-block calls legacy → **else-block DEAD**
- Boost: **+0.5** (age 500–1000 tier)

**Cascade check:**
```bash
grep -rn "fetchOffersLegacy\|handleLegacyResponse" --include="*.swift" . | grep -v "BMBOffersFeatureFlagConfigurations"
# Zero external callers → cascade DEAD (LIKELY, in shared service)
```

---

## Example 3 — ON Switch Stale: Scheduled Payments

**Switch:** `SSP_SCHEDULED_PAYMENTS` | Function Data status=ON | age=1200

```swift
// PaymentHubViewController.swift
let isScheduledPaymentsEnabled = BMBFeatureStatusHelper.isOn(BMBFeatureData.SSPScheduledPayments)

if isScheduledPaymentsEnabled {
    // SSP flow — LIVE (ON for 1200 versions, well past threshold)
    navigationController?.pushViewController(
        SSPScheduledPaymentsViewController(), animated: true
    )
} else {
    // Legacy STO flow — DEAD (age=1200 > 1000)
    navigationController?.pushViewController(
        LegacySTOViewController(), animated: true
    )
}
```

**Resolution:**
- `BMBFeatureData.SSPScheduledPayments` → `"SSP_SCHEDULED_PAYMENTS"`
- Function Data: ON, age=1200 (range 1000–1500)
- Classification: ON + age ≥ 1000 + else-block legacy → **else-block DEAD**
- Boost: **+1.0** (age 1000–1500 tier)

**Cascade:**
- `LegacySTOViewController` — if zero callers outside dead block → DEAD (LIKELY)
- `LegacySTODataSource` — same check → cascade if exclusive

---

## Example 4 — NOT FOUND: Feature Switch Missing From Both Sources

**Switch:** `DEBIT_NGCB_TF_SDM` | NOT in Function Data | NOT in Config page  
**Git:** last commit Mar 2025, feature added recently (~6 months)

```swift
// CardControlsCoordinator.swift
let isTempFreezeSDMEnabled = BMBFeatureStatusHelper.isOn(BMBFeatureData.debitNgcbSdmTempFreeze)

if isTempFreezeSDMEnabled {
    // New SDM-based temp freeze flow
    presentSDMTempFreezeFlow(for: card)
} else {
    // Current temp freeze flow
    presentCurrentTempFreezeFlow(for: card)
}
```

**Resolution:**
- `BMBFeatureData.debitNgcbSdmTempFreeze` → `"DEBIT_NGCB_TF_SDM"`
- Function Data: NOT FOUND
- Config page: NOT FOUND
- Git age: ~6 months (<12 months)
- Classification: NOT FOUND + no entry + <6 months → **KEEP ALL** (too new to judge)

No user prompt needed — the age threshold alone resolves this to KEEP.

---

## Example 5 — Policy Value: Offers Hub

**Policy:** `BarclaysPolicyType.OffersHubAvailable`  
**Source:** C001A login response / PlatformSession policies

```swift
// BMBOffersFeatureFlagConfigurations.swift
let isOffersHubAvailable = BMBPolicyValueHelper.isFeaturePolicyEnabled(
    for: BarclaysPolicyType.OffersHubAvailable
)

if isOffersHubAvailable {
    // Show offers hub tab
    addOffersHubTab(to: tabBarController)
} else {
    // Hide offers hub — use legacy offers location
    showLegacyOffersButton(in: accountSummaryView)
}
```

**Resolution for policy values:**

Policy values resolve differently from feature switches — they come from the C001A login response, not from the Function Data page. To classify:

1. Check if the policy key exists in Gateway Config page (pipe-delimited table)
2. If found with explicit value → apply classification matrix
3. If not found → policy is set per-user at login time → **KEEP ALL** (cannot determine dead statically)

**Key rule:** Policy values that vary per customer segment (e.g., "offers hub available for Premier but not for Basic") cannot be classified as dead code from static analysis alone. Only policies with universal ON/OFF across all segments can be promoted.

---

## iOS Entry Point Exception

These classes are never fully deleted, even if their master switch is OFF:

```swift
// ✗ NEVER delete the entire coordinator/view controller class
// ✓ Only delete the dead if-block body
// ✓ Keep the else block — it runs today

// PaymentFlowCoordinator.swift — registered in DI container
class PaymentFlowCoordinator: Coordinator {
    func start() {
        if BMBFeatureStatusHelper.isOn(BMBFeatureData.ConfirmationOfPayee) {
            // DELETE THIS BLOCK (if user confirms COP abandoned)
        } else {
            // KEEP — runs today
        }
    }
}
```

Applies to:
- `@main` / `@UIApplicationMain` classes
- `UIApplicationDelegate` conformers
- Root view controllers in storyboards (`UIMainStoryboardFile`)
- Coordinator classes registered in dependency injection containers
- React Native bridge modules (`RCT_EXPORT_MODULE`)
