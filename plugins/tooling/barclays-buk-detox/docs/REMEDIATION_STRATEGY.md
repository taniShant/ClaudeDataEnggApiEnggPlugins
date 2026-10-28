# CWE-937 Intelligent Remediation Strategy

## Overview

The SCA (Software Composition Analysis) remediation strategy implements a **priority-based, intelligent fallback chain** to automatically select the best remediation version for vulnerable dependencies.

## Decision Tree

```
Finding: Vulnerable Dependency
  │
  ├─ [STRATEGY 1] Wiz-Recommended Version
  │  ├─ Extract version from finding
  │  ├─ Validate JDK compatibility ✓
  │  ├─ Check Nexus availability ✓
  │  └─ Result: AUTO_APPLY with Wiz version
  │
  ├─ [STRATEGY 1b] Wiz "Latest" or No Explicit Version
  │  ├─ Nexus Search for latest stable
  │  ├─ Filter: JDK compatible + Remediation checks
  │  ├─ Validate all candidates
  │  └─ Result: AUTO_APPLY with searched version
  │
  ├─ [STRATEGY 2] safe-versions.json Pre-Validated
  │  ├─ Lookup package key in config
  │  ├─ Validate JDK compatibility ✓
  │  ├─ Check Nexus availability ✓
  │  └─ Result: AUTO_APPLY with safe version
  │
  └─ [STRATEGY 3] Manual Corrective Action
     ├─ All strategies exhausted
     ├─ Include fallback recommendations
     └─ Result: MANUAL review required
```

## Strategy Details

### Strategy 1: Wiz-Recommended Version

**When Used:**
- Wiz report explicitly provides a version recommendation
- Found in `description`, `solution`, or vulnerability details

**Validation Steps:**
1. **JDK Compatibility Check**: Ensure version works with project's JDK
   - BouncyCastle 1.85 → compatible with JDK 8, 11, 17, 21+
   - Log4j 2.24.0 → compatible with JDK 8+

2. **Nexus Availability Check**: Confirm version exists in internal Nexus
   - Queries `https://nexus.barcapint.com/nexus` API
   - Falls back to Nexus 2.x Lucene API if REST v3 unavailable

**Success Criteria:**
- ✓ JDK compatible
- ✓ Available in Nexus

**Example:**
```json
{
  "finding_id": "CVE-2026-59650",
  "remediation_strategy": "wiz_recommended",
  "selected_version": "org.bouncycastle:bcprov-jdk18on:1.85",
  "remediation_action": "auto_apply",
  "reason": "Wiz-recommended version 1.85 is JDK 17-compatible and available in Nexus"
}
```

---

### Strategy 1b: Nexus Search (Intelligent Alternative)

**When Used:**
- Wiz doesn't provide explicit version ("latest" or no version)
- Wiz version fails JDK compatibility or Nexus availability
- Need to find next suitable version autonomously

**Validation Steps:**
1. **Version Discovery**: List all available versions from Nexus
2. **Filtering**:
   - Must be newer than current vulnerable version (CVE remediation)
   - Exclude pre-release versions (alpha, beta, rc)
   - Must pass JDK compatibility check
   - Must be available in Nexus
3. **Selection**: Pick latest stable version meeting all criteria

**Success Criteria:**
- ✓ Newer than vulnerable version
- ✓ Stable (not pre-release)
- ✓ JDK compatible
- ✓ Available in Nexus

**Example:**
```json
{
  "finding_id": "CVE-2026-12860",
  "remediation_strategy": "nexus_search_latest",
  "selected_version": "org.bouncycastle:bcprov-jdk18on:1.88",
  "remediation_action": "auto_apply",
  "reason": "Wiz recommends upgrade to latest compatible version. Selected 1.88 from Nexus (JDK 17-compatible, stable)"
}
```

---

### Strategy 2: safe-versions.json Pre-Validated

**When Used:**
- Both Strategy 1 and 1b fail
- `safe-versions.json` has configuration for this package
- Pre-validated version proven to work in similar projects

