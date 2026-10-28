# Agentic Routing Test Scenarios

Test specifications for `api-engineer-agentic-agent` routing logic.
These scenarios validate that `SPEC_TYPE` and `OPERATION` inputs are correctly normalised,
validated, and propagated to the appropriate workflow pipeline.

**Version:** 1.4.0
**Covers:** Step -1 (Normalize), Step 0 (Explicit Override), Step 4B/4I (Delegation)

---

## 1. Step -1: Input Normalisation

### TEST-N01: SPEC_TYPE lowercase normalisation
```
GIVEN:
  SPEC_TYPE: SMESH
  OPERATION: generate
  SPEC_PATH: /workspace/api/openapi.yaml
  OUTPUT_PATH: /workspace/output

WHEN: Step -1 runs

THEN:
  SPEC_TYPE normalised to "smesh"
  Routing proceeds to Step 0 with SPEC_TYPE=smesh
  Capability resolved: sMesh Generate
  Classification method: explicit-override-operation
```

### TEST-N02: SPEC_TYPE whitespace trimming
```
GIVEN:
  SPEC_TYPE: "  smesh  "
  OPERATION: generate
  SPEC_PATH: /workspace/api/openapi.yaml
  OUTPUT_PATH: /workspace/output

WHEN: Step -1 runs

THEN:
  SPEC_TYPE normalised to "smesh"
  Routing proceeds to Step 0
  Capability resolved: sMesh Generate
```

### TEST-N03: OPERATION lowercase normalisation
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: GENERATE
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step -1 runs

THEN:
  OPERATION normalised to "generate"
  Routing proceeds to Step 0.1
  Capability resolved: sMesh Generate
```

### TEST-N04: SPEC_TYPE absent defaults to auto
```
GIVEN:
  SPEC_TYPE: (absent)
  INTENT: "Generate a Spring Boot 3 project from an OpenAPI 3.x specification"
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step -1 runs

THEN:
  SPEC_TYPE set to "auto"
  Step 0 does not match (SPEC_TYPE is auto)
  Falls through to Step 1 for signal-based classification
```

### TEST-N05: Unsupported SPEC_TYPE fails fast
```
GIVEN:
  SPEC_TYPE: kubernetes

WHEN: Step -1 validation runs

THEN:
  Immediate error: INPUT VALIDATION FAILED: Unsupported SPEC_TYPE
  Provided: "kubernetes"
  Allowed: daf | smesh | auto
  Agent STOPS — does not proceed to Step 0
```

### TEST-N06: Unsupported OPERATION fails fast
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: deploy

WHEN: Step -1 validation runs

THEN:
  Immediate error: INPUT VALIDATION FAILED: Unsupported OPERATION
  Provided: "deploy"
  Allowed: generate | validate | refine | fix | design | update | verify | auto
  Agent STOPS
```

### TEST-N07: SPEC_TYPE "none" defaults to auto
```
GIVEN:
  SPEC_TYPE: "none"

WHEN: Step -1 runs

THEN:
  SPEC_TYPE set to "auto"
```

---

## 2. Step 0: Explicit Override Resolution

### TEST-O01: SPEC_TYPE smesh + OPERATION generate → sMesh Generate (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: generate
  SPEC_PATH: /workspace/api/openapi.yaml
  OUTPUT_PATH: /workspace/output
  JIRA_ID: COOAPIB2B-11749
  INTENT: "Generate a Spring Boot 3 project from an OpenAPI 3.x specification"

WHEN: Step 0.1 runs

THEN:
  Capability: sMesh Generate
  Classification method: explicit-override-operation
  Confidence: 100
  Step 1 is NEVER reached
  Proceeds to Step 2 (input validation)
```

### TEST-O02: SPEC_TYPE smesh + OPERATION validate → Spec Validate (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: validate
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 0.1 runs

THEN:
  Capability: Spec Validate
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O03: SPEC_TYPE smesh + OPERATION verify → OAS Verify (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: verify
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 0.1 runs

THEN:
  Capability: OAS Verify
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O04: SPEC_TYPE smesh + OPERATION refine → sMesh Refine (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: refine
  PROJECT_PATH: /workspace/my-project

WHEN: Step 0.1 runs

THEN:
  Capability: sMesh Refine
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O05: SPEC_TYPE smesh + OPERATION fix → Project Fix (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: fix
  PROJECT_PATH: /workspace/my-project

WHEN: Step 0.1 runs

THEN:
  Capability: Project Fix
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O06: SPEC_TYPE smesh + OPERATION update → OAS Update (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: update
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 0.1 runs

THEN:
  Capability: OAS Update
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O07: SPEC_TYPE smesh + OPERATION design → OAS Design (Step 0.1)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: design
  REQUIREMENTS_PATH: /workspace/requirements.md

WHEN: Step 0.1 runs

THEN:
  Capability: OAS Design
  Classification method: explicit-override-operation
  Confidence: 100
```

