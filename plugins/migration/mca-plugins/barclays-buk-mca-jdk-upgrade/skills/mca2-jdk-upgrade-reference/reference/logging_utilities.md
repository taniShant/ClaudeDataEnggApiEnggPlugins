# Logging Utilities — MCA2 JDK Upgrade

## Overview

All migration operations MUST be logged to provide:
- Audit trail of all changes made
- Debugging information for failures
- Progress tracking for long-running migrations
- Evidence for verification and compliance

## Log File Location

Log file is created by the command and passed to all agents:
```
{project_path}/logs/migration.log
```

**Automatic Log Rotation**: When a migration starts, if `migration.log` already exists, it is automatically renamed to `migration_{timestamp}.log` (e.g., `logs/migration_20260222_143045.log`) to preserve the previous migration's logs.

## Log Format

All log entries use **tree-style format** with timestamps for readability and hierarchical structure:

```
[YYYY-MM-DD HH:MM:SS] PHASE N: {Phase Name}
[YYYY-MM-DD HH:MM:SS] ├─ {Description}
[YYYY-MM-DD HH:MM:SS] │  └─ {Sub-item}
[YYYY-MM-DD HH:MM:SS] └─ Phase N complete: SUCCESS | FAILED
```

### Timestamp Format
```bash
$(date -u +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u "+%Y-%m-%d %H:%M:%S")
```
Example: `2026-02-19 14:30:45`

### Tree Characters
- `├─` - Action or intermediate step
- `│  └─` - Sub-item or detail (nested under ├─)
- `└─` - Final item or phase completion

### Log Helper Function

Define this function in Phase 0 and use throughout all phases:

```bash
log() {
    timestamp=$(date -u +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" >> "$LOG_FILE"
    echo "[$timestamp] $1"
}
```

### Usage Examples

```bash
# Phase start
log "PHASE 0: Project Analysis & Branch Setup"
log "├─ Starting phase"

# Action with result
log "├─ Action: Creating branch feature/GENAIACCEL-1234"
log "│  └─ Command: git checkout -b feature/GENAIACCEL-1234"
log "│  └─ Result: SUCCESS"

# Action with sub-items
log "├─ Action: Searching Nexus for Spring Boot 3.5.x"
log "│  └─ Query: https://nexus-read.barcapint.com/.../spring-boot/maven-metadata.xml"
log "│  └─ Found versions: [3.5.0, 3.5.1, 3.5.2]"
log "│  └─ Selected: 3.5.2 (latest)"
log "│  └─ Result: SUCCESS"

# Warning
log "├─ Action: Running ./gradlew test"
log "│  └─ WARNING: Test coverage 85% (target: 90%)"
log "│  └─ Result: PARTIAL"

# Error
log "├─ Action: Running ./gradlew compileJava"
log "│  └─ ERROR: Compilation failed"
log "│  └─ Error details: Unresolved dependency at build.gradle:45"
log "│  └─ Result: FAILED"

# Phase complete
log "└─ Phase 0 complete: SUCCESS"
log ""
```

## Decision Logging (MANDATORY)

For every major decision in a phase, log the rationale to migration log:

**What qualifies as a "major decision":**
- Choosing to remove vs upgrade vs keep a dependency
- Choosing to comment out vs delete code
- Choosing one version over another when reference offers options
- Skipping a step due to "not applicable" condition
- Choosing to auto-fix vs report a build error

**Format:**
```bash
log "│  └─ DECISION: {What you decided}"
log "│     Reason: {Why you decided this}"
log "│     Reference: {Which file/line guided this decision}"
```

**Example:**
```bash
log "│  └─ DECISION: Remove gradle-tagversion-plugin"
log "│     Reason: Reference table states 'Not needed in Gradle 8 projects'"
log "│     Reference: reference/mca2_migration_reference.md (Section 1.5)"
```

---

## What to Log

### Phase Start/Complete (MANDATORY)
Log at the beginning and end of every phase using tree format:
```bash
log "PHASE {N}: {Phase Name}"
log "├─ Starting phase"
... (phase actions)
log "└─ Phase {N} complete: SUCCESS"
```

