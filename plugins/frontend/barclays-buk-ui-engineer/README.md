# barclays-buk-ui-engineer

> **Status: Available**

Cross-platform UI engineer dispatcher. Detects the target platform from project context and delegates to the appropriate specialist plugin. Falls back to direct generation for platforms without a specialist yet.

## How it works

```
barclays-buk-ui-engineer (dispatcher)
  ├── SDF project (@barclays/chameleon-blueprint) → barclays-buk-ui-engineer-sdf
  ├── Web project (@barclays/blueprint-react)     → barclays-buk-ui-engineer-web
  ├── iOS project (xcodeproj/xcworkspace/podspec)  → barclays-buk-ui-engineer-ios
  ├── Android TBA project (barclays.behaviourSdk)  → barclays-buk-ui-engineer-android-tba
  ├── Android project (build.gradle)               → barclays-buk-ui-engineer-android
  └── No specialist match                          → direct generation (fallback)
```

Detection is automatic — point it at your project and it works out the platform. For TBA Android projects, it detects `barclays.behaviourSdk` in `build.gradle` and routes to the TBA specialist rather than the generic Android plugin.

The specialist plugins are independently invocable — you can call them directly, or let this dispatcher route for you.

---

## Setup

### 0. Create a new SDF project (greenfield only)

If you don't have an existing project, scaffold one from the Chameleon template:

```bash
npx @react-native-community/cli@20.0.0 init <ProjectName> \
  --template @barclays/chameleon-template@latest \
  --pm npm \
  --skip-install \
  --skip-git-init
cd <ProjectName>
npm install
```

For iOS, run pod install from the shell app directory:

```bash
cd shell-app/ios && pod install && cd ../..
```

Skip this step if you are working in an existing project.

### 1. Install the plugin

```bash
claude plugin install barclays-buk-ui-engineer@barclays-cio-buk
```

This installs the dispatcher and all platform specialists (Android, iOS, SDF, Web, Android TBA).

### 2. Configure Figma MCP for your project

Agents use the Figma Dev Mode MCP server to extract real design context. Run this once per project:

```bash
# From the BUK marketplace repo root
bash plugins/frontend/barclays-buk-ui-engineer/scripts/setup-figma-mcp.sh /path/to/your/project
```

This writes `.mcp.json` and `.claude/settings.local.json` into the target project. These files are developer-local — add `.mcp.json` to `.gitignore` if you don't want it committed (the `enabledMcpjsonServers` approval is already in `.claude/settings.local.json` which is untracked).

### 3. Enable Figma Desktop Dev Mode MCP

Open Figma Desktop → **Figma menu → Preferences → Enable Dev Mode MCP Server**.

In the **Desktop MCP server settings** dialog, set **Image source** to **Local server**. This allows Figma to serve images directly over the MCP connection — no allowed directories required.

The server must be running before you start your Claude session.

### 4. Install agent-device (visual preview)

Agents use `agent-device` to open the shell app, capture screenshots, and verify screen content via the accessibility tree. Install it globally once:

```bash
npm install -g agent-device@latest
```

Verify it's working:

```bash
agent-device --version
```

If you skip this step, visual preview steps in the agents will be skipped and flagged in the batch result output.

### 5. Start Claude in your project

```bash
cd /path/to/your/project
claude
```

Run `/mcp` to confirm `figma-local` is connected before invoking any agent.

---

## Usage

Invoke `ui-engineer-agent` with:

```
PROJECT_PATH:     /path/to/your/project
JIRA_ID:          PLATENG-1234
FIGMA_URL:        https://www.figma.com/design/... | "none"
PLATFORM_OPTIONS: {}
ADDITIONAL_INPUT: free text description | "none"
```

**Example — BMB Android TBA screen:**
```
PROJECT_PATH:     /path/to/bmb/cardshubteam/lowlevel/cardshubinternal
JIRA_ID:          EMMCARDSFT-13436
FIGMA_URL:        https://www.figma.com/design/KSebbgxMYA38WxILZIV179/...?node-id=44826-21641
PLATFORM_OPTIONS: {"package": "com.barclays.bmb.features.cardshub.blueprint", "teamScope": "CardshubScope"}
```

**Example — iOS screen:**
```
PROJECT_PATH:     /path/to/ios/CardDetails
JIRA_ID:          UCG-5678
FIGMA_URL:        https://www.figma.com/design/...
```

**Example — SDF screen:**
```
PROJECT_PATH:     /path/to/sdf/card-details
JIRA_ID:          UCG-5678
FIGMA_URL:        https://www.figma.com/design/...
```

At least one of `FIGMA_URL` or `ADDITIONAL_INPUT` must be provided. If `PLATFORM` is passed explicitly as `sdf`, `ios`, `android`, `android-tba`, or `web`, auto-detection is skipped.

**PLATFORM_OPTIONS for android-tba:**

| Key | Required | Default | Description |
|---|---|---|---|
| `package` | Yes | — | Kotlin package, e.g. `com.barclays.mobilebanking.carddetails` |
| `teamScope` | Yes | — | Team scope class, e.g. `CardshubScope` |
| `isJourneyStep` | No | `false` | Generate Journey Framework slice |
| `controllerId` | No | `"none"` | MVC controller ID — required if `isJourneyStep` is `true` |
| `analyticsTag` | No | `"none"` | Analytics page tag — required if `isJourneyStep` is `true` |
| `flavorVariants` | No | `[]` | Flavors requiring branching, e.g. `["barclays","barclaycard"]` |

---

## Workflow position

```
UX Designer + Copywriter → ui-engineer-agent (dispatcher) → specialist → Quality Engineer / Accessibility Auditor
```

---

## Agents

| Agent | Purpose |
|---|---|
| `ui-engineer-agent` | Detects platform, delegates to specialist, or generates directly as fallback |

---

## Dependencies

- `barclays-buk-standards` — provides `accessibility` and `security` skills
