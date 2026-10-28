---
title: Java Type Mapping Guide
description: Authoritative type mappings from OpenAPI 3.x specifications to Java types
---

# Java Type Mapping Guide

## Overview

Definitive mappings from OpenAPI 3.x specification types to Java types for Spring Boot 3 + Java 21 code generation.

---

## Primitive Types

| Spec Type | Format | Java Type | Annotation | Notes |
|-----------|--------|-----------|-----------|-------|
| string | - | String | - | Standard string |
| string | email | String | @Email | Validates email format |
| string | uuid | UUID | - | Import: java.util.UUID |
| string | uri | URI | - | Import: java.net.URI |
| string | url | URL | - | Import: java.net.URL |
| string | date | LocalDate | - | ISO 8601 date (YYYY-MM-DD) |
| string | date-time | LocalDateTime | - | ISO 8601 date-time |
| string | time | LocalTime | - | ISO 8601 time |
| string | password | String | - | Mark as @Sensitive in docs |
| string | byte | byte[] | - | Base64 encoded |
| string | binary | byte[] | - | Binary data |
| number | - | BigDecimal | - | Precise decimal numbers |
| number | float | Float | - | 32-bit floating point |
| number | double | Double | - | 64-bit floating point |
| integer | - | Integer | - | 32-bit integer |
| integer | int32 | Integer | - | 32-bit integer |
| integer | int64 | Long | - | 64-bit integer |
| boolean | - | Boolean | - | true/false |
| null | - | null | - | Use Optional<T> wrapper |

---

## String Constraints → Annotations

| Spec Constraint | Java Annotation | Example |
|-----------------|-----------------|---------|
| required: true | @NotNull | Required field |
| maxLength: N | @Size(max=N) | Max 100 chars |
| minLength: N | @Size(min=N) | Min 3 chars |
| pattern: regex | @Pattern(regexp="...") | Specific pattern |
| enum | Use Java enum | Status: ACTIVE/INACTIVE |
| format: email | @Email | Email validation |

---

## Numeric Constraints → Annotations

| Spec Constraint | Java Annotation | Example |
|-----------------|-----------------|---------|
| required: true | @NotNull | Required field |
| maximum: N | @Max(N) | Max value 100 |
| minimum: N | @Min(N) | Min value 1 |
| exclusiveMaximum | Custom validator | Value < 100 |
| exclusiveMinimum | Custom validator | Value > 0 |
| multipleOf: N | @Pattern | Value divisible by N |

---

## Collection Types

| Spec | Java | Notes |
|------|------|-------|
| array of string | List<String> | Collection of strings |
| array of integer | List<Integer> | Collection of integers |
| array of object | List<ModelName> | Collection of models |
| array of enum | List<EnumName> | Collection of enum values |
| array with minItems | @Size(min=...) | Minimum array size |
| array with maxItems | @Size(max=...) | Maximum array size |

**Java Imports**:
```java
import java.util.List;
import java.util.Set;
import java.util.Map;
import java.util.Optional;
```

---

## Complex Types

### Objects (Models)

All DTO/model classes MUST be Java Records. Do NOT use Lombok (`@Data`, `@Builder`, etc.) on DTOs.

```yaml
# OpenAPI
User:
  type: object
  properties:
    id: integer
    name: string
    email: string
```

```java
// Java — Record (replaces @Data/@Builder/@NoArgsConstructor/@AllArgsConstructor)
public record User(
    Integer id,
    String name,
    String email
) {}
```

**Accessor syntax:** `user.id()`, `user.name()`, `user.email()` — no `get` prefix.

### Enums

```yaml
# OpenAPI
Status:
  type: string
  enum: [active, inactive, pending]
```

```java
// Java
public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}
```

Use in record:
```java
public record Order(
    String orderId,
    Status status
) {}
```

### Nested Objects

Records can nest other records directly:

**Option 1**: Inline nested records
```java
public record User(
    String name,
    Address address   // nested record
) {}

public record Address(
    String street,
    String city
) {}
```

**Option 2**: Extract to separate top-level records (recommended for reusability)

