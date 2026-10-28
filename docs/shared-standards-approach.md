# Shared Standards Approach — Research Findings

## Problem

Multiple BUK plugins will need to enforce the same rules — accessibility guidelines, security standards, API design patterns, etc. Duplicating these rules in every plugin's skill files is a maintenance burden: a change to a rule has to be applied in N places.

## Goal

A single source of truth for shared standards, automatically available (and ideally enforced) across all plugins that need it.

---

## Options Investigated

### Option 1 — `dependencies` field + agent `skills` preload (Recommended, Verified)

Claude Code's `plugin.json` supports a `dependencies` array. When a plugin is installed, any listed dependencies are automatically installed alongside it. Agent frontmatter supports a `skills` field that preloads skill content — including skills from other plugins using `plugin-name:skill-name` syntax.

Both mechanisms have been verified against the live Claude Code docs and confirmed working with a live test.

**`plugin.json`:**
```json
{
  "name": "barclays-buk-ui-engineer-sdf",
  "dependencies": ["barclays-buk-standards"]
}
```

**Worker agent frontmatter:**
```yaml
---
name: ui-engineer-sdf-worker-agent
description: ...
skills:
  - barclays-buk-standards:accessibility
  - barclays-buk-standards:security
---
```

**What this gives you:**
- `barclays-buk-standards` is always present when any dependent plugin is installed — auto-installed, not manual
- Enabling a plugin enables its dependencies transitively; disabling a dependency is blocked if another plugin still needs it
- Single source of truth: shared skill files live in `plugins/barclays-buk-standards/skills/`
- Worker agents preload only the standards they need via `skills:` frontmatter — full skill content injected at agent startup
- Removing `barclays-buk-standards` manually is blocked by the CLI if any dependent plugin is still enabled

