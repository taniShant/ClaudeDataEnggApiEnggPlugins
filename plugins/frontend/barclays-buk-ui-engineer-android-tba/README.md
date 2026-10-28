# barclays-buk-ui-engineer-android-tba

> **Status: Available**

Extends `barclays-buk-ui-engineer-android` with TBA (The Barclays App)-specific patterns. Use this plugin when generating screens or journey steps inside the BMB monorepo.

## When to use this vs the base plugin

| Scenario | Plugin to use |
|---|---|
| New screen inside BMB monorepo | `barclays-buk-ui-engineer-android-tba` |
| New multi-step journey step (registration, onboarding, auth) | `barclays-buk-ui-engineer-android-tba` |
| Server-driven journey step (next step returned by API) | `barclays-buk-ui-engineer-android-tba` |
| Generic Barclays Android app outside BMB | `barclays-buk-ui-engineer-android` |
| Library or SDK with no TBA framework dependency | `barclays-buk-ui-engineer-android` |

## What this plugin adds on top of the base

| Layer | What gets generated |
|---|---|
| **Journey module** | `{Feature}Module.kt`, `{Feature}Populator.kt` — `BaseRegistrationModule` + `JourneyFrameworkModulePopulator` |
| **Module helper** | `{Feature}Presenter.kt` — `JourneyFrameworkModuleContract.ModuleHelper` |
| **Activity host** | `{Feature}Activity.kt` — extends `BarclaysActivity`, uses `setContent {}` with `BlueprintTheme` |
| **MVC action handling** | `JourneyFrameworkGenericHandleAction` wiring in the presenter |
| **Scope registration** | `{Team}Scope` access patterns; `NavigationScope` for cross-team routing |
| **Flavor branching** | `FlavorDetails` checks where screen behaviour differs per product flavor |
| **Icon mapping** | `mapIcon()` usage via `TbaIconMapper` |
| **ComposeActivityContext** | `LocalContext.current.getAppCompatActivity()` where an Activity reference is needed |
| **Analytics** | `analyticsPageTag` wired via `DynamicViewAnalytics` |

The base `android` skill is loaded first; this skill adds TBA layers on top. No generic patterns are duplicated.

---

## Usage

The recommended entry point is `ui-engineer-agent` — it auto-detects BMB TBA projects via `barclays.behaviourSdk` in `build.gradle` and routes here automatically.

**Via the dispatcher (recommended):**

Invoke `ui-engineer-agent` with:
```
PROJECT_PATH:     /path/to/bmb/cardshubteam/lowlevel/carddetails
JIRA_ID:          PLATENG-1234
FIGMA_URL:        https://www.figma.com/design/...
PLATFORM_OPTIONS: {"package": "com.barclays.mobilebanking.carddetails", "teamScope": "CardshubScope"}
```

The dispatcher will grep `build.gradle` for `barclays.behaviourSdk`, confirm this is a TBA project, and delegate here.

**Invoke the orchestrator directly:**

Invoke `ui-engineer-android-tba-worker-agent` with:
```
PROJECT_PATH:     /path/to/bmb/cardshubteam/lowlevel/carddetails
JIRA_ID:          PLATENG-1234
FIGMA_URL:        https://www.figma.com/design/...
PLATFORM_OPTIONS: {
  "package":        "com.barclays.mobilebanking.carddetails",
  "teamScope":      "CardshubScope",
  "isJourneyStep":  false,
  "controllerId":   "none",
  "analyticsTag":   "none",
  "flavorVariants": []
}
```

**For a journey step, add the journey options:**
```
PLATFORM_OPTIONS: {
  "package":        "com.barclays.mobilebanking.auth.personaldetails",
  "teamScope":      "AuthLoginScope",
  "isJourneyStep":  true,
  "controllerId":   "AuthenticationController.CONTROLLER_ID",
  "analyticsTag":   "personal_details_capture"
}
```

**PLATFORM_OPTIONS reference:**

| Key | Required | Default | Description |
|---|---|---|---|
| `package` | Yes | — | Kotlin package, e.g. `com.barclays.mobilebanking.carddetails` |
| `teamScope` | Yes | — | Team scope class, e.g. `CardshubScope` |
| `isJourneyStep` | No | `false` | Generate Journey Framework slice |
| `controllerId` | No | `"none"` | MVC controller ID constant — required if `isJourneyStep` is `true` |
| `analyticsTag` | No | `"none"` | Analytics page tag — required if `isJourneyStep` is `true` |
| `flavorVariants` | No | `[]` | Flavors requiring branching, e.g. `["barclays","barclaycard"]` |

---

## Workflow

```
ui-engineer-android-tba-worker-agent    ← entry point: discovery + orchestration
        ↓ (spawns)
ui-engineer-android-tba-batch-worker-agent  ← generates TBA feature slice per batch
        ↓
./gradlew compileDebugKotlin             ← compile gate (auto-fix, max 3 retries)
        ↓
ui-engineer-android-validation-agent    ← base android quality gate (A1–A11)
        ↓
ui-engineer-android-tba-validation-agent ← TBA quality gate (T1–T10)
```

Each agent is independently invocable — invoke any step in isolation with an explicit `SCREENS` list.

---

## Agents

| Agent | Role |
|---|---|
| `ui-engineer-android-tba-worker-agent` | Orchestrator — screen discovery, spawns batch workers, compile gate, dual validation, final report |
| `ui-engineer-android-tba-batch-worker-agent` | Scope-bounded worker — generates one TBA feature slice per screen in an assigned batch |
| `ui-engineer-android-tba-validation-agent` | Read-only TBA quality gate — checks T1–T10 on top of base android checks |

---

## Skills loaded

| Skill | Source | Layer |
|---|---|---|
| `android` | `barclays-buk-ui-engineer-android` | Base Compose + Blueprint patterns |
| `android-tba` | This plugin | TBA Journey Framework, Scopes, FlavorDetails, BarclaysActivity |
| `accessibility` | `barclays-buk-standards` | WCAG 2.2 AA + Barclays accessibility standards |
| `security` | `barclays-buk-standards` | Secure Coding Practices v1.2.6 |
