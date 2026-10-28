# barclays-buk-standards

Shared standards for BUK CIO plugins. All other plugins in this marketplace depend on this one.

## Requirements

**Minimum Claude Code version: 2.1.110**

On 2.1.110+, installing any dependent plugin (e.g. `barclays-buk-ui-engineer-sdf`) will automatically install `barclays-buk-standards` first.

On older versions, install this plugin manually before any other:

```bash
/plugin install barclays-buk-standards@barclays-cio-buk
```

Check your version and upgrade:

```bash
/doctor
brew upgrade claude-code   # Homebrew
# or
npm install -g @anthropic-ai/claude-code@latest
```

## Skills

| Skill | Status | Description |
|---|---|---|
| `accessibility` | ✅ Full | WCAG 2.2 AA, Barclays Digital Accessibility Standards V3.0 |
| `security` | ✅ Full | Secure Coding Practices v1.2.6 |
| `consumer-duty` | ✅ Full | Barclays CDA docs + FCA FG22/5 |
| `vulnerable-customers` | ✅ Full | FCA FG21/1 |
| `customer-engagement` | ✅ Full | Customer Engagement Standard v7.2 |
| `api-design` | ✅ Full | Digital API Framework (DAF) |
| `daf` | ✅ Full | DAF Java/Spring Boot implementation rules |
| `chameleon` | ✅ Full | Chameleon Design System component standards |
| `performance` | ✅ Full | BUK VPT NFR platform/channel targets |
| `observability` | ✅ Full | OTel conventions, structured logging |
| `testing` | 🚧 Placeholder | |
| `governance` | 🚧 Placeholder | |
| `ux` | 🚧 Placeholder | |
| `brand` | 🚧 Placeholder | |
| `data` | 🚧 Placeholder | |
| `mobile` | 🚧 Placeholder | |
| `infrastructure` | 🚧 Placeholder | |
| `adr` | 🚧 Placeholder | |

## Ownership

Owned by BUK Principal Engineers. Placeholder skills need content derived from BUK internal standards documents — raise with the Principal Engineering team to progress.
