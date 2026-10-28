---
name: xray-integration
description: >
  Xray test ingestion in any form — Jira REST API (test plan / execution),
  device UI feature files (Gherkin with @JiraXrayTest_ tags), NonUI gateway
  feature files (BMB-* IDs), Jira XLS/HTML exports, and CSV. Provides tag
  extraction patterns, auth, endpoint reference, and auto-detection logic.
user-invocable: false
owner: Barclays BUK Digital Channels
review-trigger: Jira Xray REST API version change, or new Xray input source added
status: production
---

## Source Attribution

**Source:** TRACER v1.1.0 internal — Jira Xray REST API documentation + Barclays JIRA instance  
**Owner:** Barclays BUK Digital Channels  
**Review trigger:** Jira REST API version change, Barclays Jira instance migration, or new input format added  
**Status:** Production

---

## Quick Start

```bash
# Option A — Jira test plan ID
curl -s -H "Authorization: Bearer ${JIRA_PAT}" \
  "${JIRA_BASE_URL}/rest/raven/1.0/api/testplan/EANDBLUE-1234/test" \
  | python3 -I -c "
import sys, json
for t in json.load(sys.stdin):
    print(t['key'], t.get('summary',''))
"

# Option B — Device UI feature file (most informative input)
python3 -I -c "
import re, sys
content = open('Feature/ADB/Per_ProductHub2.0_main_adb.feature').read()
lines = content.splitlines()
tests = []
for i, line in enumerate(lines):
    m = re.search(r'@JiraXrayTest_([A-Z]+-\d+|\d+)', line)
    if m:
        xid = m.group(1)
        if not xid.startswith(('EANDBLUE-','BMB-','EST-')):
            xid = 'EANDBLUE-' + xid  # bare numeric → apply project prefix
        for j in range(i+1, min(i+5, len(lines))):
            if 'Scenario' in lines[j]:
                title = re.sub(r'\s*Scenario[:\s]*', '', lines[j]).strip()
                tests.append({'xray_id': xid, 'summary': title, 'source': 'feature_file'})
                break
for t in tests:
    print(t['xray_id'], t['summary'][:80])
print(f'Total: {len(tests)}')
"

# Option C — Jira XLS export (HTML-disguised)
python3 -I -c "
from html.parser import HTMLParser
import sys

class XrayHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.headers = []
        self.rows = []
        self.current_row = []
        self.current_cell = ''
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = ''
        elif tag == 'tr':
            self.current_row = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th'):
            self.current_row.append(self.current_cell.strip())
            self.in_cell = False
        elif tag == 'tr':
            if self.current_row:
                if not self.headers:
                    self.headers = [h.lower() for h in self.current_row]
                else:
                    self.rows.append(dict(zip(self.headers, self.current_row)))

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

parser = XrayHTMLParser()
parser.feed(open(sys.argv[1]).read())
id_col = next((c for c in parser.headers if c in ['key','id','xray id','issue key']), None)
name_col = next((c for c in parser.headers if c in ['summary','name','title']), None)
for row in parser.rows:
    if id_col and row.get(id_col):
        print(row[id_col], row.get(name_col,'')[:60])
" xray-export.xls
```

---

## Core Concept 1: Xray REST API Endpoints

The Barclays Jira instance uses the Raven (Xray) REST API v1.

### Test Plan Tests

```
GET /rest/raven/1.0/api/testplan/{plan_key}/test
```

Response — array of test records:
```json
[
  {
    "id": 12345,
    "key": "EANDBLUE-8254",
    "summary": "User sees PREMIER upgrade only when BLUE removed from config",
    "self": "https://estjira.barcapint.com/rest/api/2/issue/12345",
    "status": "PASS"
  }
]
```

### Test Execution Tests

```
GET /rest/raven/1.0/api/testexec/{exec_key}/test
```

Response — same schema as test plan response.

### Authentication

All requests require Bearer token from `JIRA_PAT`:
```bash
-H "Authorization: Bearer ${JIRA_PAT}"
```

Base URL from `JIRA_BASE_URL`: `https://estjira.barcapint.com`

Do NOT use Basic Auth — only Bearer PAT is supported.

---

## Core Concept 2: Feature File Scanning — Device UI and NonUI Gateway

Feature files are the richest Xray input source. They contain actual scenario text, not just IDs, which enables semantic classification of tests (routing, error handling, navigation, content visibility, vs genuinely device-specific).

