# JDK 21 to JDK 25 Migration Changes

> **Note**: Java 21 is LTS (Long-Term Support). Java 25 is a short-term release (non-LTS).
> This guide covers changes specific to Java 25 migration from Java 21.

## Overview

Most Java 21 code runs unchanged on Java 25. The changes listed here are enhancements and stabilized preview features available in Java 25.

---

## JDK 25 New Features (After Java 21)

### 1. String Templates (If Stabilized in J25)

If String Templates are stabilized in Java 25 (currently preview in later versions):

```java
// Template syntax for safer string interpolation
// This is optional - existing string.formatted() continues to work

// Old approach (Java 21)
String message = "User: " + username + " logged in at " + time;
// Or with formatted
String message = "User: %s logged in at %s".formatted(username, time);

// New approach (if available in J25)
String message = "User: \{username} logged in at \{time}";
```

**When to apply**: Only if String Templates are stabilized and used in your codebase.

---

### 2. Implicitly Declared Classes (If Stabilized in J25)

If this feature is stabilized, it enables simplified unnamed main classes:

```java
// Old approach (Java 21)
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}

// New approach (if available in J25) - for learning/scripting only
// This is NOT applicable to production APIs - kept for reference only
void main() {
    System.out.println("Hello, World!");
}
```

**When to apply**: NOT applicable to production Barclays APIs. This is primarily for learning/scripting.

---

### 3. Performance and Security Enhancements

Java 25 includes:
- **Garbage Collection Improvements**: Better performance for high-throughput applications
- **Security Fixes**: Patches for known vulnerabilities
- **API Enhancements**: New methods in existing classes
- **Deprecation Updates**: Some APIs may be deprecated (check release notes)

**No code changes required** for most cases unless using deprecated APIs.

---

### 4. API Additions

New utility methods that enhance existing classes:

```java
// Examples of potential Java 25 API additions (subject to release)
// These are typically backward compatible and optional

// Possible Collection enhancements
List<String> myList = List.of("a", "b", "c");
// Potential new methods for common operations

// Possible String enhancements
String text = "example";
// Potential new utility methods

// Possible Stream enhancements
List<String> result = myList.stream()
    // Potential new stream operations
    .toList();
```

**When to apply**: Use new APIs only when they provide significant benefit over existing approaches.

---

## Migration Path: Java 21 → Java 25

### 1. Update JDK Version

In `build.gradle`:
```groovy
java {
    sourceCompatibility = JavaVersion.VERSION_25
    targetCompatibility = JavaVersion.VERSION_25
}
```

In `gradle.properties`:
```properties
sourceCompatibility=25
targetCompatibility=25
```

### 2. Check for Deprecated APIs

```bash
# Run compilation with deprecation warnings
./gradlew compileJava -Xlint:deprecation
```

Review warnings and update deprecated APIs to modern equivalents.

### 3. Test Thoroughly

```bash
# Full test suite
./gradlew clean test integrationTest

# Optional: Check virtual thread compatibility (from Java 21)
# If using ExecutorService with virtual threads, verify continuation
```

### 4. Library Compatibility

Ensure all dependencies support Java 25:
- Check library documentation
- Update libraries to latest compatible versions
- Pay special attention to:
  - Database drivers
  - Serialization libraries (Jackson, Gson)
  - HTTP clients
  - Reactive libraries

---

## What STAYS THE SAME (Java 21 to 25)

These features from Java 21 remain unchanged and unchanged in Java 25:

### Virtual Threads
```java
// Continues to work in Java 25
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<String>> futures = urls.stream()
        .map(url -> executor.submit(() -> fetchUrl(url)))
        .toList();
}
```

### Records and Sealed Classes
```java
// Records continue to work
public record User(String name, int age) {}

// Sealed classes continue to work
public sealed class Shape permits Circle, Rectangle {}
```

### Pattern Matching
```java
// Pattern matching continues to work
String format(Object obj) {
    return switch (obj) {
        case Integer i -> "int: " + i;
        case String s -> "string: " + s;
        default -> "unknown";
    };
}
```

### Text Blocks
```java
// Text blocks continue to work
String json = """
    {
        "name": "John"
    }
    """;
```

### Sequenced Collections
```java
// Sequenced collections continue to work
List<String> list = new ArrayList<>(List.of("a", "b", "c"));
list.getFirst();  // "a"
list.getLast();   // "c"
```

---

## Checklist: Java 21 to Java 25 Upgrade

- [ ] Update JDK version in `build.gradle` and `gradle.properties` to 25
- [ ] Run compilation and review deprecation warnings: `./gradlew clean compileJava -Xlint:deprecation`
- [ ] Update deprecated APIs (if any)
- [ ] Run full test suite: `./gradlew test integrationTest`
- [ ] Update dependencies that don't support Java 25
- [ ] Verify Spring Boot 3.x compatibility with Java 25 (if applicable)
- [ ] Test virtual thread behavior (if used)
- [ ] Review release notes for breaking changes
- [ ] Performance testing (if applicable)

---

## Known Issues and Workarounds

Monitor Java 25 release notes for:
- Known issues with virtual threads
- Compatibility issues with popular libraries
- Deprecation notices for future removal

---

## Resources

- [OpenJDK Java 25 Feature List](https://openjdk.org/projects/jdk/25/)
- [Java 21 Features (baseline)](./java8-to-java21-features.md)
- [SDK3 Version Support](./barclays_internal_libraries_versions.md)
