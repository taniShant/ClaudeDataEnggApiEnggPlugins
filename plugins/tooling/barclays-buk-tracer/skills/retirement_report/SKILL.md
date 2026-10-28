---
name: retirement-report
description: >
  Xray test retirement report schema — three-group classification (retire-ready,
  needs-new-coverage, keep), evidence record format, Markdown and CSV report
  structure, Jira comment format, and classification decision rules.
user-invocable: false
owner: Barclays BUK Digital Channels
review-trigger: Retirement classification rules change, new report output format added
status: production
---

## Source Attribution

**Source:** TRACER v1.1.0 internal — Barclays BUK shift-left testing strategy  
**Owner:** Barclays BUK Digital Channels  
**Review trigger:** Retirement classification rules change, new output format added, or Jira API comment schema updated  
**Status:** Production

---

## Quick Start

```python
# Classify a single Xray test
def classify_xray_test(xray_id, matrix):
    candidate = find_in_matrix(matrix, xray_id)
    if not candidate:
        return 'needs-new-coverage', None
    if candidate['retirement_status'] == 'candidate' and candidate.get('retirement_evidence'):
        return 'retire-ready', candidate['retirement_evidence']
    if candidate['retirement_status'] == 'keep':
        return 'keep', candidate.get('retirement_evidence', 'Keep reason not specified')
    return 'needs-new-coverage', None
```

---

## Core Concept 1: Three-Group Classification

Every Xray test is assigned to exactly one group.

### Group 1: Retire-Ready

**Criteria** (all must be true):
1. `xray_id` found in the traceability matrix `retirement_candidates` list
2. `retirement_status` = `candidate`
3. `retirement_evidence` is non-empty (at least one lower-layer test ID cited)

**Meaning:** The behavior is covered at a lower-cost layer. The Xray test is redundant. It can be removed from the device test suite once the team signs off.

**Evidence required:** The lower-layer test ID, the layer name, and the framework must all be present.

### Group 2: Needs New Coverage

**Criteria** (any one):
- `xray_id` not found in matrix at all
- Found in matrix but `retirement_candidates` list is empty
- Found in matrix but `retirement_status` = `candidate` AND `retirement_evidence` is empty

**Meaning:** The behavior may or may not exist in the codebase, but there is no lower-layer test proving it is covered. The team needs to write a test at the appropriate lower layer before this Xray test can be retired.

**Action required:** The report provides the target layer and framework. The team writes the test, then re-runs `/tracer:trace-scan` to re-classify.

### Group 3: Keep

**Criteria:**
- `retirement_status` = `keep`

**Meaning:** Despite potential lower-layer coverage, this test must be retained. Common reasons:
- Device-specific hardware behavior (biometrics, camera, NFC)
- End-to-end user journey that crosses system boundaries
- Regulatory/audit requirement (e.g. PSD2, WCAG)
- Test explicitly tagged `@keep` by the team

---

## Core Concept 2: Evidence Record Format

Each retire-ready test must carry an evidence record in the matrix:

```yaml
retirement_candidates:
  - xray_id: EANDBLUE-8254
    retirement_status: candidate
    retirement_evidence: >
      Behavior 'show_premier_upgrade_only_when_blue_removed_from_config' covered by
      PropositionsManagementServiceTest#shouldReturnPremierOnly at layer 'xapi'
      (hierarchy_position 4 — cheaper than device layer 1).
      Framework: Spock. Repo: java-backend.
```

