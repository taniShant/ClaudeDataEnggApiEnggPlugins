# Nexus Version Lookup Reference

> **Cross-Platform Note:** All Gradle commands in this document use `$GRADLE_CMD` instead of `./gradlew`. XML parsing uses in-agent techniques instead of GNU-only `grep -oP`. See CLAUDE.md Cross-Platform Execution section for details.

> **Single source of truth** for all Nexus repository lookup instructions.
> Referenced by: `mca-jdk-upgrade-agent.md`, `integration-test-agent.md`

---

## Repository URLs

| Repository | URL | Authentication |
|------------|-----|----------------|
| **Public** | `https://nexus.barcapint.com/nexus/content/groups/barclays/` | None required |
| **Restricted** | `https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/` | `nexusUsername` + `nexusPassword` from env |
| **Read-only** | `https://nexus-read.barcapint.com/nexus/` | None required |

---

## Check Latest Version Available

**Public repository (no auth):**
```bash
# Pattern: curl {nexus-url}/{groupId-as-path}/{artifactId}/maven-metadata.xml
# Example for com.barclays.mca:mca-experience-common-starter
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/mca-experience-common-starter/maven-metadata.xml"

# Example for com.barclays.mca:mca-generic-experience-api-starter
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/mca-generic-experience-api-starter/maven-metadata.xml"

# Example for com.barclays.mca:referencedata-service-starter
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/referencedata-service-starter/maven-metadata.xml"
```

Parse the XML response in-agent to extract `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

**Restricted repository (requires auth):**
```bash
# MCA platform libraries
curl -sk -u "${nexusUsername}:${nexusPassword}" \
  "https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/com/barclays/mca/mca-global-libs/maven-metadata.xml"
```

Parse the XML response in-agent to extract version numbers from `<version>` tags.

---

## MCA2-Specific GroupIds

When searching for MCA2 libraries, these are the common groupIds:

| GroupId | Description |
|---------|-------------|
| `com.barclays.mca` | Core MCA libraries |
| `com.barclays.mca.experience` | MCA experience starters |
| `com.barclays.mca.referencedata` | Reference data services |
| `com.barclays.ukc` | UK Consumer libraries |
| `com.barclays.eps` | EPS libraries |

---

## Performance: Parallel Lookups

> **CRITICAL FOR AGENTS:** When looking up multiple artifact versions, run lookups sequentially or use a tool-based approach. Bash array syntax and background jobs are not cross-platform.

**Sequential lookup pattern:**
```bash
# Pattern: curl the maven-metadata.xml for each artifact and parse XML in-agent
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/mca-experience-common-starter/maven-metadata.xml"
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/mca-generic-experience-api-starter/maven-metadata.xml"
curl -sk "https://nexus.barcapint.com/nexus/content/groups/barclays/com/barclays/mca/referencedata-service-starter/maven-metadata.xml"
```

Parse XML responses in-agent to extract `<latest>` or `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

---

## Nexus Lucene Search API (Batch Lookup)

```bash
# Search for all artifacts matching a pattern (faster than individual lookups)
curl -sk "https://nexus.barcapint.com/nexus/service/local/lucene/search?g=com.barclays.mca&a=mca-*"

# Search by groupId only (returns all artifacts in group)
curl -sk "https://nexus.barcapint.com/nexus/service/local/lucene/search?g=com.barclays.mca"

# Search by artifact name (when you don't know the groupId)
curl -sk "https://nexus-read.barcapint.com/nexus/service/local/lucene/search?q=mca-experience-common-starter"
```

Parse the XML responses in-agent to extract `<groupId>`, `<artifactId>`, and `<version>` elements. Do not use `grep -oP` (GNU-only, not cross-platform).

---

## Deep Nexus Search: When Expected Versions Are Missing

**CRITICAL:** When a library version is not found in the reference tables or the Lucene search returns an unexpectedly old version, **always perform a deep Nexus search before concluding the version doesn't exist.**

### Why Lucene Search Can Mislead

The Lucene search API (`/service/local/lucene/search`) has limitations:
- May not index all repositories (e.g., `barclays-uk-releases` may not surface via Lucene)
- Default result count may be paginated and miss newer versions
- Some release trains use non-sequential version jumps (e.g., EPS libs jump from `2.6.x` → `5.x` → `6.2.x`)

### Deep Search Protocol

When a library appears to be on an incompatible old version:

**Step 1: Check maven-metadata.xml directly (authoritative source)**
```bash
curl -s "https://nexus-read.barcapint.com/nexus/content/groups/barclays/{groupId-path}/{artifactId}/maven-metadata.xml"
```
This returns ALL versions regardless of Lucene indexing. Sort and filter for newer major versions:
```bash
curl -s "https://nexus-read.barcapint.com/nexus/content/groups/barclays/com/barclays/eps/scp-eps-libs-bpm/maven-metadata.xml" \
  | grep -oE "<version>[^<]+</version>" | sed 's/<[^>]*>//g' | sort -V
```

**Step 2: Verify the candidate version exists**
```bash
# Probe via HTTP status (200 = exists, 404 = doesn't exist)
curl -o /dev/null -s -w "%{http_code}" \
  "https://nexus-read.barcapint.com/nexus/content/groups/barclays/{groupId-path}/{artifactId}/{version}/{artifactId}-{version}.pom"
```

