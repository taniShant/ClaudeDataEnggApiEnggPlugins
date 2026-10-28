---
name: parsing
description: WIZ report parsing (Wiz JSON), threat model parsing (Markdown), deduplication, and vulnerability normalization
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/parsing/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Report Parsing & Normalization
## Quick Start

This skill provides parsing logic for extracting vulnerability data from WIZ reports and threat models.

```
# Loaded by detox-parser-agent during the Parse Reports phase.
# Normalises findings from Wiz JSON and Markdown threat model formats.
```



## Purpose

Defines how to parse vulnerability reports from different sources (Wiz JSON, threat model Markdown) into a normalized `Vulnerability` data model, and how to deduplicate findings across sources.

---

## Vulnerability Data Model

Every parsed finding MUST conform to this schema:

```json
{
  "id": "string (unique identifier)",
  "cwe_id": "string|null (CWE-XXX format)",
  "title": "string (finding title)",
  "description": "string (detailed description)",
  "severity": "critical|high|medium|low|info",
  "source": "wiz|threat_model",
  "file_path": "string|null (relative path)",
  "line_number": "integer|null",
  "code_snippet": "string|null",
  "remediation_type": "code_fix|infra_config|dependency|manual",
  "tool_name": "string (wiz|threat_model_report)",
  "rule_id": "string|null",
  "confidence": "float 0.0-1.0"
}
```

---

## Wiz WIZ JSON Report Parsing

### Step 1: Locate Findings Array

Check these JSON locations in order:
1. `result[]` or `results[]`
2. `data.results[]`
3. `findings[]`
4. Top-level array (file is a JSON array)
5. `issues[]`

If none found → return empty array with warning listing top-level keys.

### Step 2: Field Extraction (Priority Order)

| Field | Extraction Locations |
|-------|---------------------|
| **id** | `id` → `finding_id` → `ruleId` (prefix: `wiz-{value}`) |
| **cwe_id** | `cwe` → `cweId` → `rule.cwe` → tags matching `CWE-\d+` |
| **title** | `title` → `name` → `rule.name` → `rule.title` → `summary` |
| **description** | `description` → `details` → `rule.description` → `message` |
| **severity** | `severity` → `risk` → `priority` → `rule.severity` |
| **file_path** | `filePath` → `file` → `location.path` → `resource.filePath` → `sourceLocation.file` |
| **line_number** | `lineNumber` → `line` → `location.startLine` → `sourceLocation.line` |
| **code_snippet** | `codeSnippet` → `snippet` → `code` → `sourceLocation.snippet` |
| **confidence** | `confidence` → `certainty` |
| **rule_id** | `ruleId` → `rule.id` → `ruleID` → `checkId` |

### Step 3: Normalization Rules

**CWE ID normalization:**
- `89` → `CWE-89`
- `"CWE-89"` → `CWE-89`
- `"cwe-89"` → `CWE-89`
- Non-numeric or zero → `null`

**Severity mapping (case-insensitive):**
| Wiz Value | Canonical |
|-----------|-----------|
| CRITICAL | critical |
| HIGH | high |
| MEDIUM | medium |
| LOW | low |
| INFORMATIONAL | info |
| Unknown → default | medium |

**Confidence normalization:**
- `"high"` → 0.9
- `"medium"` → 0.7
- `"low"` → 0.5
- Percentage → divide by 100
- 0.0-1.0 float → use directly
- Not found → default 0.8

### Step 4: Remediation Type Classification

Based on `file_path`:

| Pattern | Type |
|---------|------|
| `*.tf`, `*.tfvars`, `Dockerfile*`, `docker-compose*`, k8s/helm/deploy YAML | `infra_config` |
| `requirements.txt`, `package.json`, `pom.xml`, `go.mod`, `*.lock`, `Gemfile` | `dependency` |
| `.py`, `.java`, `.js`, `.ts`, `.cs`, `.go`, `.rb`, `.c`, `.cpp`, `.rs`, `.php`, `.kt` | `code_fix` |
| No file path, or tagged manual-review/design/architecture | `manual` |
| Ambiguous | default to `code_fix` |

### Error Handling

- File not JSON → error
- Unknown structure → empty array + warning with top-level keys
- Missing required fields → include with nulls for optional
- Duplicate IDs → append suffix: `-2`, `-3`
- Malformed CWE → set to null
- Unknown severity → default to medium, note original in description

---

## Threat Model Markdown Report Parsing

### Step 1: Identify Finding Sections

Look for structural patterns:
- Headers with IDs: `## ATK-INT-01: Title`, `### Finding 1: Title`
- Tables: `| ID | Title | Severity | CWE |`
- Numbered lists with metadata

### Step 2: Extract Fields from Each Section

For each identified finding:

1. **id**: Extract from header (e.g., `ATK-INT-01`) or table row
2. **cwe_id**: Search for `CWE-\d+` or `CWE \d+` patterns in text
3. **title**: First line/header of the finding section
4. **description**: Full body text of the finding section
5. **severity**: Look for keywords: Critical, High, Medium, Low (case-insensitive)
6. **file_path**: Look for file references in code blocks or inline code
7. **line_number**: Look for line number references
8. **remediation_type**: Classify from description content:
   - "infrastructure", "config", "deployment", "cloud", "network" → `infra_config`
   - "dependency", "library", "package", "upgrade", "version" → `dependency`
   - Code-level indicators (function names, line refs, code blocks) → `code_fix`
   - Ambiguous → `manual`

### Step 3: Handle Various Formats

**Table format:**
```markdown
| ID | Title | Severity | CWE |
|----|-------|----------|-----|
| ATK-INT-01 | SQL Injection in login | Critical | CWE-89 |
```

**Header format:**
```markdown
## ATK-INT-01: SQL Injection in Login API

**Severity**: Critical
**CWE**: CWE-89
**File**: src/auth/login.py:42

Description text...
```

**List format:**
```markdown
1. **SQL Injection** (CWE-89, Critical) - src/auth/login.py line 42
```

### Error Handling

- No structured findings → attempt freeform extraction, return best-effort
- Ambiguous severity → default to medium
- No CWE reference → set to null
- No file reference → set file_path to null

---

## Deduplication

### When to Deduplicate

When merging findings from multiple sources (WIZ + threat model).

### Deduplication Rules

Two findings are duplicates if ALL match:
1. `cwe_id` is the same (and not null)
2. `file_path` is the same (and not null)
3. `line_number` is within ±5 lines (to account for report differences)

### Merge Strategy

When duplicates found:
- Keep the finding with more detail (longer description, code snippet present)
- Merge source info: note both sources in the description
- Use higher confidence of the two
- Use higher severity of the two
- Prefix ID with source: keep both IDs in metadata

---

## Output Requirements

- Output MUST be valid JSON parseable by `json.loads()`
- Each `id` MUST be unique within the output array
- `severity` MUST be one of: `critical`, `high`, `medium`, `low`, `info`
- `remediation_type` MUST be one of: `code_fix`, `infra_config`, `dependency`, `manual`
- Do NOT truncate large reports — process all findings
- Do NOT fabricate findings not present in the source report
- Do NOT re-score severity — apply the mapping as defined

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
