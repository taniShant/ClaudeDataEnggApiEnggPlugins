#!/usr/bin/env python3
"""
DAF Engineer — Self-Healing Build Loop (Orchestrator Interface)

This script is the top-level entry point that:
  1. Runs build_verify.py to check if the project compiles/tests pass
  2. If it fails, produces a structured fix request for the orchestrator agent
  3. The orchestrator delegates to the appropriate sub-agent
  4. After the fix, this script is re-invoked for the next iteration

The orchestrator agent calls this script once per iteration using --iteration N.
Between iterations, the orchestrator reads the output, dispatches fixes, then
calls again with --iteration N+1.

Alternatively, use --autonomous mode where this script drives all 7 iterations
and outputs fix requests between each. The orchestrator must hook into the
stdout stream.

Usage (orchestrator-driven, recommended):
    # Iteration 1
    python3 build_heal_loop.py /path/to/project --iteration 1

    # If failed → orchestrator reads report, dispatches fix agent
    # Then:
    python3 build_heal_loop.py /path/to/project --iteration 2
    # ... up to iteration 7

Usage (standalone — prints all reports, exits on first success or max iterations):
    python3 build_heal_loop.py /path/to/project --autonomous

Exit codes:
    0 = Build passed (all stages green)
    1 = Build failed (fix needed — see report)
    2 = Invalid arguments / project not found
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
VERIFY_SCRIPT = SCRIPT_DIR / "build_verify.py"

MAX_ITERATIONS = 7

# Agent descriptions for the orchestrator to use in delegation prompts
AGENT_FIX_CONTEXT = {
    "daf-build-agent": (
        "Fix build.gradle, daf-dependencies.gradle, gradle.properties, or settings.gradle. "
        "Resolve dependency issues, plugin configuration, or missing module declarations."
    ),
    "daf-compliance-fixer-agent": (
        "Fix SDK3 compliance issues: replace ResponseEntity with RestResponse, fix Logger usage, "
        "correct ErrorCodes enum, fix import ordering, spotless/checkstyle violations."
    ),
    "daf-test-agent": (
        "Fix failing unit tests, improve mutation test coverage, fix Spock test compilation, "
        "or fix integration test configuration. Read the actual source code before fixing tests."
    ),
    "daf-controller-agent": (
        "Fix controller-related compilation errors: missing imports, wrong method signatures, "
        "RestResponse usage, or DafHeadersContext injection issues."
    ),
    "daf-service-agent": (
        "Fix service layer issues: interface/implementation mismatch, missing methods, "
        "incorrect dependency injection, or business logic errors."
    ),
    "daf-gateway-sub-agent": (
        "Fix gateway layer issues: RestTemplate configuration, response mapping, "
        "error handling, or downstream API connection problems."
    ),
    "daf-model-agent": (
        "Fix model/DTO issues: missing fields, incorrect annotations, builder pattern errors, "
        "or serialization problems."
    ),
    "daf-config-agent": (
        "Fix application configuration: application.properties, bean definitions, "
        "Spring configuration classes, or profile-specific settings."
    ),
}


def run_verify(project_dir: Path, iteration: int, skip_integration: bool) -> dict:
    """Run build_verify.py and parse its structured output."""
    cmd = [
        sys.executable,
        str(VERIFY_SCRIPT),
        str(project_dir),
        "--iteration", str(iteration),
        "--max-iterations", str(MAX_ITERATIONS),
    ]
    if skip_integration:
        cmd.append("--skip-integration")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

    # Parse the structured report from stdout
    stdout = result.stdout
    report = None

    start_marker = "---BUILD-VERIFY-START---"
    end_marker = "---BUILD-VERIFY-END---"

    if start_marker in stdout and end_marker in stdout:
        json_str = stdout.split(start_marker)[1].split(end_marker)[0].strip()
        try:
            report = json.loads(json_str)
        except json.JSONDecodeError:
            pass

    if report is None:
        report = {
            "iteration": iteration,
            "max_iterations": MAX_ITERATIONS,
            "status": "failed",
            "failed_stage": "unknown",
            "error_summary": f"Could not parse verify output. Exit code: {result.returncode}",
            "error_output": stdout[-2000:] if stdout else result.stderr[-2000:],
            "suggested_agent": "daf-compliance-fixer-agent",
            "metrics": {},
            "stage_results": [],
        }

    return report


def build_fix_request(report: dict, project_dir: Path) -> dict:
    """Build a structured fix request for the orchestrator agent."""
    agent = report.get("suggested_agent", "daf-compliance-fixer-agent")
    agent_context = AGENT_FIX_CONTEXT.get(agent, "Fix the reported issue.")

    return {
        "action": "fix_required",
        "iteration": report["iteration"],
        "max_iterations": report["max_iterations"],
        "remaining_attempts": report["max_iterations"] - report["iteration"],
        "project_dir": str(project_dir),
        "failed_stage": report.get("failed_stage"),
        "suggested_agent": agent,
        "agent_subagent_type": f"daf-engineer:{agent}",
        "agent_context": agent_context,
        "error_summary": report.get("error_summary", ""),
        "error_output": report.get("error_output", "")[:3000],
        "fix_prompt": build_fix_prompt(report, project_dir, agent),
    }


def build_fix_prompt(report: dict, project_dir: Path, agent: str) -> str:
    """Build the prompt the orchestrator should pass to the fix agent."""
    return (
        f"FIX THE BUILD FAILURE in project at: {project_dir}\n\n"
        f"Failed stage: {report.get('failed_stage')}\n"
        f"Iteration: {report['iteration']}/{report['max_iterations']} "
        f"({report['max_iterations'] - report['iteration']} attempts remaining)\n\n"
        f"Error summary:\n{report.get('error_summary', 'Unknown')}\n\n"
        f"Error output (tail):\n{report.get('error_output', '')[:2000]}\n\n"
        f"Instructions:\n"
        f"1. Read the failing file(s) mentioned in the error\n"
        f"2. Identify the root cause\n"
        f"3. Apply the minimal fix\n"
        f"4. Do NOT introduce new issues\n"
        f"5. Verify your fix compiles: ./gradlew compileJava\n"
    )


def output_heal_report(report: dict, fix_request: dict = None):
    """Output the structured report for the orchestrator."""
    output = {
        "verify_report": report,
    }
    if fix_request:
        output["fix_request"] = fix_request

    print("\n---HEAL-LOOP-START---")
    print(json.dumps(output, indent=2))
    print("---HEAL-LOOP-END---")


def main():
    parser = argparse.ArgumentParser(
        description="DAF Self-Healing Build Loop — Orchestrator Interface"
    )
    parser.add_argument(
        "project_dir",
        help="Path to the generated DAF service project",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=None,
        help="Run a specific iteration (1-7). Orchestrator calls with incrementing values.",
    )
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Run all iterations autonomously (no orchestrator intervention — just reports)",
    )
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip integration tests",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Maximum iterations (default: {MAX_ITERATIONS})",
    )

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    max_iters = args.max_iterations

    if not project_dir.exists():
        print(f"ERROR: Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(2)

    if not (project_dir / "gradlew").exists():
        print(f"ERROR: No gradlew in project: {project_dir}", file=sys.stderr)
        sys.exit(2)

    # Single iteration mode (orchestrator-driven)
    if args.iteration is not None:
        if args.iteration < 1 or args.iteration > max_iters:
            print(f"ERROR: --iteration must be 1-{max_iters}", file=sys.stderr)
            sys.exit(2)

        print(f"[HEAL-LOOP] Iteration {args.iteration}/{max_iters}")
        report = run_verify(project_dir, args.iteration, args.skip_integration)

        if report["status"] == "passed":
            print(f"\n[HEAL-LOOP] BUILD PASSED on iteration {args.iteration}")
            output_heal_report(report)
            sys.exit(0)
        else:
            fix_request = build_fix_request(report, project_dir)
            print(f"\n[HEAL-LOOP] BUILD FAILED — stage: {report.get('failed_stage')}")
            print(f"[HEAL-LOOP] Suggested agent: {report.get('suggested_agent')}")
            output_heal_report(report, fix_request)
            sys.exit(1)

    # Autonomous mode
    if args.autonomous:
        for iteration in range(1, max_iters + 1):
            print(f"\n{'='*60}")
            print(f"[HEAL-LOOP] Autonomous Iteration {iteration}/{max_iters}")
            print(f"{'='*60}")

            report = run_verify(project_dir, iteration, args.skip_integration)

            if report["status"] == "passed":
                print(f"\n[HEAL-LOOP] BUILD PASSED on iteration {iteration}")
                output_heal_report(report)
                sys.exit(0)

            fix_request = build_fix_request(report, project_dir)
            output_heal_report(report, fix_request)

            if iteration < max_iters:
                print(f"\n[HEAL-LOOP] Fix needed. Agent: {report.get('suggested_agent')}")
                print(f"[HEAL-LOOP] In autonomous mode, no agent dispatch — reporting only.")
                print(f"[HEAL-LOOP] Use orchestrator-driven mode for actual self-healing.\n")
            else:
                print(f"\n[HEAL-LOOP] Max iterations reached. Build still failing.")

        sys.exit(1)

    # Default: just run iteration 1
    print("[HEAL-LOOP] No --iteration or --autonomous specified. Running iteration 1.")
    report = run_verify(project_dir, 1, args.skip_integration)

    if report["status"] == "passed":
        output_heal_report(report)
        sys.exit(0)
    else:
        fix_request = build_fix_request(report, project_dir)
        output_heal_report(report, fix_request)
        sys.exit(1)


if __name__ == "__main__":
    main()
