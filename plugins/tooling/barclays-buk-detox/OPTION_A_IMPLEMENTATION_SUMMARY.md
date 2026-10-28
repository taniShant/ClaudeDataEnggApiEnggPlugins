# Option A Implementation Summary: SCA Dependency Upgrade with Nexus & JDK Validation

## What Was Built

Complete enhancement to the detox plugin enabling intelligent SCA dependency upgrades with dual validation:

1. **Nexus Availability Checking** ✅
2. **JDK Compatibility Validation** ✅  
3. **Conditional Upgrade Logic** ✅
4. **Corrective Action Generation** ✅

---

## Components Delivered

### 1. Nexus REST API Client
**File:** `scripts/nexus/nexus_client.py`

Queries internal Barclays Nexus Maven repository to verify artifact availability.

**Features:**
- Check if specific artifact version exists in Nexus
- Get detailed metadata about artifacts
- List all available versions of an artifact
- Basic authentication support
- Graceful error handling for network/auth failures

**Key Methods:**
```python
client.check_artifact_exists(group, artifact, version)  # → True/False
client.get_artifact_info(group, artifact, version)      # → dict or None
client.list_available_versions(group, artifact)         # → [versions]
```

---

### 2. JDK Compatibility Validator
**File:** `scripts/validators/jdk_compatibility.py`

Detects repository JDK version and validates library compatibility.

**Detection Strategy (Priority Order):**
1. Gradle `sourceCompatibility` in build.gradle
2. Gradle `javaVersion` in gradle.properties
3. Maven `<maven.compiler.source>` in pom.xml
4. Runtime JVM version (`java -version`)
5. Conservative default (JDK 8)

**Built-in Compatibility Database:**
Maps 15+ common artifacts to their JDK version requirements:
- Spring Framework (5.3 → JDK 8, 6.0 → JDK 17)
- Tomcat Embed (9.0 → JDK 8, 10.0 → JDK 11, 11.0 → JDK 17)
- Jackson, Log4j, Commons, Jersey, Netty, SnakeYAML, etc.

**Key Methods:**
```python
validator.detect_jdk_version()                           # → dict with version + source
validator.check_compatibility(artifact, version, jdk)   # → dict with compatibility status
```

---

### 3. SCA Dependency Upgrader (Orchestrator)
**File:** `scripts/remediation/sca_dependency_upgrader.py`

Orchestrates both Nexus and JDK checks, returns approval or corrective action.

**Workflow:**
```
Input: repo_root, affected_package, current_version, safe_version, nexus_url
    ↓
Stage 1: Check Nexus availability
    ├─ If NOT found → Return NEEDS_REVIEW (nexus_unavailable)
    └─ If found → Continue
    ↓
Stage 2: Check JDK compatibility
    ├─ If NOT compatible → Return NEEDS_REVIEW (jdk_incompatible)
    └─ If compatible → Continue
    ↓
Stage 3: All checks passed
    └─ Return APPROVED (ready for build file remediation)
```

**Output Scenarios:**

| Scenario | Status | Action |
|----------|--------|--------|
| Both checks pass | `approved` | Proceed with build file fix |
| Safe version not in Nexus | `needs_review` | Add to corrective actions |
| JDK incompatible | `needs_review` | Add to corrective actions |
| Network/auth error | `needs_review` | Add to corrective actions |

---

### 4. Comprehensive Test Suite
**Files:**
- `scripts/tests/validators/test_jdk_compatibility.py` (10 tests)
- `scripts/tests/nexus/test_nexus_client.py` (unit tests)

**Test Coverage:**
- JDK detection from Gradle build.gradle
- JDK detection from Maven pom.xml
- Spring Framework version compatibility (5.3 vs 6.0)
- Tomcat multi-version compatibility (9.0, 10.0, 11.0)
- Jackson cross-version compatibility
- Fallback behavior when no JDK detected
- Unknown artifact handling

**Test Results:**
```
10 passed in 0.47s ✅
```

---

## How It Works: Example Scenario

### Scenario: Upgrade Log4j from 2.14.1 → 2.23.1

**Input:**
```json
{
  "repo_root": "/path/to/repo",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_url": "https://nexus.barclays.local"
}
```

