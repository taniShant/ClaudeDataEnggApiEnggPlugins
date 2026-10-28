---
name: plugin-testing
description: Master plugin testing, quality assurance, and validation. Learn unit testing, integration testing, and how to ensure plugin quality before deployment.
bonded_agent: plugin-tester
bond_type: PRIMARY_BOND
---

# Plugin Testing

## Quick Start

```bash
# Validate plugin structure
/validate-plugin ./my-plugin

# Run full test suite
/test-plugin ./my-plugin

# Generate detailed quality report
/test-plugin ./my-plugin --report

# Auto-fix common issues
/test-plugin ./my-plugin --fix-issues
```

## Testing Levels

### Unit Tests

Test individual components in isolation:

```markdown
Agent:
  ✅ YAML frontmatter valid and complete
  ✅ Description present and under 1024 chars
  ✅ Capabilities list has 3+ actionable items
  ✅ Content is 200+ lines
  ✅ Status and date included

Skill:
  ✅ name is lowercase-hyphens, under 64 chars
  ✅ Quick Start section with working code
  ✅ 3+ core concepts documented
  ✅ Advanced topics section present

Command:
  ✅ Usage examples with realistic input
  ✅ Options/flags documented in a table
  ✅ Example output shown
  ✅ Related commands listed
```

### Integration Tests

Test how components interact:

```markdown
Agent → Skill:
  ✅ Agent references skill in frontmatter
  ✅ Skill file exists and is accessible
  ✅ Relationship clearly documented

Command → Agent:
  ✅ Command invokes the correct agent
  ✅ Agent responds appropriately
  ✅ Workflow is coherent end-to-end

Plugin → Manifest:
  ✅ If agents/commands/skills fields are present, every referenced path exists on disk
  ✅ If fields are absent, Claude Code auto-discovers from agents/, skills/, commands/ directories
  ✅ No broken file references
```

## Test Checklist

### Structure Tests

```json
{
  "manifest_valid": {
    "description": "plugin.json parses as valid JSON",
    "check": "JSON.parse(plugin.json) throws no error"
  },
  "files_exist": {
    "description": "Every path explicitly declared in plugin.json exists on disk. If no paths are declared, Claude Code auto-discovers from standard directories — no check needed.",
    "check": "Stat each explicitly declared file path only"
  },
  "naming_correct": {
    "description": "Agent and command .md files follow lowercase-hyphens convention. SKILL.md is always uppercase by convention.",
    "check": "Agents/commands: ^[a-z0-9][a-z0-9-]*\\.md$  |  Skills: filename must be SKILL.md"
  },
  "no_broken_refs": {
    "description": "If agents/commands/skills fields are present in plugin.json, every referenced path must exist on disk. These fields are optional — Claude Code auto-discovers from standard directories when omitted.",
    "check": "Only validate paths that are explicitly declared in plugin.json"
  }
}
```

### Schema Compliance Tests

Key rules from the Claude Code plugin schema:

```markdown
commands field:
  ✅ Must be string or array of path strings
  ❌ NOT array of objects with name/file/description

agents field:
  ✅ Must be string or array of path strings
  ❌ NOT array of objects

hooks/hooks.json:
  ✅ hooks must be a record keyed by event name
     e.g. {"hooks": {"PostToolUse": [...]}}
  ❌ NOT an array of hook objects

author field:
  ✅ Must be object: {"name": "...", "email": "..."}
  ✅ Or omitted entirely
```

### Content Tests

```markdown
Agent files:
  ✅ YAML frontmatter valid
  ✅ description < 1024 chars
  ✅ capabilities has 3–10 items
  ✅ body is 200–400 lines
  ✅ markdown properly formatted

Skill files:
  ✅ YAML frontmatter valid
  ✅ name < 64 chars, lowercase-hyphens
  ✅ Quick Start code is runnable
  ✅ 3+ concepts explained with examples
  ✅ Advanced or real-project section present

Command files:
  ✅ Markdown is valid
  ✅ Usage is unambiguous
  ✅ All options documented
  ✅ Example output provided
  ✅ Next steps or related commands listed
```

### Functionality Tests

```markdown
Agent Invocation:
  ✅ Agent loads without error
  ✅ Content renders correctly in Claude Code
  ✅ Linked skills and agents are accessible
  ✅ No broken internal references

Skill Loading:
  ✅ Skill is accessible from its bonded agent
  ✅ Code examples are accurate and runnable
  ✅ All external links are functional

Command Execution:
  ✅ Command is recognised by Claude Code
  ✅ Options work as documented
  ✅ Output matches the documented example
  ✅ Next steps are actionable
```

## BUK Marketplace Compliance Tests

These checks are specific to the BUK CIO marketplace and are applied in addition to the generic structure and content tests above.

