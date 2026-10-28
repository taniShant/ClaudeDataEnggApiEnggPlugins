# Arbiter iOS Extension — Technical Walkthrough

**Audience:** Engineers reviewing the MR, plugin consumers, and anyone wanting to understand how iOS dead code removal works.
**Author:** Pratik Goswami  
**Applies to:** `barclays-buk-arbiter` v1.7.1. For results on `barclays-app`, the spot-check methodology and the pilot plan, see [iOS-ANALYSIS-v1.6-OVERVIEW.md](iOS-ANALYSIS-v1.6-OVERVIEW.md).

---

## Executive Summary

Arbiter iOS extends the existing Arbiter dead-code-removal capability to support Swift and Objective-C codebases. The implementation follows the established Java plugin pattern while adding iOS-specific discovery, analysis, planning, removal and validation flows.

Key capabilities:

- Detects unused code across Swift and Objective-C projects using **syntax trees** (tree-sitter), not text matching.
- Understands iOS-specific references that are not visible through source-code analysis, including Storyboards, XIBs (including old-format XIBs), plists and asset-related metadata.
- Accounts for dynamic runtime patterns such as `NSSelectorFromString`, `NSClassFromString`, `performSelector` and KVC — including selectors built from runtime strings.
- Protects framework-called code through UIKit, SwiftUI, Combine, CoreData and React Native rules, plus an index of every selector declared by the iOS SDK, Pods and vendored frameworks.
- Uses confidence-based scoring to reduce false-positive removals.
- Removes whole declarations (Swift) and validates each batch with Xcode build and test gates; failures are traced to the entity that caused them.
- Records predicted vs. actual outcomes for every removal so tier precision can be measured.
- Supports dry-run execution, backup branch creation and per-batch rollback on validation failure.

The goal is not to aggressively delete as much code as possible. The goal is to safely identify high-confidence removal candidates, validate them in controlled batches and preserve application stability throughout the process.

> **Objective-C:** identified and scored, but **not removed automatically** in v1.6. ObjC candidates are listed for manual review in the plan's `reviewOnly` section.

---

## 1. What Problem Does This Solve?

The Arbiter plugin safely identifies and removes dead code. Until now it only supported **Java**. iOS codebases, especially Swift and Objective-C applications, have unique challenges:

| Challenge | Why it is hard |
|---|---|
| Storyboard/XIB references | Classes and actions can be referenced by string in XML and may be invisible to source analysis. |
| Dynamic dispatch | `NSSelectorFromString`, `performSelector`, KVC and related patterns can call code by name at runtime. |
| Framework lifecycle | Methods such as `viewDidLoad` and `tableView(_:cellForRowAt:)` are called by iOS, not directly by application code. |
| Mixed Swift / Objective-C | Swift calls ObjC under different names (`loadWithItem:` → `load(withItem:)`), and ObjC calls Swift through generated headers. |
| React Native bridges | `RCT_EXPORT_MODULE` and exported methods can be invoked from JavaScript. |
| Property wrappers | `@State`, `@Published` and similar patterns can be used implicitly by the framework. |

**Arbiter iOS** handles these by combining syntax-tree source analysis, resource scanning, framework rules, dynamic dispatch detection and Xcode validation.

---

## 2. How It Fits Into the Existing Plugin

```text
┌────────────────────────────────────────────────────────────────┐
│                   barclays-buk-arbiter v1.7.1                    │
├────────────────────────────────────────────────────────────────┤
│  UNIFIED COMMANDS — technology passed as argument               │
├────────────────────────────────────────────────────────────────┤
│  /arbiter-discover [PATH] --technology java|ios [--module M]    │
│  /arbiter-analyze  [PATH] --technology java|ios [--module M]    │
│  /arbiter-plan           --technology java|ios [--module M]     │
│  /arbiter-remove         --technology java|ios [--module M]     │
│  /arbiter-validate       --technology java|ios [--module M]     │
│  /arbiter-verify         --technology java|ios [--module M]     │
│  /arbiter-status         --technology java|ios [--module M]     │
│  /arbiter-deprecate      --technology java|ios [--module M]     │
├────────────────────────────────────────────────────────────────┤
│  Technology       │ State Dir        │ Build Tool    │ Tests    │
│  java             │ .arbiter/cache/  │ Gradle/Maven  │ JUnit   │
│  ios              │ .arbiter/swift/  │ Xcode/SPM     │ XCTest  │
└────────────────────────────────────────────────────────────────┘
```