TRACER handles two distinct feature file patterns found in Barclays BUK:

### Pattern A — Device UI feature files

Used by mobile automation test repos (e.g. `tba-connectedPlatformWS-features`). Tests are tagged with **per-scenario** `@JiraXrayTest_` tags:

```gherkin
@Test_Id_Per_ProductHub2.0_main_adb_TC_47 @JiraXrayTest_EANDBLUE-5130
Scenario: Verify user is able to navigate back to Bapp homepage from New Product Hub2.0
  And user sees "Home"
  And user taps "Products" icon
  And user sees "page-header-Products" title
  ...
  And user taps "Home"
  And user waits for "Your accounts" to appear
```

Tags to extract: `@JiraXrayTest_EANDBLUE-*` (or bare numeric, e.g. `@JiraXrayTest_5147`).

Bare numeric IDs have no project prefix — apply the expected prefix from `--xray-project` flag or infer from surrounding `@EANDBLUE-*` Feature-level tag:
```python
# Bare numeric → apply project prefix
xid = m.group(1)
if not re.match(r'^[A-Z]+-\d+$', xid):
    xid = f'{DEFAULT_PROJECT}-{xid}'  # e.g. EANDBLUE-5147
```

### Pattern B — NonUI gateway feature files

Used by `tba-release-nonui-features`. These test the full backend API through the real gateway without a device. Tests carry the same `@JiraXrayTest_` tag but with BMB-* IDs:

```gherkin
@Test_Id_Per_ProductHub_main_TC_01_NonUI @NonUI_GatewayE2E @JiraXrayTest_BMB-1257623
Scenario: Verify the Product hub page and more services for essential customer.
  Given user registers and login with details ...
  Then user calls opcode "SPR01" with properties ...
    | apiAlias | x-digi-products-hub-mgt |
    | path     | /products/hubData       |
  And user verifies JSON response is as per datatable:
    | data.attributes.productsHubPage.pageTitle | Products |
    ...
```

**Key difference:** NonUI gateway tests are an additional coverage layer between device and Karate integration. Add to `layer-registry.yaml` with `id: gateway_e2e_nonui`.

### Extraction algorithm (both patterns)

```python
import re

def extract_from_feature_file(path, default_project='EANDBLUE'):
    content = open(path).read()
    lines = content.splitlines()
    tests = []
    for i, line in enumerate(lines):
        m = re.search(r'@JiraXrayTest_([A-Za-z0-9-]+)', line)
        if m:
            raw_id = m.group(1)
            # Normalise bare numeric IDs
            xray_id = raw_id if re.match(r'^[A-Z]+-\d+$', raw_id) else f'{default_project}-{raw_id}'
            # Find Scenario title on next non-empty line
            summary = ''
            for j in range(i + 1, min(i + 5, len(lines))):
                if 'Scenario' in lines[j]:
                    summary = re.sub(r'\s*Scenario[:\s]*', '', lines[j]).strip()
                    break
            # Detect NonUI gateway vs device UI
            is_nonui = '@NonUI_GatewayE2E' in lines[i] or 'NonUI' in line
            tests.append({
                'xray_id': xray_id,
                'summary': summary,
                'source': 'nonui_gateway' if is_nonui else 'device_feature',
                'source_file': path,
            })
    return tests
```

### Input detection — feature file vs Jira key

```python
import os, re

def detect_xray_input_type(xray_input):
    if re.match(r'^[A-Z]+-\d+$', xray_input):
        return 'jira_key'                     # EANDBLUE-1234 → API call
    if xray_input.endswith('.feature'):
        return 'feature_file'                 # single .feature file
    if os.path.isdir(xray_input):
        return 'feature_dir'                  # directory → glob **/*.feature
    if xray_input.endswith('.csv'):
        return 'csv'
    if xray_input.endswith(('.xls', '.xlsx')):
        return 'excel'                        # Jira .xls is HTML-disguised
    return 'unknown'
```

### Tag-to-Scenario mapping (general)

The Xray tag appears on the line **immediately before** the `Scenario:` line. When a Scenario has no `@JiraXrayTest_` tag:
- Generate a synthetic ID: `LOCAL-<8-char SHA256 of scenario title>`
- Add to `red_flags` so the caller knows coverage cannot be tracked to a Jira ticket

---

## Core Concept 3: CSV and Excel Import

For teams that export tests from Xray into spreadsheets.

### CSV format (typical Xray export)

