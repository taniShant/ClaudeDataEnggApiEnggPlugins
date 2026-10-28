---
name: branching-strategy
description: "Systematic approach to breaking complex development work into sequential phases with commits per phase and clear validation checkpoints"
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
color: orange
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/branching_strategy/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# Skill: Iterative Git Commit Strategy

## AUTOMATION MODE

When used during SDK3 migration:
- Commits are created automatically after each phase validation passes
- Never ask the user for JIRA ID -- it's passed as a parameter to /sdk3-migrate
- Push to remote after each phase commit for backup

## Overview

A systematic approach to breaking complex development work into sequential phases with commits marking each phase completion. Each phase builds on the previous one with clear validation checkpoints, making changes easy to track, compare, and revert if needed.

## When to Use This Skill

Use this commit strategy when:

- Working on complex features that span multiple logical phases
- Need clear validation checkpoints between implementation stages
- Want to isolate changes by phase for easier debugging and review
- Require ability to rollback to specific implementation stages
- Working on projects where sequential dependencies exist between tasks

## Quick Start

### Phase Structure

```
main → feature/<jira-id>
       ↓
       Phase 1 commit → Phase 2 commit → Phase 3 commit → Phase 4 commit
```

### Basic Workflow

1. **Create Feature Branch from main**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/<JIRA-ID>
   git push -u origin feature/<JIRA-ID>
   ```

2. **Work on Phase 1**
   - Complete foundational tasks
   - Run tests and validation checks
   - Commit with Phase 1 marker

3. **Work on Phase 2**
   - Complete core feature tasks
   - Run tests and validation checks
   - Commit with Phase 2 marker

4. **Repeat for Remaining Phases**
   - Phase 3: Integration
   - Phase 4: Validation & Cleanup

5. **Push and Create PR**
   ```bash
   git push origin feature/<JIRA-ID>
   # Create PR from feature/<JIRA-ID> to main
   ```

## Core Phases

| Phase | Focus Area | Validation Checkpoint |
|-------|-----------|----------------------|
| **Phase 1** | Foundation & Setup | Configuration loads, dependencies resolve, build runs |
| **Phase 2** | Core Feature | Functionality works, code compiles, unit tests pass |
| **Phase 3** | Integration | External services connected, integration tests pass |
| **Phase 4** | Validation & Cleanup | All tests pass, performance acceptable, docs updated |
| **Final** | PR Preparation | Ready for team review |

## Key Commands

### View Phase History

```bash
# See all phase commits in the feature branch
git log --oneline --grep="Phase"

# View detailed phase commit
git show <commit-hash>

# See all commits since branching from main
git log --oneline main..HEAD
```

### Compare Between Phases

```bash
# See what changed between Phase 1 and Phase 2
git diff <phase-1-commit-hash> <phase-2-commit-hash>

# View commits between phases
git log --oneline <phase-1-commit-hash>..<phase-2-commit-hash>
```

### Revert to Earlier Phase

```bash
# Create a revert commit back to Phase 2 (keeps history)
git revert --no-commit <phase-3-commit-hash>..<phase-4-commit-hash>
git commit -m "<JIRA-ID> : Revert to Phase 2 state"

# Or reset to specific phase (rewrites history - use with caution)
git reset --hard <phase-2-commit-hash>
git push --force-with-lease origin feature/<JIRA-ID>
```

### Fix Earlier Phase

```bash
# Make fixes in current branch
git add .
git commit -m "<JIRA-ID> : Fix for Phase 2 issue

- Fix description
- Additional context"

git push origin feature/<JIRA-ID>
```

## Benefits

1. **Simplified Workflow** - Single branch to manage instead of multiple phase branches
2. **Phase Isolation** - Each commit marks a clear phase boundary
3. **Easy Comparison** - Quickly see what changed in each phase using commit hashes
4. **Debugging** - Use git bisect or revert to specific phase commits
5. **Validation Gates** - Clear checkpoints prevent cascading problems
6. **Rollback Capability** - Revert to any phase commit if needed
7. **Clear History** - Organized commits make review easier
8. **Simpler Merges** - No complex branch merging or rebasing between phases

## Common Patterns

### Atomic Commits Within Phases

```bash
# Work on Phase 1 tasks
git add .
git commit -m "<JIRA-ID> : Task 1.1 - Setup project configuration"

