---
name: arbiter-validate
agent: arbiter-validate-agent
allowed-tools: [Bash, Read, Glob, Grep]
description: "Post-removal validation: test results, compilation, confidence metrics"
---

# Validate: Comprehensive Post-Removal Verification

Execute full test suite and parse results to verify no regressions after dead code removal.

## Arguments

```
--scope all              Run full test suite (default)
--scope unit             Run unit tests only
--scope integration      Run integration tests only
--baseline PATH          Baseline results for comparison
--report                 Generate detailed Markdown report
--technology TECH   Target technology: java | ios (default: auto-detect)
--module MODULE     Target a specific submodule/package (optional)
--scheme SCHEME          Xcode scheme for validation (iOS only)
```

## Technology Routing

| Technology | Agent |
|---|---|
| `java` | arbiter-validate-agent |
| `ios` | arbiter-validate-ios-agent |

If `--technology` is not provided, the technology is auto-detected (`*.xcodeproj`, `*.xcworkspace`, `Package.swift` → ios; `pom.xml`, `build.gradle` → java).

iOS validation tools: `xcodebuild test`, xcresult parsing.

## Example

```
/arbiter-validate
/arbiter-validate --scope unit
/arbiter-validate --report
/arbiter-validate --baseline .arbiter/baseline_validation.json

# iOS
/arbiter-validate --technology ios --scheme MyApp
/arbiter-validate --technology ios --baseline .arbiter/swift/baseline.json
```

## Output

Validation report with:
- Test results (passed, failed, errors, skipped)
- Compilation status
- Regression analysis (compared to baseline)
- Confidence metrics (accuracy, false positives)

## Next Step

If all validations pass, run `/arbiter-remove next` to execute subsequent tasks, or `/arbiter-status` to see overall progress.

If regressions detected, re-run `/arbiter-analyze` to review confidence scoring.
