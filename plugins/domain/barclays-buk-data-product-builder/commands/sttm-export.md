---
description: Export STTM JSON to formatted Excel workbook
disable-model-invocation: false
---

# /sttm-export — Export STTM to Excel

Re-export an existing STTM JSON file to Excel format matching the template specification.

## Description

Reads the STTM JSON and produces an Excel workbook formatted per `templates/sttm/mapping_spec.md`. Useful for regenerating Excel after manual JSON edits.

## Arguments

- `--input`: Path to STTM JSON. Default: resolved from manifest (see Step 0B)
- `--output`: Path for Excel output. Default: resolved from manifest (see Step 0B)
- `--skip-validation`: Skip pre-export validation (default: false — validation runs first)
- `--provenance`: Also export provenance.xlsx from provenance.json (default: true)
- `--provenance-input`: Path to provenance JSON. Default: resolved from manifest (see Step 0B)
- `--provenance-output`: Path for provenance Excel. Default: resolved from manifest (see Step 0B)

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

### Step 0B — RESOLVE OUTPUT PATHS

If `--input`, `--output`, `--provenance-input`, or `--provenance-output` are not explicitly provided, resolve defaults from the output manifest:

1. Check if `output/.sttm_manifest.json` exists
   - **YES**: read manifest, use paths from `files`:
     - `--input` → `files.sttm_json`
     - `--output` → `files.sttm_xlsx`
     - `--provenance-input` → `files.provenance_json`
     - `--provenance-output` → `files.provenance_xlsx`
   - **NO**: fall back to legacy defaults:
     - `--input` → `output/sttm.json`
     - `--output` → `output/sttm.xlsx`
     - `--provenance-input` → `output/provenance.json`
     - `--provenance-output` → `output/provenance.xlsx`
2. If `--input` is explicitly provided but `--output` is not: derive `--output` by replacing `_sttm.json` with `_sttm.xlsx` in the input path (or `.json` with `.xlsx` as fallback)
3. Log: `"Export paths: {input} → {output}"`

Store resolved paths as variables for use in all subsequent steps:
- `STTM_INPUT` = resolved `--input` path
- `STTM_OUTPUT` = resolved `--output` path
- `PROV_INPUT` = resolved `--provenance-input` path
- `PROV_OUTPUT` = resolved `--provenance-output` path

---

### Pre-Export Validation (unless --skip-validation)

Perform the following validation checks before proceeding with export:

#### 1. Resolve validation paths

```
MANIFEST = "output/.sttm_manifest.json"

If MANIFEST exists:
  STTM_JSON = manifest → files.sttm_json
  VALIDATION_REPORT = manifest → files.validation_report
Else (fallback for pre-manifest output):
  STTM_JSON = "output/sttm.json"
  VALIDATION_REPORT = "output/validation_report.json"
```

#### 2. Verify STTM JSON exists

If `{STTM_JSON}` does not exist:
- STOP with: "❌ {STTM_JSON} not found. Generate STTM first with /sttm-generate"

#### 3. Validate JSON structure

Parse the STTM JSON and verify:
- File is valid JSON (not corrupted or malformed)
- Contains a `"rows"` key at the top level
- `rows` array is non-empty (has at least 1 mapping row)

If any check fails:
- Invalid JSON → STOP: "❌ Invalid JSON in {STTM_JSON}: {parse_error}"
- Missing `rows` key → STOP: "❌ {STTM_JSON} missing 'rows' key"
- Empty rows → STOP: "❌ {STTM_JSON} has 0 mapping rows"

On success, log: "OK: {count} mapping rows found"

#### 4. Check validation report for blockers

If `{VALIDATION_REPORT}` exists:
- Parse the validation report JSON
- Check `validation_results.blocker` count
- If blockers > 0:
  - Log each blocker: "❌ {rule_id}: {message}"
  - STOP: "BLOCKED: {count} blocker(s) found in validation report"
- If blockers == 0:
  - Log: "OK: 0 blockers ({warning_count} warnings)"

If `{VALIDATION_REPORT}` does not exist:
- Log: "⚠️ No validation report found — proceeding without blocker check"

Log: "Pre-export validation PASSED"

### Pre-conditions

Read `python_path` from `output/sttm_session_state.json` — per `agents/refs/python-runtime-contract.md § Invocation Pattern`.
If `python_path == null`: HALT with error:
```
⛔ Python required for Excel export. /sttm-export cannot run without Python + openpyxl.
To fix: ensure 'python' is on PATH, or set PYTHON_PATH. Then re-run /sttm-init.
```

