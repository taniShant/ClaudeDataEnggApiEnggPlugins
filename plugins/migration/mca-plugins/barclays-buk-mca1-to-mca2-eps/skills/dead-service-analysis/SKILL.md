---
name: dead-service-analysis
description: >
    Domain knowledge for analyzing production Service Call Table CSV against codebase
    to identify dead (unused in production) ServiceManager.doService() calls. Produces
    a DEAD-CODE-ANALYSIS.md report and optional @MCA2-TECH-DEBT-DEAD-CODE markers.
---

# Dead Service Call Analysis Skill

## Purpose

Cross-reference a production "Service Call Table" CSV export against `ServiceManager.doService()` calls in an MCA1 codebase to identify services that are **never called in production** (dead code). This reduces migration scope and documents tech debt before/during MCA1→MCA2 migration.

---

## CSV Schema

The production CSV export has these key columns:

| Column | Purpose | Example |
|--------|---------|---------|
| `coevent.ServiceName` | Human-readable service name (appears in code as the first argument to `doService()`) | `CustomerUpdateServiceEBS`, `CentralAuditServiceEBS` |
| `coevent.PropertyName` | Kebab-case identifier (used in `.properties` files for service endpoint configuration) | `customer-update-service-ebs`, `central-audit-service-ebs` |
| Call count columns | Number of invocations in production over reporting period | `1523`, `0` |

**Key distinction:**
- `coevent.ServiceName` → matches what's in **Java code**: `doService("CustomerUpdateServiceEBS", ...)`
- `coevent.PropertyName` → matches what's in **properties files**: `services.CustomerUpdateServiceEBS.url=...` or `customer-update-service-ebs` in kebab-case config

---

## CSV Parsing Rules

1. **Read CSV** — handle both comma and tab-delimited formats
2. **Extract unique services** — build a "production service set" from BOTH columns:
   - From `coevent.ServiceName`: the exact production service names (PascalCase)
   - From `coevent.PropertyName`: the kebab-case identifiers used in properties
3. **Normalize entries** — for each entry, generate normalized form (lowercase, strip hyphens/underscores)
4. **Filter zero-count rows** — if a service appears in CSV but with 0 calls, it is NOT in the active production set (treat as dead)
5. **Result** — a set of service names that ARE actively called in production

---

## Code Scanning Patterns

Scan all `*.java` files under `src/main/` for `doService()` invocations. Three resolution patterns:

### Pattern 1: Literal String

```java
ServiceManager.doService("CentralAuditServiceEBS", request, response);
// or
serviceManager.doService("CentralAuditServiceEBS", request, response);
```

**Resolution:** Extract the literal string directly → `CentralAuditServiceEBS`

### Pattern 2: Class Constant

```java
ServiceManager.doService(AuditService.SERVICE_NAME, request, response);
```

**Resolution:**
1. Identify the class (`AuditService`) and field (`SERVICE_NAME`)
2. Search project for that class definition
3. Extract the constant value: `public static final String SERVICE_NAME = "CentralAuditServiceEBS";`
4. Resolved → `CentralAuditServiceEBS`

### Pattern 3: Variable or External Constant

```java
ServiceManager.doService(AuditConstants.ODS_REF_API, request, response);
// or
String serviceName = getServiceName();
ServiceManager.doService(serviceName, request, response);
```

**Resolution:**
1. Try to find constant definition in project (same as Pattern 2)
2. If constant is from an external JAR (not in project source) → look up `services.properties` (see Pattern 4 below)
3. If value comes from a method call or runtime variable → mark as `UNRESOLVED`

### Pattern 4: Resolve External Constants from JAR (Primary Method)

When a constant is defined in an external JAR (e.g., `EmployeeService.SERVICE_NAME` from `com.barclays.services.executioncontext`), **open the JAR and read the constant value directly**:

