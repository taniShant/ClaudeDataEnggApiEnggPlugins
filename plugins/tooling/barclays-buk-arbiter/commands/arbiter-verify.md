---
name: arbiter-verify
agent: arbiter-verify-ios-agent
allowed-tools: [Bash, Read]
description: "Final verification after iOS dead code removal (includes the predicted-vs-actual calibration report)"
---

# Verify: Final Post-Removal Verification (iOS)

Run final verification after all iOS removal batches complete — full compile, full test suite, baseline comparison, and the calibration report (predicted confidence vs actual outcomes).

For Java projects, use `/arbiter-validate --report`.

## Arguments

```
--technology ios     Target technology (iOS only; default: auto-detect from .arbiter/swift/ state)
--module MODULE      Target a specific submodule/package (optional)
--scheme SCHEME      Xcode scheme for full verification
```

## Routing

| Technology | Agent | Verification Method |
|---|---|---|
| `ios` | arbiter-verify-ios-agent | Full xcodebuild compile + test suite, calibration report |

## Example

```
/arbiter-verify --technology ios --scheme MyApp
/arbiter-verify --technology ios --module PaymentKit --scheme MyApp
```

## Output

Final verification report:
- Total entities removed
- Code reduction metrics
- Test stability vs baseline
- Precision per confidence tier vs targets (from `.arbiter/swift/OUTCOMES.jsonl`)
- Summary pass/fail status

## When to Use

After `/arbiter-remove --technology ios --all` completes successfully, run this as the final check before merging.
