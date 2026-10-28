#!/usr/bin/env python3
"""Repository setup — clone, branch creation, .gitignore update.

Input (JSON stdin):
    {
        "repo_url": "https://app.gitlab.barcapint.com/org/repo.git",  (or local path)
        "cwe_ids": ["CWE-89", "CWE-79"],
        "clone_dir": null,  (optional)
        "base_branch": "main",
        "git_pat_env_var": "GIT_PAT",
        "checkout_branch": null,
        "new_branch": null,
        "jira_id": null
    }

Output (JSON stdout):
    {"status": "success", "clone_dir": "...", "branch_name": "...", ...}
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import (
    read_json_input, write_json_output, run_cmd, sanitize_pat, shell_quote, log,
    progress, progress_done,
    check_barclays_setup, BARCLAYS_SETUP_INSTRUCTION,
)
from scripts.core.errors import error_exit


# .detox/ holds per-run working files (pipeline state, WIZ baseline scan) — never commit.
GITIGNORE_ENTRIES = ["DETOX-REMEDIATION-REPORT.md", "corrective_actions_output/", ".detox/"]
MAX_FRESH_DIR_ATTEMPTS = 100


def is_git_url(path: str) -> bool:
    """Determine if path is a remote URL vs local directory."""
    return path.startswith("https://") or path.startswith("git@")


def extract_repo_name(url: str) -> str:
    """Extract repository name from a git URL."""
    path = urlparse(url).path if url.startswith("https://") else url.split(":")[-1]
    name = Path(path).stem  # Removes .git suffix
    return name or "repo"


def find_fresh_dir(base_name: str, parent: Path) -> Path:
    """Find a fresh directory name using incremental numbering.

    Raises error if more than MAX_FRESH_DIR_ATTEMPTS exist.
    """
    target = parent / base_name
    if not target.exists():
        return target
    for n in range(1, MAX_FRESH_DIR_ATTEMPTS + 1):
        candidate = parent / f"{base_name}-{n}"
        if not candidate.exists():
            return candidate
    error_exit(
        f"Cannot find fresh directory after {MAX_FRESH_DIR_ATTEMPTS} attempts. "
        f"Clean up existing '{base_name}-*' directories.",
        "clone_prep",
    )


def validate_branch_name(name: str) -> bool:
    """Validate that a branch name is safe for git operations."""
    # Git branch name rules: no spaces, no .., no ASCII control chars,
    # no ~^:?\*[, cannot start/end with /, cannot end with .lock
    if not name or len(name) > 255:
        return False
    if ".." in name or name.startswith("/") or name.endswith("/"):
        return False
    if any(c in name for c in " ~^:?*[\\"):
        return False
    if name.endswith(".lock"):
        return False
    return True


def generate_branch_name(cwe_ids: list[str], jira_id: str | None = None) -> str:
    """Generate branch name from CWE IDs and timestamp."""
    # Sort and extract numeric parts
    nums = sorted(set(
        int(re.search(r"\d+", cwe).group())
        for cwe in cwe_ids if re.search(r"\d+", cwe)
    ))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    cwe_part = "-".join(str(n) for n in nums)
    branch = f"remediate-cwe-{cwe_part}-{timestamp}"

    # Truncate if too long
    if len(branch) > 100:
        cwe_part = "-".join(str(n) for n in nums[:3]) + "-and-more"
        branch = f"remediate-cwe-{cwe_part}-{timestamp}"

    return branch


def update_gitignore(repo_dir: Path) -> bool:
    """Append detox entries to .gitignore if not already present."""
    gitignore = repo_dir / ".gitignore"
    existing_content = ""
    if gitignore.exists():
        existing_content = gitignore.read_text()

    lines_to_add = []
    for entry in GITIGNORE_ENTRIES:
        if entry not in existing_content:
            lines_to_add.append(entry)

    if lines_to_add:
        with open(gitignore, "a") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            for line in lines_to_add:
                f.write(f"{line}\n")
        return True
    return False


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    # HARD GATE (defense in depth): Stage 1 is the first script the orchestrator
    # runs, so enforce the mandatory Barclays user setup here in CODE — not just
    # in the orchestrator's Stage 0 prose (which an LLM can skip or ignore). If
    # ANY of the four barclays_* keys is missing/empty, refuse to run and show
    # the setup banner. Bypassable only with an explicit skip flag (test harness).
    if not input_data.get("skip_barclays_setup", False):
        setup_check = check_barclays_setup()
        if not setup_check["available"]:
            missing = ", ".join(setup_check["missing_keys"])
            error_exit(
                f"{BARCLAYS_SETUP_INSTRUCTION}\n\nMissing: {missing}",
                "barclays_setup",
            )

    repo_url = input_data.get("repo_url")
    cwe_ids = input_data.get("cwe_ids", [])
    clone_dir = input_data.get("clone_dir")
    # Explicit MR target; when absent, use the branch the work branch is created from.
    explicit_base_branch = input_data.get("base_branch")
    base_branch = explicit_base_branch
    pat_env_var = input_data.get("git_pat_env_var", "GIT_PAT")
    checkout_branch = input_data.get("checkout_branch")
    new_branch = input_data.get("new_branch")
    jira_id = input_data.get("jira_id")

    if not repo_url:
        error_exit("repo_url is required", "input_validation")

    # Determine if this is a remote clone or local path
    if is_git_url(repo_url):
        progress(f"Cloning repository — {extract_repo_name(repo_url)}...")
        # Remote repository — clone it
        pat = os.environ.get(pat_env_var, "")
        if not pat:
            error_exit(
                f"Environment variable {pat_env_var} is not set or empty. "
                "A Personal Access Token is required for cloning.",
                "pat_validation",
            )

        # Ensure URL ends with .git
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        # Determine clone directory
        repo_name = extract_repo_name(repo_url)
        if clone_dir:
            target_dir = Path(clone_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            if any(target_dir.iterdir()):
                error_exit(
                    f"Clone directory is not empty: {clone_dir}. Provide an empty directory.",
                    "clone_prep",
                )
        else:
            target_dir = find_fresh_dir(repo_name, Path.cwd())

        # Clone with credentials via environment to avoid logging token in URLs
        log(f"Cloning {repo_url} into {target_dir}")

        # If checkout_branch is specified and different from base_branch, don't use --single-branch
        # so we can fetch all branches and checkout the requested one
        use_single_branch = not checkout_branch or checkout_branch == base_branch

        # Use http.extraHeader approach for credential passing (safer than embedding in URL)
        clone_cmd = ["git", "clone"]
        if use_single_branch:
            clone_cmd.append("--single-branch")
            if base_branch:  # otherwise the remote's default branch
                clone_cmd.extend(["--branch", base_branch])
        clone_cmd.extend([repo_url, str(target_dir)])

        git_env = os.environ.copy()
        git_env["GIT_ASKPASS"] = "echo"
        git_env["GIT_ASKPASS_RESULT"] = pat

        result = run_cmd(clone_cmd, timeout=300, env=git_env)

        if result["exit_code"] != 0:
            stderr = sanitize_pat(result["stdout"] + result["stderr"], pat_env_var)

            # Try master as fallback if branch not found
            if base_branch and result["exit_code"] != 0 and ("not found" in stderr.lower() or "Remote branch" in stderr):
                log("Branch not found, retrying with 'master'")
                fallback_clone_cmd = ["git", "clone", "--single-branch", "--branch", "master", repo_url, str(target_dir)]
                result = run_cmd(fallback_clone_cmd, timeout=300, env=git_env)
                if result["exit_code"] == 0:
                    base_branch = "master"
                else:
                    stderr = sanitize_pat(result["stdout"] + result["stderr"], pat_env_var)

            if result["exit_code"] != 0:
                stderr = sanitize_pat(result["stdout"] + result["stderr"], pat_env_var)
                error_exit(f"Clone failed: {stderr}", "clone")

        # Verify clone
        if not (target_dir / ".git").is_dir():
            error_exit("Clone appeared to succeed but .git directory not found", "clone_verify")

        project_path = target_dir

    else:
        progress(f"Setting up local repository — {repo_url}")
        # Local path
        project_path = Path(repo_url).resolve()
        if not project_path.is_dir():
            error_exit(f"Local path does not exist: {repo_url}", "input_validation")
        if not (project_path / ".git").is_dir():
            error_exit(f"Not a git repository: {repo_url}", "input_validation")

    # Checkout existing branch if requested
    if checkout_branch:
        if not validate_branch_name(checkout_branch):
            error_exit(
                f"Invalid branch name: {checkout_branch}",
                "branch_checkout",
            )
        result = run_cmd(
            ["git", "checkout", checkout_branch],
            cwd=project_path,
        )
        if result["exit_code"] != 0:
            # Branch may not be available locally in shallow clone, try to fetch it
            log(f"Branch not available locally, attempting to fetch {checkout_branch}...")
            fetch_result = run_cmd(
                ["git", "fetch", "origin", f"{checkout_branch}:{checkout_branch}"],
                cwd=project_path,
            )
            if fetch_result["exit_code"] == 0:
                # Try checkout again
                result = run_cmd(
                    ["git", "checkout", checkout_branch],
                    cwd=project_path,
                )

            if result["exit_code"] != 0:
                error_exit(
                    f"Failed to checkout branch {checkout_branch}: {result['stderr']}",
                    "branch_checkout",
                )

    # The work branch is created from whatever is checked out now — that is the MR target
    # unless the caller named one explicitly.
    if not explicit_base_branch:
        current = run_cmd(["git", "branch", "--show-current"], cwd=project_path)["stdout"].strip()
        base_branch = current or base_branch or "main"

    # Create working branch
    if new_branch:
        branch_name = new_branch
    elif cwe_ids:
        branch_name = generate_branch_name(cwe_ids, jira_id)
    else:
        branch_name = f"remediate-detox-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    if not validate_branch_name(branch_name):
        error_exit(f"Generated branch name is invalid: {branch_name}", "branch_creation")

    result = run_cmd(["git", "checkout", "-b", branch_name], cwd=project_path)
    if result["exit_code"] != 0:
        error_exit(
            f"Failed to create branch {branch_name}: {result['stderr']}",
            "branch_creation",
        )

    # Verify branch
    result = run_cmd(["git", "branch", "--show-current"], cwd=project_path)
    actual_branch = result["stdout"].strip()
    if actual_branch != branch_name:
        error_exit(
            f"Branch mismatch: expected {branch_name}, got {actual_branch}",
            "branch_verify",
        )

    # Update .gitignore
    gitignore_updated = update_gitignore(project_path)

    # Get HEAD commit
    result = run_cmd(["git", "rev-parse", "HEAD"], cwd=project_path)
    head_sha = result["stdout"].strip()

    progress_done(f"Repository ready on branch {branch_name}")

    write_json_output({
        "status": "success",
        "clone_dir": str(project_path),
        "branch_name": branch_name,
        "base_branch": base_branch,
        "commit_sha_head": head_sha,
        "gitignore_updated": gitignore_updated,
        "cwe_ids": cwe_ids,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
