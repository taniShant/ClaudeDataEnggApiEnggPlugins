# Strategy Pattern: Pluggable Implementations for Cross-Cutting Concerns

## Executive Summary

The **Strategy Pattern** is used throughout MCA2 to enable pluggable, interchangeable implementations for critical infrastructure concerns. The primary example is **Mask\<T\>**, which provides interchangeable data masking/redaction strategies (StringMasker, JsonStringMasker, Redactor) that implement the same interface. This pattern enables applications to choose the most suitable masking strategy without changing application code.

**Pattern Definition (Gang of Four):**
> "Define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it."

**MCA2 Application:**
- **Strategy Interface:** `Mask<T>`
- **Concrete Strategies:** StringMasker, JsonStringMasker, Redactor
- **Context:** Sensitive data values (credit card numbers, emails, etc.)
- **Client:** Logging and response handling selects strategy at configuration time

---

## Strategy Pattern Structure

```
+-------------------------------------------+
| Mask<T> (Strategy Interface)              |
+-------------------------------------------+
| + mask(T value) : T                       |
| + supports(T value) : boolean             |
+-------------------------------------------+
          ^         ^         ^
          |         |         |
    +-----+---+ +---+-----+ ++------------+
    |         | |         | |              |
+---+---------+ +---------+-+--+ +--------+--------+
| StringMasker| |JsonString   | | Redactor         |
|             | |Masker       | |                  |
+-------------+ +-------------+ +------------------+
| + Pattern   | | + JSON path | | + Full redaction |
|   matching  | |   targeting | | + Configurable   |
| + Partial   | | + Nested    | |   replacement    |
|   masking   | |   field     | | + Audit-safe     |
| + Regex     | |   masking   | |   output         |
+-------------+ +-------------+ +------------------+
          |         |         |
    Application Configuration
    (@EnableMasking with property-driven
     strategy selection)
```

---

## Strategy Interface: Mask\<T\>

### Module Location

**Module:** `mca-masking`
**Location:** `mca-libraries/mca-masking/src/main/java/com/barclays/global/mca/masking/`

### Interface Definition

```java
public interface Mask<T> {

    /**
     * Apply masking/redaction to a value
     *
     * @param value The value to mask
     * @return The masked value
     */
    T mask(T value);
}
```

### Why This Interface?

1. **Single Responsibility:** Each strategy handles only one masking approach
2. **Open/Closed Principle:** Can add new masking strategies without modifying existing code
3. **Dependency Inversion:** Application depends on interface, not concrete implementations
4. **Testability:** Easy to mock for testing

---

## Concrete Strategy 1: StringMasker

**Module:** `mca-masking`

### Use Case

General-purpose string masking for:
- Credit card numbers
- Email addresses
- Phone numbers
- Any pattern-based sensitive data

### Implementation

```java
@Service
public class StringMasker implements Mask<String> {

    private final List<MaskPattern> patterns;

    public StringMasker(List<MaskPattern> patterns) {
        this.patterns = patterns;
    }

    @Override
    public String mask(String value) {
        if (value == null || value.isEmpty()) {
            return value;
        }

        String masked = value;
        for (MaskPattern pattern : patterns) {
            if (pattern.matches(masked)) {
                masked = pattern.apply(masked);
            }
        }

        return masked;
    }
}
```

### Configuration

```properties
# application.properties
masking.enabled=true
masking.patterns.credit-card=^([0-9]{4}).*([0-9]{4})$
masking.patterns.email=^[^@]+@(.+)$
masking.patterns.phone=^(\\d{3}).*?(\\d{4})$
```

### Masking Examples

```
Credit Card:   4111-1111-1111-1111  ->  4111-****-****-1111
Email:         user@example.com      ->  user@***
Phone:         555-123-4567          ->  555-***-4567
```

### Advantages
- Fast pattern-based masking
- Configurable via properties
- Works with any string value
- Regex-based, flexible

### Disadvantages
- Only works with flat strings (not structured data)
- Pattern order matters for overlapping matches

---

## Concrete Strategy 2: JsonStringMasker

**Module:** `mca-masking`

### Use Case

Structured JSON masking for:
- Request/response bodies in logs
- Nested sensitive fields in JSON payloads
- API response redaction

### Implementation

```java
@Service
public class JsonStringMasker implements Mask<String> {

    private final ObjectMapper objectMapper;
    private final Set<String> sensitiveFields;

    public JsonStringMasker(
        ObjectMapper objectMapper,
        Set<String> sensitiveFields
    ) {
        this.objectMapper = objectMapper;
        this.sensitiveFields = sensitiveFields;
    }

    @Override
    public String mask(String jsonValue) {
        if (jsonValue == null || jsonValue.isEmpty()) {
            return jsonValue;
        }

        try {
            JsonNode root = objectMapper.readTree(jsonValue);
            maskNode(root);
            return objectMapper.writeValueAsString(root);
        } catch (JsonProcessingException ex) {
            // Not valid JSON, fall back to string masking
            return jsonValue;
        }
    }

    private void maskNode(JsonNode node) {
        if (node.isObject()) {
            ObjectNode objectNode = (ObjectNode) node;
            objectNode.fieldNames().forEachRemaining(fieldName -> {
                if (sensitiveFields.contains(fieldName.toLowerCase())) {
                    objectNode.put(fieldName, "***REDACTED***");
                } else {
                    maskNode(objectNode.get(fieldName));
                }
            });
        } else if (node.isArray()) {
            for (JsonNode element : node) {
                maskNode(element);
            }
        }
    }
}
```

