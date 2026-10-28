---
user-invocable: false
description: "iOS validation gates — xcodebuild, xctest, xcresult parsing, rollback strategy"
---

# Skill: iOS Validation

## Source Attribution

Validation methodology from Xcode build system documentation, xcresult bundle format, and arbiter safety-first removal principles.

## Agent Self-Check

- [ ] Build system auto-detected (xcworkspace > xcodeproj > SPM)
- [ ] Scheme auto-detected or user-specified
- [ ] Timeout handling for long builds (15 min compile, 30 min tests)
- [ ] Rollback via git backup branch
- [ ] xcresult parsing for structured test results
- [ ] Baseline comparison for regression detection

---

## Environment Pre-Check (Gate 0)

Before any removal batch executes, a one-time environment pre-check must pass:

```bash
xcodebuild build \
  -workspace App.xcworkspace \
  -scheme AppScheme \
  -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO \
  2>&1
```

| Result | Action |
|--------|--------|
| Exit 0 | Environment is functional — proceed to removals |
| Exit non-zero (Podfile.lock out of sync) | **ENVIRONMENT_BLOCKED** — halt, report `pod install` needed |
| Exit non-zero (signing error) | **ENVIRONMENT_BLOCKED** — halt, report provisioning issue |
| Exit non-zero (any other) | **ENVIRONMENT_BLOCKED** — halt, report build error |

**Rule:** Never attribute a build failure to a removal unless the project compiled successfully before the removal was applied.

---

## Validation Gates by Category

| Category | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Timeout |
|----------|--------|--------|--------|--------|---------|
| All | Environment pre-check | — | — | — | 15 min |
| SAFE (3.0-4.0) | ✓ | Compile | — | — | 15 min |
| LIKELY (2.0-2.9) | ✓ | Compile | Unit tests | — | 30 min |
| UNCERTAIN (1.0-1.9) | ✓ | Compile | Unit tests | Integration/UI | 45 min |

---

## Build System Detection

Priority order (first match wins):

1. **xcworkspace** — `*.xcworkspace` in project root (CocoaPods standard)
   ```bash
   xcodebuild build -workspace App.xcworkspace -scheme AppScheme
   ```

2. **xcodeproj** — `*.xcodeproj` in project root
   ```bash
   xcodebuild build -project App.xcodeproj -scheme AppScheme
   ```

3. **SPM** — `Package.swift` in project root
   ```bash
   swift build
   swift test
   ```

---

## Scheme Detection

If no `--scheme` specified:
```bash
xcodebuild -list -json [-workspace *.xcworkspace | -project *.xcodeproj]
```

Pick the first non-test scheme. If ambiguous, ask the user.

---

## Compile Validation

```bash
xcodebuild build \
  -workspace App.xcworkspace \
  -scheme AppScheme \
  -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO \
  2>&1
```

- `CODE_SIGNING_ALLOWED=NO` — avoids provisioning issues in CI/local
- Exit code 0 = pass, non-zero = fail
- Timeout: 900 seconds (15 minutes)

---

## Test Validation

### Unit Tests
```bash
xcodebuild test \
  -workspace App.xcworkspace \
  -scheme AppScheme \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -only-testing:AppTests \
  2>&1
```

### Integration / UI Tests (UNCERTAIN only)
```bash
xcodebuild test \
  -workspace App.xcworkspace \
  -scheme AppScheme \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  2>&1
```

---

## Baseline Comparison

### Establishing Baseline

On first run or `--establish-baseline`:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "compile_status": "success",
  "tests_total": 450,
  "tests_passed": 448,
  "tests_failed": 2,
  "tests_skipped": 3,
  "duration_seconds": 180
}
```

### Detecting Regressions

After removal, compare:
- `tests_failed_now > tests_failed_baseline` → REGRESSION
- `tests_passed_now < tests_passed_baseline` → REGRESSION
- `compile_status != success` → CRITICAL FAILURE

---

## Rollback Strategy

### Before Each Batch
```bash
git branch arbiter-backup-ios-$(date +%Y%m%d-%H%M%S)
```

### On Validation Failure
```bash
git checkout arbiter-backup-ios-TIMESTAMP -- .
```

This restores all files to pre-removal state without losing the backup branch.

### After Successful Completion
Backup branches can be cleaned up:
```bash
git branch -D $(git branch | grep arbiter-backup-ios)
```

---

## Timeout Handling

| Operation | Default Timeout | On Timeout |
|-----------|----------------|-----------|
| Compile | 900s (15 min) | FAIL — may indicate removed code broke includes |
| Unit tests | 900s (15 min) | FAIL — possible infinite loop from missing code |
| Integration tests | 1800s (30 min) | FAIL — UI tests are slow but shouldn't timeout |

On timeout: treat as validation failure, trigger rollback.

---

## Graceful Degradation

If Xcode is not available:
- **HALT** — do NOT proceed with removal
- Warn user: "⚠️ ENVIRONMENT_BLOCKED — Xcode not found. Cannot validate removals."
- Suggest: install Xcode or run on a machine with Xcode
- **Never skip compile validation** — unverified removal is unsafe

If simulator not available:
- Skip UI tests only
- Run unit tests with `swift test` (SPM) if possible
- Compile validation still mandatory