### Export Process

1. Read `{STTM_INPUT}` — extract rows, source_volumetrics, and _meta
2. Read classification from `_meta.classification` (informational only — does not affect sheet selection)
3. Load `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` for column order, sheet specifications, and formatting
4. Execute Excel generation via Bash + openpyxl (built from scratch — no template file dependency):

```python
{python_path} -c "
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import json
import re

# Read STTM JSON (path passed via sys.argv[1])
import sys
sttm_input = sys.argv[1] if len(sys.argv) > 1 else 'output/sttm.json'
sttm_output = sys.argv[2] if len(sys.argv) > 2 else 'output/sttm.xlsx'
with open(sttm_input) as f:
    sttm = json.load(f)

# --- Normalize Business Logic: convert legacy formats to compact aliased newline format ---

def make_alias(table_name):
    \"\"\"Generate short alias from table name: mortgage_account -> ma\"\"\"
    parts = table_name.strip().split('_')
    if len(parts) == 1:
        return table_name[:3].lower()
    return ''.join(p[0] for p in parts if p).lower()

def normalize_business_logic(value):
    \"\"\"Convert legacy ' / ' or verbose newline format to compact newline-separated aliased format.\"\"\"
    if not value or 'Driver Table:' not in value:
        return value

    # Split on ' / ' or newline to get sections
    if ' / ' in value:
        parts = [p.strip() for p in value.split(' / ')]
    elif '\\n' in value:
        parts = [p.strip() for p in value.split('\\n')]
    else:
        return value

    # Check if already in compact aliased format (Join N: TYPE JOIN ...)
    for part in parts:
        if re.match(r'Join \d+:\s*(LEFT|INNER|RIGHT|FULL)\s+JOIN', part):
            return '\\n'.join(parts)

    # Parse sections from verbose/legacy format
    driver_table = ''
    driver_conditions = ''
    joins = {}
    value_expr = ''

    for part in parts:
        if part.startswith('Driver Table:'):
            driver_table = part.split(':', 1)[1].strip()
        elif part.startswith('Driver Conditions:'):
            driver_conditions = part.split(':', 1)[1].strip()
        elif re.match(r'Join (\d+) Table:', part):
            m = re.match(r'Join (\d+) Table:\s*(.*)', part)
            num = m.group(1)
            joins.setdefault(num, {})['table'] = m.group(2).strip()
        elif re.match(r'Join (\d+) Type:', part):
            m = re.match(r'Join (\d+) Type:\s*(.*)', part)
            joins.setdefault(m.group(1), {})['type'] = m.group(2).strip()
        elif re.match(r'Join (\d+) Conditions:', part):
            m = re.match(r'Join (\d+) Conditions:\s*(.*)', part)
            joins.setdefault(m.group(1), {})['on_cond'] = m.group(2).strip()
        elif re.match(r'Table(\d+) Conditions:', part):
            m = re.match(r'Table(\d+) Conditions:\s*(.*)', part)
            tc = m.group(2).strip()
            if tc and tc != '[]':
                joins.setdefault(m.group(1), {})['table_cond'] = tc
        elif part.startswith('Value:'):
            value_expr = part.split(':', 1)[1].strip()
        elif re.match(r'Join \d+:', part):
            # Legacy compact without aliases (Join 1: TABLE ON ...) — pass through
            return '\\n'.join(parts)

    if not driver_table:
        return value

    # Build unique aliases
    aliases = {}
    dt_clean = re.sub(r'\s*\\(.*?\\)\s*$', '', driver_table)
    aliases[dt_clean] = make_alias(dt_clean)

    for num in sorted(joins.keys(), key=int):
        jt = re.sub(r'\s*\\(.*?\\)\s*$', '', joins[num].get('table', ''))
        if jt and jt not in aliases:
            alias = make_alias(jt)
            base_alias = alias
            suffix = 1
            tparts = jt.split('_')
            while alias in aliases.values():
                if suffix <= len(tparts):
                    alias = base_alias + tparts[min(suffix, len(tparts)-1)][0]
                else:
                    alias = base_alias + str(suffix)
                suffix += 1
            aliases[jt] = alias

    # Replace full table names with aliases in expressions
    def apply_aliases(text):
        for table, alias in sorted(aliases.items(), key=lambda x: -len(x[0])):
            text = text.replace(f'{table}.', f'{alias}.')
        return text

    # Build compact output lines
    lines = []
    da = aliases[dt_clean]
    lines.append(f'Driver Table: {dt_clean} ({da})')

    if driver_conditions and driver_conditions != '[]':
        lines.append(f'Driver Conditions: {apply_aliases(driver_conditions)}')

    for num in sorted(joins.keys(), key=int):
        j = joins[num]
        jt = re.sub(r'\s*\\(.*?\\)\s*$', '', j.get('table', ''))
        ja = aliases.get(jt, make_alias(jt))
        jtype = j.get('type', 'LEFT')
        on_cond = apply_aliases(j.get('on_cond', ''))
        line = f'Join {num}: {jtype} JOIN {jt} ({ja}) ON {on_cond}'
        if j.get('table_cond'):
            line += f' {apply_aliases(j[\"table_cond\"])}'
        lines.append(line)

    lines.append(f'Value: {apply_aliases(value_expr)}')
    return '\\n'.join(lines)

# Build workbook from scratch
wb = openpyxl.Workbook()

# --- Mapping Sheet ---
ws = wb.active
ws.title = 'Mapping'
ws.sheet_properties.tabColor = '4472C4'

MAPPING_HEADERS = [
    'Target Database', 'Target Table', 'Target Column Name',
    'Target Column Definition/Description', 'Target Column Datatype',
    'Target Column Null Flag', 'Source Database', 'Source Table Name',
    'Source Column Name', 'Business Logic/Transformation Logic',
    'Additional Context', 'Target Table description',
    'Transformation Type', 'Default Value', 'Target Table Type', 'Key Column'
]
MAPPING_WIDTHS = [25, 22, 28, 40, 18, 8, 22, 22, 28, 55, 50, 50, 20, 15, 18, 12]

header_fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
header_font = Font(bold=True, size=11)
header_align = Alignment(wrap_text=True, vertical='center')
data_align = Alignment(wrap_text=True, vertical='top')

# Write mapping headers (Row 1)
for col_idx, header in enumerate(MAPPING_HEADERS, 1):
    cell = ws.cell(row=1, column=col_idx, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align

for i, width in enumerate(MAPPING_WIDTHS, 1):
    ws.column_dimensions[get_column_letter(i)].width = width

ws.freeze_panes = 'A2'

# Column order (A-P) maps to JSON keys
COL_MAP = [
    'target_database', 'target_table', 'target_column_name',
    'target_column_description', 'target_column_datatype', 'target_column_null_flag',
    'source_database', 'source_table_name', 'source_column_name',
    'business_logic', 'additional_context', 'target_table_description',
    'transformation_type', 'default_value', 'target_table_type', 'key_column'
]

# Write mapping rows starting at Row 2
for row_idx, row_data in enumerate(sttm['rows'], start=2):
    for col_idx, key in enumerate(COL_MAP, start=1):
        cell_value = row_data.get(key, '')
        if key == 'business_logic':
            cell_value = normalize_business_logic(cell_value)
        cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)
        cell.alignment = data_align

# --- Source Volumetrics Sheet ---
vol_ws = wb.create_sheet('Source Volumetrics')
vol_ws.sheet_properties.tabColor = '00B050'

VOL_HEADERS = [
    'Source Database', 'Source Table', 'Estimated Rows', 'Estimated Size (GB)',
    'Daily Increment Rows', 'Daily Increment Size (GB)', 'Primary Key',
    'Partition Key', 'Table Type', 'Broadcast Hint'
]
VOL_WIDTHS = [25, 28, 18, 22, 22, 26, 32, 20, 18, 16]

# Write volumetrics headers (Row 1)
for col_idx, header in enumerate(VOL_HEADERS, 1):
    cell = vol_ws.cell(row=1, column=col_idx, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_align

for i, width in enumerate(VOL_WIDTHS, 1):
    vol_ws.column_dimensions[get_column_letter(i)].width = width

vol_ws.freeze_panes = 'A2'

VOL_COL_MAP = [
    'source_database', 'source_table', 'estimated_rows', 'estimated_size_gb',
    'daily_increment_rows', 'daily_increment_size_gb', 'primary_key',
    'partition_key', 'table_type', 'broadcast_hint'
]

# Write volumetrics rows starting at Row 2
# When writing broadcast_hint to Excel, convert boolean true → "Y" and false → "N".
for row_idx, vol_data in enumerate(sttm.get('source_volumetrics', []), start=2):
    for col_idx, key in enumerate(VOL_COL_MAP, start=1):
        cell_value = vol_data.get(key, '')
        if key == 'broadcast_hint' and isinstance(cell_value, bool):
            cell_value = 'Y' if cell_value else 'N'
        cell = vol_ws.cell(row=row_idx, column=col_idx, value=cell_value)
        cell.alignment = data_align

# Save — output has exactly 2 sheets: Mapping + Source Volumetrics
wb.save(sttm_output)
print(f'Excel exported: {sttm_output} ({len(sttm[\"rows\"])} rows on Mapping, 2 sheets)')
"
```

