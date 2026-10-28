# Process System: Journey Definition and Routing Engine

## Executive Summary

The **MCA Process System** is the central configuration and orchestration mechanism that defines how user journeys are structured, how backend service endpoints are exposed, and how requests are validated, routed, and secured at runtime. Every MCA journey is driven by a **process.json** file -- a declarative artifact that describes endpoints, tasks (screens), navigation events, API definitions, and UI module bindings.

**Key Characteristics:**
- **process.json** is the single source of truth for each journey's endpoints, tasks, and API schemas
- **Process discovery** resolves and fetches process definitions dynamically at launch time
- **URL obfuscation** hides real backend paths behind UUID-based proxy URIs
- **Process chaining** enables parent-child journey composition with shared IOL context
- **Per-process OAS validation** enforces OpenAPI 3.0 contract validation per endpoint
- **Request processor chain** deobfuscates, resolves hosts, injects context headers, and validates -- all driven by process metadata

**Participating Modules:**

| Module | Location | Role |
|--------|----------|------|
| **process-lib** | `mca-libraries/process-lib/` | Classpath-based process.json loading and REST exposure |
| **secure-proxy-api** | `mca-libraries/secure-proxy-api/` | Process interfaces, data model, and ProcessDefinition contract |
| **secure-proxy-core** | `mca-libraries/secure-proxy-core/` | BootstrapController, BootstrapService, ProcessDiscovery implementations, request processors |
| **context** | `mca-libraries/context/` | ProcessContext in the IOL schema |

---

## Architecture Overview

### End-to-End Process Flow

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                      CLIENT (Browser/App)                    │
                    └──────────┬───────────────────────────────────┬───────────────┘
                               │                                   │
                    POST /launchProcess              POST /router?processId=xxx
                    { launchId: "cardControlDash_v1" }   (obfuscated URI)
                               │                                   │
                    ┌──────────▼──────────────┐         ┌──────────▼──────────────┐
                    │  BootstrapController     │         │  Router (Secure Proxy)   │
                    │  ─────────────────────   │         │  ────────────────────    │
                    │  1. PreBootstrapInit      │         │  Request Processor Chain │
                    │  2. BootstrapService      │         │  ┌─────────────────────┐│
                    │     .createBootstrapCtx() │         │  │ DeobfuscateUri      ││
                    └──────────┬───────────────┘         │  │ ContextHeaders      ││
                               │                         │  │ Validation (OAS)    ││
                    ┌──────────▼──────────────┐          │  │ HostResolver        ││
                    │  ProcessDiscovery        │         │  │ DynamicLogging      ││
                    │  ─────────────────────   │         │  └─────────────────────┘│
                    │  1. getProcessMetadata()  │         └──────────┬──────────────┘
                    │  2. fetchJSON() via Router│                    │
                    │  3. Return ProcessDef     │         ┌──────────▼──────────────┐
                    └──────────┬───────────────┘         │  Backend Service         │
                               │                         │  /servicing/cardcontrol/ │
                    ┌──────────▼──────────────┐          │  .../{cardId}/policy     │
                    │  MCAV1ProcessDefinition   │         └─────────────────────────┘
                    │  ──────────────────────   │
                    │  1. Parse process.json    │
                    │  2. Obfuscate endpoint URIs│
                    │  3. Extract OAS spec      │
                    │  4. Build EndPoint map    │
                    │  5. Resolve UI module     │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │  ContextStore             │
                    │  (Secure Proxy module)    │
                    │  ──────────────────────   │
                    │  Store ContextData keyed  │
                    │  by processId             │
                    │  (EndPoints + IOLSchema   │
                    │   + OAS spec)             │
                    └──────────┬───────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │  BootstrapContext         │
                    │  (returned to client)     │
                    │  ──────────────────────   │
                    │  - processId              │
                    │  - launchId               │
                    │  - process (tasks/events) │
                    │  - module (JS bundle URL) │
                    │  - webRoots               │
                    │  - localeData             │
                    │  - meta, security, etc.   │
                    └──────────────────────────┘
```

### Module Dependency Graph

```
secure-proxy-core
    ├── secure-proxy-api          (interfaces + data model)
    │       ├── context           (IOLSchema, ProcessContext)
    │       └── core-exceptions   (GenericException hierarchy)
    ├── router-api                (Router, RequestProcessor, RequestData)
    ├── oas-validation            (OASRequestValidation)
    └── process-lib               (ClasspathResourceProcessService)
