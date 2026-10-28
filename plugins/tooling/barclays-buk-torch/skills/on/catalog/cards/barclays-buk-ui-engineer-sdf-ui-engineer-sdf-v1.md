# barclays-buk-ui-engineer-sdf-ui-engineer-sdf-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-sdf-ui-engineer-sdf-v1` |
| Plugin name | `barclays-buk-ui-engineer-sdf` |
| Component type | skill-user-only |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk |
| Native command | `/barclays-buk-ui-engineer-sdf:ui-engineer-sdf` |
| Skill name | `ui-engineer-sdf` |

## Description

Generate SDF Blueprint React Native screens from Figma designs

## When to use

Use when building SDF (React Native) screens from Figma designs for a project that uses @barclays/chameleon-blueprint. Provide the project path, a JIRA ticket ID, and optionally a Figma URL or a text description of the screens to generate. The workflow is resumable — re-run the same command to continue from the last completed phase. Not for non-SDF (web) projects or projects without @barclays/chameleon-blueprint installed.

## Inputs

- `PROJECT_PATH` (required) — absolute path to the SDF React Native project directory
- `--jira JIRA_ID` (required) — JIRA ticket identifier, e.g. `UCG-1234`
- `--figma-url "<url>"` (optional) — Figma page or frame URL; enables Figma REST API discovery if `FIGMA_TOKEN` is set in the environment
- `--additional-input "<text>"` (optional) — free-text screen descriptions or supplemental layout instructions; used when no Figma URL is provided or as a fallback
- `--full-automation` (optional flag) — suppresses all human confirmation prompts; the workflow applies built-in defaults at every decision point

## Preconditions

- The project directory must exist and contain a `package.json` with `@barclays/chameleon-blueprint` as a dependency
- `JIRA_ID` must match the pattern `[A-Z]+-[0-9]+` (e.g. `UCG-1234`)
- Optional: `FIGMA_TOKEN` (or `SPECKIT_FIGMA_TO_CODE_FIGMA_TOKEN`) set in the environment to enable Figma REST API screen discovery; without it the workflow falls back to MCP-only or description-based generation

## Expected outputs

- One `.tsx` Blueprint React Native screen component per detected screen, at `src/screens/<ScreenName>/<ScreenName>.tsx`
- Barrel export at `src/screens/index.ts` aggregating all generated screens
- Completion report at `<PROJECT_PATH>/UI_ENGINEER_SDF_COMPLETE.md` listing screens generated, Figma node mappings, and build status
- A git commit in the project repository containing all generated screen files

## Exclusions

- Does not scaffold a new SDF project — the project must already exist with `@barclays/chameleon-blueprint` installed
- Does not provision Figma access or manage the `FIGMA_TOKEN` — the caller must supply it as an environment variable
- Does not wire generated screens into a React Navigation router — routing is the caller's responsibility after generation
- Does not generate non-SDF (web) components; this command is specific to `@barclays/chameleon-blueprint` React Native projects

## Verification

Run `npx tsc --noEmit` in the project directory — the command enforces a TypeScript compilation gate before completing, so a passing build is expected. Review `UI_ENGINEER_SDF_COMPLETE.md` for the list of generated screens and their Figma node mappings. Inspect `src/screens/` for one `.tsx` file per screen and `src/screens/index.ts` for the barrel export.