```yaml
# Spec
User:
  type: object
  properties:
    address:
      $ref: '#/components/schemas/Address'

Address:
  type: object
  properties:
    street: string
    city: string
```

```java
// Java — separate record definitions
public record User(
    Address address
) {}

public record Address(
    String street,
    String city
) {}
```

---

## Nullable Fields

**Specification**:
```yaml
User:
  type: object
  properties:
    name:
      type: string
      nullable: true  # OpenAPI 3.0
    email:
      type: string
      nullable: false
```

**Java Mapping** (Records — no jakarta.validation):

```java
import org.springframework.lang.Nullable;

// Nullable component annotated with @Nullable (spring-context, NOT jakarta.validation)
public record User(
    String email,                   // required — not nullable
    @Nullable String name           // nullable: true in spec
) {}
```

Or using Optional for nullable components:
```java
public record User(
    String email,
    Optional<String> name           // wraps a nullable value
) {}
```

**Rule**: If spec field has `nullable: true` or is not in the `required` array:
- Annotate the record component with `@Nullable` (spring-context)
- Or use `Optional<T>`
- Do NOT use `@NotNull` — jakarta.validation is forbidden in DTOs

---

## Date/Time Types

### LocalDate (YYYY-MM-DD)
```yaml
dateOfBirth:
  type: string
  format: date
```

```java
public record User(LocalDate dateOfBirth) {}
```

**Import**: `import java.time.LocalDate;`

### LocalDateTime (ISO 8601)
```yaml
createdAt:
  type: string
  format: date-time
```

```java
public record UserAudit(LocalDateTime createdAt) {}
```

**Import**: `import java.time.LocalDateTime;`

### LocalTime (HH:MM:SS)
```yaml
startTime:
  type: string
  format: time
```

```java
public record EventRequest(LocalTime startTime) {}
```

**Import**: `import java.time.LocalTime;`

### ZonedDateTime (with timezone)
```yaml
timestamp:
  type: string
  format: date-time
```

```java
public record AuditEvent(ZonedDateTime timestamp) {}
```

**Import**: `import java.time.ZonedDateTime;`

---

## UUID Type

```yaml
userId:
  type: string
  format: uuid
```

```java
public record UserRequest(UUID userId) {}
// accessor: request.userId()
```

**Import**: `import java.util.UUID;`

**Note**: UUID is often used for IDs, better than String or Integer

---

## Numeric Precision

### For Financial Data → BigDecimal

```yaml
price:
  type: number
  format: decimal
```

```java
import java.math.BigDecimal;

public record ProductResponse(BigDecimal price) {}
```

### For Regular Numbers → Double

```yaml
rating:
  type: number
  format: double
```

```java
public record ReviewResponse(Double rating) {}
```

**Rule**: Use `BigDecimal` for money/financial calculations, `Double` for measurements/scores

---

## Special Handling

### Polymorphism (oneOf, anyOf)

**Exception to the record rule:** `oneOf`/`anyOf` schemas require inheritance, which Java Records do not support (records are implicitly `final` and cannot extend other classes). Use interfaces + records for this case:

```yaml
Pet:
  oneOf:
    - $ref: '#/components/schemas/Dog'
    - $ref: '#/components/schemas/Cat'
```

```java
// Sealed interface (Java 21) — type-safe discriminated union
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "petType")
@JsonSubTypes({
    @JsonSubTypes.Type(value = Dog.class, name = "dog"),
    @JsonSubTypes.Type(value = Cat.class, name = "cat")
})
public sealed interface Pet permits Dog, Cat {}

// Each variant is a record implementing the sealed interface
public record Dog(String name, String breed) implements Pet {}
public record Cat(String name, String color) implements Pet {}
```

This is fully supported by Jackson 2.14+ and Java 21 sealed interfaces. Use this pattern instead of abstract classes wherever the spec uses `oneOf`/`anyOf`.

### Maps/Dictionaries

```yaml
metadata:
  type: object
  additionalProperties:
    type: string
```

```java
import java.util.Map;

public record DocumentRequest(
    Map<String, String> metadata
) {}
```

---

