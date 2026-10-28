---
description: Analyze production Service Call Table CSV against codebase to find dead service calls
argument-hint: <csv_path> [project_path]
user_invocable: true
---

You are the main Claude Code agent.

When the user runs `/analyze-dead-services`, they want to **cross-reference a production Service Call Table CSV** against `ServiceManager.doService()` calls in their MCA1 codebase to identify services that are never called in production (dead code).

## Step 1: Parse Arguments

Extract the following from the user's arguments:

- `csv_path` (required): Path to the Service Call Table CSV file. Must be an absolute path or relative to the current directory.
- `project_path` (optional): Path to the MCA1 project root. Defaults to `.` (current working directory).

If no `csv_path` is provided, ask the user:
```
Please provide the path to your Service Call Table CSV file:
/analyze-dead-services <csv_path> [project_path]
```

## Step 2: Validate Arguments (MANDATORY)

Before delegating, validate:

1. **csv_path exists**: The CSV file must exist and be readable
2. **project_path exists**: The directory must exist
3. **Contains src/main/java**: Must have Java source files
4. **Has doService calls**: Quick check — run `grep -rn "doService(" <project_path>/src/main/ --include="*.java" | head -1` to confirm at least one call exists

If validation fails, report the specific error and stop.

## Step 3: Locate Plugin Root

Find the plugin installation path by searching for the skill file:

```
Glob: **/skills/dead-service-analysis/SKILL.md
```

Extract the plugin root from the result (everything before `/skills/dead-service-analysis/SKILL.md`).

## Step 4: Delegate to Dead Service Analyzer Agent

Use the Agent tool to launch the dead-service-analyzer-agent:

```yaml
subagent_type: barclays-buk-mca1-to-mca2-eps:dead-service-analyzer-agent

prompt: |
  Analyze dead service calls for the project.

  **CSV Path:** {csv_path}
  **Project Path:** {project_path}
  **Plugin Root:** {PLUGIN_ROOT}

  Your skill file is at: {PLUGIN_ROOT}/skills/dead-service-analysis/SKILL.md
  Read it first, then execute the full analysis workflow (Phases 1-8).

  PROJECT_PATH={project_path}
```

## Step 5: Report Results

After the agent completes, inform the user:

```
Dead Service Analysis complete.

Report generated at: {project_path}/DEAD-CODE-ANALYSIS.md

Next step: Run `/migrate-mca1-to-mca2 {project_path}` — Phase 7 will read this
report and ask you per dead service whether to keep as tech debt or remove altogether
(including properties).
```

## Error Handling

If the agent fails or the user cancels:
- Report what was accomplished before failure
- Suggest re-running with the same arguments to resume (agent supports resume detection)
