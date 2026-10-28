---
name: mca2_jdk_upgrade_reference
description: "Reference documentation for Java 8→21 JDK upgrades: javax→jakarta mappings, test migration patterns, Nexus version lookup, Barclays library versions, selective migration skills"
color: blue
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca-jdk-upgrade/skills/mca2_jdk_upgrade_reference/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When Java/Spring Boot target versions change or new MCA project structures are identified
status: Full
---

# MCA2 JDK Upgrade Reference

Essential reference tables for Java 8 → Java 21 / Spring Boot 2.7 → 3.5.x migration. Includes selective migration skills and logging utilities for comprehensive audit trails.
## Quick Start

Reference documentation for MCA2 JDK upgrade patterns, known issues, and solutions.

```bash
# Validate the migrated project
./gradlew clean build test   # Should pass after all phases complete
```


## Reference Files

| File | Contents | Use When |
|------|----------|----------|
| [nexus_version_lookup.md](reference/nexus_version_lookup.md) | Nexus API patterns, MCA2 groupIds, version discovery workflow | Phase 2: Build config + any phase needing dependency updates |
| [mca2_migration_reference.md](reference/mca2_migration_reference.md) | Consolidated reference: build infrastructure (Gradle plugins, wrapper, SSL, API changes), dependency consolidation, platform BOM, Barclays internal libraries (security, MCA, UKC, EPS), migration rules, troubleshooting | Phase 0-2: Build config, dependency management, Barclays library resolution |
| [third_party_dependencies.md](reference/third_party_dependencies.md) | Third-party dependency versions (Spring, Testing, Jakarta, JAXB, IBM MQ), removal/modification lists, Springfox→SpringDoc migration | Phase 2: Third-party dependency resolution |
| [javax_jakarta.md](reference/javax_jakarta.md) | 12 javax→jakarta package pairs + dependencies | Phase 3: Namespace migration |
| [test_migration.md](reference/test_migration.md) | JUnit 4→5 + Mockito 5 + WireMock 3 mappings | Phase 6: Test migration |
| [logging_utilities.md](reference/logging_utilities.md) | Logging format, log levels, what to log, examples | All phases: Logging actions, results, and progress |
| [migration_state.md](reference/migration_state.md) | Migration state file format, phase tracking, resume logic | All phases: State file management and resume detection |

## Related Skills

| Skill | Contents | Use When |
|-------|----------|----------|
| [mca_jdk21_migration](../mca_jdk21_migration/SKILL.md) | Unified MCA1/MCA2 selective migration — project analysis, dependency updates, javax→jakarta, deprecated removal. Uses `migration_type` parameter for MCA1 (com.barclays.eps) vs MCA2 (com.barclays.global.mca) behavior | Phase 1: Selective migration (--type mca1 or --type mca2) |
| [java8_to_java21_features](../java8_to_java21_features/SKILL.md) | Java language features JDK 8→21 (lambdas, records, sealed classes, virtual threads, pattern matching) | Phase 4: Java code modernization |

## Lessons Learned

| File | Contents | Use When |
|------|----------|----------|
| [PATTERNS.md](lessons_learned/PATTERNS.md) | Auto-maintained aggregated patterns from all migrations (recurring issues, proven resolutions, anti-patterns) | Phase 0: Load before starting new migration; All phases: Check for similar past issues |
| [README.md](lessons_learned/README.md) | Lessons learned usage guide and best practices | Reference for understanding the lessons learned system |
| [example-project.md](lessons_learned/example-project.md) | Example lessons learned file with realistic content | Template for what a completed lessons file looks like |

## Template

| File | Purpose |
|------|---------|
| [pr_template.md](templates/pr_template.md) | PR description structure |

## Agent Self-Check

- [ ] Skill loaded before the upgrade phase it governs
- [ ] Source version (Java 8 / Spring Boot 2.7) confirmed before applying upgrade patterns
- [ ] Build verified with ./gradlew clean build after each phase
- [ ] No MCA1/legacy patterns remain after migration step
- [ ] Test suite still passes after code changes
- [ ] Upgrade summary logged to migration report
