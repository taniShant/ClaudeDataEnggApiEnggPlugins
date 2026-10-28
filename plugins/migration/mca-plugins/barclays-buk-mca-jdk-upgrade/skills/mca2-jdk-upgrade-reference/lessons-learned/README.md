# Lessons Learned Repository

This directory stores lessons learned from MCA2 JDK 8→21 migrations across all projects.

## Purpose

Centralize migration insights so that:
- Future migrations can reference past experiences
- Common issues and solutions are documented
- Migration patterns can be improved iteratively
- Teams can learn from each other's migrations

## File Naming Convention

Each project gets its own lessons learned file:

```
lessons_learned/
├── README.md                           (this file)
├── mca-eps-explain-interest.md        (example)
├── mca-customer-profile-service.md
├── mca-transaction-api.md
└── ...
```

**Format:** `{project-name}.md`

Where `{project-name}` is extracted from the project path using `basename "$PWD"`.

## File Structure

Each lessons learned file follows this template:

```markdown
# MCA2 JDK Migration - Lessons Learned

**Project:** {project-name}
**Migration Date:** {YYYY-MM-DD}
**JIRA:** {JIRA-ID}
**Project Path:** {absolute-path}

---

## Phase-by-Phase Insights

### Phase 0: Analysis & Branch
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

### Phase 1: OpenRewrite
- **What Worked:**
- **Issues Encountered:**
- **Improvements for Next Time:**

... (all 8 phases)

---

## Overall Retrospective

### What Went Well
1.

### What Could Be Improved
1.

### Action Items for Future Migrations
1.

### Artifacts Generated
- Migration log: `logs/migration.log`
- Lessons learned: `.claude/skills/mca2_jdk_upgrade_reference/lessons_learned/{project-name}.md`
```

## When Created

The lessons learned file is created automatically at the start of Phase 0 during migration initialization.

## When Updated

The file is updated:
1. **During each phase** - When issues are encountered, append to the phase section
2. **At phase completion** - Summarize what worked and what didn't
3. **At migration end (Phase 8)** - Finalize with overall retrospective

## How to Use

### Before Starting a New Migration

Review existing lessons learned files to avoid common pitfalls:

```bash
# List all lessons learned
ls -la .claude/skills/mca2_jdk_upgrade_reference/lessons_learned/

# View a specific project's lessons
cat .claude/skills/mca2_jdk_upgrade_reference/lessons_learned/mca-customer-profile-service.md

# Search for specific issues across all projects
grep -r "Issue:" .claude/skills/mca2_jdk_upgrade_reference/lessons_learned/
```

### During Migration

The agent automatically updates the file. Manual intervention is rarely needed.

### After Migration

Review the lessons learned file and:
1. Identify patterns across multiple projects
2. Update migration scripts/agents based on findings
3. Share insights with the team
4. Update documentation with new best practices

## Common Insights to Document

### What to Capture

- Dependency version conflicts
- Missing libraries in Nexus
- Test failures and fixes
- Build configuration issues
- Performance problems
- Time-consuming steps
- Unexpected manual interventions
- Workarounds that worked
- Dead ends that didn't work

### What NOT to Capture

- Routine operations that went as expected
- Boilerplate information already in documentation
- Personal opinions without actionable insights
- Verbose technical details (those go in migration.log)

## Integration with Migration Log

The lessons learned file complements the migration log:

| Artifact | Purpose | Content |
|----------|---------|---------|
| `logs/migration.log` | Detailed execution trace | Commands, timestamps, results |
| `lessons_learned/{project}.md` | Strategic insights | What worked, what didn't, why, improvements |

Always reference both artifacts when troubleshooting or improving migrations.

## Continuous Improvement Workflow

```
Migration 1 → lessons_learned/project1.md → Review insights
                                          ↓
Migration 2 → lessons_learned/project2.md → Compare patterns
                                          ↓
Migration 3 → lessons_learned/project3.md → Update agents/scripts
                                          ↓
Migration 4 → ... (smoother process with accumulated knowledge)
```

## Example: Finding Common Issues

```bash
# Find all projects that had OpenRewrite issues
grep -l "Phase 1: OpenRewrite" .claude/skills/mca2_jdk_upgrade_reference/lessons_learned/*.md | \
  xargs grep -A 3 "Issues Encountered:"

# Find all dependency resolution problems
grep -r "dependency" .claude/skills/mca2_jdk_upgrade_reference/lessons_learned/ | \
  grep -i "issue"
```

## Best Practices

1. **Be specific** - "JUnit version 5.11.3 failed with X error" not "tests failed"
2. **Include resolution** - Always document what fixed the issue
3. **Estimate time lost** - Helps prioritize future automation
4. **Update promptly** - Don't wait until end of migration
5. **Cross-reference** - Link to migration.log for details
6. **Think future-focused** - "Next time, do X instead of Y"

## Questions?

For issues with lessons learned tracking:
- Check the agent file: `agents/mca-jdk-upgrade-agent.md`
- Review the migration log: `logs/migration.log`