### Provenance Export (unless --provenance=false)

If provenance JSON exists and is valid, generate provenance Excel (paths resolved from Step 0B):

```python
{python_path} -c "
import openpyxl
import json
import re
import os
import sys

prov_input = sys.argv[1] if len(sys.argv) > 1 else 'output/provenance.json'
prov_output = sys.argv[2] if len(sys.argv) > 2 else 'output/provenance.xlsx'

if not os.path.exists(prov_input):
    print(f'Skipping provenance export: {prov_input} not found')
    exit(0)

with open(prov_input) as f:
    prov = json.load(f)

wb = openpyxl.Workbook()

# Sheet 1: Field Provenance
ws1 = wb.active
ws1.title = 'Field Provenance'
ws1.sheet_properties.tabColor = '4472C4'

headers_1 = ['Target Table', 'Target Column', 'Field Name', 'Value',
             'Confidence', 'Method', 'Evidence', 'Source Priority',
             'Artifact Reference', 'Business Rule Reference']
for col_idx, h in enumerate(headers_1, 1):
    cell = ws1.cell(row=1, column=col_idx, value=h)
    cell.font = openpyxl.styles.Font(bold=True)

row_idx = 2
br_pattern = re.compile(r'BR-\d+')

for entry in prov.get('field_provenance', prov.get('rows', [])):
    target_table = entry.get('target_table', '')
    target_column = entry.get('target_column', '')
    for field_name, field_data in entry.get('fields', {}).items():
        if isinstance(field_data, dict):
            prov_data = field_data.get('provenance', field_data)
            value = str(field_data.get('value', prov_data.get('value', '')))[:200]
            confidence = prov_data.get('confidence', '')
            method = prov_data.get('method', '')
            evidence = prov_data.get('evidence', prov_data.get('source_of_evidence', ''))
            source_priority = prov_data.get('source_priority', '')
            artifact = prov_data.get('artifact', '')
            br_refs = ','.join(sorted(set(br_pattern.findall(str(evidence) + ' ' + str(value)))))
        else:
            continue

        ws1.cell(row=row_idx, column=1, value=target_table)
        ws1.cell(row=row_idx, column=2, value=target_column)
        ws1.cell(row=row_idx, column=3, value=field_name)
        ws1.cell(row=row_idx, column=4, value=value)
        ws1.cell(row=row_idx, column=5, value=confidence)
        ws1.cell(row=row_idx, column=6, value=method)
        ws1.cell(row=row_idx, column=7, value=str(evidence)[:500])
        ws1.cell(row=row_idx, column=8, value=source_priority)
        ws1.cell(row=row_idx, column=9, value=artifact)
        ws1.cell(row=row_idx, column=10, value=br_refs)
        row_idx += 1

field_prov_count = row_idx - 2

# Sheet 2: Business Rules
ws2 = wb.create_sheet('Business Rules')
ws2.sheet_properties.tabColor = 'ED7D31'

headers_2 = ['Rule ID', 'Target Table', 'Affected Columns', 'Rule Description', 'Source Document']
for col_idx, h in enumerate(headers_2, 1):
    cell = ws2.cell(row=1, column=col_idx, value=h)
    cell.font = openpyxl.styles.Font(bold=True)

# Extract BR references per table from provenance
br_map = {}  # {(rule_id, target_table): set(columns)}
for entry in prov.get('field_provenance', prov.get('rows', [])):
    target_table = entry.get('target_table', '')
    target_column = entry.get('target_column', '')
    for field_name, field_data in entry.get('fields', {}).items():
        if isinstance(field_data, dict):
            prov_data = field_data.get('provenance', field_data)
            evidence = str(prov_data.get('evidence', prov_data.get('source_of_evidence', '')))
            value = str(field_data.get('value', prov_data.get('value', '')))
            for br in br_pattern.findall(evidence + ' ' + value):
                key = (br, target_table)
                if key not in br_map:
                    br_map[key] = set()
                br_map[key].add(target_column)

row_idx = 2
for (rule_id, target_table), columns in sorted(br_map.items()):
    ws2.cell(row=row_idx, column=1, value=rule_id)
    ws2.cell(row=row_idx, column=2, value=target_table)
    ws2.cell(row=row_idx, column=3, value=', '.join(sorted(columns)))
    ws2.cell(row=row_idx, column=4, value='')  # Populated from design docs if available
    ws2.cell(row=row_idx, column=5, value='')  # Populated from design docs if available
    row_idx += 1

br_count = row_idx - 2

wb.save(prov_output)
print(f'Provenance exported: {prov_output} ({field_prov_count} field entries, {br_count} BR references)')
"
```

