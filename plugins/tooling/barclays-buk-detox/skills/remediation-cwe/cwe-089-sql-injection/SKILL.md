---
name: cwe-089-sql-injection
description: "CWE-89: SQL Injection Remediation — Remediate SQL injection vulnerabilities by replacing string concatenation or format-string construction of SQL queries with parameterized queries (pre"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-89: SQL Injection Remediation
## Quick Start

This skill provides the fix pattern for CWE-089. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-089 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-89
- **CWE Name**: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')
- **Severity**: Critical
- **OWASP Category**: A03:2021 - Injection

## Purpose

Remediate SQL injection vulnerabilities by replacing string concatenation or format-string construction of SQL queries with parameterized queries (prepared statements). This skill transforms vulnerable SQL query construction patterns into safe, parameterized equivalents while preserving the query's intended logic and functionality. It covers Python (SQLAlchemy, psycopg2, raw SQL via DB-API), Java (JDBC PreparedStatement), and JavaScript/Node.js (pg, mysql2).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the vulnerable SQL query construction.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-89`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework or library in use (`sqlalchemy`, `psycopg2`, `jdbc`, `pg`, `mysql2`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and SQL library in use.**
   - Examine import statements and the coding patterns to identify the language and SQL library.
   - If `language` and `framework` inputs are provided, use them. Otherwise, auto-detect.

3. **Identify the vulnerable SQL construction pattern.**
   - Look for string concatenation (`+`, `||`), f-strings (`f"...{var}..."`), `%` formatting, `.format()`, or template literals (`` `...${var}...` ``) used to build SQL query strings with user-controlled input.
   - Trace the user-controlled input back to its source (request parameter, function argument, external data).

4. **Construct the parameterized replacement.**
   - Replace interpolated values with parameter placeholders appropriate to the library:
     - Python DB-API / psycopg2: `%s` positional placeholders or `%(name)s` named placeholders.
     - SQLAlchemy: `:name` named placeholders with `text()` or ORM constructs.
     - Java JDBC: `?` positional placeholders with `PreparedStatement.setXxx()`.
     - Node.js pg: `$1, $2, ...` numbered placeholders.
     - Node.js mysql2: `?` positional placeholders.
   - Collect the values into a separate parameter tuple, list, dict, or array passed to the execution method.

5. **Handle dynamic query components that cannot be parameterized.**
   - Table names, column names, and SQL keywords cannot be parameterized.
   - For these, implement an allowlist validation pattern: compare the dynamic value against a set of known-safe values before inserting it into the query string.
   - If the dynamic value does not match the allowlist, raise an error or use a safe default.

6. **Apply the edit.**
   - Use `Edit` to replace the vulnerable code with the parameterized version.
   - Ensure that imports are updated if new modules are needed (e.g., `from sqlalchemy import text`).
   - Preserve code formatting, indentation, and surrounding logic.

7. **Scan for similar patterns in the same file.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the file.
   - Apply the same fix to all instances.

8. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the fix is syntactically correct.
   - Confirm that no string interpolation of user input into SQL remains.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the parameterized replacement>",
      "fix_type": "parameterized_query | allowlist_validation"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries have valid `fixed_code`.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

SQL injection occurs when user-controlled input is directly concatenated or interpolated into a SQL query string without sanitization or parameterization.

### Detection Patterns

**String concatenation in SQL queries:**
```
# Regex patterns for detection
# Python f-string:          f"SELECT.*\{.*\}.*"
# Python %-format:          "SELECT.*%s" % .*
# Python .format():         "SELECT.*\{\}".format\(
# Python concatenation:     "SELECT.*" \+ .*
# Java concatenation:       "SELECT.*" \+ .*
# JavaScript template:      `SELECT.*\$\{.*\}`
```

**Indicators of user-controlled input in queries:**
- Variables sourced from `request.args`, `request.form`, `request.GET`, `request.POST`, `req.query`, `req.body`, `req.params`, `getParameter()`.
- Function parameters passed directly into query strings.
- Data read from external files or environment without validation.

## Fix Pattern

