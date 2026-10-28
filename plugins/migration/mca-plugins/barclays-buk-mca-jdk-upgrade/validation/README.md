# Validation Checklists

Post-phase validation checklists for the MCA2 JDK upgrade migration. Each file contains checks that run after a specific phase to verify expected state changes occurred.

## Files

| File | Phase | Checks | Description |
|------|-------|--------|-------------|
| `phase_0.md` | Phase 0 | 5 | Repository deduplication, public repos, distributionUrl, truststore, Nexus version |
| `phase_1.md` | Phase 1 | 7 | OpenRewrite log evidence (BLOCKER), Java files modified (BLOCKER), OpenRewrite cleanup, no public repos, Gradle 8.5+, Java 21, compilation |
| `phase_2.md` | Phase 2 | 8 | Dependencies consolidation, platform BOM, Gradle APIs, Java/Spring Boot versions |
| `phase_2_5.md` | Phase 2.5 | 3 | Test package alignment, test compilation, matching package structure |
| `phase_3.md` | Phase 3 | 3 | javax→jakarta imports, jakarta dependencies, compilation |
| `phase_4.md` | Phase 4 | 7 | Removed APIs, JAXB deps, --add-opens, Spring Security, Jackson JSR-310, Dockerfile, compilation |
| `phase_5.md` | Phase 5 | 5 | HttpClient migration (conditional - only if Apache HttpClient detected) |
| `phase_6.md` | Phase 6 | 5 | JUnit 4→5, useJUnitPlatform, --add-opens, Mockito 5, test pass |
| `phase_7.md` | Phase 7 | 4 | Unit coverage ≥90%, mutation coverage ≥90%, tests pass, full validation scan |
| `phase_8.md` | Phase 8 | 7 | Commits pushed, MR created, PR.md generated, temp files cleaned, lessons finalized |

## How Validations Are Used

1. **Inline in agent**: The main agent (`mca-jdk-upgrade-agent.md`) has POST-PHASE VALIDATION sections that run bash checks after each phase commit
2. **Validation agent**: The `mca-jdk-validation-agent` can be invoked with `validation_phase` parameter to run phase-specific checks
3. **Reference**: These files serve as the source of truth for what each phase should achieve

## Adding New Validations

When adding a new procedure to any phase:
1. Add the implementation to `agents/mca-jdk-upgrade-agent.md`
2. Add a corresponding check to the appropriate `validation/phase_N.md` file
3. Add a corresponding red flag to `agents/mca-jdk-validation-agent.md`
4. Update the inline POST-PHASE VALIDATION section in the agent
