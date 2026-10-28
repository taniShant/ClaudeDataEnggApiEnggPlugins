# Joda Time to java.time Migration Specification

## Overview
Migrate from Joda Time library to Java's standard `java.time` API (available since Java 8).

## Rationale
- `java.time` is the standard date/time API since Java 8
- No external dependency required
- Better API design and immutability
- Native support in modern frameworks (Spring Boot, Jackson)

## Type Mappings

| Joda Time | java.time | Notes |
|-----------|-----------|-------|
| `org.joda.time.LocalDate` | `java.time.LocalDate` | Date without time |
| `org.joda.time.LocalTime` | `java.time.LocalTime` | Time without date |
| `org.joda.time.LocalDateTime` | `java.time.LocalDateTime` | Date and time, no timezone |
| `org.joda.time.DateTime` | `java.time.ZonedDateTime` or `java.time.Instant` | Date/time with timezone |
| `org.joda.time.Instant` | `java.time.Instant` | Point in time (UTC) |
| `org.joda.time.Duration` | `java.time.Duration` | Time-based amount |
| `org.joda.time.Period` | `java.time.Period` | Date-based amount |

## Common Method Conversions

### LocalDate
```java
// Joda Time → java.time
LocalDate.now() → LocalDate.now()
LocalDate.parse("2024-01-01") → LocalDate.parse("2024-01-01")
date.plusDays(1) → date.plusDays(1)
date.minusMonths(1) → date.minusMonths(1)
date.getYear() → date.getYear()
date.toDateTimeAtStartOfDay() → date.atStartOfDay()

// Converting from java.util.Date
LocalDate.fromDateFields(date) →
  date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate()
```

### DateTime / ZonedDateTime
```java
// Joda Time → java.time
DateTime.now() → ZonedDateTime.now()
new DateTime(millis) → Instant.ofEpochMilli(millis).atZone(ZoneId.systemDefault())
dateTime.toDate() → Date.from(zonedDateTime.toInstant())
dateTime.getMillis() → zonedDateTime.toInstant().toEpochMilli()
```

### Date Formatting
```java
// Joda Time
DateTimeFormatter.forPattern("yyyy-MM-dd").print(date)

// java.time
DateTimeFormatter.ofPattern("yyyy-MM-dd").format(date)
```

## Gradle/Maven Changes

### Remove Joda Time Dependencies

**Gradle:**
```gradle
// Remove these lines
implementation 'joda-time:joda-time:2.x.x'
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-joda:2.x.x'
```

**Maven:**
```xml
<!-- Remove these dependencies -->
<dependency>
    <groupId>joda-time</groupId>
    <artifactId>joda-time</artifactId>
    <version>2.x.x</version>
</dependency>
<dependency>
    <groupId>com.fasterxml.jackson.datatype</groupId>
    <artifactId>jackson-datatype-joda</artifactId>
    <version>2.x.x</version>
</dependency>
```

### Add java.time JSON Serialization (Jackson)

For Spring Boot projects, ensure `jackson-datatype-jsr310` is included:

**Gradle:**
```gradle
// Usually auto-included with spring-boot-starter-web or spring-boot-starter-json
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310'
```

**Maven:**
```xml
<!-- Usually auto-included with Spring Boot starters -->
<dependency>
    <groupId>com.fasterxml.jackson.datatype</groupId>
    <artifactId>jackson-datatype-jsr310</artifactId>
</dependency>
```

**Configuration:**
```yaml
spring:
  jackson:
    serialization:
      write-dates-as-timestamps: false
```

## Migration Steps

1. **Identify all Joda Time usage**
   - Search for `org.joda.time` imports
   - Check build files for Joda Time dependencies

2. **Update imports**
   - Replace `org.joda.time.*` with `java.time.*`

3. **Convert method calls**
   - Use mapping table above
   - Pay attention to timezone handling

4. **Update date conversions**
   - `java.util.Date` ↔ `java.time` conversions require explicit handling
   - Consider timezone implications

5. **Remove dependency**
   - Remove from build.gradle or pom.xml

6. **Test thoroughly**
   - Unit tests for date logic
   - Integration tests for serialization/deserialization
   - Verify timezone handling

## Common Pitfalls

1. **Timezone handling**: Joda Time `DateTime` has timezone, `LocalDate` doesn't. Choose appropriate `java.time` type.

2. **Date conversion**: Converting `java.util.Date` to `LocalDate` requires timezone:
   ```java
   date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate()
   ```

3. **Immutability**: Both are immutable, but verify no code assumes mutability.

4. **JSON serialization**: Ensure Jackson JSR310 module is registered (auto-configured in Spring Boot).

## Verification

- All tests pass
- No `org.joda.time` imports remain
- Joda Time dependency removed from build file
- Date/time values serialize/deserialize correctly in JSON
- No timezone-related bugs introduced
