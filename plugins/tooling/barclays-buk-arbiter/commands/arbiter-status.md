---
name: arbiter-status
agent: arbiter-analyze-agent
allowed-tools: [Read, Bash]
description: "Show workflow progress and status dashboard"
---

# Status: Workflow Progress Dashboard

Show overall progress through the dead code removal workflow. Check what's done, what's pending, and next steps.

## Arguments

```
--details        Show detailed task list
--json           Output as JSON (parseable format)
--technology TECH   Target technology: java | ios (default: show all)
--module MODULE     Target a specific submodule/package (optional)
```

## Example

```
/arbiter-status
/arbiter-status --details
/arbiter-status --json

# iOS
/arbiter-status --technology ios
/arbiter-status --technology ios --details
```

## Output

Workflow status dashboard showing:
- Current phase (discovery, analysis, planning, execution, validation)
- Progress metrics (tasks completed, total tasks, effort completed vs planned)
- Recent activity (last 5 tasks executed)
- Pending tasks and blockers
- Recommended next step

## Next Step

Depends on current status:
- If discovery pending: Run `/arbiter-discover`
- If analysis pending: Run `/arbiter-analyze`
- If tasks pending: Run `/arbiter-remove next` or `/arbiter-validate`
- If complete: Celebrate! 🎉
