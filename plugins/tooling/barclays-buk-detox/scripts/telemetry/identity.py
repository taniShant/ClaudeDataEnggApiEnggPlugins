#!/usr/bin/env python3
"""Identity resolution for Detox pipeline runs.

Captures WHO ran the pipeline and WHAT REPO is being targeted.

Input (JSON stdin):
  {"project_path": "/path/to/repo"}  (optional, for git context)

Output (JSON stdout):
  {"status": "success", "identity": {
    "user_name": "...", "user_email": "...",
    "ci_job_id": "...", "ci_pipeline_id": "...",
    "hostname": "...", "source": "git_config|gitlab_ci|jenkins|github_actions|env",
    "repo_name": "...", "repo_url": "..."
  }}

Resolution order:
  1. CI environment variables (highest priority — automated run)
  2. Git config (interactive developer)
  3. Environment fallbacks (USER, hostname)
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, get_barclays_cio
from scripts.core.errors import error_exit


def _run_git(args: list[str], cwd: str | None = None) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _extract_repo_name_from_url(url: str) -> str | None:
    """Extract repository name from a git remote URL.

    Handles both SSH and HTTPS formats:
      git@gitlab.com:group/subgroup/repo-name.git -> repo-name
      https://gitlab.com/group/subgroup/repo-name.git -> repo-name
    """
    if not url:
        return None
    # Strip trailing .git
    url = re.sub(r"\.git$", "", url.strip())
    # Get last path segment
    parts = re.split(r"[:/]", url)
    if parts:
        name = parts[-1].strip()
        if name:
            return name
    return None


def resolve_ci_identity() -> dict[str, Any] | None:
    """Detect CI environment and extract identity from env vars."""

    # GitLab CI
    if os.environ.get("CI_JOB_ID"):
        return {
            "user_name": os.environ.get("GITLAB_USER_LOGIN", os.environ.get("CI_COMMIT_AUTHOR", "")),
            "user_email": os.environ.get("GITLAB_USER_EMAIL", ""),
            "ci_job_id": os.environ.get("CI_JOB_ID"),
            "ci_pipeline_id": os.environ.get("CI_PIPELINE_ID"),
            "ci_project_name": os.environ.get("CI_PROJECT_NAME"),
            "ci_project_url": os.environ.get("CI_PROJECT_URL"),
            "source": "gitlab_ci",
        }

    # Jenkins
    if os.environ.get("BUILD_NUMBER"):
        return {
            "user_name": os.environ.get("BUILD_USER", os.environ.get("USER", "")),
            "user_email": os.environ.get("BUILD_USER_EMAIL", ""),
            "ci_job_id": os.environ.get("BUILD_NUMBER"),
            "ci_pipeline_id": os.environ.get("JOB_NAME"),
            "source": "jenkins",
        }

    # GitHub Actions
    if os.environ.get("GITHUB_ACTIONS"):
        return {
            "user_name": os.environ.get("GITHUB_ACTOR", ""),
            "user_email": "",
            "ci_job_id": os.environ.get("GITHUB_RUN_ID"),
            "ci_pipeline_id": os.environ.get("GITHUB_RUN_NUMBER"),
            "ci_project_name": os.environ.get("GITHUB_REPOSITORY", "").split("/")[-1] if os.environ.get("GITHUB_REPOSITORY") else "",
            "source": "github_actions",
        }

    return None


def resolve_git_identity(project_path: str | None) -> dict[str, Any] | None:
    """Extract identity from git config."""
    cwd = project_path if project_path and Path(project_path).is_dir() else None

    user_name = _run_git(["config", "user.name"], cwd=cwd)
    user_email = _run_git(["config", "user.email"], cwd=cwd)

    if user_name or user_email:
        return {
            "user_name": user_name or "",
            "user_email": user_email or "",
            "source": "git_config",
        }

    return None


def resolve_env_identity() -> dict[str, Any]:
    """Fallback identity from environment variables."""
    return {
        "user_name": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        "user_email": "",
        "source": "env",
    }


def resolve_repo_info(project_path: str | None) -> dict[str, str]:
    """Extract repository name and URL."""
    repo_name = ""
    repo_url = ""

    if project_path:
        cwd = project_path if Path(project_path).is_dir() else None

        # Try git remote
        if cwd:
            remote_url = _run_git(["remote", "get-url", "origin"], cwd=cwd)
            if remote_url:
                repo_url = remote_url
                extracted = _extract_repo_name_from_url(remote_url)
                if extracted:
                    repo_name = extracted

        # Fallback to basename of project_path
        if not repo_name:
            repo_name = Path(project_path).name

    return {"repo_name": repo_name, "repo_url": repo_url}


def resolve_identity(input_data: dict[str, Any]) -> dict[str, Any]:
    """Resolve full identity context."""
    project_path = input_data.get("project_path")

    # Priority: CI > git config > env
    identity = resolve_ci_identity()
    if not identity:
        identity = resolve_git_identity(project_path)
    if not identity:
        identity = resolve_env_identity()

    # Always add hostname
    try:
        identity["hostname"] = socket.gethostname()
    except OSError:
        identity["hostname"] = "unknown"

    # Always resolve repo info
    repo_info = resolve_repo_info(project_path)
    identity["repo_name"] = repo_info["repo_name"]
    identity["repo_url"] = repo_info["repo_url"]

    # Barclays CIO (from the mandatory user setup) — for adoption attribution.
    identity["cio"] = get_barclays_cio()

    # Ensure all expected fields exist
    identity.setdefault("ci_job_id", None)
    identity.setdefault("ci_pipeline_id", None)

    return {"status": "success", "identity": identity}


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    result = resolve_identity(input_data)
    write_json_output(result, start_time=start_time)


if __name__ == "__main__":
    main()
