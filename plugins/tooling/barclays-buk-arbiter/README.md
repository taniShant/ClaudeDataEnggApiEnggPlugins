# Arbiter: Safe Dead Code Removal for Java & iOS

Identify and safely remove dead code from Java and iOS (Swift/Objective-C) projects using call graph analysis and confidence-based batching.

## Prerequisites

- **Claude Code:** Version 2.1.110 or later
  - Check version: `/doctor`
  - Upgrade: `brew upgrade claude-code` or `npm install -g @anthropic-ai/claude-code@latest`
- **Java:** JDK 8+ (for compilation checks and AST analysis with Spoon)
- **Build System:** Gradle or Maven (auto-detected for target repo)
- **iOS/Swift:** Xcode 14+ and Swift 5.5+ (for iOS projects); xcworkspace/xcodeproj/SPM auto-detected
- **iOS analysis:** Python 3.10+ with tree-sitter —
  `pip install tree-sitter tree-sitter-swift tree-sitter-objc`
  (without them, iOS analysis falls back to regex and iOS removal is disabled)
- **Git:** For tracking removals and rollback capability

Dependencies are automatically installed:
- `barclays-buk-standards` — shared security, testing, and best practices

## Installation

### From Main Marketplace (Stable Release)

Once merged to the main BUK marketplace:

```bash
# Add the BUK marketplace (one-time setup)
/plugin marketplace add git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git

# Install the plugin
/plugin install barclays-buk-arbiter@barclays-cio-buk

# Sync to latest version
/marketplace sync barclays-cio-buk
```

The dependency `barclays-buk-standards` is automatically installed.

### Building the Plugin (Java Tool)

Arbiter uses a Spoon-based Java tool for true AST transformation. The tool must be built before use:

```bash
# From plugin directory
cd plugins/tooling/barclays-buk-arbiter

# Build the Spoon removal tool
./gradlew clean build

# Run tests
./gradlew test

# Verify JAR was created
ls build/libs/arbiter-removal-tool.jar
```

**Output:**
- `build/libs/arbiter-removal-tool.jar` — Fat JAR with Spoon and dependencies bundled
- `build/test-results/` — JUnit XML reports

**CI/CD:** JAR is automatically built during plugin installation.

**Troubleshooting:**
- ❌ "Cannot find Gradle" → Install Gradle (macOS: `brew install gradle`)
- ❌ "Cannot resolve dependencies" → CI has Nexus access; build should succeed in CI/CD
- ❌ "Java version too old" → Upgrade to JDK 8+ (plugin requires Java 8 minimum for Spoon)

### From Fork (Pre-Merge Testing)

To test before merge, install from the feature branch:

```bash
# Add your fork as a custom marketplace
/plugin marketplace add git@app.gitlab.barcapint.com:<your-gitlab-username>/buk.git

# Install the plugin from your fork (adjust marketplace name as needed)
/plugin install barclays-buk-arbiter@<your-fork-name>

# Update to latest commits on the feature branch
/marketplace sync <your-fork-name>
```

**Uninstall if needed:**
```bash
/plugin uninstall barclays-buk-arbiter
```

## Verification

After installation, verify the plugin is working:

```bash
# Check plugin status
/status arbiter-discover

# Test language detection on a Java project
/arbiter-discover /path/to/java/project

# Verify all commands are available
/arbiter-status
```

## Pre-Merge Testing (Feature Branch)

Before this plugin is merged to main, you can test it from the feature branch:

**Branch:** `feature/DIGICAW-4203-arbiter-plugin`

1. Get the fork URL from the merge request
2. Follow "From Fork" installation section above
3. Test core commands:
   ```bash
   /arbiter-discover /path/to/test/repo
   /arbiter-analyze /path/to/test/repo
   /arbiter-plan --sprints 2
   ```
4. Report issues or feedback in the MR discussion

**Quality gate status:**
- ✅ /test-plugin score: 93/100 (PASS)
- ✅ 5 agents + 6 skills + 6 commands
- ✅ All BLOCKING checks pass
- ✅ Installable from fork before merge

## Quick Start

