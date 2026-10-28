# barclays-buk-plugin-testing-toolkit

Quality assurance and validation toolkit for Claude Code plugins. Run structured tests against any plugin directory to catch schema errors, missing files, and content issues before shipping.

## Install

```
/plugin install barclays-buk-plugin-testing-toolkit@barclays-cio-buk
```

## Commands

### `/test-plugin <path>`

Runs a full scored test suite — structure, content, and schema compliance — and returns a quality score out of 100.

```
/test-plugin ./my-plugin
```

| Score | Status |
|-------|--------|
| 90–100 | PRODUCTION READY |
| 70–89 | NEEDS MINOR FIXES |
| 50–69 | NEEDS WORK |
| < 50 | NOT READY |

### `/validate-plugin <path>`

Quick structural check only — validates `plugin.json` syntax and confirms all explicitly declared files exist on disk. Useful after edits or renames.

```
/validate-plugin ./my-plugin
```

## Typical Workflow

```
# 1. Quick check after editing plugin.json or moving files
/validate-plugin ./my-plugin

# 2. Full test before committing
/test-plugin ./my-plugin

# 3. Detailed report with per-check breakdown
/test-plugin ./my-plugin --report
```

## What Gets Tested

| Category | Points | Checks |
|----------|--------|--------|
| Structure | 40 | Valid JSON, declared files exist, naming conventions |
| Content | 40 | Agent frontmatter, capabilities, skill Quick Start, command docs |
| Schema compliance | 10 | commands/agents/hooks/author field formats |
| BUK compliance | 10 | buk- prefix, buk-standards dependency, skills frontmatter, source attribution, self-check checklist, autonomous operation, 7 principles |

See the `plugin-testing` skill for the full per-check point breakdown.

## Authoring a new plugin?

See [`docs/templates/AUTHORING.md`](../../../../docs/templates/AUTHORING.md) for templates and a principles compliance checklist.
