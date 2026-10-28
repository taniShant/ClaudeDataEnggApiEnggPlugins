---
description: "Transform an image into a draw.io diagram. Orchestrates image analysis -> actor -> export -> parallel fidelity+logic critique -> style critique -> fix."
user-invocable: true
argument-hint: "[image-file.png] [output-file.drawio]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-drawio:transform`, they want to transform an image (screenshot, PNG, JPG, etc.) into a draw.io diagram.

## Input

The user provides `$ARGUMENTS` which contains one or two positional arguments.

### Argument 1: Image file path (required)

The path to the source image file. Must exist on disk and have a supported image extension: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`.

### Argument 2: Output file path (optional)

The path for the generated `.drawio` file. Must end in `.drawio`. If omitted, defaults to `<image_stem>.drawio` in the same directory as the image (e.g., `./arch.png` -> `./arch.drawio`).

### Parsing $ARGUMENTS

```
tokens = split $ARGUMENTS

# First token is the image file path (required)
image_file = tokens[0]

# Validate: file must exist and have a supported image extension
supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
if image_file does not exist OR extension not in supported_extensions:
    error: "Image file not found or unsupported format: <image_file>"

# Second token (if present) is the output .drawio path
if tokens[1] exists AND tokens[1] ends with ".drawio":
    output_file = tokens[1]
else:
    output_file = replace image_file extension with ".drawio"
```

Store both `image_file` and `output_file` for use throughout the orchestration.

## Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| image-file | yes | — | Path to source image (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`) |
| output-file.drawio | no | `<image_stem>.drawio` | Path for generated `.drawio` file |

## Example Output

```
Source image: ./screenshots/architecture.png
File created: ./screenshots/architecture.drawio
Components: API Gateway, Auth Service, User Service, PostgreSQL, Redis
Connections: 6 connections identified
Analysis notes: 1 label marked [?] — bottom-right text unclear
Critique: Fidelity PASS, Logic PASS, Style PASS WITH NOTES (2 rounds)
```

## Iron Law

**You (the main agent) NEVER read `.drawio` files directly.** All draw.io file I/O is handled by subagents.

**You also do NOT read the image file directly.** Image perception is handled by the image analysis subagent in Round 1.

## Orchestration

### Round 1: Image Analysis

Dispatch a **single** Task (subagent_type: `general-purpose`) to analyze the source image and produce a structured text spec:

```
prompt: |
  You are an image analysis agent. Your task is to examine a diagram image and produce
  an exhaustive structured text description that can be used to recreate the diagram.

  IMAGE FILE: <image_file path>

  INSTRUCTIONS:
  1. Read the image file using the Read tool (it will be presented visually).
  2. Examine every detail of the diagram carefully.
  3. Produce a structured description covering ALL of the following:

  ## Diagram Overview
  - Diagram type (flowchart, architecture, sequence, swimlane, org chart, network, etc.)
  - Overall flow direction (left-to-right, top-to-bottom, etc.)
  - Title or heading if present

  ## Components
  For EVERY component/node visible in the image, describe:
  - Exact label text (quote it precisely; flag uncertain text with [?])
  - Shape type (rectangle, rounded rectangle, diamond, cylinder, ellipse, hexagon, etc.)
  - Approximate position (top-left, center, bottom-right, etc.)
  - Relative size (small, medium, large)
  - Semantic role (service, database, external system, queue, user/actor, decision, etc.)
  - Grouping (is it inside a container, swimlane, or cluster?)

  ## Connections
  For EVERY connection/arrow visible in the image, describe:
  - Source component (exact label)
  - Target component (exact label)
  - Direction of the arrow
  - Label on the connection (if any; quote precisely, flag uncertain with [?])
  - Line style (solid, dashed, dotted)

  ## Layout
  - Spatial arrangement (grid, tree, layered, free-form)
  - Alignment patterns (horizontal rows, vertical columns, centered)

  ## Containers / Swimlanes
  If the diagram has containers, swimlanes, or grouping regions:
  - Container labels
  - Which components are children of each container

  ## Text Annotations
  - Any standalone text labels, legends, notes, or titles not attached to components

  ## Uncertainties
  - List anything you could not read clearly or are unsure about, flagged with [?]

  CRITICAL RULES:
  - Be EXHAUSTIVE. Missing a single component or connection will cause the recreation to be inaccurate.
  - Use EXACT label text. Do not paraphrase or summarize labels.
  - Return ONLY the structured text description. Do not attempt to create any files.
```

Wait for the analysis agent to return the structured text spec. Store this as `image_spec`.

