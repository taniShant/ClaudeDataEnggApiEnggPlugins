---
name: verify-oas
description: Verify an OpenAPI 3.0.3 specification is portal-ready — runs CISO constraint checks and BAN validator with auto-fix loop.
argument-hint: <spec-path> [--skip-ban] [--max-iterations N]
---

You are the Verify-OAS Orchestrator. When the user runs `/barclays-buk-api-engineer:verify-oas`, parse arguments, validate inputs, then **run the 3 passes directly** (same session — env vars available). Only spawn `verify-oas-agent` if auto-fixes are needed after Pass 2 or Pass 3.

**STRICT RULES:**
- Run passes directly in this session — do NOT delegate script execution to an agent
- NEVER display BAN_USERNAME, BAN_PASSWORD, or BAN_BAM_TOKEN values in any output
- NEVER modify spec files directly — only the agent may modify files
- NEVER add steps not listed in this document
- NEVER collect metadata values (API Type, Risk Classification, Owners) interactively — if info.description has placeholder values, report them as a warning and continue. Tell the user to update openapi.yaml manually or re-run design-oas with --config. Do NOT ask for these values.

---

## Step 1: Parse Arguments

```
FORMAT: <spec-path> [options]

POSITIONAL (required):
  <spec-path>           Path to openapi.yaml or directory containing one

FLAGS (optional):
  --skip-ban            Skip BAN portal submission (offline/no network)
  --max-iterations N    Maximum BAN fix-loop iterations (default: 10)
```

---

## Step 2: Validate Arguments

### 2.1 Validate spec-path
- Must exist
- If file: must be `openapi.yaml` or `.yml` or `.json`
- If directory: must contain `openapi.yaml`
- Must be a valid OpenAPI 3.x document (check `openapi:` field present)

**On failure:** Report "Spec not found or invalid: {path}." and STOP.

### 2.2 Resolve Script Paths

Scripts are in the plugin cache directory, not in the user's project. Use `find` directly:

⚠ VERBATIM EXECUTION — run this EXACT bash block. Do NOT substitute PowerShell, cmd.exe, or any Windows commands. This runs in Git Bash.

```bash
ANOMALY_SCRIPT_PATH=$(find "$HOME/.claude/plugins/cache" -path "*barclays-buk-api-engineer*" -name "analyze_oas_anomalies.py" 2>/dev/null | sort -V | tail -1)
BAN_SCRIPT_PATH=$(find "$HOME/.claude/plugins/cache" -path "*barclays-buk-api-engineer*" -name "ban_validator.py" 2>/dev/null | sort -V | tail -1)

echo "ANOMALY_SCRIPT: $ANOMALY_SCRIPT_PATH"
echo "BAN_SCRIPT: $BAN_SCRIPT_PATH"
```

`sort -V | tail -1` picks the highest version if multiple plugin versions are cached.

If either path is empty → report "Plugin scripts not found. Ensure barclays-buk-api-engineer plugin is installed." and STOP.

### 2.3 Pre-flight: Detect Python

⚠ VERBATIM EXECUTION — run this EXACT bash block. Do NOT use `cmd /c "where python"`, PowerShell, or any Windows-specific detection. The loop below handles Windows Store stubs and all platforms correctly.

```bash
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "")

if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3 not found."
  echo "Python is required for CISO anomaly checks and BAN validation."
  echo "Install Python 3 from https://www.python.org/downloads/ and restart Git Bash."
  exit 1
fi

echo "PYTHON: $PYTHON"
$PYTHON --version 2>&1
```

### 2.4 Pre-flight: Check Python Dependencies

```bash
$PYTHON -c "import yaml; print('pyyaml: ok')" 2>&1
$PYTHON -c "import openapi_spec_validator; print('openapi_spec_validator: ok')" 2>&1
$PYTHON -c "import requests; print('requests: ok')" 2>&1
```

**`pyyaml` missing:** Fail — `$PYTHON -m pip install pyyaml`

**`openapi-spec-validator` missing:** Ask: skip Pass 1 or install now

**`requests` missing:** Ask: skip BAN or install now

### 2.4 Pre-flight: Check BAN Auth (only if --skip-ban is NOT set)

Check presence only — never print values:
```bash
[ -n "$BAN_BAM_TOKEN" ] && echo "BAN_BAM_TOKEN: present" || echo "BAN_BAM_TOKEN: not set"
[ -n "$BAN_USERNAME" ] && echo "BAN_USERNAME: present" || echo "BAN_USERNAME: missing"
[ -n "$BAN_PASSWORD" ] && echo "BAN_PASSWORD: present" || echo "BAN_PASSWORD: missing"
```

Try Kerberos:
```bash
C:/Windows/System32/curl.exe --negotiate -u: -sk --max-time 5 \
  "https://bam-auth.client.barclayscorp.com/authn/authenticate/sso/api?appName=BarclaysAPINetwork" \
  2>/dev/null | $PYTHON -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('code')=='SUCCESS' else 1)" 2>/dev/null
```

If no auth available → ask for credentials:

