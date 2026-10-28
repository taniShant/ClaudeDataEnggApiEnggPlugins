# Test Migration: JUnit 4 → JUnit 5, Mockito 5

## JUnit 4 → JUnit 5 Annotation Mapping

| JUnit 4 | JUnit 5 |
|---|---|
| `org.junit.Test` | `org.junit.jupiter.api.Test` |
| `org.junit.Before` | `org.junit.jupiter.api.BeforeEach` |
| `org.junit.After` | `org.junit.jupiter.api.AfterEach` |
| `org.junit.BeforeClass` | `org.junit.jupiter.api.BeforeAll` |
| `org.junit.AfterClass` | `org.junit.jupiter.api.AfterAll` |
| `org.junit.Ignore` | `org.junit.jupiter.api.Disabled` |
| `@RunWith(MockitoJUnitRunner.class)` | `@ExtendWith(MockitoExtension.class)` |
| `@RunWith(SpringRunner.class)` | `@ExtendWith(SpringExtension.class)` |
| `@Rule` | `@ExtendWith` or `@RegisterExtension` |
| `@Test(expected = Ex.class)` | `assertThrows(Ex.class, () -> { })` |

## Assertion Changes

| JUnit 4 | JUnit 5 | Key Change |
|---|---|---|
| `Assert.assertEquals(msg, expected, actual)` | `Assertions.assertEquals(expected, actual, msg)` | **Message moves to LAST** |
| `Assert.assertTrue(msg, condition)` | `Assertions.assertTrue(condition, msg)` | **Message moves to LAST** |

## Mockito 5 Requirements

1. Add dependency: `org.mockito:mockito-junit-jupiter:5.14.2`
2. Add extension: `@ExtendWith(MockitoExtension.class)` on all test classes using `@Mock`
3. Strict stubbing is default — remove unused stubs or use `lenient().when(...)`

## Spring Boot 3.4+ Test Changes

| Old | New |
|---|---|
| `@MockBean` | `@MockitoBean` |
| `@SpyBean` | `@MockitoSpyBean` |

Import: `org.springframework.test.context.bean.override.mockito.*`

## WireMock 3.x

GroupId change:
- Old: `com.github.tomakehurst:wiremock-jre8:2.x`
- New: `org.wiremock:wiremock-standalone:3.9.2`

## Required Gradle Test Config

```groovy
// Required for JUnit 5 test discovery
tasks.withType(Test).configureEach {
    useJUnitPlatform()

    // Required for Mockito/Spring reflection on Java 21
    jvmArgs += [
        '--add-opens', 'java.base/java.lang=ALL-UNNAMED',
        '--add-opens', 'java.base/java.lang.reflect=ALL-UNNAMED',
        '--add-opens', 'java.base/java.util=ALL-UNNAMED'
    ]
}
```

## Test Dependencies

```groovy
testImplementation 'org.junit.jupiter:junit-jupiter:5.11.3'
testImplementation 'org.mockito:mockito-core:5.14.2'
testImplementation 'org.mockito:mockito-junit-jupiter:5.14.2'
```
