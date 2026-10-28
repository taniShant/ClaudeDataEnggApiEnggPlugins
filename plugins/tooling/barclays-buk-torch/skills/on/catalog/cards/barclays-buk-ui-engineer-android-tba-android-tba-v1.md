# barclays-buk-ui-engineer-android-tba-android-tba-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-android-tba-android-tba-v1` |
| Plugin name | `barclays-buk-ui-engineer-android-tba` |
| Component type | skill-model-invocable |
| Owner | Barclays BUK |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-ui-engineer-android-tba@barclays-cio-buk |
| Native command | `/barclays-buk-ui-engineer-android-tba:android-tba` |
| Skill name | `android-tba` |

## Description

Generate TBA (The Barclays App) Android screens and journey steps using Jetpack Compose and Blueprint Compose, including TBA-specific patterns: Journey Framework, MVC action layer, Scope-based DI hierarchy, FlavorDetails branching, BarclaysActivity hosting, and TbaIconMapper

## When to use

Use when building new screens or journey steps in The Barclays App (TBA) Android project (BMB monorepo); requires TBA-specific patterns such as Journey Framework, MVC action layer, Scope-based DI hierarchy, FlavorDetails branching, BarclaysActivity hosting, or TbaIconMapper. NOT for generic Android or Jetpack Compose development outside the TBA/BMB monorepo.

## Inputs

- Screen or journey step specification (required) — description of the screen or multi-step flow to generate, including its role in the user journey
- Figma URL or design spec (optional) — link or node ID pointing to the Figma design; if absent the skill falls back to description-based generation
- Feature name (required) — used to derive class and file naming (`{Feature}Module`, `{Feature}Activity`, etc.)
- Analytics page tag (optional) — identifier for `DynamicViewAnalytics`; generated from feature name if not supplied
- Flavor variant (optional) — `barclays`, `barclaycard`, or `staffPilot`; drives `FlavorDetails` branching if behaviour diverges

## Preconditions

- `barclays-buk-ui-engineer-android-tba` plugin installed
- TBA Android project context in session — the BMB monorepo (`barclaysMobileBanking/`) must be the working project
- `com.barclays.mobile.blueprint.compose:ui` (`barclays.designLanguage`) must be present as a Gradle dependency
- `barclays-buk-ui-engineer-android` plugin installed (base `android` skill is a declared dependency)
- `barclays-buk-standards` plugin installed (accessibility and security checks are declared dependencies)

## Expected outputs

- `{Feature}Screen.kt` — Jetpack Compose screen composable using `BlueprintScaffold`, `BlueprintLargeNavBar`, hoisted state data class, and `BlueprintSecureField` for sensitive inputs; no hardcoded colours or typography
- `{Feature}NavGraph.kt` — NavGraph composable wiring the screen into the feature navigation
- `{Feature}ViewModel.kt` and `{Feature}ViewModelFactory.kt` — state holder and factory; scope dependencies resolved in factory, never in composables
- Journey Framework wiring (when the screen is a journey step):
  - `{Feature}Module.kt` — `BaseRegistrationModule` with `analyticsPageTag`, payload attachment, and `getAction(ActionType.NEXT)`
  - `{Feature}ModuleData.kt` — parses JSON from `JourneyFrameworkApiContent`
  - `{Feature}Populator.kt` — `JourneyFrameworkModulePopulator` implementation
  - `{Feature}Presenter.kt` — `ModuleHelper` implementation with MVC action execution via `JourneyFrameworkGenericHandleAction.Builder`
  - `{Feature}Activity.kt` — `BarclaysActivity` host with `BlueprintTheme`, `edgeToEdge = true`, analytics in `onResume`
- Unit tests for presenter (Journey Framework action routing) and ViewModel; Robolectric-based Compose UI tests where `getAppCompatActivity()` stubs are required
- `FlavorDetails`-branched logic in ViewModel/Presenter when flavor-specific behaviour is requested; source-set overrides (`src/barclaycard/`, `src/barclaysmobilebanking/`) for deeper divergence

## Exclusions

- Does not generate screen barrel exports or Navigation graph registration — caller is responsible for wiring into the app-level NavHost
- Does not run Kotlin compilation or Lint checks — caller drives the build gate
- Does not implement `JourneyFrameworkModuleLauncher` registration for the new feature — that entry is added to the shared launcher by the team responsible for it
- Does not generate generic Android screens outside the BMB monorepo; for non-TBA Jetpack Compose work use `barclays-buk-ui-engineer-android:android-ui-engineer` directly
- Does not make network calls or access Figma without `barclays-buk-ui-engineer:figma` skill loaded; falls back to description-based generation and flags the gap

## Verification

Confirm each generated `.kt` file compiles without errors in the BMB Gradle build. For Journey Framework outputs: verify `{Feature}Module` extends `BaseRegistrationModule`, all action lookups use `ActionType` constants (no hardcoded strings), and `JourneyFrameworkGenericHandleAction.Builder` is constructed from the Activity reference. For Compose screens: confirm `BlueprintScaffold` is the root composable, `BlueprintLargeNavBar` is in the `top` slot, no `Scope.get(...)` calls appear inside `@Composable` functions, and no `BuildConfig.FLAVOR` checks appear in feature code. For icon rendering: confirm `mapIcon()` calls include a `rememberVectorPainter(BlueprintVectors.Outlined.Placeholder)` fallback. Run unit tests for the presenter and ViewModel; check Robolectric Compose tests pass for screens using `getAppCompatActivity()`.