**Key design choices:**

- **Unified command set:** All commands accept `--technology java|ios` instead of separate `-ios` suffixed commands. This keeps the plugin extensible as new technologies are added.
- **Auto-detection:** If `--technology` is omitted, the plugin detects the target from project files (`.xcodeproj`/`Package.swift` → ios, `pom.xml`/`build.gradle` → java).
- **Optional `--module`:** Any command can target a specific submodule, package, or framework target to scope analysis and removal to a subset of the codebase.
- **Scripts ship with the plugin:** the iOS agents run `${CLAUDE_PLUGIN_ROOT}/src/ios/resolve_env.py` (Claude Code substitutes the plugin's install path in agent content), which reports the interpreter to use and warns about multiple installed versions, so they work from inside the repository being analysed.

---

## 3. Architecture Diagram

This view shows how the iOS implementation is structured at a system level.

```text
                       ┌──────────────────────┐
                       │     iOS Codebase      │
                       │ Swift / ObjC / Xcode  │
                       └──────────┬───────────┘
                                  │
        ┌─────────────────┬───────┴─────────┬──────────────────────┐
        │                 │                 │                      │
        ▼                 ▼                 ▼                      ▼
┌─────────────────┐ ┌─────────────────┐ ┌────────────────────┐ ┌────────────────────┐
│ Call Graph       │ │ Resource Scanner│ │ Dynamic Dispatch    │ │ Framework Selector │
│ Analyzer         │ │ Storyboard/XIB/ │ │ Scanner             │ │ Index              │
│ (tree-sitter     │ │ plist           │ │                     │ │ SDK / Pods /       │
│  Swift + ObjC)   │ │                 │ │                     │ │ vendored headers   │
└────────┬────────┘ └────────┬────────┘ └─────────┬──────────┘ └─────────┬──────────┘
         └───────────────────┴────────────┬───────┴──────────────────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Framework Rules      │
                               │ UIKit / SwiftUI / RN │
                               └──────────┬──────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Confidence Engine    │
                               │ Score 0.0 to 4.0     │
                               └──────────┬──────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Removal Planner      │
                               │ Swift batches +      │
                               │ ObjC review list     │
                               └──────────┬──────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Removal Executor     │
                               │ Whole declarations   │
                               └──────────┬──────────┘
                                          ▼
                               ┌─────────────────────────┐
                               │ Validation Layer         │
                               │ Build / Test / Attribute │
                               │ / Per-batch rollback     │
                               └──────────┬──────────────┘
                                          ▼
                               ┌─────────────────────┐
                               │ Outcome Ledger &     │
                               │ Calibration Report   │
                               └─────────────────────┘
```

### Architecture Responsibilities

| Component | Responsibility |
|---|---|
| Project Detector | Identifies Xcode project, workspace, SPM setup, schemes and test targets. |
| Call Graph Analyzer | Parses Swift and Objective-C with tree-sitter; extracts entities with line ranges and resolves references across files and languages. |
| Resource Scanner | Finds hidden class and action references in Storyboards, XIBs (modern and legacy format) and plist files. |
| Dynamic Dispatch Scanner | Searches for runtime string-based class, method and property access. |
| Framework Selector Index | Lists every selector declared by the iOS SDK, Pods/Carthage and vendored `.framework` headers, so overrides and delegate methods are recognised. |
| Framework Rules Engine | Applies lifecycle, annotation, protocol and superclass rules. |
| Confidence Engine | Converts discovered signals into a removal-confidence score. |
| Planner | Groups Swift candidates into SAFE, LIKELY and UNCERTAIN batches; lists ObjC candidates for review. |
| Removal Executor | Removes whole declarations, validates, attributes failures, retries, commits or rolls back the batch. |
| Calibration Report | Compares predicted tiers with real outcomes to measure precision. |

---

## 4. The iOS Workflow

```text
/arbiter-discover . --technology ios [--module PaymentKit]
        │
        ▼
Phase 1: DISCOVER + ANALYZE
- Detect project type
- Parse Swift and ObjC (tree-sitter); extract entities and references
- Scan resources (Storyboard/XIB/plist)
- Scan dynamic dispatch patterns
- Build the framework selector index (SDK cached in ~/.cache/arbiter/)
- Apply framework rules
- Score confidence
        │
        ▼
/arbiter-plan --technology ios [--module PaymentKit] --sprints 2
        │
        ▼
Phase 2: PLAN
- Group candidates by confidence
- Batch Swift SAFE, LIKELY and UNCERTAIN candidates
- Assign validation tier per batch
- List Objective-C candidates under reviewOnly (with every .h/.m declaration site)
        │
        ▼
/arbiter-remove --technology ios [--module PaymentKit] --all --scheme MyApp
        │
        ▼
Phase 3: REMOVE
- Refuse unstamped plans and uncommitted tracked changes (main repo or submodules); baseline build
- Create backup branch (once per run, main repo + submodules)
- Re-locate and remove each declaration in full
- Run Xcode validation gate (every build log saved to .arbiter/swift/logs/)
- On failure: fix superfluous SwiftLint disables, attribute compiler errors, then halve the
  batch until each failing entity is isolated — keep everything else
- Commit each batch in the repo that owns the files (submodules, then pointer commit)
- Continue with the next batch; report all failures at the end
- Append predicted vs actual outcome per entity to OUTCOMES.jsonl
        │
        ▼
/arbiter-verify --technology ios [--module PaymentKit]
        │
        ▼
Phase 4-5: VERIFY + STATUS
- Run full validation
- Compare against baseline
- Calibration report: precision per tier against targets
- Report removed entities, validation status and stability
```

---

## 5. Confidence Scoring — The Core Idea

Every entity starts at **4.0**, which means it appears removable unless evidence suggests otherwise. Deductions are then applied when the scanners find evidence that the entity may still be used. Any entity with at least one reference is KEEP.

```text
PaymentViewController                 Score: 4.0 start
  ├── inherits UIViewController       -0.7  → 3.3
  ├── has viewDidLoad()               AUTO-KEEP because framework/lifecycle method

UnusedHelper                          Score: 4.0 → SAFE
  ├── private
  ├── no inbound references
  ├── no resource reference
  └── no dynamic dispatch reference

OldLoginVC                            Score: 4.0 start
  ├── referenced in Main.storyboard   -2.5  → 1.5
  └── UNCERTAIN — moves away from SAFE

+[BMBViewControllerTrackingHelper BMBHomeViewController]
  └── class is sent NSSelectorFromString(className)   AUTO-KEEP (runtime-built selector)

BridgeModule                          Score: 4.0 start
  ├── contains RCT_EXPORT_MODULE      AUTO-KEEP because React Native bridge
```

### Why a 0-4 Scale?

The 0-4 scale is intentionally simple. It avoids false precision and maps cleanly to removal decisions.

Benefits:

- Easier for reviewers to reason about than percentage-based confidence.
- Fits naturally into category bands: SAFE, LIKELY, UNCERTAIN and KEEP.
- Keeps deductions transparent and explainable.
- Aligns with the existing Arbiter confidence-band approach.
- Makes conservative defaults easier to enforce.

### Category Thresholds

```text
4.0 ┐
    │ SAFE        3.0 – 4.0   Remove with compile validation
3.0 ┤
    │ LIKELY      2.0 – 2.9   Remove with compile + test validation
2.0 ┤
    │ UNCERTAIN   1.0 – 1.9   Remove one at a time with compile + test validation, review first
1.0 ┤
    │ KEEP        < 1.0       Do not remove (also: any auto-keep signal)
0.0 ┘
```

### What Causes Deductions?

| Signal | Deduction | Example |
|---|---:|---|
| Entry point | KEEP | `@main`, `@UIApplicationMain`, `UIApplicationDelegate` / `UIWindowSceneDelegate` (inherited or adopted) |
| Lifecycle method | KEEP | `viewDidLoad`, `tableView(_:cellForRowAt:)` |
| Framework selector (ObjC) | KEEP | Selector declared by the SDK, Pods or a vendored framework |
| Framework override (Swift) | KEEP | `override` of a method no repo type declares |
| SDK-named Swift method | KEEP | Non-private method whose name matches an SDK/Pods selector's Swift name |
| Runtime-built selector | KEEP | Method of a class named where `NSSelectorFromString(<variable>)` is used |
| Test code | KEEP | `Tests/`, `Mocks/`, `Stubs/`, `*Tests`/`*Spec`/`*Mock(s)`/`*Stub(s)` files, `XCTestCase` subclasses |
| React Native bridge | KEEP | `RCT_EXPORT_MODULE` |
| Used in call graph | KEEP | Any reference found |
| Storyboard/XIB custom class | -2.5 | `<viewController customClass="PaymentVC">`, legacy `<string>PaymentVC</string>` |
| Storyboard/XIB connected action | -2.5 | `<action selector="didTap:">` |
| `@IBAction` / `@IBOutlet` | -2.0 | Interface Builder connections |
| Override method | -2.0 | Called by superclass/framework (v1 engine) |
| `NSClassFromString` target | -2.0 | Class looked up by string literal |
| Dynamic dispatch target | -1.5 | `NSSelectorFromString("method")`, `performSelector`, KVC |
| `@objc` | -1.5 | Exposed to Objective-C runtime |
| Extension member | -1.5 | Globally callable |
| Public/open visibility | -1.0 | May be used by other modules (ObjC: declared in a header) |
| Codable conformance | -1.0 | Serialization/deserialization |
| `UIViewController` subclass | -0.7 | Framework-managed lifecycle |
| `@State` / `@Published` | -0.7 | SwiftUI/Combine observation |

---

## 6. Validation Matrix

The validation strategy is graduated. Higher-confidence candidates go through lighter validation; lower-confidence candidates require stronger validation and reviewer involvement.

| Classification | Score | Batch Size | Compile Check | Tests | Manual Review | Behaviour on Failure |
|---|---:|---:|---|---|---|---|
| SAFE | 3.0 – 4.0 | 10 | Required | Not run | Not required by default | Lint fix → attribute → bisect; failing entities restored, rest kept; continue |
| LIKELY | 2.0 – 2.9 | 5 | Required | Required | Not required by default | Same |
| UNCERTAIN | 1.0 – 1.9 | 1 | Required | Required | Recommended before including in `--scope` | Same |
| KEEP | < 1.0 or auto-keep | — | N/A | N/A | N/A | Never planned |

Objective-C entities are never batched (review only).

### Validation Gate Principles

- The project must build **before** any removal, and the working tree must be clean.
- A backup branch is created once per run before modifying code.
- Every removal batch must pass its assigned validation gate.
- Builds use `-destination 'generic/platform=iOS Simulator'` (no code signing); tests use the first available iPhone simulator. Both can be overridden; the build timeout defaults to 3600s.
- Failing entities are restored file by file and the rest of the batch is kept; earlier committed batches are not touched. The run continues with the next batch (`--stop-on-failure` to stop) and stops only if the baseline itself no longer builds (`environment_blocked`).
- Every build's output is kept under `.arbiter/swift/logs/`.
- `--dry-run` should be used before real removal to preview the plan.

---

## 7. The Scanners

### Scanner 1: Call Graph Analyzer

Reads:

- `*.swift` — parsed with `tree-sitter-swift`
- `*.h`, `*.m`, `*.mm` — parsed with `tree-sitter-objc`, after blanking Foundation and project macros (`NS_ASSUME_NONNULL_BEGIN`, `NS_SWIFT_NAME(...)`, `BWK_EXTERN`, …) with same-length whitespace so line numbers stay exact

Skips `Pods/`, `Carthage/`, `DerivedData/`, `.build/` and vendored `*.framework/` / `*.xcframework/` directories.

Finds:

- Swift classes, structs, enums, actors, protocols and methods, each with full line range (attributes and doc comments included)
- Objective-C classes (merged across `@interface`, class extension and `@implementation`), protocols, and methods with full selectors, e.g. `-[BMBService countFor:inSection:]`, with every declaration site

Builds:

- **Type references:** inheritance, protocol conformance, type annotations, generic arguments, constructor calls, class message receivers. Comments, strings, `#import`s, `@class` forward declarations, extensions and a type's references to itself don't count.
- **Method references:** Swift call sites by name (recursion excluded); ObjC message sends by full selector, `@selector(...)` and dot-syntax properties.
- **Swift ↔ ObjC bridging:** Swift calls to ObjC under imported names (`load(withItem:)`, `NS_SWIFT_NAME`), ObjC mentions of Swift names, and protocol requirements implemented in the other language.

### Scanner 2: Resource Scanner

Reads:

- `*.storyboard`
- `*.xib`
- `*.plist`

Finds:

- `customClass="ClassName"`
- Action selectors (`<action selector="didTap:">`) and outlets
- With `--entities`, known class names and action labels in old-format XIBs (`<string>MyViewController</string>`, `<string key="label">didTap:</string>`)
- Class names in plists

Why it matters:

- Removing a storyboard-referenced class or action can compile successfully but fail at runtime.

### Scanner 3: Dynamic Dispatch Scanner

Reads:

- `*.swift`
- `*.m`
- `*.h`

Finds patterns such as:

```swift
NSSelectorFromString("methodName")
NSClassFromString("ClassName")
value(forKey: "propertyName")
```

And Objective-C patterns such as:

```objc
performSelector:@selector(methodName)
```

In addition, the call graph analyzer detects selectors built from **runtime strings** — `NSSelectorFromString(className)`, `NSClassFromString(name)`, `Selector(name)` — and treats every class named in that method as a dynamic dispatch target.

Why it matters:

- Static analysis may miss calls that are built from strings or invoked through the Objective-C runtime.

### Scanner 4: Framework Rules Engine and Selector Index

Knows about:

- UIKit lifecycle methods.
- SwiftUI and Combine annotations.
- Framework-managed protocol conformances.
- Common superclass patterns such as `UIViewController`, `UITableViewController`, `NSManagedObject` and related framework types.
- **Every selector declared by the installed iOS SDK** (~25k, cached in `~/.cache/arbiter/` per SDK version), plus `Pods/`, `Carthage/` and vendored `.framework` headers.

Why it matters:

- Framework-managed methods can look unused in application code but are called by iOS at runtime. Matching against the SDK's own declarations catches overrides and delegate methods that no fixed rule table lists.

### Scanner 5: Project Detector

Detects:

- Build system: `xcworkspace`, `xcodeproj` or Swift Package Manager.
- Xcode version.
- Available schemes.
- Unit-test and UI-test targets.

Why it matters:

- Validation requires the correct Xcode project/workspace, scheme and test destination.

---

## 8. Why tree-sitter

v1.2 used regex. In practice that produced both false negatives and false positives: mentions in comments and strings counted as usage, cross-file references were missed, declarations such as `@objc public final class` or multi-line signatures weren't recognised, and short method names were skipped entirely. A previous campaign on the Barclays app removed 17 entities and had 274 blocked.

v1.6 parses with **tree-sitter**:

- **Still Python-only** — `pip install tree-sitter tree-sitter-swift tree-sitter-objc`; no SourceKit, no compiler internals.
- **No build or index required** — works on any checkout, before the project is configured.
- **Works on mixed Swift / Objective-C repositories.**
- **Fast** — `barclays-app` (11k Swift + 2.8k ObjC files) analyses in about 3 minutes.
- **Tolerant** — files with syntax the grammar can't fully read (0.5% Swift, 2.7% ObjC on `barclays-app`) are analysed from partial trees and never removed.

### Trade-off

tree-sitter gives **syntax**, not **types**. References are resolved by name (Swift) and selector (ObjC), not by the compiler's type checker. That errs towards keeping code: two methods with the same name share a usage count, and an ObjC method whose selector also exists in the SDK is kept. SourceKit/IndexStore (or Periphery) would be more precise but need a full build.

That trade-off is managed through conservative safety mechanisms:

- Any reference keeps an entity; ambiguity resolves to KEEP.
- Runtime and framework patterns apply confidence deductions or auto-keep.
- Resource scanning reduces storyboard and XIB false positives.
- Xcode build and test validation is required before changes are committed.
- Failures are attributed and rolled back per batch.
- Every outcome is recorded, so precision is measured rather than assumed.

If tree-sitter is not installed, analysis falls back to the legacy regex path and removal is disabled.

---

## 9. Safety Mechanisms

```text
Before Removal              During Removal                    After Failure
┌───────────────────┐       ┌───────────────────────────┐     ┌────────────────────────┐
│ stamped plan       │       │ re-locate declaration      │     │ fix superfluous lint    │
│ clean tracked tree │ ────► │ remove full range          │ ──► │ attribute compiler errs │
│ baseline build     │       │ xcodebuild build           │     │ halve until isolated    │
│ backup branches    │       │ xcodebuild test (LIKELY+)  │     │ restore failing only    │
│ (repo + submodules)│       │ logs → .arbiter/swift/logs │     │ baseline recheck        │
└───────────────────┘       └───────────────────────────┘     └────────────────────────┘
                                         │
                                         ▼
               commit per owning repo (submodules → pointer) · append OUTCOMES.jsonl
```

Safety controls:

- Conservative scoring: when in doubt, keep the code.
- Multiple scanners: source, resources, runtime dispatch, framework rules and the SDK selector index.
- Graduated validation: SAFE, LIKELY and UNCERTAIN use different validation levels.
- Dry-run support: preview before execution.
- Backup branch: created once per run before any change, in the main repo and every submodule.
- Provenance: every artifact carries a `generatedBy` stamp (plugin version + script hashes); the planner and executor refuse unstamped input, so results can't come from ad-hoc scripts.
- Syntax-aware removal: declarations sharing a line with other code, files that don't fully parse, and types whose members have external callers are skipped, not partially removed.
- Xcode project awareness: a file left empty is deleted only if no `project.pbxproj` references it (including `Pods/Pods.xcodeproj` for development pods); otherwise it is left empty and reported.
- Failure isolation: failing entities are found by compiler-error attribution or bisection and restored; the rest of the batch is kept.
- Outcome ledger: every attempt is recorded as predicted vs. actual.

---

## 10. File Structure

```text
plugins/tooling/barclays-buk-arbiter/
│
├── agents/
│   ├── arbiter-discover-analyze-ios-agent.md
│   ├── arbiter-plan-ios-agent.md
│   ├── arbiter-remove-ios-agent.md
│   ├── arbiter-validate-ios-agent.md
│   └── arbiter-verify-ios-agent.md
│
├── commands/                              ← UNIFIED (no -ios suffix)
│   ├── arbiter-discover.md                  --technology ios|java [--module M]
│   ├── arbiter-analyze.md                   --technology ios|java [--module M]
│   ├── arbiter-plan.md                      --technology ios|java [--module M]
│   ├── arbiter-remove.md                    --technology ios|java [--module M]
│   ├── arbiter-validate.md                  --technology ios|java [--module M]
│   ├── arbiter-verify.md                    --technology ios|java [--module M]
│   ├── arbiter-status.md                    --technology ios|java [--module M]
│   └── arbiter-deprecate.md                 --technology ios|java [--module M]
│
├── skills/
│   ├── arbiter_ios_patterns/SKILL.md
│   ├── arbiter_ios_framework_detection/SKILL.md
│   ├── arbiter_ios_validation/SKILL.md
│   └── arbiter_switch_analysis/SKILL.md
│
├── src/ios/
│   ├── ios_detector.py
│   ├── ast_reference_scanner.py          ← tree-sitter reference graph (Swift + ObjC)
│   ├── objc_syntax.py                    ← ObjC parsing, selectors, framework selector index
│   ├── ios_call_graph_analyzer.py        ← entities + usage counts
│   ├── ios_framework_rules.py
│   ├── ios_resource_scanner.py
│   ├── ios_dynamic_dispatch_scanner.py
│   ├── ios_confidence_engine.py          ← scorer used by the agents
│   ├── ios_confidence_engine_v2.py       ← AST-aware scorer used by ios_analyze_improved.py
│   ├── ios_analyze_improved.py           ← one-shot pipeline (analysis → plan)
│   ├── ios_deadcode_finder.py
│   ├── ios_planner.py
│   ├── ios_removal_executor.py
│   └── ios_calibration_report.py         ← predicted vs actual
│
├── docs/
│   ├── iOS-TECHNICAL-WALKTHROUGH.md      ← this document
│   └── iOS-ANALYSIS-v1.6-OVERVIEW.md     ← results, spot check, pilot plan
│
└── hooks/
    ├── swift-compile-validator.py
    └── swift-test-validator.py
```

Outputs in the analysed repository (`.arbiter/swift/`):

| File | Content |
|---|---|
| `ENTITIES.json` | Entities with line ranges, declaration sites and usage counts |
| `RESOURCE_REFS.json`, `DISPATCH_SCAN.json` | Storyboard/XIB/plist and dynamic-dispatch findings |
| `CONFIDENCE.json` | Scored entities with reasons |
| `PLAN.json` | Swift batches + `reviewOnly` ObjC candidates |
| `REMOVAL_LOG.json` | Per-batch and per-entity results |
| `OUTCOMES.jsonl` | Predicted vs actual, one line per attempted entity (append-only) |

---

## 11. Where the Code Came From

The iOS extension combines two prior implementations:

```text
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│ f_barclays-claude-code-plugins  │     │ garbage-collector-plugin        │
│ Tested on real project          │     │ Richer rules                    │
├─────────────────────────────────┤     ├─────────────────────────────────┤
│ Pipeline architecture            │     │ Framework rules                 │
│ ios_detector.py                  │     │ ios_confidence_engine.py        │
│ ios_removal_executor.py          │     │ Storyboard/XIB/plist scanner    │
│ Command thin-delegate pattern    │     │ Dynamic dispatch scanner        │
│ Setup/validation flow            │     │ Skills documentation            │
└────────────────┬────────────────┘     └────────────────┬────────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │ barclays-buk-arbiter iOS      │
                     │ Hybrid implementation         │
                     ├──────────────────────────────┤
                     │ Native 0-4 confidence scale   │
                     │ Python-only implementation    │
                     │ No setup script required      │
                     │ Matches Java plugin pattern   │
                     └──────────────────────────────┘
```

v1.6 replaced the regex call graph with tree-sitter analysis, added Objective-C identification, the framework selector index, syntax-aware removal and the calibration loop.

---

## 12. How to Use It

```bash
# Prerequisites (once) — with a Python 3.10+ interpreter
pip install tree-sitter tree-sitter-swift tree-sitter-objc
# The agents run <plugin>/src/ios/resolve_env.py and use the interpreter it prints

# Navigate to your iOS project — on a clean working branch
cd ~/Projects/MyiOSApp
git checkout -b chore/arbiter-dead-code

# Build the target scheme once so DerivedData is warm

# Step 1: Discover and analyse (auto-detects iOS from project files)
/arbiter-discover .

# Or explicit with submodule targeting:
/arbiter-discover . --technology ios --module PaymentKit

# Step 2: Review confidence output
cat .arbiter/swift/CONFIDENCE.json | python3 -m json.tool | head -20

# Step 3: Create a removal plan (ObjC candidates are listed under reviewOnly)
/arbiter-plan --technology ios --sprints 1 --scope SAFE

# Step 4: Preview before removing
/arbiter-remove --technology ios next --dry-run

# Step 5: Execute with Xcode validation (all pending batches, or --batch N for the next N)
/arbiter-remove --technology ios --all --scheme MyApp

# Step 6: Check status
/arbiter-status --technology ios

# Step 7: Final verification (includes the calibration report)
/arbiter-verify --technology ios --scheme MyApp
```

Executor options: `--scheme`, `--batch N` (next N batches), `--task ID` (one batch), `--dry-run`, `--no-commit`, `--stop-on-failure`, `--destination`, `--test-destination`, `--build-timeout SECONDS`, `--max-builds-per-batch N` (bisection budget, default 12).

Scorer options: `--usage` (defaults to the `usages` in ENTITIES.json; the scorer stops if usage data is missing), `--slim` (write only removal candidates).

Record a regression found after merge so precision stays honest:

```bash
python3 <plugin>/src/ios/ios_calibration_report.py <repo> \
  --record <file> <name> --outcome regression --note "what broke"
```

---

## 13. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Objective-C removal not automated | ObjC candidates need manual review | `reviewOnly` list with every declaration site; enable once review precision is known |
| Name/selector-based resolution (no type checking) | Some dead code with common names (`initWithName:`, `load`) is kept | Errs towards keeping code by design |
| Protocol requirement + implementation keep each other alive | Dead protocol methods are not removed | Future: remove pairs together |
| Member checks are name-based | Types whose members share common names elsewhere (`viewModel`, `CodingKeys`) are kept out of SAFE (−1.5) and blocked at removal | Future: type-resolved member references |
| Files the grammar can't fully read (0.5% Swift, 2.7% ObjC on `barclays-app`) | Analysed from partial trees; never removed | Add macros to `objc_syntax.py` as found |
| Test-file naming heuristic | Production files named `*Mock`/`*Stub` are treated as test code | Rename or adjust `ios_framework_rules.py` |
| Swift properties are not entities | Unused properties aren't reported | Future |
| Static analysis can't see runtime-only use | Possible false positives (server-driven selectors, string-built names) | Dispatch detection, build/test gates, calibration ledger |
| Requires Xcode for full validation | Cannot fully validate on Linux-only CI | Analysis runs anywhere; removal needs Xcode or `swift build` |

---

## 14. Comparison: Before and After

| Metric | Java Existing | iOS New |
|---|---|---|
| Languages | Java, Kotlin | Swift, Objective-C |
| iOS source analysis | — | tree-sitter syntax trees |
| Build validation | `./gradlew build` | `xcodebuild build` (generic iOS Simulator) / `swift build` |
| Test validation | `./gradlew test` / JUnit | `xcodebuild test` / XCTest |
| Framework detection | Spring, JUnit | UIKit, SwiftUI, Combine, CoreData, React Native + SDK selector index |
| Resource scanning | Not applicable | Storyboard, XIB (incl. legacy), plist, asset-related metadata |
| Dynamic dispatch | Reflection patterns | `NSSelectorFromString`, `NSClassFromString`, KVC, selectors, runtime-built selectors |
| Batch sizes | SAFE=5, LIKELY=3, UNCERTAIN=1 | SAFE=10, LIKELY=5, UNCERTAIN=1 |
| Outcome tracking | — | `OUTCOMES.jsonl` + calibration report |
| State directory | `.arbiter/cache/` | `.arbiter/swift/` |

---

## 15. Suggested Future Enhancements

Done in v1.6:

- ~~tree-sitter-based parsing~~ (Swift and Objective-C)
- ~~More detailed protocol witness handling~~ (repo and cross-language protocol requirements)
- Framework selector index, syntax-aware removal, per-batch rollback, predicted-vs-actual calibration

Next:

- Objective-C removal (methods in `.h` + `.m`, dead `#import`s for whole classes).
- Remove protocol requirement / implementation pairs together.
- AST-based pre-removal member scan.
- Swift properties as entities.

Later:

- SourceKit / IndexStore (or Periphery) as an optional high-precision mode when a build is available.
- Incremental graph caching.
- Cross-module dependency analysis and Swift Package reachability.
- Automated MR generation, removal recommendations dashboard, CI-based validation summary reports.

---

## Questions?

- v1.6 results, spot check and pilot plan: see `docs/iOS-ANALYSIS-v1.6-OVERVIEW.md`.
- Plugin structure: see `ARCHITECTURE.md`.
- Framework rules detail: see `skills/arbiter_ios_framework_detection/SKILL.md`.
- Hidden usage patterns: see `skills/arbiter_ios_patterns/SKILL.md`.
- Validation gates: see `skills/arbiter_ios_validation/SKILL.md`.
