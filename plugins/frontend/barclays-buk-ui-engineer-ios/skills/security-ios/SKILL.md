---
name: security-ios
description: iOS-specific secure coding extensions for buk-ui-engineer-ios. Extends barclays-buk-standards:security with BarclaysBlueprint, App Attest, TrustKit, and Xcode-specific requirements. Load alongside barclays-buk-standards:security — do not use in isolation.
user-invocable: false
owner: BUK PE
review_trigger: BarclaysBlueprint security component update, App Attest API change
---

# iOS Security — Extension to BUK Base Standards

> **Source:** barclays/mobile-ios-client security standards, BarclaysBlueprint v5.35+
> **Owner:** BUK PE
> **Review trigger:** BarclaysBlueprint security component update, App Attest API change
> This skill extends `barclays-buk-standards:security`. It does NOT repeat the baseline — load both skills together.
> When a rule here conflicts with the baseline, this takes precedence for iOS.

---

## Quick Start

```swift
// Sensitive input — always BlueprintSecureField
BlueprintSecureField(text: $viewModel.password, placeholder: "Password")

// PIN entry — always BlueprintKeypad + BlueprintPasscodeIndicator
BlueprintKeypad(onInput: viewModel.handlePinInput)
BlueprintPasscodeIndicator(filledCount: viewModel.pinLength, totalCount: 6)

// Closures — always [weak self]
viewModel.onComplete = { [weak self] in
    guard let self else { return }
    self.navigate()
}

// Never store secrets in @AppStorage or UserDefaults
// ✗ @AppStorage("authToken") var token = ""
// ✓ Use Keychain via the approved platform abstraction
```

---

## Agent Self-Check

Before finalising any generated iOS file touching security concerns:

- [ ] All password, PIN, card number, CVV, and sort code inputs use `BlueprintSecureField` — never plain `TextField` or `SecureField`
- [ ] All PIN entry uses `BlueprintKeypad` + `BlueprintPasscodeIndicator` — never custom numeric input
- [ ] No `@AppStorage` or `UserDefaults` for tokens, credentials, or sensitive identifiers — use Keychain
- [ ] `[weak self]` in every closure that captures `self` — no strong reference cycles
- [ ] No PII (account numbers, sort codes, NI numbers, card numbers, DOB) in `print()`, `NSLog()`, or `Logger` calls
- [ ] No hardcoded API keys, tokens, or secrets in generated source files
- [ ] Biometric flows use the approved Blueprint pattern — never `LocalAuthentication` directly in views

---

## 1. BarclaysBlueprint Security Constraints

The internal iOS design system (`BarclaysBlueprint`) handles some controls automatically. Do NOT re-implement these:

| Blueprint Component | What it provides automatically |
|---|---|
| `BlueprintSecureField` | Disables autocorrect, autocomplete, and clipboard for sensitive fields (passwords, card numbers, CVV) |
| `BlueprintKeypad` + `BlueprintPasscodeIndicator` | Secure numeric PIN entry with masked indicators — handles biometric fallback coordination |
| `BlueprintSecureCode` | Displays masked sensitive values (PINs, security codes) with correct accessibility redaction |
| `BlueprintInterrupt` | Loading overlay that blocks interaction during sensitive operations |

**Critical constraint:** Do NOT add custom `UITextField.isSecureTextEntry` or manual PIN entry implementations alongside these Blueprint components — it duplicates and may conflict with Blueprint's implementation.

> **Note:** The `BP*` prefix is legacy. The current BarclaysBlueprint library (v5.35+) uses the full `Blueprint*` prefix for all components. If you see `BPSecureTextField`, `BPBiometricPrompt`, or `BPScreenProtection` in code, these are references to older documentation — the correct names are `BlueprintSecureField`, `BlueprintKeypad`/`BlueprintPasscodeIndicator`, and there is no standalone screen protection component (use system background lifecycle handling instead).

---

## 2. App Attest and DeviceCheck

Apple's App Attest API provides hardware-backed assertion that requests originate from a legitimate, unmodified build of the app on a genuine Apple device.

### Requirement

- All API calls that initiate financial transactions or authenticate a user must include an App Attest assertion
- Use `DCAppAttestService` to generate and verify assertions; do not implement a custom device integrity check for this purpose
- Fall back to `DeviceCheck` (DCDevice) for devices that do not support App Attest (pre-A12 Bionic)
- The assertion must be validated server-side — client-side validation only is not sufficient

