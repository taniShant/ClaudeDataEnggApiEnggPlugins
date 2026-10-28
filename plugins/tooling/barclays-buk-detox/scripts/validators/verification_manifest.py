#!/usr/bin/env python3
"""Embed the evidence & verification section into DETOX-REMEDIATION-REPORT.md.

The section is rendered deterministically from evidence records (never written
by the LLM) — per-finding evidence tables, accountability matrix, and rescan
instructions. Stage 8 writes the report with an EVIDENCE_PLACEHOLDER line; this
script replaces it. Re-running replaces the previously embedded section in place.

Input (JSON stdin):
    {
        "job_id": "a1b2c3d4",
        "evidence_records": [...],
        "report_path": "/path/to/repo/DETOX-REMEDIATION-REPORT.md"
    }

Output (JSON stdout):
    {
        "status": "success",
        "report_path": "...",
        "summary": {
            "total_findings": 12,
            "verified": 9,
            "unverified": 2,
            "failed": 1
        }
    }
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, progress, progress_done
from scripts.core.errors import error_exit


SCHEMA_VERSION = "1.0"

# Classification icons for readability
CLASSIFICATION_ICONS = {
    "VERIFIED": "✅ VERIFIED",
    "UNVERIFIED": "⚠️ UNVERIFIED",
    "FAILED": "❌ FAILED",
}

CONFIDENCE_LABELS = {
    "high": "High (WIZ CLI)",
    "medium": "Medium (Semgrep)",
    "low": "Low (Dep tree)",
    "none": "None",
}


def compute_summary(evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Count verified/unverified/failed from evidence records."""
    verified = 0
    unverified = 0
    failed = 0

    for record in evidence_records:
        classification = (
            record.get("accountability", {}).get("classification", "UNVERIFIED")
        )
        if classification == "VERIFIED":
            verified += 1
        elif classification == "FAILED":
            failed += 1
        else:
            unverified += 1

    return {
        "total_findings": len(evidence_records),
        "verified": verified,
        "unverified": unverified,
        "failed": failed,
    }


def generate_rescan_instructions() -> dict[str, str]:
    """Static rescan commands for manual re-verification."""
    return {
        "wiz_cli": "wizcli dir scan --path . --format json --no-publish",
        "semgrep": "semgrep --config auto --json .",
    }


