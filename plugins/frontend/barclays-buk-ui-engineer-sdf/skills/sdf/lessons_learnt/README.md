# Lessons Learned Repository

This directory stores lessons learned from plugin runs across all projects.

## Purpose

Centralize run insights so that:
- Future runs can reference past experiences
- Common issues and solutions are documented
- Workflow patterns can be improved iteratively
- Teams can learn from each other's runs

## File Naming Convention

Each project gets its own lessons learned file:

```
lessons_learnt/
├── README.md              (this file)
├── PATTERNS.md            (auto-maintained aggregate across all runs)
├── example-project.md     (blank template — copy for each new run)
├── my-service-api.md      (per-run file, named from project basename)
└── ...
```

**Format:** `{project-name}.md`

Where `{project-name}` is extracted from the project path using `basename "$PROJECT_PATH"`.

## File Structure

Each lessons learned file follows this template:

```markdown
# barclays-buk-ui-engineer-sdf - Lessons Learned

**Project:** {project-name}
**Date:** {YYYY-MM-DD}
**JIRA:** {JIRA-ID}
**Project Path:** {absolute-path}

---

## Phase-by-Phase Insights

### Phase 0: Figma Screen Discovery
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

### Phase 1: Blueprint Screen Generation
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

---

## Overall Retrospective

### What Went Well
1.

### What Could Be Improved
1.

### Action Items for Future Runs
1.
```

## What to Capture

- Figma URL parsing edge cases (missing node-id, private files)
- Blueprint component API mismatches found at validation
- TypeScript compilation errors and their fixes
- Screen detection false positives / misses
- VanillaLayout or Iron Rule violations found during validation
- Workarounds that worked

## What NOT to Capture

- Routine operations that went as expected
- Boilerplate information already in SKILL.md
- Verbose technical details (those go in the run log)
