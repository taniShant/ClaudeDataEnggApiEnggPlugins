# barclays-buk-ui-engineer-sdf

Generate SDF screens from Figma designs into Blueprint React Native components for `@barclays/chameleon-blueprint` projects.

## Channel Scope

| Channel | Supported |
|---|---|
| Online Banking | ✅ (SDF/React Native projects) |
| Mobile | ✅ (SDF/React Native projects) |
| FullServe | ❌ Use `barclays-buk-ui-engineer-mca` (planned) |
| MAE | ❌ Use `barclays-buk-ui-engineer-mca` (planned) |

---

## Workflow

```
ui-engineer-discover-agent              ← turn Figma URL into SCREENS list
        ↓
ui-engineer-sdf-screen-composer-agent   ← Figma → Blueprint screen component
        ↓
ui-engineer-sdf-stub-agent              ← wire hardcoded data + navigation for visual review
        ↓
ui-engineer-sdf-api-agent               ← wire RTK Query endpoints + Redux slices
        ↓
ui-engineer-sdf-jest-functional-agent   ← pure logic unit tests
ui-engineer-sdf-jest-ui-agent           ← component render tests
ui-engineer-sdf-jest-a11y-agent         ← accessibility tests
        ↓
ui-engineer-sdf-validation-agent        ← quality gate (APPROVED / REJECTED)
```

Each agent is independently invocable — invoke any step in isolation with an explicit `SCREENS` list.

---

## Agents

| Agent | Role |
|---|---|
| `ui-engineer-sdf-screen-composer-agent` | Generates Blueprint screen components from Figma |
| `ui-engineer-sdf-stub-agent` | Wires hardcoded data and navigation stubs for visual flow review |
| `ui-engineer-sdf-api-agent` | Wires RTK Query endpoints, Redux slices, mockBridge |
| `ui-engineer-sdf-state-agent` | Scaffolds Redux state shape and slice structure |
| `ui-engineer-sdf-jest-functional-agent` | Generates pure logic unit tests |
| `ui-engineer-sdf-jest-ui-agent` | Generates component render tests |
| `ui-engineer-sdf-jest-a11y-agent` | Generates accessibility tests |
| `ui-engineer-sdf-mutation-agent` | Scaffolds Stryker mutation testing config |
| `ui-engineer-sdf-validation-agent` | Read-only quality gate — returns APPROVED or REJECTED with per-flag evidence |
| `ui-engineer-sdf-worker-agent` | Full-batch worker for automated orchestration — task agents are the preferred human entry point |

---

## Skills

| Skill | Purpose |
|---|---|
| `sdf` | Blueprint React Native component mappings, Iron Rules, Figma MCP usage, screen generation heuristics |
| `test` | Jest patterns, accessibility test rules, mutation testing |
| `commit` | TypeScript gate, conventional commit patterns |

---

## Prerequisites

- **Figma Dev Mode MCP server** — must be running via Figma Desktop app
- **`@barclays/chameleon-blueprint`** — must be a dependency in `package.json`

---

## Domain Reference

See [`skills/sdf/SKILL.md`](skills/sdf/SKILL.md) for complete Blueprint component mappings, Iron Rules, and screen layout patterns.
