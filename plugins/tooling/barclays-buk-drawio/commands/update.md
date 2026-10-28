---
description: "Update an existing draw.io diagram based on user-requested changes. Orchestrates actor -> sequential critique (logic then style) -> single fix round."
user-invocable: true
argument-hint: "[target-file.drawio] [change-spec-or-filepath]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-drawio:update`, they want to update an existing draw.io diagram.

## Input

The command accepts `$ARGUMENTS` containing two parts:

### Argument 1: Target file (required)
The path to the existing `.drawio` file to update. This is always the **first** argument.

### Argument 2: Change spec (required)
The remaining argument(s) after the target file. Can be one of two forms:

**Form A: Free text** — the change description provided directly as text.

Example: `/barclays-buk-drawio:update ./arch.drawio Add a Redis cache between API Gateway and Database`

**Form B: File path** — a path to a file containing the change description.

Example: `/barclays-buk-drawio:update ./arch.drawio ./specs/add-cache.md`

### Parsing $ARGUMENTS

```
tokens = split $ARGUMENTS

# First token that ends in .drawio is the target file
target_file = first token matching *.drawio

# Everything after the target file is the change spec
remainder = everything after target_file in $ARGUMENTS

if remainder points to an existing file:
    change_spec = read the file contents
else:
    change_spec = remainder as-is
```

Store both `target_file` and the resolved `change_spec`.

## Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| target-file.drawio | yes | — | Path to the existing `.drawio` file to update |
| change-spec | yes | — | Free text change description, OR a file path to a change spec |

## Example Output

```
File updated: ./architecture.drawio
Changes: Added "Redis Cache" (id=5), added connection API Gateway -> Redis Cache
Current state: 4 components, 4 connections
Critique: Logic PASS, Style PASS (1 round, no fixes needed)
```

## Iron Law

**You (the main agent) NEVER read `.drawio` files directly.** All draw.io file I/O is handled by subagents.

## Gathering Context (if needed)

If the user's change request references existing components but you don't know what's currently in the diagram, dispatch a **read-only** Task first to extract a summary:

```
prompt: |
  Read the draw.io file at <file path>.
  Extract and return ONLY:
  - List of all cell values (component labels) with their IDs
  - List of all connections (source label -> target label via source/target attributes)
  - Swimlane structure if present (which cells are children of which containers)
  - Total mxCell count

  Do NOT return raw XML or cell details.
```

Use this summary to understand the current state before dispatching the actor.

## Orchestration

### Round 1: Update

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Update an existing draw.io diagram.

  FILE PATH: <existing file path>

  CHANGE REQUEST:
  <paste the user's change description here>

  ORIGINAL SPEC (if available):
  <paste original spec if the user provided it, otherwise omit>

  Consult the loaded style guide skill for all styling rules.
  Read the existing file, apply the requested changes, validate consistency, write the updated file.
  Return a concise summary of changes made (what was added/removed/modified).
  NEVER return raw XML.
```

Wait for the actor to finish and return its summary.

### Round 2: Logic Critique

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-logic-critique-agent"`:

```
prompt: |
  ORIGINAL SPEC / CHANGE REQUEST:
  <paste the user's original spec if available, plus the change request>

  FILE PATH: <the updated file>

  Review the diagram for logical and factual correctness against the spec/change request.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Check the verdict:**

- **FAIL** -> Go directly to Round 4 (Fix). **Do NOT run the style critique.**
- **PASS or PASS WITH NOTES** -> Proceed to Round 3.

### Round 3: Style Critique (only if logic passed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-style-critique-agent"`:

```
prompt: |
  FILE PATH: <the updated file>

  Review the diagram for styling consistency against the loaded style guide skill.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Check the verdict:**

- **PASS or PASS WITH NOTES** -> Done. Report the actor's summary to the user.
- **FAIL** -> Go to Round 4 (Fix).

### Round 4: Fix (single round, only if any critique failed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Apply critique fixes to the diagram.

  FILE PATH: <the file to update>

  FIXES REQUIRED:
  <paste fixes from whichever critique(s) failed>

  Read the existing file, apply all fixes, validate consistency, write the updated file.
  Return a concise summary of changes made. NEVER return raw XML.
```

**No further critique rounds.** After the fix round, report the results to the user.

## Fallback Behavior

If the `barclays-buk-drawio:drawio-agent` subagent is unavailable, inform the user that the drawio plugin requires its agent subagents to function. Suggest they reinstall the plugin.

## What to Report to the User

At the end, tell the user:

1. **File path** of the updated diagram
2. **Changes made** (what was added, removed, modified)
3. **Current state** — list of components and connections after the update
4. **Critique status** — how many rounds it took, final verdicts
5. **Any remaining issues** if max iterations were hit

Do NOT show raw draw.io XML to the user. Keep the response concise.
