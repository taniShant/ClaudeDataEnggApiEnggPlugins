# Strategy B — Existing Microservice

Developer provides a local filesystem path to an existing microservice. Validate it, discover its patterns, and prepare for endpoint generation.

**Called by:** `mts-migrate.md` orchestrator when developer selects Strategy B.

---

## Input (from orchestrator)

- `SERVICE_NAME_METHOD`: the MTS service name and method being migrated

---

## Step B.1 — Get Path

```
AskUserQuestion:
  question: "Provide the local filesystem path to your existing microservice:"
  header: "Service path"
  options:
    - label: "I'll provide the path"
      description: "Enter the absolute path to the microservice project root"
```

Validate the provided path:

1. Check that the directory exists:
   ```bash
   ls <provided_path>
   ```

2. Check for a build file:
   ```
   Glob <provided_path>/build.gradle
   Glob <provided_path>/pom.xml
   ```

3. If neither build file exists:
   ```
   Error: No build.gradle or pom.xml found at <provided_path>.
   Please provide the path to the project root directory.
   ```
   Re-ask via AskUserQuestion.

Store the validated path as `TARGET_REPO_PATH`.

---

## Step B.2 — Pattern Discovery

Launch an Explore agent on the provided microservice to discover its conventions:

```
Task tool call:
  subagent_type: Explore
  thoroughness: "very thorough"
  prompt: Discover coding patterns in <TARGET_REPO_PATH>.
    Produce a Pattern Profile with these 8 categories:

    1. Feature Flags — search for hasFlag, FlagType, LaunchDarkly, FeatureToggle,
       @ConditionalOn, feature.enabled, @Value.*enabled.
       Classify: ENUM_FLAG | PROPERTY_FLAG | API_ENUM_ROUTING | NONE
    2. Dependency Injection — sample 3-5 @Service/@Component classes.
       Classify: CONSTRUCTOR_AUTOWIRED | SETTER_AUTOWIRED | SETTER_RESOURCE | XML_BEAN
    3. REST Client — search for RestTemplate, WebClient, RestConnectorRequestBean,
       ServiceManager.doService, Feign, executeApi. Capture a complete example.
    4. Converter/Mapper — search for implements Converter, MapStruct, ModelMapper.
       Classify: SPRING_CONVERTER | MANUAL_MAPPER_BEAN | STATIC_MAPPER | MAPSTRUCT
    5. Test Framework — search test dirs for @Tag("unit"), @RunWith, @ExtendWith.
       Classify: JUNIT5_MOCKITO | JUNIT4_MOCKITO | JUNIT4_JMOCK | JUNIT5_STUBS
    6. Bean Wiring — check for *-config.xml, applicationContext*.xml.
       Classify: ANNOTATION_ONLY | XML_AND_ANNOTATION
    7. Existing Migration Pattern — search for FromApi, FromMTS, dual methods, ODS+EBS.
       Capture complete dual-path code if found.
    8. Service Layer Base Class — search for extends Abstract in service impl classes.

    Use the structured Pattern Profile output format with ## headers for each
    category, including full code examples. Sample 3-5 classes per category.
```

Wait for completion. Store the full PATTERN_PROFILE text.

---

## Step B.3 — Repo Context

Determine the target's project structure for endpoint generation:

### B.3a — Package Structure

From the Pattern Profile's REST Client or Dependency Injection examples, extract the base package. Alternatively:

```
Grep "^package " <TARGET_REPO_PATH>/src/main/java/ --type java
```

Find the most common root package across source files.

### B.3b — Existing Controllers

```
Grep "@RestController|@Controller" <TARGET_REPO_PATH>/src/main/java/ --type java
```

Note any existing endpoint patterns (URL prefixes, versioning, response wrappers).

### B.3c — Spring Boot Version

Extract from the build file:
- Gradle: look for `org.springframework.boot` plugin version or `springBootVersion` variable
- Maven: look for `<parent>` with `spring-boot-starter-parent` version

---

## Output (REQUIRED — return to orchestrator)

```
## SECTION: STRATEGY_B_RESULT
- TARGET_REPO_PATH: <absolute path to the existing microservice>
- PATTERN_PROFILE: <full structured Pattern Profile text>
- BASE_PACKAGE: <detected base package>
- EXISTING_CONTROLLERS: [list of existing controller classes with their URL paths]
- SPRING_BOOT_VERSION: <detected or "unknown">
- BUILD_TOOL: gradle | maven
```
