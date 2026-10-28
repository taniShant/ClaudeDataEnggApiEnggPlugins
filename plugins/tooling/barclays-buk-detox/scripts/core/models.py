"""Shared data models for detox pipeline scripts.

NOTE: These dataclasses are currently unused at runtime. All scripts use plain
dicts for JSON I/O (stdin→dict→stdout). These models exist as schema
documentation and may be promoted to runtime validation in a future iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Vulnerability:
    """Normalized vulnerability finding from SAST report or threat model."""

    id: str
    cwe_id: str | None
    title: str
    description: str = ""
    severity: str = "medium"  # critical, high, medium, low, info
    source: str = "sast"
    file_path: str | None = None
    line_number: int | None = None
    code_snippet: str | None = None
    remediation_type: str = "code_fix"  # code_fix, infra_config, dependency, manual, not_applicable, likely_unexploitable
    tool_name: str = "wiz"
    rule_id: str | None = None
    confidence: float = 0.8
    # SCA (Software Composition Analysis) fields for CWE-937 dependency findings
    affected_package: str | None = None   # e.g. "log4j:log4j" or "lodash"
    current_version: str | None = None    # e.g. "1.2.17"
    fixed_version: str | None = None      # From Wiz report (e.g. "2.17.0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vulnerability:
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


@dataclass
class FixResult:
    """Result of applying a CWE fix."""

    vulnerability_id: str
    cwe_id: str
    status: str = "pending"  # success, failed, skipped
    files_modified: list[str] = field(default_factory=list)
    commit_sha: str | None = None
    validation_passed: bool | None = None
    retry_count: int = 0
    is_hybrid: bool = False
    pending_non_code_actions: bool = False
    title: str = ""
    description: str = ""
    file_path: str | None = None
    fix_type: str | None = None
    unfixed_reason: str | None = None  # LLM's one-line reason; exported verbatim as detox.unresolved.reason

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of a Semgrep rescan validation."""

    status: str  # success, error
    verdict: str  # PASS, PARTIAL, FAIL, ERROR
    cwe_id: str
    file_path: str
    baseline: dict[str, Any] = field(default_factory=dict)
    post_fix: dict[str, Any] = field(default_factory=dict)
    comparison: dict[str, Any] = field(default_factory=dict)
    semgrep_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestRunResult:
    """Result of running a test suite."""

    status: str  # success, error
    repo_dir: str
    test_framework: dict[str, Any] | None = None
    targeted: bool = False
    target_test_file: str | None = None
    results: dict[str, Any] | None = None
    failures: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_output_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceRecord:
    """Structured verification evidence for a single CWE fix.

    Produced by evidence_collector.py; rendered into the DETOX-REMEDIATION-REPORT.md evidence section.
    """

    finding_id: str = ""
    cwe_id: str = ""
    file_path: str = ""
    original_finding: dict[str, Any] = field(default_factory=dict)
    fix_applied: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    accountability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceRecord:
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


@dataclass
class PipelineState:
    """State of the detox remediation pipeline (v2 with evidence fields)."""

    version: int = 2
    job_id: str = ""
    project_path: str = ""
    started_at: str = ""
    jira_id: str | None = None
    model: str = "sonnet"
    severity_filter: str = "all"
    dry_run: bool = False
    generate_tests: bool = True
    test_mode: str = "fast"
    branch_name: str | None = None
    phases: dict[str, dict[str, str]] = field(default_factory=dict)
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)
    fix_results: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    infra_findings: list[dict[str, Any]] = field(default_factory=list)
    hybrid_findings: list[dict[str, Any]] = field(default_factory=list)
    manual_findings: list[dict[str, Any]] = field(default_factory=list)
    unresolved_items: list[dict[str, Any]] = field(default_factory=list)
    unexploitable_findings: list[dict[str, Any]] = field(default_factory=list)
    report_path: str | None = None
    pr_url: str | None = None
    # JDK version detection (for CWE-937 version source routing)
    jdk_version: int | None = None
    is_java_project: bool = False
    jdk_detection_source: str | None = None
    # Evidence & Accountability Framework (v2)
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    verification_manifest_path: str | None = None
    wiz_baseline_scan_path: str | None = None
    wiz_available: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState:
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
