# Detox — CWE Vulnerability Remediation Plugin

Automated security vulnerability remediation powered by Claude Code. Ingests SAST reports (Wiz) and threat model reports (Markdown), applies CWE-specific fixes, validates with WIZ CLI rescan and Semgrep, produces per-finding evidence records, and creates merge requests with atomic commits.

## Features

- **50 CWE skills** covering OWASP Top 10 and beyond (+ generic fallback)
- **CWE-937 dependency fix skill** — auto-upgrades vulnerable dependencies in build files (Maven, Gradle, npm, pip) with 3-stage validation (Nexus → JDK → Build)
- **Nexus integration** — validates package availability and auto-selects alternative versions when Wiz recommendation unavailable
  - **Fixed Nexus URL parsing** (Sept 2026) — corrected hostname vs. path distinction for `barcapint.com` Nexus URLs, enabling successful artifact lookups
- **JDK compatibility checking** — detects repository JDK version and validates compatibility before upgrade
- **Artifact rename support** — handles dependency upgrades with artifact ID changes (e.g., bcprov-jdk15on → bcprov-jdk18on)
- **OAuth2 token fallback** — git clone with embedded `oauth2:token` credentials to avoid interactive prompts
- **Enhanced tool detection** — Semgrep and GitLab CLI discovery across Windows/Linux/macOS paths with fallback to common locations
- **Improved preflight reporting** — detailed error messages showing exactly which tools are missing and why (e.g., "glab (not authenticated)")
- **Wiz integration** with flexible JSON parsing (SAST & SCA findings)
- **WIZ CLI rescan** — primary fix verification using the bank's strategic security tool (closed-loop proof)
- **Evidence & Accountability Framework** — per-finding evidence records with VERIFIED / UNVERIFIED / FAILED classification
- **Evidence section** — script-generated evidence tables and rescan instructions embedded in the local `DETOX-REMEDIATION-REPORT.md` (no separate evidence file)
- **Fallback verification chain** — WIZ CLI (high confidence) → Semgrep (medium) → dep tree (low) → none
- **Dependency resolution verification** — for CWE-937 fixes, verifies vulnerable version removed from resolved tree (Gradle, Maven, npm, pip, Go, dotnet, Cargo) with BOM/override detection
- **WIZ CLI rescan** — primary fix verification using the bank's strategic security tool (closed-loop proof)
- **Evidence & Accountability Framework** — per-finding evidence records with VERIFIED / UNVERIFIED / FAILED classification
- **Evidence section** — script-generated evidence tables and rescan instructions embedded in the local `DETOX-REMEDIATION-REPORT.md` (no separate evidence file)
- **Fallback verification chain** — WIZ CLI (high confidence) → Semgrep (medium) → dep tree (low) → none
- **Dependency resolution verification** — for CWE-937 fixes, verifies vulnerable version removed from resolved tree (Gradle, Maven, npm, pip, Go, dotnet, Cargo) with BOM/override detection
- **AI-powered threat model parsing** for Markdown reports with deduplication
- **6 language patterns** (Python, Java, JavaScript, TypeScript, C#, Go)
- **Semgrep validation** — re-scans after each fix as secondary verification
- **Build & test verification** — ensures fixes don't break compilation
- **Security test generation** — automated regression tests for applied fixes (JUnit, Jest, pytest, etc.)
- **Remediation reporting** — comprehensive executive-level reports with full audit trail
- **Atomic commits** — one commit per CWE fix for easy review/revert with version selection rationale
- **Corrective action docs** — for infrastructure findings and unresolvable dependencies requiring manual remediation
- **FORGE architecture** — orchestrator-worker pattern with phase-gated execution (9 stages, 7 agents)
- **Pre-validated safe versions** — safe-versions.json with Nexus-confirmed dependency upgrades
- **Multi-language code fixes** — source code remediation across Python, Java, JS, TS, C#, Go

## Commands

| Command | Description |
|---------|-------------|
| `/barclays-buk-detox:remediate` | Full remediation pipeline: parse → classify → fix → validate → MR |
| `/barclays-buk-detox:report` | Generate comprehensive remediation report — holistic view of all activities |
| `/barclays-buk-detox:scan` | Run Semgrep SAST scan on a directory |
| `/barclays-buk-detox:validate` | Re-scan a file after fix to verify vulnerability eliminated |
| `/barclays-buk-detox:document-infra` | Generate corrective action docs for infra findings |
| `/barclays-buk-detox:usage` | Usage and ROI report from local telemetry |

## Quick Start

```bash
# Install the plugin from the BUK marketplace (barclays-buk-standards is installed automatically)
/marketplace add barclays-cio-buk git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git
/plugin install barclays-buk-detox@barclays-cio-buk
# Commands and agents are namespaced "barclays-buk-detox:" (e.g. /barclays-buk-detox:remediate)
# Python 3 must already be installed — Detox checks for python3, py -3 or python and stops if none works
# (it never installs Python). On first run, approve the `echo … | python3 …` prompt (or `py -3` / `python`
# on Windows) — Detox runs its deterministic scripts this way

# Full pipeline with SAST report (--model is mandatory)
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./wiz-report.json --jira PROJ-1234

# Full pipeline with threat model
/barclays-buk-detox:remediate --repo . --model opus --threat-model ./threat-model.md --jira PROJ-1234

# With security test generation
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./report.json --jira PROJ-1234 --generate-tests

# Remote repository with branch options
/barclays-buk-detox:remediate --repo https://app.gitlab.barcapint.com/barclays/digital-dss/DSS-COMMON-CONTAINER_V4 \
  --model opus \
  --threat-model "./AttackPaths.md" \
  --checkout-branch release/dss-aws-fw-v4-2026.01 \
  --new-branch feature/dss-aws-fw-v4-cwe-fixes-test

# Dry run (parse and classify only)
/barclays-buk-detox:remediate --repo . --model opus --wiz-report ./report.json --dry-run

# Generate a remediation report
/barclays-buk-detox:report --repo . --wiz-report ./wiz-report.json --jira PROJ-1234

# Generate report with corrective actions for infra findings
/barclays-buk-detox:report --repo . --threat-model ./threat-model.md --generate-corrective-actions

# Scan a directory
/barclays-buk-detox:scan ./src

# Validate a fix
/barclays-buk-detox:validate src/db/queries.py --cwe CWE-89

# Document infrastructure findings
/barclays-buk-detox:document-infra ./threat-model.md --output-dir ./docs/corrective-actions
```

## Architecture

```
/barclays-buk-detox:remediate command                    /barclays-buk-detox:report command
    │                                           │
    ▼                                           ▼
┌─────────────────────────────┐       ┌──────────────────┐
│  detox-orchestrator-agent   │       │ detox-report-agent│
│  9-stage pipeline           │       │ (standalone)      │
└─────────┬───────────────────┘       └──────────────────┘
          │
    ┌─────┼─────────┬──────────────┬──────────────┐
    ▼     ▼         ▼              ▼              ▼
┌───────┐ ┌───────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐
│Parser │ │ Fix   │ │ Validator  │ │  Scan    │ │  Test    │
│Agent  │ │ Agent │ │ Agent      │ │  Agent   │ │  Agent   │
└───────┘ └───────┘ └────────────┘ └──────────┘ └──────────┘
```

### Evidence & Verification Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EVIDENCE & ACCOUNTABILITY FLOW                       │
│                                                                         │
│  Stage 0: Preflight + WIZ Setup (wiz_setup.py)                          │
│    ├─ Check wizcli installed?                                           │
│    │    NO → Ask user: "Shall I install WIZ CLI for you?"               │
│    │         YES → auto-install per platform:                           │
│    │           macOS:   brew install --cask wizcli                      │
│    │           Windows: dev tool install wizcli  OR  winget install     │
│    │           Linux:   dev tool install wizcli  OR  curl download      │
│    │         NO  → proceed without WIZ (all evidence = UNVERIFIED)      │
│    │                                                                     │
│    ├─ Check wizcli authenticated?                                       │
│    │    NO → Ask user: "Shall I authenticate? Opens browser for SSO"    │
│    │         YES → wizcli auth --use-device-code (interactive)          │
│    │               OR  wizcli auth --id/--secret (CI/CD service acct)   │
│    │         NO  → proceed without WIZ (all evidence = UNVERIFIED)      │
│    │                                                                     │
│    └─ ✓ wizcli ready                                                    │
│                                                                         │
│  Stage 4: Before Fixes (WIZ already set up in Stage 0)                  │
│    └─ WIZ baseline scan (only if wiz_available = true)                  │
│         wizcli dir scan --path . --format json --no-publish             │
│         → Save as wiz-baseline-scan.json (pre-fix snapshot)             │
│                                                                         │
│  Stage 4: Apply Fixes                                                   │
│    └─ DETOX applies CWE fix (any CWE, any language)                     │
│         → Atomic commit per fix                                         │
│                                                                         │
│  Stage 5: Validate & Collect Evidence (FOR EVERY FIX)                   │
│    │                                                                     │
│    ├─ 5a. Semgrep rescan (existing)                                     │
│    │                                                                     │
│    ├─ 5b. Build & test validation (existing)                            │
│    │                                                                     │
│    ├─ 5c. Evidence collection (NEW — per finding)                       │
│    │    ┌──────────────────────────────────────────┐                    │
│    │    │  Priority 1: WIZ CLI rescan              │                    │
│    │    │    wizcli dir scan → compare with        │                    │
│    │    │    baseline → delta (resolved/persist/new)│                    │
│    │    │    Confidence: HIGH                       │                    │
│    │    │    Classification: ✅ VERIFIED            │                    │
│    │    │                                           │                    │
│    │    │  Priority 2: Semgrep (if WIZ unavailable) │                    │
│    │    │    Confidence: MEDIUM                      │                    │
│    │    │    Classification: ⚠️  UNVERIFIED          │                    │
│    │    │                                           │                    │
│    │    │  Priority 3: Dep tree (CWE-937 only)     │                    │
│    │    │    gradle/mvn/npm/pip/go/dotnet/cargo     │                    │
│    │    │    Confidence: LOW                        │                    │
│    │    │    Classification: ⚠️  UNVERIFIED          │                    │
│    │    └──────────────────────────────────────────┘                    │
│    │    → Produces evidence record per finding                          │
│    │                                                                     │
│    └─ 5e. Evidence gate check                                           │
│         → Every successful fix must have an evidence record             │
│                                                                         │
│  Stage 8: Report (DETOX-REMEDIATION-REPORT.md, local only)              │
│    └─ verification_manifest.py embeds the evidence section:             │
│         ✅ VERIFIED    — WIZ confirms finding resolved                  │
│         ⚠️  UNVERIFIED  — Semgrep/dep-tree only, WIZ not available      │
│         ❌ FAILED      — Verifier confirms finding still present        │
│         → Per-finding proof, accountability matrix, rescan commands:    │
│           wizcli dir scan --path . --format json --no-publish           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Stages (9-Stage FORGE Architecture)

1. **Setup Repo** — Clone repo, checkout source branch, create remediation branch with atomic commit support
2. **Parse Reports** — Parse Wiz SAST JSON and/or threat model Markdown into normalized vulnerability objects
3. **Classify Findings** — Categorize by CWE, severity, and remediation type (code_fix, infra_config, dependency, manual)
4. **Apply Fixes** — WIZ baseline scan, then route each CWE to appropriate skill, apply code changes, create atomic commits
5. **Generate Tests** — Create security regression tests for applied fixes (when `--generate-tests` enabled)
6. **Validate Fixes** — Re-scan with Semgrep, verify build passes, check test suite compliance
7. **Document Infra** — Generate corrective action documents for infrastructure/config findings requiring manual remediation
8. **Generate Report** — Produce comprehensive DETOX-REMEDIATION-REPORT.md with full audit trail, fix summary, CWE mappings
9. **Create MR** — Push branch to GitLab, create merge request with detailed summary table, enable auto-merge if CI passes

### Agent Roles

| Agent | Role | Writes Files |
|-------|------|:---:|
| `detox-orchestrator-agent` | Pipeline coordination, state management | State only |
| `detox-fix-agent` | Apply CWE-specific code fixes | Yes (assigned files) |
| `detox-parser-agent` | Parse SAST/threat model reports | No (read-only) |
| `detox-validator-agent` | Semgrep re-scan, build verification | No (read-only) |
| `detox-scan-agent` | Run Semgrep directory scans | No (read-only) |
| `detox-test-agent` | Generate security regression tests for CWE fixes | Yes (test files) |
| `detox-report-agent` | Generate comprehensive remediation reports | Yes (report docs) |

## Skills Architecture

The plugin uses 17 skill categories with 90+ individual skills.

> **How skills load.** Claude Code only registers top-level skills (`skills/<name>/SKILL.md`):
> `parsing`, `validation`, `remediation-standard`, `test-generation`, `language-patterns` and
> `cwe-reference`. Every other skill is nested (`skills/<group>/<name>/`) and is **not** registered —
> agents load it by path via `scripts/utils/resolve_skill.py` (`{"cwe": "CWE-79"}`,
> `{"language": "java"}` or `{"skill": "<group>/<name>"}`), always from the installed plugin.

| Category | Skills | Purpose |
|----------|--------|---------|
| `remediation-cwe/` | 47 + fallback | CWE-specific fix patterns and remediation logic |
| `language-patterns-individual/` | 6 | Language-specific fix patterns (Python, Java, JS, TS, C#, Go) |
| `validation-individual/` | 6 | Fix completeness, regression, rescan, test generation, test runner |
| `parsing-individual/` | 4 | SAST parser, threat model parser, deduplication, normalizer |
| `analysis/` | 4 | Code context analyzer, data flow tracer, dependency analyzer, vulnerability classifier |
| `documentation/` | 4 | Corrective action writer, JIRA ticket generator, remediation summary, report generation |
| `git-ops/` | 3 | Atomic commit, PR body generator, PR creator |
| `orchestration/` | 2 | Pipeline orchestrator, retry strategy |
| `repo/` | 3 | Clone & branch, structure analysis, tech stack detection |
| `test-generation/` | 1 | Security regression test generation patterns |
| `standards/` | 2 | Remediation standard doc, skills standard |
| `cwe-reference/` | 1 | CWE database and mapping reference |
| `language-patterns/` | 1 | Consolidated language pattern reference |
| `parsing/` | 1 | Report parsing logic reference |
| `validation/` | 1 | Validation rules reference |

## Supported CWEs

| CWE | Name | Category |
|-----|------|----------|
| CWE-20 | Improper Input Validation | Input |
| CWE-22 | Path Traversal | Input |
| CWE-78 | OS Command Injection | Injection |
| CWE-79 | Cross-Site Scripting (XSS) | Injection |
| CWE-89 | SQL Injection | Injection |
| CWE-90 | LDAP Injection | Injection |
| CWE-94 | Code Injection | Injection |
| CWE-95 | Eval Injection | Injection |
| CWE-117 | Log Injection | Injection |
| CWE-183 | Permissive Allowlist | Configuration |
| CWE-200 | Information Exposure | Information |
| CWE-209 | Error Message Exposure | Information |
| CWE-287 | Improper Authentication | Auth |
| CWE-290 | Auth Bypass by Spoofing | Auth |
| CWE-295 | Improper Cert Validation | Crypto |
| CWE-297 | Cert Host Mismatch | Crypto |
| CWE-306 | Missing Authentication | Auth |
| CWE-311 | Missing Encryption | Crypto |
| CWE-312 | Cleartext Storage | Crypto |
| CWE-319 | Cleartext Transmission | Crypto |
| CWE-321 | Hardcoded Crypto Key | Crypto |
| CWE-326 | Inadequate Key Strength | Crypto |
| CWE-327 | Weak Crypto Algorithm | Crypto |
| CWE-328 | Weak Hash | Crypto |
| CWE-347 | Improper Signature Verification | Crypto |
| CWE-348 | IP Spoofing | Auth |
| CWE-352 | CSRF | Web |
| CWE-384 | Session Fixation | Auth |
| CWE-400 | Uncontrolled Resource Consumption | Resource |
| CWE-434 | Unrestricted File Upload | Input |
| CWE-502 | Insecure Deserialization | Input |
| CWE-522 | Insufficiently Protected Credentials | Auth |
| CWE-532 | Sensitive Data in Logs | Information |
| CWE-601 | Open Redirect | Web |
| CWE-611 | XXE | Injection |
| CWE-614 | Insecure Cookie | Web |
| CWE-639 | Authorization Bypass (IDOR) | Auth |
| CWE-670 | Incorrect Control Flow | Logic |
| CWE-693 | Protection Mechanism Failure | Configuration |
| CWE-770 | Allocation Without Limits | Resource |
| CWE-787 | Buffer Overflow | Resource |
| CWE-798 | Hardcoded Credentials | Auth |
| CWE-862 | Missing Authorization | Auth |
| CWE-917 | Expression Language Injection | Injection |
| CWE-918 | SSRF | Web |
| CWE-937 | Using Components with Known Vulnerabilities | Dependency | Modifies build files (pom.xml, build.gradle, package.json, etc.) — see "Dependency & SCA Findings" section |
| CWE-942 | Permissive CORS | Web |
| CWE-1188 | Insecure Default | Configuration |
| CWE-1268 | Policy/Privilege Mismatch | Auth |
| CWE-1275 | Sensitive Cookie SameSite | Web |

Unmapped CWEs use the generic fallback skill.

## Supported Languages

| Language | Frameworks |
|----------|-----------|
| Python | Django, Flask, FastAPI, SQLAlchemy, psycopg2 |
| Java | Spring Boot, JDBC, Hibernate, Jakarta EE |
| JavaScript | Express, Node.js, React, pg, mysql2 |
| TypeScript | NestJS, Next.js, Express, Angular |
| C# | ASP.NET Core, Entity Framework |
| Go | net/http, gin, echo, database/sql |

## Input Formats

### Wiz Report (JSON — SAST or SCA)
Standard Wiz scanner output in JSON format. Accepts both SAST (Static Application Security Testing) and SCA (Software Composition Analysis) findings. The parser handles multiple Wiz JSON structures automatically.

### Threat Model Report (Markdown)
Markdown document with structured findings. Supports:
- Header-based format: `## ATK-INT-01: Title`
- Table-based format: `| ID | Title | Severity | CWE |`
- List-based format with inline metadata

## Dependency & SCA Findings

### CWE-937: Using Components with Known Vulnerabilities

Detox includes a specialized **CWE-937 skill** for remediating known-vulnerable dependencies. When Wiz SCA findings are tagged with **CWE-937**, they are automatically routed to the fix pipeline and dependencies are upgraded with comprehensive pre-fix validation.

**Supported build systems:**
- **Maven**: `pom.xml`, `gradle.properties`
- **Gradle**: `build.gradle`, `gradle.properties`, `libs.versions.toml`
- **npm/yarn/pnpm**: `package.json`
- **Python**: `requirements.txt`, `pyproject.toml`
- **Go**: `go.mod`

**CWE-937 fix process — 3-Stage Validation Pipeline:**

1. **Stage 1: Nexus Availability Check**
   - Verifies Wiz-recommended safe version exists in organization's internal Nexus repository
   - If unavailable: automatically searches for next suitable stable version that:
     - Is newer than current version (remediates CVEs)
     - Is available in Nexus
     - Avoids pre-release versions (alpha, beta, rc)
   - If suitable alternative found: auto-selects with detailed reason logged
   - If no alternative available: routes to manual review with corrective action guidance

2. **Stage 2: JDK Compatibility Validation**
   - Detects repository's JDK version from build files
   - Validates selected version is compatible with detected JDK
   - If incompatible: suggests either JDK upgrade or fallback to compatible version
   - Prevents build failures from Java version mismatches

3. **Stage 3: Build File Remediation**
   - Updates build file using project's existing version management pattern (ext block, gradle.properties, pom.xml properties, etc.)
   - Runs build validation to ensure fix doesn't break compilation
   - Creates atomic commit with full audit trail of version selection rationale

**Example:** Wiz SCA report finds `log4j:log4j:1.2.17` with CWE-937
- Stage 1: `ch.qos.reload4j:reload4j:1.2.26` not in Nexus → auto-selects `1.2.27` (available, stable, remedial)
- Stage 2: Verifies JDK 11 compatibility ✓
- Stage 3: Updates `build.gradle`, confirms build passes, commits atomically

### Nexus Integration

Detox queries Barclays' internal Nexus repository to:
- **Validate availability**: Confirms safe versions exist before proposing upgrades
- **Discover alternatives**: Searches for newer stable versions if Wiz recommendation is unavailable
- **Reduce manual work**: Auto-selects best available version rather than failing or requiring user intervention
- **Audit trail**: Logs all version selection decisions (Nexus status, JDK constraints, alternative rationale)

Authentication is via embedded credentials or environment variables (`NEXUS_USER`, `NEXUS_PASS`).

**Nexus URL Parsing (September 2026):**
- Fixed critical bug in `scripts/nexus/nexus_client.py` that prevented `/nexus` path prefix from being added to Barclays Nexus URLs
- **Root cause**: Substring check `/nexus" not in self.nexus_url` was matching the hostname portion (`nexus` in `://nexus.barcapint.com`) instead of checking only the URL path
- **Fix**: Updated to use `urllib.parse.urlparse()` to check only the path component before appending `/nexus`
- **Impact**: All 36 WIZ SCA findings in CLOUDITDECOUP repository (BouncyCastle + Log4j) are now properly classified for auto-remediation instead of falling through to manual review
- **Example**: `https://nexus.barcapint.com` is now correctly transformed to `https://nexus.barcapint.com/nexus` when needed, allowing V3 and V2 API calls to hit the correct endpoint

### Git & Tool Configuration

**Credential Handling:**
- Git clone uses `oauth2:{token}` embedded in URL (`https://oauth2:{token}@host/repo.git`) — avoids interactive prompts and HTTP header issues
- Supports fallback to `master` branch if `main` not found
- PAT tokens sanitized from error messages for security

**Tool Discovery:**
- **Semgrep**: Standard PATH lookup → Windows devhome paths (`C:\devhome\tools\python3.12\...`) → Linux/Mac `~/.local/bin` → handles zipapps and non-standard installations
- **GitLab CLI (glab)**: Same discovery pattern, with additional authentication status check
- **Preflight Check**: Detailed error reporting shows exactly which tools are missing and provides platform-specific installation instructions
  - Distinguishes between "not found" vs "found but not authenticated" (e.g., "glab (not authenticated)")
  - Links to Barclays-specific resources (Dev CLI, gitlabcli installation paths)

### Other Dependency Findings

Wiz SCA findings **without a CWE-937 tag** (or with unrecognized CWEs) are classified as `dependency` type and handled as follows:
- **Parsed and analyzed**: Full dependency information extracted (package name, current version, available updates)
- **Nexus validation attempted**: Checks if newer versions are available in Nexus for manual review
- **Recommended actions logged**: Dependency analyzer identifies safe upgrade paths
- **Jira ticket generated** (with `--jira` flag): Contains detailed remediation guidance with Nexus status and corrective actions
- **Not auto-fixed**: Requires manual verification and execution (run `npm update`, `mvn`, etc.)

This approach prioritizes safety for general dependency vulnerabilities while enabling full auto-remediation for CWE-937 when Wiz correctly tags them and Nexus validation succeeds.

## Observability & Telemetry

Detox records every pipeline run and exports it to the Barclays **Observe** platform over gRPC OTLP (→ Collector → FluentBit → CloudWatch → Observe dataset `claude_code_client`). This is the strategic, platform-owned path shared with Claude Code's own telemetry. Scripts live under `scripts/telemetry/`.

> **Prerequisite — mandatory Barclays user setup (hard block):** detox refuses to run unless the one-time Barclays Claude Code user setup has populated the four `barclays_*` attributes (`barclays_user_id`, `barclays_cio`, `barclays_team`, `barclays_user_email`) in `~/.claude/settings.json`. Stage 0 preflight (`require_barclays_setup`, default `true`) aborts the pipeline with setup instructions if any are missing — enforced in `prepare_pipeline.py` and again in `scripts/git/repo_setup.py`. This also supplies the user's CIO / Business Portfolio for adoption reporting.

### What's Captured

| Data | Description |
|------|-------------|
| **Pipeline events** | Phase transitions, fix outcomes, validation results, test results — each exported to Observe as its own `detox.<event_type>` record |
| **Run summaries** | One denormalized record per run (fixes, validations, tests, timing, cost). Counts are read from the run's state file `{repo}/.detox/state.json` (written by `prepare_pipeline.py` and `pipeline_state.py`, git-ignored), never from a model-written summary; a run whose counts look lost is flagged `state_incomplete` and reported with ⚠️ |
| **Identity** | Developer name/email, **CIO / Business Portfolio** (from `barclays_cio`), target repo, CI context |
| **Phase timing** | `started_at`, `ended_at`, `duration_ms` per phase |

### Export

At pipeline end detox sends the **whole run to Observe in a single gRPC batch**: the denormalized run summary (`detox.pipeline_run`, all `detox.*` fields) **plus every granular per-phase event** (each as its own `detox.<event_type>` record), carrying Barclays identity/CIO as labels. All records are flushed in one gRPC round-trip, so latency stays ~one send regardless of event count. Export is **always on and fire-and-forget**: an unreachable endpoint, missing deps, or a TLS failure fails silently without affecting the run. A dedup hit skips both the local write and the export, so one `job_id` is exported exactly once.

The transport library (`scripts/telemetry/plugin_observability.py`) is a **verbatim** copy of the strategic Barclays Observe library (shared with the astral plugin) — never edit it; re-sync by copying the upstream file. Detox's batch send (`send_many_to_observe`) and endpoint default live in `scripts/telemetry/observe_batch.py`. Query runs in Observe with:

```
filter labels.plugin_metric = "detox.pipeline_run"
filter detox.job_id = "<job id>"
```

**Prerequisites for export to reach Observe:**

- **gRPC/OTLP deps** — `grpcio`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`. **Stage 0 (preflight) CHECKS these and HARD-STOPS the run if any are missing — it does NOT install them.** detox exports every run to Barclays Observe, so they are a mandatory prerequisite that must be **pre-provisioned per machine** (onboarding / Dev CLI). If missing, preflight blocks before any fix work and prints the exact install command. To skip the gate (offline/air-gapped only), pass `require_telemetry_deps: false`. Install once manually:
  ```bash
  python3 -m venv ~/.claude/observe_venv
  ~/.claude/observe_venv/bin/pip install --prefer-binary grpcio opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
  ```
- **Endpoint** — defaults to `metrics.dev-ai-tooling.barclays.intranet:443` (applied by detox's `observe_batch.apply_endpoint_default()`, since the library itself requires the variable); override with `OTEL_EXPORTER_OTLP_ENDPOINT`. **Set it only in `~/.claude/settings.json` `env`, NEVER in a shell profile** (`.zshenv`/`.bashrc`) — a shell export silently wins and routes metrics to the wrong host (the #1 cause of "0 metrics on macOS").
- **CA trust** — read from `NODE_EXTRA_CA_CERTS` (the Barclays CA bundle path, e.g. `~/java-cacerts/tls-ca-bundle.pem` from the java-cacerts release; set by Barclays dev tooling). If unset, the library falls back to the system bundle (`/etc/ssl/cert.pem` on macOS, `/etc/ssl/certs/ca-certificates.crt` on Debian/Ubuntu, `/etc/pki/tls/certs/ca-bundle.crt` on RHEL), which usually lacks the Barclays internal CAs — so TLS to the collector fails. Make sure `NODE_EXTRA_CA_CERTS` is visible to Claude Code (set it in `~/.claude/settings.json` `env` if you launch Claude Code outside a shell that exports it).

See [`docs/telemetry.md`](docs/telemetry.md) for the full schema and architecture.

## Configuration

### Command Line Options

Key options passed via command flags:
- `--repo`: Project path or git URL (required)
- `--model`: Agent model to use — sonnet, opus, or haiku (required)
- `--wiz-report`: Path to Wiz report JSON (SAST or SCA findings; required unless `--threat-model` is provided)
- `--threat-model`: Path to threat model Markdown report (required unless `--wiz-report` is provided)
- `--severity`: Filter by severity level (critical, high, medium, critical+high, all) — default: all
- `--dry-run`: Parse and classify without applying fixes
- `--generate-tests`: Generate security regression tests for applied fixes (default: enabled)
- `--no-tests`: Skip test generation entirely
- `--test-mode`: Test generation scope — fast (2-3 tests) or full (5-7 tests) — default: fast
- `--jira`: JIRA ticket ID for commit messages (e.g., PROJ-1234)
- `--checkout-branch`: Source branch to checkout before applying fixes
- `--new-branch`: Branch name for remediation changes
- `--generate-corrective-actions`: (report command) Also produce corrective action docs

### Safe Versions Configuration

**File:** `config/safe-versions.json` — always read from the installed plugin (`${CLAUDE_PLUGIN_ROOT}/config/`), never from the target repo

Pre-validated safe versions for autonomous CWE-937 remediation. When a vulnerable dependency is found:
1. Check if package exists in `safe-versions.json`
2. If found and not expired: apply safe version autonomously
3. If not found or expired: generate corrective action document for manual review

**Lookup Precedence & Key Strategy:**
Entries are keyed by Maven artifact coordinate (group:artifact) only — never by version. When a finding reports `org.apache.logging.log4j:log4j-core` at any version (2.14.1, 2.17.2, 2.20.0, etc.), the lookup key is always `"org.apache.logging.log4j:log4j-core"` (no version suffix). This single generic entry covers all pre-safe vulnerable versions and maps them to a common safe target (e.g., all 2.x log4j versions below 2.24.0 upgrade to 2.24.0). This design eliminates lookup ambiguity: no duplicate entries, clear precedence (one package = one rule), and predictable behavior across Wiz finding variants. Version-specific entries are not supported to prevent conflicting remediation logic.

**Current entries include:**
- log4j 1.x → reload4j (drop-in replacement with artifact rename)
- Log4j 2.x patch updates (all pre-safe 2.x versions → 2.24.0)
- Spring Framework patch updates (5.3.x)
- Jackson core/databind/annotations (2.18.x, 2.19.x)
- Tomcat Embed (9.0.x)
- SnakeYAML (2.0)
- BouncyCastle bcprov-jdk15on → bcprov-jdk18on (CVE-2026-59650 fix with artifact rename)
- Commons Text, Jersey, Netty, and 10+ other components

**Artifact Rename Support:**
When a safe version requires a different artifact ID (not just a version bump), the `drop_in_replacement` strategy is used:
- `safe_version` field contains full `group:artifact:version` coordinate (e.g., `"org.bouncycastle:bcprov-jdk18on:1.85"`)
- Build remediation agent automatically applies exclude+add pattern: excludes old artifact globally, adds new artifact declaration
- Example: upgrading `log4j:log4j:1.2.17` to `ch.qos.reload4j:reload4j:1.2.26` (100% API-compatible, no code changes)

Maintainer: **Security Champions**  
Review Cadence: **Quarterly**  
Nexus Confirmation: All versions verified available in internal Nexus

## Differences from `vulnerability` Plugin

| Feature | `vulnerability` | `detox` |
|---------|----------------|---------|
| Focus | CVE dependency scanning | CWE source code remediation |
| Data Source | PRISMA MCP (real-time) | SAST reports + threat models |
| Fix Type | Dependency upgrades | Source code fixes |
| Languages | Java, Node.js | Python, Java, JS, TS, C#, Go |
| Validation | N/A | Semgrep re-scan + regression tests |
| Reporting | N/A | Executive-level remediation reports |
| Architecture | Simple delegation | FORGE (9-stage pipeline, 7 agents) |

## Local Implementation & Testing (September 2026)

### Bug Fix: Nexus URL Parsing

**File:** `scripts/nexus/nexus_client.py` (lines 34-40)

**Issue:** The URL path prefix check for Barclays Nexus was incorrectly matching the hostname portion of the URL, preventing the `/nexus` path from being appended.

**Original Code:**
```python
if "barcapint.com" in self.nexus_url and "/nexus" not in self.nexus_url:
    self.nexus_url = f"{self.nexus_url}/nexus"
```

**Problem:** The check `"/nexus" not in self.nexus_url` would match the substring `nexus` in `https://nexus.barcapint.com`, incorrectly concluding that `/nexus` was already present.

**Fixed Code:**
```python
if "barcapint.com" in self.nexus_url:
    parsed = urllib.parse.urlparse(self.nexus_url)
    if "/nexus" not in parsed.path:
        self.nexus_url = f"{self.nexus_url}/nexus"
```

**Solution:** Use `urllib.parse.urlparse()` to parse the URL into components and check only the path portion, correctly distinguishing between the hostname and the URL path.

### Validation Results

**Test Repository:** `C:\ROLB vul remed\CLOUDITDECOUP`  
**WIZ Report:** `gl_wiz_sca_report (20).json`  
**Model:** Opus  
**Date:** 2026-09-23

**Pipeline Results:**
- **Total vulnerabilities:** 36 (all CWE-937 dependency findings)
- **Successfully remediated:** 2/2
  1. **BouncyCastle** — Upgraded `bcprov-jdk15on:1.60` → `bcprov-jdk18on:1.85` (30 CVEs: 3 critical, 18 high, 9 medium)
  2. **Log4j** — Added constraints for `log4j-core:2.24.0` and `log4j-api:2.24.0` (6 CVEs: medium)
- **Validation:** 2/2 fixes passed Semgrep validation and build verification
- **Tests Generated:** 3 security regression test cases (negative, positive, boundary)
- **Branch:** `remediate-detox-20260923-064420` (3 atomic commits, ready for push)

**Key Outcomes:**
- Nexus lookup now succeeds for all artifacts, properly classifying findings as `auto_apply` instead of `manual`
- V3 API calls to Nexus now hit the correct endpoint
- V2 fallback API also receives correct URL paths when needed
- safe-versions.json lookup strategy works as designed

**Generated Reports:**
- `DETOX-REMEDIATION-REPORT.md` — Full audit trail with CWE mappings and fix rationale
- `corrective_actions_output/CA-CWE937-transitive-bouncycastle.md` — Follow-up action for transitive dependencies

## Contributing

Want to help improve Detox? Read the **[Contributing Guide](https://pages.gitlab.barcapint.com/prasad.edlabadkar/detox/assist/contributing)** for information on:
- Adding new CWE skills
- Extending language pattern support
- Improving fix validation logic
- Contributing security test patterns
- Reporting bugs and requesting features

Contributions from Security Champions, platform teams, and developers are welcome!

### Install-mode rules (read before changing agents, commands or skills)

Developers run Detox from the marketplace cache, not from this repo. Changes that work in the
monorepo can silently break there. Verified on Claude Code 2.1.302:

1. **Plugin paths:** write the literal text `${CLAUDE_PLUGIN_ROOT}` in commands/agents — Claude Code
   substitutes it with the install path. It is **not** an environment variable at runtime
   (`os.environ`, `$env:`, `%VAR%` are empty). Never use `plugins/tooling/...` or `$0`.
2. **Names:** agents and skills register under the `plugin.json` name, which must match the
   marketplace entry (`barclays-buk-<name>`, per CONTRIBUTING.md) — e.g.
   `subagent_type: "barclays-buk-detox:detox-fix-agent"`. Skill frontmatter `name:` must match
   its folder (lowercase, hyphens — no underscores).
3. **Nested skills** are not registered — load them with `scripts/utils/resolve_skill.py`.
   Files read by path get no `${CLAUDE_PLUGIN_ROOT}` substitution; use the resolver's `plugin_root`.
4. **Bundled config** (`config/*.json`) is trusted only from the plugin root, never the target repo.
5. **Bump the version** in both `.claude-plugin/plugin.json` and the marketplace entry.
6. **Python:** invoke Detox scripts with `{python}` (verified at startup: `python3`, `py -3` or
   `python`), never a hardcoded `python3` — it is often missing on Windows. Detox only checks for
   Python 3 and stops if it is absent; it never installs it.
7. **Run `python3 -m pytest scripts/tests/test_install_mode.py`** — it enforces rules 1–6.
8. **Test from a real install** before merging:
   ```bash
   export CLAUDE_CONFIG_DIR=/tmp/detox-test   # isolated — leaves your settings untouched
   claude plugin marketplace add /path/to/buk && claude plugin install barclays-buk-detox@barclays-cio-buk
   ```

## Changelog

### 2.6.2 (2026-10-27) — deterministic run telemetry

| # | Issue | Fix |
|---|---|---|
| 1 | Orchestrator kept pipeline state only in context and passed `run_recorder.py` a hand-built summary without vulnerabilities/fix results — runs exported 0 counts to Observe | Pipeline state persisted to `{repo}/.detox/state.json`; `run_recorder.py` reads counts from it |
| 2 | Missing or partial state was reported as a successful run | Run flagged `state_incomplete` / `state_file_missing` with a warning |
| 3 | Skipped phases emitted no event | New `phase.skipped` event |
| 4 | On the corporate network semgrep's online version lookup made `semgrep --version` exceed the 30s preflight timeout — an installed semgrep was reported missing | Preflight runs semgrep with `SEMGREP_ENABLE_VERSION_CHECK=0` |

### 2.6.1 (2026-10-22) — marketplace install fixes

| # | Issue | Fix |
|---|---|---|
| 1 | `CLAUDE_PLUGIN_ROOT` read as an env var (unset at runtime) — every script call hit `FATAL`, so `/barclays-buk-detox:remediate` stopped at preparation | All invocations use inline `${CLAUDE_PLUGIN_ROOT}` substitution |
| 2 | Agents launched as bare names, which do not resolve | All `subagent_type` values use `barclays-buk-detox:<agent>` |
| 3 | 87 of 93 nested skills (all CWE fixes, language patterns, documentation, git-ops) never registered | New `scripts/utils/resolve_skill.py`; agents load skills by path |
| 4 | Invalid `barclays-buk-barclays-buk-detox:` and `detox:telemetry-contract` skill references | Replaced with by-path loading |
| 5 | `safe-versions.json` path one directory too high in `prepare_pipeline.py` — safe-versions strategy silently disabled | Fixed path |
| 6 | Agent / CWE-937 skill read safe-versions from monorepo path `plugins/tooling/...` | Read from plugin root; fail loudly if missing |
| 7 | `cve-api-signatures.json` path unanchored — could be read from the target repo, letting a planted file mark a CVE unreachable | Read only from plugin root |
| 8 | Wiz CloudEvent reports (`vulnerabilityFindings.findings`) parsed as **0 findings** with `status: success` — test existed, parser code was never committed | `extract_findings_array` handles the CloudEvent envelope |
| 9 | Agent default models: orchestrator pinned to `claude-opus-4-5`, workers on `sonnet`. Defaults apply to `/barclays-buk-detox:scan`, `/barclays-buk-detox:validate`, `/barclays-buk-detox:report`, `/barclays-buk-detox:document-infra` (no `--model`) | All 8 agents default to `model: opus`; `/barclays-buk-detox:remediate --model` still overrides |
| 10a | Orchestrator stage hand-offs relied on one general rule to pass `--model`; build-remediation hand-offs had no `subagent_type` or model at all | Every hand-off names `subagent_type: "detox:<agent>"` and `model: "{model}"` |
| 10 | `test-generation` skill registered under two names (frontmatter `test_generation`) | Frontmatter matches folder |
| 11 | Barclays setup check ignored `CLAUDE_CONFIG_DIR` (hardcoded `~/.claude/settings.json`) | `claude_config_dir()` helper |
| 11a | `plugin.json` named the plugin `detox` while the marketplace lists `barclays-buk-detox` — the only plugin of 36 that differed; external resolvers using the marketplace name could not find Detox skills | Renamed to `barclays-buk-detox` per the `barclays-buk-<name>` convention. **Commands are now `/barclays-buk-detox:remediate`, `/barclays-buk-detox:scan`, etc.** |
| 11b | 85 skills used underscores in frontmatter `name:` (e.g. `telemetry_contract`), invalid under the Agent Skills spec | Every skill `name:` matches its folder |
| 12 | No guard against install-only regressions | `scripts/tests/test_install_mode.py` — namespace, plugin-name, skill-name, env-var, monorepo-path, skill-ref and version checks |

## Support

Questions, issues, or feedback? Join the team channel:

**[DETOX PRJ (Microsoft Teams)](https://teams.microsoft.com/l/channel/19%3A9GL7IOGlcyDTRMgstwSZCjVUv-wXKS-wB1e04lXiDvw1%40thread.tacv2/General?groupId=d6c698b2-28d9-4c29-9c68-6558353faabc&tenantId=c4b62f1d-01e0-4107-a0cc-5ac886858b23)**

Documentation: **[http://detox/](https://pages.gitlab.barcapint.com/prasad.edlabadkar/detox/)**

## Author
**Prasad Edlabadkar** - prasad.edlabadkar@barclays.com

**Shilpa Dhavale** - shilpa.dhavale@barclays.com

**Devesh Kumar** — deveshkumar@barclays.com
