# barclays-buk-mca-jdk-upgrade

Java 8 to Java 21 / Spring Boot 2.7 to 3.5.x upgrade toolkit for MCA Spring Boot applications.

## Usage

```
/mca2-jdk-upgrade [project_path]   # For MCA2 applications (com.barclays.global.mca groupId)
/mca1-jdk-upgrade [project_path]   # For MCA1 applications (com.barclays.eps groupId)
```

## What it does

Automates the JDK upgrade workflow using OpenRewrite for automated migration, then applies targeted fixes across build configuration, namespace migration, test frameworks, and coverage enforcement.

**Phased validation:** each phase must pass `./gradlew clean build` before proceeding.

| Phase | Action |
|---|---|
| 0 | EAR-to-WAR conversion (MCA1 only) |
| 1 | OpenRewrite automated migration |
| 2 | Gradle build fixes |
| 2.5 | Spring conventions (optional) |
| 3 | Test framework migration (JUnit 4 → 5) |
| 4 | Push & PR |

## Standards

Loads `barclays-buk-standards:security`, `barclays-buk-standards:testing`, and `barclays-buk-standards:governance`.

## Author

Barclays AI (barclaysai@barclays.com)
