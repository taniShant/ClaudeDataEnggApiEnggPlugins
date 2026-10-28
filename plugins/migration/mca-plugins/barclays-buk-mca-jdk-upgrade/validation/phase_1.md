# Phase 1 Validation Checklist

Post-Phase 1 verification checks. Run after Phase 1 commit to confirm build infrastructure setup and platform BOM addition.

## Checks

### Check 1: dependencies.gradle Consolidated (Verification)

**What**: dependencies.gradle was already consolidated into build.gradle in Phase 0.

**How to verify**:
```bash
if grep -qE "^[^/]*apply from.*dependencies\.gradle" build.gradle 2>/dev/null; then
  echo "FAIL: dependencies.gradle still applied (Phase 0 consolidation incomplete)"
else
  echo "PASS: dependencies.gradle consolidated"
fi
```

**On failure**: This should not happen if Phase 0 completed. Agent must re-execute Phase 0 step 11 consolidation logic.

### Check 2: MCA Platform BOM Present (ALL GROUPS)

**What**: MCA platform BOM is present as the first dependency in the dependencies block.

**How to verify**:
```bash
if grep -qE "implementation platform.*['\"]com\.barclays\.global\.mca:mca-dependencies" build.gradle 2>/dev/null; then
  echo "PASS: MCA Platform BOM present"
else
  echo "FAIL: MCA Platform BOM not found"
fi
```

**On failure**: Agent must query Nexus for latest mca-dependencies version and add platform BOM.

### Check 3: BOM-Managed Dependencies Have NO Explicit Versions (HARD GATE)

**What**: After adding platform BOM, dependencies that are VERIFIED as BOM-managed must have explicit versions stripped. Dependencies NOT in the BOM POM must KEEP their versions.

**How to verify**:
```bash
if grep -qE "implementation platform.*mca-dependencies" build.gradle 2>/dev/null; then
  # Download and check the actual BOM POM to identify managed artifacts
  # Do NOT assume all com.barclays.* are BOM-managed — verify each one
  BOM_VERSION=$(grep -oE "mca-dependencies:[0-9][^'\"]*" build.gradle | head -1 | cut -d: -f2)
  curl -sk "https://nexus-read.barcapint.com/nexus/content/groups/barclays/com/barclays/global/mca/mca-dependencies/$BOM_VERSION/mca-dependencies-$BOM_VERSION.pom" -o /tmp/mca-bom-check.pom

  # For each com.barclays.* dependency with explicit version, check if it's in the BOM
  VIOLATIONS=0
  while IFS= read -r dep; do
    ARTIFACT=$(echo "$dep" | grep -oE "[^:]+:[^:]+:[^:']+" | head -1)
    GROUP_ARTIFACT=$(echo "$ARTIFACT" | cut -d: -f1-2)
    if grep -q "$(echo "$GROUP_ARTIFACT" | cut -d: -f2)" /tmp/mca-bom-check.pom 2>/dev/null; then
      echo "VIOLATION: $GROUP_ARTIFACT has explicit version but is BOM-managed"
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  done < <(grep -E "(com\.barclays\.(mca|ukc|global\.mca|ccd\.ukcad)):[^:]+:[0-9]" build.gradle 2>/dev/null)

  if [ "$VIOLATIONS" -gt 0 ]; then
    echo "FAIL: $VIOLATIONS BOM-managed dependencies still have explicit versions"
    exit 1
  else
    echo "PASS: BOM version stripping complete (non-BOM dependencies correctly retain versions)"
  fi
else
  echo "SKIP: No MCA Platform BOM present (BOM addition failed)"
fi
```

**On failure**: This is a **HARD GATE**. Agent MUST strip versions ONLY from dependencies verified as present in the BOM POM's `<dependencyManagement>` section. Dependencies NOT in the BOM POM must keep their explicit versions.

**Edge Cases (Agent Must Handle):**

