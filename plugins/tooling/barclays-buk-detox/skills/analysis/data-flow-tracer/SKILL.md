---
name: data-flow-tracer
description: "Data Flow Tracer — Trace the end-to-end data flow to and from a vulnerability point across the codebase. Starting from a known vulnerable sink (the line where the vulnerability was reported), this skill follows data bac"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/analysis/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Data Flow Tracer
## Quick Start

This skill provides code analysis capabilities for understanding vulnerability context and data flow.

```
# Loaded by detox-fix-agent before applying a fix to understand the code context.
# Traces data flow and identifies the vulnerable pattern in context.
```



## Purpose

Trace the end-to-end data flow to and from a vulnerability point across the codebase. Starting from a known vulnerable sink (the line where the vulnerability was reported), this skill follows data backward to its origin (the taint source -- typically user input or external data) and forward to its ultimate destination. It identifies all taint sources, intermediate transformations, sanitization points (or lack thereof), and sinks. The output enables downstream remediation skills to understand the full attack surface and apply fixes at the correct point in the data flow.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the vulnerable sink.
  - `line_number` (integer, required): Line number of the vulnerable sink.
  - `cwe_id` (string, optional): CWE identifier to guide source/sink heuristics.
  - `code_snippet` (string, optional): The vulnerable code expression.
- **code_context** (optional, JSON object): Output from the `code_context_analyzer` skill. If provided, skip redundant file reading and use the pre-analyzed context (enclosing function, imports, local data flow).
- **repo_root** (required, string): Absolute path to the repository root.
- **max_depth** (optional, integer, default: 10): Maximum number of cross-function or cross-file hops to trace before stopping. Prevents unbounded recursion.

## Steps

1. **Bootstrap from code context.**
   - If `code_context` is provided, extract the enclosing function, its parameters, and the local data flow inputs already identified.
   - If not provided, use `Read` to load the vulnerable file and manually identify the enclosing function and the variables feeding into the vulnerable line (replicate the relevant parts of `code_context_analyzer` Steps 2-5).

2. **Identify the vulnerable sink.**
   - Confirm the specific function call, operation, or expression on the vulnerable line that constitutes the sink.
   - Classify the sink type based on `cwe_id`:
     - CWE-89 (SQL Injection): database query execution (`cursor.execute`, ORM raw queries, etc.)
     - CWE-78 (OS Command Injection): `os.system`, `subprocess.run`, `exec`, shell calls
     - CWE-79 (XSS): template rendering, `innerHTML`, response body writes
     - CWE-22 (Path Traversal): `open()`, `Path()`, file system operations with user input
     - CWE-502 (Deserialization): `pickle.loads`, `yaml.load`, `json.loads` from untrusted sources
     - CWE-798 (Hard-coded Credentials): string literals assigned to password/key/token variables
     - For other CWE IDs or unknown: identify the dangerous operation generically.

3. **Trace backward: sink to source (taint propagation).**
   - Starting from the variables that feed into the sink, trace each one backward:
     a. **Within the enclosing function**: Follow assignments, function return values, and parameter origins.
     b. **To function callers**: If a tainted variable originates from a function parameter, use `Grep` to find all call sites of that function in the repository. Record each caller.
     c. **Across modules**: If the call site is in a different file, use `Read` to load that file and continue tracing from the call site.
     d. **To entry points**: Continue until you reach one of these taint sources:
        - HTTP request parameters (`request.args`, `request.form`, `request.json`, URL path parameters, headers)
        - File reads (uploaded files, configuration files from untrusted sources)
        - Database reads (if data was previously stored from user input)
        - Environment variables or command-line arguments
        - External API responses
        - Deserialized data from untrusted formats
     e. **Depth guard**: Stop tracing a path if `max_depth` hops have been reached without finding a source. Mark the path as `"incomplete"`.

