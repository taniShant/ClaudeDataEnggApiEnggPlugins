---
name: drawio-style-guide
description: "Single source of truth for all styling decisions in draw.io diagrams. Covers canvas settings, color palette, shape styles, connectors, typography, stroke, layout, PMP/PMBOK, consistency rules, and text overlap prevention."
user-invocable: false
---

<!-- Source: barclays-claude-code-plugins/plugins/drawio/style_guide.md -->
<!-- Owner: Vishal Khare (vishal.khare1@barclays.com) -->
<!-- Review trigger: Any change to draw.io styling conventions -->
<!-- Status: Active -->

# Draw.io Style Guide

This is the single source of truth for all styling decisions in draw.io diagrams. All agents producing or reviewing diagrams must follow these rules exactly.

## Quick Start

### Applying the style guide to a new diagram

1. Determine the **semantic role** of each component (service, database, external, queue, etc.)
2. Look up `fillColor` and `strokeColor` from the **Color Palette** table below
3. Build the style string using the **Shape Styles** templates
4. Use the **Connector Styles** table for edges
5. Align all coordinates to multiples of 10

### Example: Service connecting to Database

```xml
<!-- Service node (blue) -->
<mxCell id="2" value="API Gateway"
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
    vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>

<!-- Database node (green) -->
<mxCell id="3" value="PostgreSQL"
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;"
    vertex="1" parent="1">
  <mxGeometry x="300" y="100" width="120" height="60" as="geometry"/>
</mxCell>

<!-- Standard orthogonal connector -->
<mxCell id="4"
    style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;endFill=1;"
    edge="1" parent="1" source="2" target="3">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Checklist before writing

- All shapes include `whiteSpace=wrap;html=1;` in style
- Style strings end with a trailing semicolon
- Coordinates are multiples of 10
- Adjacent shapes have 30-50px horizontal or 20-30px vertical clearance
- Same-role elements use identical fill/stroke colors

## Canvas (mxGraphModel Attributes)

| Attribute | Value |
|-----------|-------|
| `grid` | `1` |
| `gridSize` | `10` |
| `guides` | `1` |
| `tooltips` | `1` |
| `connect` | `1` |
| `arrows` | `1` |
| `fold` | `1` |
| `page` | `1` |
| `pageScale` | `1` |
| `pageWidth` | `850` |
| `pageHeight` | `1100` |
| `math` | `0` |
| `shadow` | `0` |

## Color Palette

### Semantic Role Mappings

| Semantic Role | fillColor | strokeColor | Usage |
|--------------|-----------|-------------|-------|
| Services / Applications | `#dae8fc` | `#6c8ebf` | API gateways, microservices, application nodes |
| Databases / Data Stores | `#d5e8d4` | `#82b366` | PostgreSQL, Redis, S3, data warehouses |
| External Systems / Third-Party | `#fff2cc` | `#d6b656` | Stripe, Twilio, external APIs |
| Errors / Destructive Actions | `#f8cecc` | `#b85450` | Error states, delete operations, critical path |
| Middleware / Infrastructure | `#e1d5e7` | `#9673a6` | Message brokers, load balancers, middleware |
| Queues / Async Components | `#ffe6cc` | `#d79b00` | Message queues, async workers, event buses |
| Neutral / Containers | `#f5f5f5` | `#666666` | Swimlane headers, generic boxes, containers |

Use color to convey semantic meaning — elements of the same role must use the same fillColor and strokeColor.

## Shape Styles

Complete style strings for each shape type. Substitute `fillColor` and `strokeColor` from the semantic role table when applicable.

### Process (Rounded Rectangle) — Default Shape

```
rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;
```

### Decision (Diamond)

```
rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;
```

### Start / End (Ellipse)

```
ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;
```

### Document

```
shape=document;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;
```

### Data (Parallelogram)

```
shape=parallelogram;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;
```

### Swimlane Container

```
swimlane;html=1;startSize=20;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;align=center;verticalAlign=top;collapsible=0;
```

### Swimlane Container with Title Bar

```
swimlane;html=1;startSize=40;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;fontSize=14;align=center;verticalAlign=top;collapsible=0;
```

## Connector Styles

