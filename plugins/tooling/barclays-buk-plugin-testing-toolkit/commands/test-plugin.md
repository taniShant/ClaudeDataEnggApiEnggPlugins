---
name: test-plugin
description: Run comprehensive tests on a plugin — structure, content, functionality, and performance.
allowed-tools: Read, Glob, Grep, Bash
---

# /test-plugin — Test & Validate Plugin

## What This Does

Runs a comprehensive test suite against a plugin directory. Validates manifest JSON, checks all referenced files exist, reviews agent/skill/command content quality, and generates a scored report.

## Usage

```
/test-plugin <path>
/test-plugin <path> --full
/test-plugin <path> --report
/test-plugin <path> --fix-issues
/test-plugin <path> --verbose
```

## Options

| Option | Description |
|--------|-------------|
| `--full` | Run all test categories including performance |
| `--report` | Generate a detailed scored quality report |
| `--fix-issues` | Auto-fix simple issues (formatting, length warnings) |
| `--verbose` | Show per-file detail in output |
| `--watch` | Re-run tests on file changes |

## Example

```
$ /test-plugin ./my-plugin

PLUGIN TEST REPORT
═══════════════════════════════════════
Plugin: my-plugin
Version: 1.0.0

STRUCTURE TESTS                          (40 pts)
  ✅ Manifest valid JSON          +15
  ✅ All referenced files exist   +15
  ✅ Naming conventions           +10
  └─ Score: 40/40

CONTENT TESTS                            (40 pts)
  ✅ Agent frontmatter complete   +10
  ✅ Agent capabilities (5 items) +5
  ✅ Agent body (240 lines)       +5
  ✅ Skill Quick Start present    +10
  ✅ Skill name valid             +5
  ✅ Commands have options+output +5
  └─ Score: 40/40

SCHEMA COMPLIANCE                        (10 pts)
  ✅ commands field valid         +3
  ✅ agents field valid           +3
  ✅ hooks.json valid             +2
  ✅ author field valid           +2
  └─ Score: 10/10

BUK COMPLIANCE                           (10 pts)
  ✅ barclays-buk- prefix          +2
  ✅ barclays-buk-standards dep   +3
  ✅ skills: frontmatter          +2
  ✅ source attribution header    +2
  ✅ self-check checklist         +1
  └─ Score: 10/10

═══════════════════════════════════════
Quality Score: 100/100
Status: PRODUCTION READY ✅

Next: /validate-plugin <path> for a quick re-check after any edits
```

## Scoring

Scores are calculated from three categories totalling 100 points:

| Category | Points |
|----------|--------|
| Structure Tests | 40 |
| Content Tests | 40 |
| Schema Compliance | 10 |
| BUK Compliance | 10 |

| Score | Status |
|-------|--------|
| 90–100 | PRODUCTION READY |
| 70–89 | NEEDS MINOR FIXES |
| 50–69 | NEEDS WORK |
| < 50 | NOT READY |

A missing or invalid `plugin.json` is a blocking failure — score is capped at 0.

See the `plugin-testing` skill for the full per-check point breakdown.

## Test Categories

### Structure Tests
```
✅ plugin.json exists and parses as valid JSON
✅ Every explicitly declared path exists on disk (agents/commands/skills fields are optional)
✅ Agent/command files use lowercase-hyphens; skill files use SKILL.md (uppercase)
```

### Content Tests
```
✅ Agent frontmatter complete (name, description, capabilities)
✅ Agent description < 1024 chars, body 200–400 lines
✅ Skill name < 64 chars, Quick Start section present
✅ Command has options table and example output
```

### Functionality Tests
```
✅ Each agent loads without error in Claude Code
✅ Each skill is accessible from its bonded agent
✅ Each command executes and returns expected output
✅ No broken internal references or links
```

### Performance Tests (--full)
```
✅ Agent initialisation < 500ms
✅ Skill load time < 300ms
✅ Command execution < 2s
✅ File sizes within limits
```

## Auto-Fix Example

```
$ /test-plugin ./my-plugin --fix-issues

Auto-fixing issues...

✅ Fixed: Trailing whitespace in agents/plugin-tester.md
✅ Fixed: Missing newline at end of commands/test-plugin.md
⚠️  Warning: Skill content is 140 lines — manual expansion recommended

Fixed: 2 issues automatically
Review needed: 1 issue

Run /test-plugin ./my-plugin again to verify fixes
```

## Related Commands

- `/validate-plugin` — Quick structural check only (no content scoring)

---

**Status**: ✅ Ready | **Updated**: 2026
