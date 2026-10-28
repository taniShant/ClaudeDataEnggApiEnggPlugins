# Nexus Version Lookup Reference

> **Single source of truth** for all Nexus repository lookup instructions.
> Referenced by: `barclays_internal_libraries_versions.md`, `sdk2_sdk3_gradle/SKILL.md`, `sdk2_sdk3_migration/SKILL.md`

---

## Repository URLs

| Repository | URL | Authentication |
|------------|-----|----------------|
| **Public** | `https://nexus.barcapint.com/nexus/content/groups/barclays/` | None required |
| **Restricted** | `https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/` | `nexusUsername` + `nexusPassword` from env |
| **Read-only** | `https://nexus-read.barcapint.com/nexus/` | None required |

## MUST: Check Reference Docs Before Searching Nexus

**Always consult the reference docs first.** The correct version is likely already documented:

- `barclays_internal_libraries_versions.md` — all Barclays internal library versions (`com.barclays.*`, `com.barclaycard.*`)
- `third_party_dependencies.md` — all approved third-party versions (`org.*`, `com.google.*`, etc.)

Only search Nexus if the artifact is genuinely absent from both reference docs.

**⚠️ NEVER use Nexus to override a version already documented in reference docs.** Even if Nexus shows a newer version, always use the reference doc version. Reference docs are curated and tested — Nexus "latest" may be untested or incompatible.

## Repository Preference Order

**If an artifact is available in the restricted repo, always prefer it over the public repo.**

The restricted repo contains Barclays-curated, internally validated releases — these are the canonical versions for Barclays projects.

Resolution order:
1. **Check restricted first** (if `$nexusUsername` and `$nexusPassword` are set): use this version if found
2. **Fall back to public** only if the artifact is absent from restricted or credentials are unavailable

> If credentials are not available and the artifact appears to be an internal Barclays library, warn the user that the restricted repo may have a preferred version they are not seeing.

---

## Check Latest Version Available

**Public repository (no auth):**
```bash
# Pattern: curl {nexus-url}/{groupId-as-path}/{artifactId}/maven-metadata.xml
# Example for com.barclaycard.digital:common-filter
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclaycard/digital/common-filter/maven-metadata.xml"

# Example for com.barclays.api.emm.common.core:api-ukba-transactions
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/api/emm/common/core/api-ukba-transactions/maven-metadata.xml"
```

Parse the XML response in-agent to extract `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

**Restricted repository (requires auth):**
```bash
# SDK3 platform version
curl -sk -u "${nexusUsername}:${nexusPassword}" \
  "https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/com/barclays/api/sdk3/maven-metadata.xml"
```

Parse the XML response in-agent to extract version numbers from `<version>` tags.

---

## Performance: Parallel Lookups

> **CRITICAL FOR AGENTS:** When looking up multiple artifact versions, run lookups sequentially or use a tool-based approach. Bash array syntax and background jobs are not cross-platform.

**Sequential lookup pattern:**
```bash
# Pattern: curl the maven-metadata.xml for each artifact and parse XML in-agent
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclaycard/digital/common-filter/maven-metadata.xml"
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclaycard/digital/system-bem-payment-pojo-util/maven-metadata.xml"
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclaycard/digital/system-cmd-account-move-balance/maven-metadata.xml"
```

Parse XML responses in-agent to extract `<latest>` or `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

---

## Nexus Lucene Search API (Batch Lookup)

```bash
# Search for all artifacts matching a pattern (faster than individual lookups)
curl -sk "https://nexus.barcapint.com/nexus/service/local/lucene/search?g=com.barclaycard.digital&a=system-*"

# Search by groupId only (returns all artifacts in group)
curl -sk "https://nexus.barcapint.com/nexus/service/local/lucene/search?g=com.barclaycard.digital"

# Search by artifact name (when you don't know the groupId)
curl -sk "https://nexus-read.barcapint.com/nexus/service/local/lucene/search?q=bap-bld-lib-common"
```

Parse the XML responses in-agent to extract `<groupId>`, `<artifactId>`, and `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

---

## Ambiguous Artifact Resolution

When a Nexus search returns **multiple artifacts with the same name but different groupIds**, follow this resolution order:

**Step 1: Check build.gradle for groupId affinity**

Use the Grep tool to search `build.gradle` for dependency declarations. Identify the most frequently used groupIds in the project's existing dependencies. Do not use `grep -oP` (GNU-only, not cross-platform).

**Step 2: Check reference docs**
- [barclays_internal_libraries_versions.md](barclays_internal_libraries_versions.md) - for `com.barclays.*` / `com.barclaycard.*`
- [third_party_dependencies.md](third_party_dependencies.md) - for third-party (`org.*`, `com.google.*`, etc.)

If the artifact appears in either reference doc with a specific groupId, use that.

**Step 2b: Prefer `emm` groupId variants**

If multiple groupIds match and one contains `emm`, **always prefer the `emm` variant**:
- Barclays has migrated many internal libraries to groupIds containing `emm` (e.g., `com.barclays.api.emm.common.core`)
- Example: if both `com.barclays.api:some-lib` and `com.barclays.api.emm.common.core:some-lib` exist, use the `emm` variant
- Only fall through to Step 3 if neither option contains `emm`

**Step 3: Ask the user**
If Steps 1, 2, and 2b don't resolve the ambiguity, present the options to the user:
```
Found multiple groupIds for artifact 'common-filter':
  1. com.barclaycard.digital:common-filter:5.0.014
  2. com.barclaycard.digital.core:common-filter:3.2.001
Which groupId should be used?
```

> **NEVER guess silently.** An incorrect groupId can pull in a completely different library with incompatible APIs.

---

## Path Conversion Rules

| GroupId | Artifact | Path |
|---------|----------|------|
| `com.barclaycard.digital` | `common-filter` | `com/barclaycard/digital/common-filter/` |
| `com.barclays.api` | `sdk3` | `com/barclays/api/sdk3/` |
| `com.barclays.api.emm.common.core` | `api-ukba-transactions` | `com/barclays/api/emm/common/core/api-ukba-transactions/` |

**Rule:** Replace dots (`.`) with slashes (`/`) in the groupId, then append the artifactId.

---

## Dynamic Versions for Discovery

Use `major.minor.+` pattern in Gradle to **discover** the latest patch version. Only use `+` for artifacts that follow the `major.minor.patch` versioning pattern.

```gradle
// Correct: pin major.minor, discover latest patch
implementation 'com.barclaycard.digital:common-filter:5.0.+'
implementation 'com.barclays.api.emm.common.core:api-ukba-transactions:2.2.+'

// WRONG: too broad - risks pulling incompatible minor/major versions
// implementation 'com.barclaycard.digital:common-filter:5.+'
// implementation 'com.barclaycard.digital:common-filter:latest.release'
```

**Then resolve to see actual version:**
```bash
$GRADLE_CMD dependencies --configuration runtimeClasspath | grep common-filter
```

### IMPORTANT: Final Build Must Use Explicit Versions

Dynamic versions (`+`, `latest.release`) are for **discovery only**. Production builds MUST use explicit versions for:
- Reproducible builds
- Security auditing
- Dependency tracking

**Discovery workflow:**
1. Use `latest.release` to find newest version
2. Verify build passes with that version
3. Replace with explicit version in final build.gradle
4. Document the version update