The general fix is to separate SQL structure from SQL data by using parameterized queries (prepared statements). The database driver handles escaping and quoting of parameter values, preventing injected SQL from altering the query's structure.

**Transformation steps:**
1. Identify all user-controlled values embedded in the SQL string.
2. Replace each embedded value with a placeholder appropriate to the driver.
3. Pass the values as a separate parameter collection to the query execution method.
4. For dynamic identifiers (table/column names), use allowlist validation instead.

## Language-Specific Examples

### Python -- psycopg2

**Before (vulnerable):**
```python
def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
```

**After (fixed):**
```python
def get_user(conn, username):
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchone()
```

**Explanation:** The f-string interpolation is replaced with a `%s` placeholder. The `username` value is passed as a tuple in the second argument to `cursor.execute()`. psycopg2 handles proper escaping and quoting.

### Python -- SQLAlchemy

**Before (vulnerable):**
```python
from sqlalchemy import create_engine

def search_products(engine, product_name):
    with engine.connect() as conn:
        result = conn.execute(
            "SELECT * FROM products WHERE name LIKE '%" + product_name + "%'"
        )
        return result.fetchall()
```

**After (fixed):**
```python
from sqlalchemy import create_engine, text

def search_products(engine, product_name):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM products WHERE name LIKE :pattern"),
            {"pattern": f"%{product_name}%"}
        )
        return result.fetchall()
```

**Explanation:** String concatenation is replaced with SQLAlchemy's `text()` construct and a named parameter `:pattern`. The LIKE wildcards are applied to the parameter value, not the query structure. The import of `text` is added.

### Python -- Raw DB-API (sqlite3, etc.)

**Before (vulnerable):**
```python
import sqlite3

def delete_order(db_path, order_id):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM orders WHERE id = %s" % order_id)
    conn.commit()
```

**After (fixed):**
```python
import sqlite3

def delete_order(db_path, order_id):
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
```

