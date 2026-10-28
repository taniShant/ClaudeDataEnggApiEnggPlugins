# Arbiter iOS v1.6 — Syntax-Aware Dead Code Analysis for Swift & Objective-C

**Author:** Pratik Goswami  
**Audience:** iOS engineers, tech leads, and anyone running or reviewing Arbiter on an iOS codebase
**Plugin:** `barclays-buk-arbiter` v1.6.0 · **Ticket:** PLATENG-9468
**Status:** Ready for pilot on `barclays-app`. Swift analysis + removal enabled; Objective-C analysis enabled, ObjC removal **not** enabled (review-only).

---

## 1. TL;DR

- Arbiter's iOS analysis has moved from **regex and grep** to **real syntax trees** (tree-sitter) for both Swift and Objective-C.
- References in comments, strings, imports and a type's references to itself no longer count as "usage"; cross-file references are now found; methods are resolved by name (Swift) and by **full selector** (ObjC).
- A set of **framework-awareness rules** protects code that only the runtime calls: SDK overrides and delegate methods, storyboard/XIB connections (including old-format XIBs), `NSSelectorFromString(<runtime string>)` dispatch, test code, app delegates.
- Removal is now **syntax-aware**: whole declarations are removed (not just their first line), failures are traced to the entity that caused them, and rollback only affects the failing batch.
- Every removal attempt is recorded as **predicted vs. actual** so we can measure whether the confidence tiers are trustworthy (`ios_calibration_report.py`).
- On `barclays-app` (read-only run, ~3 min): **402 Swift SAFE** removal candidates and **801 ObjC SAFE** review candidates out of ~104k entities. In a random sample of 120 SAFE candidates, **none** was referenced from another file.

> These are analysis results. **Removal outcomes on `barclays-app` have not been measured yet** — that is the next step (Section 10).

---

## Update — v1.7 (after the first pilot)

**Pilot run** on `barclays-app` (main repo + 17 submodules, Swift only, SAFE tier), from the plugin's calibration report:

| | Value |
|---|---|
| SAFE precision | **97%** (target 95%) |
| Confirmed dead (removed, build green) | 172 |
| False positives | 6 — all caught by the build gate, none committed |
| Not attempted | 106 — mostly blocked by the pre-removal member scan |

**Fixed in v1.7 from the pilot feedback**

| Issue | Fix |
|---|---|
| Agent spec ran the scorer without usage data → almost everything SAFE | Scorer reads usages from ENTITIES.json by default and **stops** if usage data is missing |
| Agent could fall back to its own scripts | Agents stop if the plugin can't be resolved and never write analyzer code; all artifacts are stamped (`generatedBy`), planner/executor refuse unstamped input; `resolve_env.py` picks the interpreter |
| Commits failed in repos with submodules | Commit in the repo that owns each file, then a pointer commit; dirty check ignores untracked files and submodule pointers |
| Same-name calls treated as recursion (4 of the 6 false positives) | Recursion = same method on `self` with the same argument labels |
| Pure-Swift SDK protocols not recognised (BioCatch) | Protocol requirements indexed from `.swiftinterface` files (SDK, Pods, vendored) |
| File of a development pod deleted while `Pods.xcodeproj` listed it | `Pods/*.xcodeproj` included in the project-file check |
| SAFE types blocked by member callers | Types whose members are mentioned elsewhere score −1.5 (not SAFE) |
| SwiftLint `superfluous_disable_command` failed builds | Superfluous `swiftlint:disable` comments removed automatically |
| Unattributed failures rolled back whole batches; one failure stopped the run | Batch is halved until failing entities are isolated; the run continues with the next batch |
| Build logs discarded | Saved per build under `.arbiter/swift/logs/` |
| 135 MB CONFIDENCE.json | Compact JSON + `--slim` (1.5 MB on the same repo) |
| `--batch N` ran task N | `--batch N` = next N batches; `--task ID` = one batch |
| Members of a removed type logged as skipped | Logged as `removed (with its parent)`; manual removals can be added with `--record … --type --tier` |

Re-scoring the pilot branch with v1.7 (read-only): all five Swift false positives are now KEEP, and 106 of the 112 SAFE candidates that weren't removed now score LIKELY/UNCERTAIN because their members are mentioned elsewhere — i.e. they are no longer ranked SAFE only to be blocked.

