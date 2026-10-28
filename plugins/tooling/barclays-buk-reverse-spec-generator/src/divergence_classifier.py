"""
divergence_classifier.py — classify spec↔code divergences and format reports.

The classifier applies a source_of_truth heuristic suited to a reverse-spec
workflow (code always comes first):

    missing_impl  → spec was the intent  → source_of_truth: "spec"
    missing_spec  → code came first      → source_of_truth: "code"
    diverged      → ambiguous            → source_of_truth: "unknown"
    under_spec    → code more specific   → source_of_truth: "code"
    aligned       → no divergence        → preserves existing or "code"

Explicit overrides in ConvergenceState (set by /amend) always take precedence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Divergence types
# ---------------------------------------------------------------------------

MISSING_IMPL = "missing_impl"   # spec says X; no matching code found
MISSING_SPEC = "missing_spec"   # code has X; spec doesn't mention it
DIVERGED = "diverged"           # both exist but behaviour differs
UNDER_SPECIFIED = "under_spec"  # code more specific than spec describes
ALIGNED = "aligned"             # spec and code match


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------


@dataclass
class Divergence:
    """
    A single divergence between a spec item and its code implementation.

    Attributes
    ----------
    item_type       : section name — "behaviors", "rules", or "constraints"
    item_name       : the snake_case name of the item
    divergence_type : one of the MISSING_IMPL / DIVERGED / etc. constants
    source_of_truth : "spec" | "code" | "unknown"
    description     : human-readable description of the divergence
    fix_action      : what to do to resolve it
    details         : optional extra context (what the spec says vs code)
    """

    item_type: str
    item_name: str
    divergence_type: str
    source_of_truth: str
    description: str
    fix_action: str
    details: str = ""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

# Default source_of_truth by divergence type (reverse-spec heuristic)
_DEFAULT_SOT: dict = {
    MISSING_IMPL: "spec",
    MISSING_SPEC: "code",
    DIVERGED: "unknown",
    UNDER_SPECIFIED: "code",
    ALIGNED: "code",
}

_FIX_ACTIONS: dict = {
    MISSING_IMPL: "Implement the behavior in code, or remove from spec if no longer required",
    MISSING_SPEC: "Add this to the spec via /amend, or remove from code if it is dead",
    DIVERGED: "Review: update code to match spec (if source_of_truth=spec) or /amend spec (if source_of_truth=code)",
    UNDER_SPECIFIED: "Run /amend to add details from code into spec, or accept as design flexibility",
    ALIGNED: "No action required",
}


def classify(
    item_name: str,
    item_type: str,
    divergence_type: str,
    state=None,
) -> str:
    """
    Determine source_of_truth for one item.

    Checks the ConvergenceState for an explicit override first.
    Falls back to the heuristic default for the divergence_type.

    Parameters
    ----------
    item_name       : name of the spec item
    item_type       : "behaviors" | "rules" | "constraints"
    divergence_type : one of the divergence type constants
    state           : ConvergenceState (optional) — provides explicit overrides

    Returns
    -------
    "spec" | "code" | "unknown"
    """
    if state is not None:
        sec_dict = state.section(item_type)
        existing = sec_dict.get(item_name)
        if existing is not None and existing.source_of_truth != "unknown":
            return existing.source_of_truth
    return _DEFAULT_SOT.get(divergence_type, "unknown")


def make_divergence(
    item_type: str,
    item_name: str,
    divergence_type: str,
    description: str,
    details: str = "",
    state=None,
) -> Divergence:
    """
    Construct a Divergence with classified source_of_truth and standard fix_action.
    """
    sot = classify(item_name, item_type, divergence_type, state)
    fix = _FIX_ACTIONS.get(divergence_type, "Review and resolve")
    return Divergence(
        item_type=item_type,
        item_name=item_name,
        divergence_type=divergence_type,
        source_of_truth=sot,
        description=description,
        fix_action=fix,
        details=details,
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

_STATUS_ICON = {
    ALIGNED: "✓",
    MISSING_IMPL: "✗",
    MISSING_SPEC: "?",
    DIVERGED: "≠",
    UNDER_SPECIFIED: "~",
}

_SOT_LABEL = {
    "spec": "spec leads → update code",
    "code": "code leads → update spec",
    "unknown": "ambiguous  → human decision needed",
}

_SEVERITY = {
    MISSING_IMPL: "HIGH",
    DIVERGED: "HIGH",
    MISSING_SPEC: "MEDIUM",
    UNDER_SPECIFIED: "LOW",
    ALIGNED: "NONE",
}


def format_report(
    spec_file: str,
    divergences: List[Divergence],
    state=None,
    show_aligned: bool = False,
) -> str:
    """
    Render a convergence report string from a list of Divergence objects.

    Parameters
    ----------
    spec_file    : name of the spec file for the report header
    divergences  : list of Divergence objects
    state        : ConvergenceState (optional) — used for summary counts
    show_aligned : include ALIGNED items in the report (default: False)
    """
    lines: list = []

    # Header
    lines.append("=" * 60)
    lines.append(f"  Convergence Report: {spec_file}")
    lines.append("=" * 60)

    # Summary from state if available
    if state is not None:
        state.recompute_summary()
        lines.append(
            f"\n  Status: {state.convergence_pct:.1f}% converged"
            f"  (iteration {state.iteration_count})"
        )
        lines.append(
            f"  {state.aligned} aligned · "
            f"{state.diverged} diverged · "
            f"{state.missing_impl} missing impl · "
            f"{state.missing_spec} missing spec"
        )

    # Group by section
    sections: dict = {"behaviors": [], "rules": [], "constraints": []}
    for div in divergences:
        if not show_aligned and div.divergence_type == ALIGNED:
            continue
        sections[div.item_type].append(div)

    total_issues = sum(len(v) for v in sections.values())
    if total_issues == 0:
        lines.append("\n  No issues found — spec and code are aligned.\n")
        lines.append("=" * 60)
        return "\n".join(lines)

    lines.append(f"\n  {total_issues} issue(s) found:\n")

    # Render each section
    for sec_name, items in sections.items():
        if not items:
            continue
        lines.append(f"  [{sec_name.upper()}]")
        for div in sorted(items, key=lambda d: (_severity_rank(d.divergence_type), d.item_name)):
            icon = _STATUS_ICON.get(div.divergence_type, "·")
            sev = _SEVERITY.get(div.divergence_type, "")
            sot_label = _SOT_LABEL.get(div.source_of_truth, "")
            lines.append(f"\n  {icon} {div.item_name}  [{sev}]")
            lines.append(f"    type   : {div.divergence_type}")
            lines.append(f"    truth  : {div.source_of_truth}  ({sot_label})")
            lines.append(f"    detail : {div.description}")
            if div.details:
                lines.append(f"             {div.details}")
            lines.append(f"    action : {div.fix_action}")

    lines.append("")
    lines.append("  Next steps:")
    lines.append("    HIGH items   → fix now (code or spec per source_of_truth)")
    lines.append("    MEDIUM items → /amend spec or mark as known")
    lines.append("    LOW items    → review at next iteration")
    lines.append("    Re-run /converge after changes to check progress.")
    lines.append("    Run /status to see overall loop state.\n")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _severity_rank(divergence_type: str) -> int:
    return {
        MISSING_IMPL: 0,
        DIVERGED: 1,
        MISSING_SPEC: 2,
        UNDER_SPECIFIED: 3,
        ALIGNED: 4,
    }.get(divergence_type, 5)


def summarise(divergences: List[Divergence]) -> dict:
    """Return a count summary dict for a list of divergences."""
    counts: dict = {
        MISSING_IMPL: 0,
        DIVERGED: 0,
        MISSING_SPEC: 0,
        UNDER_SPECIFIED: 0,
        ALIGNED: 0,
    }
    for div in divergences:
        key = div.divergence_type
        counts[key] = counts.get(key, 0) + 1
    return counts
