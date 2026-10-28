# MTS Migrate Settings

Global configuration for the `/mts-migrate` plugin. These values are read by the orchestrator at startup and passed to strategy files and agents.

---

## GitLab Template

- **Template URL:** `<TO_BE_CONFIGURED>`
- **Default branch:** main

> If Template URL is `<TO_BE_CONFIGURED>`, the orchestrator will prompt the developer at runtime via AskUserQuestion.

---

## Scaffolding Defaults

- **Group ID prefix:** com.barclays.uk
- **Default Spring Boot version:** detect-from-template
- **Default Java version:** detect-from-template

---

## Clone Location

- **Base directory:** code/mts

All Strategy A clones go into `code/mts/<service-name>/`.

---

## Strategy Defaults

- **Default response contract:** ask-developer