---

## 2. Why We Changed It

A previous removal campaign on the Barclays app recorded **17 entities removed (6.2%) and 274 blocked (93.8%)**. Investigating the pipeline showed the causes were structural, not tuning:

| Problem in the previous pipeline | Effect |
|---|---|
| Usage was a raw substring count (`content.count(name)`) | `UnusedClass` mentioned in a comment, a string and its own extension counted as 3 "uses" — never flagged |
| Types only matched against names declared **in the same file** | Cross-file references were never detected by the "AST" scanner |
| Regex declaration matching | Missed `@objc public final class`, `@MainActor final class`, `indirect enum`, `nonisolated public func`, `override public func`, multi-line signatures; matched code inside `/* … */` |
| Method names ≤ 5 characters skipped in usage counting | Every short method (`load`, `get`, `reset`) looked unused |
| Removal commented out **only the first line** of a method/type | `// ARBITER REMOVED: func foo() {` left the body behind → build failure → rollback, for almost every multi-line method |
| Rollback restored the whole tree to the run's start | Batches that had already passed in the same run were silently reverted |
| Type files deleted without updating the Xcode project | Build failed with "input file not found" |
| v2 scorer: one reference = −0.5 from 4.0 | A referenced type still scored 3.5 = **SAFE** |
| v2 scorer read storyboard/dispatch data in the wrong format | Storyboard and `NSClassFromString` protections never applied |
| Objective-C | Regex only; every ObjC entity penalised as "ObjC-exposed", so ObjC could never reach SAFE; ObjC removal broke builds |

Earlier design notes described a `swiftc`-based AST; that was never implemented — the scanner was still regex. **This document and the [technical walkthrough](iOS-TECHNICAL-WALKTHROUGH.md) describe the current implementation.**

---

## 3. What Changed — At a Glance

| Area | Before | v1.6 |
|---|---|---|
| Swift parsing | Regex | tree-sitter (`tree-sitter-swift`) |
| ObjC parsing | Regex (`.m/.mm` only) | tree-sitter (`tree-sitter-objc`), `.h/.m/.mm`, macro-aware |
| Type usage | Substring count | Syntax-tree references: inheritance, conformance, type annotations, generics, constructor calls; comments/strings/self-references/extensions excluded |
| Method usage | Substring count, ≥ 6 chars | Swift call sites by name; ObjC by full selector (`countFor:inSection:`), `@selector`, dot-syntax; Swift↔ObjC bridged names |
| Framework-called code | Partial rule tables | + SDK/Pods/vendored-framework selector index, override detection, runtime-dispatch detection, legacy XIB scanning |
| Removal | First line commented out | Whole declaration range (incl. attributes and doc comments), re-located in the current file |
| Failure handling | Roll back everything | Attribute compiler errors → retry without culprits → roll back only the failing batch |
| Feedback | None | Outcome ledger + calibration report (predicted vs actual) |

---

## 4. How the Analysis Works

```
                 ┌──────────────────────────┐
 .swift ────────▶│ tree-sitter-swift        │──┐
                 └──────────────────────────┘  │   ┌───────────────────────┐
 .h .m .mm ─────▶│ macro blanking →          │──┼──▶│ Reference graph       │
                 │ tree-sitter-objc          │  │   │  types · selectors ·  │
                 └──────────────────────────┘  │   │  Swift↔ObjC names     │
 SDK + Pods + ──▶│ framework selector index │──┘   └──────────┬────────────┘
 .framework hdrs └──────────────────────────┘                   │
 .storyboard .xib .plist ─▶ resource scanner ───┐               ▼
 source ─────────────────▶ dispatch scanner ────┼──▶ Confidence scoring (0–4) ─▶ SAFE / LIKELY / UNCERTAIN / KEEP
                                                 └──▶ (storyboard classes & actions, NSClassFromString, KVC)
```

