# barclays-buk-mca-jdk-upgrade-mca2-jdk-upgrade-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mca-jdk-upgrade-mca2-jdk-upgrade-v1` |
| Plugin name | `barclays-buk-mca-jdk-upgrade` |
| Component type | skill-user-only |
| Owner | Barclays AI |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-mca-jdk-upgrade@barclays-cio-buk |
| Native command | `/barclays-buk-mca-jdk-upgrade:mca2-jdk-upgrade` |
| Skill name | `mca2-jdk-upgrade` |

## Description

Run Java 8 to Java 21 JDK upgrade for MCA2 Spring Boot applications (com.barclays.global.mca). Analyzes project first, then selectively upgrades MCA2 BOM and dependencies to 2.2+/2.3+, removes any legacy MCA1 dependencies, updates Spring Boot plugin to 3.3+/3.5+, migrates javax to jakarta, removes deprecated log4j/IBM MQ/OJDBC artifacts, and updates Gradle wrapper to 8.5. No EAR-to-WAR step — MCA2 projects already use WAR/JAR packaging. Use when user says "upgrade MCA2 to Java 21", "MCA2 JDK upgrade", "Java 21 migration for MCA2 app", or runs /mca2-jdk-upgrade.

## When to use

Use when upgrading an MCA2 Spring Boot application (com.barclays.global.mca package) from Java 8 to Java 21 — handles Spring Boot 3.3+/3.5+ upgrade, jakarta namespace migration, Gradle 8.5 wrapper update, MCA2 BOM upgrade to 2.2+/2.3+, removal of any legacy MCA1 dependencies, and deprecated dependency removal; this skill is NOT for MCA1 applications (use mca1-jdk-upgrade for that) and NOT for projects that have already completed the JDK 21 migration.

## Inputs

- Run from the project root of the MCA2 Spring Boot application (must contain `build.gradle` or `pom.xml` and `src/main/java` with `com.barclays.global.mca` package structure)
- Optional: `JIRA_ID` — used for logging and reporting purposes

## Preconditions

- Plugin `barclays-buk-mca-jdk-upgrade` installed (dependency: `barclays-buk-standards`)
- MCA2 Spring Boot project using `com.barclays.global.mca` groupId and `com.barclays.global.mca:mca-dependencies` BOM (version 2.x)
- Gradle wrapper (`gradlew`/`gradlew.bat`) present and the project builds cleanly on Java 8 before migration begins
- Java 21 JDK available on the PATH (target JDK for post-migration build verification)

## Expected outputs

- Updated `build.gradle` (or `pom.xml`) with:
  - MCA2 BOM upgraded to `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+` for Spring Boot 3.5)
  - Any legacy MCA1 dependencies (`com.barclays.eps:*`, `com.barclays.eps:mca-dependencies` BOM) removed
  - Spring Boot plugin updated to `3.3.+` (or `3.5.+`) with `io.spring.dependency-management` added if missing
  - DevOps plugin `gradle-mca-jar-plugin` updated to `8.2.+`; deprecated DevOps plugins removed
  - Deprecated dependencies removed (log4j, legacy IBM MQ, `ojdbc14`, `is_messaging`, IS framework < 6.x)
  - `cacheChangingModulesFor 0, 'seconds'` and `cacheDynamicVersionsFor 0, 'seconds'` added to both `buildscript configurations.all` and main `configurations.all`
  - JUnit 4 migrated to JUnit 5 with `useJUnitPlatform()` and `--add-opens` JVM args if JUnit 4 tests detected
- `gradle/wrapper/gradle-wrapper.properties` updated to Gradle 8.5 distribution URL
- Java source files updated: `javax.*` Jakarta EE imports migrated to `jakarta.*`; `@Autowired` removed from `@Bean` methods (Spring Boot 3.5+ only); deprecated `new Date(String)` constructor replaced
- Property files updated: MQ SSL cipher suite, MQ connection factory class, Hibernate dialect corrected where found
- Migration analysis report written to console summarising all found and changed items

## Exclusions

- Does NOT upgrade MCA1 applications — use `mca1-jdk-upgrade` for that
- Does NOT perform an EAR-to-WAR conversion — MCA2 projects already use WAR or JAR packaging via `gradle-mca-jar-plugin`
- Does NOT perform MCA1-to-MCA2 framework migration (replacing `EpsServiceAbstractController`, etc.) — use `mca1-to-mca2-eps` for that
- Does NOT migrate frontend/UI code — use `mca1-migration` for JMVC/BDL frontend migration
- Does NOT change `javax.crypto`, `javax.net`, `javax.sql.DataSource`, `javax.security.auth`, `javax.naming`, `javax.management`, `javax.imageio`, `javax.swing`, `javax.xml.parsers`, `javax.xml.transform`, or `javax.xml.xpath` imports (these remain in Java SE)
- Does NOT fix checkstyle warnings — only dependency, config, and javax/jakarta changes are applied
- Does NOT create or manage JIRA tickets

## Verification

After migration, run `./gradlew clean build` and `./gradlew test` from the project root. Confirm `build.gradle` references `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+`), contains no `com.barclays.eps` dependency lines, contains no deprecated dependency patterns (`log4j-core`, `com.ibm.mq.allclient`, `ojdbc14`), and uses Gradle 8.5 in `gradle-wrapper.properties`. Confirm no Java source file contains the migrated `javax.servlet`, `javax.persistence`, `javax.validation`, `javax.jms`, or `javax.annotation` imports. A clean build with all tests passing confirms end-to-end completion.
