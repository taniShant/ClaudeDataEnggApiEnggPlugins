---
description: "Create a new draw.io diagram from a description. Orchestrates actor -> sequential critique (logic then style) -> single fix round."
user-invocable: true
argument-hint: "[diagram-spec-or-filepath]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-drawio:create`, they want to create a new draw.io diagram.

## Input

The user provides the command argument (`$ARGUMENTS`) which is the **diagram spec**. It can be one of two forms:

### Form 1: Free text
The argument is the spec itself — a plain-text description of components, relationships, and flow.

Example: `/barclays-buk-drawio:create API Gateway connects to Auth Service and User Service. User Service connects to PostgreSQL database.`

### Form 2: File path
The argument is a path to a file containing the spec. Detect this by checking if the argument is a valid file path that exists on disk.

Example: `/barclays-buk-drawio:create ./specs/architecture.md`

When a file path is provided, **read the file** to extract the spec text before proceeding.

### Resolving the Spec

```
if $ARGUMENTS points to an existing file:
    spec = read the file contents
else:
    spec = $ARGUMENTS as-is
```

Store the resolved spec text — it is passed to both the actor and the logic critique agents.

### Output File Path

The user may optionally include an output file path in their spec or as part of the argument. If no output path is specified, choose a sensible default based on the spec content (e.g., `./architecture.drawio`). The output file must end in `.drawio`.

## Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| diagram-spec | yes | — | Free text description of diagram components and connections, OR a file path to a spec |
| output path | no | `<spec-derived-name>.drawio` | Path for the generated .drawio file (must end in `.drawio`) |

## Example Output

```
File created: ./architecture.drawio
Components: API Gateway (id=2), Auth Service (id=3), PostgreSQL (id=4)
Connections: API Gateway -> Auth Service, Auth Service -> PostgreSQL
Critique: Logic PASS, Style PASS (1 round, no fixes needed)
```

## Iron Law

**You (the main agent) NEVER read `.drawio` files directly.** All draw.io file I/O is handled by subagents. Draw.io XML files are verbose (100-200 tokens per mxCell) and have low information density, making them ideal for subagent delegation.

## Orchestration

### Round 1: Create

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Create a new draw.io diagram.

  SPEC:
  <paste the user's description/spec here>

  FILE PATH: <target file path>

  Consult the loaded style guide skill for all styling rules.
  Write the file, then return a concise summary (components, connections, file path).
  NEVER return raw XML.
```

Wait for the actor to finish and return its summary.

### Round 2: Logic Critique

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-logic-critique-agent"`:

```
prompt: |
  ORIGINAL SPEC:
  <paste the user's description/spec here>

  FILE PATH: <the file the actor wrote>

  Review the diagram for logical and factual correctness against the spec.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Check the verdict:**

- **FAIL** -> Go directly to Round 4 (Fix) with the logic critique's fixes. **Do NOT run the style critique** — it would waste tokens on a diagram that needs structural changes first.
- **PASS or PASS WITH NOTES** -> Proceed to Round 3.

### Round 3: Style Critique (only if logic passed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-style-critique-agent"`:

```
prompt: |
  FILE PATH: <the file the actor wrote>

  Review the diagram for styling consistency against the loaded style guide skill.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Check the verdict:**

- **PASS or PASS WITH NOTES** (and logic also passed) -> Done. Report the actor's summary to the user.
- **FAIL** -> Go to Round 4 (Fix) with the style critique's fixes.

### Round 4: Fix (single round, only if any critique failed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Update the diagram based on critique feedback.

  FILE PATH: <the file to update>

  FIXES REQUIRED:
  <paste fixes from whichever critique(s) failed>

  Read the existing file, apply all fixes, validate consistency, write the updated file.
  Return a concise summary of changes made. NEVER return raw XML.
```

**No further critique rounds.** After the fix round, report the results to the user.

### Flow Diagram

```
$ARGUMENTS (free text or file path)
        |
        v
  Resolve spec (read file if path, else use as-is)
        |
        v
   +---------+
   |  actor   | -- create diagram
   +---------+
        |
        v
  +--------------+
  | logic critic |
  +--------------+
         |
    PASS? --no--> skip style, go to fix
         |
        yes
         |
         v
  +--------------+
  | style critic |
  +--------------+
         |
    PASS? --no--> go to fix
         |
        yes
         |
         v
   Done. Report to user.

         -- fix path --

         v
   +---------+
   |  actor   | -- apply fixes (single round)
   +---------+
        |
        v
   Done. Report to user.
```

## Fallback Behavior

If the `barclays-buk-drawio:drawio-agent` subagent is unavailable, inform the user that the drawio plugin requires its agent subagents to function. Suggest they reinstall the plugin.

## What to Report to the User

At the end, tell the user:

1. **File path** of the created diagram
2. **Components** included (list of node labels)
3. **Connections** (list of relationships)
4. **Critique status** — how many rounds it took, final verdicts
5. **Any remaining issues** if max iterations were hit

Do NOT show raw draw.io XML to the user. Keep the response concise.