**Step 3: Inspect the candidate JAR for Jakarta compatibility**
```bash
# Download and verify the key classes use jakarta.servlet (not javax.servlet)
curl -s -o /tmp/artifact.jar "{nexus-url}/{path}/{version}/{artifact}-{version}.jar"
javap -verbose -classpath /tmp/artifact.jar {fully.qualified.ClassName} 2>/dev/null \
  | grep -E "jakarta|javax|HandlerInterceptor|super_class"
```

### EPS Library Version Jump Pattern

EPS libraries (`com.barclays.eps:scp-eps-libs-*`) follow a **version train pattern** for major platform migrations:

| Version Series | Platform | Servlet Namespace |
|----------------|----------|-------------------|
| `1.x` – `2.6.x` | Spring Boot 2.x / Java 8 | `javax.servlet` |
| `5.x` | Spring Boot 2.x migration builds | `javax.servlet` |
| `6.x` | **Spring Boot 3.x / Java 21** | **`jakarta.servlet`** |

**Key implication:** If you are on Spring Boot 3.x and see an EPS library at `2.x` or `5.x`, always check whether a `6.x` version exists — it will have the Jakarta migration applied.

Examples discovered:
- `scp-eps-libs-bpm`: `5.1.002` (javax) → `6.2.002` (jakarta, implements `AsyncHandlerInterceptor` directly)
- `scp-eps-libs-service-delegate`: `0.1.009` (javax) → `6.0.002` (jakarta)
- `scp-eps-core-comm`: `6.2.x` is Jakarta-compatible (the `6.x` train is the jakarta migration)

---

## Ambiguous Artifact Resolution

When a Nexus search returns **multiple artifacts with the same name but different groupIds**, follow this resolution order:

**Step 1: Check build.gradle for groupId affinity**

Use the Grep tool to search `build.gradle` for dependency declarations. Identify the most frequently used groupIds in the project's existing dependencies.

**Step 2: Check reference docs**
- Check the MCA2 dependency versions table in `mca-jdk-upgrade-agent.md`

If the artifact appears in the reference doc with a specific groupId, use that.

**Step 3: Spawn auto-decision-agent**
If Steps 1 and 2 don't resolve the ambiguity, spawn the `auto-decision-agent` with the options and context.

> **NEVER guess silently.** An incorrect groupId can pull in a completely different library with incompatible APIs.

---

## Path Conversion Rules

| GroupId | Artifact | Path |
|---------|----------|------|
| `com.barclays.mca` | `mca-experience-common-starter` | `com/barclays/mca/mca-experience-common-starter/` |
| `com.barclays.mca` | `mca-generic-experience-api-starter` | `com/barclays/mca/mca-generic-experience-api-starter/` |
| `com.barclays.ukc` | `ukc-bronze-service-api` | `com/barclays/ukc/ukc-bronze-service-api/` |

**Rule:** Replace dots (`.`) with slashes (`/`) in the groupId, then append the artifactId.

---

## Dynamic Versions for Discovery

Use `major.minor.+` pattern in Gradle to **discover** the latest patch version. Only use `+` for artifacts that follow the `major.minor.patch` versioning pattern.

```gradle
// Correct: pin major.minor, discover latest patch
implementation 'com.barclays.mca:mca-experience-common-starter:3.0.+'
implementation 'com.barclays.mca:referencedata-service-starter:3.0.+'

// WRONG: too broad - risks pulling incompatible minor/major versions
// implementation 'com.barclays.mca:mca-experience-common-starter:3.+'
// implementation 'com.barclays.mca:mca-experience-common-starter:latest.release'
```

**Then resolve to see actual version:**
```bash
$GRADLE_CMD dependencies --configuration runtimeClasspath | grep mca-experience
```

---

## Version Format Convention: `major.minor.+` for New Dependencies

**RULE:** When adding a new dependency after a Nexus version search, if the returned version is in `major.minor.patch` format, declare the dependency in `build.gradle` as `major.minor.+`.

This applies to all Barclays internal artifacts that use the `major.minor.patch` versioning convention:

| Nexus returns | Write in build.gradle |
|---------------|----------------------|
| `1.0.036` | `1.0.+` |
| `03.0011.001` | `03.0011.+` |
| `2.3.021` | `2.3.+` |
| `6.3.019` | `6.3.+` |
| `14.04.001.0` | Pin explicitly (4-part version — not eligible) |

**Why:** Barclays internal artifacts release patches frequently. Using `major.minor.+` means the build always gets the latest compatible patch without requiring manual version bumps, while keeping the API stable within the minor version.

**Exception — pin explicitly when:**
- The version has 4 or more parts (e.g., `14.04.001.0`)
- The artifact uses semver with breaking changes per minor version
- A specific patch is required for a security fix

```gradle
// Example: Nexus search returns 03.0011.001
// Write as:
implementation group:'com.barclays.services.bankinformation', name:'ebs_bankinforefdata', version:'03.0011.+'

// Example: Nexus search returns 2.3.021
// Write as:
implementation group:'com.barclays.global.mca', name:'mca-logging-spy', version:'2.3.+'
```

---

### IMPORTANT: Final Build Must Use Explicit Versions

Dynamic versions (`+`, `latest.release`) are for **discovery only** for third-party/non-Barclays artifacts. For **Barclays internal artifacts** following `major.minor.patch` format, use the `major.minor.+` convention above (this is the declared convention for Barclays MCA builds).

For standard production builds with third-party dependencies:
- Use explicit versions for reproducible builds
- Use explicit versions for security auditing

**Discovery workflow (third-party deps):**
1. Use `latest.release` or maven-metadata.xml lookup to find newest version
2. Verify build passes with that version
3. Replace with explicit version in final build.gradle
4. Document the version update
