# Strategy A — New Microservice

Clone a GitLab template into `code/mts/<service>/`, scaffold it, discover its patterns, and prepare for endpoint generation.

**Called by:** `mts-migrate.md` orchestrator when developer selects Strategy A.

---

## Input (from orchestrator)

- `SERVICE_NAME_METHOD`: the MTS service name and method being migrated
- `SETTINGS_DATA`: contents of `config/mts-migrate-settings.md` (template URL, defaults)

---

## Step A.1 — Template URL

Read the template URL from the embedded SETTINGS_DATA.

If the template URL is `<TO_BE_CONFIGURED>`:

```
AskUserQuestion:
  question: "No GitLab template URL is configured. Please provide the Git clone URL for your microservice template:"
  header: "Template URL"
  options:
    - label: "I'll provide it"
      description: "Enter the Git URL for the microservice starter template"
```

Store the resolved template URL.

---

## Step A.2 — Project Naming

Ask the developer for project identifiers:

```
AskUserQuestion:
  question: "What artifact ID should the new microservice use?"
  header: "Artifact ID"
  options:
    - label: "<auto-derived-from-service-name>"
      description: "Derived from the MTS service name (e.g., customer-enquiry-api)"
    - label: "Custom name"
      description: "Provide your own artifact ID"
```

```
AskUserQuestion:
  question: "What service name should the new microservice use?"
  header: "Service name"
  options:
    - label: "<same-as-artifact-id>"
      description: "Use the artifact ID as the service name"
    - label: "Custom name"
      description: "Provide a different service name"
```

Derive from the answers and settings:
- **ARTIFACT_ID**: the artifact ID (e.g., `customer-enquiry-api`)
- **SERVICE_NAME**: the service name (e.g., `customer-enquiry-api`)
- **GROUP_ID**: `<settings.group_id_prefix>.<domain>` (e.g., `com.barclays.uk.customerenquiry`)
- **BASE_PACKAGE**: same as GROUP_ID with dots (e.g., `com.barclays.uk.customerenquiry`)
- **APPLICATION_CLASS**: PascalCase from artifact ID + "Application" (e.g., `CustomerEnquiryApplication`)

---

## Step A.3 — Clone Template

```bash
mkdir -p code/mts
git clone <template_url> code/mts/<SERVICE_NAME>
rm -rf code/mts/<SERVICE_NAME>/.git
```

Verify the clone succeeded by checking for a build file:
```
Glob code/mts/<SERVICE_NAME>/build.gradle
Glob code/mts/<SERVICE_NAME>/pom.xml
```

If neither exists, report an error and stop.

**Directory rule:** Only create the base package directory and resources directory.
Do NOT pre-create sub-packages (controller/, service/, client/, converter/, model/).
The code agent creates these as needed via the Write tool.

---

## Step A.4 — Git Tracking

```
AskUserQuestion:
  question: "Should the new microservice be tracked in this BUK repo, or gitignored?"
  header: "Git tracking"
  options:
    - label: "Gitignore (Recommended)"
      description: "Add code/mts/<SERVICE_NAME>/ to .gitignore. The service will have its own repo later."
    - label: "Track in BUK"
      description: "Keep the cloned service tracked in this repo's git history."
```

If gitignore: append `code/mts/<SERVICE_NAME>/` to `.gitignore` using Edit tool.

---

## Step A.5 — Scaffold

Launch the scaffold agent to rename all template identifiers:

```
Task tool call:
  subagent_type: general-purpose
  model: <AGENT_MODEL>
  prompt: <embed full instructions from agents/mts-migrate-scaffold-agent.md>

  ## EMBEDDED INPUT DATA
  - TEMPLATE_PATH: <absolute path to code/mts/SERVICE_NAME>
  - ARTIFACT_ID: <from Step A.2>
  - GROUP_ID: <from Step A.2>
  - BASE_PACKAGE: <from Step A.2>
  - SERVICE_NAME: <from Step A.2>
  - APPLICATION_CLASS: <from Step A.2>
```

Wait for completion. Receive `SCAFFOLD_RESULT` with files_modified, old/new package, build tool, versions.

---

## Step A.6 — Pattern Discovery

Launch an Explore agent on the cloned and scaffolded microservice to discover its conventions:

```
Task tool call:
  subagent_type: Explore
  prompt: Discover coding patterns in <absolute path to code/mts/SERVICE_NAME>.
    Produce a Pattern Profile with these 8 categories:

    1. Feature Flags — search for hasFlag, FlagType, LaunchDarkly, FeatureToggle,
       @ConditionalOn, feature.enabled, @Value.*enabled.
       Classify: ENUM_FLAG | PROPERTY_FLAG | API_ENUM_ROUTING | NONE
       (likely NONE for a fresh template)
    2. Dependency Injection — sample @Service/@Component classes.
       Classify: CONSTRUCTOR_AUTOWIRED | SETTER_AUTOWIRED | SETTER_RESOURCE | XML_BEAN
    3. REST Client — search for RestTemplate, WebClient, RestConnectorRequestBean,
       ServiceManager.doService, Feign, executeApi. Capture a complete example.
    4. Converter/Mapper — search for implements Converter, MapStruct, ModelMapper.
       Classify: SPRING_CONVERTER | MANUAL_MAPPER_BEAN | STATIC_MAPPER | MAPSTRUCT
    5. Test Framework — search test dirs for @Tag("unit"), @RunWith, @ExtendWith.
       Classify: JUNIT5_MOCKITO | JUNIT4_MOCKITO | JUNIT4_JMOCK | JUNIT5_STUBS
    6. Bean Wiring — check for *-config.xml, applicationContext*.xml.
       Classify: ANNOTATION_ONLY | XML_AND_ANNOTATION
    7. Existing Migration Pattern — search for FromApi, FromMTS, dual methods.
       (will be NO for a fresh template)
    8. Service Layer Base Class — search for extends Abstract in service classes.

    Use the structured Pattern Profile output format with ## headers for each
    category, including full code examples.
```

Wait for completion. Store the full PATTERN_PROFILE text.

---

## Output (REQUIRED — return to orchestrator)

```
## SECTION: STRATEGY_A_RESULT
- TARGET_REPO_PATH: <absolute path to code/mts/SERVICE_NAME>
- PATTERN_PROFILE: <full structured Pattern Profile text>
- SCAFFOLD_RESULT: <from Step A.5>
- ARTIFACT_ID: <value>
- GROUP_ID: <value>
- BASE_PACKAGE: <value>
- SERVICE_NAME: <value>
- APPLICATION_CLASS: <value>
```