```

---

## Process.json: Structure and Field Reference

### Complete Structure

Process.json is loaded from the classpath at `processes/{processName}.json` (via `ClasspathResourceProcessService`) or fetched remotely via the Router (via `MCAProcessDiscovery`).

```json
{
  "process": {
    "id": "cardControlDash_v1",
    "uiModuleName": "card_control_dashboard",
    "metaDataPresent": "true",
    "endpoints": {
      "<endpointName>": {
        "uri": "/servicing/path/{pathParam}",
        "method": "GET|POST|PUT|DELETE",
        "contexts": ["CustomerContext", "AccountContext"],
        "excludeInjectionFields": ["fieldName"],
        "type": "mca1"
      }
    },
    "contentEndpoints": {
      "<contentName>": {
        "uri": "/content/path/{locale}",
        "method": "GET"
      }
    },
    "tasks": [
      {
        "id": "TASK_ID",
        "name": "Human-readable name",
        "view": { "src": "/route/path" },
        "events": [
          {
            "name": "eventName",
            "action": {
              "services": ["endpointName"],
              "transition": { "task-id": "OTHER_TASK" },
              "process": { "id": "CHILD_LAUNCH_ID", "framework": "jsmvc" }
            }
          }
        ]
      }
    ],
    "apiDefinition": {
      "schemas": { "<endpointName>": { "request": "<json-schema-string>" } },
      "oas": {
        "path": "oas/openapi.yaml",
        "version": "1.0.0",
        "content": "<populated-at-runtime>",
        "oasEnabled": "true"
      },
      "raml": { "src": "ramlFileName" }
    }
  },
  "mandatoryContext": "CustomerContext,AccountContext"
}
```

### Field Descriptions: `process` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | String | Yes | Unique process identifier, typically `{name}_v{version}` |
| `uiModuleName` | String | Yes | Name of the client-side JavaScript module (used to build bundle URL) |
| `metaDataPresent` | String/Boolean | No | Whether metadata endpoints should be included (`"true"`/`"false"`) |
| `endpoints` | Object | Yes | Map of endpoint name to endpoint definition (backend service calls) |
| `contentEndpoints` | Object | No | Map of CMS/content endpoint name to content endpoint definition |
| `tasks` | Array | Yes | Ordered list of task (screen/step) definitions forming the journey |
| `apiDefinition` | Object | No | API schema information (OAS, RAML, or inline JSON schemas) |

### Field Descriptions: `endpoints.<name>` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uri` | String | Yes | Real backend URI path. May contain path parameters `{paramName}` |
| `method` | String | Yes | HTTP method: `GET`, `POST`, `PUT`, `DELETE` |
| `contexts` | Array[String] | No | IOL context types to inject as headers when routing (e.g., `["CustomerContext", "AccountContext"]`) |
| `excludeInjectionFields` | Array[String] | No | Fields to exclude from context header injection |
| `type` | String | No | Endpoint type flag. Set to `"mca1"` for legacy MCA1-style endpoints |
| `requestSchema` | String | No | Reference to request schema name in `apiDefinition.schemas` |

### Field Descriptions: `contentEndpoints.<name>` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uri` | String | Yes | CMS/content service URI |
| `method` | String | No | Defaults to `GET`. HTTP method for content retrieval |

Content endpoints are treated as `cms` type and are registered with their real path (no obfuscation).

### Field Descriptions: `tasks[*]` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | String | Yes | Unique task identifier (e.g., `CARD_CONTROL_DASHBOARD`) |
| `name` | String | No | Human-readable task description |
| `view.src` | String | No | Client-side route path for this task |
| `events` | Array | Yes | List of events the UI can trigger from this task |

### Field Descriptions: `events[*]` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Event identifier (matched by UI event dispatch) |
| `action.services` | Array[String] | No | Endpoint names to invoke when this event fires |
| `action.transition.task-id` | String | No | Navigate to another task within the same process |
| `action.process.id` | String | No | Launch a child process (process chaining). The id becomes the child launchId |
| `action.process.framework` | String | No | Framework hint for child process (e.g., `"jsmvc"` for MCA1) |

---

## Process Discovery and Bootstrap Flow

### Step-by-Step Bootstrap Sequence

The bootstrap flow is initiated when a client calls the `/launchProcess` endpoint. The following sequence describes how a process is resolved, transformed, and returned.

```
1. Client sends POST /launchProcess
   Body: { "launchId": "cardControlDash_v1", "theme": "dark" }
   Headers: IOL context headers (X-UserContext, etc.)

2. BootstrapController receives request
   ├── PreBootstrapDataInitializer.initialize(request, launchProcess)
   └── BootstrapService.createBootstrapContext(launchProcess, iolSchema)

3. BootstrapService.initBootstrapContext()
   ├── Generate new processId via ProcessIdProvider
   ├── Clone/create IOL schema for this process instance
   │   ├── Set PID (Process Instance ID) in IOLSchema
   │   ├── Set SID (Session ID) from session IOLSchema
   │   ├── Set AID (Application ID / Launch ID)
   │   └── Set Correlation-ID
   ├── If parentProcessId provided:
   │   ├── Load parent ContextData from ContextStore
   │   ├── Authenticate context access (same user check)
   │   └── ProcessLevelIOLCreator.create() copies parent context
   ├── Validate IOL schema via IOLContextValidator
   └── Check entitlements via EntitlementProvider.authorize()

4. ProcessDiscovery.getProcess(processIOLSchema)
   ├── MCAProcessDiscovery.getProcessMetadata(iolSchema)
   │   ├── Resolve processJsonPath via ServiceDiscovery
   │   └── Query service definitions for backend hosts
   ├── MCAProcessDiscovery.prepareProcessJson()
   │   └── fetchJSON() via Router (HTTP GET to EPS service)
   └── Return MCAV1ProcessDefinition(processMetadata)

5. MCAV1ProcessDefinition.apply(bootstrapContext, contextData)
   ├── transform(launchId)
   │   ├── Parse endpoints from process JSON
   │   ├── For each endpoint:
   │   │   ├── Generate obfuscated URI: /mcaservice/{launchId}/{name}/{uuid}
   │   │   ├── Create EndPoint object (realPath, obfuscatedPath, method, contexts)
   │   │   ├── Replace URI in JSON with obfuscated path
   │   │   └── Extract request schema reference
   │   ├── Parse contentEndpoints (no obfuscation, type=cms)
   │   ├── Process checkout endpoints in tasks (child process links)
   │   ├── Extract OAS spec, version, and enabled flag
   │   └── Remove apiDefinition from client-facing JSON
   ├── Populate ContextData with EndPoint map
   ├── Populate ContextData with ServiceDefinitions
   ├── Set OAS spec and version in ContextData
   ├── Set process JSON in BootstrapContext
   ├── Set ClientSideModule (name + bundle URL)
   └── Set webRoots in BootstrapContext

6. BootstrapService stores ContextData in ContextStore (provided by Secure Proxy)
   Key: processId
   Value: ContextData (endPointDefinitions, iolSchema, oasSpec, ...)

7. BootstrapContext returned to client
   Contains: processId, launchId, tasks, obfuscated endpoints, module info
```

