# Migration Lessons: scp-eps-cheque-processing

**Date:** 2026-03-10
**JIRA:** EMMDIGI-22935
**Branch:** feature/EMMDIGI-22935 → feature/feature.jdk21_migration
**MR:** !80
**Migration Type:** MCA1
**Java:** 8 → 21
**Spring Boot:** 2.7 → 3.5.10

---

## Issues Encountered

### 1. EAR→WAR Conversion Not Performed in Initial Migration
**Phase:** Phase 0 (EAR→WAR)
**Impact:** `war/` submodule still present after JDK migration — CI and bootRun broken
**Root Cause:** The `/mca1-jdk-upgrade` command ran the JDK migration phases but did not automatically detect and convert the EAR structure. EAR→WAR conversion had to be triggered separately with the `ear_to_war_conversion` skill.
**Fix:** Ran `ear_to_war_conversion` skill — promoted `war/` to root, merged `build.gradle`, fixed path references, updated CI variables.
**Lesson:** The `mca1-jdk-upgrade` orchestrator should detect EAR structure and invoke `ear_to_war_conversion` automatically before JDK migration phases begin.

### 2. Wrong `mainClass` in `bootRun`
**Phase:** Post-EAR→WAR
**Impact:** `bootRun` used `com.barclays.scp.eps.chequeprocessing.Application` — class does not exist; app failed to start
**Root Cause:** The merged `build.gradle` used a generic class name guess rather than the actual `@SpringBootApplication` class, which is `ChequeProcessingApplication`.
**Fix:** Set `mainClass = 'com.barclays.scp.eps.chequeprocessing.ChequeProcessingApplication'`
**Lesson:** Always grep `src/main/java/` for `@SpringBootApplication` annotation to determine the correct FQCN before setting `mainClass`.

### 3. `archivePath` Deprecated in Gradle 8
**Phase:** Post-EAR→WAR
**Impact:** `pathingJar.archivePath` caused `Could not get unknown property 'archivePath'` build failure
**Root Cause:** `archivePath` was removed in Gradle 7. The merged `build.gradle` retained the old API.
**Fix:** `pathingJar.archivePath` → `pathingJar.archiveFile.get().asFile`
**Lesson:** Add `archivePath` to the Gradle 8 cleanup checklist in Step 8 of `ear_to_war_conversion`.

### 4. Spring Boot 3.x Fatal Logback Startup Error
**Phase:** CI component test (bootRun)
**Impact:** Application never bound to port 8080 in CI — component tests all failed
**Root Cause:** `application.properties` and `application-dev.properties` set `logging.file.path=/opt/springboot/logs/chequeprocessing/`. In Spring Boot 3.x, a `RollingFileAppender` that cannot create its configured log directory causes a **fatal** `IllegalStateException: Logback configuration error detected` at startup. In Spring Boot 2.x, this was a non-fatal warning.
**Fix:**
```groovy
bootRun {
    doFirst { new File("${rootDir}/build/logs").mkdirs() }
    jvmArgs "-Dlogging.file.path=${rootDir}/build/logs"
    jvmArgs "-Dserver.tomcat.accesslog.directory=${rootDir}/build/logs"
}
```
**Lesson:** This is a universal issue for all MCA apps migrating to Spring Boot 3.x. Add Step 13 to `ear_to_war_conversion` skill and include it in the main JDK migration checklist.

### 5. Stale `war/src/` Keystore Paths in `application-dev.properties`
**Phase:** Post-EAR→WAR
**Impact:** Unresolvable Spring property placeholders for SSL keystore paths; harmless at runtime (overridden by JVM args) but incorrect
**Root Cause:** `application-dev.properties` had:
```
core.rest-template.socket-factory.external-ssl.key-store-path=${rootDir}/war/src/main/resources/keystores/mqssl.jks
```
After EAR→WAR flattening, `war/src/` no longer exists. Keystores are at `src/test/resources/keystores/`.
**Fix:** Updated paths to `${rootDir}/src/test/resources/keystores/mqssl.jks`
**Lesson:** Step 5.5 of `ear_to_war_conversion` should also scan `src/main/resources/` for `war/src/` references, not just `build.gradle`.

