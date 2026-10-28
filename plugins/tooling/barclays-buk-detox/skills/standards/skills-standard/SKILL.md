---
name: skills-standard
description: "Defines the required structure and quality standards for all skill files in the CWE remediation pipeline"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/standards/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Skills Standard

All skill files in this project follow a consistent structure to ensure quality and predictability when used as system prompts for Claude Code.
## Quick Start

This skill defines the quality and compliance standards applied to all detox remediations and documentation.

```
# Loaded by detox-report-agent and detox-fix-agent to validate output quality.
```



## Template Structure

Every skill file MUST include these sections:

### Purpose
A clear, one-paragraph description of what this skill does.

### Inputs
- List each expected input with type and description
- Mark required vs optional inputs
- Specify format expectations (JSON, markdown, file path, etc.)

### Steps
1. Numbered, ordered steps the agent should follow
2. Each step should be specific and actionable
3. Include decision points and branching logic where applicable
4. Reference specific tools to use (Read, Edit, Grep, Glob, Bash)

### Output Format
- Specify the exact format of the expected output
- Include a JSON schema or example where applicable
- Define success/failure indicators

### Error Handling
- List common failure modes and how to handle them
- Specify when to retry vs. fail
- Define fallback behaviors

### Constraints
- List things the agent must NOT do
- Performance boundaries (time, cost)
- Security considerations

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
