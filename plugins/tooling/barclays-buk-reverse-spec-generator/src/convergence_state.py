"""
convergence_state.py — persistent loop state for the self-verification cycle.

One `.convergence.yaml` file lives alongside each `.spec` file.
It is written by /converge and /run-tests, read by all skills.

State tracks per-item:
    source_of_truth : "spec" | "code" | "unknown"
    test_status     : "passing" | "failing" | "error" | "not_run" | "no_test"
    divergence_status: "aligned" | "diverged" | "missing_impl" | "missing_spec" | "unknown"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Valid enumeration values
# ---------------------------------------------------------------------------

_VALID_SOT = {"spec", "code", "unknown"}
_VALID_TEST_STATUS = {"passing", "failing", "error", "not_run", "no_test"}
_VALID_DIV_STATUS = {
    "aligned",
    "diverged",
    "missing_impl",
    "missing_spec",
    "unknown",
}
_SECTIONS = ("behaviors", "rules", "constraints")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ConvergenceItem:
    """State record for a single spec item (behavior, rule, or constraint)."""

    source_of_truth: str = "unknown"   # "spec" | "code" | "unknown"
    test_status: str = "not_run"       # "passing" | "failing" | "error" | "not_run" | "no_test"
    divergence_status: str = "unknown" # "aligned" | "diverged" | "missing_impl" | "missing_spec" | "unknown"
    last_verified: Optional[str] = None  # ISO date string "YYYY-MM-DD"
    notes: str = ""

    def to_dict(self) -> dict:
        d: dict = {
            "source_of_truth": self.source_of_truth,
            "test_status": self.test_status,
            "divergence_status": self.divergence_status,
        }
        if self.last_verified:
            d["last_verified"] = self.last_verified
        if self.notes:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ConvergenceItem":
        return cls(
            source_of_truth=_validated(d.get("source_of_truth", "unknown"), _VALID_SOT, "unknown"),
            test_status=_validated(d.get("test_status", "not_run"), _VALID_TEST_STATUS, "not_run"),
            divergence_status=_validated(
                d.get("divergence_status", "unknown"), _VALID_DIV_STATUS, "unknown"
            ),
            last_verified=d.get("last_verified"),
            notes=d.get("notes", ""),
        )


@dataclass
class ConvergenceState:
    """Full convergence state for one spec file."""

    spec_file: str = ""
    module: str = ""
    last_run: str = ""
    iteration_count: int = 0
    convergence_pct: float = 0.0

    # Per-section item maps: item_name -> ConvergenceItem
    behaviors: Dict[str, ConvergenceItem] = field(default_factory=dict)
    rules: Dict[str, ConvergenceItem] = field(default_factory=dict)
    constraints: Dict[str, ConvergenceItem] = field(default_factory=dict)

    # Summary counts (derived, kept for quick reads)
    total_items: int = 0
    aligned: int = 0
    diverged: int = 0
    missing_impl: int = 0
    missing_spec: int = 0
    unknown_divergence: int = 0

    def section(self, name: str) -> Dict[str, ConvergenceItem]:
        """Return the dict for a given section name."""
        return getattr(self, name)

    def all_items(self):
        """Iterate (section, item_name, item) across all sections."""
        for sec in _SECTIONS:
            for name, item in self.section(sec).items():
                yield sec, name, item

    def recompute_summary(self) -> None:
        """Recompute derived counts and convergence_pct from current items."""
        totals = {k: 0 for k in ("total", "aligned", "diverged", "missing_impl", "missing_spec", "unknown")}
        for _, _, item in self.all_items():
            totals["total"] += 1
            status = item.divergence_status
            if status == "aligned":
                totals["aligned"] += 1
            elif status == "diverged":
                totals["diverged"] += 1
            elif status == "missing_impl":
                totals["missing_impl"] += 1
            elif status == "missing_spec":
                totals["missing_spec"] += 1
            else:
                totals["unknown"] += 1

        self.total_items = totals["total"]
        self.aligned = totals["aligned"]
        self.diverged = totals["diverged"]
        self.missing_impl = totals["missing_impl"]
        self.missing_spec = totals["missing_spec"]
        self.unknown_divergence = totals["unknown"]
        self.convergence_pct = (
            round(100.0 * totals["aligned"] / totals["total"], 1) if totals["total"] else 0.0
        )

    def to_dict(self) -> dict:
        self.recompute_summary()
        d: dict = {
            "version": "1.0",
            "spec_file": self.spec_file,
            "module": self.module,
            "last_run": self.last_run,
            "iteration_count": self.iteration_count,
            "convergence_pct": self.convergence_pct,
            "summary": {
                "total_items": self.total_items,
                "aligned": self.aligned,
                "diverged": self.diverged,
                "missing_impl": self.missing_impl,
                "missing_spec": self.missing_spec,
                "unknown": self.unknown_divergence,
            },
        }
        for sec in _SECTIONS:
            sec_dict = self.section(sec)
            if sec_dict:
                d[sec] = {name: item.to_dict() for name, item in sec_dict.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ConvergenceState":
        state = cls(
            spec_file=d.get("spec_file", ""),
            module=d.get("module", ""),
            last_run=d.get("last_run", ""),
            iteration_count=int(d.get("iteration_count", 0)),
            convergence_pct=float(d.get("convergence_pct", 0.0)),
        )
        for sec in _SECTIONS:
            sec_data = d.get(sec, {})
            if isinstance(sec_data, dict):
                for name, item_dict in sec_data.items():
                    getattr(state, sec)[name] = ConvergenceItem.from_dict(item_dict)
        summary = d.get("summary", {})
        state.total_items = int(summary.get("total_items", 0))
        state.aligned = int(summary.get("aligned", 0))
        state.diverged = int(summary.get("diverged", 0))
        state.missing_impl = int(summary.get("missing_impl", 0))
        state.missing_spec = int(summary.get("missing_spec", 0))
        state.unknown_divergence = int(summary.get("unknown", 0))
        return state


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def _state_path(spec_path: Path) -> Path:
    """Return the .convergence.yaml path for a given .spec file."""
    stem = spec_path.stem  # e.g. "a-digi-msg-data-mgt"
    if stem.endswith(".spec"):
        stem = stem[:-5]
    return spec_path.parent / f"{stem}.convergence.yaml"


def load_state(spec_path) -> ConvergenceState:
    """
    Load convergence state from the .convergence.yaml alongside spec_path.
    Returns a fresh empty state if the file does not exist.
    """
    spec_path = Path(spec_path)
    state_file = _state_path(spec_path)
    if not state_file.exists():
        return ConvergenceState(
            spec_file=spec_path.name,
            module=_module_from_path(spec_path),
        )
    text = state_file.read_text(encoding="utf-8")
    d = _simple_yaml_load(text)
    return ConvergenceState.from_dict(d)


def save_state(state: ConvergenceState, spec_path) -> None:
    """
    Persist convergence state to the .convergence.yaml alongside spec_path.
    Overwrites the existing file.
    """
    spec_path = Path(spec_path)
    state_file = _state_path(spec_path)
    state.last_run = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = _simple_yaml_dump(state.to_dict())
    state_file.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# State update helpers
# ---------------------------------------------------------------------------


def update_from_divergences(
    state: ConvergenceState,
    divergences: list,
) -> ConvergenceState:
    """
    Merge a list of Divergence objects (from divergence_classifier) into state.
    Preserves existing source_of_truth overrides; updates divergence_status and
    last_verified. Increments iteration_count.

    Each divergence must have attributes:
        item_type       : "behaviors" | "rules" | "constraints"
        item_name       : str
        divergence_type : "aligned" | "diverged" | "missing_impl" | "missing_spec" | "unknown"
        source_of_truth : "spec" | "code" | "unknown"
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for div in divergences:
        sec = div.item_type  # already plural
        sec_dict = state.section(sec)
        existing = sec_dict.get(div.item_name)
        if existing is None:
            # New item — create with classifier's source_of_truth
            sec_dict[div.item_name] = ConvergenceItem(
                source_of_truth=div.source_of_truth,
                divergence_status=div.divergence_type,
                last_verified=today,
            )
        else:
            # Preserve explicit source_of_truth overrides set by /amend
            if existing.source_of_truth == "unknown":
                existing.source_of_truth = div.source_of_truth
            existing.divergence_status = div.divergence_type
            existing.last_verified = today
    state.iteration_count += 1
    state.recompute_summary()
    return state


