# Migration Output Template

The `/mts-migrate` pipeline produces multiple artifacts. The exact output varies by strategy
(A/B/C) and response contract (mts-compat/ods-native). This template shows the structure
of each output artifact.

---

## Pipeline Outputs Summary

| Artifact | File Pattern | Producer |
|----------|-------------|----------|
| Generated code | `src/main/java/<package>/*.java` | `mts-migrate-code-agent` |
| Generated tests | `src/test/java/<package>/*.java` | `mts-migrate-test-agent` |
| Migration issues doc | `docs/mts/migrate-issues-<Service>-<method>.md` | `mts-migrate-issues-agent` |
| Final report | Console output | Orchestrator (Step S.4) |

---

## 1. Code Generation Output

### Strategy A/B (Standalone Endpoint)

Files created in `TARGET_REPO_PATH`:

| Component | Directory | File Pattern |
|-----------|-----------|-------------|
| REST Controller | `controller/` | `<Domain>Controller.java` |
| API Client Service | `client/` | `Ods<Domain>Client.java` |
| Derivation/Business Logic | `service/` | `<Domain>Service.java` |
| Converter (mts-compat only) | `converter/` | `Ods<Domain>Converter.java` |
| Response Model (ods-native only) | `model/response/` | `Ods<Domain>Response.java` |
| Config | `config/` | `<Domain>Config.java` |
| Exception Handler | `config/` | `GlobalExceptionHandler.java` |

### Strategy C (In-Place Dual-Path)

Files created or modified:

| Component | Action | File |
|-----------|--------|------|
| API Response Model | Create (or extend existing) | `model/Ods<Domain>Response.java` |
| API Service Class | Create | `service/Ods<Domain>ApiService.java` |
| Converter/Mapper | Create | `converter/<ApiResponse>To<Edo>Converter.java` |
| Feature Flag | Modify | Enum class or properties file |
| Existing Service Impl | Modify | Add routing + FromMTS/FromApi methods |
| Config | Modify | `application.properties` |

### Code Agent Result Format

```
## SECTION: CODE_GENERATION_RESULT
- strategy: A | B | C
- response_contract: mts-compat | ods-native
- files_created: [list of absolute paths]
- files_modified: [list of absolute paths + change description]
- warnings: [list of warnings]
```

---

## 2. Test Generation Output

Tests follow the target repo's test framework (detected from Pattern Profile):

| Framework | Pattern |
|-----------|---------|
| JUnit 5 + Mockito | `@ExtendWith(MockitoExtension.class)` |
| JUnit 4 + Mockito | `@RunWith(MockitoJUnitRunner.class)` |
| Spring Boot Test | `@SpringBootTest` with `@MockBean` |

### Test Files Created

| Component | File Pattern | Coverage |
|-----------|-------------|----------|
| Client test | `Ods<Domain>ClientTest.java` | API call, error handling |
| Converter test | `Ods<Domain>ConverterTest.java` | Field mapping, null handling |
| Service test | `<Domain>ServiceTest.java` | Routing logic (Strategy C) |
| Controller test | `<Domain>ControllerTest.java` | Endpoint integration |

### Mock Data

- API response JSON fixtures in test resources
- WireMock stubs (if WireMock is detected in repo)

### Test Agent Result Format

```
## SECTION: TEST_GENERATION_RESULT
- files_created: [list of test file paths]
- warnings: [list of warnings]
```

---

## 3. Migration Issues Document

Output: `docs/mts/migrate-issues-<ServiceName>-<method>.md`

```markdown
# Migration Issues: <Service>.<method>

## Summary

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| Data Gaps | N | N | N | N | N |
| Transformations | N | N | N | N | N |
| Error Handling | N | N | N | N | N |
| Config/Infra | N | N | N | N | N |
| **Total** | **N** | **N** | **N** | **N** | **N** |

## Data Gaps

| # | MTS Field | Severity | Status | Action Required |
|---|-----------|----------|--------|-----------------|
| 1 | fieldName | Medium | Open | Description of gap and recommended fix |

## Transformation Issues

| # | MTS Field | ODS Field | Issue | Severity | Action |
|---|-----------|-----------|-------|----------|--------|
| 1 | booleanField | indicator | Y/N vs true/false | Low | Use equalsIgnoreCase("Y") |

## Error Handling Differences

| # | Scenario | MTS Behaviour | ODS Behaviour | Action |
|---|----------|---------------|---------------|--------|
| 1 | Not found | Returns empty response | HTTP 404 | Map 404 to empty response |

## Config & Infrastructure

| # | Item | Detail | Action |
|---|------|--------|--------|
| 1 | REST connector | New connector config needed | Add to application.properties |

## Compile Fixes Applied

(Fixes applied during Step S.1.5 compilation verification)

| # | File | Error | Fix Applied |
|---|------|-------|-------------|
| 1 | OdsClient.java | Missing import | Added import for RestTemplate |

## Test Fixes Applied

(Fixes applied during Step S.2.5 test execution)

| # | File | Failure | Fix Applied |
|---|------|---------|-------------|
| 1 | OdsClientTest.java | Wrong mock setup | Fixed mock return type |
```

---

## 4. Final Report (Console Output)

```
MTS migration code generation complete:

Strategy: <A: New microservice | B: Existing microservice | C: In-place>
Response contract: <mts-compat | ods-native>
Target: <TARGET_REPO_PATH>
Repo pattern: <Pattern Profile summary>

New files created:
- <list of new files with paths>

Modified files:
- <list of modified files with description of change>

Summary:
- N new classes, N modified files, N unit tests
- N field mappings (X exact, Y renamed, Z transformed)
- N known migration issues (see migrate-issues doc)
- N fields with no API equivalent (true gaps)

Review the issues doc for manual follow-up items:
  docs/mts/migrate-issues-<ServiceName>-<method>.md
```
