---
description: "Non-negotiable rule for all generation agents — COPY template verbatim first, then SUBSTITUTE placeholders only; do not rearrange, rename, add/remove keys, or restructure templates."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-03
---

# Template-First Rule (NON-NEGOTIABLE)

> This rule applies to ALL generation agents and commands that produce artefacts from templates.

## Core Rule

Generation = **COPY** the template file verbatim, then **SUBSTITUTE** `{{placeholders}}`.

## Constraints

- Do NOT rearrange keys, rename fields, add keys, remove keys, or restructure
- Do NOT construct output from prose descriptions — prose is reference context ONLY
- The template defines: structure, key names, nesting, ordering
- If a placeholder cannot be resolved → leave as `{{placeholder_name}}`
- If template and prose conflict, **the template wins — always**

## Template Loading

1. Select the correct template based on the command's template selection matrix
2. Load ONLY the selected template — do NOT merge or blend templates
3. Read the template file verbatim before any substitution
