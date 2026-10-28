---
description: "Single source of truth for Python runtime detection, session state storage, and downstream invocation patterns. All capabilities (CG, STTM, DM) follow this contract to ensure deterministic Python availability handling."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-10-05
---

# Python Runtime Contract

> Detect once at init, store in session state, read downstream — never re-probe.

## 1. Detection Algorithm

Canonical probe order — used by `/init` (CG), `/sttm-init` (STTM), and `/dm-bra` (DM):

1. Run `python --version` — if exit code 0: use `python`, store detected version
2. If `PYTHON_PATH` environment variable is set and non-empty: use that value directly
3. Run `python3 --version` — if exit code 0: use `python3`
4. Run `py --version` — if exit code 0: use `py` (Windows launcher)
5. If all fail: store `python_path = null`, `python_version = null`

This check is **non-blocking** — initialization always continues regardless of result.

## 2. Session State Fields

| Field | Type | Set by | Description |
|-------|------|--------|-------------|
| `python_path` | string \| null | Init command | Resolved Python executable (`"python"`, `"python3"`, `"py"`, or a full path from `PYTHON_PATH`). `null` if none found. |
| `python_version` | string \| null | Init command | Version string from `--version` output (e.g. `"3.12.7"`). `null` if `python_path` is null. |

**CG** stores these in `session/session_state.json`.
**STTM** stores these in `output/sttm_session_state.json`.
**DM** stores as a local variable within the agent invocation (no persistent session).

Fields are set once at init and immutable for the session lifetime. Downstream commands and agents MUST read `python_path` from session state — never re-probe.

## 3. Guard Pattern

For commands/agents that run Python-dependent operations (syntax checks, validators, pytest). Use this pattern verbatim:

```
Read `session_state.python_path`.
If `python_path == null`: set `{result_field} = "skipped_no_python"`, log to audit, CONTINUE.
If available: proceed with `{python_path}` for Bash invocations.
```

Rules:
- **Never halt** on Python unavailability — always CONTINUE (generation works without Python)
- Set the appropriate `skipped_no_python` value so downstream gates (e.g. `/push`) can report it
- Log the skip to `session/audit_log.jsonl`

## 4. Invocation Pattern

For commands/agents that call Python inline (e.g. `python -c "..."` one-liners):

- **Always** use `{python_path} -c` where `python_path` comes from session state
- **Never** write bare `python -c` or `python3 -c` — those ignore session state and may not exist on the user's system
- If `python_path == null` and the operation is non-critical (JSON read/write): skip with warning, use Read/Write tools as fallback
- If `python_path == null` and the operation is critical (Excel generation via openpyxl): HALT with clear error and install instructions

For external package dependencies (`openpyxl`, `sqlglot`, `pytest`), check availability before use:

```
{python_path} -c "import {package}" 2>/dev/null
```

If the import fails, display:

```
⚠️ {package} not installed. Install: {python_path} -m pip install {package}
```

## 5. Bash Script Pattern

**Only** for shell hooks that run before session state may exist (e.g. `session-state-persist.sh` validates the JSON of the session file being written — reading that file for `python_path` would be circular).

```bash
PYTHON_CMD=""
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
elif [ -n "${PYTHON_PATH:-}" ]; then
  PYTHON_CMD="$PYTHON_PATH"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD="py"
fi
```

This is the **only** exception to the "never re-probe" rule. All other consumers MUST read from session state.

## 6. User Remediation

Standard warning when Python is not found (displayed at init):

```
⚠️ Python not found on PATH.
Impact:
  • Syntax validation (py_compile) will be SKIPPED on generated .py files
  • Test execution (pytest) will be SKIPPED
  • Excel export (openpyxl) will be UNAVAILABLE
  • All other artefact generation still works (no Python needed)
To enable:
  • Ensure 'python' is on PATH (most common)
  • export PYTHON_PATH="/path/to/python"
  • Or add to .claude/settings.json: { "env": { "PYTHON_PATH": "/path/to/python" } }
```
