---
name: arbiter-deprecate
agent: arbiter-deprecate-agent
allowed-tools: [Bash, Read, Glob, Grep, Write]
description: "Analyze and remove a specific deprecated class with targeted workflow"
---

# Deprecate: Fast Removal of Deprecated Code

Analyze a specific deprecated class and execute removal with a streamlined workflow, skipping full repository discovery and baseline phases.

## Arguments

```
CLASS_NAME              Fully qualified class name (required)
                       e.g., com.barclays.mobile.gateway.operation.data.ClientLogging

--auto                 Auto-approve removal if categorized as SAFE 
                       (age ≥6 months, forRemoval=true, 0 usages)

--dry-run              Show what would be removed without committing

--review               Prompt for approval on SAFE removals (default: auto without this flag)

--technology TECH      Target technology: java | ios (default: auto-detect)
--module MODULE        Target a specific submodule/package (optional)
--scheme SCHEME        Xcode scheme for validation (iOS only)
```

## Technology Routing

| Technology | Deprecation Signals | Validation |
|---|---|---|
| `java` | `@Deprecated`, `forRemoval=true`, age | `./gradlew build` + test |
| `ios` | `@available(*, deprecated)`, `DEPRECATED` pragma, age | `xcodebuild build` + test |

## Example

```
/arbiter-deprecate com.barclays.mobile.gateway.operation.data.ClientLogging --dry-run
/arbiter-deprecate com.barclays.mobile.gateway.operation.data.ClientLogging --auto
/arbiter-deprecate com.example.api.LegacyService --review

# iOS
/arbiter-deprecate OldPaymentVC --technology ios --scheme MyApp
/arbiter-deprecate LegacyNetworkManager --technology ios --module NetworkKit --dry-run
```

## Output

Deprecation analysis report with:
- Deprecation status (@Deprecated annotation, age, forRemoval flag)
- Replacement class/method (from JavaDoc)
- Usage count within repository
- Categorization: SAFE | REVIEW | CONSULT
- Removal plan (if approved)
- Validation results (compile + unit tests)

## Workflow

This command bypasses the full 7-phase workflow:

| Phase | Full Workflow | Deprecate Shortcut |
|-------|---|---|
| Preparation | ✅ Manual | ❌ Auto-verify in background |
| Discovery | ✅ Full repo | ❌ Skip (target class only) |
| Analysis | ✅ Full repo analysis | ✅ Target class + deprecation |
| Baseline | ✅ Establish baseline | ❌ Skip (assume clean) |
| Planning | ✅ Multi-task plan | ✅ Single task plan |
| Execution | ✅ Iterate tasks | ✅ Execute single task |
| Verification | ✅ Full validation | ✅ Compile + unit tests |

**Result:** ~5-7K tokens vs ~13.5K for full workflow.

## Categorization Rules

| Category | Criteria | Auto-Approval |
|----------|----------|---|
| **SAFE** | @Deprecated + forRemoval=true + age ≥1 year + 0 usages + clear replacement | ✅ With --auto |
| **REVIEW** | @Deprecated + 6-12 months old + <5 usages + clear replacement | ❌ Requires review |
| **CONSULT** | @Deprecated + <6 months old OR unclear replacement OR 5+ usages | ❌ Requires team approval |

### iOS categorization

| Category | Criteria | Auto-Approval |
|----------|----------|---|
| **SAFE** | @available(*, deprecated) + age ≥1 year + 0 usages + replacement named | ✅ With --auto |
| **REVIEW** | deprecated + 6-12 months old + <5 usages + replacement available | ❌ Requires review |
| **CONSULT** | deprecated + <6 months old OR unclear replacement OR 5+ usages | ❌ Requires team approval |

## Next Steps

- If removal succeeds: Review commit and run full test suite
- If removal fails: Investigate compilation/test failures; may need refactoring
- For REVIEW/CONSULT: Use `/arbiter-analyze` for deeper investigation

## When to Use

✅ **Use arbiter-deprecate when:**
- You have a specific deprecated class to remove
- You want fast removal (skip discovery/baseline)
- Class is marked @Deprecated(forRemoval=true)
- You need targeted, low-risk removal

❌ **Use full workflow (`/arbiter-discover` → `/arbiter-analyze`) when:**
- You want to analyze multiple deprecated classes
- You need comprehensive dead code scan
- You're establishing baseline for large refactor
