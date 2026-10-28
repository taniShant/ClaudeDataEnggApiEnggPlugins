---
name: cwe-770-allocation-without-limits
description: "CWE-770: Allocation of Resources Without Limits or Throttling Remediation — Remediate resource allocation vulnerabilities by adding explicit limits to memory allocation, connection pools, file descriptor usage, thread creation"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-770: Allocation of Resources Without Limits or Throttling Remediation
## Quick Start

This skill provides the fix pattern for CWE-770. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-770 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-770
- **CWE Name**: Allocation of Resources Without Limits or Throttling
- **Severity**: High
- **OWASP Category**: A05:2021 - Security Misconfiguration

## Purpose

Remediate resource allocation vulnerabilities by adding explicit limits to memory allocation, connection pools, file descriptor usage, thread creation, and data collection operations. This skill identifies code paths where unbounded resource allocation can be triggered by external input, leading to memory exhaustion, file descriptor exhaustion, connection pool starvation, or thread pool saturation, and adds appropriate limits with graceful error handling. It covers Python (memory limits, connection pools, iterators), Java (pool sizing, bounded collections, resource limits), and JavaScript/Node.js (memory limits, connection pools, stream backpressure).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the resource allocation vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-770`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `allocation_type` (string, optional): Type of allocation at risk (`memory`, `connections`, `file_descriptors`, `threads`, `disk`, `generic`). Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use. Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and identify the unbounded allocation.**
   - Examine the code to identify what resource is being allocated without limits.
   - Trace the allocation to its trigger (user input, external data, loop iteration).

3. **Classify the allocation type.**
   - **Memory**: Growing lists, dictionaries, or buffers based on external input without size limits.
   - **Connections**: Creating database, HTTP, or socket connections without pool limits or maximum counts.
   - **File descriptors**: Opening files in loops without closing, or creating too many sockets.
   - **Threads/Processes**: Spawning threads or processes per request without pool limits.
   - **Disk**: Writing data to disk without size or quota limits.

4. **Apply the appropriate limit.**
   - **Memory**: Add collection size limits, use iterators/generators instead of loading all data, implement streaming for large data.
   - **Connections**: Configure connection pool with maximum size, timeouts, and idle limits.
   - **File descriptors**: Use context managers (`with` statements), limit concurrent open files, close resources in `finally` blocks.
   - **Threads/Processes**: Use bounded thread pools or process pools with a maximum worker count.
   - **Disk**: Add quota checks, enforce maximum file sizes, implement cleanup policies.
   - **Pagination**: Add cursor-based or offset pagination for data retrieval endpoints.

5. **Apply the edit.**
   - Use `Edit` to add resource limits.
   - Add necessary imports.
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other instances of unbounded allocation.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm resource limits are in place.
   - Confirm that error handling is present for when limits are reached.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "allocation_type": "<string: memory | connections | file_descriptors | threads | disk | generic>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the unbounded code>",
      "fixed_code": "<string: the bounded replacement>",
      "fix_type": "collection_limit | pool_config | context_manager | thread_pool | pagination | streaming | quota"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "limits_configured": {
    "max_memory_per_request": "<string: if applicable>",
    "max_pool_size": "<integer: if applicable>",
    "max_threads": "<integer: if applicable>",
    "max_items": "<integer: if applicable>"
  },
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all unbounded allocations have explicit limits.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Resource allocation without limits occurs when an application creates or accumulates resources (memory, connections, threads, files) in an unbounded manner based on external input. An attacker can trigger excessive allocation to exhaust the resource, causing denial of service.

### Detection Patterns

**Unbounded memory allocation:**
```
# Python:      data = []; for item in huge_input: data.append(process(item))
# Python:      content = request.get_data()  # No size limit
# Python:      json.loads(request.data)  # Parsing arbitrary-size JSON
# JavaScript:  const items = []; while (hasMore) items.push(await fetch(next))
# Java:        List<Item> items = new ArrayList<>(); while (rs.next()) items.add(map(rs))
```

**Unbounded connection creation:**
```
# Python:      conn = psycopg2.connect(...)  # New connection per request, no pool
# JavaScript:  const client = new Client(); await client.connect()  # No pool
# Java:        Connection conn = DriverManager.getConnection(url)  # No pool
```

**Unbounded file descriptor usage:**
```
# Python:      f = open(path)  # Not closed, no context manager
# Python:      files = [open(p) for p in paths]  # Opens many files at once
# JavaScript:  fs.openSync(path)  # Not closed
```

**Unbounded thread/process creation:**
```
# Python:      threading.Thread(target=handler).start()  # Unbounded threads
# Java:        new Thread(handler).start()  # Unbounded threads
# JavaScript:  cluster.fork()  # Unbounded forking
```

**Reading entire files or streams into memory:**
```
# Python:      data = file.read()  # Reads entire file into memory
# Python:      response = requests.get(url); data = response.content  # Entire response in memory
# JavaScript:  const data = fs.readFileSync(path)  # Entire file in memory
# Java:        byte[] data = Files.readAllBytes(path)  # Entire file in memory
```

**Regex detection patterns:**
```
# Unbounded list:       \[\]\s*;?\s*(for|while).*\.append\(|\.push\(
# No pool:              (psycopg2|DriverManager|new Client)\.(connect|getConnection)
# Missing close:        open\([^)]+\)(?!.*with\s|.*\.close\(\))
# Unbounded thread:     (threading\.Thread|new\s+Thread)\(.*\)\.start\(\)
# Read all:             \.(read|readFileSync|readAllBytes)\(\)
```

## Fix Pattern

The general fix adds explicit bounds to all resource allocation paths:

1. **Memory**: Use bounded collections, generators/iterators, streaming, and pagination.
2. **Connections**: Use connection pools with configurable maximum sizes and timeouts.
3. **File descriptors**: Use context managers and limit concurrent open files.
4. **Threads**: Use bounded thread pools (ThreadPoolExecutor, ExecutorService).
5. **Data retrieval**: Use pagination with server-enforced maximum page sizes.

**Transformation steps:**
1. Identify the resource being allocated without limits.
2. Determine a reasonable maximum based on the application's requirements.
3. Add explicit bounds, pool configuration, or streaming patterns.
4. Add error handling for when limits are reached.
5. Ensure resources are properly released (connections closed, files closed, threads terminated).

## Language-Specific Examples

### Python -- Unbounded List Growth

**Before (vulnerable):**
```python
from flask import Flask, request, jsonify

