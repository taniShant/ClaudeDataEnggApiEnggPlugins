# mca1-ui-mca2-migration

Autonomously migrate MCA1 UI projects to MCA2 with Blueprint-React and functional component patterns. The plugin replaces BDL `<mca-*>` web components with `@barclays/blueprint-react` equivalents, converts JMVC `$scope`/`BaseController` patterns to React functional components, and enforces the full Blueprint-React v1.3.0 API contract before committing.

This is a FORGE-compliant plugin with state file resume support, parallel file-batch transformation, and a read-only validation gatekeeper. Local transformations only — no remote push (ready for MR after validation).

---

## Quick Start

```bash
# Run on current directory
/mca-ui-migrate .

# Run with optional JIRA ticket ID
/mca-ui-migrate . --jira MCAUI-1234

# Run with API contract verification (backend EPS repo)
/mca-ui-migrate /path/to/mca1-project --eps-repo "git@app.gitlab.barcapint.com:team/my-app-eps.git"

# Run in full automation mode (no prompts)
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --full-automation

# Run with regression test conversion (Phase 4)
/mca-ui-migrate /path/to/mca1-project --jira MCAUI-2388 --regression-repo "https://gitlab.barclays.internal/team/regression-tests.git"
```

---

## Phases

| Phase | Name | Description | Hard Gate |
|-------|------|-------------|-----------|
| 0 | Project Setup & MCA1 Validation | Confirm MCA1 project structure, check npm, create feature branch | npm --version exits 0 |
| 1 | Codebase Analysis | Scan for BDL/JMVC patterns, classify files, produce batch plan | analysis.json written |
| 2 | BDL→Blueprint-React Transformation | Apply transformations in parallel file batches (3–6 files/worker) | npm run lint; tsc; npm run build |
| 3 | Validation | Read-only gatekeeper — 9 red flag checks | APPROVED verdict required |
| 4 | Regression Test Conversion | Clone regression repo, generate Cypress E2E tests with isolated MSW mocks (conditional) | Cypress files exist; tsc; lint |

---

## Agents

| Agent | Model | Scope | Description |
|-------|-------|-------|-------------|
| `mca1-orchestrator-agent` | sonnet | All phases | Hub orchestrator. Manages phases, state file, parallel batching, quality gate. Never implements domain logic inline. |
| `mca1-analysis-agent` | sonnet | Phase 1 only | Read-only scanner. Discovers BDL and JMVC files, classifies transformation type per file, writes `analysis.json` with batch plan. |
| `mca1-transform-agent` | sonnet | Phase 2 only | Scope-bounded worker. Receives a file batch and applies 7 transformation types (FormItem, Dialog, Table, Button, JMVC, Icon, imports). Never touches business logic. |
| `mca1-validation-agent` | haiku | Phase 3 only | Read-only gatekeeper. Checks 9 domain-specific red flags. Returns `APPROVED` or `REJECTED`. |
| `mca1-regression-agent` | sonnet | Phase 4 only | Clones regression test repo, analyzes scripts, generates Cypress E2E tests in `cypress/e2e/regression/` with MSW mock handlers in `cypress/mocks/`. Never modifies `mockServer/middleware.js`. |
| `auto-decision-agent` | sonnet | Any phase | Resolves ambiguity autonomously using 7-rule decision framework. Returns concrete decision — never asks questions. |

---

## Skills

| Skill | Purpose |
|-------|---------|
| `domain-reference` | Phase architecture, BDL component mapping table (41 components), iron rules, decision rules, implementation guide with 29 documented mistakes, 23 per-component mapping files, 19 reference guides |

---

## What Gets Transformed

| MCA1 Pattern | MCA2 Replacement |
|---|---|
| `import { X } from 'bdl'` | `import { X } from '@barclays/blueprint-react'` |
| `<mca-input>` | `<FormItem render>` + `<FormInput>` |
| `<mca-radios>` + `<mca-radio>` | `<FormMultiItem render>` + `<FormRadio>` |
| `<mca-modal>` | `<Dialog head=... foot=...>` |
| `<mca-table>` | `<Table>` + `<thead>/<tbody>/<tr>/<td>` |
| `<mca-button variant="ghost">` | `<Button variant="subtle">` |
| `<mca-button variant="danger">` | `<Button status="danger">` |
| `extends BaseController` | React functional component |
| `$scope.property = x` | `useState(x)` |
| `$scope.handler = () => ...` | event handler function |
| `static $inject = [...]` | `useAppDispatch` / `useContext` |
| `BrowserRouter` | `MemoryRouter` |
| `<Icon icon="tick-circle">` | `<Icon icon="tick" size="md">` |
| `<Icon icon="spinner">` | `<Loading size="lg" shape="circle">` |

---

## What Does NOT Get Modified

- Redux reducers, thunks, selectors (`store/`)
- API service files (`api/`, `services/`)
- `process.json` endpoint definitions
- Business logic and calculation functions
- Test files (`.test.tsx`, `.spec.tsx`)

---

## Full Automation Mode

When `--full-automation` is passed, the plugin installs hooks that:
1. Block any `AskUserQuestion` tool calls — the agent makes the best autonomous decision instead
2. Monitor for incomplete work and resume automatically if the agent stops prematurely

Hooks are automatically restored on completion (success or failure).

---

## State File and Resume Support

State file location: `{PROJECT_PATH}/.claude/mca1-ui-mca2-migration-state.json`

If the migration is interrupted at any phase, re-running the same command will automatically resume from the last incomplete phase. Completed phases are skipped.

---

## Domain Knowledge (Skill Reference)

The `skills/domain-reference/` directory contains the comprehensive knowledge base built from real MCA1→MCA2 migration runs:

- `SKILL.md` — Phase architecture, iron rules, decision rules
- `IMPLEMENTATION_GUIDE.md` — 29 documented mistakes with correct patterns
- `guides/BDL_TO_BLUEPRINT_REACT.md` — Complete 41-component mapping index
- `guides/BLUEPRINT_REACT_CORRECT_PATTERNS.md` — Authoritative pattern reference for FormItem, Dialog, Table, Button, Layout
- `mappings/` — 23 per-component mapping files with before/after examples
- `guides/ERROR_SCENARIOS.md` — 12 real-world error solutions
- `guides/DEBUGGING_GUIDE.md` — Troubleshooting techniques

---

## Reference

- BDL component mappings: `skills/domain-reference/mappings/` (23 per-component files)
- Blueprint-React patterns: `skills/domain-reference/guides/BLUEPRINT_REACT_CORRECT_PATTERNS.md`
- FORGE standard: `docs/forge-standard.md`
- Blueprint-React version: 1.3.0 (`@barclays/blueprint-react`)
