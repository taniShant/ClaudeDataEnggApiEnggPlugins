# barclays-buk-ui-engineer-android

> **Status: Planned**

Generate Android screens from Figma designs into Jetpack Compose composables using `com.barclays.compose.blueprint`.

## Channel Scope

Mobile (native Android)

---

## Workflow

```
ui-engineer-discover-agent          ← turn Figma URL into SCREENS list
        ↓
ui-engineer-android-screen-composer-agent   ← Figma → composable + ViewModel stub
        ↓
ui-engineer-android-viewmodel-agent         ← wire OAS → full ViewModel, Factory, Scope
        ↓
ui-engineer-android-navigation-agent        ← NavGraph, Navigator, Routes
        ↓
ui-engineer-android-test-agent              ← ViewModel unit tests + screen UI tests
        ↓
ui-engineer-android-validation-agent        ← quality gate (APPROVED / REJECTED)
```

Each agent is independently invocable — invoke any step in isolation with an explicit `SCREENS` list.

---

## Agents

| Agent | Role |
|---|---|
| `ui-engineer-android-screen-composer-agent` | Generates screen composables from Figma, with minimal ViewModel stub |
| `ui-engineer-android-viewmodel-agent` | Generates full ViewModel, Factory, Scope — optionally OAS-derived state |
| `ui-engineer-android-navigation-agent` | Generates NavGraph, typed Navigator, Routes constants |
| `ui-engineer-android-test-agent` | Generates ViewModel unit tests (MockK) and screen UI tests (Robolectric) |
| `ui-engineer-android-validation-agent` | Read-only quality gate — returns APPROVED or REJECTED with per-flag evidence |
| `ui-engineer-android-worker-agent` | Full-batch worker for automated orchestration — task agents are the preferred human entry point |

---

## Skills

| Skill | Purpose |
|---|---|
| `android` | BMB Jetpack Compose patterns — module structure, ViewModel, DI, Blueprint component map, testing |
| `tba` | The Barclays App patterns — Journey Framework, MVC action layer, Scope DI, FlavorDetails |