### Key Classes in the Bootstrap Flow

**Location:** `mca-libraries/secure-proxy-core/src/main/java/com/barclays/global/mca/libs/secureproxy/`

```
service/
└── BootstrapService.java          Orchestrates the entire bootstrap lifecycle

controller/
└── BootstrapController.java       REST endpoints: /launchProcess, /chainProcess, /ProcessComplete

repository/
├── MCAProcessDiscovery.java       Abstract base: fetches process JSON via Router
└── MCAV1ProcessDiscovery.java     Extends MCAProcessDiscovery with ServiceDiscovery integration
```

**Location:** `mca-libraries/secure-proxy-api/src/main/java/com/barclays/global/mca/libs/secureproxy/`

```
interfaces/
├── ProcessDiscovery.java          getProcess(IOLSchema) -> ProcessDefinition
├── ProcessDefinition.java         apply(BootstrapContext, ContextData)
├── ProcessIdProvider.java         Generate unique process instance IDs
└── ProcessLevelIOLCreator.java    Create/clone IOL schema for process instances

data/
├── LaunchProcess.java             Launch request: launchId, parentProcessId, theme, chaining flag
├── BootstrapContext.java          Returned to client: processId, launchId, process JSON, module info
├── ContextData.java               Stored in session: endPointDefinitions, iolSchema, oasSpec
├── EndPoint.java                  Single endpoint: realPath, obfuscatedPath, method, contexts
├── ProcessMetadata.java           Intermediate: serviceDefinitions, processJson, webRoots, flags
├── MCAV1ProcessDefinition.java    ProcessDefinition impl: transforms JSON, obfuscates, extracts OAS
├── ServiceDefinition.java         Backend host: protocol, host, port, contextPath
├── ClientSideModule.java          UI module: name, bundle URL(s), charset
└── BootstrapUrlMappings.java      Configurable URL mappings for bootstrap/chaining endpoints
```

---

## Process-lib Module: ClasspathResourceProcessService

### Purpose

The `process-lib` module provides a standalone mechanism to load process.json files from the classpath and serve them via REST. This is useful for local development and testing, or for EPS services that host their own process definitions.

### ProcessService Interface

**Location:** `mca-libraries/process-lib/src/main/java/com/barclays/global/mca/libs/process/service/ProcessService.java`

```java
public interface ProcessService {
    /**
     * Fetches the process definition in JSON format.
     *
     * @param processPath process-id which should be the filename
     * @return the JSON process definition as a String
     */
    Object retrieveProcess(String processPath);
}
```

### ClasspathResourceProcessService

**Location:** `mca-libraries/process-lib/src/main/java/com/barclays/global/mca/libs/process/service/impl/ClasspathResourceProcessService.java`

**Classpath Convention:**
```
src/main/resources/
└── processes/
    ├── cardControlDash_v1.json
    ├── exampleApp.json
    └── exampleChildMca2App.json
```

**Loading Behavior:**
1. Receives `processPath` (e.g., `cardControlDash_v1`)
2. Validates the path matches alphanumeric/hyphen/underscore pattern
3. Loads from classpath: `processes/{processPath}.json`
4. Parses JSON and enriches `apiDefinition`:
   - If OAS is configured and enabled: loads OAS spec content, version, and enabled flag via `OasProvider`
   - If RAML is configured: loads RAML content from classpath
   - Otherwise: builds inline schemas from `schema/{uri}.{method}.request.json` files
5. Validates mandatory config parameters
6. Returns JSON string

**Code Example -- retrieving a process:**

```java
@Autowired
private ProcessService processService;

public void loadProcess() {
    // Loads from classpath:processes/cardControlDash_v1.json
    String processJson = (String) processService.retrieveProcess("cardControlDash_v1");
}
```

---

## Endpoint Definitions and Routing

### How Endpoints Are Processed

Each entry in `process.endpoints` is transformed by `MCAV1ProcessDefinition` into an `EndPoint` object during bootstrap:

```
process.json endpoint entry:
{
  "getCardPolicy": {
    "uri": "/servicing/jserv/cardcontrol/cardpolicy",
    "method": "GET",
    "contexts": ["CustomerContext", "AccountContext", "CallerContext"]
  }
}

                    │ MCAV1ProcessDefinition.transform()
                    ▼

EndPoint object:
  realPath       = "/servicing/jserv/cardcontrol/cardpolicy"
  obfuscatedPath = "/mcaservice/cardControlDash_v1/getCardPolicy/a1b2c3d4-..."
  method         = "GET"
  contexts       = "CustomerContext,AccountContext,CallerContext"
  requestSchema  = null (or schema string if defined)
  endPointType   = null (or "mca1" if type was set)
```

### EndPoint Data Model

**Location:** `mca-libraries/secure-proxy-api/src/main/java/com/barclays/global/mca/libs/secureproxy/data/EndPoint.java`

```java
public class EndPoint implements Serializable {
    private String method;               // HTTP method
    private String obfuscatedPath;       // /mcaservice/{launchId}/{name}/{uuid}
    private String realPath;             // Actual backend URI
    private String contexts;             // Comma-separated IOL context types
    private String requestSchema;        // JSON schema for request validation
    private String excludeInjectionFields; // Fields to exclude from context injection
    private String endPointType;         // "mca1" for legacy, null for MCA2
}
```

### ContextData: Runtime Endpoint Registry

After bootstrap, `ContextData` is stored in the `ContextStore` (provided by the Secure Proxy module) keyed by `processId`. It acts as the runtime registry that the request processor chain uses to resolve incoming obfuscated URIs back to real endpoints.

**Location:** `mca-libraries/secure-proxy-api/src/main/java/com/barclays/global/mca/libs/secureproxy/data/ContextData.java`

```java
public class ContextData implements Serializable {
    // Obfuscated path -> EndPoint mapping
    private Map<String, EndPoint> endPointDefinition = new ConcurrentHashMap<>();

    // Context path -> ServiceDefinition mapping (backend host resolution)
    private Map<String, ServiceDefinition> contextServiceDefinition = new ConcurrentHashMap<>();

    // The IOL schema for this process instance
    private IOLSchema iolSchema;

    // OAS validation data
    private String oasSpec;
    private String oasVersion;
    private boolean oasEnabled;

    // Full URL to the process.json source
    private String processJsonPath;
}
```

---

## Task Definitions and Journey Flow

### Tasks as a State Machine

Tasks in process.json define the UI-side state machine for a journey. Each task represents a screen or step, and events define transitions between tasks, service calls, or child process launches.

```
                    ┌─────────────────────────────┐
                    │  CARD_CONTROL_DASHBOARD      │
                    │  view: /                     │
                    ├─────────────────────────────┤
                    │  Events:                     │
                    │  ├─ getCardPolicy  -> svc    │
                    │  ├─ blockCard      -> svc    │
                    │  ├─ lockCard       -> task:  │
                    │  │    UPDATE_LOCK_CONFIRM     │
                    │  └─ navigateToManageControls │
                    │       -> task: MANAGE_CONTROLS│
                    └───────┬───────────────┬──────┘
                            │               │
               ┌────────────▼───┐   ┌───────▼─────────────┐
               │ UPDATE_LOCK_   │   │ MANAGE_CONTROLS      │
               │ CONFIRM        │   │ view: /manage/{id}   │
               │ view: /confirm │   ├──────────────────────┤
               ├────────────────┤   │ Events:              │
               │ Events:        │   │ ├─ merchants -> task │
               │ ├─ saveSuccess │   │ ├─ spendLimit-> task │
               │ │   -> DASHBOARD│  │ ├─ notifs   -> task  │
               │ └─ cancel      │   │ ├─ blockCard -> svc  │
               │     -> DASHBOARD│  │ └─ back     -> task: │
               └────────────────┘   │     DASHBOARD        │
                                    └──────────────────────┘
```

### Event Action Types

Events define what happens when a user interacts with a task. There are three action types:

**1. Service Call** -- invoke a backend endpoint:
```json
{
  "name": "getCardPolicy",
  "action": {
    "services": ["getCardPolicy"]
  }
}
```

**2. Task Transition** -- navigate to another task in the same process:
```json
{
  "name": "navigateToManageControls",
  "action": {
    "transition": {
      "task-id": "MANAGE_CONTROLS"
    }
  }
}
```

**3. Child Process Launch** -- chain to another MCA process:
```json
{
  "name": "testChildMCA2",
  "action": {
    "process": {
      "id": "CHILD_APP_LAUNCH_ID",
      "framework": "jsmvc"
    }
  }
}
```

When a child process event is defined, `MCAV1ProcessDefinition` obfuscates the process id in the same way as endpoint URIs and registers it as a checkout `EndPoint`.

---

## Process Chaining: Parent-Child Composition

### Overview

Process chaining enables a parent journey to invoke a child journey, with the child inheriting the parent's IOL context. When the child completes, control returns to the parent.

### Chaining Endpoints

**Location:** `mca-libraries/secure-proxy-core/src/main/java/com/barclays/global/mca/libs/secureproxy/controller/BootstrapController.java`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/launchProcess` | POST/GET | Launch a new process (no parent) |
| `/chainProcess` | POST | Chain from current process to child process |
| `/ProcessComplete` | GET | Complete child process, return to parent |

### Chaining Flow

```
1. Parent process is running with processId = "proc-parent-123"

2. Client calls POST /chainProcess
   Body: {
     "launchId": "CHILD_LAUNCH_ID",
     "currentProcessId": "proc-parent-123",
     "mcaType": "MCA2"
   }