```bash
# Step 1: Find the JAR in Gradle cache using the import package path
find ~/.gradle/caches -path "*executioncontext*employee*" -name "*.jar" | head -1

# Step 2: Find the class inside the JAR
jar tf <jar_path> | grep "EmployeeService.class"

# Step 3: Extract the class
unzip -o <jar_path> <class_path> -d /tmp/jar_extract

# Step 4: Read the constant value from bytecode
javap -verbose /tmp/jar_extract/<class_path> | grep -A1 "ConstantValue"
```

**Example output:**
```
ConstantValue: String ExecutionContextEmployeeService
```

This gives you the exact value: `SERVICE_NAME = "ExecutionContextEmployeeService"` → RESOLVED.

**Resolution steps:**
1. Find the import statement for the external class (e.g., `import com.barclays.services.executioncontext.employee.service.EmployeeService`)
2. Search `~/.gradle/caches` for a JAR matching the package path
3. Extract the `.class` file and run `javap -verbose` to read `ConstantValue`
4. The `ConstantValue: String <value>` line gives you the literal service name
5. This is now RESOLVED — apply the matching algorithm

### Pattern 5: Fallback — Resolve from services.properties

If the JAR is not available in Gradle cache (rare), fall back to `services.properties`:

```properties
# Pattern: external.services.<servicename-lowercase>.implementationClass=...
external.services.executioncontextemployeeservice.implementationClass=com.barclays.services.executioncontext.employee.service.EmployeeImpl
```

The key segment between `external.services.` and `.implementationClass` is the service name (lowercase). Convert to PascalCase: `executioncontextemployeeservice` → `ExecutionContextEmployeeService`.

**Only mark as UNRESOLVED if:** The constant cannot be resolved from the JAR bytecode AND there is no matching entry in `services.properties`.

### REST Connector Exclusion Rule

**IMPORTANT:** If a `doService()` call uses `RestConnectorRequestBean` as request objects and calls method `"executeApi"` (or `REST_SERVICE_EXECUTE`), it is a **REST connector call**, not a traditional EBS service call. These are routed through `ServiceManager` but implemented by `RestConnectorImpl`.

To confirm: check `services.properties` for the service name — if `implementationClass=com.barclays.scp.eps.common.restconnector.impl.RestConnectorImpl`, **exclude this service from dead-code analysis**. REST connector calls are not tracked in the EBS Service Call Table CSV.

Alternatively, detect from code context:
- Request type is `RestConnectorRequestBean` (not a regular DTO/list)
- Method name is `"executeApi"` or referenced via `REST_SERVICE_EXECUTE` constant

**Action:** Classify as `EXCLUDED-REST-CONNECTOR` — not dead, just a different call path not tracked in the EBS CSV.

### Grep Commands

```bash
# Find all doService calls
grep -rn "doService(" src/main/ --include="*.java"

# Find constant definitions (after identifying constant names)
grep -rn "SERVICE_NAME\s*=" src/main/ --include="*.java"
grep -rn "static final String.*=.*\".*Service" src/main/ --include="*.java"

# Resolve external constants from services.properties
grep -in "external.services.*implementationClass" src/test/resources/services.properties

# Identify REST connector services (exclude from analysis)
grep -in "RestConnectorImpl" src/test/resources/services.properties
```

---

## Service Name Matching Algorithm

### Step 1: Normalize

For both code-extracted names and CSV entries, produce a normalized form:
- Convert to lowercase
- Strip all hyphens (`-`) and underscores (`_`)
- Strip trailing whitespace

Example: `customer-update-service-ebs` → `customerupdateserviceebs`
Example: `CustomerUpdateServiceEBS` → `customerupdateserviceebs`

### Step 2: Match Layers

