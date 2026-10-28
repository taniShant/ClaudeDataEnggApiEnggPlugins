---
name: resolve-context
description: Resolve and classify all context sources, check accessibility and record authority status.
agent: context-resolver
user-invocable: true
---

## Purpose

Resolve and classify all context sources referenced by a project or requirement document, verify accessibility at the point of invocation, and record the authority status (approved, proposed, deprecated, unknown) of each source. Produces a signed context manifest that other commands consume to confirm they are operating against current, authoritative material.

## Usage

```
/resolve-context --sources <urls|"register"> [--output <path>] [--validate-currency <true|false>] [--help]
```

## Arguments

| Name | Required / Optional | Description |
|------|---------------------|-------------|
| `--sources` | Required | Comma-separated list of URLs or file paths to resolve, or the literal string `register` to load the full source register for the current project. |
| `--output` | Optional | Directory path to write the context manifest. Defaults to `./output/context/`. |
| `--validate-currency` | Optional | Boolean (`true`/`false`). When `true`, the agent queries Policy Hub to confirm each resolved source is the latest version. Defaults to `true`. |
| `--help` | Optional | Print the input/output schema, loaded standards, and an example invocation, then exit with code `0`. |

## Example Invocations

**1. Resolve the full project source register:**
```
/resolve-context --sources register --output ./output/context/initial/
```

**2. Resolve two specific URLs and skip currency validation (offline mode):**
```
/resolve-context --sources "https://policy-hub.example.com/dp-001,https://confluence.example.com/pages/data-standards" --validate-currency false
```

**3. Resolve a mix of URLs and a local file reference:**
```
/resolve-context --sources "https://policy-hub.example.com/dp-001,./standards/local-addendum.md" --output ./output/context/sprint-3/
```

## Output

On success the agent writes the following artefacts to the output directory:

- `context-manifest.json` — Structured manifest containing:
  - `sources[]` — Each source with url/path, resolved_title, authority_status (`approved|proposed|deprecated|unknown`), version, last_checked timestamp, and accessibility (`reachable|unreachable|auth_required`).
  - `currency_check_performed` — Boolean flag.
  - `policy_hub_version_mismatches[]` — Sources where a newer version exists on Policy Hub.
  - `loaded_standards[]` — Names and versions of classification standards used.
  - `unverified_assumptions[]` — Any authority determinations that could not be confirmed automatically.
- `context-summary.md` — Human-readable summary of all source statuses.

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | All sources resolved and classified successfully. |
| `1` | One or more sources were unreachable; partial manifest written — inspect `accessibility` field. |
| `2` | Source register not found for current project (`register` mode only). |
| `3` | Policy Hub unreachable; currency validation skipped — `currency_check_performed` set to `false`. |
| `10` | Zero sources supplied or resolved. |

## Related Commands

- `/assess` — Use the resolved context manifest to inform requirement assessment.
- `/validate` — Validate artefacts against the resolved and approved context sources.
