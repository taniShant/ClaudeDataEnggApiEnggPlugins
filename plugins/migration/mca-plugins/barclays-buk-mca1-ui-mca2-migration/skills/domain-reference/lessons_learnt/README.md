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
├── my-mca1-service.md     (per-run file, named from project basename)
└── ...
```

**Format:** `{project-name}.md`

Where `{project-name}` is extracted from the project path using `basename "$PROJECT_PATH"`.

## File Structure

Each lessons learned file follows this template:

```markdown
# mca1-ui-mca2-migration - Lessons Learned

**Project:** {project-name}
**Date:** {YYYY-MM-DD}
**JIRA:** {JIRA-ID}
**Project Path:** {absolute-path}

---

## Phase-by-Phase Insights

### Phase 0: Project Setup & MCA1 Validation
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

### Phase 1: Codebase Analysis
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

### Phase 2: BDL→Blueprint-React Transformation
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

### Phase 3: Validation
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

## When Created

The lessons learned file is created automatically at the start of Phase 0 during workflow initialization.

## When Updated

The file is updated:
1. **During each phase** — When issues are encountered, append to the phase section
2. **At phase completion** — Summarize what worked and what didn't
3. **At workflow end** — Finalize with overall retrospective and update `PATTERNS.md`

## How to Use

### Before Starting a New Run

Review existing lessons learned files to avoid common pitfalls:

```bash
# List all lessons learned
ls -la .claude/skills/mca1-ui-mca2-migration/lessons_learnt/

# View a specific project's lessons
cat .claude/skills/mca1-ui-mca2-migration/lessons_learnt/my-mca1-service.md

# Search for specific issues across all projects
grep -r "Issue:" .claude/skills/mca1-ui-mca2-migration/lessons_learnt/
```

### During a Run

The orchestrator agent automatically updates the file. Manual intervention is rarely needed.

### After a Run

Review the lessons learned file and:
1. Identify patterns across multiple projects
2. Update agents based on findings
3. Share insights with the team

## What to Capture

- BDL components without direct Blueprint equivalents
- JMVC patterns that required auto-decision-agent
- Transform agent files that were incorrectly skipped
- Build gate failures and their root causes
- Lint errors introduced by the transformation
- TypeScript type errors from missing props

## What NOT to Capture

- Routine operations that went as expected
- Boilerplate information already in documentation
- Personal opinions without actionable insights
- Verbose technical details (those go in the run log)

## Integration with Run Log

The lessons learned file complements the run log:

| Artifact | Purpose | Content |
|---|---|---|
| `logs/mca1-ui-mca2-migration.log` | Detailed execution trace | Commands, timestamps, results |
| `lessons_learnt/{project}.md` | Strategic insights | What worked, what didn't, why, improvements |

## Continuous Improvement Workflow

```
Run 1 → lessons_learnt/project1.md → Review insights
                                    ↓
Run 2 → lessons_learnt/project2.md → Compare patterns → Update PATTERNS.md
                                    ↓
Run 3 → lessons_learnt/project3.md → Update agents/scripts
                                    ↓
Run 4 → ... (smoother process with accumulated knowledge)
```