### Actions (MANDATORY)
Log every significant operation using tree structure:
- Branch creation/checkout
- File modifications (which files, what changed)
- Build commands (gradle/maven)
- Test runs
- Nexus searches
- Dependency updates
- Agent delegations

### Results (MANDATORY)
Log the outcome of every action using tree format:
- `Result: SUCCESS` for successful operations
- `WARNING:` prefix for non-fatal issues
- `ERROR:` prefix for failures (include error message and location)

### File Modifications
When modifying files, log:
```bash
log "├─ Action: Modifying build.gradle"
log "│  └─ Updating Spring Boot version"
log "│  └─ Changed: spring_boot: '2.7.12' → '3.5.2'"
log "│  └─ Result: SUCCESS"
```

### Nexus Searches
When searching Nexus, log the query and result:
```bash
log "├─ Action: Searching Nexus for mca-experience-common-starter"
log "│  └─ Query: https://nexus-read.barcapint.com/.../maven-metadata.xml"
log "│  └─ Found version: 3.0.0-RELEASE"
log "│  └─ Result: SUCCESS"
```

### Build/Test Commands
When running builds or tests, log the command and result:
```bash
log "├─ Action: Running ./gradlew clean build"
log "│  └─ Command: ./gradlew clean build -x test"
log "│  └─ Duration: 120s"
log "│  └─ Result: SUCCESS"
```

For failures:
```bash
log "├─ Action: Running ./gradlew test"
log "│  └─ Command: ./gradlew test --console=plain"
log "│  └─ ERROR: Tests failed - 5 failures in UserServiceTest"
log "│  └─ Result: FAILED"
```

### Agent Delegations
When delegating to sub-agents, log:
```bash
log "├─ Action: Delegate to test-fix-agent"
log "│  └─ Test class: UserServiceTest"
log "│  └─ Spawning agent via Task tool"
log "│  └─ Result: SUCCESS"
```

### Java Version Switching
When switching Java versions, log detection and switching:
```bash
log "├─ Action: Detect Java version manager"
log "│  └─ Found: jenv"
log "│  └─ Result: SUCCESS"
log "├─ Action: Switch to Java 8 for OpenRewrite"
log "│  └─ Command: jenv local 1.8"
log "│  └─ Verified: java -version shows 1.8"
log "│  └─ Result: SUCCESS"
log "├─ Action: Running OpenRewrite migration"
log "│  └─ Result: SUCCESS"
log "├─ Action: Switch to Java 21"
log "│  └─ Command: jenv local 21"
log "│  └─ Verified: java -version shows 21"
log "│  └─ Result: SUCCESS"
```

JAVA_HOME fallback:
```bash
log "├─ Action: Detect Java version manager"
log "│  └─ WARNING: jenv not available, using JAVA_HOME fallback"
log "│  └─ Result: PARTIAL"
log "├─ Action: Detecting Java installations"
log "│  └─ Found JDK 8: /usr/lib/jvm/java-8-openjdk"
log "│  └─ Found JDK 21: /usr/lib/jvm/java-21-openjdk"
log "│  └─ Result: SUCCESS"
log "├─ Action: Switch to Java 8"
log "│  └─ Set JAVA_HOME=/usr/lib/jvm/java-8-openjdk"
log "│  └─ Result: SUCCESS"
```

### Validation Checks
When running validation, log each check:
```bash
log "├─ Validation: Check #1 - Mixed javax/jakarta imports"
log "│  └─ Scanning all .java files"
log "│  └─ Result: PASS - No mixed imports found"

log "├─ Validation: Check #4 - Java 8 source/target"
log "│  └─ Checking build.gradle sourceCompatibility"
log "│  └─ ERROR: Found sourceCompatibility='1.8' at build.gradle:15"
log "│  └─ Result: FAIL"
```

## Log File Structure

A complete migration log follows this structure:

```
========================================
MCA2 JDK UPGRADE MIGRATION LOG
========================================
JIRA ID: GENAIACCEL-1234
Project: /Users/dev/projects/mca-service
Build Tool: gradle
Source Branch: develop
Target Group: capl
Started: 2026-02-19 14:30:45
Resume From: Fresh start
========================================

[2026-02-19 14:30:46] [PHASE_START] Phase 0: Project Analysis & Branch Setup
[2026-02-19 14:30:46] [ACTION] Creating branch feature/GENAIACCEL-1234 from develop
[2026-02-19 14:30:47] [SUCCESS] Branch created successfully
[2026-02-19 14:30:47] [ACTION] Scanning project structure
[2026-02-19 14:30:48] [SUCCESS] Found: build.gradle, src/main/java, Dockerfile
[2026-02-19 14:30:48] [ACTION] Detecting current versions
[2026-02-19 14:30:49] [SUCCESS] Java 8, Spring Boot 2.7.12, Gradle 7.6, JUnit 4
[2026-02-19 14:30:50] [ACTION] Creating Phase 0 commit
[2026-02-19 14:30:51] [SUCCESS] Committed abc123de
[2026-02-19 14:30:51] [PHASE_COMPLETE] Phase 0 completed successfully (5s)

[2026-02-19 14:30:52] [PHASE_START] Phase 1: OpenRewrite Automated Migration
[2026-02-19 14:30:52] [SUCCESS] jenv detected
[2026-02-19 14:30:53] [ACTION] Set Java version to 1.8 via jenv
[2026-02-19 14:30:54] [SUCCESS] Java 8 confirmed
[2026-02-19 14:30:54] [ACTION] Loading OpenRewrite configuration
[2026-02-19 14:30:55] [ACTION] Adding OpenRewrite plugin to build.gradle
[2026-02-19 14:30:56] [ACTION] Running OpenRewrite migration under Java 8
[2026-02-19 14:33:45] [SUCCESS] OpenRewrite completed successfully
[2026-02-19 14:33:46] [ACTION] Removing OpenRewrite plugin from build file
[2026-02-19 14:33:47] [ACTION] Set Java version to 21 via jenv
[2026-02-19 14:33:48] [SUCCESS] Java 21 confirmed
[2026-02-19 14:33:49] [ACTION] Creating Phase 1 commit
[2026-02-19 14:33:50] [SUCCESS] Committed def456ab
[2026-02-19 14:33:50] [PHASE_COMPLETE] Phase 1 completed successfully - Now using Java 21 (178s)
...
```

## Error Handling

When errors occur:
1. Log the error with `[ERROR]`
2. Include the error message
3. Include file location if applicable
4. Include command output if relevant
5. Log retry attempts

Example:
```bash
[ACTION] Running ./gradlew rewriteRun
[ERROR] OpenRewrite failed: Could not resolve dependency 'com.barclays.mca.recipe:mca-rewrite-spring:1.1.5'
[ACTION] Verifying Nexus connectivity and retrying
[SUCCESS] OpenRewrite completed successfully
```

## Best Practices

1. **Always log before and after actions** — helps track where failures occur
2. **Include context** — log file names, version numbers, specific values
3. **Log errors immediately** — don't wait until phase end
4. **Use consistent messages** — helps with log parsing and analysis
5. **Log timestamps** — essential for tracking duration and debugging
6. **Don't log sensitive data** — no passwords, tokens, or API keys
7. **Be specific** — "Updated 15 dependencies" is better than "Updated dependencies"

## Log Analysis

To analyze logs after migration:

### Count errors/warnings
```bash
# Current migration
grep "\[ERROR\]" logs/migration.log | wc -l
grep "\[WARNING\]" logs/migration.log | wc -l

# All migrations (including archived)
grep "\[ERROR\]" logs/migration*.log | wc -l
grep "\[WARNING\]" logs/migration*.log | wc -l
```

### View failed phases
```bash
# Current migration
grep "\[ERROR\]" logs/migration.log

# All migrations
grep "\[ERROR\]" logs/migration*.log
```

### Check phase durations
```bash
# Current migration
grep "PHASE_COMPLETE" logs/migration.log

# All migrations
grep "PHASE_COMPLETE" logs/migration*.log
```

### View Nexus lookups
```bash
# Current migration
grep "Searching Nexus" logs/migration.log

# All migrations
grep "Searching Nexus" logs/migration*.log
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-19
**Document Type:** Logging Utilities Reference
