#!/usr/bin/env python3
"""Fetch Harness CD execution data for cd-diagnose.

Preflight: tries Harness CLI first. Falls back to direct API (urllib + proxy)
if the CLI is unavailable or not authenticated. Fails fast with clear setup
instructions if neither works — the agent is never invoked in that case.

Writes to the current working directory:
  harness_execution.json       — execution summary
  harness_steps.json           — flat step list with status, fqn, log_key
  harness_log_<safe>_<id>.json — one per failed step log key (best-effort)

Usage:
  python harness_diagnose.py --exec-id <planExecutionId> --profile <prod|nonprod>

Exit codes:
  0  success
  1  cannot reach Harness (both CLI and API failed) — see stderr for setup steps
  2  execution not found or API error
  3  unexpected error
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HARNESS = "harness"

INSTANCES = {
    "prod":   {"url": "https://barclays.harness.io",        "account": "NTEwZmY4Y2MtOWZmNS00ZD"},
    "nonprod": {"url": "https://barclays-nonprod.harness.io", "account": "ZjRkN2I1MTgtYjQxOS00Yj"},
}

TOKEN_VAR = {
    "prod":   "HARNESS_API_TOKEN_PROD",
    "nonprod": "HARNESS_API_TOKEN_NONPROD",
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_shell_var(name: str) -> str:
    r = subprocess.run(["bash", "-lc", f"echo ${name}"], capture_output=True, text=True)
    return r.stdout.strip()


def _get_api_token(profile: str) -> str:
    """Resolve API token: profile-specific first, then universal fallback."""
    return _get_shell_var(TOKEN_VAR[profile]) or _get_shell_var("HARNESS_API_TOKEN")


def _safe_name(s: str, max_len: int = 60) -> str:
    return re.sub(r"[^\w\-]", "_", s)[:max_len]


# ---------------------------------------------------------------------------
# CLI transport
# ---------------------------------------------------------------------------

def _cli_available(profile: str) -> bool:
    """Return True if CLI is installed and authenticated for this profile."""
    r = subprocess.run(
        ["bash", "-lc", f"harness auth status --profile {profile}"],
        capture_output=True, text=True
    )
    return r.returncode == 0 and "cannot reach" not in r.stdout.lower()


def _cli_run(args: list, label: str) -> dict:
    cmd = " ".join([HARNESS] + args + ["--json", "--raw"])
    r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"CLI error ({label}): {r.stderr.strip()}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"CLI JSON parse error ({label}): {e}")


def _cli_run_list(args: list, label: str) -> list:
    cmd = " ".join([HARNESS] + args + ["--json", "--all"])
    r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"CLI error ({label}): {r.stderr.strip()}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"CLI JSON parse error ({label}): {e}")


def fetch_via_cli(exec_id: str, profile: str) -> tuple[dict, list]:
    """Return (execution_dict, steps_list) via CLI."""
    pf = ["--profile", profile]
    execution = _cli_run(["get", "execution", exec_id] + pf, "get execution")
    steps = _cli_run_list(["list", "execution_step", exec_id] + pf, "list execution_step")
    return execution, steps


# ---------------------------------------------------------------------------
# API transport
# ---------------------------------------------------------------------------

def _api_opener() -> urllib.request.OpenerDirector:
    proxy = _get_shell_var("http_proxy")
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({"https": proxy, "http": proxy})
    )


def _api_get(opener, base_url: str, token: str, path: str, params: dict) -> dict:
    url = base_url + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-api-key": token})
    try:
        with opener.open(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"API HTTP {e.code} on {path}: {body[:200]}")


def _api_steps_from_graph(node_map: dict) -> list:
    """Flatten executionGraph.nodeMap into the same shape as CLI list execution_step."""
    steps = []
    for node in node_map.values():
        start_ts = node.get("startTs", 0)
        end_ts = node.get("endTs", 0)
        duration_ms = (end_ts - start_ts) if (start_ts and end_ts) else 0
        duration_s = duration_ms // 1000
        duration_str = f"{duration_s}s" if duration_s < 60 else f"{duration_s // 60}m{duration_s % 60}s"

        steps.append({
            "name":        node.get("name", ""),
            "status":      node.get("status", ""),
            "fqn":         node.get("baseFqn", ""),          # normalised to fqn
            "log_key":     node.get("logBaseKey", ""),        # normalised to log_key
            "duration":    duration_str,
            "startTs":     start_ts,
            "endTs":       end_ts,
            "failureInfo": node.get("failureInfo", {}),
            "uuid":        node.get("uuid", ""),
            "identifier":  node.get("identifier", ""),
            "stepType":    node.get("stepType", ""),
        })
    return steps


def fetch_via_api(exec_id: str, profile: str) -> tuple[dict, list]:
    """Return (execution_dict, steps_list) via direct API. Raises RuntimeError on failure."""
    cfg = INSTANCES[profile]
    token = _get_api_token(profile)
    if not token:
        raise RuntimeError("no api token")

    opener = _api_opener()
    params = {
        "accountIdentifier": cfg["account"],
        "orgIdentifier":     "MCA",
        "projectIdentifier": "MCA_Prod",
    }

    data = _api_get(opener, cfg["url"], token,
                    f"/pipeline/api/pipelines/execution/{exec_id}",
                    {**params, "renderFullBottomGraph": "true"})

    inner = data.get("data", {})
    execution = inner.get("pipelineExecutionSummary", inner)
    node_map  = inner.get("executionGraph", {}).get("nodeMap", {})
    steps     = _api_steps_from_graph(node_map)

    return execution, steps


# ---------------------------------------------------------------------------
# Preflight + fetch dispatcher
# ---------------------------------------------------------------------------

def _setup_instructions(profile: str) -> str:
    cfg = INSTANCES[profile]
    token_var = TOKEN_VAR[profile]
    return (
        "\n"
        "ERROR: Cannot reach Harness. Both CLI and API failed.\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "OPTION 1 — API token (easiest, recommended for most users)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"  1. Open {cfg['url']} in your browser and log in\n"
        "  2. Click your profile icon (top right) → Account Settings\n"
        "  3. Go to API Keys → + Add API Key → give it a name → + Add Token\n"
        "  4. Copy the token and run ONE of these in your terminal:\n"
        "\n"
        f"     export {token_var}=<paste-token-here>    # profile-specific\n"
        "     export HARNESS_API_TOKEN=<paste-token-here>   # universal (works for both prod and nonprod)\n"
        "\n"
        "  5. Re-run this command.\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "OPTION 2 — Harness CLI (if you already have it installed)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "  The CLI requires proxy config on Barclays laptops (Zscaler intercept).\n"
        "  Run these BEFORE the harness auth login command:\n"
        "\n"
        "     export HTTPS_PROXY=http://gateway.zscaler.net:80\n"
        f"     harness auth login --api-url {cfg['url']} --api-token <token> --profile {profile}\n"
        "\n"
        "  Verify it worked:\n"
        f"     harness auth status --profile {profile}\n"
    )


def fetch_execution_data(exec_id: str, profile: str) -> tuple[dict, list, str]:
    """
    Try CLI first; fall back to API.
    Returns (execution, steps, transport_used).
    Prints clear setup instructions and exits 1 if both fail.
    """
    cli_ok = _cli_available(profile)

    if cli_ok:
        print("Transport: Harness CLI", file=sys.stderr)
        try:
            execution, steps = fetch_via_cli(exec_id, profile)
            return execution, steps, "cli"
        except RuntimeError as e:
            print(f"CLI fetch failed: {e}", file=sys.stderr)
            print("Falling back to API...", file=sys.stderr)

    # API fallback
    print("Transport: Harness API (direct)", file=sys.stderr)
    try:
        execution, steps = fetch_via_api(exec_id, profile)
        return execution, steps, "api"
    except RuntimeError as e:
        api_error = str(e)

    # Both failed — print clear setup instructions and exit
    print(_setup_instructions(profile), file=sys.stderr)
    if "no api token" not in api_error:
        print(f"API error detail: {api_error}\n", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Log blob fetch (API only — CLI cannot complete through Zscaler proxy)
# ---------------------------------------------------------------------------

def _fetch_log_blob(opener, base_url: str, token: str, account: str,
                    log_key: str, out_path: Path) -> bool:
    url = (
        f"{base_url}/gateway/log-service/blob"
        f"?accountID={urllib.parse.quote(account)}"
        f"&key={urllib.parse.quote(log_key)}"
    )
    req = urllib.request.Request(
        url, headers={"x-api-key": token, "Content-Type": "application/json"}
    )
    try:
        with opener.open(req, timeout=30) as resp:
            out_path.write_bytes(resp.read())
        return True
    except urllib.error.HTTPError as e:
        print(f"  log fetch failed ({e.code}): {log_key}", file=sys.stderr)
        return False
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"  log fetch error ({type(e).__name__}): {log_key}: {e}", file=sys.stderr)
        return False


def fetch_log_blobs(steps: list, profile: str) -> dict:
    """Download log blobs for failed steps. Returns {log_key: file_path}."""
    failed = [
        s for s in steps
        if s.get("status") in ("Failed", "IgnoreFailed", "FAILED", "IGNORE_FAILED")
        and s.get("log_key")
    ]
    if not failed:
        print("No failed steps — skipping log download.", file=sys.stderr)
        return {}

    cfg = INSTANCES[profile]
    token = _get_api_token(profile)
    if not token:
        token_var = TOKEN_VAR[profile]
        print(
            f"Warning: no API token found ({token_var} or HARNESS_API_TOKEN not set) — "
            "log blob downloads skipped.\n"
            "Step logs give richer diagnosis. To enable them:\n"
            f"  export {token_var}=<your-harness-api-token>\n"
            "  (or: export HARNESS_API_TOKEN=<token>  — universal, works for prod and nonprod)",
            file=sys.stderr
        )
        return {}

    opener = _api_opener()
    # account from log_key prefix (format: <accountId>/pipeline/...)
    first_key = failed[0]["log_key"]
    if "/" in first_key:
        account = first_key.split("/")[0]
        if account not in (INSTANCES["prod"]["account"], INSTANCES["nonprod"]["account"]):
            print(f"  Warning: log_key account prefix '{account}' does not match known accounts; "
                  f"falling back to configured account for {profile}", file=sys.stderr)
            account = cfg["account"]
    else:
        print(f"  Warning: log_key has no account prefix; using configured account for {profile}",
              file=sys.stderr)
        account = cfg["account"]

    log_files = {}
    print(f"Downloading logs for {len(failed)} failed step(s)...", file=sys.stderr)
    for step in failed:
        log_key = step["log_key"]
        safe = _safe_name(step.get("name", log_key))
        uid = re.sub(r"[^\w]", "", log_key)[-8:]
        out_path = Path(f"harness_log_{safe}_{uid}.json")
        ok = _fetch_log_blob(opener, cfg["url"], token, account, log_key, out_path)
        if ok:
            print(f"  log saved: {out_path}", file=sys.stderr)
            log_files[log_key] = str(out_path)

    return log_files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Harness CD execution data")
    parser.add_argument("--exec-id",  required=True, dest="exec_id")
    parser.add_argument("--profile",  required=True, choices=["prod", "nonprod"])
    args = parser.parse_args()

    # --- preflight + fetch ---
    print("Fetching execution data...", file=sys.stderr)
    execution, steps, transport = fetch_execution_data(args.exec_id, args.profile)

    # --- write files ---
    Path("harness_execution.json").write_text(json.dumps(execution, indent=2))
    print(f"  harness_execution.json written (via {transport})", file=sys.stderr)

    Path("harness_steps.json").write_text(json.dumps(steps, indent=2))
    print(f"  harness_steps.json written ({len(steps)} steps, via {transport})", file=sys.stderr)

    # --- log blobs ---
    log_files = fetch_log_blobs(steps, args.profile)

    # --- summary to stdout for agent ---
    failed_steps = {
        s["log_key"]: s.get("name", s["log_key"])
        for s in steps
        if s.get("status") in ("Failed", "IgnoreFailed", "FAILED", "IGNORE_FAILED")
        and s.get("log_key")
    }
    print(json.dumps({
        "failed_steps":   failed_steps,
        "execution_file": "harness_execution.json",
        "steps_file":     "harness_steps.json",
        "log_files":      list(log_files.values()),
        "transport":      transport,
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