## JPA Entity Mapping

### Basic Column Mapping

JPA entities are an **exception to the record rule** — JPA requires mutable objects with a no-arg constructor. Use Lombok `@Data` for entities only.

```java
@Entity
@Table(name = "users")
@Data
public class UserEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    
    @Column(nullable = false, unique = true, length = 100)
    private String email;
    
    @Column(name = "full_name", length = 200)
    private String name;
    
    @Column(columnDefinition = "DECIMAL(10,2)")
    private BigDecimal balance;
}
```

### Temporal Columns

```java
@Entity
public class UserEntity {
    @Id
    private Integer id;
    
    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;
}
```

### Enumerated Columns

```java
@Entity
public class OrderEntity {
    @Enumerated(EnumType.STRING)  // Store enum as string
    @Column(length = 20)
    private OrderStatus status;
}

public enum OrderStatus {
    PENDING,
    CONFIRMED,
    SHIPPED,
    DELIVERED,
    CANCELLED
}
```

### Relationships (One-to-Many, Many-to-One)

```java
// Parent
@Entity
public class UserEntity {
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL)
    private List<OrderEntity> orders = new ArrayList<>();
}

// Child
@Entity
public class OrderEntity {
    @ManyToOne
    @JoinColumn(name = "user_id", nullable = false)
    private UserEntity user;
}
```

---

## Validation Annotations Summary

```java
// String validations
@NotNull
@NotBlank
@NotEmpty
@Size(min=1, max=100)
@Pattern(regexp="...")
@Email

// Numeric validations
@Min(0)
@Max(100)
@Positive
@PositiveOrZero
@Negative
@NegativeOrZero

// Collection validations
@Size(min=1, max=10)  // For lists

// Custom
@Valid  // Validate nested objects
```

---

## Common Mappings Cheat Sheet

```java
// String types
String email;           // @Email
String phone;           // @Pattern(regexp="...")
String password;        // @NotBlank, @Size(min=8)
String status;          // Use enum instead
UUID userId;            // Format: uuid
String dateStr;         // Use LocalDate instead

// Numeric types
Integer count;          // @Min(0), @Max(...)
Long id;                // Long, not Integer for IDs
BigDecimal price;       // For money
Double rating;          // For scores/measurements

// Temporal types
LocalDate birthDate;    // YYYY-MM-DD
LocalDateTime created;  // ISO 8601
ZonedDateTime schedule; // With timezone

// Collections
List<String> tags;      // Multiple values
List<User> users;       // Multiple objects
Map<String, String> props;  // Key-value pairs
Set<Integer> ids;       // Unique values

// Optional
Optional<String> nickname;  // Can be null
@Nullable String description;  // Can be null
```

---

## Type Mapping Checklist

Before generating code:

- [ ] All request/response DTOs are Java Records (`public record Foo(Type field, ...) {}`) — NOT Lombok POJOs
- [ ] Lombok (`@Data`, `@Builder`, etc.) used ONLY on JPA entities (`model/entity/`), never on DTO records
- [ ] All string types mapped (String, UUID, LocalDate, etc.)
- [ ] All numeric types mapped (Integer, Long, BigDecimal, etc.)
- [ ] All formats recognised (email, uuid, date, date-time, etc.)
- [ ] Nullable fields annotated with `@Nullable` (spring-context) or wrapped in `Optional<T>` — NOT `@NotNull` (forbidden in DTOs)
- [ ] Collections typed correctly (List<T>, not raw List)
- [ ] Enums generated for enum values
- [ ] Nested objects are also records (or sealed-interface + record for oneOf/anyOf)
- [ ] Date/time fields use LocalDate/LocalDateTime, not String
- [ ] No jakarta.validation annotations (`@NotNull`, `@Valid`, etc.) on record components
- [ ] JPA entities have @Id and @Column mappings
- [ ] No Object types (all specific types)
- [ ] Record component accessors used (`record.fieldName()`) — NOT getter-style (`record.getFieldName()`)

---

**Version**: 1.0.0  
**Authority**: Organization type mapping standard  
**Last Updated**: 2026-06-13
