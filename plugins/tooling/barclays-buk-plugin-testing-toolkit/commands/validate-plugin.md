---
name: validate-plugin
description: Quick structural validation of a plugin — checks manifest JSON and file references without full content scoring.
allowed-tools: Read, Glob
---

# /validate-plugin — Quick Plugin Validation

## What This Does

Performs a fast structural check: validates `plugin.json` syntax, confirms all referenced agent/skill/command files exist on disk, and flags any naming convention violations. Runs in seconds — ideal for a quick sanity-check after edits.

## Usage

```
/validate-plugin <path>
/validate-plugin <path> --verbose
```

## Options

| Option | Description |
|--------|-------------|
| `--verbose` | Show per-file pass/fail detail |

## Example

```
$ /validate-plugin ./my-plugin

VALIDATION RESULT
═══════════════════════════════
Plugin: my-plugin  v1.0.0

  ✅ plugin.json — valid JSON
  ✅ agents/plugin-tester.md — found
  ✅ skills/plugin-testing/SKILL.md — found
  ✅ commands/test-plugin.md — found
  ✅ commands/validate-plugin.md — found

═══════════════════════════════
5/5 checks passed ✅
STRUCTURE VALID
```

### Failure Example

```
$ /validate-plugin ./my-plugin

VALIDATION RESULT
═══════════════════════════════
Plugin: my-plugin  v1.0.0

  ✅ plugin.json — valid JSON
  ❌ agents/02-missing.md — NOT FOUND
  ✅ skills/plugin-testing/SKILL.md — found
  ✅ commands/test-plugin.md — found

═══════════════════════════════
3/4 checks passed ❌

Fix: Create agents/02-missing.md OR remove the reference from plugin.json
Then re-run: /validate-plugin ./my-plugin
```

## When to Use

- Immediately after editing `plugin.json`
- After renaming or moving files
- Before running the full `/test-plugin` suite
- As a lightweight CI check in a pre-commit hook

## Related Commands

- `/test-plugin` — Full test suite with content scoring and quality report

---

**Status**: ✅ Ready | **Updated**: 2026