3. BootstrapController.chainMcaProcess()
   ├── Validates currentProcessId is present
   ├── Sets launchProcess.chaining = true
   └── Delegates to BootstrapService.createBootstrapContext()

4. BootstrapService.initBootstrapContext() [chaining path]
   ├── Load parent ContextData from ContextStore using currentProcessId
   ├── Get parent IOL schema
   ├── Set CHAINING_MCA2 attribute in IOL schema
   ├── Resolve real launchId from parent's EndPoint map
   │   (the obfuscated checkout URL maps to the real child launchId)
   ├── Set launch ID and correlation ID in IOL schema
   ├── Run process discovery with the chaining IOL schema
   ├── ProcessDefinition.apply() creates child bootstrap context
   ├── Child gets new processId but parent's IOL context
   └── Store child ContextData in ContextStore

5. Child process executes with its own processId and endpoints

6. Client calls GET /ProcessComplete?processId=proc-parent-123
   ├── BootstrapService resolves parent context
   ├── CheckoutAppFinder locates the parent's bootstrap context
   └── Returns parent BootstrapContext for resumption
```

### LaunchProcess Data Model

**Location:** `mca-libraries/secure-proxy-api/src/main/java/com/barclays/global/mca/libs/secureproxy/data/LaunchProcess.java`

```java
public class LaunchProcess {
    @NotNull(message = "launchId cannot be null")
    private String launchId;           // Target process identifier
    private String parentProcessId;    // Parent process for inheritance
    private String currentProcessId;   // Current process (for chaining)
    private String customProcessId;    // Custom process ID override
    private String theme;              // UI theme
    private String mcaType;            // "MCA2" or null for MCA1
    private boolean chaining;          // True when chaining
    private String storedStateId;      // For saved/resumed state
    private String launchType;         // "inline" or "iframe"
}
```

---

## URL Obfuscation

### Purpose

URL obfuscation hides real backend service paths from the client. The client only sees proxy URIs containing UUID tokens, preventing:
- Direct backend service invocation bypassing the secure proxy
- Information leakage about internal service architecture
- Endpoint tampering by modifying known URI patterns

### Obfuscation Mechanism

**Implemented in:** `MCAV1ProcessDefinition.createEndPointDefinition()`

**Pattern:**
```
Real Path:       /servicing/jserv/cardcontrol/cardpolicy
Obfuscated Path: /mcaservice/{launchId}/{endpointName}/{uuid}
Example:         /mcaservice/cardControlDash_v1/getCardPolicy/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Generation Logic:**
```java
String obfuscatedUri = "/mcaservice/%s/%s/%s".formatted(
    launchId,                         // e.g., "cardControlDash_v1"
    endpointName,                     // e.g., "getCardPolicy"
    UUID.randomUUID().toString()      // unique per bootstrap
);
```

### Deobfuscation at Runtime

When the client makes a service call using the obfuscated URI, the `DeobfuscateUriPreProcessor` restores the real path.

**Location:** `mca-libraries/secure-proxy-core/src/main/java/com/barclays/global/mca/libs/secureproxy/processors/eps/DeobfuscateUriPreProcessor.java`

```java
public class DeobfuscateUriPreProcessor extends MCAProcessAwareRequestProcessor {

    @Override
    protected void run(ContextData contextData, RequestData requestData) {
        String path = requestData.getIncomingRequestInfo().getUri();
        String epsContextPath = path.split("/")[1];

        if ("mcaservice".equals(epsContextPath)) {
            // Look up the EndPoint by the obfuscated path
            String restoredPath = getEndPointDefinition(requestData).getRealPath();
            requestData.getTargetRequestInfo().setUri(restoredPath);
        }
    }
}
```

**How it works:**
1. `MCAProcessAwareRequestProcessor.run()` loads `ContextData` using the `processId` from the request
2. It looks up the `EndPoint` by matching the incoming obfuscated URI against the `endPointDefinition` map
3. `DeobfuscateUriPreProcessor` reads the `EndPoint.realPath` and sets it as the target URI

### Disabling Obfuscation

Obfuscation can be disabled per launchId by configuring the `excludeObfuscationLaunchIds` list in `MCAProcessDiscovery`. When disabled, the real path is used directly in both the client-facing JSON and the endpoint map.

---

## Process-Aware Request Processing

### MCAProcessAwareRequestProcessor

**Location:** `mca-libraries/secure-proxy-core/src/main/java/com/barclays/global/mca/libs/secureproxy/processors/MCAProcessAwareRequestProcessor.java`

This is the abstract base class for all request processors that need access to process context. It extends `AbstractRequestProcessor` from the Router API and adds process-aware behavior.

**Core Behavior:**
```java
public abstract class MCAProcessAwareRequestProcessor extends AbstractRequestProcessor {

    private final ContextStore contextStore; // ContextStore is provided by the Secure Proxy module

    public void run(RequestData requestData) {
        // 1. Get processId from request params or headers
        String processId = getProcessId(requestData);

        // 2. Load ContextData from ContextStore (Secure Proxy)
        ContextData contextData = contextStore.get(processId, ContextData.class);

        // 3. Match incoming URI to EndPoint definition
        EndPoint endPoint = contextData.getEndPointDefinition(uri);

        // 4. Delegate to subclass
        run(contextData, requestData);
    }

    // Subclasses implement this
    protected void run(ContextData contextData, RequestData requestData) { }
}
```

