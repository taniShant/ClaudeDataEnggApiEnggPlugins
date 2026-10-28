---
name: code-context-analyzer
description: "Code Context Analyzer — Analyze the code context surrounding a reported vulnerability to build a rich understanding of the affected code structure. This skill reads the affected file, examines the enclosing function, class, "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/analysis/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Code Context Analyzer
## Quick Start

This skill provides code analysis capabilities for understanding vulnerability context and data flow.

```
# Loaded by detox-fix-agent before applying a fix to understand the code context.
# Traces data flow and identifies the vulnerable pattern in context.
```



## Purpose

Analyze the code context surrounding a reported vulnerability to build a rich understanding of the affected code structure. This skill reads the affected file, examines the enclosing function, class, and module, traces imports and local data flow, and produces a structured JSON context object that downstream skills (remediation, classification, data flow tracing) can consume to make informed decisions.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing at minimum:
  - `file_path` (string, required): Absolute or repo-relative path to the affected file.
  - `line_number` (integer, required): The 1-based line number where the vulnerability was reported.
  - `cwe_id` (string, optional): CWE identifier (e.g., `CWE-89`).
  - `code_snippet` (string, optional): The snippet flagged by the scanner.
  - `rule_id` (string, optional): The WIZ rule that triggered the finding.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.

## Steps

1. **Locate the affected file.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If the file does not exist, report an error immediately (see Error Handling).

2. **Extract the vulnerable line and surrounding context.**
   - Read a window of +/- 50 lines around `vulnerability.line_number` to capture sufficient context.
   - Identify the exact line matching the `code_snippet` if provided; if the line number and snippet disagree, prefer the snippet match and note the discrepancy.

3. **Identify the enclosing scope.**
   - Determine the innermost function or method that contains the vulnerable line.
   - Determine the enclosing class (if any).
   - Record the function signature (name, parameters, return type annotation if present).
   - Record the class name and its base classes.

4. **Analyze imports and dependencies.**
   - Collect all import statements at the top of the file.
   - Identify which imports are used on or near the vulnerable line (within the enclosing function).
   - Flag any imports from third-party packages versus standard library versus local project modules.
   - Use `Grep` with the import names against the repository to locate their definitions when they are local modules.

5. **Map local data flow within the enclosing function.**
   - Identify all variables that flow into the vulnerable expression as arguments or operands.
   - For each variable, trace backward within the function to find its origin:
     - Is it a function parameter?
     - Is it derived from another function call? If so, which?
     - Is it a literal/constant?
   - Identify where the result of the vulnerable expression flows to (return value, assignment, passed to another call).

6. **Detect related patterns in the same file.**
   - Use `Grep` within the file to find other occurrences of the same vulnerable pattern (e.g., same function call, same string formatting approach).
   - Count how many similar patterns exist in the file to estimate remediation scope.

7. **Identify test coverage hints.**
   - Use `Glob` to search for test files that reference the affected file name or the enclosing function/class name (patterns: `**/test_*.py`, `**/*_test.py`, `**/*_spec.*`).
   - Note whether test files exist (do not read their full content, just confirm presence).

8. **Assemble the structured context.**
   - Compose the output JSON object as specified in the Output Format section.

## Output Format

Return a single JSON object with the following schema:

```json
{
  "vulnerability_id": "<string: the vulnerability id if provided>",
  "file_path": "<string: absolute path to the affected file>",
  "language": "<string: detected programming language, e.g., python, javascript, java>",
  "line_number": "<integer: confirmed line number of the vulnerability>",
  "line_number_adjusted": "<boolean: true if the line number was corrected from the original input>",
  "vulnerable_code": "<string: the exact vulnerable line or expression>",
  "context_window": {
    "start_line": "<integer>",
    "end_line": "<integer>",
    "code": "<string: the code within the context window>"
  },
  "enclosing_function": {
    "name": "<string or null>",
    "signature": "<string: full signature including parameters>",
    "start_line": "<integer>",
    "end_line": "<integer>",
    "decorators": ["<string: decorator names if any>"]
  },
  "enclosing_class": {
    "name": "<string or null>",
    "base_classes": ["<string>"],
    "start_line": "<integer>",
    "end_line": "<integer>"
  },
  "imports": {
    "standard_library": ["<string: import statements>"],
    "third_party": ["<string: import statements>"],
    "local": ["<string: import statements>"]
  },
  "relevant_imports": ["<string: imports directly used in the vulnerable expression>"],
  "data_flow": {
    "inputs": [
      {
        "variable": "<string: variable name>",
        "origin": "<string: 'parameter' | 'function_call' | 'literal' | 'attribute' | 'unknown'>",
        "origin_detail": "<string: e.g., function name called, parameter position>"
      }
    ],
    "outputs": [
      {
        "variable": "<string: variable or expression receiving the result>",
        "destination": "<string: 'return' | 'assignment' | 'function_argument' | 'unused'>",
        "destination_detail": "<string: e.g., function name called with the result>"
      }
    ]
  },
  "similar_patterns": {
    "count": "<integer: number of similar vulnerable patterns in the same file>",
    "locations": ["<integer: line numbers of similar patterns>"]
  },
  "test_files": ["<string: paths to related test files, if found>"],
  "metadata": {
    "file_total_lines": "<integer>",
    "file_size_bytes": "<integer or null>",
    "cwe_id": "<string or null>",
    "rule_id": "<string or null>"
  }
}
```

### Success Indicator

The output JSON contains a non-null `enclosing_function.name` or at minimum a valid `context_window.code` block. If both are null/empty, the analysis has failed.

### Failure Indicator

The output JSON has an `"error"` top-level key with a description string, and all other fields are either null or omitted.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON: `{"error": "File not found: <path>", "file_path": "<path>"}`. Do not retry. |
| **Line number out of range** | Clamp to file bounds, set `line_number_adjusted` to true, and add a warning in `metadata`. Proceed with analysis. |
| **Snippet does not match line** | Search the entire file for the snippet. If found, update `line_number` and set `line_number_adjusted` to true. If not found, proceed with the original line number and add a warning. |
| **Binary or non-text file** | Return error JSON: `{"error": "Binary or unsupported file format", "file_path": "<path>"}`. Do not retry. |
| **Language not recognized** | Set `language` to `"unknown"` and proceed. Scope detection may be less accurate; note this in `metadata`. |
| **Enclosing function cannot be determined** | Set `enclosing_function.name` to null. Still return the context window and all other available data. |
| **Grep/Glob tool failures** | Log the failure, set affected fields to empty arrays or null, and continue with remaining steps. Do not abort the entire analysis. |

## Constraints

- **Read-only**: This skill MUST NOT modify any files. It is purely analytical.
- **No execution**: Do not execute, compile, or run any code from the target repository.
- **Scope limit**: Analyze only the single file identified by `file_path`. Cross-file analysis is the responsibility of the `data_flow_tracer` skill.
- **Performance**: Limit Grep searches to the repository root. Do not perform unbounded recursive searches outside the repo. Keep Glob patterns specific (e.g., include file extensions).
- **Output size**: The `context_window.code` field should contain at most 100 lines. If the enclosing function exceeds 100 lines, truncate and note truncation in `metadata`.
- **No secrets exposure**: If the file appears to contain secrets (API keys, passwords, tokens), redact them in the output with `[REDACTED]`.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery. Do not use `Bash` to run code analysis tools.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
