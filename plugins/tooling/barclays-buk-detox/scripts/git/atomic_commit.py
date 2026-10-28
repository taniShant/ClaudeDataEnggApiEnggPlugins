#!/usr/bin/env python3
"""Create an atomic git commit for one CWE remediation fix.

Input (JSON stdin):
    {
        "cwe_id": "CWE-89",
        "files": ["/absolute/path/to/file.py"],
        "description": "Parameterize SQL queries in user_repository.py",
        "repo_dir": "/path/to/repo",
        "jira_id": null,
        "verification_result": {"verdict": "PASS"},
        "allow_unvalidated": false
    }

Output (JSON stdout):
    {"status": "success", "commit_sha": "...", "commit_message_subject": "...", ...}
"""

from __future__ import annotations

import re
import sys
import tempfile
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


# Expanded secret file patterns — names and extensions that should never be committed
SECRET_FILE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "credentials.json", "secrets.json", "service-account.json",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    ".htpasswd", ".netrc",
}

SECRET_FILE_EXTENSIONS = {
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore",
    ".secret", ".crt",
}


def is_secret_file(file_path: str) -> bool:
    """Check if a file matches secret file patterns."""
    name = Path(file_path).name.lower()
    suffix = Path(file_path).suffix.lower()

    if name in SECRET_FILE_NAMES:
        return True
    if suffix in SECRET_FILE_EXTENSIONS:
        return True
    # Match .env.* variants
    if name.startswith(".env"):
        return True
    return False