```csv
key,summary,status,labels
EANDBLUE-8254,"User sees PREMIER upgrade only",PASS,"regression,smoke"
EANDBLUE-9001,"Blue customer sees current balance",FAIL,"smoke"
```

### Auto-detect column names

Column names vary across export configurations. Apply this priority:

| Field | Column names to try (in order) |
|-------|-------------------------------|
| ID | `key`, `id`, `xray_id`, `test_id`, `issue_key` |
| Name | `summary`, `name`, `title`, `description`, `test_summary` |

```python
import csv

reader = csv.DictReader(open('xray-export.csv'))
cols = [c.lower() for c in (reader.fieldnames or [])]

id_col = next((c for c in cols if c in ['key','id','xray_id','test_id','issue_key']), None)
name_col = next((c for c in cols if c in ['summary','name','title','description','test_summary']), None)

if not id_col:
    raise ValueError(f"Cannot find ID column. Columns found: {cols}")
```

### Excel (.xlsx) import

```python
try:
    import openpyxl
    wb = openpyxl.load_workbook('xray-export.xlsx')
    ws = wb.active
    headers = [str(c.value).lower() for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        ...
except ImportError:
    # openpyxl not installed — tell user to export as CSV
    raise RuntimeError("openpyxl not available. Export the spreadsheet as .csv and retry.")
```

---

## Core Concept 4: Error Handling and Rate Limits

### HTTP error codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Parse JSON response |
| 401 | Invalid PAT | Add red_flag: "JIRA_PAT invalid or expired" |
| 403 | No permission | Add red_flag: "PAT lacks Xray read permission on {key}" |
| 404 | Key not found | Add red_flag: "Test plan/execution {key} not found" |
| 429 | Rate limited | Wait 5s, retry once; if still 429, add red_flag |
| 5xx | Server error | Add red_flag: "Jira API unavailable — HTTP {code}" |

### Retry pattern

```bash
HTTP_CODE=$(curl -s -o /tmp/xray_response.json -w "%{http_code}" \
  -H "Authorization: Bearer ${JIRA_PAT}" \
  "${JIRA_BASE_URL}/rest/raven/1.0/api/testplan/${KEY}/test")

if [ "${HTTP_CODE}" = "429" ]; then
    sleep 5
    HTTP_CODE=$(curl -s -o /tmp/xray_response.json -w "%{http_code}" \
      -H "Authorization: Bearer ${JIRA_PAT}" \
      "${JIRA_BASE_URL}/rest/raven/1.0/api/testplan/${KEY}/test")
fi
```

---

## Advanced: Large Test Plans (Pagination)

The Raven API does not paginate — it returns all tests in one response. For test plans with >500 tests, the response may be large (>1MB). Use streaming JSON if needed:

```python
import json, subprocess
result = subprocess.run([
    'curl', '-s', '-H', f'Authorization: Bearer {jira_pat}',
    f'{jira_base_url}/rest/raven/1.0/api/testplan/{key}/test'
], capture_output=True)
tests = json.loads(result.stdout)
```

---

## Agent Self-Check

Before the Xray Importer Agent processes any input, verify:

- [ ] Input type is detected first (`jira_key` / `feature_file` / `feature_dir` / `csv` / `excel`) — never assume
- [ ] `JIRA_PAT` is set in env — if missing, add red_flag immediately and skip API calls
- [ ] `JIRA_BASE_URL` is set in env — default to `https://estjira.barcapint.com` if missing
- [ ] Input matches `^[A-Z]+-\d+$` before treating as a Jira key (Jira path)
- [ ] Feature file path exists on disk before opening (feature file / feature_dir path)
- [ ] Bare numeric IDs in feature files (`@JiraXrayTest_5147`) have project prefix applied before output
- [ ] NonUI gateway tests (`@NonUI_GatewayE2E` tag or `NonUI` in path) are flagged with `source: nonui_gateway` — they represent a separate layer, not device tests
- [ ] HTTP response code is checked before attempting JSON parse (Jira API path)
- [ ] Jira `.xls` files are parsed as HTML (`html.parser`), not with `xlrd`/`openpyxl` — Jira exports `.xls` as HTML
- [ ] CSV reader confirms at least one ID column before iterating rows
- [ ] `openpyxl` import is attempted before reading `.xlsx`; fallback message is clear
- [ ] Synthetic `LOCAL-` IDs are listed in `red_flags`, not silently created
- [ ] Total test count is logged after extraction regardless of source type
