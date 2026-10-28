# Checkstyle Fix Patterns Reference

> **Purpose:** Common checkstyle error patterns and automated fix strategies.
> **Used by:** checkstyle-agent
> **Scope:** Only `severity="error"` violations. Warnings are informational — ignore them entirely.

---

## 1. Error Detection

Parse the XML report at `build/reports/checkstyle/main.xml`:
- Use Grep with pattern `severity="error"` to extract all error lines
- Use Grep with pattern `severity="warning"` to count warnings (log count, then discard)

**If zero errors (only warnings):** Build is compliant. No fixes needed.

---

## 2. Common Error Patterns and Fixes

### 2.1 Unused Imports
**Pattern:** `"Unused import"` or `"UnusedImports"`
**Fix:** Remove the import line. Options:
- MCP tool: `mcp__jetbrains__reformat_file(path=file_path)` (auto-removes unused imports)
- Edit tool: Remove the specific import line

### 2.2 Line Length Violations
**Pattern:** `"Line is longer than"` (typically >120 chars)
**Fix:** Wrap long lines at natural boundaries:
- Method parameters: break after comma
- Method chains: break before `.`
- String concatenation: break before `+`
- Ternary operators: break before `?` and `:`

### 2.3 Whitespace Issues
**Pattern:** `"WhitespaceAround"`, `"WhitespaceAfter"`, `"NoWhitespaceBefore"`
**Fix:** MCP tool `mcp__jetbrains__reformat_file(path=file_path)` handles all whitespace issues.

### 2.4 Missing Javadoc
**Pattern:** `"Missing a Javadoc comment"` or `"JavadocMethod"`
**Fix:** Add minimal Javadoc for public/protected methods only:
```java
/**
 * {Brief description of what the method does}.
 */
```
Private methods do not need Javadoc.

### 2.5 Naming Violations
**Pattern:** `"Name.*must match pattern"` or `"MemberName"`, `"MethodName"`, `"ParameterName"`
**Fix:** Use MCP tool `mcp__jetbrains__rename_refactoring(pathInProject, symbolName, newName)` for safe project-wide rename.

### 2.6 Missing Final Modifier
**Pattern:** `"Variable.*should be declared final"`
**Fix:** Add `final` keyword to the variable declaration.

### 2.7 Empty Blocks
**Pattern:** `"Must have at least one statement"` or `"EmptyBlock"`
**Fix:** Add a comment explaining why the block is empty, or add appropriate handling.

---

## 3. Fix Strategy Priority

1. **Batch by file:** Group all errors per file, fix all errors in one file before moving to next
2. **Use MCP reformat first:** `mcp__jetbrains__reformat_file` fixes whitespace + unused imports in one pass
3. **Manual fixes second:** Line length, Javadoc, naming require targeted edits
4. **Verify per file:** Re-run checkstyle after fixing each file to catch cascading issues

---

## 4. Verification

After all fixes:
```bash
$GRADLE_CMD checkstyle --console=plain
```

**Success condition:** Zero `severity="error"` violations. Warnings are acceptable.

If errors remain: re-read XML, fix remaining errors, re-run. Do NOT attempt to fix warnings.

---

**Document Version:** 1.0
**Last Updated:** 2026-02-28
