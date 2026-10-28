---
name: java8-to-java21-features
description: Reference guide for Java language features from JDK 8 to JDK 21 (standard features only, no previews). Use when modernizing Java code, migrating between JDK versions, or applying modern Java idioms like records, pattern matching, sealed classes, and virtual threads.
owner: Barclays AI (barclaysai@barclays.com)
version: 1.0.0
license: Proprietary. For Barclays internal use only.
user-invocable: false
source: barclays-claude-code-plugins/plugins/sdk3-migration/skills/java8_to_java21_features/SKILL.md
owner: Barclays AI (barclaysai@barclays.com)
review-trigger: When SDK3 BOM versions change or new migration patterns are identified
status: Full
---

# Java 8 to Java 21 Features Guide

A comprehensive reference for standard Java language features introduced from JDK 8 through JDK 21. This guide excludes preview features and focuses only on finalized, production-ready capabilities.
## Quick Start

Reference for Java 21 language features used in SDK3 migration.

```java
// Records (Java 16+): replaces simple POJOs
record ApiResponse(String status, String body) {}

// Text blocks (Java 15+): multi-line strings
String json = """
    {"status": "ok"}
    """;
```


## JDK 8 Features (2014) - LTS

### Lambda Expressions

Functional programming with concise syntax for anonymous functions.

```java
// Before: Anonymous inner class
Runnable r = new Runnable() {
    @Override
    public void run() {
        System.out.println("Hello");
    }
};

// After: Lambda expression
Runnable r = () -> System.out.println("Hello");

// With parameters
Comparator<String> comp = (a, b) -> a.compareToIgnoreCase(b);

// Multi-line lambda
Function<String, Integer> parser = s -> {
    if (s == null || s.isBlank()) {
        return 0;
    }
    return Integer.parseInt(s);
};
```

### Method References

Shorthand for lambdas that call existing methods.

```java
// Static method reference
Function<String, Integer> parser = Integer::parseInt;

// Instance method on a particular object
String prefix = "Mr. ";
Function<String, String> addPrefix = prefix::concat;

// Instance method on an arbitrary object of a type
Function<String, String> toUpper = String::toUpperCase;

// Constructor reference
Supplier<ArrayList<String>> listFactory = ArrayList::new;
Function<Integer, String[]> arrayFactory = String[]::new;
```

### Stream API

Declarative data processing with pipelines.

```java
List<String> names = List.of("Alice", "Bob", "Charlie", "David");

// Filter, map, collect
List<String> result = names.stream()
    .filter(name -> name.length() > 3)
    .map(String::toUpperCase)
    .sorted()
    .collect(Collectors.toList());

// Reduce
int totalLength = names.stream()
    .mapToInt(String::length)
    .sum();

// Grouping
Map<Integer, List<String>> byLength = names.stream()
    .collect(Collectors.groupingBy(String::length));

// Parallel processing
long count = names.parallelStream()
    .filter(name -> name.startsWith("A"))
    .count();

// FlatMap for nested structures
List<List<Integer>> nested = List.of(List.of(1, 2), List.of(3, 4));
List<Integer> flat = nested.stream()
    .flatMap(List::stream)
    .collect(Collectors.toList());
```

### Optional

Container for nullable values to avoid NullPointerException.

```java
// Creating Optional
Optional<String> present = Optional.of("value");
Optional<String> nullable = Optional.ofNullable(maybeNull);
Optional<String> empty = Optional.empty();

// Consuming values
optional.ifPresent(System.out::println);
String value = optional.orElse("default");
String computed = optional.orElseGet(() -> computeDefault());
String required = optional.orElseThrow(() -> new IllegalStateException("Missing"));

// Transforming
Optional<Integer> length = optional.map(String::length);
Optional<String> filtered = optional.filter(s -> s.length() > 3);

// Chaining
Optional<String> result = optional
    .map(String::trim)
    .filter(s -> !s.isEmpty())
    .map(String::toUpperCase);
```

### Default and Static Interface Methods

```java
public interface Validator<T> {
    boolean validate(T value);

    // Default method with implementation
    default boolean validateAll(Collection<T> values) {
        return values.stream().allMatch(this::validate);
    }

    // Static factory method
    static <T> Validator<T> notNull() {
        return value -> value != null;
    }

    // Combine validators
    default Validator<T> and(Validator<T> other) {
        return value -> this.validate(value) && other.validate(value);
    }
}
```

