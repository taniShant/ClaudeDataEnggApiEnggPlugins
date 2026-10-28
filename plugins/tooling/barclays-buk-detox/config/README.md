# Detox Plugin Configuration

## Overview

This directory contains configuration files for the **Detox CWE Vulnerability Remediation Plugin**, which automates security fixes across 50+ CWE vulnerabilities in Python, Java, JavaScript, TypeScript, C#, and Go.

### Key Configuration File: `safe-versions.json`

Pre-validated dependency versions that enable **autonomous CWE-937 (Vulnerable Components) remediation** without user confirmation prompts. This allows Detox to automatically upgrade vulnerable dependencies in Maven, Gradle, npm, and other build systems.

### Plugin Capabilities This Config Enables

The Detox plugin provides **47+ CWE skills** for code remediation (Python, Java, JS, TS, C#, Go). For **CWE-937 (Vulnerable Components)**, this config enables:

- ✅ **Autonomous dependency upgrades** in Maven, Gradle, npm, pip, Go
- ✅ **Security test generation** with regression test patterns
- ✅ **Atomic commits** with full CVE audit trail
- ✅ **Build validation** ensuring fixes don't break compilation
- ✅ **CI/CD integration** without user interaction

### How It Works

**Config-Driven Auto-Fix:**
- Orchestrator parses Wiz SCA report → finds log4j:1.2.17 (CWE-937)
- Looks up in `safe-versions.json` → finds `ch.qos.reload4j:reload4j:1.2.26` (pre-validated)
- Applies fix autonomously → creates atomic commit with CVE traceability → generates tests
- Problem solved: Runs in fully autonomous CI/CD pipelines

---

## How It Works

### 1. CWE-937 Skill Flow (Updated)

The remediation skill now uses this sequence:

```
Step V1: Load Pre-Validated Safe Versions from Config
├─ Search for affected_package in safe-versions.json
├─ If found → use config version, set nexus_confirmed from config
└─ If NOT found → check if excluded; if so, flag for manual review

Step V2: (SKIPPED — all versions now come from config)

Step V3: Confirm selection before proceeding
└─ Apply config-validated version to build file
```

### 2. Orchestrator Flow (9-Stage FORGE Pipeline)

**Stage 2: Parse Reports** — Parser reads Wiz SCA findings and threat models

**Stage 3: Classify** — Findings tagged with CWE-937 routed to dependency fix path

**Stage 4: Apply Fixes** — Substage 4b routes CWE-937 to `detox-build-remediation-agent`
- Agent loads safe-versions.json
- Looks up vulnerable package
- Applies build file changes autonomously (pom.xml, build.gradle, package.json, etc.)
- Creates atomic commit with CVE reference

**Stage 5: Generate Tests** — Security regression tests created for each fix

**Stage 6: Validate Fixes** — Build verification + Semgrep re-scan confirms CVEs patched

**Stage 8: Generate Report** — DETOX-REMEDIATION-REPORT.md documents all fixes with audit trail

**Stage 9: Create PR** — Pushes to GitLab with summary showing safe versions applied

---

## Configuration Structure

### Top-Level Fields

```json
{
  "version": "1.0",                    // Config schema version
  "description": "...",                // Purpose
  "last_updated": "2026-07-22",       // Last review date
  "maintained_by": "Security Champions",
  "review_cadence": "quarterly",       // How often to update
  "versions": { ... },                 // Package → safe version mappings
  "special_cases": { ... },            // Complex migration scenarios
  "exclusions": { ... },               // Packages NOT auto-fixed
  "nexus_availability_check": { ... }  // Verification commands
}
```

### versions Section

Each entry defines a safe version for a vulnerable package:

```json
"log4j:log4j": {
  "current_vulnerable": "1.2.17",
  "safe_version": "ch.qos.reload4j:reload4j:1.2.26",
  "strategy": "drop_in_replacement",
  "nexus_confirmed": true,
  "notes": "...",
  "cves_patched": ["CVE-2022-23302", ...],
  "tested_projects": ["coreMortgages", "SALES"],
  "requires_bridge": false,
  "requires_code_changes": false
}
```

**Key Fields:**
- `current_vulnerable`: The version triggering the vulnerability
- `safe_version`: The version to upgrade/replace to
- `strategy`: How to apply the fix (see Strategies below)
- `nexus_confirmed`: `true` if version verified available in internal Nexus
- `cves_patched`: List of CVEs resolved by this version
- `tested_projects`: Projects where this upgrade has been validated
- `requires_bridge`: Whether a compatibility bridge is needed (`true`, `false`, or `"conditional"`)
- `requires_code_changes`: Whether source code modifications are needed

### Strategies

| Strategy | Meaning | Example |
|----------|---------|---------|
| `drop_in_replacement` | Same API, different artifact (log4j 1.x → reload4j) | No code changes |
| `in_place_upgrade` | Same artifact, higher safe version (1.9 → 1.10.0) | Backward compatible |
| `major_version_upgrade` | Major version bump (snakeyaml 1.x → 2.x) | May need code review |
| `force_with_related_artifacts` | Update multiple coordinated artifacts (jackson-core/databind/annotations) | All same version |
| `related_artifacts_in_place_upgrade` | Update all artifacts matching a pattern (jersey.* → 2.42) | All same version |
| `library_replacement` | Exclude old, add new (log4j 1.x → log4j 2.x) | Major migration |

---

## When to Update safe-versions.json

### Add a New Entry
1. **New CVE discovered** → Org decides on a safe version
2. **New library adopted** → Add its baseline version
3. **Quarterly review** → Bump versions as new patches release

**Process:**
1. Create a JIRA ticket: "Add CWE-937 config entry for {package}"
2. Security team verifies:
   - Safe version patches all listed CVEs
   - Version is available in internal Nexus
   - Version has been tested in at least one project
3. Add to config with `tested_projects` list
4. Run `/test-plugin ./plugins/tooling/barclays-buk-detox` to validate

### Update Existing Entry
1. Org releases new patch version
2. Security team tests it (e.g., in a staging environment)
3. Update `safe_version` field
4. Update `tested_projects` with new testing evidence
5. Update `last_updated` date
6. Commit with message: `fix: Update CWE-937 config {package} to {new_version}`

### Move a Package to exclusions
1. **If it's too complex for auto-fix** (e.g., AWS SDK v1→v2 migration)
2. **If multiple strategies are valid** (e.g., log4j 1.x can be reload4j OR 2.x)
3. **If it requires external coordination** (GPL license approval, shared library upgrade)

**Process:**
1. Move package from `versions` to `exclusions`
2. Add `reason` explaining why it's excluded
3. Update `last_updated`
4. Commit with message: `fix: Exclude {package} from auto-fix — {reason}`

---

## Nexus Availability Verification

Before adding a version to the config, verify it's available in internal Nexus:

### For Gradle Projects
```bash
./gradlew dependencies --configuration runtimeClasspath 2>/dev/null | grep "log4j:log4j"
```
Expected: `log4j:log4j:1.2.26.1` or similar (not 404/error)

### For Maven Projects
```bash
mvn help:describe -Dartifact=log4j:log4j:1.2.26.1
```
Expected: Artifact details printed (not "Unknown artifact")

### Manual Check in Nexus UI
Browse: `https://nexus.barclays.com/nexus/content/repositories/` → search for package/version

---

## Example: Adding Log4j 2.x as Alternative

The current config has `reload4j` as the primary safe version. If you want to offer Log4j 2.x as an alternative (for projects that need 2.x-specific features):

1. **Add a special_cases entry:**
   ```json
   "log4j_migration_1x_to_2x": {
     "description": "When Log4j 1.x must migrate to 2.x (not reload4j)",
     "trigger": "User specifies 2.x is required OR reload4j compatibility issues detected",
     "strategy": "Exclude log4j 1.x globally, add log4j-core + log4j-api + conditional bridges",
     "nexus_confirmed": true,
     "notes": "Not auto-selected; requires hybrid or manual review flag"
   }
   ```

2. **Document in agent:** The `detox-build-remediation-agent` would read this and check for special conditions before applying

3. **Update skill:** Add logic to handle special_cases in Step V1

---

## Testing the Config

After updating `safe-versions.json`:

```bash
cd /c/claude_buk_repo/shilpa_fort/buk
/test-plugin ./plugins/tooling/barclays-buk-detox
```

Expected output: Score 90+, no errors in config parsing or schema validation.

---

## Ownership and Review Cadence

| Role | Responsibility |
|------|-----------------|
| **Security Champions** | Review CVE advisories quarterly; add/update safe versions |
| **Platform Engineering** | Verify Nexus availability; coordinate with artifact repo team |
| **Application Teams** | Test in staging; report compatibility issues |

**Review Calendar:**
- Q1 (Jan): Winter CVE review, Log4j/Spring patches
- Q2 (Apr): Spring patches, dependency audit
- Q3 (Jul): Summer security releases
- Q4 (Oct): Fall review, year-end planning

---

## Troubleshooting

### Build Fails After Auto-Fix Applied

**Symptom:** Detox applied log4j upgrade, but `./gradlew build` fails with "NoClassDefFoundError"

**Diagnosis:**
1. Check if SLF4J binding was removed (slf4j-log4j12 → log4j-slf4j2-impl)
2. Check if legacy imports exist (`import org.apache.log4j.*`)
3. Check if bridge was added (log4j-1.2-api)

**Fix:** Update config entry's `requires_bridge` field to `"conditional"`, document what to check

### Version Not Available in Nexus

**Symptom:** Detox applies fix with safe version that isn't in Nexus; build fails at runtime

**Prevention:** Always verify with `nexus_availability_check` commands before adding to config

**Recovery:** Set `nexus_confirmed: false` in config; agent will proceed but flag warning in PR

---

## Plugin Features Enabled by This Configuration

The safe-versions.json config powers these core Detox features:

| Feature | Enabled By | Benefit |
|---------|-----------|---------|
| **Autonomous CWE-937 Fixes** | Pre-validated versions | No user prompts; runs in CI/CD pipelines |
| **Multi-Build System Support** | Nexus-confirmed versions | Works with Maven, Gradle, npm, pip, Go |
| **Atomic Commits** | Config-driven fixes | One commit per dependency upgrade with full traceability |
| **Security Test Generation** | Config metadata (cves_patched) | Generates regression tests verifying CVE patches |
| **Remediation Reporting** | Config entries | Executive reports mapping fixes to CVEs |
| **Corrective Actions** | Exclusions list | Identifies packages requiring manual review |

## Related Documentation

- **Main Plugin README**: `plugins/tooling/barclays-buk-detox/README.md`
- **CWE-937 Skill**: `plugins/tooling/barclays-buk-detox/skills/remediation-cwe/cwe-937-vulnerable-components/SKILL.md`
- **Build Remediation Agent**: `plugins/tooling/barclays-buk-detox/agents/detox-build-remediation-agent.md`
- **Orchestrator**: `plugins/tooling/barclays-buk-detox/agents/detox-orchestrator-agent.md` (Stage 4b)

## Contributing

Want to improve Detox? Read the **[Contributing Guide](https://pages.gitlab.barcapint.com/prasad.edlabadkar/detox/assist/contributing)** for information on:
- Adding new safe versions to this config
- Proposing new CWE skills
- Extending language pattern support
- Contributing security test patterns
- Reporting bugs or suggesting enhancements

Contributions from Security Champions, platform teams, and developers are welcome!