### 4.1 Swift
- **Declarations:** classes, structs, enums, actors, protocols and methods, with full line ranges (`startLine`/`endLine`, including attributes and doc comments directly above) and whether the declaration shares a line with other code (`ownsLines`).
- **Type references:** every `type_identifier` / identifier node resolved against all declared types in the repo. Classified as `inheritance`, `protocol_conformance`, `type_annotation`, `generic_argument`, `constructor_call`, `identifier`, `extension_type`. Extending a type is **not** evidence that it is used.
- **Method references:** call sites by name (`foo()`, `x.foo()`, `#selector(foo)`, function references). Declarations, parameter names, argument labels and calls from inside the method itself (recursion) don't count. Overloads share a count — this errs on the side of keeping code.
- **Protocol witnesses:** a method that implements a protocol requirement declared in the repo counts as used.

### 4.2 Objective-C
- **Macro blanking:** `NS_ASSUME_NONNULL_BEGIN/END`, `NS_SWIFT_NAME(...)`, `API_AVAILABLE(...)`, `NS_DESIGNATED_INITIALIZER`, `NS_ENUM(...)`, and project-prefixed attribute macros (`BWK_EXTERN`, `*_EXTENSIBLE_STRING_ENUM`, `*_ONLY_AVAILABLE_IN_TEST`, …) are replaced with same-length whitespace so line numbers stay exact.
- **Declarations:** classes are merged across `@interface` (header), class extension and `@implementation`; categories on framework classes contribute methods but not a class entity. Methods are identified as `-[Class selector:with:]` / `+[Class selector]`, with every declaration site (`.h` declaration, `.m` definition).
- **Usage:**
  - message sends by **full selector** (`[x countFor:a inSection:b]` → `countFor:inSection:`), `@selector(...)`, dot-syntax property access (getter and setter);
  - class references as receivers, types, superclasses, protocol lists — but **not** `@class` forward declarations, `#import`s, or a class's references to itself;
  - **Swift → ObjC:** Swift call sites under the imported name (`loadWithItem:completion:` → `load(withItem:)`, `NS_SWIFT_NAME(count(for:section:))` → `count`); `init…` methods count Swift constructor calls of their class;
  - **ObjC → Swift:** whole-word mentions of Swift names in ObjC files (including `fooWithBar` selector forms).
- **Cross-language protocols:** ObjC protocol requirements implemented in Swift, and Swift `@objc` protocol requirements implemented in ObjC, keep each other alive.

### 4.3 Framework-awareness rules (always KEEP unless noted)

| Rule | Why | Example |
|---|---|---|
| **Framework selector index** — ObjC method whose selector is declared by the iOS SDK, `Pods/`, `Carthage/` or a vendored `.framework` | The framework calls it (override or delegate method) | `viewDidLoad`, `tableView:numberOfRowsInSection:`, a Pod's delegate callback |
| **Swift override of a non-repo method** | Overrides an SDK/Pod method | `override func preferredLayoutAttributesFitting(_:)` |
| **Swift non-private method named like an SDK selector** | Likely a framework protocol method | `func tableView(_:numberOfRowsInSection:)` |
| **Runtime-built selectors** — a method calls `NSSelectorFromString(x)` / `NSClassFromString(x)` / `Selector(x)` with a non-literal argument | Any method of the classes it names may be called | `NSSelectorFromString(className)` sent to `BMBViewControllerTrackingHelper` |
| **Storyboard/XIB** — `customClass`, action selectors, and old-format XIBs (`<string>MyViewController</string>`, `<string key="label">didTap:</string>`) | Instantiated / connected by Interface Builder | Classes −2.5; connected actions −2.5 (with `@IBAction` −2.0 → KEEP) |
| **Test code** — `Tests/`, `Mocks/`, `Stubs/` paths; `*Tests`, `*Spec`, `*Mock(s)`, `*Stub(s)`, `*Fake(s)` file names; `XCTestCase`/`QuickSpec` subclasses | Run by the test runner | `FinanceCoach/Source/BMBFCInsightCTATests.swift` |
| **App/scene delegate** — conforms to or inherits `UIApplicationDelegate` / `UIWindowSceneDelegate` | Entry point | `@interface AppDelegate : UIResponder <UIApplicationDelegate>` |
| Existing rules (unchanged) | | `@main`, `@objc`, `@IBAction`, UIKit/SwiftUI/Combine/CoreData/React Native tables, `NSClassFromString`/`performSelector`/KVC from the dispatch scanner |

