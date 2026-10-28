# barclays-buk-mca-jdk-upgrade-mca1-jdk-upgrade-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mca-jdk-upgrade-mca1-jdk-upgrade-v1` |
| Plugin name | `barclays-buk-mca-jdk-upgrade` |
| Component type | skill-user-only |
| Owner | Barclays AI |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-mca-jdk-upgrade@barclays-cio-buk |
| Native command | `/barclays-buk-mca-jdk-upgrade:mca1-jdk-upgrade` |
| Skill name | `mca1-jdk-upgrade` |

## Description

Run Java 8 to Java 21 JDK upgrade for MCA1 Spring Boot applications (com.barclays.eps). Analyzes project first, then selectively upgrades MCA1 BOM and dependencies to 6.2+/6.3+, upgrades any MCA2 cross-dependencies to 2.2+/2.3+, updates Spring Boot plugin to 3.3+/3.5+, migrates javax to jakarta, removes deprecated log4j/IBM MQ/OJDBC artifacts, updates Gradle wrapper to 8.5, and handles EAR-to-WAR conversion if needed. Use when user says "upgrade MCA1 to Java 21", "MCA1 JDK upgrade", "Java 21 migration for EPS app", or runs /mca1-jdk-upgrade.

## When to use

Use when upgrading an MCA1 Spring Boot application (com.barclays.eps package) from Java 8 to Java 21 — handles Spring Boot 3.3+/3.5+ upgrade, jakarta namespace migration, Gradle 8.5 wrapper update, MCA1 BOM upgrade to 6.2+/6.3+, deprecated dependency removal, and EAR-to-WAR conversion if present; this skill is NOT for MCA2 applications (use mca2-jdk-upgrade for that) and NOT for projects that have already completed the JDK 21 migration.

## Inputs

- Run from the project root of the MCA1 Spring Boot application (must contain `build.gradle` or `pom.xml` and `src/main/java` with `com.barclays.eps` package structure)
- Optional: `JIRA_ID` — used for logging and reporting purposes

## Preconditions

- Plugin `barclays-buk-mca-jdk-upgrade` installed (dependency: `barclays-buk-standards`)
- MCA1 Spring Boot project using `com.barclays.eps` groupId and `com.barclays.eps:mca-dependencies` BOM (version 5.x or 6.x)
- Gradle wrapper (`gradlew`/`gradlew.bat`) present and the project builds cleanly on Java 8 before migration begins
- Java 21 JDK available on the PATH (target JDK for post-migration build verification)

## Expected outputs

- Updated `build.gradle` (or `pom.xml`) with:
  - MCA1 BOM upgraded to `com.barclays.eps:mca-dependencies:6.2.+` (or `6.3.+` for Spring Boot 3.5)
  - Any MCA2 cross-dependencies upgraded to `com.barclays.global.mca:mca-dependencies:2.2.+` (or `2.3.+`)
  - Spring Boot plugin updated to `3.3.+` (or `3.5.+`) with `io.spring.dependency-management` added if missing
  - DevOps plugin `gradle-eps2-war-plugin` renamed to `gradle-eps-war-plugin` at `8.2.+`; deprecated DevOps plugins removed
  - Deprecated dependencies removed (log4j, legacy IBM MQ, `ojdbc14`, `is_messaging`, IS framework < 6.x)
  - `cacheChangingModulesFor 0, 'seconds'` and `cacheDynamicVersionsFor 0, 'seconds'` added to both `buildscript configurations.all` and main `configurations.all`
  - JUnit 4 migrated to JUnit 5 with `useJUnitPlatform()` and `--add-opens` JVM args if JUnit 4 tests detected
- `gradle/wrapper/gradle-wrapper.properties` updated to Gradle 8.5 distribution URL
- Java source files updated: `javax.*` Jakarta EE imports migrated to `jakarta.*`; `@Autowired` removed from `@Bean` methods (Spring Boot 3.5+ only); deprecated `new Date(String)` constructor replaced
- Property files updated: MQ SSL cipher suite, MQ connection factory class, Hibernate dialect corrected where found
- EAR-to-WAR conversion applied if project uses `gradle-eps2-war-plugin` (old EAR packaging) — converted to WAR with updated plugin ID and `eps-war` application
- Migration analysis report written to console summarising all found and changed items

## Exclusions

- Does NOT upgrade MCA2 applications — use `mca2-jdk-upgrade` for that
- Does NOT perform MCA1-to-MCA2 framework migration (replacing `EpsServiceAbstractController`, `EpsAbstractService`, etc.) — use `mca1-to-mca2-eps` for that
- Does NOT migrate frontend/UI code — use `mca1-migration` for JMVC/BDL frontend migration
- Does NOT change `javax.crypto`, `javax.net`, `javax.sql.DataSource`, `javax.security.auth`, `javax.naming`, `javax.management`, `javax.imageio`, `javax.swing`, `javax.xml.parsers`, `javax.xml.transform`, or `javax.xml.xpath` imports (these remain in Java SE)
- Does NOT fix checkstyle warnings — only dependency, config, and javax/jakarta changes are applied
- Does NOT create or manage JIRA tickets

## Verification

After migration, run `./gradlew clean build` and `./gradlew test` from the project root. Confirm `build.gradle` references `com.barclays.eps:mca-dependencies:6.2.+` (or `6.3.+`), contains no deprecated dependency patterns (`log4j-core`, `com.ibm.mq.allclient`, `ojdbc14`), and uses Gradle 8.5 in `gradle-wrapper.properties`. Confirm no Java source file contains the migrated `javax.servlet`, `javax.persistence`, `javax.validation`, `javax.jms`, or `javax.annotation` imports. A clean build with all tests passing confirms end-to-end completion.