```swift
// ✅ Correct — generate assertion before sensitive API call
let service = DCAppAttestService.shared
guard service.isSupported else {
    // Fall back to DeviceCheck for older hardware
    return useDeviceCheckFallback()
}
let keyId = try await service.generateKey()
let assertion = try await service.generateAssertion(keyId, clientDataHash: requestHash)
// Pass assertion in request header — validated server-side
```

---

## 3. TrustKit Certificate Pinning

`BPNetworkClient` configures TrustKit by default using the Barclays certificate bundle. You only need to intervene when:

- Making direct `URLSession` calls outside of `BPNetworkClient`
- Integrating a third-party SDK that manages its own network stack

### Requirement for direct URLSession usage

```swift
// ✅ Correct — implement pinning validator in URLSession delegate
func urlSession(
    _ session: URLSession,
    didReceive challenge: URLAuthenticationChallenge,
    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
) {
    let validator = TrustKit.sharedInstance().pinningValidator
    if !validator.handle(challenge, completionHandler: completionHandler) {
        completionHandler(.cancelAuthenticationChallenge, nil)
    }
}
```

Never call `completionHandler(.useCredential, URLCredential(trust: challenge.protectionSpace.serverTrust!))` unconditionally — this disables certificate validation entirely.

---

## 4. Xcode Build Settings

These must be verified before every production release. The iOS Platform CI pipeline checks these automatically, but generate them correctly from the start.

| Setting | Required value | Why |
|---|---|---|
| `DEBUG_INFORMATION_FORMAT` | `dwarf-with-dsym` for Release | dSYMs for crash symbolication; debug info not in binary |
| `ENABLE_BITCODE` | `NO` (Xcode 14+, bitcode deprecated) | Apple deprecated; leave disabled |
| `SWIFT_OPTIMIZATION_LEVEL` | `-Owholemodule` for Release | Enables whole-module optimisation; harder to reverse |
| `VALIDATE_PRODUCT` | `YES` | Runs entitlement and provisioning checks at build time |
| `GCC_PREPROCESSOR_DEFINITIONS` | Must not include `DEBUG=1` in Release | Prevents debug code paths in production |
| `OTHER_SWIFT_FLAGS` | Must not include `-Onone` in Release | `-Onone` disables optimisation and leaves debug symbols |
| Code signing | Distribution certificate (not development) for App Store/Enterprise builds | |

---

## 5. VoiceOver and Secure Screen Readers

iOS VoiceOver reads screen content aloud. Sensitive data fields need explicit suppression:

```swift
// ✅ Correct — suppress VoiceOver on sensitive values
accountNumberLabel.accessibilityElementsHidden = true
// Or provide a redacted label instead of the real value:
accountNumberLabel.accessibilityLabel = "Account number ending \(last4)"
```

Blueprint `BPSecureTextField` handles this automatically. For custom display components showing sensitive data (account numbers, sort codes, card PANs) — always provide a redacted `accessibilityLabel`, never expose the full value.

---

## 6. iOS-Specific Checklist Extension

Add these to the base `barclays-buk-standards:security` checklist when reviewing iOS code:

### App Integrity
- [ ] `DCAppAttestService` used for transaction/auth API calls
- [ ] Server-side assertion validation confirmed with backend team
- [ ] `DeviceCheck` fallback implemented for pre-A12 devices

### Build
- [ ] `SWIFT_OPTIMIZATION_LEVEL = -Owholemodule` in Release scheme
- [ ] `GCC_PREPROCESSOR_DEFINITIONS` does not include `DEBUG=1` in Release
- [ ] Distribution certificate used for production signing
- [ ] `BPScreenProtection` active on all screens displaying PII or financial data

### Networking
- [ ] Direct `URLSession` calls implement TrustKit delegate (not using `BPNetworkClient`)
- [ ] No unconditional `useCredential` in auth challenge handler

### Accessibility + Sensitive Data
- [ ] Custom sensitive-data views have redacted `accessibilityLabel` (not the real value)
- [ ] `BPSecureTextField` used for password and card number inputs (not bare `UITextField`)