### New Date/Time API (java.time)

```java
// Current date/time
LocalDate today = LocalDate.now();
LocalTime now = LocalTime.now();
LocalDateTime dateTime = LocalDateTime.now();
Instant instant = Instant.now();

// Creating specific values
LocalDate date = LocalDate.of(2024, Month.MARCH, 15);
LocalTime time = LocalTime.of(14, 30, 0);
LocalDateTime dt = LocalDateTime.of(date, time);

// Parsing and formatting
LocalDate parsed = LocalDate.parse("2024-03-15");
DateTimeFormatter formatter = DateTimeFormatter.ofPattern("dd/MM/yyyy");
String formatted = date.format(formatter);

// Arithmetic
LocalDate nextWeek = today.plusWeeks(1);
LocalDate lastMonth = today.minusMonths(1);
Period period = Period.between(date1, date2);
Duration duration = Duration.between(time1, time2);

// Time zones
ZonedDateTime zoned = ZonedDateTime.now(ZoneId.of("Europe/London"));
ZonedDateTime converted = zoned.withZoneSameInstant(ZoneId.of("America/New_York"));

// Converting from legacy Date
Date legacyDate = new Date();
Instant fromLegacy = legacyDate.toInstant();
LocalDateTime fromDate = LocalDateTime.ofInstant(fromLegacy, ZoneId.systemDefault());
```

---

## JDK 9 Features (2017)

### Module System (Project Jigsaw)

```java
// module-info.java
module com.example.myapp {
    requires java.sql;
    requires transitive com.example.utils;

    exports com.example.myapp.api;
    exports com.example.myapp.spi to com.example.plugin;

    opens com.example.myapp.internal to com.fasterxml.jackson.databind;

    uses com.example.myapp.spi.Plugin;
    provides com.example.myapp.spi.Plugin with com.example.myapp.DefaultPlugin;
}
```

### Collection Factory Methods

```java
// Immutable collections (throw UnsupportedOperationException on modification)
List<String> list = List.of("a", "b", "c");
Set<Integer> set = Set.of(1, 2, 3);
Map<String, Integer> map = Map.of("one", 1, "two", 2);

// For larger maps
Map<String, Integer> largeMap = Map.ofEntries(
    Map.entry("one", 1),
    Map.entry("two", 2),
    Map.entry("three", 3),
    Map.entry("four", 4)
);

// Copying collections (creates immutable copy)
List<String> copy = List.copyOf(mutableList);
```

### Stream Enhancements

```java
// takeWhile - take elements while predicate is true
Stream.of(1, 2, 3, 4, 5, 4, 3)
    .takeWhile(n -> n < 4)
    .toList(); // [1, 2, 3]

// dropWhile - skip elements while predicate is true
Stream.of(1, 2, 3, 4, 5, 4, 3)
    .dropWhile(n -> n < 4)
    .toList(); // [4, 5, 4, 3]

// ofNullable - create 0 or 1 element stream
Stream.ofNullable(nullableValue)
    .forEach(System.out::println);

// iterate with predicate (finite stream)
Stream.iterate(1, n -> n < 100, n -> n * 2)
    .toList(); // [1, 2, 4, 8, 16, 32, 64]
```

### Optional Enhancements

```java
// ifPresentOrElse
optional.ifPresentOrElse(
    value -> System.out.println("Found: " + value),
    () -> System.out.println("Not found")
);

// or - lazy alternative Optional
Optional<String> result = optional.or(() -> computeAlternative());

// stream - convert to 0 or 1 element stream
List<String> values = optionals.stream()
    .flatMap(Optional::stream)
    .toList();
```

### Private Interface Methods

```java
public interface DataProcessor {
    void process(String data);

    default void processAll(List<String> items) {
        items.forEach(this::processItem);
    }

    default void processBatch(String... items) {
        Arrays.stream(items).forEach(this::processItem);
    }

    // Private method to share logic between default methods
    private void processItem(String item) {
        validate(item);
        process(item);
    }

    private void validate(String item) {
        if (item == null || item.isBlank()) {
            throw new IllegalArgumentException("Invalid item");
        }
    }
}
```

### Try-with-Resources Enhancement