> **Governance reference:** [ADR 011.00 — Enterprise Claude Plugin Marketplace](https://app.gitlab.barcapint.com/barclays/dspe/architecture/-/blob/main/adr/ai-dev-tooling/011.00-claude-code-marketplace/README.md) defines the naming convention, tiered architecture, and governance model. The checks below implement the rules from that ADR for the `barclays-cio-buk` marketplace.

### BUK Structure Checks

```markdown
Plugin manifest:
  ✅ name conforms to ADR 011.00 naming convention: `barclays-buk-<name>` for BUK CIO Area plugins
  ✅ dependencies array includes "barclays-buk-standards"
  ✅ No agents/skills/commands paths declared (auto-discovery used)
  ✅ author field present with name and email

Agent files:
  ✅ skills: frontmatter field present and non-empty
  ✅ owner: frontmatter field present
  ✅ All cross-plugin skill references use "plugin-name:skill-name" syntax
  ✅ Referenced cross-plugin skills exist in the named plugin's skills/ directory
  ✅ Your Inputs block present (## Your Inputs section)
  ✅ Your Outputs block present (## Your Outputs section)
  ✅ Flags section present in output spec
  ❌ Agent body must NOT contain "FULLY AUTONOMOUSLY" or "Never ask the user" — workflow posture belongs in commands
  ❌ No stale `buk-` references without `barclays-` prefix (check subagent_type values, inline JSON, plugin name references)

Skill files:
  ✅ user-invocable field present (true or false)
  ✅ Source attribution header present (Source, Owner, Review trigger, Status)
  ✅ Agent Self-Check section present with at least 5 checklist items
  ✅ Placeholder skills state their status explicitly in the header

Command files:
  ❌ No stale `buk-` references without `barclays-` prefix (check "plugin" JSON fields, subagent_type values, install commands)

README files:
  ❌ No stale `buk-` references without `barclays-` prefix (check install commands, naming convention text, plugin name references)
```

**How to scan for stale names:** grep each file for `\bbuk-` and verify every match is preceded by `barclays-`. Flag any occurrence of bare `buk-<name>` as a stale reference.

**Exclusions:** BMAD agent short codes (`buk-qa`, `buk-sec`, `buk-pm`, etc.) in `workflows/bmad-buk-template/_bmad/custom/` and `workflows/bmad-integration.md` are BMAD persona identifiers, not plugin names — do not flag these.

### BUK Principles Compliance Checks

| Principle | Check |
|---|---|
| P1 — Single source of truth | No skill content duplicated from barclays-buk-standards |
| P2 — Framework-agnostic | Skill content contains no workflow step references |
| P4 — Independently invocable | Agent has `## Your Inputs` AND `## Your Outputs` sections |
| P5 — Transparent | Agent has `## Flags` section covering: placeholder skills, missing inputs, decisions under uncertainty |
| P6 — Owned and dated | Skill has Owner and Review trigger in source header; agent has `owner:` in frontmatter |
| P7 — No workflow enforcement | Agent body does NOT contain "FULLY AUTONOMOUSLY" or "Never ask the user" |

### BUK Scoring Addition

Add these to the total score (20 points):

| Check | Points | Deduction on fail |
|---|---|---|
| name has barclays-buk- prefix (ADR 011.00) | 3 | −3 |
| dependencies includes barclays-buk-standards | 5 | −5 (blocking for agents with skills) |
| No stale buk- references in any file content | 3 | −1 per file with violations (max −3) |
| Agent has skills: frontmatter | 4 | −4 |
| Skill has source attribution header | 4 | −4 |
| Skill has self-check checklist (5+ items) | 4 | −2 per missing item up to −4 |

---

## Scoring Rubric

Total score is out of 100. Tally points from each category, then apply the status threshold.

### Structure Tests — 40 points

| Check | Points | Deduction on fail |
|-------|--------|-------------------|
| plugin.json exists and is valid JSON | 15 | −15 (blocking) |
| All referenced files exist on disk | 15 | −5 per missing file |
| File naming: agents/commands lowercase-hyphens, skills use SKILL.md | 10 | −2 per violation |

### Content Tests — 40 points

| Check | Points | Deduction on fail |
|-------|--------|-------------------|
| Agent frontmatter complete (name, description, model, tools) | 10 | −3 per missing field |
| Agent capabilities list has 3+ items | 5 | −5 if absent or < 3 |
| Agent body is 200+ lines | 5 | −5 if under 200 lines |
| Skill has Quick Start section | 10 | −10 if absent |
| Skill name < 64 chars, lowercase-hyphens | 5 | −5 if violated |
| Each command has options table and example output | 5 | −3 per missing element |

### Schema Compliance Tests — 10 points

| Check | Points | Deduction on fail |
|-------|--------|-------------------|
| commands field is path strings, not objects | 3 | −3 |
| agents field is path strings, not objects | 3 | −3 |
| hooks.json uses record keyed by event name, not array | 2 | −2 |
| author field is object {name, email} or absent | 2 | −2 |

### BUK Compliance Tests — 10 points

| Check | Points | Deduction on fail |
|-------|--------|-------------------|
| name has barclays-buk- prefix (ADR 011.00) | 2 | −2 |
| dependencies includes barclays-buk-standards | 2 | −2 |
| Agent has skills: and owner: frontmatter | 2 | −1 per missing field |
| Agent has Your Inputs + Your Outputs + Flags sections | 2 | −1 per missing section (max −2) |
| No "FULLY AUTONOMOUSLY" / "Never ask the user" in agent body | 1 | −1 |
| Skill has source attribution header and self-check checklist | 1 | −1 |

### Status Thresholds

| Score | Status |
|-------|--------|
| 90–100 | PRODUCTION READY |
| 70–89 | NEEDS MINOR FIXES |
| 50–69 | NEEDS WORK |
| < 50 | NOT READY |

Any blocking failure (plugin.json missing or invalid JSON) caps the score at 0 regardless of other checks.

---

## Test Report Format

```markdown
PLUGIN TEST REPORT
═══════════════════════════════════════
Plugin: my-plugin
Version: 1.0.0
Date: 2026-01-18

STRUCTURE TESTS
  ✅ Manifest valid JSON       (5/5)
  ✅ Files exist on disk       (8/8)
  ✅ Naming conventions        (6/6)
  └─ Result: PASS

CONTENT TESTS
  ✅ Agents valid              (1/1)
  ✅ Skills valid              (1/1)
  ✅ Commands valid            (2/2)
  └─ Result: PASS

FUNCTIONALITY TESTS
  ✅ Agents invoke             (1/1)
  ✅ Skills load               (1/1)
  ✅ Commands execute          (2/2)
  └─ Result: PASS

QUALITY SCORE: 98% ✅
READY FOR PRODUCTION: YES ✅
═══════════════════════════════════════
```

## Common Test Failures

### JSON Syntax Error

```
❌ Error parsing plugin.json at line 15
   Missing comma after "name": "value"

Fix:
  "name": "value",   ← Add comma
  "version": "1.0.0"
```

### File Not Found

```
❌ Agent agents/missing.md referenced in plugin.json but not found on disk

Fix:
  1. Create the file at the referenced path, OR
  2. Remove the reference from plugin.json
```

### Invalid YAML Frontmatter

```
❌ YAML parse error in agents/plugin-tester.md

Fix:
  - Use two-space indentation (never tabs)
  - Quote values containing : or special characters
  - Verify list items use "- " prefix
```

### Content Too Short

```
⚠️  Warning: Skill SKILL.md is only 120 lines
   Recommended minimum: 200 lines

Fix:
  - Expand the Quick Start section with more examples
  - Add a second core concept with code
  - Include a real-world project example
```

### Invalid hooks.json

```
❌ Hook load failed: hooks — Invalid input: expected record, received array

Fix:
  Change from:
    {"hooks": [{...}, {...}]}

  To:
    {"hooks": {"PostToolUse": [{"matcher": "Write|Edit", "hooks": [...]}]}}
```

### Invalid commands field

```
❌ Manifest validation error: commands — Invalid input

Fix:
  Change from:
    "commands": [{"name": "foo", "file": "./commands/foo.md"}]

  To:
    "commands": ["./commands/foo.md"]
```

## Performance Baselines

```
Agent initialisation:  < 500ms ✅
Skill loading:         < 300ms ✅
Command execution:     < 2s    ✅
Full plugin load:      < 5s    ✅
```

### File Size Limits

```
Agent files:    < 400 lines  ✅
Skill files:    < 300 lines  ✅
Command files:  < 150 lines  ✅
plugin.json:    < 50KB       ✅
```

## Automated Testing

```bash
# Quick structural check (< 1 min)
/validate-plugin ./my-plugin

# Full test suite (< 5 min)
/test-plugin ./my-plugin

# Full suite with verbose quality report
/test-plugin ./my-plugin --report --verbose

# Watch mode: re-run on file changes
/test-plugin ./my-plugin --watch
```

## Pre-Deployment Checklist

```markdown
[ ] All structure tests pass
[ ] All content validation passes
[ ] No broken file references
[ ] Schema compliance verified (commands, hooks, agents as path strings)
[ ] Performance within baselines
[ ] Documentation complete and clear
[ ] All code examples tested and runnable
[ ] Error messages are descriptive
[ ] Integration workflows verified
[ ] Manual smoke-test completed

BUK Marketplace:
[ ] Plugin name conforms to ADR 011.00: starts with "barclays-buk-"
[ ] dependencies includes "barclays-buk-standards"
[ ] No stale buk- references in any file (grep \bbuk- and verify each match is preceded by barclays-)
[ ] No agents/skills/commands paths declared in plugin.json (auto-discovery)
[ ] All agents have skills: frontmatter loaded
[ ] All agents have owner: frontmatter field
[ ] All agents have ## Your Inputs and ## Your Outputs sections
[ ] All agents have ## Flags section in output spec
[ ] No agent body contains "FULLY AUTONOMOUSLY" or "Never ask the user"
[ ] All skills have source attribution header (Source, Owner, Review trigger)
[ ] All skills have self-check checklist (5+ items)
[ ] 7 principles compliance verified (see docs/templates/AUTHORING.md)
[ ] Ready for marketplace submission
```

---

**Use this skill when:**
- Testing plugin components before committing
- Validating structure after reorganising files
- Checking quality metrics before deployment
- Finding and fixing issues reported by Claude Code
- Submitting a plugin to the marketplace

---

**Status**: ✅ Production Ready | **Bonded Agent**: plugin-tester
