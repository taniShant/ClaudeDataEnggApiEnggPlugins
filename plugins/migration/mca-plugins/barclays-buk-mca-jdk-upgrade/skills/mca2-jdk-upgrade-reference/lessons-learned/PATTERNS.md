# Cross-Project Migration Patterns

> **Auto-maintained file.** The `mca-jdk-upgrade-agent` updates this file after each migration by aggregating lessons from individual project files in this directory. Do not edit manually — changes will be overwritten.

---

## Recurring Issues

- **Issue:** Spring Boot 3.x `bootRun` / CI component test fails to start — app never binds to port
  **Affected Phases:** EAR→WAR conversion (Phase 0), Post-migration CI validation
  **Projects:** scp-eps-cheque-processing, scp-eps-other-payments
  **Root Cause:** Spring Boot 3.x changed Logback startup failure from warning to fatal `IllegalStateException`. MCA apps configure `logging.file.path=/opt/springboot/logs/${HOSTNAME}/` in `application.properties`. This path does not exist in CI or local bootRun environments. Spring Boot 3.x aborts startup; 2.x silently continued.
  **Resolution:** Add to `bootRun {}` block:
  ```groovy
  doFirst { new File("${rootDir}/build/logs").mkdirs() }
  jvmArgs "-Dlogging.file.path=${rootDir}/build/logs"
  jvmArgs "-Dserver.tomcat.accesslog.directory=${rootDir}/build/logs"
  ```

- **Issue:** Veracode SAST scan `cp: cannot stat '{project}-{version}.war': No such file or directory`
  **Affected Phases:** EAR→WAR conversion (Phase 0) — GitLab CI variable migration
  **Projects:** scp-eps-cheque-processing, scp-eps-other-payments
  **Root Cause:** `BUILD_LIB_PATH` variable still pointed to `war/build/libs/` after EAR→WAR conversion. GitLab CI artifact exposure used the wrong path, so the Veracode job received no WAR artifact.
  **Resolution:** In `.gitlab-ci-variables.yml`, replace all `war/build/` with `build/` — the `ear_to_war_conversion` skill Step 12 handles this. Verify after conversion: `grep -E 'war/build' .gitlab-ci-variables.yml` should return no matches.

- **Issue:** `bootRun` fails with `BeanDefinitionParsingException: Only one ScheduledAnnotationBeanPostProcessor may exist within the context`
  **Affected Phases:** Post-migration bootRun validation
  **Projects:** scp-eps-cheque-processing
  **Root Cause:** `<task:annotation-driven/>` in an XML bean config loaded via `@ImportResource` creates a `ScheduledAnnotationBeanPostProcessor`. Spring Boot 3.x (Spring Framework 6.x) auto-configuration creates another. Spring 6.x is now strict and throws a fatal exception on duplicates; Spring 5.x was lenient.
  **Resolution:** Remove `<task:annotation-driven/>` from all XML configs loaded via `@ImportResource`. Also clean up the now-unused `xmlns:task` namespace declaration and schema location. Spring Boot handles scheduling auto-configuration automatically.
  **Detection:** `grep -r "task:annotation-driven" src/main/resources/`

- **Issue:** `bootRun` fails with `JCEKS KeyStore initialization failed` / `NullPointerException` after Logback fix is applied
  **Affected Phases:** EAR→WAR conversion (Phase 0), Post-migration CI validation
  **Projects:** scp-eps-cheque-processing
  **Root Cause:** `placeholder.resolver.vault=true` in `application.properties` triggers `JceksSecretsToSpringEnvironmentPropertiesPostProcessor` (from `mca-jceks-spring-properties-processor`). The processor attempts to open a JCEKS keystore file whose path is null in CI/local environments. The NPE occurs at `FileInputStream.<init>` when the keystore path property is unset.
  **Resolution:** Add `jvmArgs "-Dplaceholder.resolver.vault=false"` to the `bootRun {}` block. JVM system properties override `application.properties`, so deployed servers (where the keystore is present) are unaffected.

