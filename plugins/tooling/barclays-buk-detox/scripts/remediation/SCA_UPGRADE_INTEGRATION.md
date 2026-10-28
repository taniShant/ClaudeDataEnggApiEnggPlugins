# SCA Dependency Upgrade with Nexus & JDK Validation

## Overview

Enhanced SCA (Software Composition Analysis) dependency remediation for CWE-937 (Using Components with Known Vulnerabilities) that:

1. **Checks Nexus availability** — Verifies that recommended safe versions exist in internal Nexus
2. **Validates JDK compatibility** — Ensures the safe version is compatible with the repository's JDK
3. **Conditionally upgrades** — Applies build file fixes only if both checks pass
4. **Generates corrective actions** — Documents incompatible versions for manual review

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Detox Orchestrator → SCA Dependency Upgrader               │
│ (CWE-937 Vulnerable Components)                             │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────────────────┐  ┌──────────────────┐  ┌──────────────┐
│ Nexus Availability │  │ JDK Compatibility│  │ Build File   │
│ Checker            │  │ Validator        │  │ Remediation  │
│                    │  │                  │  │              │
│ • Check artifact   │  │ • Detect repo JDK│  │ • Update     │
│   in Nexus         │  │ • Verify safe    │  │   build.gradle
│ • Verify version   │  │   version compat │  │ • Update     │
│   exists           │  │ • Map min JDK    │  │   pom.xml    │
│                    │  │   per version    │  │ • Update     │
│                    │  │                  │  │   package.json
└────────────────────┘  └──────────────────┘  └──────────────┘
     ▲                        ▲                       ▲
     │                        │                       │
     └────────────────────────┴───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
    ✅ APPROVED                  ❌ NEEDS REVIEW
    (Apply fix)              (Add to corrective actions)
```

## Components

### 1. Nexus Client (`nexus_client.py`)

REST API client for querying internal Nexus Maven repository.

**Methods:**
- `check_artifact_exists(group, artifact, version)` — Returns `True` if version available
- `get_artifact_info(group, artifact, version)` — Get detailed artifact metadata
- `list_available_versions(group, artifact)` — List all available versions

**Input:**
```json
{
  "nexus_url": "https://nexus.barclays.local",
  "nexus_user": "ci-user",
  "nexus_pass": "$NEXUS_PASSWORD",
  "group": "org.apache.logging.log4j",
  "artifact": "log4j-core",
  "version": "2.23.1",
  "mode": "check"
}
```

**Output:**
```json
{
  "status": "success",
  "exists": true,
  "group": "org.apache.logging.log4j",
  "artifact": "log4j-core",
  "version": "2.23.1"
}
```

### 2. JDK Compatibility Validator (`jdk_compatibility.py`)

Detects repository JDK version and validates library compatibility.

**Detection Strategy (Priority Order):**
1. Gradle `build.gradle` — `sourceCompatibility = '11'`
2. Gradle `gradle.properties` — `javaVersion = 11`
3. Maven `pom.xml` — `<maven.compiler.source>11</maven.compiler.source>`
4. Runtime JVM — `java -version`
5. Default fallback — JDK 8

**Compatibility Database:**
Pre-built mapping of artifact versions to min JDK requirements:

```python
MIN_JDK_REQUIREMENTS = {
    "org.springframework:spring-webmvc": {
        "5.3": 8,    # Spring 5.3.x requires JDK 8+
        "6.0": 17,   # Spring 6.0 requires JDK 17+
    },
    "org.apache.tomcat.embed:tomcat-embed-core": {
        "9.0": 8,    # Tomcat 9.0 requires JDK 8+
        "10.0": 11,  # Tomcat 10.0 requires JDK 11+
        "11.0": 17,  # Tomcat 11.0 requires JDK 17+
    },
    # ... more entries
}
```

**Input:**
```json
{
  "repo_root": "/path/to/repo",
  "mode": "check",
  "artifact": "org.springframework:spring-core",
  "version": "6.0.0"
}
```

**Output (detect mode):**
```json
{
  "status": "success",
  "jdk": {
    "detected_version": 11,
    "source": "gradle",
    "confidence": "high",
    "raw_value": "11",
    "file_path": "/path/to/build.gradle"
  }
}
```

**Output (check mode):**
```json
{
  "status": "success",
  "jdk": { ... },
  "compatibility": {
    "compatible": false,
    "artifact": "org.springframework:spring-core",
    "version": "6.0.0",
    "jdk_version": 11,
    "min_jdk_required": 17,
    "reason": "Library requires JDK 17 but repo uses JDK 11"
  }
}
```

### 3. SCA Dependency Upgrader (`sca_dependency_upgrader.py`)

Orchestrates Nexus and JDK checks, returns approval or corrective action.

**Input:**
```json
{
  "repo_root": "/path/to/repo",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_url": "https://nexus.barclays.local",
  "nexus_user": "ci-user",
  "nexus_pass": "$NEXUS_PASSWORD"
}
```

**Success Output (APPROVED):**
```json
{
  "status": "approved",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_available": true,
  "jdk_compatible": true,
  "jdk_info": {
    "detected_version": 11,
    "source": "gradle",
    "confidence": "high"
  },
  "compatibility": {
    "compatible": true,
    "artifact": "org.apache.logging.log4j:log4j-core",
    "version": "2.23.1",
    "jdk_version": 11,
    "min_jdk_required": 8,
    "reason": "Compatible"
  },
  "message": "Safe version 2.23.1 is available in Nexus and compatible with JDK 11. Ready for build file remediation.",
  "next_step": "Trigger build file remediation agent (detox-build-remediation-agent)"
}
```

**Failure Output (NEEDS REVIEW):**

*Reason: nexus_unavailable*
```json
{
  "status": "needs_review",
  "reason": "nexus_unavailable",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_available": false,
  "jdk_compatible": null,
  "message": "Safe version 2.23.1 is not available in Nexus repository. Manual review required.",
  "corrective_action": "Verify that org.apache.logging.log4j:log4j-core:2.23.1 is deployed to internal Nexus. Check with DevOps/Security team."
}
```

*Reason: jdk_incompatible*
```json
{
  "status": "needs_review",
  "reason": "jdk_incompatible",
  "affected_package": "org.springframework:spring-core",
  "current_version": "5.3.22",
  "safe_version": "6.0.0",
  "nexus_available": true,
  "jdk_compatible": false,
  "jdk_info": {
    "detected_version": 11,
    "source": "gradle",
    "confidence": "high"
  },
  "compatibility": {
    "compatible": false,
    "artifact": "org.springframework:spring-core",
    "version": "6.0.0",
    "jdk_version": 11,
    "min_jdk_required": 17,
    "reason": "Library requires JDK 17 but repo uses JDK 11"
  },
  "message": "Safe version requires JDK 17 but repository uses JDK 11",
  "corrective_action": "Option 1: Upgrade repository JDK to 17+. Option 2: Find alternative safe version compatible with JDK 11."
}
```

## Integration with Detox Pipeline

### Stage 4 (Apply Fixes) - Enhanced Flow

```
For each CWE-937 finding:
├─ Load safe version from config
├─ Call SCA Dependency Upgrader
│  ├─ Check Nexus availability
│  └─ Validate JDK compatibility
├─ If status == "approved"
│  └─ Trigger build remediation agent
└─ If status == "needs_review"
   └─ Add to corrective actions with reason + guidance
