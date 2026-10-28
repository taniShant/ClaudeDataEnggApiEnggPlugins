#!/usr/bin/env python3
"""Detect build system and run build command.

Input (JSON stdin):
    {"repo_dir": "/path/to/repo", "timeout_seconds": 300}

Output (JSON stdout):
    {"status": "success", "build_system": "gradle", "command_executed": "...", ...}
"""

from __future__ import annotations

import json
import shlex
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


# Build system detection rules (ordered by priority)
BUILD_SYSTEMS = [
    {
        "name": "gradle",
        "indicators": ["build.gradle", "build.gradle.kts"],
        "command_with_wrapper": "./gradlew build",
        "command_without_wrapper": "gradle build",
        "wrapper_file": "gradlew",
    },
    {
        "name": "maven",
        "indicators": ["pom.xml"],
        "command_with_wrapper": "./mvnw compile",
        "command_without_wrapper": "mvn compile",
        "wrapper_file": "mvnw",
    },
    {
        "name": "npm",
        "indicators": ["package.json"],
        "command_with_wrapper": "npm run build",
        "command_without_wrapper": "npm run build",
        "wrapper_file": None,
    },
    {
        "name": "go",
        "indicators": ["go.mod"],
        "command_with_wrapper": "go build ./...",
        "command_without_wrapper": "go build ./...",
        "wrapper_file": None,
    },
    {
        "name": "cargo",
        "indicators": ["Cargo.toml"],
        "command_with_wrapper": "cargo build",
        "command_without_wrapper": "cargo build",
        "wrapper_file": None,
    },
    {
        "name": "dotnet",
        "indicators": ["*.csproj", "*.sln"],
        "command_with_wrapper": "dotnet build",
        "command_without_wrapper": "dotnet build",
        "wrapper_file": None,
    },
]


def detect_build_system(repo_dir: Path) -> dict | None:
    """Detect the build system by checking for indicator files."""
    for bs in BUILD_SYSTEMS:
        for indicator in bs["indicators"]:
            if "*" in indicator:
                # Glob pattern
                matches = list(repo_dir.glob(indicator))
                if matches:
                    return bs
            else:
                if (repo_dir / indicator).exists():
                    return bs
    return None


def check_npm_has_build(repo_dir: Path) -> bool:
    """Check if package.json has a build script."""
    pkg = repo_dir / "package.json"
    if not pkg.exists():
        return False
    try:
        with open(pkg) as f:
            data = json.load(f)
        return "build" in data.get("scripts", {})
    except (json.JSONDecodeError, KeyError):
        return False


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    timeout = input_data.get("timeout_seconds", 300)

    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")

    repo_path = Path(repo_dir)
    if not repo_path.is_dir():
        error_exit(f"Directory not found: {repo_dir}", "dir_check")

    # Detect build system
    progress("Detecting build system...")
    bs = detect_build_system(repo_path)
    if bs is None:
        write_json_output({
            "status": "success",
            "build_system": None,
            "command_executed": None,
            "exit_code": 0,
            "overall": "SKIP",
            "warnings": ["No build system detected. Skipping build validation."],
            "raw_output_tail": "",
        }, start_time=start_time)
        return

    # Special handling for npm: check if build script exists
    if bs["name"] == "npm" and not check_npm_has_build(repo_path):
        write_json_output({
            "status": "success",
            "build_system": "npm",
            "command_executed": None,
            "exit_code": 0,
            "overall": "SKIP",
            "warnings": ["package.json found but no 'build' script defined. Skipping."],
            "raw_output_tail": "",
        }, start_time=start_time)
        return

    # Determine command (list-form for injection safety)
    if bs["wrapper_file"] and (repo_path / bs["wrapper_file"]).exists():
        command_str = bs["command_with_wrapper"]
    else:
        command_str = bs["command_without_wrapper"]

    # Convert command string to list-form for safe execution
    cmd_parts = shlex.split(command_str)

    # Run build (list-form: injection-safe, no shell interpretation)
    progress(f"Running build — {bs['name']} ({command_str})...")
    log(f"Running build: {command_str}")
    result = run_cmd(cmd_parts, cwd=repo_path, timeout=timeout)

    overall = "PASS" if result["exit_code"] == 0 else "FAIL"
    progress_done(f"Build {overall} ({bs['name']})")

    # Truncate output to last 100 lines
    output_lines = (result["stdout"] + result["stderr"]).splitlines()
    raw_tail = "\n".join(output_lines[-100:]) if len(output_lines) > 100 else "\n".join(output_lines)

    warnings = []
    if result["exit_code"] == -1 and "timed out" in result["stderr"]:
        overall = "ERROR"
        warnings.append(f"Build timed out after {timeout} seconds.")

    write_json_output({
        "status": "success",
        "build_system": bs["name"],
        "command_executed": command_str,
        "exit_code": result["exit_code"],
        "overall": overall,
        "warnings": warnings,
        "raw_output_tail": raw_tail,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