### v1.0 Optimized Workflow (Recommended)

```bash
# 1. Combined Discovery & Analysis (v1.0: single scan, 35% token savings)
/arbiter-discover /path/to/repo

# 2. Plan: Create removal tasks with effort estimation (deterministic Python planner)
/arbiter-plan --sprints 2

# 3a. Remove ALL tasks at once (v1.0: 95% fewer commands!)
/arbiter-remove --all

# 3b. OR remove by category
/arbiter-remove --category SAFE    # Remove all SAFE first
/arbiter-remove --category LIKELY  # Then LIKELY
/arbiter-remove --category UNCERTAIN  # Then UNCERTAIN

# 4. Check status anytime
/arbiter-status
# Baseline is auto-established on first task (no explicit step needed)
```

**Expected performance:** 
- Token usage: 8-9K (35% savings vs legacy)
- Phases: 5 effective (cleaner workflow)
- User commands for 18 tasks: 3-4 total (90% reduction)

### Legacy Workflow (Still Supported for Backward Compatibility)

```bash
# Traditional step-by-step (still works, but not recommended)
/arbiter-discover /path/to/repo          # Detect languages
/arbiter-analyze /path/to/repo           # Build call graph
/arbiter-plan --sprints 2                # Create plan
/arbiter-remove next                     # Execute first task
# Repeat: /arbiter-remove next (18 times for 18 tasks)
/arbiter-validate --report               # Final verification
```

### Fast Path (Targeted Deprecation Removal)

```bash
# For a specific @Deprecated class (no repo scan needed):
/arbiter-deprecate com.example.LegacyService --dry-run
/arbiter-deprecate com.example.LegacyService --auto
```

**Use when:** You have a specific @Deprecated class marked for removal  
**Use full workflow when:** You want comprehensive dead code analysis

## Workflow Phases (v1.0: 5 Effective Phases)

| Phase | Command(s) | Duration | v1.0 Notes |
|-------|-----------|----------|-----------|
| **1: Discover-Analyze** | `/arbiter-discover` | ~15 min | Merged: single pass (was 2 separate phases) |
| **2: Plan** | `/arbiter-plan --sprints 2` | <1 min | Now deterministic Python planner |
| **3: Execute** | `/arbiter-remove --all` | Hours-Days | New batch modes reduce user commands 95% |
| **4: Verify** | `/arbiter-status` | Implicit | Baseline auto-established on first task |
| **5: Report** | `/arbiter-validate --report` | ~5-10 min | Optional final check |

**Removed:** Explicit "Preparation" phase (merged into Discovery); Explicit "Baseline" phase (implicit in Execute)  
**Token savings:** 13.5K → 8-9K (35% improvement)  
**User commands:** 6-20+ → 3-4 for full workflow (75-90% fewer)

## Commands

### `/arbiter-discover [PATH] [--quick] [--languages LANG] [--exclude PATTERNS]`

Detect languages, build systems, and frameworks. Recommends analyzer tier.

**Example:**
```bash
/arbiter-discover .
/arbiter-discover /path/to/repo --languages java,kotlin
/arbiter-discover . --quick  # Incremental (changed files only)
```

### `/arbiter-analyze [PATH] [--scope all|FILE] [--min-confidence 0-4]`

Build call graph, identify dead code candidates, assign confidence scores.

**Categories:**
- **SAFE (3.0-4.0):** Private methods/classes, no usage found
- **LIKELY (2.0-2.9):** May have indirect usage; review needed
- **UNCERTAIN (1.0-1.9):** Ambiguous; investigate first
- **KEEP (<1.0):** Too risky; do not remove

**Example:**
```bash
/arbiter-analyze .
/arbiter-analyze . --scope "src/main/**/*.java"
/arbiter-analyze . --min-confidence 2  # Skip uncertain
```

### `/arbiter-plan [--sprints N] [--scope CATEGORY] [--batch-size N]`

Convert findings into batched removal tasks with effort estimation.

**Example:**
```bash
/arbiter-plan                    # Default: 2 sprints, all categories
/arbiter-plan --sprints 3
/arbiter-plan --scope SAFE --batch-size 3
```

