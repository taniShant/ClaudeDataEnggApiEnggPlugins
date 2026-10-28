# BUK Plugin Authoring Guide

This guide covers how to build a plugin for the BUK CIO marketplace. Read [docs/plugin-principles.md](../plugin-principles.md) first — the templates here are designed to enforce those principles.

---

## Plugin structure

Every plugin lives under `plugins/<group>/barclays-buk-<name>/` and follows this layout:

```
plugins/<group>/barclays-buk-<name>/
├── .claude-plugin/
│   └── plugin.json          ← required
├── agents/
│   └── <name>-agent.md      ← at least one agent
├── skills/
│   └── <skill-name>/
│       └── SKILL.md          ← one skill per subdirectory
└── commands/                 ← optional
    └── <command-name>.md
```

See [`plugin.json.template`](plugin.json.template) for the manifest format.

---

## The three artefacts

### 1. `plugin.json` — the manifest

- `name` must be `barclays-buk-<name>`, lowercase hyphens only
- `dependencies` must include `"barclays-buk-standards"` for all plugins that use shared standards
- Do not declare `agents`, `skills`, or `commands` paths in the manifest — Claude Code auto-discovers from the standard directories

→ See [`plugin.json.template`](plugin.json.template)

### 2. Agent files

- One agent per `.md` file in `agents/`
- Filename: `<plugin-name>-agent.md` (lowercase hyphens, `.md` extension)
- Must declare `skills:` in frontmatter for every standard the agent enforces
- Must declare `owner:` in frontmatter — the team or individual responsible
- Must declare explicit `## Your Inputs` and `## Your Outputs` sections
- Must include a `## Flags` section in output — covers placeholder skills, missing inputs, decisions under uncertainty
- Must not enforce a specific upstream workflow (Principle 7) — sequencing belongs in commands

→ See [`agent.md.template`](agent.md.template)

### 3. Skill files

- One skill per subdirectory under `skills/`, file always named `SKILL.md`
- `user-invocable: false` for standards skills (they are loaded by agents, not called directly)
- Must include source attribution — where the content came from
- Must include a self-check checklist at the end
- Skills are atomic — no inheritance. Use the cross-plugin `plugin-name:skill-name` syntax to load shared skills

→ See [`skill.md.template`](skill.md.template)

---

## Shared standards

Load standards from `barclays-buk-standards` in agent frontmatter:

```yaml
skills:
  - barclays-buk-standards:accessibility
  - barclays-buk-standards:security
  - barclays-buk-standards:consumer-duty
```

Only load the skills your agent actually needs — don't load everything.

For the full list of available skills see [`plugins/barclays-buk-standards/`](../../plugins/barclays-buk-standards/).

---

## Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Plugin name | `barclays-buk-<name>` lowercase hyphens | `barclays-buk-api-engineer` |
| Agent file | `<plugin-name>-agent.md` | `api-engineer-agent.md` |
| Skill directory | lowercase hyphens | `skills/api-design/` |
| Skill file | always `SKILL.md` (uppercase) | `SKILL.md` |
| Command file | lowercase hyphens | `commands/generate-api.md` |
| Node IDs in agents | `SCREAMING_SNAKE_CASE` for inputs | `API_SPEC:` |

---

## Anti-patterns

Before authoring, read [`docs/anti-patterns.md`](../anti-patterns.md) for an explicit list of prohibited patterns and the reasoning behind each. The most common violation is using Claude Code hooks — see that doc for why hooks are banned and what to do instead.

---

## Principles checklist

Before opening an MR, verify your plugin against the [7 principles](../plugin-principles.md):

- [ ] **Principle 1 — Single source of truth**: shared rules live in `barclays-buk-standards`, not copied into your plugin
- [ ] **Principle 2 — Framework-agnostic**: skill content works regardless of what workflow calls it
- [ ] **Principle 3 — Extensible**: your agent can be extended without forking (use skill extension pattern)
- [ ] **Principle 4 — Independently invocable**: agent has explicit `## Your Inputs` and `## Your Outputs` sections; works standalone
- [ ] **Principle 5 — Transparent**: agent `## Flags` section covers placeholder skills, missing inputs, and decisions made under uncertainty
- [ ] **Principle 6 — Owned and dated**: skill has named owner and review trigger; agent has `owner:` in frontmatter
- [ ] **Principle 7 — No workflow enforcement**: agent body contains no `FULLY AUTONOMOUSLY` / `Never ask the user` declarations; sequencing lives in commands
- [ ] **Anti-patterns**: no hooks registered or referenced anywhere in the plugin — see [`docs/anti-patterns.md`](../anti-patterns.md)
