#!/usr/bin/env python3
"""iOS Calibration Report — compares predicted confidence with real removal outcomes.

Reads the outcome ledger written by ios_removal_executor.py
(.arbiter/swift/OUTCOMES.jsonl) and reports, per predicted category:

  - projection: what the plan expected (planned entities, target precision)
  - outcome:    what actually happened (removed and still building/testing,
                failed with a compiler/test error, rolled back unattributed)
  - precision:  confirmed dead / (confirmed dead + false positives)

False positives are listed with the scoring reasons they had and the error that
exposed them, grouped by error kind so the missing detection signal is visible.

Later feedback (a QA regression, a revert after merge) can be appended with
--record, so precision reflects more than "it compiled".

Usage:
  python3 ios_calibration_report.py <project_path> [--plan PLAN.json] [--json OUT.json]
  python3 ios_calibration_report.py <project_path> --record <file> <name> --outcome regression --note "..."
  python3 ios_calibration_report.py <project_path> --record <file> <name> --outcome removed \
      --type method --tier SAFE --note "removed manually while diagnosing batch 4"
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from .arbiter_meta import stamp
except ImportError:
    from arbiter_meta import stamp

OUTCOMES_FILE = Path(".arbiter") / "swift" / "OUTCOMES.jsonl"

# Minimum precision each tier should achieve; tiers below target need re-tuning
TARGET_PRECISION = {"SAFE": 0.95, "LIKELY": 0.80, "UNCERTAIN": 0.50}

FALSE_POSITIVE_OUTCOMES = ("build_failed", "tests_failed", "regression")
NOT_ATTEMPTED_OUTCOMES = ("skipped", "blocked")

# Compiler error kind → which detection signal most likely missed the reference
ERROR_KINDS = [
    (re.compile(r"\.(m|mm|h):\d+.*error"), "referenced from Objective-C"),
    (re.compile(r"does not conform to protocol|protocol requires"), "protocol witness"),
    (re.compile(r"has no member"), "member access (dot syntax)"),
    (re.compile(r"cannot find (type )?'\w+' in scope"), "direct reference"),
    (re.compile(r"Build input file cannot be found"), "Xcode project file reference"),
    (re.compile(r"(storyboard|xib|nib)", re.I), "Interface Builder"),
]


def load_outcomes(project_path: Path) -> List[Dict[str, Any]]:
    ledger = project_path / OUTCOMES_FILE
    if not ledger.exists():
        return []
    with open(ledger) as f:
        return [json.loads(line) for line in f if line.strip()]


def latest_per_entity(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Latest outcome per entity (a later regression overrides an earlier 'removed').

    A later skip/block doesn't hide an earlier real attempt.
    """
    latest: Dict[str, Dict[str, Any]] = {}
    for r in sorted(records, key=lambda r: r.get("timestamp", "")):
        key = f"{r.get('file')}::{r.get('type')}::{r.get('name')}"
        if r["outcome"] not in NOT_ATTEMPTED_OUTCOMES or key not in latest:
            latest[key] = r
    return latest


def classify_error(detail: str) -> str:
    for pattern, kind in ERROR_KINDS:
        if pattern.search(detail or ""):
            return kind
    return "test failure" if "test" in (detail or "").lower() else "other"


