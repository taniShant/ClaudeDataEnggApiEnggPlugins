# barclays-buk-ui-engineer-ios

> **Status: Available**

Generate iOS screens from Figma designs into SwiftUI views using `BarclaysBlueprint`.

## Channel Scope

| Channel | Supported |
|---|---|
| Online Banking (native iOS) | ✅ |
| Mobile (native iOS) | ✅ |
| Android | ❌ Use `barclays-buk-ui-engineer-android` or `barclays-buk-ui-engineer-android-tba` |

---

## Usage

The recommended entry point is `ui-engineer-agent` — it auto-detects iOS projects via `.xcodeproj`, `.xcworkspace`, or `.podspec` and routes here automatically.

**Via the dispatcher (recommended):**

Invoke `ui-engineer-agent` with:
```
PROJECT_PATH:  /path/to/ios/feature-module
JIRA_ID:       UCG-1234
FIGMA_URL:     https://www.figma.com/design/...
```

**Invoke the orchestrator directly:**

Invoke `ui-engineer-ios-screen-composer-agent` with:
```
PROJECT_PATH:     /path/to/ios/feature-module
JIRA_ID:          UCG-1234
FIGMA_URL:        https://www.figma.com/design/...
ADDITIONAL_INPUT: free text description | "none"
```

**Invoke a task agent directly** (after screens have been generated):

```
# Wire ViewModels to an OpenAPI spec
ui-engineer-ios-viewmodel-agent
  PROJECT_PATH:  /path/to/ios/feature-module
  JIRA_ID:       UCG-1234
  OAS_SPEC_PATH: /path/to/openapi.yaml
  SCREENS:       [{componentName, viewFile, viewModelFile, ...}]

# Generate navigation coordinators
ui-engineer-ios-navigation-agent
  PROJECT_PATH:  /path/to/ios/feature-module
  JIRA_ID:       UCG-1234
  SCREENS:       [{componentName, viewFile, viewModelFile, ...}]

# Generate tests
ui-engineer-ios-test-agent
  PROJECT_PATH:  /path/to/ios/feature-module
  JIRA_ID:       UCG-1234
  SCREENS:       [{componentName, viewFile, viewModelFile, ...}]

# Run the quality gate
ui-engineer-ios-validation-agent
  PROJECT_PATH:  /path/to/ios/feature-module
  JIRA_ID:       UCG-1234
```

---

## Workflow

```
ui-engineer-ios-screen-composer-agent   ← entry point: discovery + orchestration
        ↓ (spawns)
ui-engineer-ios-batch-worker-agent      ← generates SwiftUI View + ViewModel per batch
        ↓
xcodebuild build / swift build          ← compile gate (auto-fix, max 3 retries)
        ↓
ui-engineer-ios-validation-agent        ← quality gate (APPROVED / REJECTED)
```

Task agents (viewmodel, navigation, test) are invoked separately and in any order after screen-composer completes. Each accepts the `SCREENS` list from screen-composer output.

---

## Agents

| Agent | Role |
|---|---|
| `ui-engineer-ios-screen-composer-agent` | Orchestrator — screen discovery, spawns batch workers, compile gate, validation, final report |
| `ui-engineer-ios-batch-worker-agent` | Scope-bounded worker — generates SwiftUI View + ViewModel stub per screen in an assigned batch |
| `ui-engineer-ios-viewmodel-agent` | Wires full ObservableObject ViewModel from OAS spec — stubs with TODOs if no spec supplied |
| `ui-engineer-ios-navigation-agent` | Generates UIKit Coordinator, public Factory, Router protocol |
| `ui-engineer-ios-test-agent` | Generates XCTest ViewModel unit tests and XCUITest smoke tests |
| `ui-engineer-ios-validation-agent` | Read-only quality gate — returns APPROVED or REJECTED with per-flag evidence |

---

## Skills

| Skill | Purpose |
|---|---|
| `ios` | BMB SwiftUI + BarclaysBlueprint patterns — module structure, ViewModel, DI, Blueprint component map, theme tokens, testing, localisation, accessibility, security |
| `security-ios` | iOS-specific security extensions — App Attest, TrustKit, Xcode build settings, BlueprintSecureField, BlueprintKeypad |
