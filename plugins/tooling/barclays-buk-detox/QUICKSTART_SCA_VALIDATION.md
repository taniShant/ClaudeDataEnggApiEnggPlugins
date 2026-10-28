# Quick Start: SCA Dependency Upgrade with Nexus & JDK Validation

## 30-Second Overview

The detox plugin now automatically validates SCA (dependency) upgrades before applying them:

1. **Checks if the safe version exists in Nexus**
2. **Checks if it's compatible with your repository's JDK**
3. **Only applies the upgrade if both checks pass**
4. **Documents incompatible upgrades for manual review**

## Installation (Already Done ✅)

All components are in place:

```
scripts/nexus/nexus_client.py                    # Nexus querier
scripts/validators/jdk_compatibility.py          # JDK detector & validator
scripts/remediation/sca_dependency_upgrader.py   # Orchestrator
```

## Quick Test

### 1. Detect Your Repository's JDK

```bash
python scripts/validators/jdk_compatibility.py << 'EOF'
{
  "repo_root": ".",
  "mode": "detect"
}
EOF
```

**Output Example:**
```json
{
  "jdk": {
    "detected_version": 11,
    "source": "gradle",
    "confidence": "high",
    "file_path": "./build.gradle"
  }
}
```

### 2. Check if a Safe Version is Compatible

```bash
python scripts/validators/jdk_compatibility.py << 'EOF'
{
  "repo_root": ".",
  "mode": "check",
  "artifact": "org.springframework:spring-core",
  "version": "6.0.0"
}
EOF
```

**Output Example:**
```json
{
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

### 3. Full Validation (What the Pipeline Uses)

```bash
python scripts/remediation/sca_dependency_upgrader.py << 'EOF'
{
  "repo_root": ".",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_url": "https://nexus.barclays.local",
  "nexus_user": "your-user",
  "nexus_pass": "your-token"
}
EOF
```

**Output if APPROVED:**
```json
{
  "status": "approved",
  "safe_version": "2.23.1",
  "nexus_available": true,
  "jdk_compatible": true,
  "message": "Safe version 2.23.1 is available in Nexus and compatible with JDK 11. Ready for build file remediation."
}
```

**Output if BLOCKED (needs review):**
```json
{
  "status": "needs_review",
  "reason": "jdk_incompatible",
  "message": "Safe version requires JDK 17 but repository uses JDK 11",
  "corrective_action": "Option 1: Upgrade repository JDK to 17+. Option 2: Find alternative safe version compatible with JDK 11."
}
```

## How It Fits Into Detox Pipeline

```
When detox finds a vulnerable dependency (CWE-937):