@app.route('/api/process', methods=['POST'])
def process_data():
    items = request.json.get('items', [])
    results = []
    for item in items:
        results.append(expensive_process(item))
    return jsonify({'results': results})
```

**After (fixed):**
```python
from flask import Flask, request, jsonify

MAX_ITEMS = 1000

@app.route('/api/process', methods=['POST'])
def process_data():
    items = request.json.get('items', [])

    if not isinstance(items, list):
        return jsonify({'error': 'Items must be a list'}), 400
    if len(items) > MAX_ITEMS:
        return jsonify({'error': f'Too many items. Maximum is {MAX_ITEMS}'}), 400

    results = []
    for item in items:
        results.append(expensive_process(item))
    return jsonify({'results': results})
```

**Explanation:** The number of items that can be processed in a single request is capped at `MAX_ITEMS`. Input type is validated. Without this limit, an attacker could send millions of items, consuming CPU and memory.

### Python -- Streaming Large Data Instead of Loading into Memory

**Before (vulnerable):**
```python
def process_large_file(file_path):
    with open(file_path, 'r') as f:
        data = f.read()  # Loads entire file into memory
    lines = data.split('\n')
    results = []
    for line in lines:
        results.append(parse_line(line))
    return results
```

**After (fixed):**
```python
def process_large_file(file_path, max_lines=100000):
    results = []
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num > max_lines:
                break
            results.append(parse_line(line.rstrip('\n')))
    return results

# For very large files, use a generator:
def process_large_file_streaming(file_path, max_lines=100000):
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num > max_lines:
                break
            yield parse_line(line.rstrip('\n'))
```

**Explanation:** Instead of reading the entire file into memory with `f.read()`, the file is read line by line using iteration (which uses minimal memory). A maximum line count is enforced. A generator version is provided for truly streaming processing where results do not need to be collected in memory.

### Python -- Connection Pool Configuration

**Before (vulnerable):**
```python
import psycopg2
from flask import Flask

app = Flask(__name__)