**Validation Steps:**
1. **Config Lookup**: Extract safe version from `config/safe-versions.json`
2. **JDK Compatibility**: Check `compatible_jdk` list or assume compatible if not specified
3. **Nexus Availability**: Confirm safe version exists in Nexus
4. **Fallback Logic**: Already tested in projects like CLOUDITDECOUP, SALES

**Success Criteria:**
- ✓ JDK compatible (or not restricted)
- ✓ Available in Nexus
- ✓ Marked `nexus_confirmed: true` in config

**Example Configuration:**
```json
{
  "org.bouncycastle:bcprov-jdk15on": {
    "current_vulnerable": "1.60",
    "safe_version": "org.bouncycastle:bcprov-jdk18on:1.85",
    "strategy": "drop_in_replacement",
    "nexus_confirmed": true,
    "cves_patched": ["CVE-2026-59650", "CVE-2026-12860", ...],
    "tested_projects": ["CLOUDITDECOUP"]
  }
}
```

**Remediation Result:**
```json
{
  "finding_id": "CVE-2026-12816",
  "remediation_strategy": "safe_versions",
  "selected_version": "org.bouncycastle:bcprov-jdk18on:1.85",
  "remediation_action": "auto_apply",
  "reason": "Safe-versions.json entry: bcprov-jdk18on:1.85 is JDK 17-compatible and available in Nexus"
}
```

---

### Strategy 3: Manual Corrective Action

**When Used:**
- All three automated strategies exhausted
- No suitable version found anywhere
- Requires human judgment and testing

**Decision Criteria for Manual:**
- ✗ Wiz version not compatible with project JDK
- ✗ Wiz version not in Nexus and no suitable alternatives
- ✗ safe-versions.json missing or incompatible
- ✗ Nexus search returns no candidates

**Fallback Recommendations Included:**
- Links to CVE details
- Known compatible versions (if any)
- Suggested investigation steps
- Reference to similar projects if available

**Example:**
```json
{
  "finding_id": "CVE-2026-XXXX",
  "remediation_strategy": "no_suitable_version",
  "selected_version": null,
  "remediation_action": "manual",
  "reason": "Wiz-recommended version 3.0 requires JDK 21+ (project has JDK 17). No Nexus alternatives found. Requires vendor update or JDK upgrade.",
  "details": {
    "wiz_version": "3.0",
    "wiz_jdk_required": 21,
    "project_jdk": 17,
    "alternatives_searched": true,
    "safe_versions_entry": false
  }
}
```

---

## Configuration: safe-versions.json

Pre-validated safe versions for known vulnerable packages:

**File Location:**
```
${CLAUDE_PLUGIN_ROOT}/config/safe-versions.json   # inside the installed plugin, never the target repo
```

**Schema:**
```json
{
  "org.bouncycastle:bcprov-jdk15on": {
    "current_vulnerable": "1.60",
    "safe_version": "org.bouncycastle:bcprov-jdk18on:1.85",
    "strategy": "drop_in_replacement",
    "nexus_confirmed": true,
    "expires": "2027-03-22",
    "notes": "Detailed explanation...",
    "cves_patched": ["CVE-2026-59650", ...],
    "tested_projects": ["CLOUDITDECOUP", "SALES"],
    "requires_bridge": false,
    "requires_code_changes": false
  }
}
```

**Key Fields:**
- `current_vulnerable`: The vulnerable version this entry targets
- `safe_version`: The remediation version to upgrade to
- `strategy`: Type of upgrade (drop_in_replacement, in_place_upgrade, etc.)
- `nexus_confirmed`: Boolean - version must be verified available in Nexus before marking true
- `cves_patched`: List of CVEs fixed by this upgrade
- `tested_projects`: Real projects where this upgrade was validated
- `requires_code_changes`: Boolean - whether code changes needed after upgrade

---

## Implementation Example

### CLOUDITDECOUP Remediation

**Project Details:**
- JDK 17
- Java project (Gradle build)
- 36 SCA findings from Wiz report

**Remediation Results:**

| Package | Current | Remediated | Strategy | Status |
|---------|---------|------------|----------|--------|
| BouncyCastle | 1.60 | 1.85 | safe_versions | ✓ AUTO_APPLY |
| Log4j | 2.17.2 | 2.24.0 | safe_versions | ✓ AUTO_APPLY |
| (Other deps) | - | - | (various) | (varies) |