### Request Processor Chain (EPS Routing)

When a client calls the router with an obfuscated URI, the request passes through an ordered chain of process-aware processors:

```
┌─────────────────────────────────────────────────────────────────┐
│ Request Processor Chain (ordered by processor order value)       │
│                                                                 │
│  1. ContextHeadersPreProcessor                                  │
│     ├── Load EndPoint for this request                          │
│     ├── Read contexts from EndPoint (e.g., "CustomerContext,    │
│     │   AccountContext") + default contexts from config          │
│     └── Inject matching IOL context headers into target request │
│                                                                 │
│  2. ValidationRequestPreProcessor                               │
│     ├── If OAS enabled for this process: validate against spec  │
│     ├── Otherwise: validate against inline JSON schema          │
│     └── On failure: throw RequestException (400 Bad Request)    │
│                                                                 │
│  3. DeobfuscateUriPreProcessor                                  │
│     ├── Check if URI starts with /mcaservice/                   │
│     ├── Look up EndPoint.realPath                               │
│     └── Replace target URI with real backend path               │
│                                                                 │
│  4. HostResolverPreProcessor                                    │
│     ├── Extract context path from URI                           │
│     ├── Look up ServiceDefinition for context path              │
│     ├── Resolve host URL (protocol://host:port)                 │
│     ├── If not found: try RuntimeHostProvider                   │
│     └── Set target host on request                              │
│                                                                 │
│  5. DynamicLoggingProviderPreProcessor                          │
│     ├── Check MDC for dynamic log level                         │
│     └── If present: add X-SystemContext header with DLL value   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Context Header Injection Example

For an endpoint defined with `"contexts": ["CustomerContext", "AccountContext", "CallerContext"]`, plus default contexts from configuration, the `ContextHeadersPreProcessor` adds:

```
X-CustomerContext: {"customerId":"C123","name":"John Doe",...}
X-AccountContext: {"accountId":"ACC001","accountType":"CHECKING",...}
X-CallerContext: {"callerId":"USER001",...}
X-SystemContext: {...}
X-UserContext: {...}
```

Only contexts matching the endpoint's `contexts` list and the default contexts list are injected.

---

## OAS Validation Integration

### Per-Process OAS Validation

Unlike the global `ValidationFilter` (filter-chain level), the `ValidationRequestPreProcessor` performs per-process OAS validation using the OpenAPI spec embedded in the process definition.

**Flow:**

```
1. During bootstrap, MCAV1ProcessDefinition extracts:
   - oasSpec (full OpenAPI YAML/JSON content)
   - oasVersion (spec version)
   - oasEnabled flag

2. These are stored in ContextData alongside endpoint definitions

3. At request time, ValidationRequestPreProcessor:
   a. Checks if OAS validation is enabled:
      - oasConfig.isEnabled() (global toggle)
      - contextData.isOasEnabled() (per-process flag)
      - contextData.getOasSpec() is not empty
      - launchId is in oasConfig.getAllLaunchIds()
   b. Creates or retrieves cached OASRequestValidation instance
      (keyed by processJsonPath + "#" + oasVersion)
   c. Validates: method, path, content-type, query params, request body
   d. If errors and blocking mode: throws RequestException (400)
   e. If errors and reporting mode: logs warnings, continues
   f. If validated: sets X-SchemaValidated header
```

**Fallback to JSON Schema Validation:**

If OAS validation is not applicable, the processor falls back to inline JSON schema validation:
```
1. Check if request is non-GET with application/json content type
2. Load requestSchema from EndPoint definition
3. Validate request body against the JSON schema
4. If invalid: throw RequestException (400)
```

### OAS Configuration Properties

```properties
# Global OAS validation toggle for the router-level processor
secure-proxy.oas.enabled=true
secure-proxy.oas.blockingMode=true
secure-proxy.oas.ignoreMissingSchema=false
secure-proxy.oas.excludedHeaders=X-Internal-Token,X-Trace-Id
secure-proxy.oas.launchIds=cardControlDash_v1,exampleApp
```

---

## Configuration Properties

### Bootstrap URL Mappings

```properties
# Primary bootstrap endpoint paths (up to 4 URL patterns supported)
secure-proxy.default.urlmappings.bootstrap=/launchProcess
secure-proxy.default.urlmappings.bootstrap[1]=/launchProcess/v2

# Chaining endpoint paths
secure-proxy.default.urlmappings.chaining=/chainProcess
secure-proxy.default.urlmappings.chaining[1]=/chainProcess/v2

