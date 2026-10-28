#!/usr/bin/env python3
"""
DAF Engineer — Build Verification & Self-Healing Loop

Runs all build/test commands against a generated DAF service project.
If any command fails, outputs a structured failure report that the orchestrator
agent can parse to delegate fixes to the appropriate sub-agent.

The loop runs up to MAX_ITERATIONS (7) times. On each iteration:
  1. compileJava
  2. test (unit tests)
  3. pitest (mutation testing)
  4. integrationTest (if enabled)
  5. Full build (clean build test)

If all pass → exits 0 with SUCCESS report.
If any fail → outputs FAILURE report with diagnosis and suggested agent.
The orchestrator reads stdout, dispatches the fix agent, then re-invokes this script.

Usage:
    python3 build_verify.py <project_dir> [--max-iterations 7] [--skip-integration]

Output format (stdout):
    ---BUILD-VERIFY-START---
    { JSON report }
    ---BUILD-VERIFY-END---
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class Stage(str, Enum):
    COMPILE = "compileJava"
    UNIT_TEST = "test"
    PITEST = "pitest"
    INTEGRATION_TEST = "integrationTest"
    FULL_BUILD = "clean_build_test"


# Maps failure stage to the sub-agent best suited to fix it
STAGE_TO_AGENT = {
    Stage.COMPILE: "daf-compliance-fixer-agent",
    Stage.UNIT_TEST: "daf-test-agent",
    Stage.PITEST: "daf-test-agent",
    Stage.INTEGRATION_TEST: "daf-test-agent",
    Stage.FULL_BUILD: "daf-compliance-fixer-agent",
}

# Maps failure patterns to more specific agent recommendations
FAILURE_PATTERN_AGENTS = [
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.controller", "daf-controller-agent"),
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.service", "daf-service-agent"),
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.gateway", "daf-gateway-sub-agent"),
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.model", "daf-model-agent"),
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.dto", "daf-model-agent"),
    (r"cannot find symbol.*import com\.barclays\.api\.\w+\.config", "daf-config-agent"),
    (r"Execution failed for task ':checkstyle", "daf-compliance-fixer-agent"),
    (r"Execution failed for task ':spotless", "daf-compliance-fixer-agent"),
    (r"ResponseEntity", "daf-compliance-fixer-agent"),
    (r"package .* does not exist", "daf-build-agent"),
    (r"Could not resolve.*daf-", "daf-build-agent"),
    (r"jacocoTestCoverageVerification.*FAILED", "daf-test-agent"),
    (r"Mutation testing.*below threshold", "daf-test-agent"),
    (r"WireMock\|wiremock\|Karate\|karate", "daf-test-agent"),
]


@dataclass
class StageResult:
    stage: str
    command: str
    exit_code: int
    passed: bool
    duration_seconds: float
    stdout_tail: str = ""
    stderr_tail: str = ""
    error_summary: str = ""


@dataclass
class IterationReport:
    iteration: int
    max_iterations: int
    status: str  # "passed" | "failed"
    stages_run: int = 0
    stages_passed: int = 0
    failed_stage: Optional[str] = None
    suggested_agent: Optional[str] = None
    error_summary: str = ""
    error_output: str = ""
    metrics: dict = field(default_factory=dict)
    stage_results: list = field(default_factory=list)
    duration_seconds: float = 0.0


def run_gradle_command(project_dir: Path, task: str, timeout: int = 600) -> StageResult:
    """Run a Gradle task and return structured result."""
    if task == "clean_build_test":
        cmd = ["./gradlew", "clean", "build", "test"]
    else:
        cmd = ["./gradlew", task]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start
        combined_output = result.stdout + "\n" + result.stderr

        # Extract error summary from output
        error_summary = ""
        if result.returncode != 0:
            error_summary = extract_error_summary(combined_output)

        return StageResult(
            stage=task,
            command=" ".join(cmd),
            exit_code=result.returncode,
            passed=(result.returncode == 0),
            duration_seconds=round(duration, 2),
            stdout_tail=tail_lines(result.stdout, 80),
            stderr_tail=tail_lines(result.stderr, 40),
            error_summary=error_summary,
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return StageResult(
            stage=task,
            command=" ".join(cmd),
            exit_code=-1,
            passed=False,
            duration_seconds=round(duration, 2),
            error_summary=f"Command timed out after {timeout}s",
        )
    except Exception as e:
        duration = time.time() - start
        return StageResult(
            stage=task,
            command=" ".join(cmd),
            exit_code=-2,
            passed=False,
            duration_seconds=round(duration, 2),
            error_summary=f"Exception: {str(e)}",
        )


def extract_error_summary(output: str) -> str:
    """Extract the most relevant error lines from Gradle output."""
    lines = output.splitlines()
    error_lines = []

    # Look for "What went wrong" section
    in_error_section = False
    for i, line in enumerate(lines):
        if "What went wrong" in line:
            in_error_section = True
            continue
        if in_error_section:
            if line.startswith("* ") and "Try" in line:
                break
            if line.strip():
                error_lines.append(line.strip())
            if len(error_lines) >= 10:
                break

    # Also capture compilation errors
    for line in lines:
        if "error:" in line.lower() and (".java:" in line or ".groovy:" in line):
            error_lines.append(line.strip())
            if len(error_lines) >= 20:
                break

    # Capture test failures
    for line in lines:
        if "FAILED" in line and ("test" in line.lower() or "Test" in line):
            error_lines.append(line.strip())
            if len(error_lines) >= 20:
                break

    return "\n".join(error_lines[:20]) if error_lines else "Unknown error — check full output"


def extract_metrics(project_dir: Path) -> dict:
    """Extract coverage and test metrics from build reports."""
    metrics = {
        "tests_passed": None,
        "tests_failed": None,
        "line_coverage_pct": None,
        "branch_coverage_pct": None,
        "mutation_score_pct": None,
        "mutation_killed": None,
        "mutation_total": None,
    }

    # Parse JaCoCo XML report
    jacoco_xml = project_dir / "build" / "reports" / "jacoco" / "test" / "jacocoTestReport.xml"
    if jacoco_xml.exists():
        try:
            content = jacoco_xml.read_text()
            # Extract overall counters from the last <counter> elements (report level)
            line_match = re.findall(
                r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content
            )
            branch_match = re.findall(
                r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', content
            )
            if line_match:
                missed, covered = int(line_match[-1][0]), int(line_match[-1][1])
                total = missed + covered
                if total > 0:
                    metrics["line_coverage_pct"] = round(covered / total * 100, 1)
            if branch_match:
                missed, covered = int(branch_match[-1][0]), int(branch_match[-1][1])
                total = missed + covered
                if total > 0:
                    metrics["branch_coverage_pct"] = round(covered / total * 100, 1)
        except Exception:
            pass

    # Parse pitest report
    pitest_dir = project_dir / "build" / "reports" / "pitest"
    if pitest_dir.exists():
        # Look for mutations.xml or index.html
        for html_file in pitest_dir.rglob("index.html"):
            try:
                content = html_file.read_text()
                # Parse "Generated X mutations Killed Y (Z%)"
                match = re.search(
                    r"Generated (\d+) mutations Killed (\d+) \((\d+)%\)", content
                )
                if match:
                    metrics["mutation_total"] = int(match.group(1))
                    metrics["mutation_killed"] = int(match.group(2))
                    metrics["mutation_score_pct"] = int(match.group(3))
                    break
            except Exception:
                pass

    # Parse test results from XML
    test_results_dir = project_dir / "build" / "test-results" / "test"
    if test_results_dir.exists():
        total_tests = 0
        total_failures = 0
        for xml_file in test_results_dir.glob("*.xml"):
            try:
                content = xml_file.read_text()
                tests_match = re.search(r'tests="(\d+)"', content)
                failures_match = re.search(r'failures="(\d+)"', content)
                errors_match = re.search(r'errors="(\d+)"', content)
                if tests_match:
                    total_tests += int(tests_match.group(1))
                if failures_match:
                    total_failures += int(failures_match.group(1))
                if errors_match:
                    total_failures += int(errors_match.group(1))
            except Exception:
                pass
        if total_tests > 0:
            metrics["tests_passed"] = total_tests - total_failures
            metrics["tests_failed"] = total_failures

    return metrics


def determine_suggested_agent(stage: str, error_output: str) -> str:
    """Determine which sub-agent should fix the failure based on error patterns."""
    # Check specific patterns first
    for pattern, agent in FAILURE_PATTERN_AGENTS:
        if re.search(pattern, error_output, re.IGNORECASE):
            return agent

    # Fall back to stage-based mapping
    try:
        return STAGE_TO_AGENT[Stage(stage)]
    except (ValueError, KeyError):
        return "daf-compliance-fixer-agent"


def tail_lines(text: str, n: int = 50) -> str:
    """Return the last n lines of text."""
    lines = text.splitlines()
    return "\n".join(lines[-n:]) if len(lines) > n else text


def run_iteration(
    project_dir: Path,
    iteration: int,
    max_iterations: int,
    skip_integration: bool = False,
) -> IterationReport:
    """Run one full verification iteration."""
    start = time.time()
    report = IterationReport(iteration=iteration, max_iterations=max_iterations, status="passed")
    stage_results = []

    # Define stages to run in order
    stages = [
        Stage.COMPILE,
        Stage.UNIT_TEST,
        Stage.PITEST,
    ]
    if not skip_integration:
        stages.append(Stage.INTEGRATION_TEST)
    stages.append(Stage.FULL_BUILD)

    for stage in stages:
        print(f"  [{iteration}/{max_iterations}] Running: ./gradlew {stage.value} ...", flush=True)
        result = run_gradle_command(project_dir, stage.value)
        stage_results.append(asdict(result))
        report.stages_run += 1

        if result.passed:
            report.stages_passed += 1
            print(f"  [{iteration}/{max_iterations}] PASSED: {stage.value} ({result.duration_seconds}s)")
        else:
            print(f"  [{iteration}/{max_iterations}] FAILED: {stage.value} ({result.duration_seconds}s)")
            report.status = "failed"
            report.failed_stage = stage.value
            report.error_summary = result.error_summary
            report.error_output = result.stdout_tail + "\n" + result.stderr_tail
            report.suggested_agent = determine_suggested_agent(
                stage.value, report.error_output
            )
            # Stop at first failure — no point running subsequent stages
            break

    report.stage_results = stage_results
    report.duration_seconds = round(time.time() - start, 2)

    # Extract metrics if we got past unit tests
    if report.stages_passed >= 2:
        report.metrics = extract_metrics(project_dir)

    return report


def output_report(report: IterationReport):
    """Output the structured report for the orchestrator to parse."""
    report_dict = asdict(report)
    print("\n---BUILD-VERIFY-START---")
    print(json.dumps(report_dict, indent=2))
    print("---BUILD-VERIFY-END---")


def main():
    parser = argparse.ArgumentParser(
        description="DAF Build Verification & Self-Healing Loop"
    )
    parser.add_argument(
        "project_dir",
        help="Path to the generated DAF service project",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=7,
        help="Maximum retry iterations (default: 7)",
    )
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip integration tests (they require deployed infrastructure)",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=None,
        help="Run only a single specific iteration (for orchestrator-driven mode)",
    )

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    # Validate project directory
    if not project_dir.exists():
        print(f"ERROR: Project directory does not exist: {project_dir}", file=sys.stderr)
        sys.exit(2)

    gradlew = project_dir / "gradlew"
    if not gradlew.exists():
        print(f"ERROR: No gradlew found in: {project_dir}", file=sys.stderr)
        sys.exit(2)

    # Ensure gradlew is executable
    if not os.access(gradlew, os.X_OK):
        os.chmod(gradlew, 0o755)

    print(f"{'='*60}")
    print(f"DAF Build Verification")
    print(f"Project: {project_dir}")
    print(f"Max Iterations: {args.max_iterations}")
    print(f"Skip Integration: {args.skip_integration}")
    print(f"{'='*60}\n")

    # Single iteration mode (orchestrator calls this repeatedly)
    if args.iteration is not None:
        print(f"--- Iteration {args.iteration}/{args.max_iterations} ---")
        report = run_iteration(
            project_dir, args.iteration, args.max_iterations, args.skip_integration
        )
        output_report(report)
        sys.exit(0 if report.status == "passed" else 1)

    # Autonomous loop mode (runs all iterations internally)
    for iteration in range(1, args.max_iterations + 1):
        print(f"\n{'─'*60}")
        print(f"--- Iteration {iteration}/{args.max_iterations} ---")
        print(f"{'─'*60}\n")

        report = run_iteration(
            project_dir, iteration, args.max_iterations, args.skip_integration
        )
        output_report(report)

        if report.status == "passed":
            print(f"\n{'='*60}")
            print(f"BUILD VERIFICATION PASSED on iteration {iteration}/{args.max_iterations}")
            print(f"{'='*60}")
            sys.exit(0)

        if iteration < args.max_iterations:
            print(f"\n  Failure detected. Suggested agent: {report.suggested_agent}")
            print(f"  Error: {report.error_summary[:200]}")
            print(f"  Orchestrator should delegate fix and re-run.\n")
            # In autonomous mode, we just report — the orchestrator handles the fix
            # Exit with code 1 so the orchestrator knows to intervene
            sys.exit(1)

    # All iterations exhausted
    print(f"\n{'='*60}")
    print(f"BUILD VERIFICATION FAILED after {args.max_iterations} iterations")
    print(f"{'='*60}")
    sys.exit(1)


if __name__ == "__main__":
    main()