### Post-Export — UPDATE SESSION STATE

If `output/sttm_session_state.json` exists, update the `output_files` block:
```json
{
  "sttm_json": "<STTM_JSON path>",
  "sttm_xlsx": "<STTM_OUTPUT path>",
  "provenance_json": "<PROV_INPUT path>",
  "provenance_xlsx": "<PROV_OUTPUT path>",
  "validation_report": "<VAL_REPORT path>"
}
```

### Post-Export — REPORT

Report to user:
- Scenario classified: {scenario}
- Output sheets: Mapping + Source_Volumetrics (2 sheets only)
- Mapping rows written: {count}
- Source Volumetrics rows: {count}
- STTM output: {STTM_OUTPUT}
- Provenance output: {PROV_OUTPUT} (Field Provenance + Business Rules sheets)

## JSON Export Content

**extracted_constraints inclusion:**
When exporting sttm.json, include the `extracted_constraints` section if present. This section is consumed by DE's `/parse-mapping` to populate `extracted_predicates.json` without lossy regex re-extraction.

**source_column_allowlist inclusion:**
When exporting sttm.json, include the `source_column_allowlist` section if present. This section is consumed by DE's `/gen-transform` STEP 0.4 to validate column references without re-extracting from mapping_parsed.json.

**structured_transformation inclusion:**
When exporting sttm.json, include the `structured_transformation` object on each mapping row if present. This per-row JSON object is built by the sttm-row-generator-agent directly from lineage data and provides a machine-readable representation of the transformation logic. DE's `/parse-mapping` prefers this object over regex extraction from `business_logic` text — it is the authoritative structured representation. The `structured_transformation` field is JSON-only (it is NOT written to the Excel mapping sheet — Excel has only the 16 canonical text columns).