**Verified behaviour (from docs + live test):**
- `dependencies` field: supported since Claude Code v2.1.110. Auto-installs, auto-enables, blocks orphaned removal.
- Cross-plugin skill preload (`barclays-buk-standards:skill-name` in agent `skills:` field): **confirmed working** via live test on 2026-06-23.
- Reference: [plugin-dependencies](https://code.claude.com/docs/en/plugin-dependencies), [plugins-reference manifest schema](https://code.claude.com/docs/en/plugins-reference#plugin-manifest-schema), [sub-agents preload skills](https://code.claude.com/docs/en/sub-agents#preload-skills-into-subagents)

**Limitations:**
- Enforced at install/enable time. If a user force-removes `barclays-buk-standards` outside normal CLI commands, there is no runtime guard (see Option 2).
- Skills preloaded via `skills:` cannot have `disable-model-invocation: true` set, as preloading draws from the same set Claude can invoke.

---

### Option 2 — `SessionStart` hook (Runtime enforcement, manual only)

A `SessionStart` hook fires before any work begins and can block with exit code `2`. A hook script could check whether `barclays-buk-standards` appears in the installed plugins list and deny the session if not.

```bash
#!/bin/bash
# Check barclays-buk-standards is installed
if ! grep -q "barclays-buk-standards" ~/.claude/plugins/cache/*/plugin.json 2>/dev/null; then
  echo '{"decision":"block","reason":"buk-standards plugin is required. Install it first: /plugin install barclays-buk-standards@barclays-cio-buk"}' >&2
  exit 2
fi
```

**What this gives you:**
- Runtime enforcement — blocks use of the plugin if dependency is missing

**Critical limitation:**
- Hooks **cannot be auto-configured by a plugin**. The `settings.json` a plugin can write only supports `agent` and `subagentStatusLine` fields — not `hooks`
- Users must manually add the hook to their `~/.claude/settings.json` or project `.claude/settings.json`
- This means it's a documented recommendation, not automatic enforcement

---

### Option 3 — Inline duplication (Status quo, not recommended)

Each plugin copies the shared rules into its own `skills/` directory. Simple, but every update requires touching N plugins.

---

## Recommended Approach

**Phase 1 — Install-time enforcement via `dependencies` + agent `skills` preload:**

1. `plugins/barclays-buk-standards/` contains all shared skill files:

   | Skill | Status |
   |---|---|
   | `skills/accessibility/SKILL.md` | ✅ Full — WCAG 2.2 AA, Barclays Digital Accessibility Standards V3.0 |
   | `skills/security/SKILL.md` | ✅ Full — Secure Coding Practices v1.2.6 |
   | `skills/consumer-duty/SKILL.md` | ✅ Full — Barclays CDA docs + FCA FG22/5 |
   | `skills/vulnerable-customers/SKILL.md` | ✅ Full — FCA FG21/1 |
   | `skills/customer-engagement/SKILL.md` | ✅ Full — Customer Engagement Standard v7.2 |
   | `skills/api-design/SKILL.md` | ✅ Full — Digital API Framework (DAF) |
   | `skills/performance/SKILL.md` | ✅ Full — BUK VPT NFR platform/channel targets |
   | `skills/testing/SKILL.md` | 🚧 Placeholder |
   | `skills/governance/SKILL.md` | 🚧 Placeholder |
   | `skills/ux/SKILL.md` | 🚧 Placeholder |
   | `skills/brand/SKILL.md` | 🚧 Placeholder |
   | `skills/observability/SKILL.md` | 🚧 Placeholder |
   | `skills/data/SKILL.md` | 🚧 Placeholder |
   | `skills/mobile/SKILL.md` | 🚧 Placeholder |
   | `skills/infrastructure/SKILL.md` | 🚧 Placeholder |
   | `skills/adr/SKILL.md` | 🚧 Placeholder |

2. Add `"dependencies": ["barclays-buk-standards"]` to each plugin's `plugin.json` that needs shared standards
3. In each dependent plugin's worker agent, declare the relevant skills in frontmatter:
   ```yaml
   skills:
     - barclays-buk-standards:accessibility
     - barclays-buk-standards:security
   ```

**Phase 2 — Documented hook setup (optional, manual):**

Document in `barclays-buk-standards` README how users can add a `SessionStart` hook for stricter runtime enforcement. Cannot be automated.

---

## Open Questions

1. ~~Does `dependencies` in `plugin.json` work in the current Claude Code CLI version?~~ **Resolved: Yes.** Supported since v2.1.110. Auto-installs dependencies, blocks orphaned removal.
2. ~~Do CLI agent frontmatter skill references support cross-plugin syntax (`barclays-buk-standards:accessibility`)?~~ **Resolved: Yes.** Confirmed working via live test on 2026-06-23.
3. Is a `barclays-buk-standards` plugin the right home, or should it be a separate marketplace-level concern (group-level standards rather than CIO area)? **Resolved:** Lives at `plugins/barclays-buk-standards/` as a top-level peer alongside the group folders, owned by BUK Principal Engineers.

---

## Current Structure

```
plugins/barclays-buk-standards/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    ├── accessibility/SKILL.md      ✅ Full
    ├── security/SKILL.md           ✅ Full
    ├── consumer-duty/SKILL.md      ✅ Full
    ├── vulnerable-customers/SKILL.md ✅ Full
    ├── customer-engagement/SKILL.md ✅ Full
    ├── api-design/SKILL.md         ✅ Full
    ├── performance/SKILL.md        ✅ Full
    ├── testing/SKILL.md            🚧 Placeholder
    ├── governance/SKILL.md         🚧 Placeholder
    ├── ux/SKILL.md                 🚧 Placeholder
    ├── brand/SKILL.md              🚧 Placeholder
    ├── observability/SKILL.md      🚧 Placeholder
    ├── data/SKILL.md               🚧 Placeholder
    ├── mobile/SKILL.md             🚧 Placeholder
    ├── infrastructure/SKILL.md     🚧 Placeholder
    └── adr/SKILL.md                🚧 Placeholder
```

Example dependent plugin `plugin.json`:
```json
{
  "name": "barclays-buk-ui-engineer-sdf",
  "dependencies": ["barclays-buk-standards", "barclays-buk-ui-engineer"]
}
```

Example worker agent frontmatter:
```yaml
---
name: ui-engineer-sdf-worker-agent
description: ...
skills:
  - barclays-buk-ui-engineer:figma
  - barclays-buk-standards:accessibility
  - barclays-buk-standards:security
---
```