| Connector Type | Style String |
|---------------|-------------|
| Standard (orthogonal) | `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;endFill=1;` |
| Straight | `rounded=0;html=1;jettySize=auto;orthogonalLoop=1;endArrow=classic;endFill=1;` |
| Curved | `curved=1;rounded=1;html=1;jettySize=auto;orthogonalLoop=1;endArrow=classic;endFill=1;` |
| Dashed (async/optional) | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;dashPattern=5 5;endArrow=classic;endFill=1;` |
| No arrow (association) | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=none;endFill=0;` |
| Bidirectional | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;startArrow=classic;startFill=1;endArrow=classic;endFill=1;` |
| Critical path (thick red) | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeWidth=3;strokeColor=#b85450;endArrow=classic;endFill=1;` |
| Dotted (future/planned) | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;dashPattern=2 4;endArrow=classic;endFill=1;` |

Use `exitX`, `exitY`, `entryX`, `entryY` style properties for explicit connector routing when needed:
```
exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;
```

## Typography

| Context | Style Properties |
|---------|-----------------|
| Default labels | `fontSize=12;fontStyle=0;` |
| Headings / titles | `fontSize=14;fontStyle=1;` (bold) |
| Large headings | `fontSize=16;fontStyle=1;` (bold) |
| Annotations / secondary | `fontSize=10;fontStyle=0;` |
| Code / technical labels | `fontSize=11;fontStyle=0;fontFamily=Courier New;` |

### Text Alignment (all shapes)

| Property | Value |
|----------|-------|
| `align` | `center` |
| `verticalAlign` | `middle` |
| `whiteSpace` | `wrap` |
| `html` | `1` |

Standalone text labels or annotations may use `align=left` when they serve as callouts.

## Stroke

| Property | Default | Notes |
|----------|---------|-------|
| `strokeColor` | Per semantic role table | Must match the role's strokeColor |
| `strokeWidth` | Not set (draw.io default ~1px) | Use `strokeWidth=2;` for emphasis. Use `strokeWidth=3;` for critical path only. |
| `dashed` | Not set (solid) | Set `dashed=1;dashPattern=5 5;` only for async/optional connections. |

## Layout

| Property | Value |
|----------|-------|
| Coordinate alignment | Multiples of 10 (x, y, width, height) |
| Horizontal spacing between shapes | 30–50px edge-to-edge |
| Vertical spacing between shapes | 20–30px edge-to-edge |
| Row spacing (between swimlane rows) | 40–50px |
| Small shape size | 80x40 |
| Medium shape size (default) | 120x60 |
| Large shape size | 160x80 |
| Extra-large shape size | 200x80 |
| Swimlane lane height | 120–150px per lane |

### Connector Entry/Exit

For clean routing, use explicit entry/exit points:
- `exitX=1;exitY=0.5;` — exit from the right center
- `entryX=0;entryY=0.5;` — enter from the left center
- `exitX=0.5;exitY=1;` — exit from the bottom center
- `entryX=0.5;entryY=0;` — enter from the top center

## PMP/PMBOK Specific Styles

### Process Group Colors

| Process Group | fillColor | strokeColor |
|--------------|-----------|-------------|
| Initiating | `#d5e8d4` | `#82b366` |
| Planning | `#dae8fc` | `#6c8ebf` |
| Executing | `#ffe6cc` | `#d79b00` |
| Monitoring & Controlling | `#fff2cc` | `#d6b656` |
| Closing | `#e1d5e7` | `#9673a6` |

### Knowledge Area Colors

| Knowledge Area | fillColor | strokeColor |
|---------------|-----------|-------------|
| Integration Management | `#f5f5f5` | `#666666` |
| Scope Management | `#dae8fc` | `#6c8ebf` |
| Schedule Management | `#d5e8d4` | `#82b366` |
| Cost Management | `#ffe6cc` | `#d79b00` |
| Quality Management | `#f8cecc` | `#b85450` |
| Resource Management | `#e1d5e7` | `#9673a6` |
| Communications Management | `#b1ddf0` | `#10739e` |
| Risk Management | `#fff2cc` | `#d6b656` |
| Procurement Management | `#f8cecc` | `#b85450` |
| Stakeholder Management | `#e1d5e7` | `#9673a6` |

### Risk Matrix Colors

| Risk Level | fillColor | strokeColor | fontColor |
|-----------|-----------|-------------|-----------|
| Critical | `#8B0000` | `#600000` | `#ffffff` |
| High | `#FF0000` | `#CC0000` | `#ffffff` |
| Medium | `#FFA500` | `#CC8400` | `#000000` |
| Low | `#FFFF00` | `#CCCC00` | `#000000` |
| Very Low | `#90EE90` | `#66AA66` | `#000000` |

### RACI Matrix Cell Colors

| Assignment | fillColor | strokeColor |
|-----------|-----------|-------------|
| R (Responsible) | `#d5e8d4` | `#82b366` |
| A (Accountable) | `#dae8fc` | `#6c8ebf` |
| C (Consulted) | `#fff2cc` | `#d6b656` |
| I (Informed) | `#e1d5e7` | `#9673a6` |

### WBS Level Colors