### Configuration

```properties
# application.properties
masking.json.sensitive-fields=password,creditCardNumber,ssn,accountNumber,cvv
```

### Masking Example

```json
// Before masking
{
  "customer": "John Doe",
  "creditCardNumber": "4111111111111111",
  "cvv": "123",
  "amount": 50.00
}

// After masking
{
  "customer": "John Doe",
  "creditCardNumber": "***REDACTED***",
  "cvv": "***REDACTED***",
  "amount": 50.00
}
```

### Advantages
- Handles nested JSON structures
- Field-name based targeting
- Preserves JSON structure in logs
- Configurable sensitive field list

### Disadvantages
- JSON parsing overhead
- Only works with JSON content

---

## Concrete Strategy 3: Redactor

**Module:** `mca-masking`

### Use Case

Full redaction for audit-safe output:
- Complete removal of sensitive values
- Compliance-driven redaction (PCI-DSS, GDPR)
- Irreversible data masking

### Implementation

```java
@Service
public class Redactor implements Mask<String> {

    private final String replacementValue;

    public Redactor(String replacementValue) {
        this.replacementValue = replacementValue;
    }

    @Override
    public String mask(String value) {
        if (value == null || value.isEmpty()) {
            return value;
        }
        return replacementValue;  // Full redaction
    }
}
```

### Configuration

```properties
# application.properties
masking.redactor.replacement=[REDACTED]
```

### Advantages
- Simplest implementation
- Guaranteed no data leakage
- Compliance-friendly
- No pattern matching overhead

### Disadvantages
- No partial masking (all or nothing)
- Less useful for debugging

---

## Strategy Selection in MCA2

### Configuration-Driven Selection

```java
@Configuration
@ConditionalOnProperty(name = "masking.enabled", havingValue = "true")
public class MaskingConfig {

    @Bean
    @ConditionalOnProperty(name = "masking.strategy", havingValue = "string")
    public Mask<String> stringMasker(MaskingProperties props) {
        return new StringMasker(props.getPatterns());
    }

    @Bean
    @ConditionalOnProperty(name = "masking.strategy", havingValue = "json")
    public Mask<String> jsonStringMasker(
        ObjectMapper objectMapper,
        MaskingProperties props
    ) {
        return new JsonStringMasker(objectMapper, props.getSensitiveFields());
    }

    @Bean
    @ConditionalOnProperty(name = "masking.strategy", havingValue = "redact")
    public Mask<String> redactor(MaskingProperties props) {
        return new Redactor(props.getReplacementValue());
    }

    @Bean
    @ConditionalOnMissingBean(Mask.class)
    public Mask<String> defaultMasker(MaskingProperties props) {
        // Default to StringMasker
        return new StringMasker(props.getPatterns());
    }
}
```

### MaskFactory Pattern

```java
public class MaskFactory {

    public static Mask<String> create(String type, MaskingProperties props) {
        return switch (type) {
            case "string" -> new StringMasker(props.getPatterns());
            case "json" -> new JsonStringMasker(
                new ObjectMapper(), props.getSensitiveFields()
            );
            case "redact" -> new Redactor(props.getReplacementValue());
            default -> new StringMasker(props.getPatterns());
        };
    }
}
```

---

## Other Strategy Pattern Examples in MCA2

### DdosPreventor Strategy

```java
// Strategy interface
public interface DdosPreventor {
    boolean isAllowed(HttpServletRequest request);
}

// Concrete strategies
public class DefaultAllowAllRequestDdosPreventor implements DdosPreventor {
    @Override
    public boolean isAllowed(HttpServletRequest request) {
        return true;  // Allow all
    }
}

public class ChannelPropositionBasedDdosPreventor implements DdosPreventor {
    @Override
    public boolean isAllowed(HttpServletRequest request) {
        // Rate limit by channel/proposition
        IOLSchema context = WebUtils.getIOLSchema();
        return rateLimiter.isAllowed(context.getChannel());
    }
}
```

### PropertyPlaceholderProcessor Strategy

```java
// Strategy interface
public interface PropertyPlaceholderProcessor {
    String process(String value);
}

// Concrete strategies
public class JCEKSPropertyProcessor implements PropertyPlaceholderProcessor {
    // Resolve from JCEKS keystore
}

public class VaultPropertyProcessor implements PropertyPlaceholderProcessor {
    // Resolve from HashiCorp Vault
}

public class StandardPropertyProcessor implements PropertyPlaceholderProcessor {
    // Standard Spring resolution
}
```

### OasProvider Strategy

The OAS validation module uses the Strategy pattern for loading and providing the OpenAPI specification to the validation engine.