@app.route('/api/data')
def get_data():
    conn = psycopg2.connect(
        host='db.example.com',
        database='myapp',
        user='appuser',
        password=os.environ['DB_PASSWORD']
    )
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data LIMIT 100")
        results = cursor.fetchall()
        return jsonify(results)
    finally:
        conn.close()
```

**After (fixed):**
```python
import os
from psycopg2 import pool
from flask import Flask, jsonify

app = Flask(__name__)

# Create a bounded connection pool
db_pool = pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=20,
    host='db.example.com',
    database='myapp',
    user='appuser',
    password=os.environ['DB_PASSWORD']
)

@app.route('/api/data')
def get_data():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data LIMIT 100")
        results = cursor.fetchall()
        return jsonify(results)
    finally:
        db_pool.putconn(conn)
```

**Explanation:** Instead of creating a new database connection per request (which can exhaust database connection limits under load), a `ThreadedConnectionPool` is used with a maximum of 20 connections. Connections are borrowed from the pool and returned after use.

### Python -- Bounded Thread Pool

**Before (vulnerable):**
```python
import threading

def handle_request(request):
    thread = threading.Thread(target=process, args=(request,))
    thread.start()
```

**After (fixed):**
```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

def handle_request(request):
    try:
        future = executor.submit(process, request)
    except RuntimeError:
        raise ServiceUnavailableError("Server is at capacity, please try again later")
```

**Explanation:** Unbounded `threading.Thread()` creation is replaced with a `ThreadPoolExecutor` with a maximum of 10 workers. When all workers are busy, new submissions are queued. The pool prevents thread exhaustion under heavy load.

### Java -- Bounded Connection Pool with HikariCP

**Before (vulnerable):**
```java
public class DataService {
    public List<Data> getData() throws SQLException {
        Connection conn = DriverManager.getConnection(
            "jdbc:postgresql://db.example.com:5432/myapp",
            System.getenv("DB_USER"),
            System.getenv("DB_PASSWORD")
        );
        try {
            PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM data LIMIT 100");
            ResultSet rs = pstmt.executeQuery();
            List<Data> results = new ArrayList<>();
            while (rs.next()) {
                results.add(mapRow(rs));
            }
            return results;
        } finally {
            conn.close();
        }
    }
}
```

**After (fixed):**
```java
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

public class DataService {

    private static final HikariDataSource dataSource;

    static {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:postgresql://db.example.com:5432/myapp");
        config.setUsername(System.getenv("DB_USER"));
        config.setPassword(System.getenv("DB_PASSWORD"));
        config.setMaximumPoolSize(20);
        config.setMinimumIdle(5);
        config.setConnectionTimeout(30000);   // 30 seconds
        config.setIdleTimeout(600000);         // 10 minutes
        config.setMaxLifetime(1800000);        // 30 minutes
        dataSource = new HikariDataSource(config);
    }

    public List<Data> getData() throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            PreparedStatement pstmt = conn.prepareStatement("SELECT * FROM data LIMIT 100");
            ResultSet rs = pstmt.executeQuery();
            List<Data> results = new ArrayList<>();
            while (rs.next()) {
                results.add(mapRow(rs));
            }
            return results;
        }
    }
}
```

**Explanation:** `DriverManager.getConnection()` (which creates a new connection each time) is replaced with HikariCP, a high-performance connection pool. The pool is configured with maximum size (20), idle timeout, and connection timeout. The `try-with-resources` statement ensures connections are returned to the pool.

### Java -- Bounded Collection with Size Limit

**Before (vulnerable):**
```java
@PostMapping("/api/import")
public ResponseEntity<?> importData(@RequestBody ImportRequest request) {
    List<Record> records = new ArrayList<>();
    for (String line : request.getData()) {
        records.add(parseLine(line));
    }
    recordService.saveAll(records);
    return ResponseEntity.ok(Map.of("imported", records.size()));
}
```

**After (fixed):**
```java
private static final int MAX_IMPORT_RECORDS = 10000;

