#!/usr/bin/env python3
"""Run a WIZ CLI directory scan and return structured findings.

Input (JSON stdin):
    {
        "repo_dir": "/path/to/repo",
        "output_path": "/tmp/wiz-scan.json",
        "timeout_seconds": 600,
        "no_publish": true
    }

Output (JSON stdout) — success:
    {
        "status": "success",
        "scan_result": {
            "findings": [...],
            "libraries": [...],
            "metadata": {...}
        },
        "metadata": {
            "wizcli_version": "v0.105.0-c9f6a22",
            "authenticated_as": "user@barclays.com",
            "timestamp": "2026-09-23T14:00:00Z",
            "no_publish": true
        }
    }

Output (JSON stdout) — unavailable:
    {
        "status": "unavailable",
        "reason": "wizcli_not_installed" | "wizcli_not_authenticated",
        "metadata": {}
    }
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import (
    read_json_input,
    write_json_output,
    run_cmd,
    log,
    progress,
    progress_done,
    sanitize_pat,
)
from scripts.core.errors import error_exit


def check_wizcli_installed() -> dict:
    """Check if wizcli is installed.

    Returns {"installed": bool, "version": str}.
    """
    result = run_cmd(["wizcli", "version"])
    if result["exit_code"] != 0:
        log(f"wizcli version check failed: {sanitize_pat(result['stderr'])}")
        return {"installed": False, "version": ""}

    stdout = result["stdout"].strip()
    # Parse version from output like: "Wiz CLI v0.105.0-c9f6a22, built 2025-11-19T12:35:08Z"
    version = ""
    for token in stdout.split():
        if token.startswith("v") and len(token) > 1:
            # Strip trailing comma if present
            version = token.rstrip(",")
            break

    return {"installed": True, "version": version}


def check_wizcli_auth() -> dict:
    """Check if wizcli is authenticated.

    Returns {"authenticated": bool, "client_email": str, "expires_at": str}.

    CRITICAL: The access token is NEVER included in the return value.
    Any token strings are redacted via sanitize_pat() before logging.
    """
    result = run_cmd(["wizcli", "auth", "--print-token"])

    if result["exit_code"] != 0:
        log(f"wizcli auth check failed: {sanitize_pat(result['stderr'])}")
        return {"authenticated": False, "client_email": "", "expires_at": ""}

    stdout = result["stdout"]
    stderr = result["stderr"]

    # Check for explicit "not authenticated" messages in BOTH stdout and stderr
    # wizcli returns exit 0 even when no token is stored, and puts the message in stderr
    combined = stdout + stderr
    if "No stored authentication data" in combined or "not authenticated" in combined.lower():
        log("wizcli has no stored authentication — token expired or never authenticated")
        return {"authenticated": False, "client_email": "", "expires_at": "", "expired": True}

    # Redact output before any processing to prevent token leakage in logs
    sanitized_stdout = sanitize_pat(stdout)
    log(f"wizcli auth output (redacted): {sanitized_stdout}")

    client_email = ""
    expires_at = ""

    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Client email:"):
            client_email = stripped[len("Client email:"):].strip()
        elif stripped.startswith("Expires at:"):
            expires_at = stripped[len("Expires at:"):].strip()

    # Check if token is expired
    expired = False
    if expires_at:
        try:
            from datetime import datetime, timezone
            # Parse "2026-09-10 10:59:45.248422 +0000 UTC" or ISO format
            exp_str = expires_at.replace(" UTC", "+00:00").replace(" +0000", "+00:00")
            # Try ISO format first
            try:
                exp_dt = datetime.fromisoformat(exp_str)
            except ValueError:
                # Try space-separated format: "2026-09-10 10:59:45.248422+00:00"
                exp_dt = datetime.strptime(exp_str.split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            expired = exp_dt < datetime.now(timezone.utc)
        except (ValueError, TypeError):
            pass  # Can't parse — assume not expired

    if expired:
        log(f"wizcli token expired at {expires_at}")
        return {
            "authenticated": False,
            "client_email": client_email,
            "expires_at": expires_at,
            "expired": True,
        }

    # NEVER return the access token — only structured metadata
    return {
        "authenticated": True,
        "client_email": client_email,
        "expires_at": expires_at,
    }


def run_wiz_scan(
    repo_dir: str,
    output_path: str,
    timeout: int = 600,
    no_publish: bool = True,
) -> dict:
    """Run wizcli dir scan and return structured result.

    Returns graceful error dicts (not error_exit) so the caller can use a
    fallback chain.

    Returns:
        On success:  {"status": "success", "scan_path": str, "findings_count": int, "metadata": dict}
        On failure:  {"status": "error", "reason": "scan_failed", "detail": str}
        On timeout:  {"status": "error", "reason": "scan_timeout"}
    """
    cmd = [
        "wizcli",
        "dir",
        "scan",
        "--path", repo_dir,
        "--format", "json",
        "--output", f"{output_path},json",
    ]
    if no_publish:
        cmd.append("--no-publish")

    log(f"Running wizcli scan: path={repo_dir} output={output_path} no_publish={no_publish}")
    result = run_cmd(cmd, timeout=timeout)

    if result["exit_code"] != 0:
        stderr = result["stderr"]
        if "timed out" in stderr.lower():
            log("wizcli scan timed out")
            return {"status": "error", "reason": "scan_timeout"}
        log(f"wizcli scan failed: {sanitize_pat(stderr[:500])}")
        return {
            "status": "error",
            "reason": "scan_failed",
            "detail": stderr[:500],
        }

    # Parse findings from the output file
    parsed = parse_wiz_scan_output(output_path)
    findings_count = len(parsed.get("findings", []))

    return {
        "status": "success",
        "scan_path": output_path,
        "findings_count": findings_count,
        "metadata": parsed.get("metadata", {}),
        "findings": parsed.get("findings", []),
        "libraries": parsed.get("libraries", []),
    }


def parse_wiz_scan_output(path: str) -> dict:
    """Read and parse a WIZ CLI JSON scan output file.

    Real WIZ CloudEvent schema:
      .extraDetails.sastDetails.findings[]         — SAST findings
      .extraDetails.vulnerabilityDetails.libraries[] — SCA libraries
      .id, .status, .timestamp                     — scan metadata
      .rawAuditLogRecord.startedAt/createdAt       — timing

    Returns {"findings": [...], "libraries": [...], "metadata": {...}}.
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        log(f"WIZ scan output file not found: {path}")
        return {"findings": [], "libraries": [], "metadata": {}}
    except json.JSONDecodeError as e:
        log(f"WIZ scan output is not valid JSON: {e}")
        return {"findings": [], "libraries": [], "metadata": {}}

    extra = data.get("extraDetails", {})
    sast = extra.get("sastDetails", {})
    findings = sast.get("findings", [])

    vuln = extra.get("vulnerabilityDetails", {})
    libraries = vuln.get("libraries", [])

    raw = data.get("rawAuditLogRecord", {})
    metadata = {
        "scan_id": data.get("id", ""),
        "scan_status": data.get("status", ""),
        "scan_started_at": raw.get("startedAt", data.get("timestamp", "")),
        "scan_completed_at": raw.get("createdAt", ""),
    }

    return {
        "findings": findings,
        "libraries": libraries,
        "metadata": metadata,
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    output_path = input_data.get("output_path", "")
    timeout_seconds = int(input_data.get("timeout_seconds", 600))
    no_publish = bool(input_data.get("no_publish", True))

    # --- Validate required inputs ---
    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")
    if not output_path:
        error_exit("output_path is required", "input_validation")

    progress("Checking wizcli installation...")

    # --- Check wizcli is installed ---
    install_info = check_wizcli_installed()
    if not install_info["installed"]:
        progress_done("wizcli is not installed — returning unavailable")
        write_json_output(
            {
                "status": "unavailable",
                "reason": "wizcli_not_installed",
                "metadata": {},
            },
            start_time=start_time,
        )
        return

    wizcli_version = install_info["version"]
    log(f"wizcli version: {wizcli_version}")

    # --- Check wizcli authentication ---
    progress("Checking wizcli authentication...")
    auth_info = check_wizcli_auth()
    if not auth_info["authenticated"]:
        progress_done("wizcli is not authenticated — returning unavailable")
        write_json_output(
            {
                "status": "unavailable",
                "reason": "wizcli_not_authenticated",
                "metadata": {"wizcli_version": wizcli_version},
            },
            start_time=start_time,
        )
        return

    authenticated_as = auth_info["client_email"]
    log(f"wizcli authenticated as: {authenticated_as}")

    # --- Run scan ---
    progress(f"Running wizcli scan on {repo_dir}...")
    scan_result = run_wiz_scan(
        repo_dir=repo_dir,
        output_path=output_path,
        timeout=timeout_seconds,
        no_publish=no_publish,
    )

    if scan_result["status"] != "success":
        progress_done(f"WIZ scan did not complete: {scan_result.get('reason', 'unknown')}")
        write_json_output(
            {
                "status": "error",
                "reason": scan_result.get("reason", "scan_failed"),
                "detail": scan_result.get("detail", ""),
                "metadata": {
                    "wizcli_version": wizcli_version,
                    "authenticated_as": authenticated_as,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "no_publish": no_publish,
                },
            },
            start_time=start_time,
        )
        return

    progress_done(
        f"WIZ scan complete — {scan_result['findings_count']} code finding(s)"
    )

    write_json_output(
        {
            "status": "success",
            "scan_result": {
                "findings": scan_result.get("findings", []),
                "libraries": scan_result.get("libraries", []),
                "metadata": scan_result.get("metadata", {}),
            },
            "metadata": {
                "wizcli_version": wizcli_version,
                "authenticated_as": authenticated_as,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "no_publish": no_publish,
            },
        },
        start_time=start_time,
    )


if __name__ == "__main__":
    main()