```java
// Strategy interface
public interface OasProvider {
    // Provides the OpenAPI specification for request validation
}

// Concrete strategy: loads OAS from a Spring Resource (classpath, file, URL)
public class SimpleOasProvider implements OasProvider {
    // Loads and parses the OpenAPI spec from the configured resource path
    // Used when core.default.oas.enabled=true
}

// Concrete strategy: no-op provider when validation is disabled
public class EmptyOasProvider implements OasProvider {
    // Returns nothing; effectively disables OAS validation
    // Used when core.default.oas.enabled=false
}
```

**Selection mechanism:** The `core.default.oas.enabled` property drives which provider is instantiated via Spring auto-configuration:

```properties
# When true -> SimpleOasProvider is created, loading the spec from core.default.oas.path
core.default.oas.enabled=true
core.default.oas.path=classpath:oas/openapi.yaml

# When false -> EmptyOasProvider is created (no-op, no validation)
core.default.oas.enabled=false
```

**Key classes:**
- `OasProvider` (interface) -- in `mca-libraries/oas-validation`
- `SimpleOasProvider` -- loads OAS from a Spring Resource location
- `EmptyOasProvider` -- no-op implementation for disabled state
- `OASRequestValidation` -- the validation engine that consumes the provider

This follows the same pattern as `Mask<T>` and `DdosPreventor`: the application depends on the `OasProvider` interface, and the concrete implementation is selected through configuration properties at startup time.

---

## Benefits of Strategy Pattern in MCA2

| Benefit | How Achieved |
|---------|-------------|
| **Flexibility** | Choose masking strategy at configuration time |
| **Extensibility** | Add new strategies without modifying existing code |
| **Testability** | Easy to mock Mask\<T\> for testing |
| **Compliance** | Each strategy meets different regulatory requirements |
| **Maintainability** | Each strategy has isolated implementation |
| **Standards** | Interface defines clear contract |
| **Decoupling** | Application depends on interface, not implementation |

---

## Anti-Patterns: What NOT To Do

### Anti-Pattern 1: Hardcoded Implementation

```java
// BAD - Hardcoded to specific masking strategy
public class LoggingService {
    private StringMasker masker = new StringMasker();

    public void log(String message) {
        logger.info(masker.mask(message));  // Always uses StringMasker
    }
}

// Problem: Can't switch strategies, tightly coupled
```

### Correct Approach

```java
// GOOD - Depends on interface
public class LoggingService {
    private Mask<String> masker;  // Can be any implementation

    @Autowired
    public LoggingService(Mask<String> masker) {
        this.masker = masker;  // Injected at runtime
    }

    public void log(String message) {
        logger.info(masker.mask(message));  // Uses whatever strategy is configured
    }
}
```

### Anti-Pattern 2: Strategy Selection Logic in Application

```java
// BAD - Application decides strategy
public class Application {
    public Mask<String> createMasker() {
        if (environment.equals("production")) {
            return new JsonStringMasker();
        } else {
            return new StringMasker();
        }
    }
}

// Problem: Application shouldn't make infrastructure decisions
```

### Correct Approach

```java
// GOOD - Configuration decides strategy
@Configuration
@ConditionalOnProperty(name = "masking.strategy", havingValue = "json")
public class JsonMaskingConfig {
    @Bean
    public Mask<String> masker(...) {
        return new JsonStringMasker(...);
    }
}

// Enable via properties, not code
```

---

## Testing with Strategy Pattern

### Mock Strategy for Unit Tests

```java
@Service
public class NoOpMasker implements Mask<String> {
    @Override
    public String mask(String value) {
        return value;  // No masking for tests
    }
}

// Usage in tests
@SpringBootTest
public class LoggingServiceTest {

    @MockBean
    private Mask<String> masker;

    @Test
    public void testLogMasking() {
        String sensitiveData = "4111-1111-1111-1111";
        String maskedData = "4111-****-****-1111";

        when(masker.mask(sensitiveData)).thenReturn(maskedData);

        loggingService.log(sensitiveData);

        verify(masker).mask(sensitiveData);
    }
}
```

---

## Next Steps

1. **Choose your masking strategy:** StringMasker, JsonStringMasker, or Redactor
2. **Enable with @EnableMasking annotation**
3. **Configure properties:** masking.enabled=true, masking.strategy=string
4. **Test with NoOpMasker:** For unit tests
5. **Review other strategies:** DdosPreventor, PropertyPlaceholderProcessor

---

## Quick Reference: Strategy Pattern

| Strategy | Implementation | Best For |
|----------|---------------|----------|
| **Mask\<String\>** | StringMasker | Pattern-based partial masking |
| **Mask\<String\>** | JsonStringMasker | Structured JSON field masking |
| **Mask\<String\>** | Redactor | Full redaction, compliance |
| **DdosPreventor** | Various | Rate limiting strategies |
| **PropertyPlaceholderProcessor** | Various | Property resolution |
| **OasProvider** | SimpleOasProvider | Load OAS spec from resource |
| **OasProvider** | EmptyOasProvider | No-op when validation disabled |

**Strategy Pattern enables flexible, extensible infrastructure without modifying application code.**