4. **Identify sanitization and validation points.**
   - Along each traced path, look for operations that sanitize, validate, or transform the data:
     - Input validation (regex checks, type casting, allow-list checks)
     - Encoding/escaping functions (HTML escape, URL encode, SQL parameterization)
     - Type conversions that constrain the value (e.g., `int()` on user input)
     - Framework-provided sanitizers (Django's `mark_safe` escape, Rails `sanitize`)
   - Record each sanitization point with its location and whether it is sufficient for the identified CWE.

5. **Trace forward: sink to output (impact analysis).**
   - From the vulnerable sink, trace where the result flows:
     - Is it returned to the caller? If so, trace up the call chain (up to `max_depth`).
     - Is it written to a database, file, HTTP response, or log?
     - Is it passed to another function that may amplify the impact?
   - Record the final destinations to assess blast radius.

6. **Build the complete taint graph.**
   - Assemble all paths from sources to the sink into a directed graph structure.
   - Each node represents a code location (file, line, function).
   - Each edge represents a data transformation or pass-through.

7. **Assess exploitability.**
   - Based on the traced paths, determine:
     - Is there at least one complete path from an untrusted source to the sink with no adequate sanitization? If yes, the vulnerability is likely exploitable.
     - Are all paths sanitized? If yes, the finding may be a false positive.
     - Are some paths sanitized and others not? If yes, note which paths are vulnerable.

## Output Format

Return a single JSON object with the following schema:

```json
{
  "vulnerability_id": "<string or null>",
  "sink": {
    "file_path": "<string: absolute path>",
    "line_number": "<integer>",
    "function_name": "<string>",
    "expression": "<string: the vulnerable expression>",
    "sink_type": "<string: e.g., 'sql_query', 'os_command', 'html_output', 'file_access', 'deserialization', 'other'>"
  },
  "taint_sources": [
    {
      "id": "<string: unique source identifier, e.g., 'src-1'>",
      "file_path": "<string>",
      "line_number": "<integer>",
      "function_name": "<string>",
      "source_type": "<string: 'http_request' | 'file_read' | 'database_read' | 'env_var' | 'cli_arg' | 'api_response' | 'deserialization' | 'unknown'>",
      "expression": "<string: the source expression>",
      "description": "<string: human-readable description of the source>"
    }
  ],
  "taint_paths": [
    {
      "source_id": "<string: references a taint_sources[].id>",
      "status": "<string: 'complete' | 'incomplete'>",
      "is_sanitized": "<boolean: true if adequate sanitization was found along this path>",
      "nodes": [
        {
          "file_path": "<string>",
          "line_number": "<integer>",
          "function_name": "<string>",
          "expression": "<string: the relevant code expression>",
          "node_type": "<string: 'source' | 'transform' | 'sanitizer' | 'passthrough' | 'sink'>",
          "sanitization_detail": "<string or null: description of sanitization applied, if node_type is 'sanitizer'>"
        }
      ]
    }
  ],
  "forward_flow": [
    {
      "file_path": "<string>",
      "line_number": "<integer>",
      "function_name": "<string>",
      "destination_type": "<string: 'http_response' | 'database_write' | 'file_write' | 'log' | 'return_value' | 'other'>",
      "description": "<string>"
    }
  ],
  "exploitability_assessment": {
    "has_unsanitized_path": "<boolean>",
    "unsanitized_path_count": "<integer>",
    "sanitized_path_count": "<integer>",
    "incomplete_path_count": "<integer>",
    "assessment": "<string: 'likely_exploitable' | 'likely_false_positive' | 'partially_sanitized' | 'inconclusive'>",
    "reasoning": "<string: explanation of the assessment>"
  },
  "trace_metadata": {
    "max_depth_used": "<integer>",
    "files_analyzed": ["<string: paths of all files read during tracing>"],
    "total_hops": "<integer: total cross-function/cross-file hops performed>",
    "warnings": ["<string: any warnings encountered during tracing>"]
  }
}
```

### Success Indicator

The output contains at least one entry in `taint_sources` and a valid `sink` object, or the `exploitability_assessment.assessment` field is populated.

### Failure Indicator

The output contains a top-level `"error"` key with a description string.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Vulnerable file not found** | Return error JSON: `{"error": "Vulnerable file not found: <path>"}`. Do not retry. |
| **Enclosing function not determinable** | Trace from the vulnerable line directly using variable assignments. Set a warning in `trace_metadata.warnings`. |
| **No callers found for a function** | Mark that path as `"incomplete"` with status. Continue tracing other paths. |
| **Max depth reached** | Mark the path as `"incomplete"`. Record the last known node. Do not retry with a higher depth automatically. |
| **Circular reference detected** | Stop tracing the circular path. Add a warning: `"Circular reference detected at <file>:<line>"`. Do not loop. |
| **File read failure during cross-file trace** | Skip that file, mark the path as `"incomplete"`, add a warning. Continue with other paths. |
| **Grep returns too many results (>100 matches)** | Narrow the search by adding the function name or class name as context. If still too many, take the first 20 results and add a warning. |
| **Language not supported for deep tracing** | Perform best-effort tracing using text-based pattern matching. Add a warning about reduced accuracy. |

## Constraints

- **Read-only**: This skill MUST NOT modify any files. It is purely analytical.
- **No execution**: Do not execute, compile, or interpret any code from the target repository.
- **Depth limit**: Respect the `max_depth` parameter. The default of 10 hops is a balance between thoroughness and performance. Do not exceed it.
- **Scope**: Trace within the repository defined by `repo_root` only. Do not follow paths into installed third-party packages, virtual environments, or `node_modules` directories.
- **Performance**: Minimize the number of `Grep` calls by using specific patterns. Prefer searching for function names with word boundaries (e.g., `\bfunction_name\b`) rather than broad substrings. Limit `Glob` results to relevant file extensions.
- **No secrets exposure**: If traced data appears to include secrets or credentials, note their presence but redact actual values with `[REDACTED]` in the output.
- **Tool usage**: Use `Read` for file content, `Grep` for cross-file searching, `Glob` for file discovery. Do not use `Bash` for code execution or analysis tools.
- **False positive awareness**: This skill traces data flow but does not make final remediation decisions. The `exploitability_assessment` is advisory. Downstream skills make the final call.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