### `/arbiter-remove TASK_ID | next [--dry-run] [--no-commit]`

Execute removal task with validation gates (compile, unit tests, integration tests).

**Example:**
```bash
/arbiter-remove T001             # Execute task 1
/arbiter-remove next             # Execute next task in sequence
/arbiter-remove T005 --dry-run   # Show what would be removed
```

### `/arbiter-validate [--scope all|unit|integration] [--report]`

Verify compilation and test results. Compare to baseline for regressions.

**Example:**
```bash
/arbiter-validate
/arbiter-validate --scope unit
/arbiter-validate --report  # Generate detailed report
```

### `/arbiter-status [--details] [--json]`

Show workflow progress, pending tasks, and next steps.

**Example:**
```bash
/arbiter-status
/arbiter-status --details
/arbiter-status --json  # Parseable format
```

### `/arbiter-deprecate CLASS_NAME [--auto] [--dry-run] [--review]`

**Fast removal of a specific deprecated class.** Bypasses full repository discovery and baseline phases—targets a single @Deprecated class for streamlined analysis and removal.

**Arguments:**
- `CLASS_NAME`: Fully qualified class name (e.g., `com.barclays.mobile.gateway.operation.data.ClientLogging`)
- `--auto`: Auto-approve removal if categorized as SAFE (age ≥1 year, forRemoval=true, 0 usages)
- `--dry-run`: Show what would be removed without committing
- `--review`: Skip auto-approval; always prompt for confirmation

**Example:**
```bash
/arbiter-deprecate com.barclays.mobile.gateway.operation.data.ClientLogging --dry-run
/arbiter-deprecate com.barclays.mobile.gateway.operation.data.ClientLogging --auto
/arbiter-deprecate com.example.api.LegacyService --review
```

**Output:**
- Deprecation metadata (@Deprecated annotation, age, forRemoval flag)
- Replacement class (extracted from JavaDoc)
- Usage count in repository
- Categorization: SAFE | REVIEW | CONSULT
- Removal decision and validation results

**Categorization:**
- **SAFE (confidence ≥3.0):** @Deprecated + forRemoval=true + age ≥1 year + 0 usages → Auto-approvable with `--auto`
- **REVIEW (2.0-2.9):** 6-12 months old, <5 usages → Manual review required
- **CONSULT (<2.0):** <6 months old OR unclear replacement OR 5+ usages → Team approval required

**Workflow (vs. full 6-phase workflow):**

| Step | Full Workflow | Deprecate Shortcut |
|------|---|---|
| Discovery | Full repo scan | Skip (target class only) |
| Analysis | Full repo analysis | Target class + deprecation |
| Baseline | Establish baseline | Auto-verify |
| Planning | Multi-task plan | Single task plan |
| Execution | Iterate tasks | Execute single task |
| Verification | Full validation | Compile + unit tests |

**Token usage:** ~5-7K (vs ~13.5K for full workflow)

**When to use:**
- ✅ You have a specific @Deprecated class to remove
- ✅ Quick removal without full repository scan
- ✅ Class marked @Deprecated(forRemoval=true)
- ❌ For multiple deprecated classes, use `/arbiter-analyze` + `/arbiter-plan` + `/arbiter-remove`

## iOS Workflow

> **How the iOS analysis works, what it protects, results on `barclays-app` and known
> limitations:** see [docs/iOS-ANALYSIS-v1.6-OVERVIEW.md](docs/iOS-ANALYSIS-v1.6-OVERVIEW.md).

### Quick Start (iOS)

```bash
# 1. Combined Discovery & Analysis (detects entities, builds call graph, scores confidence)
/arbiter-discover /path/to/ios-app --technology ios

# 2. Plan: Create batched removal tasks (Objective-C candidates are listed for review only)
/arbiter-plan --technology ios --sprints 2

# 3. Execute removals (with xcodebuild validation, failure attribution + per-batch rollback)
/arbiter-remove --technology ios --all

# 4. Check status
/arbiter-status --technology ios

# 5. Final verification (includes the predicted-vs-actual calibration report)
/arbiter-verify --technology ios --scheme MyApp
```