| Layer | Method | Confidence |
|-------|--------|------------|
| **Layer 1: Exact match** | Code service name exactly matches a `coevent.ServiceName` entry | HIGH — confirmed active |
| **Layer 2: Normalized match** | Normalized code name matches normalized CSV entry (handles PascalCase ↔ kebab-case) | HIGH — confirmed active |
| **Layer 3: PropertyName match** | Code service name (normalized) matches a `coevent.PropertyName` entry (normalized) | HIGH — confirmed active |
| **No match** | Service found in code but NOT in any CSV column after normalization | POTENTIALLY DEAD |

### Step 3: Classification

| Result | Classification | Action |
|--------|---------------|--------|
| Match found (Layer 1, 2, or 3) | `ACTIVE` | Will be migrated normally in Phase 7 |
| No match found | `POTENTIALLY-DEAD` | Flag for developer decision |
| Constant unresolved (not in source OR services.properties) | `UNRESOLVED` | Flag for manual review — cannot determine service name |
| implementationClass is `RestConnectorImpl` or uses `RestConnectorRequestBean` + `executeApi` | `EXCLUDED-REST-CONNECTOR` | Ignore — REST calls not tracked in EBS CSV |

**CRITICAL RULES:**

1. **UNRESOLVED is a last resort.** A service is ONLY classified as `UNRESOLVED` if the constant's literal value **cannot be determined** from project source code AND cannot be resolved from `services.properties`. If the constant IS resolved to a string value — regardless of what it looks like (REST-style, kebab-case, etc.) — it is RESOLVED and must go through the matching algorithm above.

2. **Always check services.properties for external JARs.** Before marking a constant as UNRESOLVED, look up `src/test/resources/services.properties` for `external.services.<name>.implementationClass=...`. The key between `external.services.` and `.implementationClass` is the service name (lowercase). This resolves most external JAR constants.

3. **Exclude REST connector services.** If `implementationClass=com.barclays.scp.eps.common.restconnector.impl.RestConnectorImpl` in services.properties, OR the code uses `RestConnectorRequestBean` + method `"executeApi"`/`REST_SERVICE_EXECUTE`, the service is a REST API call routed through ServiceManager. These are NOT tracked in the EBS Service Call Table CSV and must be excluded from dead-code analysis entirely.

---

## Output: DEAD-CODE-ANALYSIS.md

Generate this report at `{PROJECT_PATH}/DEAD-CODE-ANALYSIS.md`:

```markdown
# Dead Service Call Analysis Report

**Project:** {project_name}
**Generated:** {timestamp}
**CSV Source:** {csv_file_path}
**Analysis Tool:** barclays-buk-mca1-to-mca2-eps:dead-service-analyzer-agent

---

## Summary

| Metric | Count |
|--------|-------|
| Unique services in production CSV | X |
| Unique services found in codebase | Y |
| Confirmed ACTIVE (matched in CSV) | Z |
| POTENTIALLY DEAD (no CSV match) | W |
| EXCLUDED (REST connector — not in EBS CSV) | E |
| UNRESOLVED (cannot determine name) | U |

---

## Potentially Dead Services

| # | Service Name | Code Location | Constant Source | Status |
|---|---|---|---|---|
| 1 | CustomerUpdateServiceEBS | AuditHelper.java:1701 | Literal | @MCA2-TECH-DEBT-DEAD-CODE |

---

## Active Services (Confirmed in Production)

| # | Service Name | Code Location | CSV Match Column | CSV Match Value | Prod Call Count |
|---|---|---|---|---|---|
| 1 | CentralAuditServiceEBS | AuditService.java:45 | coevent.ServiceName | CentralAuditServiceEBS | 152,340 |

---

## Excluded Services (REST Connector — Not Tracked in EBS CSV)

| # | Service Name | Code Location | Reason |
|---|---|---|---|
| 1 | odsRefDataAPI | AuditHelper.java:1727 | Uses RestConnectorRequestBean + executeApi (REST connector, not EBS) |

---

## Unresolved Services

| # | Code Reference | Code Location | Reason |
|---|---|---|---|
| 1 | AuditConstants.ODS_REF_API | OdsHelper.java:88 | Constant not in source AND not in services.properties |

---

## Recommendations

1. **POTENTIALLY DEAD services** should be verified with the owning team before removal
2. Services with `UNRESOLVED` status require manual lookup of the constant value
3. Run `/migrate-mca1-to-mca2` after this analysis — Phase 7 will read this report and offer
   per-service choices: migrate normally (if you know it's active), keep as tech debt, or remove
4. Zero-count services in CSV are treated as dead — verify reporting period covers typical usage
```