def update_from_test_results(state: ConvergenceState, results) -> ConvergenceState:
    """
    Merge test run results into state.test_status per behavior.

    results must be a TestResults object with a .results list of TestResult,
    each having .behavior_name and .status ("passing"|"failing"|"error"|None).
    """
    for result in results.results:
        if not result.behavior_name:
            continue
        item = state.behaviors.get(result.behavior_name)
        if item is None:
            state.behaviors[result.behavior_name] = ConvergenceItem(
                test_status=result.status or "not_run",
            )
        else:
            item.test_status = result.status or "not_run"
    state.recompute_summary()
    return state


def compute_convergence_pct(state: ConvergenceState) -> float:
    """Return the convergence percentage (0–100) from the current state."""
    state.recompute_summary()
    return state.convergence_pct


def set_source_of_truth(
    state: ConvergenceState,
    section: str,
    item_name: str,
    source_of_truth: str,
) -> ConvergenceState:
    """
    Explicitly set source_of_truth for one item.
    Called by /amend when it modifies a behavior — marks it as spec-led.
    Returns the mutated state for chaining.
    """
    if source_of_truth not in _VALID_SOT:
        raise ValueError(f"Invalid source_of_truth: {source_of_truth!r}")
    sec_dict = state.section(section)
    item = sec_dict.get(item_name)
    if item is None:
        sec_dict[item_name] = ConvergenceItem(source_of_truth=source_of_truth)
    else:
        item.source_of_truth = source_of_truth
    return state