### iOS Commands

| Command | Purpose |
|---------|---------|
| `/arbiter-discover [PATH] --technology ios` | Detect iOS project, build call graph, score confidence |
| `/arbiter-analyze [PATH] --technology ios` | Alias for discover (combined phase on iOS) |
| `/arbiter-plan --technology ios [--sprints N]` | Generate batched removal plan |
| `/arbiter-remove --technology ios [TASK\|next\|--all]` | Execute removal with xcodebuild validation |
| `/arbiter-validate --technology ios [--report]` | Run compilation + tests, compare baseline |
| `/arbiter-verify --technology ios` | Final post-removal verification + calibration report |
| `/arbiter-status --technology ios` | Show workflow progress |

### iOS Confidence Scoring

The iOS engine uses the same 0-4 arbiter scale with iOS-specific deductions:

| Signal | Deduction | Impact |
|--------|-----------|--------|
| Entry point (@main, app delegate) | Auto-KEEP | Score = 0 |
| iOS lifecycle method (viewDidLoad, etc.) | Auto-KEEP | Score = 0 |
| React Native bridge (RCT_EXPORT_*) | Auto-KEEP | Score = 0 |
| Storyboard/XIB customClass | -2.5 | → UNCERTAIN |
| @IBAction / @IBOutlet | -2.0 | → LIKELY |
| @objc / @objcMembers | -1.5 | → LIKELY |
| Override method | -2.0 | → LIKELY |
| Public/open access | -1.0 | Minor |
| Protocol conformance (Codable, etc.) | -0.7 to -1.0 | Minor |
| SwiftUI property wrappers | -0.7 | Minor |

### iOS-Specific Features

- **Resource scanning:** Detects class references in storyboards, XIBs, and plists
- **Dynamic dispatch detection:** NSSelectorFromString, NSClassFromString, performSelector, KVC
- **Framework rules:** 57 always-keep lifecycle methods, 19 annotation rules, 17 protocol rules
- **xcodebuild validation:** Compile + test gates after each batch
- **Auto-rollback:** Git backup branch + automatic revert on failure

---

## Confidence Scoring

Entities are scored 0-4 based on evidence of usage:

| Tier | Score | Criteria | Risk |
|------|-------|----------|------|
| **SAFE** | 3-4 | Private, no external refs, not framework-annotated | Low |
| **LIKELY** | 2-2.9 | May have indirect usage, framework annotations | Medium |
| **UNCERTAIN** | 1-1.9 | Ambiguous, reflection patterns, public visibility | High |
| **KEEP** | <1 | Critical, serialization, JNI, insufficient evidence | Critical |

### Confidence Deductions

```
Start: 4.0
-0.5: Public visibility (may be called externally)
-0.5: Spring/JUnit annotations (framework invocation)
-1.0: Reflection patterns (cannot resolve statically)
-1.0: @Scheduled/@Async (must not remove; entry point)
+0.5: @Deprecated (explicitly marked for removal)
-0.2: Test-only usage
-0.2: Implements interface (may override)

Result: Clamp to [0, 4]
```

## Batch Execution Strategy

1. **Start with SAFE:** Low risk, quick validation
2. **Then LIKELY:** If SAFE succeeds; requires review
3. **Finally UNCERTAIN:** If LIKELY succeeds; requires investigation

**Never skip phases.** Build confidence iteratively.

## Validation Gates

Each removal task has 2 mandatory gates (3 for LIKELY/UNCERTAIN):

1. **Compile Gate:** Code must compile post-removal
2. **Unit Test Gate:** All unit tests must pass
3. **Integration Test Gate:** (LIKELY/UNCERTAIN only)

**Automatic rollback** if any gate fails.

## Effort Estimation

| Category | Batch Size | Effort/Task | Example |
|----------|-----------|-------------|---------|
| **SAFE** | 5 | 0.5-1h | 10 tasks × 0.75h = 7.5h |
| **LIKELY** | 3 | 1-2h | 8 tasks × 1.5h = 12h |
| **UNCERTAIN** | 1 | 2-4h | 5 tasks × 3h = 15h |