def build_accountability_matrix(evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the accountability matrix from evidence records."""
    methods_used: set[str] = set()
    verifiers_used: set[str] = set()

    for record in evidence_records:
        verification = record.get("verification", {})
        methods_used.add(verification.get("method", "none"))
        verifiers_used.add(verification.get("verified_by", "none"))

    primary = "none"
    fallback = "none"
    priority = ["wiz_cli", "semgrep", "dep_tree", "none"]
    for method in priority:
        if method in methods_used:
            if primary == "none":
                primary = method
            elif fallback == "none":
                fallback = method

    return {
        "pipeline_tool": "detox",
        "primary_verifier": primary,
        "fallback_verifier": fallback,
        "methods_used": sorted(methods_used),
        "verifiers": sorted(verifiers_used - {"none"}),
    }


def _short_sha(sha: str) -> str:
    """Truncate a commit SHA for display."""
    if sha and len(sha) > 7 and sha != "—":
        return f"`{sha[:7]}`"
    if sha and sha != "—":
        return f"`{sha}`"
    return "—"


def render_evidence_table(evidence_records: list[dict[str, Any]]) -> str:
    """Render the per-finding evidence summary table in Markdown."""
    if not evidence_records:
        return "_No evidence records collected._\n"

    lines = [
        "| # | CWE | File | Severity | Classification | Verified/Rejected By | Proof | Commit |",
        "|---|-----|------|----------|---------------|---------------------|-------|--------|",
    ]

    for i, record in enumerate(evidence_records, 1):
        cwe = record.get("cwe_id", "—")
        file_path = record.get("file_path", "—")
        orig = record.get("original_finding", {})
        severity = orig.get("severity", "—")
        verification = record.get("verification", {})
        acc = record.get("accountability", {})
        fix = record.get("fix_applied", {})
        classification_key = acc.get("classification", "UNVERIFIED")
        classification = CLASSIFICATION_ICONS.get(classification_key, "⚠️ UNVERIFIED")
        commit = _short_sha(fix.get("commit_sha", "—"))
        delta = verification.get("delta", {})
        method = verification.get("method", "none")
        verified_by = verification.get("verified_by", "—")

        # Build proof/excuse column based on classification
        if classification_key == "VERIFIED":
            proof = f"{verified_by}: {delta.get('resolved', 0)} resolved, 0 remaining"
        elif classification_key == "FAILED":
            proof = f"{verified_by}: {delta.get('persistent', 0)} still present"
        else:
            reason = verification.get("reason", "")
            if reason:
                # Take first reason (before semicolon) for table brevity
                proof = reason.split(";")[0].strip()
            elif method != "none":
                proof = f"{verified_by}: {delta.get('resolved', 0)} resolved (not WIZ)"
            else:
                proof = "No verifier available"

        lines.append(
            f"| {i} | {cwe} | `{file_path}` | {severity} | {classification} | {verified_by} | {proof} | {commit} |"
        )

    return "\n".join(lines) + "\n"


def render_finding_details(evidence_records: list[dict[str, Any]]) -> str:
    """Render detailed per-finding evidence sections.

    Each classification gets a different narrative:
    - VERIFIED: who verified, what they scanned, before/after delta
    - UNVERIFIED: what was tried, why each method failed, what to do
    - FAILED: who detected the failure, what's still there
    """
    if not evidence_records:
        return ""

    sections = []
    for i, record in enumerate(evidence_records, 1):
        cwe = record.get("cwe_id", "—")
        file_path = record.get("file_path", "—")
        orig = record.get("original_finding", {})
        fix = record.get("fix_applied", {})
        verification = record.get("verification", {})
        acc = record.get("accountability", {})
        classification_key = acc.get("classification", "UNVERIFIED")
        classification = CLASSIFICATION_ICONS.get(classification_key, "⚠️ UNVERIFIED")
        delta = verification.get("delta", {})
        method = verification.get("method", "none")
        verified_by = verification.get("verified_by", "—")

        # Common header
        section = f"""#### Finding {i}: {cwe} — `{file_path}`

**Classification: {classification}**

| Attribute | Value |
|-----------|-------|
| Source | {orig.get('source', '—')} |
| Rule | {orig.get('rule_id', '—')} |
| Severity | {orig.get('severity', '—')} |
| Title | {orig.get('title', '—')} |
| Fix Commit | `{fix.get('commit_sha', '—')}` |
| Fix Description | {fix.get('diff_summary', '—')} |

"""
        # Classification-specific narrative
        if classification_key == "VERIFIED":
            pre_count = verification.get("pre_scan", {}).get("finding_count", "?")
            post_count = verification.get("post_scan", {}).get("finding_count", "?")
            section += f"""**✅ Proof of fix — verified by {verified_by}:**
| Evidence | Value |
|----------|-------|
| Verifier | {verified_by} |
| Method | {method} |
| Baseline findings (before fix) | {pre_count} |
| Post-fix findings (after fix) | {post_count} |
| Resolved | {delta.get('resolved', 0)} |
| Persistent | {delta.get('persistent', 0)} |
| New | {delta.get('new', 0)} |
"""

        elif classification_key == "FAILED":
            pre_count = verification.get("pre_scan", {}).get("finding_count", "?")
            post_count = verification.get("post_scan", {}).get("finding_count", "?")
            section += f"""**❌ Fix did not work — confirmed by {verified_by}:**
| Evidence | Value |
|----------|-------|
| Verifier | {verified_by} |
| Method | {method} |
| Baseline findings (before fix) | {pre_count} |
| Post-fix findings (after fix) | {post_count} |
| Still persistent | {delta.get('persistent', 0)} |
| New findings introduced | {delta.get('new', 0)} |

> **Action required:** Manual review needed. The fix was applied (commit `{fix.get('commit_sha', '—')}`) but the verifier still detects the vulnerability.
"""

        else:  # UNVERIFIED
            reason = verification.get("reason", "")
            action = verification.get("action_required", "")

            if method != "none":
                # Partially verified (e.g., Semgrep said OK but not WIZ)
                section += f"""**⚠️ Partially checked — {verified_by} says resolved, but WIZ has not confirmed:**
| Evidence | Value |
|----------|-------|
| Verifier | {verified_by} (secondary — not the bank's official scanner) |
| Method | {method} |
| Resolved | {delta.get('resolved', 0)} |
| Persistent | {delta.get('persistent', 0)} |

> **Why not VERIFIED:** WIZ CLI is the bank's strategic scanner. This fix was only checked by {method}, which is not authoritative. Install and authenticate WIZ CLI for VERIFIED status.
"""
            else:
                # No verification at all
                section += f"""**⚠️ Not verified — no scanner could check this fix:**

> **Why:** {reason or 'No verification method available'}

> **Action required:** {action or 'Re-run the pipeline with WIZ CLI installed and authenticated.'}
"""

        sections.append(section)

    return "\n".join(sections)


EVIDENCE_PLACEHOLDER = "<!-- DETOX-EVIDENCE-SECTION -->"
SECTION_BEGIN = "<!-- DETOX-EVIDENCE:BEGIN (generated by verification_manifest.py — do not edit) -->"
SECTION_END = "<!-- DETOX-EVIDENCE:END -->"


def build_evidence_section(job_id: str, evidence_records: list[dict[str, Any]]) -> str:
    """Assemble the evidence section embedded in DETOX-REMEDIATION-REPORT.md."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = compute_summary(evidence_records)
    matrix = build_accountability_matrix(evidence_records)
    instructions = generate_rescan_instructions()

    return f"""{SECTION_BEGIN}
## Evidence & Verification

**Generated:** {generated_at} | **Job ID:** `{job_id}` | **Schema Version:** {SCHEMA_VERSION}

### Evidence Summary

| Metric | Count |
|--------|-------|
| **Total Findings** | **{summary['total_findings']}** |
| ✅ VERIFIED (WIZ CLI confirmed) | {summary['verified']} |
| ⚠️ UNVERIFIED (Semgrep/dep-tree only) | {summary['unverified']} |
| ❌ FAILED (still flagged after fix) | {summary['failed']} |

### Evidence Table

{render_evidence_table(evidence_records)}
### Detailed Evidence Per Finding

{render_finding_details(evidence_records)}
### Accountability Matrix

| Attribute | Value |
|-----------|-------|
| Pipeline Tool | {matrix['pipeline_tool']} |
| Primary Verifier | {matrix['primary_verifier']} |
| Fallback Verifier | {matrix['fallback_verifier']} |
| Methods Used | {', '.join(matrix['methods_used'])} |

### Rescan Instructions

To independently verify these findings, run:

**WIZ CLI (gold standard):**
```bash
{instructions['wiz_cli']}
```

**Semgrep (secondary):**
```bash
{instructions['semgrep']}
```

### Classification Legend

| Icon | Meaning | What It Proves |
|------|---------|---------------|
| ✅ VERIFIED | WIZ CLI rescan confirms finding resolved | WIZ (the bank's scanner) says it's fixed |
| ⚠️ UNVERIFIED | Semgrep or dep-tree says resolved, WIZ not available | A scanner says it's fixed, but not the official one |
| ❌ FAILED | Verifier confirms finding still present after fix | Fix did not work — manual review required |

> **Note:** VERIFIED means WIZ CLI locally confirmed the fix. The WIZ portal updates
> when the next CI/CD pipeline scan runs on the default branch after merge.
{SECTION_END}"""


def embed_section(report: str, section: str) -> str:
    """Put the section into the report: replace a prior embed, else the placeholder, else append."""
    begin, end = report.find(SECTION_BEGIN), report.find(SECTION_END)
    if begin != -1 and end > begin:
        return report[:begin] + section + report[end + len(SECTION_END):]
    if EVIDENCE_PLACEHOLDER in report:
        return report.replace(EVIDENCE_PLACEHOLDER, section, 1)
    return report.rstrip("\n") + "\n\n---\n\n" + section + "\n"


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    job_id = input_data.get("job_id", "")
    evidence_records = input_data.get("evidence_records", [])
    report_path = input_data.get("report_path", "")

    if not report_path:
        error_exit("report_path is required", "input_validation")
    path = Path(report_path)
    if not path.is_file():
        error_exit(f"report not found: {report_path}", "input_validation")

    progress("Embedding evidence section into DETOX-REMEDIATION-REPORT.md...")

    section = build_evidence_section(job_id, evidence_records)
    path.write_text(embed_section(path.read_text(), section))
    summary = compute_summary(evidence_records)

    progress_done(
        f"Evidence section: {summary['verified']} verified, "
        f"{summary['unverified']} unverified, "
        f"{summary['failed']} failed"
    )

    write_json_output({
        "status": "success",
        "report_path": str(path),
        "summary": summary,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
