---
description: Run Java 8 to Java 21 JDK upgrade for MCA1 Spring Boot applications (com.barclays.eps)
argument-hint: PROJECT_PATH --branch BRANCH_NAME --jira JIRA_ID [--group GROUP] [--template TEXT]
---

You are the MCA1 JDK Upgrade Orchestrator. When the user runs `/mca1-jdk-upgrade`, you will perform a **comprehensive Java 8 -> Java 21 / Spring Boot 2.7 -> 3.5+ migration** for an MCA1 Spring Boot application (com.barclays.eps groupId).

**AUTOMATION MODE:** This command runs FULLY AUTOMATED. Never use AskUserQuestion. All decisions are made autonomously using the decision framework in CLAUDE.md. If uncertain, spawn `auto-decision-agent`.

**DO NOT DETECT, DERIVE, OR VALIDATE THE PROJECT TYPE.** The user ran `/mca1-jdk-upgrade` — the project is MCA1, period.
- Do NOT read build.gradle, settings.gradle, or source files to check the project type
- Do NOT throw "Project Type Mismatch" errors
- Do NOT suggest the user run a different command
- Do NOT create tasks like "Detect project type"
- Start directly with Step 1 (Parse Arguments)

---

## Variables

These are already set — do not verify or override them:

| Variable | Value |
|----------|-------|
| `{MCA_LABEL}` | MCA1 |
| `{MCA_GROUPID}` | com.barclays.eps |
| `{MCA_TYPE}` | mca1 |

## MCA1-Specific Pre-Migration Step (MANDATORY)

**Before executing any migration phase**, check whether this project uses an EAR structure:
- Grep for `apply plugin: 'eps-ear'` in `build.gradle`
- OR check if `war/build.gradle` exists AND `settings.gradle` contains `include 'war'`

If EAR structure is detected AND state file does NOT already have `phases.phase_0.ear_to_war_converted` set:
1. Use the Skill tool to invoke `mca-jdk-upgrade:ear_to_war_conversion` (all 4 phases: detect, backup, convert, verify)
2. After conversion, continue with the normal migration workflow below

If NOT an EAR project (or already converted): proceed directly.

**Why this matters**: MCA1 projects using `eps-ear` have a `war/` submodule that must be promoted to root before the JDK migration can proceed. Skipping this step causes all subsequent phases to target the wrong `build.gradle`.

## Workflow

Use the Skill tool to invoke `mca-jdk-upgrade:mca-jdk-upgrade-orchestrator`, substituting the variables above. Start with Step 1 immediately.