@PostMapping("/api/import")
public ResponseEntity<?> importData(@RequestBody ImportRequest request) {
    List<String> data = request.getData();
    if (data == null) {
        return ResponseEntity.badRequest().body(Map.of("error", "No data provided"));
    }
    if (data.size() > MAX_IMPORT_RECORDS) {
        return ResponseEntity.badRequest()
            .body(Map.of("error", "Too many records. Maximum is " + MAX_IMPORT_RECORDS));
    }

    List<Record> records = new ArrayList<>(data.size());
    for (String line : data) {
        records.add(parseLine(line));
    }
    recordService.saveAll(records);
    return ResponseEntity.ok(Map.of("imported", records.size()));
}
```

**Explanation:** The number of records that can be imported in a single request is capped. The `ArrayList` is initialized with a known capacity to avoid unnecessary resizing. Without the limit, an attacker could send millions of records, exhausting memory.

### JavaScript/Node.js -- Connection Pool Limits

**Before (vulnerable):**
```javascript
const { Client } = require('pg');

app.get('/api/data', async (req, res) => {
  const client = new Client({
    connectionString: process.env.DATABASE_URL
  });
  await client.connect();
  try {
    const result = await client.query('SELECT * FROM data LIMIT 100');
    res.json(result.rows);
  } finally {
    await client.end();
  }
});
```

**After (fixed):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,                    // Maximum 20 connections
  idleTimeoutMillis: 30000,   // Close idle connections after 30s
  connectionTimeoutMillis: 5000, // Timeout if pool is full
});

app.get('/api/data', async (req, res) => {
  let client;
  try {
    client = await pool.connect();
    const result = await client.query('SELECT * FROM data LIMIT 100');
    res.json(result.rows);
  } catch (err) {
    if (err.message.includes('timeout')) {
      return res.status(503).json({ error: 'Database connection unavailable' });
    }
    throw err;
  } finally {
    if (client) client.release();
  }
});
```

**Explanation:** The `Client` (one connection per request) is replaced with `Pool` (shared, bounded pool). The pool is configured with a maximum of 20 connections, idle timeout, and connection timeout. When the pool is exhausted, new requests wait or timeout with a 503 response.

### JavaScript/Node.js -- Stream Backpressure for Large Data

**Before (vulnerable):**
```javascript
const fs = require('fs');

app.get('/api/export', async (req, res) => {
  const data = fs.readFileSync('/data/large-dataset.json', 'utf8');
  const parsed = JSON.parse(data);  // Entire file in memory
  res.json(parsed);
});
```

**After (fixed):**
```javascript
const fs = require('fs');
const { Transform } = require('stream');
const JSONStream = require('JSONStream');

app.get('/api/export', (req, res) => {
  const filePath = '/data/large-dataset.json';

  // Check file size before streaming
  const stats = fs.statSync(filePath);
  if (stats.size > 100 * 1024 * 1024) { // 100 MB limit
    return res.status(413).json({ error: 'Dataset too large' });
  }

  res.setHeader('Content-Type', 'application/json');

  const readStream = fs.createReadStream(filePath, { highWaterMark: 64 * 1024 });
  const parser = JSONStream.parse('*');

  let count = 0;
  const MAX_ITEMS = 100000;
  const limiter = new Transform({
    objectMode: true,
    transform(chunk, encoding, callback) {
      if (count >= MAX_ITEMS) {
        this.push(null);
        return callback();
      }
      count++;
      callback(null, chunk);
    }
  });

  readStream
    .pipe(parser)
    .pipe(limiter)
    .pipe(JSONStream.stringify())
    .pipe(res);

  readStream.on('error', (err) => {
    res.status(500).json({ error: 'Failed to read data' });
  });
});
```

**Explanation:** Instead of reading the entire file into memory with `readFileSync` and `JSON.parse`, the file is streamed using `JSONStream`. A transform stream limits the number of items to `MAX_ITEMS`. Backpressure from the network automatically controls how fast data is read from disk, preventing memory exhaustion.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Memory limit test**: Submit a request with an excessively large payload or many items. Verify the request is rejected with a 400 or 413 response.
2. **Connection pool test**: Under concurrent load, verify that connection usage stays within the pool maximum and requests queue or fail gracefully.
3. **File descriptor test**: Verify that files are properly closed after processing (check with `/proc/PID/fd` on Linux or resource monitoring).
4. **Thread pool test**: Under heavy load, verify that thread count stays within the pool maximum.
5. **Pagination test**: Request a large dataset and verify results are paginated with a capped page size.

### Automated Test Pattern