```java
// JDK 9: Can use effectively final variables
BufferedReader reader = new BufferedReader(new FileReader(file));
try (reader) {  // No need to declare new variable
    return reader.readLine();
}

// Multiple resources
FileInputStream fis = new FileInputStream(input);
FileOutputStream fos = new FileOutputStream(output);
try (fis; fos) {
    fis.transferTo(fos);
}
```

---

## JDK 10 Features (2018)

### Local Variable Type Inference (var)

```java
// Basic usage - type inferred from right side
var list = new ArrayList<String>();
var map = new HashMap<String, List<Integer>>();
var stream = list.stream();

// In loops
for (var entry : map.entrySet()) {
    var key = entry.getKey();
    var value = entry.getValue();
}

// With try-with-resources
try (var reader = new BufferedReader(new FileReader(file))) {
    var line = reader.readLine();
}

// Lambda parameters (JDK 11)
BiFunction<String, String, String> concat = (var a, var b) -> a + b;

// Where NOT to use var:
// - Method parameters: void process(var data) // INVALID
// - Return types: var getData() // INVALID
// - Fields: private var name; // INVALID
// - When null: var x = null; // INVALID
// - When it reduces readability
```

---

## JDK 11 Features (2018) - LTS

### HTTP Client API

```java
// Create client (reusable, thread-safe)
HttpClient client = HttpClient.newBuilder()
    .version(HttpClient.Version.HTTP_2)
    .connectTimeout(Duration.ofSeconds(10))
    .followRedirects(HttpClient.Redirect.NORMAL)
    .build();

// Synchronous GET request
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/data"))
    .header("Accept", "application/json")
    .GET()
    .build();

HttpResponse<String> response = client.send(request,
    HttpResponse.BodyHandlers.ofString());
int status = response.statusCode();
String body = response.body();

// Asynchronous request
CompletableFuture<HttpResponse<String>> future = client.sendAsync(request,
    HttpResponse.BodyHandlers.ofString());

future.thenApply(HttpResponse::body)
    .thenAccept(System.out::println)
    .join();

// POST with JSON body
HttpRequest postRequest = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/users"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
    .build();

// Download to file
HttpResponse<Path> fileResponse = client.send(request,
    HttpResponse.BodyHandlers.ofFile(Path.of("output.txt")));
```

### String Methods

```java
String text = "  Hello World  ";

// isBlank - true if empty or only whitespace
"   ".isBlank();     // true
"".isBlank();        // true
"  a  ".isBlank();   // false

// strip - Unicode-aware trim
text.strip();        // "Hello World"
text.stripLeading(); // "Hello World  "
text.stripTrailing();// "  Hello World"

// lines - stream of lines
"line1\nline2\nline3".lines()
    .map(String::trim)
    .toList();

// repeat
"ab".repeat(3);      // "ababab"

// JDK 12+: indent and transform
"hello".indent(4);   // "    hello\n"
"hello".transform(s -> s.toUpperCase()); // "HELLO"
```

### Files Convenience Methods

```java
// Read entire file as string
String content = Files.readString(Path.of("file.txt"));
String contentWithCharset = Files.readString(path, StandardCharsets.UTF_8);

// Write string to file
Files.writeString(Path.of("output.txt"), "content");
Files.writeString(path, "content", StandardCharsets.UTF_8,
    StandardOpenOption.CREATE, StandardOpenOption.APPEND);

// With isMismatch (JDK 12)
long mismatch = Files.mismatch(path1, path2); // -1 if identical
```

### Collection toArray Enhancement

```java
List<String> list = List.of("a", "b", "c");

// New way - cleaner syntax
String[] array = list.toArray(String[]::new);

// Old way
String[] oldArray = list.toArray(new String[0]);
```

---

## JDK 14 Features (2020)

### Helpful NullPointerExceptions

```java
// Given this code that throws NPE:
String city = employee.getAddress().getCity().toUpperCase();

// Before JDK 14:
// Exception: NullPointerException

// After JDK 14:
// Exception: NullPointerException: Cannot invoke "Address.getCity()"
//            because the return value of "Employee.getAddress()" is null
```

### Switch Expressions (Standard)

