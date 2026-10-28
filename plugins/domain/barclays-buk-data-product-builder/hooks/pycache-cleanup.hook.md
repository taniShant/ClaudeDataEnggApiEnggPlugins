# Hook: pycache-cleanup

**Trigger**: PostToolUse — after any Bash command completes

**Purpose**: Remove Python compiled files (`__pycache__/`, `*.pyc`) that accumulate during `py_compile` syntax checks and `pytest` execution. Keeps the working directory clean.

---

## Behaviour

1. Find and remove all `__pycache__` directories under `${CLAUDE_PLUGIN_ROOT}` (plugin source tree)
2. Find and remove all `*.pyc` files under `${CLAUDE_PLUGIN_ROOT}`
3. Repeat for `generated/` in the user's project directory (test artifacts)
4. Exit 0 (always succeeds — idempotent, never blocks)

## Notes

- This hook is **non-blocking** — it never returns exit code 2
- Runs after EVERY Bash command (fast: ~50ms on empty directories, ~200ms with cache to clean)
- Idempotent: safe to run when no `__pycache__` exists (find exits cleanly)
- The `.gitignore` already excludes these files; this hook handles local disk cleanup