1. Load safe version from safe-versions.json ✓ (existing)
2. Check if safe version is in Nexus              ← NEW
3. Check if safe version is JDK-compatible        ← NEW
4. If both checks pass → Apply fix to build file ✓ (existing)
5. If either check fails → Add to corrective actions
```

## Common Scenarios

### ✅ Scenario 1: Safe Version Approved

**Situation:** Upgrading log4j 2.14.1 → 2.23.1
- Nexus check: ✅ Version 2.23.1 found
- JDK check: ✅ Compatible with repo's JDK 11

**Result:** Fix applied automatically

**Corrective Actions:** None

---

### ❌ Scenario 2: Version Not in Nexus

**Situation:** Upgrading Spring to 5.3.40 (not released yet)
- Nexus check: ❌ Version not found
- JDK check: Skipped (no point checking unavailable version)

**Result:** Fix blocked

**Corrective Action:** "Verify that org.springframework:spring-core:5.3.40 is deployed to internal Nexus. Check with DevOps/Security team."

**What to do:** Ping DevOps, or choose an available version (e.g., 5.3.39)

---

### ❌ Scenario 3: Incompatible with Repository JDK

**Situation:** Upgrading Spring to 6.0.0, but repo uses JDK 11
- Nexus check: ✅ Version 6.0.0 found
- JDK check: ❌ Spring 6.0 requires JDK 17+

**Result:** Fix blocked

**Corrective Action:** "Library requires JDK 17 but repo uses JDK 11. Option 1: Upgrade repository JDK to 17+. Option 2: Find alternative safe version compatible with JDK 11."

**What to do:**
- Option A: Upgrade repo's JDK (gradle.properties, pom.xml, etc.) — architectural decision
- Option B: Use Spring 5.3.39 instead (JDK 8+ compatible) — lower risk

---

## Configuration

### Environment Variables (For CI/CD)

```bash
export NEXUS_URL="https://nexus.barclays.local"
export NEXUS_USER="ci-automation"
export NEXUS_PASSWORD="<token-from-vault>"
```

### Safe Versions File (Already Configured ✓)

`config/safe-versions.json` contains:
- Pre-validated safe versions from Barclays team
- Nexus confirmation (`nexus_confirmed: true`)
- Related artifacts (Jackson, Jersey, Log4j)
- Special migration cases (Log4j 1.x → 2.x)

To add new safe versions, update `config/safe-versions.json`:

```json
{
  "versions": {
    "com.example:my-lib": {
      "current_vulnerable": "1.0.0",
      "safe_version": "1.1.0",
      "strategy": "in_place_upgrade",
      "nexus_confirmed": true,
      "expires": "2026-12-31",
      "notes": "Patches CVE-2024-12345",
      "requires_bridge": false,
      "requires_code_changes": false
    }
  }
}
```

## Extending JDK Compatibility Database

Add libraries to `MIN_JDK_REQUIREMENTS` in `scripts/validators/jdk_compatibility.py`:

```python
MIN_JDK_REQUIREMENTS = {
    # ... existing ...
    "com.example:my-library": {
        "1.0": 8,      # my-library 1.x requires JDK 8+
        "2.0": 11,     # my-library 2.x requires JDK 11+
        "3.0": 17,     # my-library 3.x requires JDK 17+
    },
}
```

Then add a test:
```python
def test_check_compatibility_my_library(self):
    validator = JDKCompatibilityValidator(".")
    result = validator.check_compatibility(
        "com.example:my-library", "3.0.0", 11
    )
    self.assertFalse(result["compatible"])
    self.assertEqual(result["min_jdk_required"], 17)
```

Run tests:
```bash
python -m pytest scripts/tests/validators/test_jdk_compatibility.py -v
```

## Troubleshooting

### "Nexus not found" Error

**Cause:** Nexus server unreachable or credentials invalid

**Fix:**
1. Check Nexus URL is correct: `https://nexus.barclays.local`
2. Check credentials in env vars
3. Test manually: `curl -u $NEXUS_USER:$NEXUS_PASSWORD https://nexus.barclays.local/service/rest/v1/search`

### "JDK not detected" Warning

**Cause:** Repository doesn't have explicit JDK version set

**Result:** Uses conservative default (JDK 8)

**Fix:** Add explicit JDK version:
- **Gradle:** Add to build.gradle: `sourceCompatibility = '11'`
- **Maven:** Add to pom.xml: `<maven.compiler.source>11</maven.compiler.source>`

### "Incompatible with JDK" Error

**Cause:** Safe version requires newer JDK than repository uses

**Options:**
1. Upgrade repository JDK (architectural change)
2. Find alternative compatible version
3. Mark as accepted risk (manual security review)

## Next Steps

1. **Run full detox pipeline** (includes new SCA validation):
   ```bash
   /barclays-buk-detox:remediate --repo . --model opus --wiz-report ./report.json --jira PROJ-1234
   ```

2. **Check corrective actions** for any blocked dependency upgrades

3. **Review decisions** with security team for incompatible versions

4. **Update safe-versions.json** when new validated safe versions become available

## Full Documentation

- **Architecture & Design:** `scripts/remediation/SCA_UPGRADE_INTEGRATION.md`
- **Implementation Summary:** `OPTION_A_IMPLEMENTATION_SUMMARY.md`
- **API Specification:** `scripts/remediation/SCA_UPGRADE_INTEGRATION.md`

## Questions?

Refer to:
- JDK detection: See `scripts/validators/jdk_compatibility.py` (lines 50-100)
- Nexus integration: See `scripts/nexus/nexus_client.py` (lines 1-80)
- Full workflow: See `scripts/remediation/sca_dependency_upgrader.py`
