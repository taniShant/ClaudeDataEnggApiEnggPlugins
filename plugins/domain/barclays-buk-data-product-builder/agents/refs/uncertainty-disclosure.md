---
description: "Universal rule for all agents — state explicitly what is uncertain and why, use {{placeholder}} for non-blocking unknowns, HALT with data requirements for blocking unknowns, never silently fill gaps."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-03
---

# Uncertainty Disclosure (Universal)

> These rules apply to ALL agents in the plugin. When an agent encounters ambiguity or insufficient information:

- **State explicitly** what is uncertain and why in the output
- **Use `{{placeholder}}` markers** for non-blocking unknowns (values that can be resolved later without re-running the agent)
- **HALT with data requirements** (not command prescriptions) for blocking unknowns (values that fundamentally change the output if wrong)
- **Present available options** with confidence levels where applicable
- **Never silently fill gaps** — a known unknown is better than a confident hallucination
> **Crypto exception**: For Protegrity DE names, the crypto-refusal-protocol takes precedence. Do NOT emit `{{de_name}}` placeholders for crypto Data Elements. See `${CLAUDE_PLUGIN_ROOT}/agents/refs/crypto-refusal-protocol.md`.
- If source data or mapping intent is unclear, **surface the ambiguity** to the user rather than assuming