def build_report(project_path: Path, plan_path: Optional[Path] = None) -> Dict[str, Any]:
    entities = latest_per_entity(load_outcomes(project_path))

    planned: Dict[str, int] = defaultdict(int)
    if plan_path and plan_path.exists():
        with open(plan_path) as f:
            for task in json.load(f).get("tasks", []):
                planned[task["category"]] += len(task.get("entities", []))

    tiers: Dict[str, Dict[str, Any]] = {}
    by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reasons: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    false_positives: List[Dict[str, Any]] = []

    for r in entities.values():
        cat = r.get("predictedCategory", "UNKNOWN")
        t = tiers.setdefault(cat, defaultdict(int))
        outcome = r["outcome"]
        bucket = ("confirmed" if outcome == "removed"
                  else "false_positive" if outcome in FALSE_POSITIVE_OUTCOMES
                  else "not_attempted" if outcome in NOT_ATTEMPTED_OUTCOMES
                  else "inconclusive")  # rolled back with an unattributed failure
        t[bucket] += 1
        by_type[r.get("type", "?")][bucket] += 1
        for reason in r.get("scoringReasons") or ["(no deductions)"]:
            reasons[re.sub(r"^-?[\d.]+:\s*", "", reason)][bucket] += 1
        if bucket == "false_positive":
            false_positives.append({
                "name": r.get("name"), "type": r.get("type"), "file": r.get("file"),
                "predictedCategory": cat, "confidenceScore": r.get("confidenceScore"),
                "scoringReasons": r.get("scoringReasons", []),
                "outcome": outcome, "detail": r.get("detail", ""),
                "missedSignal": ("runtime-only use (found after merge)" if outcome == "regression"
                                 else classify_error(r.get("detail", ""))),
            })

    summary = {}
    for cat in sorted(set(tiers) | set(planned)):
        t = tiers.get(cat, {})
        decided = t.get("confirmed", 0) + t.get("false_positive", 0)
        precision = t.get("confirmed", 0) / decided if decided else None
        target = TARGET_PRECISION.get(cat)
        summary[cat] = {
            "planned": planned.get(cat),
            "confirmed": t.get("confirmed", 0),
            "falsePositives": t.get("false_positive", 0),
            "inconclusive": t.get("inconclusive", 0),
            "notAttempted": t.get("not_attempted", 0),
            "precision": precision,
            "targetPrecision": target,
            "meetsTarget": None if precision is None or target is None else precision >= target,
        }

    missed = defaultdict(int)
    for fp in false_positives:
        missed[fp["missedSignal"]] += 1

    return {
        "generatedAt": datetime.now().isoformat(),
        "entitiesTracked": len(entities),
        "tiers": summary,
        "byType": {k: dict(v) for k, v in by_type.items()},
        "byScoringReason": {k: dict(v) for k, v in reasons.items()},
        "missedSignals": dict(sorted(missed.items(), key=lambda kv: -kv[1])),
        "falsePositives": false_positives,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    def pct(v):
        return "—" if v is None else f"{v:.0%}"

    out = ["# Arbiter iOS calibration — predicted vs actual", "",
           f"Entities tracked: {report['entitiesTracked']}", "",
           "| Tier | Planned | Confirmed dead | False positives | Inconclusive | Not attempted "
           "| Precision | Target | |",
           "|---|---|---|---|---|---|---|---|---|"]
    for cat, t in report["tiers"].items():
        flag = {True: "✅", False: "❌ re-tune", None: ""}[t["meetsTarget"]]
        out.append(f"| {cat} | {t['planned'] if t['planned'] is not None else '—'} | {t['confirmed']} "
                   f"| {t['falsePositives']} | {t['inconclusive']} | {t['notAttempted']} "
                   f"| {pct(t['precision'])} | {pct(t['targetPrecision'])} | {flag} |")

    out += ["", "Precision = confirmed / (confirmed + false positives). Inconclusive = rolled back "
            "with a failure no single entity could be blamed for; re-run those in smaller batches.", ""]

    if report["missedSignals"]:
        out += ["## What the analysis missed", "", "| Missed signal | False positives |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in report["missedSignals"].items()]
        out.append("")

    if report["falsePositives"]:
        out += ["## False positives", "",
                "| Entity | Type | Tier (score) | Reasons | Error |", "|---|---|---|---|---|"]
        for fp in report["falsePositives"]:
            reasons = "; ".join(fp["scoringReasons"]) or "no deductions"
            detail = fp["detail"].replace("|", "\\|")[:140]
            out.append(f"| `{fp['name']}` ({fp['file']}) | {fp['type']} | "
                       f"{fp['predictedCategory']} ({fp['confidenceScore']}) | {reasons} | {detail} |")
        out.append("")

    out += ["## By entity type", "", "| Type | Confirmed | False positives | Inconclusive | Not attempted |",
            "|---|---|---|---|---|"]
    for typ, b in sorted(report["byType"].items()):
        out.append(f"| {typ} | {b.get('confirmed', 0)} | {b.get('false_positive', 0)} "
                   f"| {b.get('inconclusive', 0)} | {b.get('not_attempted', 0)} |")
    return "\n".join(out)


def record_feedback(project_path: Path, file: str, name: str, outcome: str, note: str,
                    entity_type: Optional[str] = None, tier: Optional[str] = None) -> Dict:
    """Append feedback for an entity: a post-merge regression, or a removal done by hand.

    Entities not yet in the ledger (e.g. removed manually while diagnosing a failed batch)
    need entity_type and tier so they can be counted.
    """
    previous = [r for r in load_outcomes(project_path)
                if r.get("file") == file and r.get("name") == name]
    if previous:
        base = previous[-1]
    elif entity_type and tier:
        base = {"name": name, "file": file, "type": entity_type, "predictedCategory": tier,
                "confidenceScore": None, "scoringReasons": [], "language": "swift"}
    else:
        raise SystemExit(f"No ledger entry for {name} in {file} — pass --type and --tier to add one")
    entry = {**base, "timestamp": datetime.now().isoformat(), "outcome": outcome,
             "attributed": True, "detail": note, "runId": "feedback"}
    with open(project_path / OUTCOMES_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    project = Path(sys.argv[1]).resolve()
    args = sys.argv[2:]

    def opt(flag: str) -> Optional[str]:
        return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else None

    if "--record" in args:
        i = args.index("--record")
        entry = record_feedback(project, args[i + 1], args[i + 2],
                                opt("--outcome") or "regression", opt("--note") or "",
                                opt("--type"), opt("--tier"))
        print(json.dumps(entry, indent=2))
        sys.exit(0)

    plan = opt("--plan")
    report = build_report(project, Path(plan) if plan else project / ".arbiter" / "swift" / "PLAN.json")
    report["generatedBy"] = stamp(["ios_calibration_report.py"])
    if opt("--json"):
        with open(opt("--json"), "w") as f:
            json.dump(report, f, indent=2)
    print(render_markdown(report))