- **Issue:** Stale `war/src/` keystore paths in `application-dev.properties` after EAR→WAR
  **Affected Phases:** EAR→WAR conversion (Phase 0)
  **Projects:** scp-eps-cheque-processing, scp-eps-other-payments
  **Root Cause:** `application-dev.properties` contained `core.rest-template.socket-factory.external-ssl.key-store-path=${rootDir}/war/src/main/resources/keystores/mqssl.jks`. After EAR→WAR flattening, keystores moved to `src/test/resources/keystores/`.
  **Resolution:** Fix paths in `application-dev.properties`: replace `${rootDir}/war/src/main/resources/keystores/` with `${rootDir}/src/test/resources/keystores/`. Note: `${rootDir}` is not a standard Spring property — it only resolves if a JVM `-DrootDir=...` arg is set. These properties are typically overridden by JVM args in `bootRun` (`-Djavax.net.ssl.trustStore=...`), so the unresolved placeholder is usually harmless.

---

## Proven Resolutions

- **Problem:** `bootRun` exits immediately or Spring Boot fails to start with `IllegalStateException: Logback configuration error detected`
  **Resolution:**
  1. Add `doFirst { new File("${rootDir}/build/logs").mkdirs() }` inside the `bootRun {}` block
  2. Add `jvmArgs "-Dlogging.file.path=${rootDir}/build/logs"` to `bootRun`
  3. Add `jvmArgs "-Dserver.tomcat.accesslog.directory=${rootDir}/build/logs"` to `bootRun`
  4. JVM system properties always override `application.properties` and profile files — no changes to properties files needed
  **Success Rate:** 1/1 projects (scp-eps-cheque-processing)

- **Problem:** `pathingJar.archivePath` causes Gradle build failure (`Could not get unknown property 'archivePath'`)
  **Resolution:** Replace `pathingJar.archivePath` with `pathingJar.archiveFile.get().asFile` in the `bootRun {}` block. `archivePath` was deprecated in Gradle 6.x and removed in Gradle 7+.
  **Success Rate:** 1/1 projects (scp-eps-cheque-processing)

- **Problem:** Application fails to start because `mainClass` references non-existent class (e.g., `.Application` when actual class is `.ChequeProcessingApplication`)
  **Resolution:** Search `src/main/java/` for `@SpringBootApplication` annotation to find the real class FQCN, then update `mainClass` in `bootRun {}` and in `bootWar {}` / `bootJar {}` if present.
  **Success Rate:** 1/1 projects (scp-eps-cheque-processing)

---

## Phase-Specific Patterns

### Phase 0: EAR→WAR Conversion

- **`BUILD_LIB_PATH` is the most critical CI variable.** If still `war/build/libs/`, every CI job that depends on the built artifact (Veracode, deploy, component tests) will fail. The `ear_to_war_conversion` skill Step 12 handles the fix, but always verify after conversion.

- **Spring Boot 3.x is incompatible with non-existent log directories at startup.** MCA profile properties files (`application.properties`, `application-dev.properties`, `application-{env}.properties`) commonly set `logging.file.path=/opt/springboot/logs/...` which only exists on deployed servers. Always add `bootRun` JVM arg overrides — see Step 13 of the `ear_to_war_conversion` skill.

- **`application-dev.properties` is the most likely file to contain stale `war/` paths.** After EAR→WAR, also scan all `src/main/resources/application-*.properties` for `war/src/` or `war/build/` references.

- **The `ftpupload.gradle` script still references `.ear` files after conversion.** These references are in non-default tasks (`ftp`, `scp`) so they don't break the standard build, but they should be updated to `.war` to prevent failures if those tasks are ever invoked.

### Phase 8: Push and MR

- **GitLab pre-receive hook TADS-CO-01403 requires valid JIRA reference in ALL commit messages.** Format must be `JIRA-1234:` (colon immediately after ID, no space). If commits were made with wrong JIRA IDs or format, use `git filter-branch --msg-filter` to rewrite message history before pushing.

---

## Anti-Patterns (Things That Failed)

- **Attempted:** Changing `logging.file.path` in `application.properties` to a local path
  **Why It Failed:** The value is profile-specific — changing the base file affects all environments. The deployed app expects `/opt/springboot/logs/...`
  **Better Alternative:** Override via `bootRun` JVM arg: `-Dlogging.file.path=${rootDir}/build/logs`. JVM system properties always override application properties, so the deployed behaviour is unchanged.

- **Attempted:** Relying on Spring profile not being activated in CI to avoid dev-profile log paths
  **Why It Failed:** `jvmArgs` inside the `bootRun {}` task definition in `build.gradle` ARE applied when CI runs `./gradlew bootrun`. CI not explicitly passing `-Dspring.profiles.active=dev` on the command line makes no difference — the task's own `jvmArgs` activate the profile anyway.
  **Better Alternative:** Add JVM arg overrides for log paths directly in `bootRun`, regardless of which profile is active.