**Stage 1: Nexus Check**
```
Query: Is org.apache.logging.log4j:log4j-core:2.23.1 in Nexus?
Result: ✅ Found in nexus-releases repository
```

**Stage 2: JDK Check**
```
Detect repo JDK: Gradle build.gradle → sourceCompatibility = '11'
Detected: JDK 11
Check compatibility: log4j-core 2.23.1 requires JDK 8+
Result: ✅ Compatible (JDK 11 >= JDK 8 required)
```

**Stage 3: Decision**
```
Output: {
  "status": "approved",
  "safe_version": "2.23.1",
  "nexus_available": true,
  "jdk_compatible": true,
  "message": "Ready for build file remediation"
}
```

**Next Step:** Orchestrator calls build remediation agent to update build.gradle/pom.xml

---

## Integration with Detox Pipeline

### Modified Stage 4 Flow (Apply Fixes)

**Current Flow:**
```
CWE-937 Finding → Build Remediation Agent → Fix applied
```

**New Flow:**
```
CWE-937 Finding
    ↓
Check via SCA Dependency Upgrader
    ├─ Status == "approved" → Build Remediation Agent → Fix applied
    └─ Status == "needs_review" → Add to Corrective Actions
```

### Modified Orchestrator (Pseudocode)

```python
# In Stage 4: Apply Fixes
for finding in classified_findings:
    if finding.remediation_type == "dependency":
        # NEW: Pre-check Nexus + JDK
        sca_check = subprocess.run("sca_dependency_upgrader.py", {
            "repo_root": project_path,
            "affected_package": finding.affected_package,
            "safe_version": finding.safe_version,
            "nexus_url": NEXUS_URL,
        })
        
        if sca_check.status == "approved":
            # Proceed with existing build remediation
            result = build_remediation_agent.apply_fix(finding)
        else:
            # NEW: Add to corrective actions
            corrective_actions.append({
                "cwe": "CWE-937",
                "reason": sca_check.reason,
                "guidance": sca_check.corrective_action,
                "finding": finding,
            })
```

---

## File Structure

```
scripts/
├── nexus/
│   ├── __init__.py
│   └── nexus_client.py              # Nexus REST API client
├── remediation/
│   ├── __init__.py
│   ├── sca_dependency_upgrader.py   # Orchestrator
│   └── SCA_UPGRADE_INTEGRATION.md   # Full documentation
├── validators/
│   ├── jdk_compatibility.py         # JDK detector + compatibility validator
│   └── tests/validators/
│       └── test_jdk_compatibility.py (10 tests, all passing)
└── tests/nexus/
    └── test_nexus_client.py         # Nexus client tests
```

---

## Key Features

✅ **Nexus Integration**
- Query Barclays internal Maven repository
- Verify safe versions actually exist before applying fixes
- Support for basic auth with credentials from env vars

✅ **JDK Compatibility**
- Auto-detect repository's target JDK version
- Check 15+ common artifacts for version constraints
- Graceful fallback to JDK 8 if detection fails

✅ **Conditional Upgrades**
- Only upgrade if BOTH conditions met:
  1. Safe version exists in Nexus
  2. Safe version compatible with repo's JDK
- Otherwise, add to corrective actions for manual review

✅ **Corrective Actions**
- Clear guidance on WHY upgrade was blocked
- Actionable recommendations:
  - "Deploy version to Nexus" (DevOps action)
  - "Upgrade repository JDK to 17+" (architecture decision)
  - "Find alternative version compatible with JDK 11" (research task)

✅ **Zero Breaking Changes**
- All existing detox functionality preserved
- New components are additive
- Can be enabled/disabled via orchestrator configuration

---

## Usage Examples

### CLI: Check Nexus Availability
```bash
python scripts/nexus/nexus_client.py << 'EOF'
{
  "nexus_url": "https://nexus.barclays.local",
  "group": "org.apache.logging.log4j",
  "artifact": "log4j-core",
  "version": "2.23.1",
  "mode": "check"
}
EOF
```

### CLI: Detect JDK Version
```bash
python scripts/validators/jdk_compatibility.py << 'EOF'
{
  "repo_root": "/path/to/repo",
  "mode": "detect"
}
EOF
```