---

## Marker Convention

**Marker:** `// @MCA2-TECH-DEBT-DEAD-CODE`

**Purpose:** Flags the **start of a dead call trace** — the entry point (controller endpoint, service interface method) where live code meets dead code that calls a service not observed in production.

**Placement:** At the **top of the call trace** — NOT at the leaf `doService()` call. The marker goes on the controller method, service interface method, or highest-level caller that initiates the dead path:

```java
// @MCA2-TECH-DEBT-DEAD-CODE — GenericAuditServiceEBS not observed in production
// Dead call chain removed: Controller → ServiceImpl → Helper → doService("GenericAuditServiceEBS")
@PostMapping("/audit/v1/getAuditResults")
public ResponseEntity<?> getAuditResults(...) { ... }
```

**Properties file marker:** Comment out corresponding properties entries:

```properties
# @MCA2-TECH-DEBT-DEAD-CODE — not observed in production
# external.services.genericauditserviceebs.implementationClass=com.barclays.services.audit.impl.AuditServiceImpl
```

## Dead Code Removal Strategy

**CRITICAL: Do NOT return null from dead methods — that causes NPEs in callers.**

The correct approach is to trace the call graph UPWARD and remove from the top:

1. **Trace up** from `doService()` → calling method → its caller → ... → controller/entry point
2. **Find the boundary** — the point where live code calls into dead code
3. **Add marker at the boundary** (the entry point)
4. **Remove ALL downstream dead code** — every method in the chain below the boundary
5. **Verify compilation** — `./gradlew compileJava` must pass

**Decision tree per method in the chain:**
- Does this method have ANY other purpose besides calling the dead service?
  - **NO** → it's dead too, trace up further and remove it
  - **YES** → this is the boundary. Keep the method, remove only the dead call within it
- After removal, is the class now empty (no remaining methods)?
  - **YES** → delete the class file entirely. Do NOT leave empty shells.
  - **NO** → keep the class with its remaining live methods

**For controller endpoints that are entirely dead:**
- Remove the endpoint method body, keep the signature with the marker
- Or comment out the `@RequestMapping`/`@PostMapping` annotation

**For service interface methods that are entirely dead:**
- Comment out the method signature in the interface with the marker
- Remove the implementation entirely

**Relationship to Phase 7:** When the main migration agent (Phase 7B) encounters a service marked in `DEAD-CODE-ANALYSIS.md`:
- It asks the developer per dead service: **"Keep as tech debt"** or **"Remove altogether"**
- **Keep as tech debt:** Add `@MCA2-TECH-DEBT-DEAD-CODE` marker at call trace entry, remove all downstream dead code, verify compilation
- **Remove altogether:** Same as above PLUS delete the service properties entries entirely (not just comment out)

---

## Integration with Main Migration

The `DEAD-CODE-ANALYSIS.md` report is consumed by the main `mca1-to-mca2-eps-agent` during Phase 7:

1. Agent checks if `{PROJECT_PATH}/DEAD-CODE-ANALYSIS.md` exists
2. If present: parses the "Potentially Dead Services" table
3. For each `doService()` call being migrated:
   - If service is in the POTENTIALLY-DEAD list → ask developer: keep as tech debt or remove
   - If service is ACTIVE or not in the report → migrate normally using chosen REST strategy
4. If absent: migrate all services normally (backward-compatible)

This ensures the dead-service analysis is **optional** — projects that skip it get normal migration behavior.