### TEST-O08: SPEC_TYPE daf + OPERATION auto → DAF Generate via keyword (Step 0.2)
```
GIVEN:
  SPEC_TYPE: daf
  OPERATION: auto
  INTENT: "Generate a DAF microservice for payment limits"
  SERVICE_SPEC_PATH: /workspace/spec.md

WHEN: Step 0.2 keyword matching runs

THEN:
  Capability: DAF Generate (keyword "daf" matches)
  Classification method: explicit-override-keyword
  Confidence: 100
  Step 1 is NEVER reached
```

### TEST-O09: SPEC_TYPE smesh + OPERATION auto + INTENT contains "generate" → sMesh Generate (Step 0.2)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: auto
  INTENT: "Generate a Spring Boot 3 project from an OpenAPI 3.x specification"
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 0.2 keyword matching runs

THEN:
  Capability: sMesh Generate (keyword "generate" matches "smesh + generate" row)
  Classification method: explicit-override-keyword
  Confidence: 100
```

### TEST-O10: SPEC_TYPE smesh + OPERATION auto + no keyword match → default sMesh Generate (Step 0.3)
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: auto
  INTENT: "Do something with the API"
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 0.2 keyword matching fails (no keywords match)
AND Step 0.3 default resolution runs

THEN:
  Capability: sMesh Generate (default for SPEC_TYPE=smesh)
  Classification method: explicit-override-default
  Confidence: 100
  Flags section notes: "SPEC_TYPE was set to 'smesh' but no OPERATION or INTENT keywords matched — defaulted to sMesh Generate."
  Step 1 is NEVER reached
```

### TEST-O11: SPEC_TYPE smesh NEVER falls through to Step 1
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: auto
  INTENT: "Help me with something"
  (No keywords match any row in Step 0.2)

WHEN: Step 0 processing completes

THEN:
  Step 0.3 catches this case — defaults to sMesh Generate
  Step 1 signal extraction NEVER runs
  Agent does NOT score DAF Generate or any other capability via signal extraction
```

### TEST-O12: SPEC_TYPE daf + no keywords → default DAF Generate (Step 0.3)
```
GIVEN:
  SPEC_TYPE: daf
  OPERATION: auto
  INTENT: "Help me build a service"
  SERVICE_SPEC_PATH: /workspace/spec.md

WHEN: Step 0.3 default resolution runs

THEN:
  Capability: DAF Generate (default for SPEC_TYPE=daf)
  Classification method: explicit-override-default
  Confidence: 100
```

---

## 3. Step 4B: sMesh Generate Delegation

### TEST-D01: sMesh Generate delegates through generate.md pipeline
```
GIVEN:
  Capability resolved: sMesh Generate
  SPEC_PATH: /workspace/api/openapi.yaml
  OUTPUT_PATH: /workspace/output
  JIRA_ID: COOAPIB2B-11749

WHEN: Step 4B executes

THEN:
  Executes commands/workflows/generate.md from Step 0
  Does NOT spawn project-generation-agent via Task() directly
  generate.md runs the full pipeline:
    Step 6: spec-parsing-agent → SPEC_ANALYSIS
    Step 6a: API classification detection
    Step 6b: Barclays standards validation
    Step 7: clarification-checkpoint-agent → CONFIG
    Step 8: project-generation-agent (with SPEC_ANALYSIS + CONFIG)
    Step 9: SDK integration
    Step 9a: Post-SDK compliance
    Step 10: Compilation
```

### TEST-D02: sMesh Generate passes --full-automation when FLAGS includes it
```
GIVEN:
  Capability resolved: sMesh Generate
  FLAGS: --full-automation

WHEN: Step 4B executes

THEN:
  --full-automation is passed to generate.md
  generate.md installs automation hooks (Step 0)
  clarification-checkpoint-agent uses defaults without prompting
```

### TEST-D03: sMesh Generate extracts structured params from ADDITIONAL_INPUT
```
GIVEN:
  Capability resolved: sMesh Generate
  ADDITIONAL_INPUT: "package=com.barclays.api artifact=busparsemgmt-xapi api-class=external db=no"

WHEN: Step 4B executes

THEN:
  --package com.barclays.api is passed to generate.md
  --artifact busparsemgmt-xapi is passed to generate.md
  --api-class external is passed to generate.md
  --db no is passed to generate.md
```

### TEST-D04: Generated SMESH project contains no DAF markers
```
GIVEN:
  Step 4B completed successfully for sMesh Generate

THEN:
  Generated project does NOT contain:
    - daf-starter Gradle plugin
    - daf-dependencies.gradle
    - @HeaderContract annotation
    - com.barclays.daf:* dependencies
  Generated project DOES contain:
    - SDK3 RestApiClient imports
    - RestResponse.assemble() pattern
    - Java Records for DTOs
    - ExternalApiInitializer or InternalApiInitializer bean
