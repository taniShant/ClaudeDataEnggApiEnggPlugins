# barclays-buk-confluence-confluence-tree-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-confluence-confluence-tree-v1` |
| Plugin name | `barclays-buk-confluence` |
| Component type | skill-model-invocable |
| Owner | Vishal Khare |
| Action scope | read-only |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-confluence@barclays-cio-buk |
| Native command | `/barclays-buk-confluence:confluence-tree` |
| Skill name | `confluence-tree` |

## Description

Browse the page hierarchy of a Confluence space or view child pages under a given page

## When to use

Use when you need to browse the page hierarchy of a Confluence space or see what child pages exist under a given page. NOT for reading page content (use confluence-read).

## Inputs

- `SPACE_KEY` (required, one of): A Confluence space key to browse the top-level page hierarchy (e.g. `ENG`)
- `PAGE_ID` (required, one of): A numeric Confluence page ID to list child pages under that specific page

## Preconditions

- The `barclays-buk-confluence` plugin must be installed and accessible
- The user must have network access to the internal Confluence instance
- Valid authentication/credentials for the Confluence API must be configured
- The target space or page must exist and be readable by the user

## Expected outputs

- An indented tree structure showing page titles and their hierarchy within the space or under the given parent page
- Each entry includes the page title and a link to the Confluence page

## Exclusions

- Does not read or display the body content of any page — use confluence-read for that
- Does not search for pages by keyword — use confluence-search for that
- Does not create, edit, or delete pages
- Does not recurse beyond the immediate child level unless the skill is configured to do so

## Verification

The capability completed successfully when an indented page tree is displayed with page titles and links. If the space is empty or the page has no children, an explicit message stating that no child pages exist will be shown. If the space key or page ID is invalid, an error message will be returned.