1. **Dependencies with `<optional>true</optional>` in BOM:** STRIP version (BOM-managed)
2. **Dependencies with `<scope>provided</scope>` or `<scope>test</scope>` in BOM:** STRIP version (BOM-managed)
3. **Dependencies with `${property}` version in BOM:** Resolve property from `<properties>` or parent POM, then STRIP version (BOM-managed)
4. **Dependencies with `<exclusions>` in BOM:** STRIP version (BOM-managed, exclusions inherited)
5. **Dependencies in parent BOM:** Parse parent POM recursively (up to 5 levels), STRIP if found in parent (BOM-managed)
6. **Dependencies NOT found in BOM or parents:** KEEP explicit version (NOT BOM-managed)

**Concrete Examples:**

Example 1: Optional dependency
```xml
<!-- In BOM POM -->
<dependency>
  <groupId>com.barclays.mca</groupId>
  <artifactId>mca-logging-starter</artifactId>
  <version>3.0.0</version>
  <optional>true</optional>
</dependency>
```
**Action:** STRIP version from build.gradle (BOM manages version, optional means inclusion is optional, not version management)

Example 2: Property reference
```xml
<!-- In BOM POM -->
<properties>
  <mca.common.version>3.0.0-RELEASE</mca.common.version>
</properties>
<dependency>
  <groupId>com.barclays.ccd.ukcad</groupId>
  <artifactId>mca-experience-common-starter</artifactId>
  <version>${mca.common.version}</version>
</dependency>
```
**Action:** STRIP version from build.gradle (property resolves to 3.0.0-RELEASE, BOM-managed)

Example 3: NOT in BOM
```groovy
// In build.gradle
implementation 'com.barclays.ccd.ukcad:legacy-custom-lib:1.5.2'
```
If `legacy-custom-lib` does NOT appear in BOM POM's `<dependencyManagement>` → KEEP version 1.5.2 (NOT BOM-managed)

### Check 4: Gradle Wrapper Version Upgraded to 8.5+

**What**: Phase 1 upgrades the Gradle wrapper version to 8.5+ (Phase 0 only normalized the base URL path). The distributionUrl must use the Barclays Nexus flat-path format AND have Gradle version 8.5 or higher.

**How to verify**:
```bash
DIST_URL=$(grep "distributionUrl" gradle/wrapper/gradle-wrapper.properties 2>/dev/null)
if echo "$DIST_URL" | grep -qE "nexus.*barcapint.*content/groups/barclays/gradle-8\.[5-9]|gradle-8\.1[0-9]"; then
  echo "PASS: distributionUrl has Nexus flat path with Gradle 8.5+"
else
  echo "FAIL: distributionUrl version not upgraded to 8.5+. Current: $DIST_URL"
fi
```

**On failure**: Agent must update the Gradle version in the distributionUrl to 8.5:
```bash
sed -i.bak "s|gradle-[0-9][0-9.]*-bin.zip|gradle-8.5-bin.zip|" gradle/wrapper/gradle-wrapper.properties
rm -f gradle/wrapper/gradle-wrapper.properties.bak
```

### Check 6: No Public Repositories

**What**: All public repository declarations (mavenCentral, gradlePluginPortal, etc.) remain removed from Phase 0.

**How to verify**:
```bash
if grep -qE "mavenCentral\(\)|gradlePluginPortal\(\)|repo\.maven\.apache|services\.gradle\.org" build.gradle 2>/dev/null; then
  echo "FAIL: Public repository declarations found"
else
  echo "PASS: No public repositories"
fi
```

**On failure**: Agent must use Edit tool to remove public repositories and ensure only Barclays Nexus URLs remain.

See [common.md](common.md) for auto-fix behavior, integration details, and the mandatory Gradle exit code verification pattern.

**Phase 1 specifics:** This phase focuses on build infrastructure preparation. The HARD GATE is Check 3 (MCA BOM version stripping) - all MCA dependencies MUST have versions removed before Phase 2 can begin selective migration. The validation agent covers these checks via red flags 5, 11, 14, 17.