**File I/O metadata inclusion (`_meta` block):**
When `io_mode` is not `"table"` (i.e., the session involves file-based sources or targets), the exported `_meta` block in the STTM JSON must include:
- `io_mode`: the classified I/O mode (`"file"` or `"hybrid"`)
- `source_io`: file source configuration — one entry per logical file source (e.g., `{sources: [{logical_name: "customer_extract", storage_path: "s3://raw-bucket/data/customer_extract/", format: "parquet"}]}`). Present when any source uses `(file:parquet)`. `logical_name` is derived from storage_path basename.
- `target_io`: file target configuration (e.g., `{logical_name: "customer_events_clean", format: "parquet", write_mode: "overwrite"}`). Present when the target table name contains `(file:parquet)` suffix.

When `io_mode = "table"` (default), these fields are omitted from `_meta` for backward compatibility.

## Important Rules

- Row 1 = headers (per templates/sttm/mapping_spec.md). NO instructions row. Data starts at Row 2.
- Output has exactly 2 sheets: "Mapping" + "Source Volumetrics" (built from scratch)
- Tab colors: Blue (#4472C4) for Mapping, Green (#00B050) for Source Volumetrics
- Column order MUST match specification exactly (A=Target Database through P=Key Column)
- All 16 columns must be present even if some values are empty strings
- Additional Context (column K) populated ONLY in first data row; empty for all subsequent rows
- Target Table Description (column L) populated ONLY in first data row; empty for all subsequent rows
- Provenance data (BR references, confidence, evidence) is NEVER in sttm.xlsx — it goes to provenance.xlsx
- File sources in Source Volumetrics: rows with `source_database = (file:parquet)` and `source_table = {logical_name}` are valid entries in the Source Volumetrics sheet. They follow the same 10-column schema — volumetric fields (estimated rows/size) describe the file source dimensions.
- No Excel format changes are needed for file I/O support — the 16-column mapping sheet and 10-column volumetrics sheet remain unchanged. File I/O metadata (`io_mode`, `source_io`, `target_io`) lives in the JSON `_meta` block only.
