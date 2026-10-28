---
description: "Load guard for full-automation mode — defines tool invocation mechanisms for Main→Phase Agent, Phase Agent→Inline Command, and Phase Agent→Leaf Agent orchestration patterns."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Tool Invocation Patterns

> **Load guard:** Read this ref ONLY when `session_state.auto_chain.enabled == true` (full-automation mode).

When plugin command/agent specs say "invoke", "delegate to", "run", or "call" another component, use these tool mechanisms:

**Main → Phase Agent** (full-automation orchestration):
```
Agent(description="Phase A: Discovery", prompt="<phase prompt contract>")
```
The main conversation dispatches 4 foreground Agent() calls (Phase A → B1 → B2 → C). Each phase agent gets fresh context. Between phases, the main conversation verifies checkpoints and halt state from disk.

**Phase Agent → Inline Command Execution** (within a phase):
```
Phase agent reads ${CLAUDE_PLUGIN_ROOT}/commands/{command}.md and executes steps inline.
```
Phase agents do NOT use Skill() to invoke commands. They read the command markdown directly and follow its logic. This avoids creating a 3rd nesting level (which causes API dispatch errors).

**Phase Agent → Leaf Agent** (delegation within a phase):
```
Agent(description="mapping-parser-agent", prompt="<delegation context>")
```
When a command spec says "delegate to {agent-name}", the phase agent uses Agent() to spawn the named leaf agent. Maximum nesting depth: Main(0) → Phase Agent(1) → Leaf Agent(2). Leaf agents are terminal — they do NOT spawn further agents.

**Interactive Mode — Command → Command** (user-driven, no auto-chain):
```
Skill({ skill: "barclays-buk-data-product-builder:parse-mapping" })
```
In interactive mode (no `--full-automation`), commands are invoked via Skill() by the user or main conversation. This creates depth 1 only (Main → Skill/Command → Leaf Agent = depth 2 max).

**Validators** — inline validation logic:
Validators are NOT separate tool invocations. They are inline logic: read the target file, apply rules, report pass/fail. The executing agent applies validator logic directly within its own turn.

**Hooks** — event-driven:
Hooks fire automatically on triggering events. When a hook needs agent work (e.g., post-review regeneration), it uses the Agent tool to invoke the target agent.

---

**Nesting depth summary:**

| Context | Pattern | Max Depth |
|---------|---------|-----------|
| Interactive (user Skill calls) | Main → Command → Leaf Agent | 2 |
| Full-automation (phase agents) | Main → Phase Agent → Leaf Agent | 2 |
| ❌ FORBIDDEN | Main → Phase Agent → Skill() → Agent | 3 (causes API errors) |