```java
// Expression form - returns a value
String result = switch (day) {
    case MONDAY, FRIDAY, SUNDAY -> "relaxed";
    case TUESDAY -> "productive";
    case THURSDAY, SATURDAY -> "busy";
    case WEDNESDAY -> "moderate";
};

// With yield for complex logic
int numLetters = switch (day) {
    case MONDAY, FRIDAY, SUNDAY -> 6;
    case TUESDAY -> {
        System.out.println("Tuesday!");
        yield 7;
    }
    case THURSDAY, SATURDAY -> 8;
    case WEDNESDAY -> 9;
};

// Exhaustiveness - compiler ensures all cases covered for enums/sealed types
// No default needed if all enum values handled
```

---

## JDK 15 Features (2021)

### Text Blocks (Standard)

```java
// Multi-line strings with proper indentation
String json = """
    {
        "name": "John",
        "age": 30,
        "city": "London"
    }
    """;

// SQL query
String sql = """
    SELECT id, name, email
    FROM users
    WHERE status = 'ACTIVE'
    ORDER BY name
    """;

// HTML
String html = """
    <html>
        <body>
            <h1>Hello, %s!</h1>
        </body>
    </html>
    """.formatted(name);

// Escaping
String escaped = """
    Line with \""" triple quotes
    Line with trailing space\s
    Line continuation \
    on same line
    """;
```

---

## JDK 16 Features (2021)

### Records (Standard)

Immutable data carriers with auto-generated methods.

```java
// Simple record - generates constructor, getters, equals, hashCode, toString
public record Point(int x, int y) {}

// Usage
Point p = new Point(10, 20);
int x = p.x();  // accessor method (not getX)
int y = p.y();

// Record with validation (compact constructor)
public record Range(int start, int end) {
    public Range {
        if (start > end) {
            throw new IllegalArgumentException("start must be <= end");
        }
    }
}

// Record with additional methods
public record Person(String name, int age) {
    // Static factory
    public static Person of(String name, int age) {
        return new Person(name, age);
    }

    // Additional instance method
    public boolean isAdult() {
        return age >= 18;
    }

    // Override accessor
    public String name() {
        return name.toUpperCase();
    }
}

// Record implementing interface
public record Circle(double radius) implements Shape {
    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

// Generic record
public record Pair<T, U>(T first, U second) {}

// Local record (inside method)
public List<String> processData(List<Data> items) {
    record Intermediate(String id, int value) {}

    return items.stream()
        .map(d -> new Intermediate(d.getId(), d.getValue()))
        .filter(i -> i.value() > 0)
        .map(Intermediate::id)
        .toList();
}
```

### Pattern Matching for instanceof (Standard)

```java
// Before: instanceof + cast
if (obj instanceof String) {
    String s = (String) obj;
    System.out.println(s.length());
}

// After: pattern variable
if (obj instanceof String s) {
    System.out.println(s.length());
}

// With logical operators
if (obj instanceof String s && s.length() > 5) {
    System.out.println(s.toUpperCase());
}

// In complex conditions
if (obj instanceof String s && !s.isBlank()) {
    process(s.trim());
} else if (obj instanceof Number n) {
    process(n.doubleValue());
}

// Negation pattern
if (!(obj instanceof String s)) {
    return; // s not in scope here
}
// s is in scope here
System.out.println(s.length());
```

### Stream.toList()

```java
// New concise way - returns unmodifiable list
List<String> list = stream.toList();

// Equivalent to (but more efficient than):
List<String> list = stream.collect(Collectors.toUnmodifiableList());

// Note: toList() returns unmodifiable list
// If you need mutable list:
List<String> mutable = stream.collect(Collectors.toList());
// Or
List<String> mutable = new ArrayList<>(stream.toList());
```

---

## JDK 17 Features (2021) - LTS

### Sealed Classes (Standard)

Restrict which classes can extend/implement a type.

```java
// Sealed class with permits clause
public sealed class Shape permits Circle, Rectangle, Triangle {
    public abstract double area();
}

// Permitted subclasses must be final, sealed, or non-sealed
public final class Circle extends Shape {
    private final double radius;

    public Circle(double radius) {
        this.radius = radius;
    }

    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

public final class Rectangle extends Shape {
    private final double width, height;

    public Rectangle(double width, double height) {
        this.width = width;
        this.height = height;
    }

    @Override
    public double area() {
        return width * height;
    }
}

// Non-sealed allows unrestricted extension
public non-sealed class Triangle extends Shape {
    // Any class can extend Triangle
    @Override
    public double area() { return 0; }
}

// Sealed interfaces
public sealed interface Result<T> permits Success, Failure {
}

public record Success<T>(T value) implements Result<T> {}
public record Failure<T>(String error) implements Result<T> {}

// Useful with pattern matching (JDK 21)
double getArea(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.radius() * c.radius();
        case Rectangle r -> r.width() * r.height();
        case Triangle t -> t.area();
    };
}
```