Vendored binary SDKs (`*.framework/`, `*.xcframework/`) are **not** analysed as repo code; their headers feed the selector index.

### 4.4 Confidence tiers (unchanged scale)

| Tier | Score | Removal plan |
|---|---|---|
| SAFE | 3.0–4.0 | Batches of 10, compile gate |
| LIKELY | 2.0–2.9 | Compile + unit tests |
| UNCERTAIN | 1.0–1.9 | Full test suite |
| KEEP | < 1.0 or any always-keep rule | Never planned |

Any entity with at least one reference is KEEP.

---

## 5. How Removal Works (Swift)

1. **Pre-checks** — working tree must be clean; project must build (`-destination 'generic/platform=iOS Simulator'`, no code signing). A backup branch is created.
2. **Re-locate** — each entity is found again with tree-sitter in the file's *current* state (plan line numbers can be stale after earlier batches).
3. **Remove the whole declaration** — attributes and doc comments included. Skipped (not half-removed) when:
   - the declaration shares a line with other code;
   - the file has syntax the parser can't fully read;
   - a type's members have callers elsewhere (pre-removal member scan across `.swift/.m/.mm/.h`).
4. **Files** — a file left with only imports is deleted, unless a `project.pbxproj` references it; then it is left empty and reported ("remove X.swift from the Xcode project").
5. **Validate** — SAFE: build. LIKELY/UNCERTAIN: build + tests (first available iPhone simulator).
6. **On failure** — compiler errors naming removed entities (`cannot find 'X' in scope`, `has no member 'X'`, …) mark those entities `build_failed`; the rest of the batch is re-applied and validated once more. If it still fails, **only the files this batch touched** are restored.
7. **Commit** each passing batch with a message listing removed and not-removed entities.

Objective-C entities are **never** removed in v1.6 — the planner lists them under `reviewOnly` with every declaration site.

---

## 6. Feedback Loop: Predicted vs. Actual

Every attempted removal appends a line to `.arbiter/swift/OUTCOMES.jsonl`:

```json
{"predictedCategory": "SAFE", "confidenceScore": 3.5, "scoringReasons": [...],
 "name": "fetch", "type": "method", "file": "Sources/Demo/Service.swift",
 "outcome": "build_failed", "attributed": true,
 "detail": "main.swift:2:11: error: value of type 'Service' has no member 'fetch'"}
```

Outcomes: `removed`, `build_failed`, `tests_failed`, `rolled_back` (unattributed), `blocked`, `skipped`, and `regression` (recorded later).

`ios_calibration_report.py` (run by `/arbiter-verify`) turns the ledger into:

- **precision per tier** = confirmed dead / (confirmed + false positives), against targets **SAFE ≥ 95%, LIKELY ≥ 80%, UNCERTAIN ≥ 50%**; tiers below target are flagged "re-tune";
- **what the analysis missed** — false positives grouped by cause (referenced from ObjC, member access, protocol witness, Interface Builder, runtime-only use…), pointing at which rule to improve;
- the false-positive list with each entity's scoring reasons and the error that exposed it.

A successful build only proves the code *compiled*. When QA finds a regression or a removal is reverted after merge, record it so precision reflects reality:

```bash
python3 <plugin>/src/ios/ios_calibration_report.py <repo> \
  --record <file> <name> --outcome regression --note "what broke"
```

---

## 7. Results So Far

### 7.1 Controlled fixtures
- Swift package, end-to-end with real `swift build`: 7 dead entities removed, build green, commit created. A deliberately injected false positive was attributed from the compiler error, excluded, and the batch retried successfully. A simulated failure in a second batch restored only that batch; the first batch's commit was untouched.
- Swift declaration fixture: regex found 10 entities (2 phantom, from a block comment) and missed 11; tree-sitter found all 19 with no phantoms.
- ObjC fixture: dead classes, methods, recursion, category methods flagged; Swift-called (`NS_SWIFT_NAME`, `load(withItem:)`), framework-called, delegate, storyboard and runtime-dispatch methods kept.

### 7.2 `barclays-app` — read-only analysis (no repo changes)

