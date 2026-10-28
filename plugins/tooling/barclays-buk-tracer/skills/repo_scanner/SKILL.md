---
name: repo-scanner
description: >
  Multi-stack test repository scanner — git clone with PAT, language detection,
  test file glob patterns per language (Java/Kotlin/Swift/TypeScript/JS/Python),
  behavior name normalisation, and coverage map construction.
user-invocable: false
owner: Barclays BUK Digital Channels
review-trigger: New language stack added, layer-registry.yaml schema change
status: production
---

## Source Attribution

**Source:** TRACER v1.1.0 internal — language detection heuristics + test pyramid conventions  
**Owner:** Barclays BUK Digital Channels  
**Review trigger:** New language stack added to Barclays BUK repos, or layer-registry schema changes  
**Status:** Production

---

## Quick Start

```bash
# Shallow clone a remote Stash repo with PAT
git clone --depth 1 \
  "https://oauth2:${STASH_PAT}@stash.barcapint.com/scm/team/mobile-app.git" \
  /tmp/tracer-scan-abc123

# Detect language: Kotlin?
ls /tmp/tracer-scan-abc123/ | grep -E "build.gradle|pom.xml"
find /tmp/tracer-scan-abc123 -name "*.kt" -type f | head -1

# Find all Spock test files
find /tmp/tracer-scan-abc123 -name "*Spec.groovy" -type f

# Extract Spock test method names from one file
grep -n "def " /tmp/tracer-scan-abc123/src/test/groovy/MySpec.groovy | grep -v "//"
```

---

## Core Concept 1: Repository Access

### Remote clone — Stash (Bitbucket)

```bash
git clone --depth 1 \
  "https://oauth2:${STASH_PAT}@stash.barcapint.com/scm/${PROJECT}/${REPO}.git" \
  "${CLONE_PATH}"
```

### Remote clone — GitLab

```bash
git clone --depth 1 \
  "https://oauth2:${GITLAB_PAT}@app.gitlab.barcapint.com/${NAMESPACE}/${REPO}.git" \
  "${CLONE_PATH}"
```

### Clone path convention

Use a hash of the URL so multiple repos don't collide:
```bash
CLONE_PATH="/tmp/tracer-scan-$(echo '${URL}' | sha256sum | cut -c1-8)"
```

### Cleanup (always)

```bash
rm -rf "${CLONE_PATH}"
```

Clean up after scanning regardless of success or failure. Use a `trap` to ensure cleanup on error:
```bash
trap "rm -rf ${CLONE_PATH}" EXIT
```

---

## Core Concept 2: Language Detection

Apply heuristics in this priority order — first match wins.

| Priority | Signal file/pattern | Detected language |
|----------|---------------------|-------------------|
| 1 | `build.gradle` or `pom.xml` present **AND** `.kt` files found | `kotlin` |
| 2 | `build.gradle` or `pom.xml` present | `java` |
| 3 | `Package.swift` present OR `*.swift` files found | `swift` |
| 4 | `package.json` present **AND** `*.ts` files found | `typescript` |
| 5 | `package.json` present | `javascript` |
| 6 | `requirements.txt` or `pyproject.toml` or `setup.py` present | `python` |
| 7 | `*.feature` files present, nothing else | `gherkin` |
| 8 | None matched | `unknown` |

```bash
detect_language() {
    REPO="$1"
    if (ls "${REPO}/build.gradle" "${REPO}/pom.xml" 2>/dev/null | head -1 | grep -q .) && \
       find "${REPO}" -name "*.kt" | head -1 | grep -q .; then
        echo "kotlin"
    elif ls "${REPO}/build.gradle" "${REPO}/pom.xml" 2>/dev/null | head -1 | grep -q .; then
        echo "java"
    elif ls "${REPO}/Package.swift" 2>/dev/null | grep -q . || \
         find "${REPO}" -name "*.swift" | head -1 | grep -q .; then
        echo "swift"
    elif ls "${REPO}/package.json" 2>/dev/null | grep -q . && \
         find "${REPO}" -name "*.ts" | head -1 | grep -q .; then
        echo "typescript"
    elif ls "${REPO}/package.json" 2>/dev/null | grep -q .; then
        echo "javascript"
    elif ls "${REPO}/requirements.txt" "${REPO}/pyproject.toml" "${REPO}/setup.py" 2>/dev/null | head -1 | grep -q .; then
        echo "python"
    elif find "${REPO}" -name "*.feature" | head -1 | grep -q .; then
        echo "gherkin"
    else
        echo "unknown"
    fi
}
```

---

## Core Concept 3: Test File Patterns Per Language

### Java

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit tests | `src/test/java/**/*Test.java` | JUnit |
| Component/xapi | `src/test/groovy/**/*Spec.groovy` | Spock |
| Component | `src/test/java/**/*IT.java` | JUnit (integration) |
| Contract | `src/test/resources/**/*.feature` | Karate |
| Device (Xray) | `src/test/resources/features/**/*.feature` | Gherkin |

### Kotlin

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit tests | `src/test/kotlin/**/*Test.kt` | JUnit5/Kotest |
| Component | `src/test/kotlin/**/*Spec.kt` | Kotest |
| Contract | `src/test/kotlin/**/*Contract.kt` | Pact |

