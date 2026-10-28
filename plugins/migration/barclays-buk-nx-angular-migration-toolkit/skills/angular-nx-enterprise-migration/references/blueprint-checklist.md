# Blueprint Angular Checklist

Use this checklist for every migration phase.

The goal is to preserve Barclays Blueprint Angular component behaviour and compatibility.

## Files and areas to inspect

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

## Packages to inspect

```text
@barclays/blueprint-angular
@barclays/olb-blueprint-angular-extended
@barclays/olb-bp-common-footer
@barclays/olb-bp-common-header
@barclays/olb-bp-nps-survey
@barclays/olb-bp-session-timeout
@barclays/olb-core
@angular/cdk
```

## Usage patterns to search

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

## Compatibility checks

Check:

- package version
- peer dependency range
- Angular version support
- Angular CDK version support
- module import changes
- component selector changes
- style import changes
- theme import changes
- accessibility wrappers
- custom elements schema usage

## UI risks

Watch for:

- component module import failures
- template binding failures
- SCSS variable changes
- CSS class changes
- theme regressions
- accessibility attribute changes
- focus handling changes
- keyboard navigation regressions
- custom wrapper incompatibility
- peer dependency mismatch

## Accessibility-sensitive checks

Pay attention to:

- buttons
- links
- form controls
- modals
- accordions
- tabs
- dropdowns
- alerts
- headers
- footers
- session timeout
- NPS survey
- navigation components

## Do not guess internal package compatibility

If compatibility cannot be established locally, stop and report:

```markdown
## Blueprint compatibility blocker

Package:
Current version:
Target Angular version:
Known peer dependency:
Missing information:
Impact:
Decision needed:
```

## Required output

Produce this section in every phase report:

```markdown
## Blueprint validation

| Check | Status | Notes |
|---|---|---|
| Blueprint package version reviewed | | |
| peer dependencies reviewed | | |
| Angular compatibility reviewed | | |
| module imports reviewed | | |
| templates reviewed | | |
| styles reviewed | | |
| accessibility-sensitive components reviewed | | |
| UI smoke areas identified | | |

## Blueprint risks

...
```