# ---------------------------------------------------------------------------
# Minimal YAML helpers (stdlib only — no PyYAML)
# ---------------------------------------------------------------------------


def _simple_yaml_load(text: str) -> dict:
    """
    Load a .convergence.yaml file.
    The format is a subset of YAML: string scalars, integers, floats, nested
    mappings, and no sequences at the top level. Sufficient for our state file.
    """
    lines = text.splitlines()
    result: dict = {}
    stack: list = [result]
    indent_stack: list = [-1]
    current_key: Optional[str] = None

    for raw_line in lines:
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        stripped = raw_line.strip()

        # Pop stack until we find the right indent level
        while indent <= indent_stack[-1]:
            stack.pop()
            indent_stack.pop()

        if ":" in stripped:
            colon_pos = stripped.index(":")
            key = stripped[:colon_pos].strip()
            value_part = stripped[colon_pos + 1:].strip()

            if value_part == "" or value_part.startswith("#"):
                # Nested mapping incoming
                new_dict: dict = {}
                stack[-1][key] = new_dict
                stack.append(new_dict)
                indent_stack.append(indent)
                current_key = key
            else:
                stack[-1][key] = _parse_scalar(value_part)
        else:
            # bare value — skip (not expected in this format)
            pass

    return result


def _parse_scalar(raw: str) -> object:
    """Parse a YAML scalar value to a Python object."""
    raw = raw.strip()
    if raw.startswith("#"):
        raw = raw[:raw.index("#")].strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw in ("null", "~", ""):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _simple_yaml_dump(d: dict, indent: int = 0) -> str:
    """Dump a dict to YAML string (subset: no sequences at root level)."""
    lines: list = []
    if indent == 0:
        lines.append("# Auto-generated by reverse-spec-generator — do not edit manually")
    for key, value in d.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_simple_yaml_dump(value, indent + 1).rstrip("\n"))
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {str(value).lower()}")
        elif isinstance(value, str):
            # Quote strings that could be misread
            safe = value.replace('"', '\\"')
            lines.append(f'{prefix}{key}: "{safe}"')
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _validated(value: str, valid_set: set, default: str) -> str:
    return value if value in valid_set else default


def _module_from_path(spec_path: Path) -> str:
    stem = spec_path.stem
    if stem.endswith(".spec"):
        stem = stem[:-5]
    return re.sub(r"[^a-z0-9_]", "_", stem.lower())
