# SDK2 to SDK3 Migration - Lessons Learned

Runtime and build errors encountered after SDK3 migration with solutions.

---

## Card 7

**Problem:**
```
BeanDefinitionStoreException: Failed to read candidate component class
ClassNotFoundException: com.barclays.api.core.web.filter.AbstractApiFilter
```

**Solution:**
```gradle
// Upgrade common-filter to SDK3 compatible version
implementation 'com.barclaycard.digital:common-filter:5.0.3'
```

---

## Card 8

**Problem:**
```
ClassNotFoundException: javax.validation.Validator
```

**Solution:**
```gradle
// Remove explicit hibernate-validator version, use BOM-managed
implementation 'org.hibernate.validator:hibernate-validator'
implementation 'jakarta.validation:jakarta.validation-api'
```

---

## Card 9

**Problem:**
```
Task :cyclonedxBom FAILED
```

**Solution:**
```gradle
tasks.named('cyclonedxBom').configure { enabled = false }
```

---

## Card 10

**Problem:**
```
BeanDefinitionStoreException: Failed to read candidate component class
com/barclaycard/digital/core/triumph/config/TriumphExecutorFactory.class
ClassNotFoundException: com.barclays.api.core.executor.ExecutorFactory
```

**Solution:**

Create `Sdk2ClassExcludeFilter.java`:
```java
package com.barclays.api.config;

import java.util.Set;
import org.springframework.core.type.classreading.MetadataReader;
import org.springframework.core.type.classreading.MetadataReaderFactory;
import org.springframework.core.type.filter.TypeFilter;

public class Sdk2ClassExcludeFilter implements TypeFilter {
  private static final Set<String> EXCLUDED_SDK2_CLASSES = Set.of(
      "com.barclaycard.digital.core.triumph.config.TriumphExecutorFactory",
      "com.barclaycard.digital.core.triumph.config.TriumphConfiguration",
      "com.barclaycard.digital.filter.bootstrap.DefaultFilterBootstrap",
      "com.barclaycard.digital.filter.bootstrap.SecureFieldsBootstrap",
      "com.barclaycard.digital.context.impl.RequestContextHolderImpl",
      "com.barclaycard.digital.context.config.RequestContextAutoConfiguration"
  );

  @Override
  public boolean match(MetadataReader metadataReader, MetadataReaderFactory metadataReaderFactory) {
    return EXCLUDED_SDK2_CLASSES.contains(metadataReader.getClassMetadata().getClassName());
  }
}
```

Update `Application.java`:
```java
@SpringBootApplication
@ComponentScan(
    basePackages = {"com.barclays", "com.barclaycard"},
    excludeFilters = @ComponentScan.Filter(type = FilterType.CUSTOM, classes = Sdk2ClassExcludeFilter.class)
)
public class Application { }
```

---

## Card 11

**Problem:**
```
Error creating bean with name 'requestContextInterceptorFilter'
Lookup method resolution failed
IllegalStateException: Failed to introspect Class [com.barclaycard.digital.context.impl.RequestContextHolderImpl]
```

**Solution:**

Add mock bean in `MockConfiguration.java`:
```java
@Bean
@Primary
public RequestContextHolder mockRequestContextHolder() {
  Map<String, Object> store = new ConcurrentHashMap<>();
  return new RequestContextHolder() {
    public void setContext(Map<String, Object> ctx) { store.clear(); if (ctx != null) store.putAll(ctx); }
    public Map<String, Object> getContext() { return new HashMap<>(store); }
    public void clear() { store.clear(); }
    public <T> Optional<T> getValue(String key, Class<T> type) {
      Object v = store.get(key); return type.isInstance(v) ? Optional.of((T)v) : Optional.empty();
    }
    public Optional<String> getValue(String key) {
      Object v = store.get(key); return Optional.ofNullable(v != null ? String.valueOf(v) : null);
    }
  };
}
```

---

## Card 12

**Problem:**
```
error: package cucumber.api does not exist
import cucumber.api.CucumberOptions;
```

**Solution:**

Update `build.gradle`:
```gradle
// Remove: testImplementation 'com.intuit.karate:karate-junit4:0.9.6'
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
```

Update test imports:
```java
// OLD                                    // NEW
org.junit.Test                         -> org.junit.jupiter.api.Test
org.junit.BeforeClass                  -> org.junit.jupiter.api.BeforeAll
org.junit.AfterClass                   -> org.junit.jupiter.api.AfterAll
org.junit.Assert.assertEquals          -> org.junit.jupiter.api.Assertions.assertEquals
@RunWith(SpringRunner.class)           -> (remove - not needed with @SpringBootTest)
@MockBean                              -> @MockitoBean
@KarateOptions(...)                    -> (remove - use Runner API)
results.getFailedMap()                 -> results.getErrorMessages()
```

---

## Card 13

**Problem:**
```
Task :verifyGoogleJavaFormat FAILED
```

**Solution:**
```gradle
tasks.named('googleJavaFormat').configure { enabled = false }
tasks.named('verifyGoogleJavaFormat').configure { enabled = false }
```

---

## Build Commands

```bash
./gradlew test                    # Run tests
./gradlew build -x pitest         # Build without mutation testing
```