# Router endpoint
secure-proxy.default.urlmappings.router=/router/*
```

### Default Context Injection

```properties
# Contexts injected into ALL routed requests (in addition to per-endpoint contexts)
secure-proxy.default.contexts=SystemContext,UserContext,CallerContext,LocaleContext,AID,Correlation-ID
```

### Obfuscation Control

```properties
# Launch IDs that should NOT have URL obfuscation applied
secure-proxy.excludeObfuscationLaunchIds=debugApp,testApp
```

### Process Discovery

```properties
# Service discovery for locating process.json host
service-locator.process-service.protocol=https
service-locator.process-service.host=process-service.internal
service-locator.process-service.port=443
service-locator.process-service.context-path=/api/v1
```

### OAS Validation (Router-Level)

```properties
secure-proxy.oas.enabled=true
secure-proxy.oas.blockingMode=true
secure-proxy.oas.ignoreMissingSchema=false
secure-proxy.oas.excludedHeaders=X-Internal-Token
secure-proxy.oas.launchIds=cardControlDash_v1,exampleApp
```

---

## Code Examples: Java Usage Patterns

### Example 1: Creating a Process.json File

Place the file at `src/main/resources/processes/myJourney_v1.json`:

```json
{
  "process": {
    "id": "myJourney_v1",
    "uiModuleName": "my-journey-module",
    "metaDataPresent": "true",
    "endpoints": {
      "getAccountSummary": {
        "uri": "/servicing/accounts/summary",
        "method": "GET",
        "contexts": ["CustomerContext", "AccountContext"]
      },
      "submitTransfer": {
        "uri": "/servicing/transfers",
        "method": "POST",
        "contexts": ["CustomerContext", "AccountContext", "ProcessContext"],
        "requestSchema": "submitTransfer"
      }
    },
    "tasks": [
      {
        "id": "ACCOUNT_SUMMARY",
        "name": "View Account Summary",
        "view": { "src": "/" },
        "events": [
          {
            "name": "loadSummary",
            "action": { "services": ["getAccountSummary"] }
          },
          {
            "name": "startTransfer",
            "action": { "transition": { "task-id": "TRANSFER_FORM" } }
          }
        ]
      },
      {
        "id": "TRANSFER_FORM",
        "name": "Make a Transfer",
        "view": { "src": "/transfer" },
        "events": [
          {
            "name": "submit",
            "action": { "services": ["submitTransfer"] }
          },
          {
            "name": "cancel",
            "action": { "transition": { "task-id": "ACCOUNT_SUMMARY" } }
          }
        ]
      }
    ],
    "apiDefinition": {
      "oas": {
        "path": "oas/openapi.yaml",
        "version": "1.0.0"
      }
    }
  }
}
```

### Example 2: Implementing Custom ProcessDiscovery

If you need a custom process resolution strategy (e.g., loading from a database or remote registry):

```java
public class RemoteProcessDiscovery extends MCAProcessDiscovery {

    private final MyProcessRegistry registry;

    public RemoteProcessDiscovery(Router router,
                                  List<String> excludeObfuscationLaunchIds,
                                  MyProcessRegistry registry) {
        super(router, excludeObfuscationLaunchIds);
        this.registry = registry;
    }

    @Override
    public ProcessMetadata getProcessMetadata(IOLSchema iolSchema) {
        String launchId = iolSchema.getAID();
        ProcessMetadata metadata = new ProcessMetadata();
        metadata.setProcessJsonPath(registry.getProcessPath(launchId));
        metadata.setServiceDefinitions(registry.getServiceDefs(launchId));
        return metadata;
    }
}
```

### Example 3: Launching a Process from the Client

```javascript
// POST /launchProcess
const response = await fetch('/launchProcess', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-UserContext': JSON.stringify(userContext),
        'X-CustomerContext': JSON.stringify(customerContext)
    },
    body: JSON.stringify({
        launchId: 'cardControlDash_v1',
        theme: 'dark'
    })
});

const bootstrapContext = await response.json();
// bootstrapContext.processId      -> unique process instance ID
// bootstrapContext.process.tasks  -> task definitions with obfuscated endpoints
// bootstrapContext.module.url     -> JS bundle URL to load
```

### Example 4: Making a Routed Service Call

After bootstrap, the client uses obfuscated URIs from the process definition:

```javascript
// The endpoint URI from bootstrapContext.process.endpoints.getCardPolicy.uri
// is already obfuscated: /mcaservice/cardControlDash_v1/getCardPolicy/a1b2c3d4-...

const response = await fetch('/router' + obfuscatedUri + '?processId=' + processId, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
});
```

The secure proxy router:
1. Extracts `processId` from query parameter
2. Loads `ContextData` from `ContextStore` (provided by the Secure Proxy module)
3. Runs the request processor chain (deobfuscate, inject headers, validate, resolve host)
4. Forwards to the real backend service

---

## ProcessContext in IOL

**Location:** `mca-libraries/context/src/main/java/com/barclays/global/mca/libs/context/data/ProcessContext.java`

`ProcessContext` is a simple key-value pair that is part of the IOL context hierarchy. It is used to pass process-specific data through the context propagation mechanism.

```java
public class ProcessContext implements Serializable {
    @NotNull
    @Pattern(regexp = "^[a-zA-Z0-9-]*$")
    private String key;

    @NotNull
    @Pattern(regexp = "^[a-zA-Z0-9 '.&/,-]*$")
    private String value;
}
```

When `"ProcessContext"` is listed in an endpoint's `contexts` array, the `ContextHeadersPreProcessor` includes the `X-ProcessContext` header in the outbound request to the backend service.

---

## Troubleshooting

### Issue: Bootstrap Returns 500 with "Process Not Found"

**Causes:**
- Process.json file is not at the expected classpath location
- ServiceDiscovery cannot resolve the process service host
- The EPS service returned a non-2xx response for the process JSON fetch

**Solution:**
```
1. Verify file exists at: src/main/resources/processes/{launchId}.json
2. Check ServiceDiscovery configuration (LDAP, Consul, or static config)
3. Enable DEBUG logging for com.barclays.global.mca.libs.secureproxy.repository
4. Check Router logs for the process JSON fetch request/response
```

### Issue: Request Returns 400 "Invalid Input Data" After OAS Validation

**Causes:**
- Request body does not match the OpenAPI schema
- Query parameters do not match expected types
- Content-Type header is missing or incorrect

**Solution:**
```
1. Review the OAS spec embedded in the process definition
2. Enable reporting-only mode: secure-proxy.oas.blockingMode=false
3. Check ValidationRequestPreProcessor logs for specific validation errors
4. Verify the endpoint's OAS path matches the real URI path
```

### Issue: "No Endpoint Found" During Deobfuscation

**Causes:**
- The obfuscated URI does not match any registered EndPoint in ContextData
- The processId in the request does not match the stored process instance
- The process session has expired from ContextStore

**Solution:**
```
1. Verify processId is correctly passed as query param or header
2. Check ContextStore TTL/expiration configuration
3. Enable DEBUG logging for DeobfuscateUriPreProcessor
4. Confirm the client is using the exact obfuscated URI from the bootstrap response
```

### Issue: Context Headers Not Propagated to Backend

**Causes:**
- The endpoint does not list required contexts in its `contexts` array
- Default contexts configuration is missing
- The IOL schema does not contain the expected context type

**Solution:**
```
1. Add required context types to the endpoint's "contexts" array in process.json
2. Verify secure-proxy.default.contexts includes system-level contexts
3. Check that the IOL schema was properly populated during bootstrap
```

---

## Quick Reference

### Process System Components

| Component | Class | Module | Purpose |
|-----------|-------|--------|---------|
| **ProcessService** | `ProcessService` | process-lib | Interface for process.json retrieval |
| **ClasspathResourceProcessService** | `ClasspathResourceProcessService` | process-lib | Loads process.json from classpath |
| **ProcessDiscovery** | `ProcessDiscovery` | secure-proxy-api | Interface: resolve IOLSchema to ProcessDefinition |
| **ProcessDefinition** | `ProcessDefinition` | secure-proxy-api | Interface: apply process definition to bootstrap/context |
| **MCAProcessDiscovery** | `MCAProcessDiscovery` | secure-proxy-core | Abstract base: fetches process JSON via Router |
| **MCAV1ProcessDiscovery** | `MCAV1ProcessDiscovery` | secure-proxy-core | Extends MCAProcessDiscovery with ServiceDiscovery |
| **MCAV1ProcessDefinition** | `MCAV1ProcessDefinition` | secure-proxy-api | Transforms process JSON, obfuscates URIs, extracts OAS |
| **BootstrapService** | `BootstrapService` | secure-proxy-core | Orchestrates full bootstrap lifecycle |
| **BootstrapController** | `BootstrapController` | secure-proxy-core | REST endpoints: launch, chain, complete |
| **BootstrapContext** | `BootstrapContext` | secure-proxy-api | Client-facing response: processId, tasks, module info |
| **ContextData** | `ContextData` | secure-proxy-api | Session-stored: EndPoint map, IOLSchema, OAS spec |
| **EndPoint** | `EndPoint` | secure-proxy-api | Single endpoint: real/obfuscated paths, method, contexts |
| **LaunchProcess** | `LaunchProcess` | secure-proxy-api | Launch request payload: launchId, parent, chaining flag |
| **ProcessMetadata** | `ProcessMetadata` | secure-proxy-api | Intermediate: serviceDefinitions, processJson, webRoots |
| **ProcessContext** | `ProcessContext` | context | IOL context key-value pair for process data propagation |
| **MCAProcessAwareRequestProcessor** | `MCAProcessAwareRequestProcessor` | secure-proxy-core | Base class for process-aware request processors |
| **DeobfuscateUriPreProcessor** | `DeobfuscateUriPreProcessor` | secure-proxy-core | Restores real path from obfuscated URI |
| **ContextHeadersPreProcessor** | `ContextHeadersPreProcessor` | secure-proxy-core | Injects IOL context headers per endpoint definition |
| **ValidationRequestPreProcessor** | `ValidationRequestPreProcessor` | secure-proxy-core | OAS and JSON schema validation per process |
| **HostResolverPreProcessor** | `HostResolverPreProcessor` | secure-proxy-core | Resolves backend host from ServiceDefinition |

### Process.json Filename Convention

```
src/main/resources/processes/{processName}.json
```

The `processName` must match the `launchId` used in the `LaunchProcess` request and must contain only alphanumeric characters, hyphens, and underscores.

### Key REST Endpoints

| Endpoint | Method | Controller | Purpose |
|----------|--------|------------|---------|
| `/launchProcess` | POST | BootstrapController | Launch a new process, return BootstrapContext JSON |
| `/launchProcess?launchId=...` | GET | BootstrapController | Launch process with HTML response (server-rendered) |
| `/chainProcess` | POST | BootstrapController | Chain from parent to child process |
| `/ProcessComplete?processId=...` | GET | BootstrapController | Complete child process, return to parent |
| `/bootstrapContext` | POST | BootstrapController | Internal forward for inline chaining |

**The Process System is the central orchestration layer that binds user journeys, backend services, security, and validation into a single declarative configuration.**
