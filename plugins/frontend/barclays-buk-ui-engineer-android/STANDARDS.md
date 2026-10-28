# barclays-buk-ui-engineer-android — Standards

> Extends `barclays-buk-ui-engineer/STANDARDS.md`. This document covers only what is specific to the Android (Jetpack Compose + Blueprint Compose) platform. Read the shared STANDARDS.md first.

---

## Mission

Create high-quality, beautiful Jetpack Compose screens for customer journeys on the Android mobile channel — using Figma designs, an API contract, and user stories as inputs. Produces fully typed `com.barclays.compose.blueprint` composables and MVVM ViewModels, placed in the correct bmb-android module tier, accessible, secure, and ready to wire up.

---

## Platform Scope

| Channel | Supported |
|---|---|
| Mobile (native Android) | Yes |
| Online Banking (web/SDF) | No — use `barclays-buk-ui-engineer-sdf` or `barclays-buk-ui-engineer-web` |

---

## Inputs

All shared inputs apply (see `barclays-buk-ui-engineer/STANDARDS.md`). Android-specific additions:

| Input | Source | Required |
|---|---|---|
| `SCREENS[].nodeId` | Figma frame node ID | No — fallback heuristics if absent |
| `FIGMA_TOKEN` | Figma personal access token | No — MCP-only mode if absent |

---

## Outputs

| Artifact | Path | Description |
|---|---|---|
| Screen composable | `{PROJECT_PATH}/src/main/java/{package}/screens/{COMPONENT_NAME}/{COMPONENT_NAME}.kt` | Jetpack Compose screen function |
| ViewModel | `{PROJECT_PATH}/src/main/java/{package}/screens/{COMPONENT_NAME}/{COMPONENT_NAME}ViewModel.kt` | `ViewModel` subclass with `StateFlow<UiState>` — state derived from OAS schema |
| UiState data class | Defined in the ViewModel file | Sealed or data class representing all screen state |
| Completion report | `{PROJECT_PATH}/UI_ENGINEER_ANDROID_COMPLETE.md` | Summary of screens generated, flags, suggested next steps |
| Execution log | `{PROJECT_PATH}/logs/ui-engineer-android.log` | Timestamped log of all agent actions |

Module tier placement follows `barclays-buk-ui-engineer-android:tba` Section 1 — see that skill for the `appwide`/`highlevel`/`lowlevel`/`internal` decision rules.

---

## Standards Enforced

All shared standards apply (accessibility WCAG 2.2 AA, security, design tokens, Figma extraction). Android-specific Iron Rules:

### Iron Rules — Jetpack Compose + Blueprint Compose

| Rule | Check | Severity if violated |
|---|---|---|
| Screen composable is annotated `@Composable` | Every generated `.kt` screen file contains `@Composable` | Critical |
| `Modifier` chain built fresh, incoming `modifier` param appended last with `.then(modifier)` | No `.then(modifier)` appearing before other modifiers in the chain | High — wrong order applies caller modifiers in wrong sequence |
| No `CoroutineScope` passed as a composable parameter | `grep -rn "CoroutineScope" src/main/java/*/screens/` on composable params returns empty | High — scopes must be created with `rememberCoroutineScope()` inside the composable |
| `clearAndSetSemantics` banned | `grep -rn "clearAndSetSemantics" src/main/java/*/screens/` returns empty | Critical — strips all accessibility behaviour including skip/previous navigation |
| `requestFocus()` never inside `semantics {}` block | No `requestFocus` nested within `semantics { }` | High — causes focus to fire on every recomposition |
| Navigator interface never extends `ViewModel` | Navigator is a plain interface, injected | High — ViewModel lifecycle and navigation lifecycle are separate concerns |
| `remember(key) { }` used for expensive operations | Expensive computations wrapped in `remember` with appropriate key | High — missing key causes recomputation on every recomposition |
| Lazy list items always have a `key` parameter | `LazyColumn`/`LazyRow` item lambdas include `key = { }` | High — missing keys cause incorrect animations and unnecessary recompositions |
| Zero hardcoded colour values | No hex literals, no `Color(0xFF...)` outside of token definitions | High |
| Blueprint Compose components used — no raw Material/Compose equivalents for UI chrome | Screens import from `com.barclays.compose.blueprint` | High |
| ALFRED detekt threshold not exceeded | `./gradlew detekt` exits 0 | High — ALFRED is the CI gate |
| Version catalog references use named catalogs | No `libs.*` — use `blueprint.*`, `core.*`, `barclays.*`, etc. per `settings.gradle` | High |