| WBS Level | fillColor | strokeColor | fontColor |
|----------|-----------|-------------|-----------|
| Level 0 (Project) | `#1ba1e2` | `#006EAF` | `#ffffff` |
| Level 1 (Deliverables) | `#60a917` | `#2D7600` | `#ffffff` |
| Level 2 (Sub-deliverables) | `#d5e8d4` | `#82b366` | `#000000` |
| Level 3 (Work Packages) | `#f5f5f5` | `#666666` | `#000000` |

### Gantt Chart Elements

| Element | Style Properties |
|---------|-----------------|
| Timeline bar | `rounded=0;whiteSpace=wrap;html=1;fillColor=#60a917;strokeColor=#2D7600;fontColor=#ffffff;` |
| Milestone (diamond) | `rhombus;whiteSpace=wrap;html=1;fillColor=#fa6800;strokeColor=#C73500;fontColor=#000000;` |
| Dependency arrow | `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=2;` |

## Consistency Rules

- **Same-role elements must be visually identical.** All service nodes share the same fillColor, strokeColor, fontSize, and fontStyle.
- **Same-type connectors must be visually identical.** All standard connection edges share the same edgeStyle, endArrow, endFill, and strokeWidth. Dashed connectors are reserved for async/optional flows and must be used consistently for that purpose.
- **No one-off overrides.** If one element differs from others of the same role, it is a violation unless the spec explicitly calls for the distinction.
- **Style strings must be properly terminated** with a trailing semicolon.
- **All shape cells must include** `whiteSpace=wrap;html=1;` in their style string.
- **No overlapping text — CRITICAL.** This is the highest-priority consistency rule. No text may visually overlap any other text or obscure any content. This applies to ALL text: node labels, edge labels, annotation text, headings, and legend items. Violations of this rule always result in a FAIL verdict.

## Text Overlap Prevention (Mandatory)

Text overlap is the most common and most damaging visual defect. All agents must actively prevent and detect it.

### Bounding Box Calculation

Every text element occupies a rectangular bounding box. To check for overlap:

1. **Node labels:** The bounding box is the shape's `mxGeometry` (x, y, width, height). Add parent offset for swimlane children.
2. **Edge labels:** Estimate the label bounding box at the edge's midpoint. A label of `N` characters at `fontSize=F` occupies approximately `(N x F x 0.6)` pixels wide and `(F x 1.3 x lineCount)` pixels tall, centered at the midpoint of the edge path.
3. **Standalone text cells:** The bounding box is the cell's `mxGeometry`.
4. **Minimum clearance:** All bounding boxes must have at least **10px** clearance from every other bounding box — no touching, no overlapping.

### Common Overlap Scenarios to Check

| Scenario | How to Detect | How to Fix |
|----------|--------------|------------|
| Edge labels overlapping each other | Two edges with labels share similar midpoints | Stagger labels using waypoints, or move one edge's path |
| Edge labels overlapping nodes | Edge label midpoint falls inside or near a node's bounding box | Add waypoints to route the edge further from the node |
| Node labels too close together | Adjacent nodes with less than 10px clearance between their edges | Increase spacing between nodes |
| Long labels overflowing their shapes | Label text width exceeds shape width | Increase shape width, or shorten the label with `<br>` line breaks |
| Annotation text overlapping shapes | Text cell bounding box intersects a shape | Reposition annotation to an empty area |
| Converging edges with labels | Multiple labeled edges enter/exit the same node | Use different exit/entry points (exitX/exitY/entryX/entryY) and stagger label positions |

### Edge Label Positioning Rules

- **Do NOT rely on default edge label placement.** When edges are close together or share endpoints, their labels WILL collide at default positions.
- **Use waypoints** (`<Array as="points">` with `<mxPoint>` children) to route edges apart so their midpoints (where labels appear) are well-separated.
- **For edges converging on the same node:** Use different exit/entry points (e.g., `exitX=0.25` vs `exitX=0.75`) and ensure waypoints create distinct paths with separated midpoints.
- **Minimum midpoint separation:** Edge label midpoints must be at least **40px apart** from each other and at least **20px away** from any node edge.

## Agent Self-Check

Before finalising any diagram output or review, verify:

1. [ ] All shape cells use `fillColor` and `strokeColor` matching their semantic role from the Color Palette table
2. [ ] All shape cells include `whiteSpace=wrap;html=1;` in their style string
3. [ ] All style strings terminate with a trailing semicolon
4. [ ] All coordinates (x, y, width, height) are multiples of 10
5. [ ] Adjacent shapes have at least 30px horizontal or 20px vertical clearance edge-to-edge
6. [ ] All connectors use the correct style string from the Connector Styles table for their type
7. [ ] No text overlaps any other text (10px minimum clearance between all bounding boxes)
8. [ ] Same-role elements are styled identically — no one-off overrides exist