def build_subject(cwe_id: str, description: str, jira_id: str | None = None,
                  max_len: int = 72) -> str:
    """Build the commit subject, truncating the description at a word boundary."""
    head = f"{jira_id} fix({cwe_id}): " if jira_id else f"fix({cwe_id}): "
    if len(head) + len(description) <= max_len:
        return head + description
    max_desc = max_len - len(head) - 3
    cut = description[:max_desc]
    # Drop the partial last word unless the cut already falls on a space
    if description[max_desc] != " " and " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return head + cut.rstrip(" ,;:-([") + "..."


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    cwe_id = input_data.get("cwe_id", "")
    files = input_data.get("files", [])
    description = input_data.get("description", "")
    repo_dir = input_data.get("repo_dir", "")
    jira_id = input_data.get("jira_id")
    verification_result = input_data.get("verification_result")
    allow_unvalidated = input_data.get("allow_unvalidated", False)

    progress(f"Creating atomic commit — {cwe_id} ({len(files)} file(s))...")

    # --- Validate inputs ---
    # CWE ID
    if not re.match(r"(?i)cwe-\d+", cwe_id):
        error_exit(f"Invalid cwe_id format: {cwe_id}. Expected CWE-<number>", "validation")
    cwe_id = cwe_id.upper()

    # Files
    if not files or not isinstance(files, list):
        error_exit("files must be a non-empty list of file paths", "validation")

    # Description
    if not description:
        error_exit("description is required", "validation")
    if len(description) > 200:
        description = description[:197] + "..."

    # Repo dir
    if not repo_dir:
        error_exit("repo_dir is required", "validation")
    repo_path = Path(repo_dir)
    if not (repo_path / ".git").is_dir():
        error_exit(f"Not a git repository: {repo_dir}", "validation")

    # --- Check verification status ---
    warnings = []
    if verification_result:
        verdict = verification_result.get("verdict", "").upper()
        if verdict in ("FAIL", "ERROR") and not allow_unvalidated:
            error_exit(
                f"Cannot commit a fix that failed validation. Verdict: {verdict}.",
                "verification_check",
            )
        if verdict == "PARTIAL":
            warnings.append("Rescan validation was PARTIAL. Manual review recommended.")
    else:
        if not allow_unvalidated:
            error_exit(
                "Verification result is required before committing. Set allow_unvalidated=true to override.",
                "verification_check",
            )
        warnings.append("Fix committed without rescan validation.")

    # --- Verify files exist and are within repo ---
    valid_files = []
    rejected_secrets = []
    for f in files:
        fp = Path(f)
        if not fp.exists():
            warnings.append(f"File not found, skipping: {f}")
            continue
        # Check within repo boundary
        try:
            fp.resolve().relative_to(repo_path.resolve())
        except ValueError:
            warnings.append(f"File outside repository, skipping: {f}")
            continue
        # Check secret patterns
        if is_secret_file(f):
            rejected_secrets.append(f)
            warnings.append(f"Secret file rejected: {f}")
            continue
        valid_files.append(str(fp))

    if not valid_files:
        error_exit("No valid files available to commit.", "staging")

    # --- Unstage any unrelated files (using list-form commands) ---
    result = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo_path)
    if result["exit_code"] == 0 and result["stdout"].strip():
        staged = set(result["stdout"].strip().splitlines())
        # Compute relative paths of our files
        our_files_rel = set()
        for f in valid_files:
            try:
                rel = str(Path(f).resolve().relative_to(repo_path.resolve()))
                our_files_rel.add(rel)
            except ValueError:
                pass
        unrelated = staged - our_files_rel
        for uf in unrelated:
            run_cmd(["git", "reset", "HEAD", "--", uf], cwd=repo_path)

    # --- Stage files (using list-form command) ---
    stage_cmd = ["git", "add", "--"] + valid_files
    result = run_cmd(stage_cmd, cwd=repo_path)
    if result["exit_code"] != 0:
        error_exit(f"git add failed: {result['stderr']}", "staging")

    # --- Construct commit message ---
    subject = build_subject(cwe_id, description, jira_id)

    body_lines = [f"CWE: {cwe_id}", ""]
    if warnings:
        for w in warnings:
            body_lines.append(f"Note: {w}")
        body_lines.append("")
    body_lines.append("Files modified:")
    for f in valid_files:
        try:
            rel = str(Path(f).resolve().relative_to(repo_path.resolve()))
        except ValueError:
            rel = f
        body_lines.append(f"  - {rel}")
    body_lines.append("")
    body_lines.append(f"Remediation-CWE: {cwe_id}")
    body_lines.append("")
    body_lines.append("Co-Authored-By: Claude")

    body = "\n".join(body_lines)
    full_message = f"{subject}\n\n{body}"

    # --- Create commit using temp file (avoids shell quoting issues) ---
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(full_message)
        tmp_path = tmp.name

    try:
        result = run_cmd(["git", "commit", "-F", tmp_path], cwd=repo_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if result["exit_code"] != 0:
        error_exit(f"git commit failed: {result['stderr']}", "commit")

    # --- Verify commit ---
    result = run_cmd(["git", "log", "-1", "--format=%H %s"], cwd=repo_path)
    if result["exit_code"] != 0:
        error_exit("Failed to verify commit", "commit_verify")

    parts = result["stdout"].strip().split(" ", 1)
    commit_sha = parts[0] if parts else ""

    # Verify staging area is clean
    result = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=repo_path)
    if result["stdout"].strip():
        warnings.append("Staging area not clean after commit — unexpected files remain staged.")

    # Get files in commit
    result = run_cmd(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        cwd=repo_path,
    )
    files_committed = result["stdout"].strip().splitlines() if result["exit_code"] == 0 else []

    verdict = "PASS"
    if verification_result:
        verdict = verification_result.get("verdict", "UNKNOWN").upper()

    log(f"Committed {cwe_id}: {commit_sha[:8]}")
    progress_done(f"Committed {cwe_id} ({commit_sha[:8]})")

    write_json_output({
        "status": "success",
        "commit_sha": commit_sha,
        "commit_message_subject": subject,
        "cwe_id": cwe_id,
        "files_committed": files_committed,
        "verification_verdict": verdict,
        "warnings": warnings,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
