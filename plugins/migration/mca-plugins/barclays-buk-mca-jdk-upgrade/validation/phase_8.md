# Phase 8 Validation Checklist

Post-Phase 8 verification checks. Run after Phase 8 completion to confirm push and merge request creation succeeded.

## Checks

### Check 1: All Commits Pushed to Remote

**What**: All phase commits have been pushed to the remote feature branch.

**How to verify**:
```bash
UNPUSHED=$(git log origin/feature/{jira_id}..feature/{jira_id} --oneline 2>/dev/null | wc -l)
if [ "$UNPUSHED" -eq 0 ]; then
  echo "PASS: All commits pushed to remote"
else
  echo "FAIL: $UNPUSHED commits not pushed to remote"
fi
```

**On failure**: Agent must retry `git push -u origin feature/{jira_id}`.

### Check 2: Merge Request Created

**What**: GitLab merge request was created for the feature branch.

**How to verify**:
```bash
# Check using glab CLI
MR_URL=$(glab mr list --source-branch "feature/{jira_id}" --state opened 2>/dev/null | grep -o "https://[^[:space:]]*")
if [ -n "$MR_URL" ]; then
  echo "PASS: Merge request created: $MR_URL"
else
  echo "FAIL: No merge request found for feature/{jira_id}"
fi
```

**On failure**: Agent must retry MR creation via `glab mr create`.

### Check 3: PR.md Generated

**What**: PR.md file exists with comprehensive migration summary.

**How to verify**:
```bash
if [ -f "PR.md" ]; then
  PR_LINES=$(wc -l < PR.md)
  if [ "$PR_LINES" -gt 50 ]; then
    echo "PASS: PR.md exists and has content ($PR_LINES lines)"
  else
    echo "WARN: PR.md exists but seems too short ($PR_LINES lines)"
  fi
else
  echo "FAIL: PR.md not found"
fi
```

**On failure**: Agent must regenerate PR.md using the push-agent.

### Check 4: Temporary Files Cleaned

**What**: Temporary migration artifacts have been cleaned up.

**How to verify**:
```bash
TEMP_FILES=0

# Check for backup files
if find . -name "*.bak" -o -name "*.backup" 2>/dev/null | grep -q .; then
  echo "WARN: Backup files (.bak, .backup) still present"
  TEMP_FILES=$((TEMP_FILES + 1))
fi

# Check for OpenRewrite build directory
if [ -d ".rewrite" ]; then
  echo "WARN: .rewrite directory still present"
  TEMP_FILES=$((TEMP_FILES + 1))
fi

if [ $TEMP_FILES -eq 0 ]; then
  echo "PASS: No temporary files detected"
fi
```

**On failure**: Not blocking, but good housekeeping to clean these.

### Check 5: Lessons Learned Finalized

**What**: Lessons learned file was created and finalized.

**How to verify**:
```bash
PROJECT_NAME=$(basename "$PWD")
LESSONS_FILE=".claude/skills/mca2_jdk_upgrade_reference/lessons_learned/${PROJECT_NAME}.md"

if [ -f "$LESSONS_FILE" ]; then
  LESSONS_LINES=$(wc -l < "$LESSONS_FILE")
  if [ "$LESSONS_LINES" -gt 50 ]; then
    echo "PASS: Lessons learned file exists and has content ($LESSONS_LINES lines)"
  else
    echo "WARN: Lessons learned file exists but seems incomplete ($LESSONS_LINES lines)"
  fi
else
  echo "FAIL: Lessons learned file not found at $LESSONS_FILE"
fi
```

**On failure**: Agent should review logs and generate lessons learned file.

### Check 6: Migration Log Complete

**What**: Migration log contains entries for all 8 phases.

**How to verify**:
```bash
if [ -f "logs/migration.log" ]; then
  PHASES_LOGGED=$(grep -c "^\\[.*\\] PHASE [0-8]:" logs/migration.log 2>/dev/null)
  if [ "$PHASES_LOGGED" -ge 8 ]; then
    echo "PASS: All phases logged ($PHASES_LOGGED phase entries)"
  else
    echo "WARN: Only $PHASES_LOGGED phases logged (expected 8-9)"
  fi
else
  echo "FAIL: Migration log not found"
fi
```

**On failure**: Log may be incomplete or moved.

### Check 7: PATTERNS.md Updated (if applicable)

**What**: If multiple project migrations exist, PATTERNS.md should be aggregated.

**How to verify**:
```bash
LESSONS_COUNT=$(find .claude/skills/mca2_jdk_upgrade_reference/lessons_learned -name "*.md" -not -name "PATTERNS.md" -not -name "README.md" 2>/dev/null | wc -l)
if [ "$LESSONS_COUNT" -ge 2 ]; then
  # Check if PATTERNS.md was modified in this migration session (cross-platform using git)
  PATTERNS_FILE=".claude/skills/mca2_jdk_upgrade_reference/lessons_learned/PATTERNS.md"
  if git diff HEAD "$PATTERNS_FILE" 2>/dev/null | grep -q "^+"; then
    echo "PASS: PATTERNS.md aggregated from $LESSONS_COUNT projects"
  elif git log -1 --name-only --pretty=format: 2>/dev/null | grep -q "PATTERNS.md"; then
    echo "PASS: PATTERNS.md updated in last commit"
  else
    echo "WARN: PATTERNS.md not updated (should aggregate from $LESSONS_COUNT projects)"
  fi
else
  echo "SKIP: Only $LESSONS_COUNT project(s), aggregation not needed yet"
fi
```

**On failure**: Agent should aggregate lessons from all project files into PATTERNS.md.

## Final Phase

Phase 8 is the final phase — by this point, the migration is complete and code is pushed. Any failures here are post-migration cleanup issues that don't affect the migration itself but should be reported.

## Integration

Phase 8 validation ensures all artifacts are properly created, pushed, and documented for future reference.