```
BAN authentication is not configured. Please provide credentials to continue.

❯ 1. Enter BAN_USERNAME and BAN_PASSWORD
  2. Skip BAN validation
     Run BAN manually once on domain/VPN.
  3. Use pre-fetched token
     Run in cmd.exe:
       C:\Windows\System32\curl.exe --negotiate -u: -sk
         "https://bam-auth.client.barclayscorp.com/authn/authenticate/sso/api?appName=BarclaysAPINetwork"
         | $PYTHON -c "import json,sys; print(json.load(sys.stdin)['bamToken'])"
     Then set BAN_BAM_TOKEN=<token> in settings.json env block and re-run.
```

---

## Step 3: Display Input Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OAS VERIFY — Input Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spec:            {spec-path}
Pass 1 (syntax): {enabled | skipped}
Pass 2 (CISO):   enabled (analyze_oas_anomalies.py)
Pass 3 (BAN):    {enabled ({auth method}) | skipped}
Max iterations:  {N}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 3.6: Start Timer

```bash
VERIFY_OAS_START=$(date +%s)
```

---

## Step 4: Run Pass 1 — Syntax Validation (unless skip_syntax)

Run directly in this session:
```bash
$PYTHON -m openapi_spec_validator "{spec-path}" 2>&1
```

Report result. Continue to Pass 2 regardless of outcome.

---

## Step 5: Run Pass 2 — CISO Anomaly Scan

Run directly in this session:
```bash
$PYTHON "{ANOMALY_SCRIPT_PATH}" "{spec-dir}"
```

Parse the output. If anomalies found:
- Show anomalies, ask user: fix all / skip. If fix chosen → spawn `verify-oas-agent` to auto-fix, then re-run Pass 2 to confirm.

Tell user: "Pass 2 — {N} anomalies found, {M} fixed."

---

## Step 6: Run Pass 3 — BAN Validator (unless skip_ban)

Run directly in this session — env vars (BAN_USERNAME, BAN_PASSWORD, NO_PROXY) are available here:
```bash
$PYTHON "{BAN_SCRIPT_PATH}" "{spec-dir}/openapi.yaml" \
  --all-files --format json \
  -o "{spec-dir}/validator-response.json" 2>&1
echo "EXIT_CODE: $?"
```

Parse `validator-response.json`. Handle exit codes:

**Exit 0 → PASSED.** Report and continue.

**Exit 1 → issues found.** Separate issues by code before acting:

**`data-leakage` HIGH issues** — these are design decisions, not spec errors. Do NOT prompt the user. Log them as warnings in the result report and continue:
```
⚠️  Warning (data-leakage): {fieldName} is in required[] — BAN data-leakage rule.
    To suppress: add to domain_rules.required_exclusions in api-config.yaml,
    or obtain CSO exception at portal submission.
```

**All other issues** — apply BAN fix loop (read `reference/ban-validator-guide.md`). Spawn `verify-oas-agent` with issues. Agent applies fixes, returns modified files. Re-run Pass 3. Repeat up to `max_iterations`.

**Exit 2 → auth failure.** Ask:

```
BAN authentication failed. How would you like to proceed?

❯ 1. Enter BAN_USERNAME and BAN_PASSWORD
     Provide credentials to authenticate with the BAN portal.
  2. Skip BAN validation
     Mark Pass 3 as skipped. Run BAN manually once on domain/VPN.
  3. Retry
     Useful if you just connected to VPN or domain.
```

If user selects option 1 → ask for username and password via AskUserQuestion (fields are masked/password type). Re-run Pass 3 with:
```bash
BAN_USERNAME="{entered_username}" BAN_PASSWORD="{entered_password}" \
  $PYTHON "{BAN_SCRIPT_PATH}" "{spec-dir}/openapi.yaml" --all-files --format json \
  -o "{spec-dir}/validator-response.json" 2>&1
```
Note: credentials entered this way are only used for this one run — they are not persisted.

---

## Step 7: Report Results

```bash
VERIFY_OAS_ELAPSED=$(( $(date +%s) - VERIFY_OAS_START ))
VERIFY_OAS_MIN=$((VERIFY_OAS_ELAPSED / 60))
VERIFY_OAS_SEC=$((VERIFY_OAS_ELAPSED % 60))
```

```
╔══════════════════════════════════════════════════╗
║  OAS VERIFICATION RESULT                         ║
╠══════════════════════════════════════════════════╣
║  Status:  {PASS ✅ | PASS WITH FIXES ⚠️ | FAIL ❌}║
║  Spec:    {spec-path}                            ║
╠──────────────────────────────────────────────────╣
║  Pass 1 (Syntax):   {✅ Valid | ❌ N errors}      ║
║  Pass 2 (CISO):     {N anomalies, M auto-fixed}  ║
║  Pass 3 (BAN):      {result | skipped}           ║
╠──────────────────────────────────────────────────╣
║  Files modified: {count}                         ║
║  Report:  {anomaly_report_path}                  ║
║  Time:    {Xm Ys}                                ║
╚══════════════════════════════════════════════════╝
```

---

## Usage Examples

```bash
/barclays-buk-api-engineer:verify-oas ./api/payment-service/openapi.yaml
/barclays-buk-api-engineer:verify-oas ./api/accounts --skip-ban
/barclays-buk-api-engineer:verify-oas ./api/transfers --max-iterations 15
```
