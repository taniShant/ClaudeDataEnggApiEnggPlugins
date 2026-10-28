# CWE-937 Skill Update: Nexus & JDK Validation Integration

## Summary

Updated the CWE-937 (Vulnerable Components) skill to integrate Nexus availability and JDK compatibility checks BEFORE applying dependency upgrades.

## What Changed

### Old Flow
```
Wiz SCA Finding (safe_version: "2.23.1")
    ↓
Apply fix directly to build.gradle
    ↓
[Later] Build fails: "version not found in Nexus"
        or "requires JDK 17 but repo uses JDK 11"
```

### New Flow
```
Wiz SCA Finding (safe_version: "2.23.1")
    ↓
[NEW] Step V0: Validate with Nexus & JDK
    ├─ Check Nexus: Is 2.23.1 available?
    ├─ Check JDK: Is 2.23.1 compatible with repo's JDK?
    ├─ Both pass? → Continue to V1 (apply fix)
    └─ Either fails? → Add to corrective actions, STOP
    ↓
Step V1: Load config & apply fix (existing)
    ↓
Steps 2-10: Build file mods & verify (existing)
```

## Files Updated

**File:** `./skills/remediation-cwe/cwe-937-vulnerable-components/SKILL.md`

**Sections Modified:**
1. Purpose section — Added flow diagram showing new V0 step
2. New Step V0 section — Complete Nexus & JDK validation logic
3. Step V1 — Updated to execute only after V0 passes
4. Inputs section — Already supported (nexus_confirmed field exists)

## Step V0: How It Works

### Pre-requisites
- Environment variables set: `NEXUS_URL`, `NEXUS_USER`, `NEXUS_PASSWORD`
- SCA Dependency Upgrader script available: `scripts/remediation/sca_dependency_upgrader.py`
- JDK Compatibility Validator available: `scripts/validators/jdk_compatibility.py`

### Execution

Call the SCA Dependency Upgrader with the safe version from Wiz report:

```bash
python scripts/remediation/sca_dependency_upgrader.py << 'EOF'
{
  "repo_root": "/path/to/repo",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",  # From Wiz report
  "nexus_url": "https://nexus.barclays.local",
  "nexus_user": "$NEXUS_USER",
  "nexus_pass": "$NEXUS_PASSWORD"
}
EOF
```

### Decision Logic

**If status == "approved":**
```json
{
  "status": "approved",
  "nexus_available": true,
  "jdk_compatible": true,
  "message": "Safe version 2.23.1 is available in Nexus and compatible with JDK 11. Ready for build file remediation."
}
```
→ **Action:** Proceed to Step V1, apply build file fix

**If status == "needs_review" (reason: nexus_unavailable):**
```json
{
  "status": "needs_review",
  "reason": "nexus_unavailable",
  "message": "Safe version 2.23.1 is not available in Nexus repository",
  "corrective_action": "Verify with DevOps team or select an available alternative version"
}
```
→ **Action:** Add to corrective actions, do NOT apply fix

**If status == "needs_review" (reason: jdk_incompatible):**
```json
{
  "status": "needs_review",
  "reason": "jdk_incompatible",
  "jdk_version": 11,
  "min_jdk_required": 17,
  "message": "Safe version requires JDK 17 but repository uses JDK 11",
  "corrective_action": "Upgrade repository JDK to 17+ OR find alternative version compatible with JDK 11"
}
```
→ **Action:** Add to corrective actions, do NOT apply fix

## Integration with Detox Pipeline

### Stage 4: Apply Fixes

The orchestrator (detox-orchestrator-agent) should:

1. For each CWE-937 finding:
   - Call Step V0 (Nexus + JDK validation)
   - If approved → Trigger build remediation agent
   - If needs_review → Add to corrective actions with guidance

**Pseudocode:**

```python
for finding in cwe_937_findings:
    # NEW: Pre-validation
    sca_check = run_sca_dependency_upgrader(
        repo_root=project_path,
        affected_package=finding.affected_package,
        current_version=finding.current_version,
        safe_version=finding.safe_version,
        nexus_url=NEXUS_URL,
        nexus_user=NEXUS_USER,
        nexus_pass=NEXUS_PASSWORD
    )
    
    if sca_check.get("status") == "approved":
        # Existing logic: apply build remediation
        result = build_remediation_agent.apply_fix(finding)
    else:
        # NEW: Add to corrective actions
        corrective_actions.append({
            "cwe": "CWE-937",
            "finding": finding,
            "reason": sca_check.get("reason"),
            "message": sca_check.get("message"),
            "guidance": sca_check.get("corrective_action"),
        })
```

## Benefits

✅ **Nexus Integration**
- Prevents "version not found in Nexus" build failures
- Confirms version availability before applying fix
- Provides clear action items if version unavailable

✅ **JDK Compatibility**
- Prevents incompatible JDK requirement mismatches
- Detects repo's JDK automatically (Gradle/Maven/runtime)
- Provides guidance on JDK upgrade or alternative versions

✅ **Corrective Actions**
- Failed checks documented with clear reasoning
- Actionable guidance for manual resolution
- Prevents wasted CI/CD time on incompatible upgrades

✅ **Zero Breaking Changes**
- Existing skill logic preserved
- V0 is purely additive (new validation layer)
- If V0 passes, existing Steps V1-10 work unchanged

## Testing

Test the updated skill with:

```bash
# 1. Verify JDK detection
python scripts/validators/jdk_compatibility.py << 'EOF'
{"repo_root": ".", "mode": "detect"}
EOF

# 2. Verify JDK compatibility check
python scripts/validators/jdk_compatibility.py << 'EOF'
{
  "repo_root": ".",
  "mode": "check",
  "artifact": "org.springframework:spring-core",
  "version": "6.0.0"
}
EOF

# 3. Verify full SCA validation
python scripts/remediation/sca_dependency_upgrader.py << 'EOF'
{
  "repo_root": ".",
  "affected_package": "org.apache.logging.log4j:log4j-core",
  "current_version": "2.14.1",
  "safe_version": "2.23.1",
  "nexus_url": "https://nexus.barclays.local"
}
EOF
```

## Documentation References

- **Implementation:** `OPTION_A_IMPLEMENTATION_SUMMARY.md`
- **Quick Start:** `QUICKSTART_SCA_VALIDATION.md`
- **Technical Details:** `scripts/remediation/SCA_UPGRADE_INTEGRATION.md`
- **Skill File:** `./skills/remediation-cwe/cwe-937-vulnerable-components/SKILL.md`

## Environment Setup

Required environment variables for Nexus/JDK validation:

```bash
export NEXUS_URL="https://nexus.barclays.local"
export NEXUS_USER="ci-automation"
export NEXUS_PASSWORD="<secure-token>"
```

Add to CI/CD pipeline secrets or `.env.local` (never commit credentials).

## Backward Compatibility

✅ **Fully backward compatible**
- Old CWE-937 findings without safe_version still work
- V0 validation can be skipped if safe_version not available
- Config-based safe versions continue to work
- Build remediation logic unchanged

## Next Steps

1. Merge updated SKILL.md to main branch
2. Update detox-orchestrator-agent to call V0 in Stage 4
3. Configure NEXUS credentials in CI/CD
4. Test with real Wiz SCA findings
5. Update main README.md to document new capabilities

---

**Status:** ✅ Skill updated and ready for orchestrator integration

**Files Modified:** 1
- `./skills/remediation-cwe/cwe-937-vulnerable-components/SKILL.md`

**Lines Added:** ~100 (new Step V0 section)
**Lines Modified:** ~30 (Purpose, Step V1)
**Breaking Changes:** None