```python
def test_max_items_limit(client):
    large_payload = {'items': list(range(10001))}  # Over the 10000 limit
    response = client.post('/api/process', json=large_payload)
    assert response.status_code == 400
    assert 'Too many items' in response.get_json()['error']

def test_connection_pool_bounded():
    # Verify pool configuration
    assert db_pool.maxconn == 20

def test_stream_processing_memory():
    """Verify large file processing does not consume excessive memory."""
    import tracemalloc
    tracemalloc.start()
    results = list(process_large_file_streaming('/tmp/large_file.csv', max_lines=1000))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 50 * 1024 * 1024  # Less than 50 MB peak memory
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: unbounded-list-append
    patterns:
      - pattern: |
          $LIST = []
          for $ITEM in $INPUT:
              $LIST.append(...)
      - pattern-not-inside: |
          if len($INPUT) > $MAX:
              ...
    message: "List grows without bound from external input"
    languages: [python]
    severity: WARNING
  - id: no-connection-pool
    pattern: "DriverManager.getConnection(...)"
    message: "Direct JDBC connection without pool"
    languages: [java]
    severity: WARNING
  - id: unbounded-thread
    pattern: "threading.Thread(...).start()"
    message: "Unbounded thread creation - use ThreadPoolExecutor"
    languages: [python]
    severity: WARNING
```

### Verifying Functionality is Preserved

- Verify that normal-sized requests are processed correctly within the limits.
- Verify that connection pool provides enough connections for typical load.
- Verify that streaming and pagination return complete and correct data across multiple pages or chunks.
- Verify error messages are clear and actionable when limits are reached.

## Common Mistakes

1. **Setting pool sizes too small for production load.** A connection pool with `max=5` may be fine for development but insufficient for production. Size pools based on expected concurrent load and available database connections.

2. **Not releasing resources back to the pool.** Borrowing a connection from the pool and failing to return it (e.g., due to an exception) leaks the resource. Always use try/finally or context managers to ensure resources are returned.

3. **Loading data into a list when a generator would suffice.** If the consumer processes items one at a time, use a generator instead of collecting all items into a list. This keeps memory usage constant regardless of input size.

4. **Setting limits only in configuration files without enforcement in code.** A `MAX_ITEMS = 10000` constant is useless if the code never checks it. Limits must be enforced at the point where resources are allocated.

5. **Not handling the "limit reached" case.** When a limit is hit, the application should return a clear error message (e.g., 400, 429, 503) rather than crashing or hanging.

6. **Using `readAll`/`readFileSync` for files of unknown size.** Always check the file size before reading, or use streaming for files that may be large.

7. **Not setting idle timeouts on connection pools.** Idle connections consume resources on both the client and server. Configure idle timeouts to release unused connections.

8. **Unbounded caching.** Caches without eviction policies or size limits grow indefinitely. Use LRU (least recently used) caches with a maximum size (e.g., `functools.lru_cache(maxsize=1000)` in Python, Caffeine in Java, `lru-cache` in Node.js).

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine the resource type** | Apply general limits (input size validation, collection bounds) and flag for manual review. |
| **Connection pool library not available** | Recommend adding the library to dependencies. Provide a manual connection-limiting pattern as a temporary measure. |
| **Resource limits depend on deployment environment** | Note that pool sizes, thread counts, and memory limits should be tuned per environment. Provide reasonable defaults and flag for DevOps review. |
| **Existing code architecture prevents simple limiting** | If the code uses patterns that make limiting difficult (e.g., global state, shared mutable collections), note the architectural concern and provide the limit as close to the allocation point as possible. Flag for refactoring review. |
| **Multiple allocation points for the same resource** | Apply limits at each allocation point independently. If a shared limit is needed, recommend a centralized resource manager. |

## Constraints

- **Preserve functionality**: Limits must not prevent the application from handling normal workloads. Set limits based on reasonable usage expectations.
- **No execution**: Do not run the application or perform load testing.
- **Graceful degradation**: When limits are reached, return clear error messages with appropriate HTTP status codes. Do not crash or hang.
- **Minimal diff**: Add limits around the existing allocation logic. Do not refactor unrelated code.
- **Resource cleanup**: Ensure all resources are properly released (connections returned to pool, files closed, threads terminated) in all code paths, including error paths.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