### ViewModel rules

| Rule | Check | Severity if violated |
|---|---|---|
| ViewModel extends `ViewModel()` | Class declaration correct | High |
| UiState exposed as `StateFlow` | `val uiState: StateFlow<{Name}UiState>` present | High |
| UiState is a sealed class or data class — no raw primitives exposed | Type-safe state | High |
| Use-case interfaces injected via constructor — not instantiated inside ViewModel | Constructor parameters are interfaces | High — enables testing |
| ViewModel fields: max 6 for data-derived ViewModel state | State class has ≤ 6 fields (pure UI state — `isCollapsed`, `isVisible` — may live closer to UI) | Medium |

---

## Tools and Tech

| Property | Value | Why |
|---|---|---|
| Language | Kotlin | bmb-android is a Kotlin project |
| Framework | Jetpack Compose | Current Android UI framework at Barclays |
| Component library | `com.barclays.compose.blueprint` | Blueprint Compose — never raw Material3 components for UI chrome |
| State | `ViewModel` + `StateFlow` | MVVM pattern used throughout TBA |
| Lint | ALFRED (detekt) | CI gate — all generated code must pass |
| Build check | `./gradlew assembleDebug` or `./gradlew detekt` | Must compile and pass detekt |

### Version catalogs (bmb-android)

Generated `build.gradle` dependency references must use the named catalogs from `settings.gradle`. Never use `libs.*`.

| Catalog | Use for |
|---|---|
| `blueprint.*` | Blueprint Compose components |
| `core.*` | Core Android dependencies |
| `barclays.*` | Barclays-internal libraries |
| `lifecycle.*` | ViewModel, LiveData, Compose lifecycle |
| `tests.*` | Test dependencies |
| `support.*` | AndroidX support libraries |
| `observability.*` | Logging and tracing |

### Skills loaded (Android additions)

| Skill | Source | Purpose |
|---|---|---|
| `barclays-buk-ui-engineer-android:android` | This plugin | ALFRED detekt thresholds, Blueprint Compose rules, Kotlin rules |
| `barclays-buk-ui-engineer-android:tba` | This plugin | bmb-android module structure, shared utilities (safeLet, asyncAll, etc.), MVVM/navigation/feature-flag patterns |

---

## Quality Gates (in execution order)

| Gate | Check | Threshold |
|---|---|---|
| Kotlin compile | `./gradlew assembleDebug` | Exit 0 |
| Detekt | `./gradlew detekt` (ALFRED rules) | Exit 0 — 0 new violations |
| Iron Rule validation | Grep checks above | 0 Critical violations |
| Accessibility | `barclays-buk-standards:accessibility` Android-Compose rules applied | 0 Critical violations |

---

## Handoff Criteria

All shared handoff criteria apply. Android-specific additions:

| Gate | Why |
|---|---|
| Agent tested against a real bmb-android module — correct tier placement verified | Module structure is complex; wrong tier placement causes dependency resolution failures |
| `./gradlew assembleDebug` passes on first attempt for all generated files | Kotlin compile errors in generated output are a blocker |
| `./gradlew detekt` passes with zero new violations | ALFRED is the CI gate — violations block merge |
| ViewModel `StateFlow` state fields match OAS response schema on a real spec | Core of Option B — ViewModel generation validated against a real contract |
| Named version catalogs verified — no `libs.*` references in generated files | Wrong catalog names fail at Gradle sync |
| `clearAndSetSemantics` confirmed absent from all generated output | Critical accessibility violation — must be verified explicitly |

---

## Definition of Done

All shared DoD items apply. Android-specific additions:

- [ ] Every screen composable has a corresponding `{ComponentName}ViewModel.kt` and `{ComponentName}UiState` alongside it
- [ ] ViewModel state is exposed as `StateFlow` — no `LiveData` or `MutableState` in the ViewModel layer
- [ ] Use-case interfaces are injected into ViewModel constructor — no direct instantiation
- [ ] `./gradlew assembleDebug` exits 0 on first attempt
- [ ] `./gradlew detekt` exits 0 — zero new ALFRED violations
- [ ] No `clearAndSetSemantics` in any generated file
- [ ] All lazy list items have a `key` parameter
- [ ] `remember(key)` used for all expensive operations
- [ ] Version catalog references use named catalogs from `settings.gradle` — zero `libs.*`