| Metric | Value |
|---|---|
| Swift files / ObjC files (`.m/.mm` + `.h`) | 11,223 / 1,314 + 1,453 |
| Files the parser couldn't fully read | Swift 56 (0.5%), ObjC 76 (2.7%) — analysed from partial trees, skipped for removal |
| Entities analysed | 104,149 (Swift 85,497 · ObjC 18,652) |
| References resolved | ~200k type references |
| Run time / peak memory | ~3 min / ~2.2 GB |

| | SAFE | LIKELY | UNCERTAIN | KEEP |
|---|---|---|---|---|
| Swift (removal candidates) | **402** | 100 | 53 | 84,942 |
| Objective-C (review only) | **801** | 38 | 27 | 17,786 |

Main KEEP reasons: used in call graph 55,198 · test code 37,194 · SDK/Pods-named Swift methods 5,837 · ObjC framework selectors 3,089 · storyboard/XIB actions 865 · framework overrides 160 · runtime-dispatch classes 15 (e.g. `BMBViewControllerTrackingHelper`, `BMBLoginTrackingHelper`).

The removal plan contains **61 Swift batches** (SAFE + LIKELY).

### 7.3 Independent spot check
Method: random sample of 60 Swift + 60 ObjC SAFE candidates; for each, search every source/storyboard/XIB/plist file **other than its own declaration files** for the name.

| Iteration | Swift flagged | ObjC flagged | Fixes it drove |
|---|---|---|---|
| 1 | 14 / 40 | 12 / 40 | Test-file naming, framework overrides, storyboard scanning, vendored frameworks, runtime-dispatch |
| 2 | 1 / 60 | 14 / 60 | Legacy XIBs, app-delegate conformance, cross-language protocol witnesses |
| **Final** | **2 / 60** | **8 / 60** | — |

Every remaining hit in the final sample was a **same-named declaration in another class**, a **different selector** (e.g. `showTour:onViewController:` vs `showTour:`), a **string literal**, or an **`#import`** — i.e. none was an actual reference. This is strong evidence, not proof: uses that exist only at runtime can't be found by any static check, which is what the calibration ledger is for.

---

## 8. How to Use It

### Prerequisites
- Xcode 14+, Swift 5.5+, Python 3.10+
- `pip install tree-sitter tree-sitter-swift tree-sitter-objc` (agents stop and ask if missing; without them analysis falls back to regex and removal is disabled)
- A **clean working branch** (removal commits each batch and refuses a dirty tree)
- Build the target scheme once beforehand so DerivedData is warm

### Install (local marketplace)
```bash
claude plugin marketplace update barclays-cio-buk-local
claude plugin update barclays-buk-arbiter@barclays-cio-buk-local   # restart Claude Code afterwards
```

### Run
```text
/barclays-buk-arbiter:arbiter-discover . --technology ios                 # analyse
/barclays-buk-arbiter:arbiter-plan --technology ios --scope SAFE          # batch Swift; list ObjC for review
/barclays-buk-arbiter:arbiter-remove --technology ios next --dry-run      # preview
/barclays-buk-arbiter:arbiter-remove --technology ios --batch 2           # real removal, 2 batches
/barclays-buk-arbiter:arbiter-verify --technology ios --scheme <Scheme>   # final check + calibration report
```

Executor options (via the remove agent or directly): `--scheme`, `--batch N`, `--dry-run`, `--no-commit`, `--destination`, `--test-destination`, `--build-timeout SECONDS` (default 3600).

### Outputs (`.arbiter/swift/`)
| File | Content |
|---|---|
| `ENTITIES.json` | Entities with line ranges, declarations, usage counts |
| `RESOURCE_REFS.json` / `DISPATCH_SCAN.json` | Storyboard/XIB/plist and dynamic-dispatch findings |
| `CONFIDENCE.json` | Scored entities and reasons |
| `PLAN.json` | Swift batches + `reviewOnly` ObjC candidates |
| `REMOVAL_LOG.json` | Per-batch, per-entity results |
| `OUTCOMES.jsonl` | Predicted vs actual ledger (append-only) |

The SDK selector index is cached in `~/.cache/arbiter/` (delete after an Xcode upgrade).

---

## 9. Known Limitations