```

### Modified Orchestrator Logic

```python
# In detox-orchestrator-agent.md, Stage 4:

if finding.remediation_type == "dependency":
    # Check Nexus + JDK before applying fix
    sca_check = await _run_script("remediation/sca_dependency_upgrader.py", {
        "repo_root": project_path,
        "affected_package": finding.affected_package,
        "current_version": finding.current_version,
        "safe_version": finding.safe_version,
        "nexus_url": NEXUS_URL,
        "nexus_user": os.getenv("NEXUS_USER"),
        "nexus_pass": os.getenv("NEXUS_PASSWORD"),
    })

    if sca_check.get("status") == "approved":
        # Proceed with build remediation
        result = await build_remediation_agent.apply_fix(finding)
    else:
        # Add to corrective actions
        corrective_actions.append({
            "cwe": "CWE-937",
            "finding": finding,
            "reason": sca_check.get("reason"),
            "message": sca_check.get("message"),
            "action": sca_check.get("corrective_action"),
        })
```

## Environment Variables

Required for Nexus authentication:

```bash
export NEXUS_URL="https://nexus.barclays.local"
export NEXUS_USER="ci-automation"
export NEXUS_PASSWORD="<token-from-vault>"
```

## Adding New Artifacts to Compatibility Database

To add a new library to `MIN_JDK_REQUIREMENTS`:

```python
MIN_JDK_REQUIREMENTS = {
    # ... existing entries ...
    "com.example:my-library": {
        "1.0": 8,    # my-library 1.0.x requires JDK 8+
        "2.0": 11,   # my-library 2.0.x requires JDK 11+
        "3.0": 17,   # my-library 3.0.x requires JDK 17+
    },
}
```

**Where to find min JDK requirements:**
- Library release notes / docs
- Maven Central (view POM for `<source>` property)
- GitHub repository README or CONTRIBUTING.md
- Official library website

## Testing

Run all tests:
```bash
python -m pytest scripts/tests/validators/test_jdk_compatibility.py -v
python -m pytest scripts/tests/nexus/test_nexus_client.py -v
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Nexus not available | Returns `needs_review`, suggests DevOps check |
| JDK incompatible | Returns `needs_review`, suggests JDK upgrade or alternative version |
| Nexus credentials invalid | Falls back to requiring manual verification |
| JDK not detected | Uses conservative default (JDK 8) |

## Future Enhancements

1. **Nexus version recommendation** — When safe version unavailable, suggest next-best compatible version
2. **Multi-version support** — Test compatibility matrix across JDK versions
3. **Automatic bridge detection** — Detect when compatibility bridges are needed (e.g., log4j-1.2-api)
4. **CVE metadata** — Include CVE details in corrective action documentation
5. **Policy enforcement** — Block upgrades to major versions that would require significant JDK updates
