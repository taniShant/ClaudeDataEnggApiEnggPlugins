Use the angular-nx-enterprise-migration skill.

Use the blueprint-angular-specialist agent mindset.

Task:
Review Blueprint Angular compatibility for the current migration phase.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| phase | No | Migration phase to review (e.g. "12 to 13", defaults to current) |

Rules:
- Do not edit files unless explicitly asked.
- Do not run migrations.
- Do not guess internal @barclays package compatibility.
- Treat @barclays packages as internal source-of-truth dependencies.
- Preserve Blueprint component behaviour.
- Preserve accessibility-sensitive behaviour.

Inspect files and areas:

```text
package.json
package-lock.json
src/app/**/*.module.ts
src/app/**/*.component.ts
src/app/**/*.component.html
src/app/**/*.component.scss
libs/**/*.module.ts
libs/**/*.component.ts
libs/**/*.component.html
libs/**/*.component.scss
shared-ui modules
design-system wrapper modules
theme files
global styles
```

Search for:

```text
Blueprint
Bp
bp-
barclays
CUSTOM_ELEMENTS_SCHEMA
NO_ERRORS_SCHEMA
@barclays/blueprint-angular
@barclays/olb-
```

Commands to run if appropriate:

```bash
grep -R "Blueprint\|Bp\|bp-\|CUSTOM_ELEMENTS_SCHEMA\|NO_ERRORS_SCHEMA\|@barclays/blueprint-angular\|@barclays/olb-" -n src apps libs . 2>/dev/null || true
npm ls @barclays/blueprint-angular @barclays/olb-blueprint-angular-extended @barclays/olb-bp-common-footer @barclays/olb-bp-common-header @barclays/olb-bp-nps-survey @barclays/olb-bp-session-timeout @barclays/olb-core @angular/cdk || true
```

Output format:

```markdown
# Blueprint Angular Compatibility Review

## Blueprint package summary

| Package | Version | Evidence | Risk |
|---|---:|---|---|
| @barclays/blueprint-angular | | | |
| @barclays/olb-blueprint-angular-extended | | | |
| @barclays/olb-bp-common-footer | | | |
| @barclays/olb-bp-common-header | | | |
| @barclays/olb-bp-nps-survey | | | |
| @barclays/olb-bp-session-timeout | | | |
| @barclays/olb-core | | | |
| @angular/cdk | | | |

## Files inspected

```text
...
```

## Usage patterns found

| Pattern | Found | Location | Notes |
|---|---|---|---|
| Blueprint module imports | | | |
| bp-* selectors | | | |
| CUSTOM_ELEMENTS_SCHEMA | | | |
| NO_ERRORS_SCHEMA | | | |
| global Blueprint styles | | | |
| SCSS overrides | | | |

## Compatibility assessment

...

## UI smoke areas

- ...

## Accessibility-sensitive areas

- ...

## Blockers

| Package | Issue | Evidence | Decision needed |
|---|---|---|---|
| | | | |

## Required changes

...

## Recommendation

...
```

Do not apply fixes unless explicitly asked.