Evidence string must include:
- Behavior name (snake_case)
- Lower-layer test ID (ClassName#methodName or equivalent)
- Layer name and hierarchy_position
- Framework
- Repo name

---

## Core Concept 3: Markdown Report Structure

```markdown
# XRAY RETIREMENT REPORT — {MODULE}

**Generated:** {YYYY-MM-DD}
**Xray source:** {plan_id or path}
**Repos scanned:** {comma-separated repo names}
**Matrix file:** {relative path to .tracer.yaml}

---

## Summary

| Category | Count |
|----------|-------|
| Total Xray tests | {total} |
| ✅ Retire-ready | {N} |
| ⚠️ Needs new coverage | {N} |
| 🔒 Keep | {N} |

---

## ✅ Retire-Ready ({N})

> Safe to retire. Lower-layer coverage confirmed. Awaiting team sign-off.

### {XRAY_ID} — {summary}
- **Behavior:** `{behavior_name}`
- **Covered by:** `{test_id}` [{layer_id}, {framework}]
- **Repo:** {repo}
- **Evidence:** {retirement_evidence}

---

## ⚠️ Needs New Coverage ({N})

> Write a lower-layer test for each entry, then re-run `/tracer:trace-scan`.

### {XRAY_ID} — {summary}
- **Behavior:** `{behavior_name}` *(or: not yet mapped to a behavior)*
- **Gap:** No `{target_layer}` test found for this behavior
- **Action:** Write a `{framework}` test at the `{target_layer}` layer

---

## 🔒 Keep ({N})

> Intentionally retained. Do not retire.

### {XRAY_ID} — {summary}
- **Reason:** {keep_reason}
```

---

## Core Concept 4: CSV Report Schema

```csv
xray_id,summary,decision,behavior_name,covered_by,layer,framework,repo,evidence
EANDBLUE-8254,"User sees PREMIER upgrade only",retire-ready,show_premier_upgrade_only,...,xapi,spock,java-backend,"Covered by ..."
EANDBLUE-9001,"Blue customer sees balance",needs-new-coverage,blue_customer_sees_balance,,,,,
EANDBLUE-7001,"User authenticates with biometrics",keep,user_authenticates_with_biometrics,,,,,Device-specific hardware
```

Columns:
- `xray_id` — Jira issue key
- `summary` — original Xray test summary
- `decision` — `retire-ready` | `needs-new-coverage` | `keep`
- `behavior_name` — snake_case behavior from matrix (empty if not in matrix)
- `covered_by` — lower-layer test ID (empty if not retire-ready)
- `layer` — layer_id of covering test
- `framework` — test framework
- `repo` — repo where covering test was found
- `evidence` — full evidence string (retire-ready only)

---

## Core Concept 5: Jira Comment Format

Post to `POST /rest/api/2/issue/{plan_key}/comment` using Jira wiki markup:

```
h2. TRACER RETIREMENT REPORT — {MODULE}

*Generated:* {date}
*Matrix file:* {matrix_path}
*Repos scanned:* {comma-separated}

|| Category || Count ||
| ✅ Retire-ready | {N} |
| ⚠️ Needs new coverage | {N} |
| 🔒 Keep | {N} |
| *Total* | {total} |

h3. Next Steps

* *Retire-ready:* Review the evidence in {{MODULE}}-xray-retirement-report.md and raise a PR to remove these tests from the Xray test plan.
* *Needs new coverage:* Write lower-layer tests for these, then re-run {{/tracer:trace-scan}}.
* *Keep:* No action needed.

_Generated by TRACER v1.1.0 — [Full report in repository]_
```

---

## Advanced: Idempotent Jira Comment

Check for an existing TRACER comment before posting to avoid duplicates:

```bash
EXISTING_ID=$(curl -s -H "Authorization: Bearer ${JIRA_PAT}" \
  "${JIRA_BASE_URL}/rest/api/2/issue/${KEY}/comment" \
  | python3 -I -c "
import sys, json
data = json.load(sys.stdin)
for c in data.get('comments', []):
    if 'TRACER RETIREMENT REPORT' in c.get('body', ''):
        print(c['id'])
        break
")

if [ -n "${EXISTING_ID}" ]; then
    # Update
    curl -s -X PUT -H "Authorization: Bearer ${JIRA_PAT}" \
      -H "Content-Type: application/json" \
      -d "{\"body\": \"${COMMENT_BODY}\"}" \
      "${JIRA_BASE_URL}/rest/api/2/issue/${KEY}/comment/${EXISTING_ID}"
else
    # Create
    curl -s -X POST -H "Authorization: Bearer ${JIRA_PAT}" \
      -H "Content-Type: application/json" \
      -d "{\"body\": \"${COMMENT_BODY}\"}" \
      "${JIRA_BASE_URL}/rest/api/2/issue/${KEY}/comment"
fi
```

---

## Agent Self-Check

Before the Report Agent writes any output, verify:

- [ ] Matrix loaded successfully — `retirement_candidates` field accessible per behavior
- [ ] All Xray tests from importer accounted for — total in + total out should match (retire+keep+needs)
- [ ] Retire-ready count only includes tests where `retirement_evidence` is non-empty
- [ ] Needs-coverage section lists behavior name when known, "not yet mapped" when not
- [ ] Markdown report file written to disk before posting Jira comment
- [ ] Jira comment check performed before POST (avoid duplicate comments)
- [ ] `FORMAT` input respected — skip Jira step if `FORMAT = markdown`
- [ ] CSV written with all 9 columns present — empty string (not null) for missing fields
