---
name: mts-lessons-learned-index
description: Index of lessons learned from MTS documentation and migration runs
type: reference
---

# MTS Lessons Learned

This directory captures lessons learned from real MTS documentation and migration runs. Use these to avoid repeating known failure modes.

## Index

| File | Scope | Last Updated |
|------|-------|-------------|
| [PATTERNS.md](PATTERNS.md) | Common discovery and migration patterns | See file |
| [example-project.md](example-project.md) | Example walkthrough of a real service migration | See file |

## How to Use

When `mts-discovery-agent`, `mts-api-match-agent`, or `mts-migrate-code-agent` encounter a scenario that matches a known pattern, they should check this directory first:

1. Read `PATTERNS.md` for common failure modes and their fixes
2. Read `example-project.md` for a worked example of the full pipeline

## How to Contribute

After completing a migration run, add any non-obvious findings to `PATTERNS.md`:
- Discovery steps that failed and why
- API match candidates that scored incorrectly and the fix
- Code generation patterns that required manual correction
