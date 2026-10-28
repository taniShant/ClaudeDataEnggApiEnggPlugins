---
description: "Universal contract establishing that every agent can be invoked independently outside the full pipeline chain — each agent declares the minimum required context for standalone execution."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-03
---

# Standalone Invocation (Universal)

> Every agent in this plugin can be invoked independently outside the full pipeline chain.

When invoked standalone, provide inputs directly via the invocation prompt.
Session files are the standard source but not the only valid source.

Each agent declares its own **Minimum required context** — the smallest set of inputs needed to produce correct output without session state. See the agent's `## Standalone Invocation` section for its specific requirements.