### Round 2: Create Diagram (Actor)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Create a new draw.io diagram from the following description.
  This description was extracted from an image of an existing diagram.
  Your goal is to recreate the diagram as accurately as possible.

  SPEC:
  <paste the image_spec from Round 1>

  FILE PATH: <output_file path>

  IMPORTANT NOTES:
  - Preserve the spatial layout described in the spec as closely as possible.
  - Use the exact label text from the spec.
  - Recreate all connections with correct source, target, and direction.
  - Recreate containers/swimlanes and parent-child relationships if described.

  Consult the loaded style guide skill for all styling rules.
  The style guide colors take precedence over the original image colors —
  map each component's semantic role to the appropriate style guide color.

  Write the file, then return a concise summary (components, connections, file path).
  NEVER return raw XML.
```

Wait for the actor to finish and return its summary.

### Round 3: Export to Image

Export the generated `.drawio` file to a PNG so it can be visually compared against the source image.

Run via Bash:

```bash
python3 <path-to-plugin>/scripts/export_drawio.py <output_file> --format png --output <exported_image_path>
```

Where `<exported_image_path>` is `<output_file_stem>_exported.png` in the same directory as the output file.

If the export fails (script error, timeout, CDN unreachable), **skip the fidelity critique entirely** and proceed with logic critique only. Log the export failure in the final report.

### Round 4: Fidelity Critique + Logic Critique (in parallel)

Dispatch **two** Tasks **in parallel** (in a single message with two Task tool calls):

#### 4a: Fidelity Critique (visual comparison)

Dispatch with `subagent_type: "barclays-buk-drawio:drawio-fidelity-critique-agent"`:

```
prompt: |
  This diagram was created by transforming a source image into a .drawio file,
  then exporting the .drawio back to a PNG. Your job is to visually compare
  the two images and assess conversion fidelity.

  SOURCE IMAGE (original): <image_file path>
  EXPORTED IMAGE (from .drawio): <exported_image_path>

  Follow your review process:
  1. Read the SOURCE IMAGE. Extract all components, connections, groupings, flow direction.
  2. Read the EXPORTED IMAGE. Extract the same information.
  3. Cross-reference the two lists systematically.
  4. Produce your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).

  The SOURCE IMAGE is the ground truth. You do NOT read any .drawio XML.
  You do NOT check colors/styling — only content fidelity.
```

#### 4b: Logic Critique

Dispatch with `subagent_type: "barclays-buk-drawio:drawio-logic-critique-agent"`:

```
prompt: |
  This diagram was created by transforming an image into a .drawio file.

  TEXT SPEC (extracted from the image by an analysis agent):
  <paste the image_spec from Round 1>

  FILE PATH: <output_file path>

  Review the diagram for logical and structural correctness against the text spec.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Wait for both to complete, then process results:**

#### Decision Logic

| Fidelity (4a) | Logic (4b) | What Happens |
|----------------|------------|-------------|
| PASS/NOTES | PASS/NOTES | Proceed to Style Critique (Round 5) |
| FAIL | PASS/NOTES | Actor fixes fidelity (1 iteration), then proceed to Style Critique |
| PASS/NOTES | FAIL | Skip style, go to Round 6 Actor fix for logic issues |
| FAIL | FAIL | Actor fixes fidelity (1 iteration), then Round 6 Actor fix for logic issues |

### Round 5: Style Critique (only if logic passed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-style-critique-agent"`:

```
prompt: |
  FILE PATH: <output_file path>

  Review the diagram for styling consistency against the loaded style guide skill.
  Return your structured critique with verdict (PASS/FAIL/PASS WITH NOTES).
```

**Check the verdict:**

- **PASS or PASS WITH NOTES** -> Done. Report the results to the user.
- **FAIL** -> Go to Round 6 (Fix) with the style critique's fixes.

### Round 6: Fix (single round, only if logic or style critique failed)

Dispatch a **single** Task with `subagent_type: "barclays-buk-drawio:drawio-agent"`:

```
prompt: |
  TASK: Apply critique fixes to the diagram.

  FILE PATH: <output_file path>

  FIXES REQUIRED:
  <paste fixes from whichever critique(s) failed — logic and/or style>

  Read the existing file, apply all fixes, validate consistency, write the updated file.
  Return a concise summary of changes made. NEVER return raw XML.
```

**No further critique rounds.** After the fix round, report the results to the user.

## Fallback Behavior

If the `barclays-buk-drawio:drawio-agent` subagent is unavailable, inform the user that the drawio plugin requires its agent subagents to function. Suggest they reinstall the plugin.

## What to Report to the User

At the end, tell the user:

1. **Source image** — the image that was analyzed
2. **Output file path** of the created diagram
3. **Components** included (list of node labels)
4. **Connections** (list of relationships)
5. **Analysis notes** — any uncertainties flagged with [?] from the image analysis
6. **Critique status** — how many rounds it took, final verdicts
7. **Fixes applied** — if any critique failed, what was corrected
8. **Any remaining issues** if max iterations were hit

Do NOT show raw draw.io XML to the user. Keep the response concise.
