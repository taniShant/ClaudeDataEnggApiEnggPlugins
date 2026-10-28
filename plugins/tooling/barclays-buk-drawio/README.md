# barclays-buk-drawio

> Migrated from `barclays-claude-code-plugins/plugins/drawio/`

A Claude Code plugin for creating, updating, transforming, and exporting draw.io diagrams through orchestrated multi-agent delegation with style-guided critique loops.

## Purpose

This plugin provides a multi-agent system for working with draw.io files (`*.drawio`) without exhausting the main agent's context budget. Draw.io XML files are verbose (each mxCell has an inline style string + mxGeometry child = 100-200 tokens per cell) but have low information density, making them ideal for subagent delegation.

## When to Use

Use this plugin when:

- Working with files ending in `.drawio`
- User requests diagram operations: "create flowchart", "update swimlane diagram", "create architecture diagram in draw.io"
- User wants to convert/transform an image or screenshot of a diagram into a `.drawio` file
- User mentions: "flowchart", "draw.io", "swimlane diagram", "BPMN", "WBS", "RACI", "Gantt chart", "network diagram", "org chart"
- Performing architecture/design documentation tasks involving visual artifacts in draw.io format
- Working with PMP/PMBOK project management diagrams

## Directory Structure

```
plugins/tooling/barclays-buk-drawio/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── drawio-agent.md                    # Primary actor: creates/edits .drawio XML
│   ├── drawio-fidelity-critique-agent.md  # Visual comparison (transform only)
│   ├── drawio-logic-critique-agent.md     # Spec correctness review
│   └── drawio-style-critique-agent.md     # Style guide compliance review
├── commands/
│   ├── create.md                          # Orchestrator: create new diagrams
│   ├── update.md                          # Orchestrator: update existing diagrams
│   ├── transform.md                       # Orchestrator: transform image to draw.io
│   └── export.md                          # Export to PNG/JPG
├── skills/
│   └── drawio-style-guide/
│       └── SKILL.md                       # Styling rules (color, layout, typography)
├── scripts/
│   └── export_drawio.py                   # Python export utility (Playwright + Canvas)
└── README.md
```

## Commands

| Command | Purpose |
|---------|---------|
| `/barclays-buk-drawio:create` | Create a new diagram from a text description or spec file |
| `/barclays-buk-drawio:update` | Update an existing diagram with requested changes |
| `/barclays-buk-drawio:transform` | Transform an image (PNG, JPG, screenshot) into a `.drawio` diagram |
| `/barclays-buk-drawio:export` | Export a `.drawio` file to PNG or JPG |

## Agent Team

| Agent | Responsibility |
|-------|----------------|
| **drawio-agent** | Creates and modifies `.drawio` XML files directly. Reads the style guide, generates valid draw.io XML, validates structural integrity. Returns text summaries, never raw XML. |
| **drawio-fidelity-critique-agent** | **Transform only.** Visually compares two images: the original source image and a PNG exported from the generated `.drawio`. Checks component completeness, label accuracy, connection correctness, layout direction. Does NOT read `.drawio` XML. |
| **drawio-logic-critique-agent** | Reviews diagrams for logical/factual correctness against the original spec. Checks component completeness, relationship accuracy, edge direction, parent/child integrity. Does NOT check styling. |
| **drawio-style-critique-agent** | Reviews diagrams for styling consistency against the style guide skill. Audits every cell's style string against every rule. Does NOT check logical correctness. |

## Architecture

### Create/Update Flow

```
User Request -> Orchestrator (command)
  -> Round 1: Actor (create/update .drawio)
  -> Round 2: Logic Critique (spec vs diagram)
     FAIL? -> skip style, go to fix
  -> Round 3: Style Critique (style guide vs diagram)
     FAIL? -> go to fix
  -> Round 4: Actor Fix (single round, no re-critique)
  -> Report to user
```

### Transform Flow

```
User provides image
  -> Round 1: Image Analysis (structured text spec)
  -> Round 2: Actor (create .drawio from spec)
  -> Round 3: Export to PNG
  -> Round 4: Fidelity Critique + Logic Critique (parallel)
     Fidelity FAIL? -> Actor fix (1 iteration)
     Logic FAIL? -> skip style, go to Round 6
  -> Round 5: Style Critique
     FAIL? -> go to Round 6
  -> Round 6: Actor Fix (single round)
  -> Report to user
```

## The Iron Law

**Main agents NEVER read draw.io files directly. No exceptions.**

The problem is verbosity, not complexity:
- Each mxCell has an inline style string (50-100+ characters) + mxGeometry child
- 25 cells x ~150 tokens/cell = ~3,750 tokens
- Only cell `value` attributes and edge `source`/`target` matter (~10% of content)

| Scenario | Without Delegation | With Delegation | Savings |
|----------|-------------------|-----------------|---------|
| Small diagram (15 cells) | ~2,250 tokens | ~400 tokens | 82% |
| Medium diagram (30 cells) | ~4,500 tokens | ~600 tokens | 87% |
| Large swimlane (50+ cells) | ~7,500 tokens | ~800 tokens | 89% |

## Usage Examples

### Creating a Diagram

```
/barclays-buk-drawio:create API Gateway -> Auth Service -> PostgreSQL
```

Or with a spec file:

```
/barclays-buk-drawio:create ./specs/architecture.md
```

### Updating a Diagram

```
/barclays-buk-drawio:update architecture.drawio Add a Redis cache connected to the API service
```

### Transforming an Image to Draw.io

```
/barclays-buk-drawio:transform ./screenshots/architecture.png
```

With a custom output path:

```
/barclays-buk-drawio:transform ./screenshots/architecture.png ./diagrams/architecture.drawio
```

### Exporting a Diagram

```
/barclays-buk-drawio:export architecture.drawio png
```

## Style Guide

The style guide skill (`barclays-buk-drawio:drawio-style-guide`) is the single source of truth for all visual decisions. Key rules:

**Color Palette (Semantic Roles)**:
- Services/Applications: `fillColor=#dae8fc;strokeColor=#6c8ebf;` (blue)
- Databases/Data Stores: `fillColor=#d5e8d4;strokeColor=#82b366;` (green)
- External Systems: `fillColor=#fff2cc;strokeColor=#d6b656;` (yellow)
- Errors/Destructive: `fillColor=#f8cecc;strokeColor=#b85450;` (red)
- Middleware/Infrastructure: `fillColor=#e1d5e7;strokeColor=#9673a6;` (purple)
- Queues/Async: `fillColor=#ffe6cc;strokeColor=#d79b00;` (orange)
- Neutral/Containers: `fillColor=#f5f5f5;strokeColor=#666666;` (gray)

**Typography**: `fontSize=12` (labels), `fontSize=14` (headings), `fontStyle=1` (bold).

**Layout**: Grid-aligned (multiples of 10), 30-50px horizontal spacing, 20-30px vertical.

**Consistency**: Same-role elements must be visually identical. No one-off overrides.

## Dependencies

- `barclays-buk-standards` — shared BUK standards