**Explanation:** The `%` string formatting operator is replaced with a `?` placeholder (sqlite3's paramstyle). The value is passed as a tuple.

### Java -- JDBC PreparedStatement

**Before (vulnerable):**
```java
public User getUser(Connection conn, String username) throws SQLException {
    String query = "SELECT * FROM users WHERE username = '" + username + "'";
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(query);
    if (rs.next()) {
        return new User(rs.getString("username"), rs.getString("email"));
    }
    return null;
}
```

**After (fixed):**
```java
public User getUser(Connection conn, String username) throws SQLException {
    String query = "SELECT * FROM users WHERE username = ?";
    PreparedStatement pstmt = conn.prepareStatement(query);
    pstmt.setString(1, username);
    ResultSet rs = pstmt.executeQuery();
    if (rs.next()) {
        return new User(rs.getString("username"), rs.getString("email"));
    }
    return null;
}
```

**Explanation:** `Statement` is replaced with `PreparedStatement`. The concatenated `username` is replaced with a `?` placeholder and bound via `pstmt.setString(1, username)`. The parameter index is 1-based.

### JavaScript/Node.js -- pg (PostgreSQL)

**Before (vulnerable):**
```javascript
async function getUser(pool, username) {
  const query = `SELECT * FROM users WHERE username = '${username}'`;
  const result = await pool.query(query);
  return result.rows[0];
}
```

**After (fixed):**
```javascript
async function getUser(pool, username) {
  const query = 'SELECT * FROM users WHERE username = $1';
  const result = await pool.query(query, [username]);
  return result.rows[0];
}
```

**Explanation:** The template literal with interpolation is replaced with a plain string containing the `$1` numbered placeholder. The value is passed as an array in the second argument to `pool.query()`.

### JavaScript/Node.js -- mysql2

**Before (vulnerable):**
```javascript
async function getUser(connection, username) {
  const query = "SELECT * FROM users WHERE username = '" + username + "'";
  const [rows] = await connection.execute(query);
  return rows[0];
}
```

**After (fixed):**
```javascript
async function getUser(connection, username) {
  const query = 'SELECT * FROM users WHERE username = ?';
  const [rows] = await connection.execute(query, [username]);
  return rows[0];
}
```

**Explanation:** String concatenation is replaced with a `?` placeholder. The value is passed as an array in the second argument to `connection.execute()`.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Manual test with SQL injection payloads:**
   - Input: `' OR '1'='1` -- should return no results or only the matching row, not all rows.
   - Input: `'; DROP TABLE users; --` -- should not execute the DROP statement.
   - Input: `' UNION SELECT password FROM admin --` -- should not return admin passwords.

2. **Automated unit test pattern:**
   ```python
   def test_sql_injection_prevented(db_connection):
       malicious_input = "' OR '1'='1"
       result = get_user(db_connection, malicious_input)
       assert result is None  # No user has this literal username
   ```

3. **Semgrep rules that should pass after fix:**
   ```yaml
   rules:
     - id: python-sql-injection
       patterns:
         - pattern: |
             $CURSOR.execute("..." + $VAR + "...")
         - pattern: |
             $CURSOR.execute(f"...{$VAR}...")
       message: "SQL injection via string concatenation"
       languages: [python]
       severity: ERROR
   ```

### Verifying Functionality is Preserved

- Run existing unit and integration tests for the affected module.
- Verify that the query returns the same results for known valid inputs.
- Test edge cases: empty strings, strings with single quotes, strings with special characters, NULL values, numeric values.

## Common Mistakes

1. **Parameterizing only some inputs.** If a query has multiple interpolated values, all of them must be parameterized, not just the one flagged by the scanner.

2. **Using parameterization for identifiers.** Table names, column names, and SQL keywords cannot be parameterized. Using `SELECT * FROM ?` will fail. Use allowlist validation for identifiers instead:
   ```python
   ALLOWED_TABLES = {"users", "orders", "products"}
   if table_name not in ALLOWED_TABLES:
       raise ValueError(f"Invalid table name: {table_name}")
   query = f"SELECT * FROM {table_name} WHERE id = %s"
   cursor.execute(query, (record_id,))
   ```

3. **Using escaping instead of parameterization.** Manual escaping (e.g., `value.replace("'", "''")`) is fragile and encoding-dependent. Always prefer parameterized queries.

4. **Forgetting to pass parameters as a tuple in Python.** `cursor.execute(query, (value))` passes a single value, not a tuple. Use `(value,)` with a trailing comma for single-element tuples.

5. **Using `executemany()` when `execute()` is needed.** These are different methods. A single query with multiple parameters still uses `execute()`.

6. **Wrapping parameterized values in quotes in the query string.** Do not write `WHERE name = '%s'` -- the driver adds quotes automatically. Write `WHERE name = %s`.

7. **Using ORMs but dropping to raw SQL for complex queries without parameterization.** When using SQLAlchemy or similar ORMs, if you must use raw SQL, always use `text()` with bound parameters rather than string formatting.

8. **Ignoring stored procedures.** If user input is passed to a stored procedure that internally concatenates it into SQL, the injection still exists. Verify that stored procedures also use parameterized internal queries.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Language not recognized** | Return error JSON. SQL injection remediation requires knowing the specific driver API. |
| **Cannot determine SQL library** | Flag for manual review. Provide the general parameterized query pattern as guidance but do not apply an edit. |
| **Query spans multiple lines/files** | Reconstruct the full query string from all contributing lines before applying the fix. If the query is assembled across files, flag for manual review. |
| **Dynamic query construction in a loop** | Handle each iteration's query construction. If the pattern is too complex to safely transform automatically, flag for manual review. |
| **ORM query builder (not raw SQL)** | ORM query builders (SQLAlchemy ORM, Hibernate Criteria) are typically safe. Verify that user input is not being used in `text()` or `literal()` calls without parameterization. If the ORM usage is safe, mark as false positive. |

## Constraints

- **Preserve query logic**: The parameterized query must produce the same results as the original for all valid inputs.
- **No execution**: Do not execute queries against any database to test the fix.
- **No schema changes**: Do not alter database schemas, stored procedures, or views.
- **Minimal diff**: Change only the vulnerable query construction. Do not refactor surrounding code unless required for the fix (e.g., adding an import).
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
