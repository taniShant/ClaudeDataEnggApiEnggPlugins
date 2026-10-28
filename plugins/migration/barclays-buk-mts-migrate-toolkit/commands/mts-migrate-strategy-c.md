# Strategy C — In-Place Migration

Perform dual-path migration within the current BUK monolith repo. This is the original `/mts-migrate` behavior, extracted into its own strategy file.

**Called by:** `mts-migrate.md` orchestrator when developer selects Strategy C.

---

## Input (from orchestrator)

- `SERVICE_NAME_METHOD`: the MTS service name and method being migrated
- `MTS_SERVICE_DOC_DATA`: extracted gateway, EDO class, service name, request/response fields
- `MATCH_REPORT_DATA`: full match report data (needed for bean gap validation in Step C.2e)

---

## Step C.1 — Pattern Discovery

Launch an Explore agent on the BUK repo to discover its conventions:

```
Task tool call:
  subagent_type: Explore
  thoroughness: "very thorough"
  prompt: Discover coding patterns in this BUK Spring Boot monolith repo.
    Produce a Pattern Profile with these 8 categories:

    1. Feature Flags — search for hasFlag, FlagType, ActionFlag, LaunchDarkly,
       FeatureToggle, @ConditionalOn, feature.enabled, @Value.*enabled.
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
    8. Service Layer Base Class — search for extends EpsAbstractService,
       extends Abstract in service impl classes.

    Use the structured Pattern Profile output format with ## headers for each
    category, including full code examples.
```

Wait for completion. Store the full PATTERN_PROFILE text.

---

## Step C.2 — Repo-Specific Context

Using the Pattern Profile as background, perform discovery specific to THIS migration.

### C.2a — Find the Calling Service Class

Search for the class that currently calls the MTS gateway method:

```
Grep "<ServiceName>.SERVICE_NAME" in src/main/java/
```

or using the service doc's caller hierarchy:

```
Grep "doService.*<ServiceName>" in src/main/java/
```

Read the calling service class to identify:
- The method where the MTS call happens
- The existing return type (EDO class)
- Any existing flag-based routing nearby
- Injected dependencies

Store as `CALLING_SERVICE_CLASS` (full source text).

### C.2b — Feature Flag Details

Based on the Pattern Profile's Feature Flags section:

- If `ENUM_FLAG`: Read the enum class file to see existing constants and the pattern for adding new ones. Store as `FEATURE_FLAG_DATA`.
- If `PROPERTY_FLAG`: Note the property prefix for the new flag. Store as `FEATURE_FLAG_DATA`.
- If `NONE`: Note that no flag routing will be generated. Store `FEATURE_FLAG_DATA` = "NONE".

### C.2c — Read Config Files

Read `src/main/resources/application.properties` (or equivalent from Pattern Profile).

Find the section with existing REST connector configurations to know:
- Where to insert the new connector config
- What pattern to follow

Store as `CONFIG_DATA` (relevant config section text).

### C.2d — Determine Target Packages and Naming

Derive the domain name from the gateway class:
- `CustomerGateway` -> domain = `customer`
- `ProductGateway` -> domain = `productholdings`
- `AccountGateway` -> domain = `account`
- Strip "Gateway", "Eao", "Service", "Delegate" suffix, lowercase the remainder.

Determine package paths from Pattern Profile's REST Client example.

Determine naming:
- **API service class**: `<ApiShortName>Service`
- **Converter/mapper**: Follow Pattern Profile's Converter/Mapper style
- **Feature flag**: Follow Pattern Profile's Feature Flag pattern
- **REST connector name**: `<apiShortName>Connector`

### C.2e — Validate Existing ODS Response Beans

If the Pattern Profile shows an existing migration (Existing Migration Pattern = YES) and a connector for the target API already exists:

1. Find existing ODS response model classes:
   ```
   Grep "setResponseClass" in src/main/java/ — find the response class for the matched API connector
   ```
2. Read the response model class and its nested beans (follow getter chains)
3. Compare fields against the match report's response field mapping
4. For each match report field:
   - If bean has a matching getter -> `BEAN_COMPLETE`
   - If bean lacks a matching getter -> `BEAN_GAP` with class name and missing field
5. Store the BEAN_GAP list

If no existing response model exists, skip this step.

Store as `BEAN_GAP_LIST`.

---

## Output (REQUIRED — return to orchestrator)

```
## SECTION: STRATEGY_C_RESULT
- TARGET_REPO_PATH: <absolute path to BUK repo root>
- PATTERN_PROFILE: <full structured Pattern Profile text>
- CALLING_SERVICE_CLASS: <full source of the calling service class>
- CALLING_SERVICE_CLASS_PATH: <file path>
- FEATURE_FLAG_DATA: <flag enum/property contents or "NONE">
- FEATURE_FLAG_FILE_PATH: <path or "N/A">
- CONFIG_DATA: <relevant config section>
- CONFIG_FILE_PATH: <path>
- TARGET_PACKAGES: <package paths and class names>
- BEAN_GAP_LIST: [list of bean gaps or "NONE"]
```