### 6. Veracode SAST `cp` Failure — WAR Not Found
**Phase:** CI Veracode scan
**Impact:** `cp: cannot stat 'scp-eps-cheque-processing-EMMDIGI-22935.EMMDIGI-22935.001.war': No such file or directory`
**Root Cause:** `BUILD_LIB_PATH` in `.gitlab-ci-variables.yml` was `war/build/libs/` (old EAR submodule path) rather than `build/libs/`. GitLab CI artifact exposure used the wrong directory, so the Veracode job received no artifact.
**Fix:** Step 12 of `ear_to_war_conversion` replaces all `war/build/` → `build/` in `.gitlab-ci-variables.yml`. This fix was already applied. The Veracode failure shown was from a pipeline run before the fix was pushed.
**Lesson:** Already handled by Step 12 — confirmed working. The Veracode failure can be safely ignored for pipeline runs triggered before the fix commit.

### 7. `jvmArgs` in `bootRun` ARE Applied by CI
**Phase:** Investigation / CI debugging
**Symptom:** CI runs `./gradlew bootrun` without `-Dspring.profiles.active=dev`. Appeared that dev profile was not being activated.
**Actual Behaviour:** `jvmArgs` defined inside the `bootRun {}` task block in `build.gradle` ARE applied unconditionally when the task runs. CI not explicitly passing `-Dspring.profiles.active=dev` on the command line makes no difference. The dev profile IS active during CI component tests.
**Lesson:** When diagnosing CI vs local behaviour differences, always check that task-level `jvmArgs` are applied in both environments.

### 8. JCEKS Placeholder Resolver Fails in CI After Logback Fix
**Phase:** CI component test (bootRun) — second failure after Logback fix
**Impact:** `bootRun` still fails; Spring fails to start with `JCEKS KeyStore initialization failed` and `NullPointerException`
**Root Cause:** `placeholder.resolver.vault=true` in `application.properties` enables `JceksSecretsToSpringEnvironmentPropertiesPostProcessor`. The processor tries to load a JCEKS keystore via a property whose value is null in CI/local environments. Fails at `FileInputStream.<init>(FileInputStream.java:144)`.
**Fix:** Added `-Dplaceholder.resolver.vault=false` to `bootRun` JVM args in `build.gradle`
**Lesson:** Any MCA app with `mca-jceks-spring-properties-processor` on the classpath AND `placeholder.resolver.vault=true` will hit this. Add Step 13.4 to `ear_to_war_conversion` skill; always add this override to `bootRun`.

### 9. Duplicate `ScheduledAnnotationBeanPostProcessor` — Spring Boot 3.x Fatal Failure
**Phase:** Post-migration bootRun validation
**Impact:** `BeanDefinitionParsingException: Only one ScheduledAnnotationBeanPostProcessor may exist within the context.` — app fails to start
**Root Cause:** `eps-cheque-processing-config.xml` contained `<task:annotation-driven/>`. In Spring Boot 2.x, this was tolerated alongside Spring's auto-configured scheduler. Spring Boot 3.x (Spring Framework 6.x) now throws a fatal exception if more than one `ScheduledAnnotationBeanPostProcessor` is registered.
**Fix:** Removed `<task:annotation-driven/>` from `eps-cheque-processing-config.xml` and cleaned up the unused `xmlns:task` and `xmlns:mvc` namespace declarations. Spring Boot auto-configuration handles scheduling automatically.
**Lesson:** After EAR→WAR / Spring Boot 3.x migration, scan all `@ImportResource` XML files for `<task:annotation-driven/>` and remove it. Spring Boot replaces the need for this XML element.

---

## What Went Well

- All javax→jakarta imports migrated correctly (21 files)
- Spring Boot 3.5.10 + MCA BOM 2.3.021 dependency resolution worked cleanly
- Test suite fully migrated to JUnit 5 + Mockito 5
- All unit tests passed after migration
- EAR→WAR structural flattening completed successfully

---

## Commit History

```
071a257  Remove duplicate ScheduledAnnotationBeanPostProcessor (task:annotation-driven in XML)
ca34122  Disable JCEKS vault placeholder resolver in bootRun
25e0c3e  Fix bootRun startup failures in CI (logging + Tomcat access log overrides, stale keystore paths)
9176ece  Fix bootRun mainClass and archivePath for Gradle 8
5d66c64  EAR to WAR conversion - flatten multi-module structure
4bb826e  Phase 8 - Migration complete, awaiting push authorization
a5093b1  Phase 7 - Validation passed, tests pass
deb1b40  Phase 6 - Test migration to JUnit 5 and Mockito 5 complete
70f6db2  Phase 4 - Java 8 to 21 code changes and Spring Boot 3 API updates
4420068  Phase 3 - javax to jakarta namespace migration complete
```