**Execution:**
```bash
# Run pipeline with Wiz report (20).json
/barclays-buk-detox:remediate \
  --repo C:\ROLB vul remed\CLOUDITDECOUP \
  --model opus \
  --wiz-report gl_wiz_sca_report (20).json

# Stages 0-3: Parse, classify, select strategies
# Stage 4: Apply fixes (24+ auto-apply, 12 manual)
# Stage 5-9: Validate, test, document, create MR
```

---

## Nexus Integration

### Connection Details
- **URL**: `https://nexus.barcapint.com/nexus/`
- **Auth**: Basic auth via `NEXUS_USER` and `NEXUS_PASSWORD` environment variables
- **API**: Nexus 2.x Lucene API (v3 falls back automatically)

### Querying for Availability
The NexusClient checks artifact availability:

```python
client = NexusClient("https://nexus.barcapint.com/nexus/", 
                    username="//ok7pe7",
                    password=os.environ["NEXUS_PASSWORD"])

# Check specific version
exists = client.check_artifact_exists("org.bouncycastle", "bcprov-jdk18on", "1.85")

# List all available versions
versions = client.list_available_versions("org.bouncycastle", "bcprov-jdk18on")
# Returns: ['1.88', '1.87', '1.86', '1.85', ...]
```

---

## JDK Compatibility Validation

Certain packages require specific JDK versions:

| Package | Min JDK | Max JDK | Notes |
|---------|---------|---------|-------|
| bcprov-jdk15on | 1.5 | 8 | End-of-life, migrate to jdk18on |
| bcprov-jdk18on | 8 | ∞ | Current, supports 8, 11, 17, 21+ |
| log4j-core 2.x | 8 | ∞ | 2.x supports Java 8+ |

---

## Troubleshooting

### Issue: "No suitable version found" (Manual Action Required)

**Possible Causes:**
1. Wiz version requires higher JDK than project has
   - Solution: Plan JDK upgrade or use alternative library
   
2. Wiz version not in Nexus and no alternatives
   - Solution: Add to safe-versions.json after testing
   
3. Package deprecated or no longer maintained
   - Solution: Evaluate replacement libraries

**Debug Steps:**
1. Check Nexus manually: `https://nexus.barcapint.com/nexus/`
2. Verify JDK in build file: `build.gradle` or `pom.xml`
3. Add to safe-versions.json after local testing
4. Re-run remediation pipeline

### Issue: "Nexus connection failed"

**Possible Causes:**
1. Network/VPN not connected
2. Credentials expired or incorrect
3. Nexus server down

**Solution:**
- Check: `NEXUS_USER` and `NEXUS_PASSWORD` env vars
- Test: `curl -u $NEXUS_USER:$NEXUS_PASSWORD https://nexus.barcapint.com/nexus/`
- Fallback: Remediation still works with hardcoded known-versions list

---

## Maintenance

### Updating safe-versions.json

When a new package needs pre-validated remediation:

1. **Test Locally**: Upgrade package in a development environment
2. **Validate**: Run full build, tests, security scans
3. **Add Entry**:
   ```json
   "org.new.package:library": {
     "current_vulnerable": "1.0",
     "safe_version": "2.0",
     "strategy": "in_place_upgrade",
     "nexus_confirmed": true,
     "cves_patched": ["CVE-2026-XXXX"],
     "tested_projects": ["PROJECT_NAME"],
     "requires_code_changes": false
   }
   ```
4. **Commit**: Update config and re-run pipelines

### Review Cadence
- **Quarterly**: Review all entries, update expiration dates
- **As-Needed**: Add new entries when remediation succeeds
- **Monthly**: Check Nexus for newer stable versions

---

## Related Documentation

- [CWE-937 Implementation Guide](./CWE-937.md)
- [DETOX Pipeline Overview](./DETOX_PIPELINE.md)
- [Nexus Client Documentation](../scripts/nexus/README.md)
- [JDK Compatibility Validator](../scripts/validators/jdk_compatibility.py)