### Swift (iOS / macOS)

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit tests | `**/Tests/**/*Tests.swift` | XCTest |
| UI tests | `**/UITests/**/*UITests.swift` | XCUITest |
| Snapshot | `**/SnapshotTests/**/*.swift` | SnapshotTesting |

### TypeScript

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit tests | `src/**/*.spec.ts` | Jest |
| Component | `src/**/*.test.ts` | Jest/RTL |
| E2E | `cypress/**/*.cy.ts` | Cypress |
| E2E | `e2e/**/*.spec.ts` | Playwright |

### JavaScript

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit/component | `src/**/*.spec.js`, `src/**/*.test.js` | Jest/Mocha |

### Python

| Layer type | Glob pattern | Framework |
|-----------|-------------|-----------|
| Unit/component | `tests/**/test_*.py`, `tests/**/*_test.py` | pytest |
| BDD | `features/**/*.feature` | behave |

---

## Core Concept 4: Behavior Name Extraction and Normalisation

Every test ID extracted from a file is normalised to `snake_case` for matching against the TRACER matrix.

### Java / Groovy (Spock)

```bash
# Extract Spock `def` test method names
grep -n "^\s*def " file.groovy | grep -v "void\|static\|private\|protected"
```

`def "should return premier upgrade only when blue removed"()` →
strip quotes, to snake_case → `should_return_premier_upgrade_only_when_blue_removed`

`def shouldReturnPremierOnly()` →
camelCase to snake_case → `should_return_premier_only`

### Kotlin

```bash
grep -n "^\s*fun test" file.kt
grep -n "@Test" file.kt -A1
```

`fun testShowPremierUpgradeWhenBlueRemoved()` → `show_premier_upgrade_when_blue_removed`

### Swift

```bash
grep -n "func test" file.swift
```

`func testShowPremierUpgradeOnlyWhenBlueRemovedFromConfig()` → `show_premier_upgrade_only_when_blue_removed_from_config`

Strip leading `test` prefix, apply camelCase → snake_case conversion.

### TypeScript / JavaScript

```bash
grep -n "it(\|test(\|describe(" file.spec.ts
```

`it('shows premier upgrade only when blue removed', ...)` →
strip quotes, lowercase, spaces → underscores → `shows_premier_upgrade_only_when_blue_removed`

### Python

```bash
grep -n "def test_" file.py
```

`def test_show_premier_upgrade_when_blue_removed():` → strip `test_` prefix → `show_premier_upgrade_when_blue_removed`

### Gherkin

```bash
grep -n "Scenario:" file.feature
```

`Scenario: User sees premier upgrade only when blue removed from config` →
lowercase, strip "scenario:", spaces → underscores → `user_sees_premier_upgrade_only_when_blue_removed_from_config`

### Normalisation algorithm (all languages)

```python
import re

def to_snake_case(text):
    # camelCase to snake_case
    text = re.sub(r'([A-Z])', r'_\1', text)
    # lowercase
    text = text.lower()
    # replace spaces, hyphens, and multiple underscores with single underscore
    text = re.sub(r'[\s\-]+', '_', text)
    text = re.sub(r'_+', '_', text)
    # strip leading/trailing underscores
    text = text.strip('_')
    # strip special chars (keep alphanumeric and underscore)
    text = re.sub(r'[^a-z0-9_]', '', text)
    return text
```

---

## Advanced: Multi-Repo Parallel Scanning

When scanning multiple repos, each repo can be processed independently. The TRACER orchestrator uses FORGE Pattern 5 (parallel batching) to scan repos concurrently.

Coverage maps from individual repos are merged by `behavior_name`:

```python
def merge_coverage_maps(maps: list) -> dict:
    merged = {}
    for coverage_map in maps:
        for behavior, layers in coverage_map.items():
            if behavior not in merged:
                merged[behavior] = []
            for layer in layers:
                # deduplicate: same test_id + layer_id = same entry
                key = (layer['layer_id'], frozenset(layer['test_ids']))
                if not any(
                    (l['layer_id'], frozenset(l['test_ids'])) == key
                    for l in merged[behavior]
                ):
                    merged[behavior].append(layer)
    return merged
```

---

## Agent Self-Check

Before the Repo Scanner Agent begins scanning, verify:

- [ ] All repo paths in `REPOS` are resolved (exist on disk, or remote URLs)
- [ ] `STASH_PAT` set when any repo URL contains `stash.barcapint.com`
- [ ] `GITLAB_PAT` set when any repo URL contains `gitlab.barcapint.com`
- [ ] `LAYER_REGISTRY_PATH` exists and is readable
- [ ] Temp clone directory (`/tmp/tracer-scan-*`) does not already exist before cloning
- [ ] Cleanup (`rm -rf`) is registered before clone begins (trap on EXIT)
- [ ] Language detection result logged per repo before scanning begins
- [ ] Layers with zero test files are listed in `red_flags`, not silently omitted
- [ ] `behavior_name` normalisation is applied consistently — no raw method names in coverage map