```

---

## 4. Step 4I: TDD Generate Delegation

### TEST-T01: TDD Generate delegates through tdd.md pipeline
```
GIVEN:
  Capability resolved: TDD Generate
  SPEC_PATH: /workspace/api/openapi.yaml
  OUTPUT_PATH: /workspace/output

WHEN: Step 4I executes

THEN:
  Executes commands/workflows/tdd.md from Step 0
  Does NOT spawn tdd-orchestrator-agent via Task() directly
  tdd.md runs the full pipeline:
    Step 3: spec-parsing-agent → SPEC_ANALYSIS
    Step 3a: API classification resolution
    Step 4: clarification-checkpoint-agent → CONFIG
    Step 6: tdd-orchestrator-agent (with SPEC_ANALYSIS + CONFIG)
```

---

## 5. Step 1: Signal-Based Classification (SPEC_TYPE=auto)

### TEST-S01: Auto classification routes to sMesh Generate with strong signals
```
GIVEN:
  SPEC_TYPE: auto
  INTENT: "Generate a Spring Boot 3 project from an OpenAPI 3.x specification"
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Step 1 runs

THEN:
  Signals: has_oas_spec (+40), kw_generate (+30), kw_spring_boot (+20), kw_openapi (+20)
  sMesh Generate score: 110 (threshold: 30) → PASS
  DAF Generate score: -40 (kw_openapi) -30 (kw_spring_boot) -20 (has_oas_spec) = -90 → FAIL threshold
  Winner: sMesh Generate
  Delegates to commands/workflows/generate.md pipeline
```

### TEST-S02: Auto classification routes to DAF Generate with strong signals
```
GIVEN:
  SPEC_TYPE: auto
  INTENT: "Generate a DAF microservice for payment limits"
  SERVICE_SPEC_PATH: /workspace/spec.md

WHEN: Step 1 runs

THEN:
  Signals: has_service_spec (+50), kw_daf (+40), kw_microservice (+30)
  DAF Generate score: 120 (threshold: 30) → PASS
  Winner: DAF Generate
```

---

## 6. Regression Tests

### TEST-R01: /create --type smesh path remains unchanged
```
GIVEN:
  User runs: /barclays-buk-api-engineer:create COOAPIB2B-11749 --type smesh --operation generate ./api.yaml --output ./output --package com.barclays.api --artifact busparsemgmt-xapi

WHEN: create.md processes the command

THEN:
  --type normalised to "smesh"
  Routes to Step 4B.3 → commands/workflows/generate.md
  No changes to create.md behavior
```

### TEST-R02: DAF Generate via agentic agent still works
```
GIVEN:
  SPEC_TYPE: daf
  OPERATION: auto
  INTENT: "Generate a DAF microservice"
  SERVICE_SPEC_PATH: /workspace/spec.md
  OUTPUT_PATH: /workspace/output

WHEN: Agentic agent processes inputs

THEN:
  Step 0.2 matches daf + keyword → DAF Generate
  Step 4A spawns daf-orchestrator-agent via Task (unchanged)
```

### TEST-R03: Spec Validate via agentic agent still works
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: validate
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Agentic agent processes inputs

THEN:
  Step 0.1 resolves smesh + validate → Spec Validate
  Step 4C spawns barclays-standards-validation-agent via Task (unchanged)
```

### TEST-R04: OAS Verify via agentic agent still works
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: verify
  SPEC_PATH: /workspace/api/openapi.yaml

WHEN: Agentic agent processes inputs

THEN:
  Step 0.1 resolves smesh + verify → OAS Verify
  Step 4D spawns verify-oas-agent via Task (unchanged)
```

### TEST-R05: Project Fix via agentic agent still works
```
GIVEN:
  SPEC_TYPE: smesh
  OPERATION: fix
  PROJECT_PATH: /workspace/my-project

WHEN: Agentic agent processes inputs

THEN:
  Step 0.1 resolves smesh + fix → Project Fix
  Step 4H spawns self-correcting-agent via Task (unchanged)
```

---

## 7. Parameter Propagation Tests

### TEST-P01: Agentic invocation produces equivalent internal request to /create
```
GIVEN (agentic):
  JIRA_ID: COOAPIB2B-11749
  SPEC_TYPE: smesh
  OPERATION: generate
  SPEC_PATH: ./busparsemgmt-xapi-1.0.001/openapi.yaml
  OUTPUT_PATH: busparsemgmt-xapi
  ADDITIONAL_INPUT: "package=com.barclays.api artifact=busparsemgmt-xapi version=1.0.0 db=no api-class=external"

GIVEN (equivalent /create):
  /barclays-buk-api-engineer:create COOAPIB2B-11749 --type smesh --operation generate
    ./busparsemgmt-xapi-1.0.001/openapi.yaml
    --output busparsemgmt-xapi
    --package com.barclays.api
    --artifact busparsemgmt-xapi
    --version 1.0.0
    --db no
    --api-class external

THEN:
  Both invocations execute commands/workflows/generate.md with identical parameters
  Both produce structurally equivalent sMesh projects
  No DAF markers in either output
```
