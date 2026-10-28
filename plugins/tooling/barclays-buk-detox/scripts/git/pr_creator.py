#!/usr/bin/env python3
"""Push branch and create merge request via glab (GitLab CLI).

Input (JSON stdin):
    {
        "repo_dir": "/path/to/repo",
        "branch_name": "remediate-cwe-79-89-20260429-143000",
        "base_branch": "main",
        "mr_title": "fix: CWE remediation for CWE-79, CWE-89",
        "mr_body": "## Summary\n...",
        "labels": ["security", "cwe-remediation", "automated"],
        "reviewers": [],
        "draft": false
    }

Output (JSON stdout):
    {"status": "success", "mr_url": "...", "mr_iid": 42, ...}
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, sanitize_pat, log, progress, progress_done
from scripts.core.errors import error_exit


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    branch_name = input_data.get("branch_name", "")
    base_branch = input_data.get("base_branch", "main")
    mr_title = input_data.get("mr_title", "")
    mr_body = input_data.get("mr_body", "")
    labels = input_data.get("labels", ["security", "cwe-remediation", "automated"])
    reviewers = input_data.get("reviewers", [])
    draft = input_data.get("draft", False)

    # Support deprecated pr_title/pr_body with warning
    warnings = []
    if not mr_title and input_data.get("pr_title"):
        mr_title = input_data["pr_title"]
        warnings.append("'pr_title' is deprecated. Use 'mr_title' instead.")
    if not mr_body and input_data.get("pr_body"):
        mr_body = input_data["pr_body"]
        warnings.append("'pr_body' is deprecated. Use 'mr_body' instead.")

    # --- Validate inputs ---
    repo_path = Path(repo_dir)
    if not (repo_path / ".git").is_dir():
        error_exit(f"Not a git repository: {repo_dir}", "validation")
    if not branch_name:
        error_exit("branch_name is required", "validation")
    if not mr_title:
        error_exit("mr_title is required", "validation")
    if len(mr_title) > 256:
        mr_title = mr_title[:253] + "..."
    if not mr_body:
        error_exit("mr_body is required", "validation")

    # --- Verify current branch ---
    result = run_cmd(["git", "branch", "--show-current"], cwd=repo_path)
    current_branch = result["stdout"].strip()
    if current_branch != branch_name:
        result = run_cmd(["git", "checkout", branch_name], cwd=repo_path)
        if result["exit_code"] != 0:
            error_exit(f"Branch {branch_name} does not exist locally.", "branch_check")

    # --- Verify there are commits to push ---
    if not base_branch:
        result = run_cmd(
            ["git", "remote", "show", "origin"],
            cwd=repo_path,
        )
        if result["exit_code"] == 0 and "HEAD branch" in result["stdout"]:
            for line in result["stdout"].splitlines():
                if "HEAD branch" in line:
                    base_branch = line.strip().split()[-1]
                    break
        if not base_branch:
            base_branch = "main"

    result = run_cmd(
        ["git", "log", f"{base_branch}..HEAD", "--oneline"],
        cwd=repo_path,
    )
    if result["exit_code"] != 0 or not result["stdout"].strip():
        error_exit("No commits found on branch. Nothing to push or create an MR for.", "branch_check")

    commits_count = len(result["stdout"].strip().splitlines())

    # --- Verify glab CLI ---
    result = run_cmd(["glab", "--version"])
    if result["exit_code"] != 0:
        error_exit(
            "GitLab CLI (glab) is not installed.\n"
            "Mac: brew install glab\n"
            "Windows: Install gitlabcli using Dev CLI.\n"
            "Then configure: glab config set --global host https://app.gitlab.barcapint.com",
            "glab_check",
        )

    result = run_cmd(["glab", "auth", "status"])
    if result["exit_code"] != 0:
        error_exit(
            "GitLab CLI is not authenticated.\n"
            "Run: glab config set --global host https://app.gitlab.barcapint.com\n"
            "Run: glab config set --global token YOUR_PERSONAL_ACCESS_TOKEN\n"
            "Create token at: https://app.gitlab.barcapint.com/-/user_settings/personal_access_tokens",
            "glab_check",
        )

    # --- Push branch (list-form for safety) ---
    progress(f"Pushing branch {branch_name} and creating merge request...")
    log(f"Pushing branch {branch_name}")
    result = run_cmd(
        ["git", "push", "-u", "origin", branch_name],
        cwd=repo_path,
    )
    if result["exit_code"] != 0:
        output = sanitize_pat(result["stdout"] + result["stderr"])
        # Try without -u if branch already exists on remote
        if "already exists" in output.lower() or "updates were rejected" in output.lower():
            result = run_cmd(
                ["git", "push", "origin", branch_name],
                cwd=repo_path,
            )
            if result["exit_code"] != 0:
                output = sanitize_pat(result["stdout"] + result["stderr"])
                error_exit(f"Push failed: {output}", "push")
        else:
            error_exit(f"Push failed: {output}", "push")

    # --- Create Merge Request ---
    # Build glab command as a list (injection-safe, no shell interpretation)
    cmd = [
        "glab", "mr", "create",
        "--title", mr_title,
        "--description", mr_body,
        "--source-branch", branch_name,
        "--target-branch", base_branch,
        "--remove-source-branch",
    ]
    for label in labels:
        cmd.extend(["--label", label])
    for reviewer in reviewers:
        cmd.extend(["--reviewer", reviewer])
    if draft:
        cmd.append("--draft")

    log(f"Creating MR: {mr_title}")
    result = run_cmd(cmd, cwd=repo_path, timeout=60)

    if result["exit_code"] != 0:
        output = result["stdout"] + result["stderr"]
        # Check if MR already exists
        if "already exists" in output.lower() or "already a merge request" in output.lower():
            # Try to get existing MR
            result = run_cmd(
                ["glab", "mr", "list", "--source-branch", branch_name, "--json"],
                cwd=repo_path,
            )
            if result["exit_code"] == 0 and result["stdout"].strip():
                try:
                    mr_list = json.loads(result["stdout"])
                    if mr_list and len(mr_list) > 0:
                        mr_data = mr_list[0]
                        write_json_output({
                            "status": "success",
                            "mr_url": mr_data.get("web_url", ""),
                            "mr_iid": mr_data.get("iid", 0),
                            "mr_title": mr_data.get("title", mr_title),
                            "branch_name": branch_name,
                            "base_branch": base_branch,
                            "state": mr_data.get("state", "opened"),
                            "draft": draft,
                            "labels": labels,
                            "reviewers": reviewers,
                            "commits_included": commits_count,
                            "warnings": warnings + ["Merge request already existed for this branch."],
                        }, start_time=start_time)
                        return
                except json.JSONDecodeError:
                    pass
        error_exit(f"MR creation failed: {output}", "mr_creation")

    # Extract MR URL from output (glab mr create prints the URL)
    mr_url = ""
    for line in result["stdout"].strip().splitlines():
        if "http" in line:
            mr_url = line.strip()
            break

    # --- Verify MR ---
    mr_iid = 0
    state = "opened"
    result = run_cmd(
        ["glab", "mr", "view", branch_name, "--output", "json"],
        cwd=repo_path,
    )
    if result["exit_code"] == 0 and result["stdout"].strip():
        try:
            mr_data = json.loads(result["stdout"])
            mr_iid = mr_data.get("iid", 0)
            mr_url = mr_data.get("web_url", mr_url)
            state = mr_data.get("state", "opened")
        except json.JSONDecodeError:
            pass

    progress_done(f"Merge request created — {mr_url or mr_title}")

    write_json_output({
        "status": "success",
        "mr_url": mr_url,
        "mr_iid": mr_iid,
        "mr_title": mr_title,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "state": state,
        "draft": draft,
        "labels": labels,
        "reviewers": reviewers,
        "commits_included": commits_count,
        "warnings": warnings,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