git add .
git commit -m "<JIRA-ID> : Task 1.2 - Add required dependencies"

git add .
git commit -m "<JIRA-ID> : Task 1.3 - Configure build system"

# Phase checkpoint commit
git add .
git commit -m "<JIRA-ID> : Phase 1 - Foundation complete

- Project configuration setup
- Dependencies added
- Build system configured

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase Validation Before Commit

```bash
# Run validation commands before phase commit
./run-tests.sh
./check-build.sh
./lint.sh

# Commit only after validation passes
git add .
git commit -m "<JIRA-ID> : Phase X - <description>..."

# Push to remote
git push origin feature/<JIRA-ID>
```

---

## MANDATORY: Commit Protocol

**CRITICAL: After completing each phase validation, you MUST commit changes before proceeding.**

### Step 1: Get JIRA ID

**If JIRA ID is not already known in the current conversation context**, ask the user:

> "Please provide the JIRA ID for this work (e.g., PROJECTKEY-12345):"

**Store the JIRA ID** and reuse it for all subsequent phase commits in the session.

### Step 2: Review and Commit Changes

```bash
# Review what will be committed
git status
git diff --stat

# Stage and commit with JIRA ID
git add -A
git commit -m "<JIRA-ID> : Phase N - <Short description>

<Detailed bullet points of changes>

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 3: Verify Commit

```bash
git log --oneline -1  # Confirm JIRA ID is present
```

### Commit Message Format

```
<JIRA-ID> : Phase <N> - <Short description>

- Change 1
- Change 2
- Change 3

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Example

```
CARDOPSAPI-15153 : Phase 2 - Package and import migration complete

- Migrate javax.* to jakarta.* imports
- Update SDK2 packages to SDK3 equivalents
- Fix compilation errors after package changes

Co-Authored-By: Claude <noreply@anthropic.com>
```

**NEVER proceed to next phase without committing current phase changes.**

---

## Customization

Adapt the phases to your project needs:

- **3-Phase Projects**: Foundation -> Implementation -> Validation
- **5-Phase Projects**: Add "Phase 5: Documentation & Polish"
- **Different Names**: Use domain-specific phase names in commits (e.g., `Phase 1 - Schema Setup`, `Phase 2 - API Implementation`, `Phase 3 - UI Integration`)

## Git Aliases (Optional)

```bash
# Show phase commits
git config alias.phases 'log --oneline --grep="Phase"'

# Show specific phase commit details
git config alias.phase-show '!f() { git log --grep="Phase $1" -1; }; f'

# Compare between two phase numbers
git config alias.phase-diff '!f() {
  PHASE1=$(git log --grep="Phase $1" --format="%H" -1)
  PHASE2=$(git log --grep="Phase $2" --format="%H" -1)
  git diff $PHASE1..$PHASE2
}; f'
```

## Checklist for Success

- [ ] **Get JIRA ID from user at start of work (if not in context)**
- [ ] Create single feature branch: `feature/<JIRA-ID>`
- [ ] Define clear phases with validation checkpoints
- [ ] Make atomic commits for individual tasks
- [ ] **Commit with Phase marker after each phase validation**
- [ ] Validate thoroughly before committing phase checkpoint
- [ ] Push to remote after each phase for backup
- [ ] Document phase goals and completion criteria in commit messages
- [ ] Create PR from feature branch to main when all phases complete

## Version

**Skill Version:** 2.1
**Compatible With:** Git 2.0+
**Last Updated:** 2026-02-17
**Changes:** Added AUTOMATION MODE directive for SDK3 migration usage

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
