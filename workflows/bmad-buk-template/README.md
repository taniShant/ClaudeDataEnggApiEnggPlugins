# BUK × BMAD Template

A BMAD custom module that wires BUK Barclays domain knowledge into BMAD's standard agent roles.

## What this does

Injects BUK `persistent_facts` and skill references into BMAD's product manager, UX designer, architect, engineer, and quality agent roles. After applying this template, BMAD agents will automatically apply:

- **Consumer Duty** (FCA FG22/5) — PM, UX, Copywriter
- **Vulnerable customers** — PM, UX, Copywriter
- **Barclays Secure Coding Practices** — Architect, Engineers
- **BUK API Design standards** — API Engineer, Solution Architect
- **WCAG 2.1 AA accessibility** — UX, UI Engineers, QE, Accessibility Auditor
- **BUK governance triggers** — PM (DRA/FRA, Change Control, RAID)

## Usage

```bash
# From your project root (after BMAD is installed)
cp -r path/to/buk/workflows/bmad-buk-template/_bmad/custom/* _bmad/custom/

# Install BUK plugins
/plugin marketplace add git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git
/plugin install barclays-buk-standards@barclays-cio-buk
# ... install specific plugins you need (see bmad-integration.md)
```

## Files

```
_bmad/custom/
├── config.toml                     ← Registers custom BUK agents (QA, Security)
├── bmad-agent-pm.toml              ← Product Manager (BMAD default) + Consumer Duty, governance
├── bmad-agent-ux-designer.toml     ← UX Designer (BMAD default) + accessibility, Consumer Duty
├── bmad-agent-architect.toml       ← Solution Architect (BMAD default) + api-design, security, ADR
├── bmad-agent-dev.toml             ← Developer (BMAD default) + security, api-design, SDF rules
├── bmad-agent-tech-writer.toml     ← Technical Writer (BMAD default) + architecture docs, ADR
├── bmad-agent-analyst.toml         ← Analyst (BMAD default) + observability, reliability, incident
├── bmad-agent-qa.toml              ← Quality Engineer (BUK custom) + testing, accessibility
└── bmad-agent-security.toml        ← Security Architect (BUK custom) + Barclays Secure Coding
```

BMAD has 6 default agents: Analyst, Product Manager, Architect, Developer, UX Designer, Technical Writer. BUK adds two custom agents (QA, Security) via `config.toml`.

## Customisation

Each `.toml` file is a sparse override — only the fields you want to change. You can:

- Add project-specific `persistent_facts` (e.g. your service name, tech stack)
- Extend the `menu` with additional BUK commands
- Override `principles` to add team-specific working agreements

See [BMAD customisation docs](https://docs.bmad-method.org/how-to/expand-bmad-for-your-org/) for the full override model.

## See also

- [`workflows/bmad-integration.md`](../bmad-integration.md) — full integration guide
- [`plugins/barclays-buk-standards/`](../../plugins/barclays-buk-standards/) — all available BUK skills
- [`docs/plugin-principles.md`](../../docs/plugin-principles.md) — BUK plugin design principles