**Total:** ~34h spread over 2-3 sprints.

## Sprint Integration Options

### Option 1: Dedicated Sprint
- Allocate full sprint to dead code removal
- Focus: Execute all planned tasks
- Validation: Continuous throughout sprint

### Option 2: Incremental Per Sprint
- Allocate 20% of capacity
- Execute 3-5 tasks per sprint
- Spread over 2-3 sprints

### Option 3: Post-Feature Cleanup
- After completing feature, run incremental scan
- Remove dead code introduced during feature work
- Keeps codebase continuously clean

## Best Practices

✅ **Do:**
- Start with full scan (establish baseline)
- Review confidence scores before planning
- Execute SAFE category first
- Commit after each successful task
- Maintain clean baseline (all tests passing)
- Consult engineers for @Deprecated code
- Track false positives to improve accuracy

❌ **Don't:**
- Skip validation gates (except for testing)
- Remove @Deprecated without consultation
- Batch too many entities per task
- Proceed with failing baseline
- Remove confidence <40% (KEEP category)
- Rush execution (quality over speed)

## False Positives: Learning from Failures

If a removal fails (validation gate breaks):

1. **Record the failure:**
   - Entity removed
   - Why confidence was too high
   - What pattern was missed

2. **Fix the scoring:**
   - Update deductions for similar entities
   - Improve pattern detection

3. **Example:**
   ```
   Entity: calculateLegacy()
   Confidence: 90% (SAFE)
   Actual usage: Spring @Scheduled task (not detected)
   Fix: -50% for methods in @EnableScheduling classes
   ```

## Dependencies

**Required:**
- Java 8+ (for building and running Spoon removal tool)
- Gradle or Maven (build system for Arbiter plugin and target repo)
- Git (for incremental scans and commits)

**Java Tool Dependencies (in Arbiter):**
- Spoon 10.4.0 (AST transformation; from Barclays Nexus)
- GSON 2.10.1 (JSON serialization)
- JUnit 4.13.2 (testing)

**iOS analysis (Python):**
- Python 3.10+ with `tree-sitter`, `tree-sitter-swift`, `tree-sitter-objc`
- Xcode 14+ (or `swift build` for Swift packages) for validation

**Optional:**
- JaCoCo (test coverage tracking)
- Checkstyle/PMD (code quality metrics)
- SonarQube (additional static analysis)

## Architecture

Two-layer design:
- **Markdown layer:** Commands, agents, skills (BUK marketplace routing)
- **Python layer:** Deterministic logic (language detection, call graph, validation hooks)

See ARCHITECTURE.md for deep dive.

## Plugin Principles

This plugin follows the 7 BUK Plugin Principles:

1. ✅ Standards from `barclays-buk-standards` (no duplication)
2. ✅ Framework-agnostic domain knowledge (skills reusable)
3. ✅ Extensible (base agents can be extended)
4. ✅ Independently invocable (explicit inputs/outputs)
5. ✅ Transparent flags (documents limitations, assumptions)
6. ✅ Owned & reviewed (Preetha Ramaswamy, quarterly cadence)
7. ✅ No workflow enforcement (agents suggest, user decides)

## Next Steps

After completing dead code removal workflow:

**Option 1: Incremental Maintenance**
```bash
/arbiter-discover . --quick  # Weekly scan
/arbiter-analyze --min-confidence 3  # Focus on SAFE
```

**Option 2: Expand Scope**
- Analyze different codebase
- Repeat 7-phase workflow

**Option 3: Deep Investigation**
- Research UNCERTAIN category
- May reclassify as SAFE/LIKELY after investigation

## Support

For issues or feedback:
- Check `/test-plugin ./plugins/tooling/barclays-buk-arbiter` for validation
- See ARCHITECTURE.md for technical details
- Review skills for domain knowledge

---

**Owner:** Preetha Ramaswamy  
**iOS author / owner:** Pratik Goswami  
**iOS contributors:** Naveen Kumar Reddy  
**Version:** 1.7.1  
**License:** Internal (Barclays)
