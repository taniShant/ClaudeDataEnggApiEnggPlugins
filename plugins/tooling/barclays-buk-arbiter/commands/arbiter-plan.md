---
name: arbiter-plan
agent: arbiter-plan-agent
allowed-tools: [Bash, Read, Write]
description: "Convert analysis findings into executable removal tasks with rollback strategies"
---

# Plan: Removal Task Generation

Convert dead code analysis into batched removal tasks with effort estimation and sprint allocation.

## Arguments

```
--sprints N          Number of sprints to allocate work (default: 2)
--scope CATEGORY     Filter by category: SAFE | LIKELY | UNCERTAIN (default: SAFE,LIKELY)
--batch-size N       Max entities per task (default: 5)
--effort-only        Just estimate effort, don't create tasks
--technology TECH   Target technology: java | ios (default: auto-detect)
--module MODULE     Target a specific submodule/package (optional)
```

## Technology Routing

| Technology | Agent |
|---|---|
| `java` | arbiter-plan-agent |
| `ios` | arbiter-plan-ios-agent |

If `--technology` is not provided, the technology is auto-detected (`*.xcodeproj`, `*.xcworkspace`, `Package.swift` → ios; `pom.xml`, `build.gradle` → java).

iOS batch sizes: SAFE=10, LIKELY=5, UNCERTAIN=1. Objective-C candidates go to the plan's `reviewOnly` list instead of removal batches.

## Example

```
/arbiter-plan
/arbiter-plan --sprints 3
/arbiter-plan --scope SAFE --batch-size 3
/arbiter-plan --effort-only

# iOS
/arbiter-plan --technology ios --sprints 2 --scope SAFE
```

## Output

Removal plan (YAML) with:
- Tasks batched by confidence category
- Estimated effort per task and total
- Sprint allocation
- Validation gates for each task
- Dependencies between tasks

## Next Step

Once plan is reviewed, run `/arbiter-remove T001` to execute first task, or `/arbiter-remove next` to execute sequentially.