| Limitation | Impact | Mitigation / plan |
|---|---|---|
| ObjC removal not automated | ObjC candidates need manual review | Enable after review confirms identification precision (needs `.h` + `.m` + `#import` removal) |
| Selector/name matching is name-based, not type-resolved | Some dead code with common names (e.g. `initWithName:`, `load`) is kept | Accepted trade-off: errs towards keeping code |
| Protocol requirement + implementation pairs keep each other alive | Dead protocol methods are never removed | Future: remove pairs together |
| Member checks are name-based | Types whose members share common names elsewhere (`viewModel`, `CodingKeys`) are kept out of SAFE (−1.5) and blocked at removal | Future: type-resolved member references |
| 0.5% Swift / 2.7% ObjC files not fully parseable | Analysed from partial trees; never removed | Add macros as found |
| Test-name heuristic | Production files named `*Mock`/`*Stub` are treated as test code (never flagged) | Rename or exclude if needed |
| Static analysis can't see runtime-only use (string-built class names, server-driven selectors) | Possible false positives | Dispatch scanner + calibration ledger + `--record regression` |
| Swift properties are not entities | Unused properties aren't reported | Future |

---

## 10. Pilot Plan & How You Can Help

1. **Run analysis** on `barclays-app` and review the Swift SAFE list and a sample of the ObjC `reviewOnly` list with feature owners.
2. **Remove 2–3 Swift SAFE batches** on a branch; run the calibration report.
3. **Report anything wrong** — a SAFE candidate you know is used, a framework pattern we don't recognise, a macro that breaks parsing. Each one becomes a rule (that is how the protections in §4.3 were found).
4. **Record post-merge regressions** with `--record` so the SAFE tier's precision stays honest.
5. Decide on **ObjC removal** once ObjC review precision is known.

Success criteria for the pilot: SAFE precision ≥ 95% on the calibration report, with no post-merge regressions.

---

## 11. FAQ

**Is this Periphery?** No. Periphery uses the compiler's index store and is more precise but needs a full build. Arbiter works from source without building, and is designed to combine with build-validated, batched removal. Periphery integration remains an option for a future high-precision mode.

**Will it delete code that's only used in tests?** It treats a test reference as a reference, so production code called from tests is KEEP. Test code itself is never removed.

**What if a removal breaks something the build doesn't catch?** LIKELY/UNCERTAIN batches also run tests. For anything found later, revert the batch commit (each batch is its own commit) and record it with `--record … --outcome regression`.

**Does it need the network?** No. Everything runs locally; the SDK index is built from your installed Xcode.

**Why are ObjC methods with common selectors kept?** If the SDK or a Pod declares the same selector, the method may be an override or delegate callback. Keeping it is the safe choice.

---

## 12. Change Summary (v1.2 → v1.6)

| File | Change |
|---|---|
| `src/ios/ast_reference_scanner.py` | tree-sitter Swift scanner; ObjC integration; Swift↔ObjC names; runtime-dispatch detection; framework index wiring |
| `src/ios/objc_syntax.py` | **New** — ObjC parsing, macro blanking, selectors, references, SDK/Pods/framework selector index |
| `src/ios/ios_call_graph_analyzer.py` | tree-sitter Swift entities with line ranges; usage merge for Swift/ObjC; framework/override/dynamic flags |
| `src/ios/ios_confidence_engine.py`, `_v2.py` | Framework-selector, runtime-dispatch and app-delegate KEEP rules; storyboard action protection; v2 loader fixes; v2 "used ⇒ KEEP" |
| `src/ios/ios_resource_scanner.py` | Legacy XIB class/action detection (`--entities`) |
| `src/ios/ios_removal_executor.py` | Rewritten: syntax-aware removal, attribution + retry, per-batch rollback, commits, outcome ledger, simulator destinations |
| `src/ios/ios_calibration_report.py` | **New** — predicted vs actual report; `--record` feedback |
| `src/ios/ios_planner.py` | ObjC `reviewOnly`; reasons passed through |
| `src/ios/ios_framework_rules.py` | Shared test-code detection |
| `src/ios/ios_analyze_improved.py` | Runs resource + dispatch scans; reuses the AST graph |
| `agents/*-ios-agent.md`, `README.md` | Script locator for installed plugin, dependencies, new behaviour |
