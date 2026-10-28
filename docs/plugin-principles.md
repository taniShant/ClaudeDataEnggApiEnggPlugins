# BUK AI Plugin Principles

These principles govern how BUK Claude Code plugins, agents, and skills are designed and maintained. They apply to all plugins in this repository.

---

## 1. Standards and domain knowledge must have a single source of truth

Standards and domain knowledge must have a single source of truth. Use Claude Code plugin dependencies to share skills across plugins rather than copying content. A change to a standard should be made in one place and propagate automatically.

## 2. Domain knowledge should not be tied to specific AI frameworks or methodologies

Standards and domain knowledge live in skills. Agents pull in the skills they need. The workflow layer — whether BMAD, Spec-Kit, a custom orchestrator, or a human — is separate from the knowledge layer. Skills must remain usable regardless of what framework surrounds them.

Agents are also framework-agnostic. Because every BUK agent has explicit inputs and outputs (Principle 4), any framework can invoke any BUK agent without modification. Integration guides for specific frameworks (BMAD, Spec-Kit, etc.) are wiring layers — they surface BUK capabilities at the right workflow step, but do not change the agents themselves.

## 3. Agents should be extensible

A base agent or skill can be extended by a specialist team without modifying the original. Extensions add or override — they never fork. The base remains stable and continues to receive updates from its owner.

## 4. Agents should be independently invocable

An agent must be useful on its own, not only as part of a chain. It accepts explicit inputs and produces explicit outputs. If an agent requires a specific upstream artefact format to function, it is too coupled to a workflow.

## 5. Agents should be transparent about what they know and don't know

When an agent operates with incomplete or placeholder standards, it must say so in its output rather than silently fill in gaps. A known unknown is better than a confident hallucination.

## 6. Standards must have clear ownership and a review cadence

Every skill in `barclays-buk-standards` has a named owner and a defined review trigger (e.g. annual, or on regulatory change). Without ownership, standards drift. Without a review cadence, they go stale.

## 7. Agents should not enforce workflow

An agent may suggest a logical next step but must never require a specific predecessor or block on a missing upstream artefact. Sequencing is the responsibility of the workflow layer, not the agent.
