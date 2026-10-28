# PR Description Template: MCA2 JDK Upgrade

Use this template to generate the PR description after completing the migration.

---

## {JIRA_ID}: Java 8 → Java 21 / Spring Boot 2.7 → 3.5.x Migration

### Summary

Migrates **{PROJECT_NAME}** from Java 8 / Spring Boot 2.7.x to Java 21 / Spring Boot 3.5.x using the MCA2 JDK Upgrade workflow.

### Changes by Phase

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Project Analysis & Branch Setup | {STATUS} |
| Phase 1 | OpenRewrite Automated Migration | {STATUS} |
| Phase 2 | Build Configuration (Gradle/Maven, Java 21, Spring Boot 3.5.x) | {STATUS} |
| Phase 3 | javax → jakarta Namespace Migration | {STATUS} |
| Phase 4 | Java 8→21 Code Changes | {STATUS} |
| Phase 5 | Apache HttpClient → JDK HttpClient | {STATUS_OR_SKIPPED} |
| Phase 6 | Test Migration (JUnit 4→5, Mockito 5) | {STATUS} |
| Phase 7 | Validation & Coverage Enforcement | {STATUS} |

### Validation Results

| Metric | Target | Actual |
|--------|--------|--------|
| Unit Test Coverage (JaCoCo) | ≥ 90% | {ACTUAL}% |
| Mutation Test Coverage (Pitest) | ≥ 90% | {ACTUAL}% |
| Compilation | Pass | {PASS/FAIL} |
| Unit Tests | Pass | {PASS/FAIL} |
| Integration Tests | Pass | {PASS/FAIL} |

### Key Dependency Updates

| Dependency | Old Version | New Version |
|-----------|-------------|-------------|
| Java | 8 | 21 |
| Spring Boot | 2.7.x | {SPRING_BOOT_VERSION} |
| Gradle Wrapper | {OLD} | 8.5 |
| JUnit | 4.13.x | 5.11.x (Jupiter) |
| Mockito | {OLD} | 5.14.x |
| Jakarta EE | javax.* | jakarta.* |
| mca-experience-common-starter | {OLD} | 3.0.0-RELEASE |
| mca-generic-experience-api-starter | {OLD} | 2.0.0-RELEASE |
| Pitest Plugin | {OLD} | 1.15.0 |

### Breaking Changes

- **javax → jakarta**: All Enterprise Java imports changed from `javax.*` to `jakarta.*`
- **JUnit 5**: Test annotations changed (`@Before` → `@BeforeEach`, etc.)
- **Spring Security**: `WebSecurityConfigurerAdapter` replaced with `SecurityFilterChain` bean
- **Spring Boot Properties**: `spring.redis.*` → `spring.data.redis.*` (if applicable)
- {ADDITIONAL_BREAKING_CHANGES}

### Reviewer Checklist

- [ ] No `javax.` imports remain (except safe packages: `javax.swing`, `javax.crypto`, `javax.sql`, etc.)
- [ ] No Apache HttpClient usage remains (`org.apache.http.*`)
- [ ] No JUnit 4 annotations remain (`@Before`, `@After`, `@RunWith`, etc.)
- [ ] All test tasks have `useJUnitPlatform()`
- [ ] `--add-opens` JVM args present for test tasks
- [ ] No public Maven repositories (`mavenCentral()`, `gradlePluginPortal()`)
- [ ] All repositories point to Barclays Nexus
- [ ] OpenRewrite configuration removed from build file
- [ ] Gradle wrapper updated to 8.5 (Nexus URL)
- [ ] Spring Boot version is 3.5.x
- [ ] Java source/target compatibility is 21
- [ ] Unit test coverage ≥ 90%
- [ ] Mutation test coverage ≥ 90%
- [ ] `spring.factories` replaced with `AutoConfiguration.imports` (if applicable)
- [ ] Application starts successfully (`bootRun` / `spring-boot:run`)

### Co-Authored-By

Co-Authored-By: Claude <noreply@anthropic.com>