---

## JDK 21 Features (2023) - LTS

### Record Patterns (Standard)

Deconstruct records in pattern matching.

```java
record Point(int x, int y) {}
record Line(Point start, Point end) {}

// Pattern matching with record deconstruction
if (obj instanceof Point(int x, int y)) {
    System.out.println("x=" + x + ", y=" + y);
}

// Nested record patterns
if (obj instanceof Line(Point(int x1, int y1), Point(int x2, int y2))) {
    double length = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
}

// In switch expressions
String describe(Object obj) {
    return switch (obj) {
        case Point(int x, int y) when x == y -> "diagonal point";
        case Point(int x, int y) -> "point at (%d, %d)".formatted(x, y);
        case Line(Point start, Point end) -> "line from %s to %s".formatted(start, end);
        default -> "unknown";
    };
}

// With var for inferred types
if (obj instanceof Point(var x, var y)) {
    // x and y are inferred as int
}
```

### Pattern Matching for switch (Standard)

```java
// Type patterns in switch
String format(Object obj) {
    return switch (obj) {
        case Integer i -> "int: %d".formatted(i);
        case Long l -> "long: %d".formatted(l);
        case Double d -> "double: %.2f".formatted(d);
        case String s -> "string: %s".formatted(s);
        case null -> "null value";
        default -> "unknown: " + obj.getClass();
    };
}

// Guarded patterns with 'when'
String describeNumber(Number n) {
    return switch (n) {
        case Integer i when i < 0 -> "negative int";
        case Integer i when i == 0 -> "zero";
        case Integer i -> "positive int: " + i;
        case Double d when d.isNaN() -> "not a number";
        case Double d when d.isInfinite() -> "infinite";
        case Double d -> "double: " + d;
        default -> "other number";
    };
}

// Null handling
String process(String s) {
    return switch (s) {
        case null -> "empty";
        case String str when str.isBlank() -> "blank";
        case String str -> str.trim();
    };
}

// With sealed types - exhaustive (no default needed)
sealed interface PaymentMethod permits CreditCard, BankTransfer, Cash {}
record CreditCard(String number, String expiry) implements PaymentMethod {}
record BankTransfer(String iban) implements PaymentMethod {}
record Cash() implements PaymentMethod {}

String process(PaymentMethod method) {
    return switch (method) {
        case CreditCard(var number, var expiry) -> "Card: " + number;
        case BankTransfer(var iban) -> "Bank: " + iban;
        case Cash() -> "Cash payment";
    };
}
```

### Virtual Threads (Standard)

Lightweight threads for high-throughput concurrent applications.

```java
// Create virtual thread
Thread vThread = Thread.startVirtualThread(() -> {
    System.out.println("Running in virtual thread");
});

// Using builder
Thread vThread = Thread.ofVirtual()
    .name("my-virtual-thread")
    .start(() -> doWork());

// ExecutorService with virtual threads
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    // Each task runs in its own virtual thread
    IntStream.range(0, 10_000).forEach(i ->
        executor.submit(() -> {
            Thread.sleep(Duration.ofSeconds(1));
            return i;
        })
    );
} // Executor auto-closed, waits for all tasks

// Practical example: concurrent HTTP calls
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<String>> futures = urls.stream()
        .map(url -> executor.submit(() -> fetchUrl(url)))
        .toList();

    List<String> results = futures.stream()
        .map(f -> {
            try {
                return f.get();
            } catch (Exception e) {
                return "error";
            }
        })
        .toList();
}

// Check if current thread is virtual
boolean isVirtual = Thread.currentThread().isVirtual();

// Virtual threads are daemon threads by default
// They don't prevent JVM shutdown
```

### Sequenced Collections (Standard)

New interfaces for collections with defined encounter order.

