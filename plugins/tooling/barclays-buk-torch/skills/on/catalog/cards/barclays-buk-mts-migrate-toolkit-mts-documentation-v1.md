# barclays-buk-mts-migrate-toolkit-mts-documentation-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mts-migrate-toolkit-mts-documentation-v1` |
| Plugin name | `barclays-buk-mts-migrate-toolkit` |
| Component type | skill-user-only |
| Owner | MCA Core Engineering |
| Action scope | read-only |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-mts-migrate-toolkit@barclays-cio-buk |
| Native command | `/barclays-buk-mts-migrate-toolkit:mts-documentation` |
| Skill name | `mts-documentation` |

## Description

Generate MTS service documentation for any BUK Spring Boot codebase

## When to use

Use BEFORE mts-migrate to document all MTS mainframe service calls in a BUK Spring Boot codebase — scans for doService()/callService() patterns across 15 transport categories (mainframe-mq, SOAP, Oracle DB, DB2, CMOD, TCV hybrid, SCV, and others), extracts WMID/TDL mappings and DataGroup definitions, and produces per-service documentation files required for migration planning; NOT for services that contain no MTS calls or have already been migrated to REST.

## Inputs

- PROJECT_PATH (required, positional): path to the Spring Boot codebase root; must contain `build.gradle` or `pom.xml` and a `src/main/java` source tree with MTS transport dependencies (EBS/EGS JARs)

## Preconditions

- Plugin `barclays-buk-mts-migrate-toolkit` is installed with all sub-agents available
- Target project is a Spring Boot project containing MTS `doService()` or `callService()` integration points
- MTS transport dependencies (EBS/EGS JARs) are resolvable from the Gradle cache
- Git is initialized in the project (documentation output is written to the working tree)

## Expected outputs

- Per-service documentation files (one per discovered MTS service) listing:
  - All `doService()`/`callService()` call sites with class and method context
  - Transport category classification (one of 15 supported categories, e.g. `mainframe-mq`, `soap-stub`, `oracle-db-direct`)
  - WMID parameter to TDL table mappings for each call
  - DataGroup enum types and gateway method bindings
  - Write table extraction and orchestration sub-service TDL tracing
  - Migration complexity indicators (field count, transport type, hybrid flag)
  - API replacement candidates (populated in the subsequent `api-replacement-match` step)
- Summary overview document listing all discovered services, their transport categories, and complexity scores

## Exclusions

- Does NOT modify any source files — output is documentation only
- Does NOT perform API replacement matching — that is the responsibility of `api-replacement-match`
- Does NOT generate migration code — that is the responsibility of `mts-migrate`
- Does NOT document services classified as `already-api-rest` or `already-api-direct-http`

## Verification

Confirm that per-service documentation files have been created for every MTS service call site identified in the codebase, that each file contains the transport category classification and at least one WMID/TDL mapping entry, and that the summary overview lists a service count consistent with the number of `doService()`/`callService()` call sites visible in the source tree. No source files should be modified.