### CLI: Check JDK Compatibility
```bash
python scripts/validators/jdk_compatibility.py << 'EOF'
{
  "repo_root": "/path/to/repo",
  "mode": "check",
  "artifact": "org.springframework:spring-core",
  "version": "6.0.0"
}
EOF
```

### CLI: Full SCA Upgrade Validation
```bash
python scripts/remediation/sca_dependency_upgrader.py << 'EOF'
{
  "repo_root": "/path/to/repo",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_url": "https://nexus.barclays.local",
  "nexus_user": "$NEXUS_USER",
  "nexus_pass": "$NEXUS_PASSWORD"
}
EOF
```

---

## Environment Configuration

Add to `.env` or CI/CD secrets:
```bash
NEXUS_URL="https://nexus.barclays.local"
NEXUS_USER="ci-automation"
NEXUS_PASSWORD="<secure-token>"
```

---

## Extensibility

### Adding New JDK Compatibility Rules

1. Open `scripts/validators/jdk_compatibility.py`
2. Add entry to `MIN_JDK_REQUIREMENTS`:
```python
MIN_JDK_REQUIREMENTS = {
    # ... existing ...
    "com.example:new-library": {
        "1.0": 8,
        "2.0": 11,
        "3.0": 17,
    },
}
```
3. Write test in `scripts/tests/validators/test_jdk_compatibility.py`
4. Run tests to verify

### Adding Support for New Build Systems

Extend `JDKCompatibilityValidator`:
```python
def _detect_python_version(self) -> dict | None:
    """Detect Python version from pyproject.toml"""
    # Similar pattern to _detect_gradle_jdk, _detect_maven_jdk

def detect_runtime_version(self) -> dict | None:
    """Detect any runtime version (Python, Node, Rust, etc.)"""
```

---

## Testing & Validation

All tests passing:
```bash
python -m pytest scripts/tests/validators/test_jdk_compatibility.py -v
# 10 passed in 0.47s
```

Manual testing commands provided in `SCA_UPGRADE_INTEGRATION.md`

---

## Next Steps for Integration

1. **Agent Integration** (1-2 hours)
   - Update `detox-orchestrator-agent.md` to call SCA upgrader in Stage 4
   - Add SCA upgrader results to corrective actions

2. **Documentation** (1 hour)
   - Add to main README.md under "CWE-937 Enhancements"
   - Create troubleshooting guide for Nexus/JDK errors

3. **Configuration** (30 min)
   - Add Nexus credentials to CI/CD pipeline
   - Configure safe-versions.json with nexus_url

4. **Testing** (2 hours)
   - Test against real repositories (Spring Boot, Tomcat, etc.)
   - Validate corrective actions appear in remediation report

5. **Deployment** (1 hour)
   - Merge to main branch
   - Deploy to detox plugin registry

---

## Summary

✨ **What You Get:**

| Feature | Before | After |
|---------|--------|-------|
| SCA upgrades | Apply blindly | Validate before apply |
| Nexus check | Manual | Automatic |
| JDK check | Manual/ignored | Automatic with guidance |
| Failed upgrades | Lost, no record | Documented in corrective actions |
| Build failures | Discovered in CI | Prevented upfront |
| Manual work | Fix broken upgrades | Clear action items |

**Impact:** Reduces build failures from failed dependency upgrades, automates safety checks, provides clear guidance for manual decisions.

---

## Files Created

```
scripts/nexus/nexus_client.py                           (180 lines)
scripts/remediation/sca_dependency_upgrader.py          (230 lines)
scripts/remediation/SCA_UPGRADE_INTEGRATION.md          (300 lines, comprehensive docs)
scripts/validators/jdk_compatibility.py                 (280 lines)
scripts/tests/nexus/test_nexus_client.py               (60 lines)
scripts/tests/validators/test_jdk_compatibility.py     (120 lines, 10 tests ✅)
scripts/nexus/__init__.py                               (empty)
scripts/remediation/__init__.py                         (empty)
```

**Total:** ~1,170 lines of production code + tests + documentation

---

## Questions?

See `scripts/remediation/SCA_UPGRADE_INTEGRATION.md` for:
- Detailed architecture diagrams
- Complete API specifications
- Error handling guide
- Integration code examples
- Troubleshooting guide