```java
// New interfaces:
// SequencedCollection<E> extends Collection<E>
// SequencedSet<E> extends Set<E>, SequencedCollection<E>
// SequencedMap<K,V> extends Map<K,V>

// SequencedCollection methods
List<String> list = new ArrayList<>(List.of("a", "b", "c"));
list.getFirst();        // "a"
list.getLast();         // "c"
list.addFirst("z");     // ["z", "a", "b", "c"]
list.addLast("d");      // ["z", "a", "b", "c", "d"]
list.removeFirst();     // removes "z"
list.removeLast();      // removes "d"
list.reversed();        // reversed view: ["c", "b", "a"]

// SequencedSet (e.g., LinkedHashSet)
SequencedSet<String> set = new LinkedHashSet<>(List.of("a", "b", "c"));
set.getFirst();         // "a"
set.getLast();          // "c"
set.reversed();         // reversed view

// SequencedMap (e.g., LinkedHashMap)
SequencedMap<String, Integer> map = new LinkedHashMap<>();
map.put("one", 1);
map.put("two", 2);
map.put("three", 3);

map.firstEntry();       // one=1
map.lastEntry();        // three=3
map.pollFirstEntry();   // removes and returns one=1
map.pollLastEntry();    // removes and returns three=3
map.putFirst("zero", 0);
map.putLast("four", 4);
map.reversed();         // reversed view

// Reversed views are backed by original collection
var reversed = list.reversed();
reversed.add("x");      // adds to front of original list
```

---

## Migration Patterns

### JDK 8 to 11 Quick Wins

```java
// Collection creation
// Before
List<String> list = Collections.unmodifiableList(Arrays.asList("a", "b"));
// After
List<String> list = List.of("a", "b");

// String operations
// Before
String s = "  hello  ";
if (s.trim().isEmpty()) { }
// After
if (s.isBlank()) { }

// Optional chaining
// Before
if (opt.isPresent()) {
    process(opt.get());
} else {
    processDefault();
}
// After
opt.ifPresentOrElse(this::process, this::processDefault);
```

### JDK 11 to 17 Quick Wins

```java
// Data classes with records
// Before
public class Point {
    private final int x;
    private final int y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    public int getX() { return x; }
    public int getY() { return y; }

    @Override
    public boolean equals(Object o) { /* ... */ }
    @Override
    public int hashCode() { /* ... */ }
    @Override
    public String toString() { /* ... */ }
}

// After
public record Point(int x, int y) {}

// instanceof with cast
// Before
if (obj instanceof String) {
    String s = (String) obj;
    return s.length();
}
// After
if (obj instanceof String s) {
    return s.length();
}

// Multi-line strings
// Before
String json = "{\n" +
    "  \"name\": \"John\",\n" +
    "  \"age\": 30\n" +
    "}";
// After
String json = """
    {
      "name": "John",
      "age": 30
    }
    """;

// Stream to list
// Before
List<String> list = stream.collect(Collectors.toList());
// After
List<String> list = stream.toList();
```

### JDK 17 to 21 Quick Wins

```java
// First/last element access
// Before
String first = list.get(0);
String last = list.get(list.size() - 1);
// After
String first = list.getFirst();
String last = list.getLast();

// High-throughput concurrent tasks
// Before (platform threads - expensive)
ExecutorService executor = Executors.newFixedThreadPool(100);
// After (virtual threads - lightweight)
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

// Pattern matching in switch
// Before
String result;
if (obj instanceof Integer i) {
    result = "int: " + i;
} else if (obj instanceof String s) {
    result = "string: " + s;
} else {
    result = "unknown";
}
// After
String result = switch (obj) {
    case Integer i -> "int: " + i;
    case String s -> "string: " + s;
    default -> "unknown";
};
```

## Guidelines

- **Records**: Use for DTOs, value objects, and data transfer. Don't use when you need inheritance or mutable state.
- **Sealed Classes**: Use to model fixed set of types (state machines, ASTs, domain models).
- **Virtual Threads**: Use for I/O-bound tasks. Not beneficial for CPU-bound tasks.
- **Pattern Matching**: Prefer over chains of instanceof checks or type-based switch statements.
- **var**: Use when the type is obvious from context. Avoid when it reduces readability.
- **Text Blocks**: Use for multi-line strings (JSON, SQL, HTML). Mind the indentation.

## Agent Self-Check

Before executing, verify:
- [ ] All required inputs are present
- [ ] Skill documentation has been loaded
- [ ] Scope boundary is understood — no out-of-scope changes
- [ ] Iron Rules (No Assumptions, Version Source of Truth) acknowledged
- [ ] Output format understood
