#!/usr/bin/env python3
"""Pre-flight check — verify all required tools are available before pipeline starts.

Input (JSON stdin):
    {
        "require_semgrep": true,
        "require_glab": true,
        "require_git": true,
        "require_wizcli": false,
        "require_barclays_setup": true,     # 4 barclays_* keys in OTEL_RESOURCE_ATTRIBUTES
        "require_telemetry_deps": true      # grpcio + opentelemetry (gRPC/OTLP) — CHECK ONLY
    }

Output (JSON stdout):
    {
        "status": "success" | "missing_tools",
        "platform": "darwin" | "win32",
        "tools": {...},
        "missing": [...],
        "install_instructions": {...}
    }

This script NEVER installs anything (tools OR Python deps). It only CHECKS that
prerequisites are present and reports what is missing with Barclays-specific
installation instructions; a missing mandatory prerequisite blocks the pipeline.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import (
    read_json_input, write_json_output, run_cmd, progress, progress_done,
    check_barclays_setup, BARCLAYS_SETUP_INSTRUCTION,
)


def get_platform() -> str:
    """Return normalized platform: 'darwin' or 'win32' or 'linux'."""
    return sys.platform


OBSERVE_DEPS = (
    ("grpc", "grpcio"),
    ("opentelemetry.sdk", "opentelemetry-sdk"),
    ("opentelemetry.exporter.otlp.proto.grpc", "opentelemetry-exporter-otlp-proto-grpc"),
)


def check_observe_deps() -> dict:
    """CHECK-ONLY: verify the OTel/gRPC telemetry deps are importable.

    Does NOT install anything. Injects the ~/.claude/observe_venv site-packages onto
    sys.path (if the venv exists) and then import-tests each required package. Returns
    the standard tool-check dict with `available` and the list of `missing` packages.
    Never raises.
    """
    import importlib.util

    # Make the dedicated observe_venv visible (same resolution the exporter uses),
    # but do NOT create it or install into it — this is a presence check only.
    try:
        # The library raises at import without an endpoint — apply detox's default
        # first, or the venv is never injected and deps are falsely reported missing.
        from scripts.telemetry.observe_batch import apply_endpoint_default
        apply_endpoint_default()
        from scripts.telemetry.plugin_observability import _inject_venv_path
        _inject_venv_path()
    except Exception:
        pass

    missing_pkgs = []
    for mod, pkg in OBSERVE_DEPS:
        try:
            if importlib.util.find_spec(mod) is None:
                missing_pkgs.append(pkg)
        except (ModuleNotFoundError, ValueError):
            missing_pkgs.append(pkg)

    return {
        "name": "observe_deps",
        "available": not missing_pkgs,
        "missing_packages": missing_pkgs,
        "venv": str(Path.home() / ".claude" / "observe_venv"),
    }


def check_python() -> dict:
    """Verify Python 3.10+ is available."""
    version = sys.version_info
    available = version >= (3, 10)
    return {
        "name": "python",
        "available": available,
        "version": f"{version.major}.{version.minor}.{version.micro}",
        "min_version": "3.10",
        "path": sys.executable,
    }


def check_git() -> dict:
    """Verify git is available."""
    result = run_cmd(["git", "--version"], timeout=10)
    available = result["exit_code"] == 0
    version = result["stdout"].strip().replace("git version ", "") if available else None
    path_cmd = ["which", "git"] if sys.platform != "win32" else ["where", "git"]
    path = run_cmd(path_cmd, timeout=5)["stdout"].strip() if available else None
    return {
        "name": "git",
        "available": available,
        "version": version,
        "path": path,
    }


# Skip semgrep's online "newer release?" lookup: behind the corporate proxy it hangs
# ~30s and pushes `semgrep --version` past the timeout, so an installed semgrep
# was reported missing. Does not affect scanning.
SEMGREP_NO_VERSION_CHECK = {"SEMGREP_ENABLE_VERSION_CHECK": "0"}


def check_semgrep() -> dict:
    """Verify semgrep is available."""
    # Try standard semgrep first (with longer timeout for first run initialization)
    result = run_cmd(["semgrep", "--version"], timeout=30, env=SEMGREP_NO_VERSION_CHECK)
    if result["exit_code"] == 0:
        version = result["stdout"].strip()
        return {
            "name": "semgrep",
            "available": True,
            "version": version,
        }

    # Try common installation locations (Windows paths)
    common_paths = [
        r"C:\devhome\tools\python3.12\current\Scripts\semgrep",
        r"C:\devhome\tools\python3.11\current\Scripts\semgrep",
        str(Path.home() / ".local" / "bin" / "semgrep"),
    ]

    permission_denied_paths = []
    for semgrep_path_str in common_paths:
        semgrep_path = Path(semgrep_path_str)

        # Check file permissions if file exists
        if semgrep_path.exists() and not os.access(semgrep_path, os.X_OK):
            permission_denied_paths.append(semgrep_path_str)
            continue

        # Try to run it, even if Path().exists() returns False (handles zipapps)
        # Use longer timeout for first run initialization
        result = run_cmd([semgrep_path_str, "--version"], timeout=30, env=SEMGREP_NO_VERSION_CHECK)
        if result["exit_code"] == 0:
            version = result["stdout"].strip()
            return {
                "name": "semgrep",
                "available": True,
                "version": version,
            }

    error_detail = ""
    if permission_denied_paths:
        error_detail = f" (found at {', '.join(permission_denied_paths)} but not executable)"

    return {
        "name": "semgrep",
        "available": False,
        "version": None,
        "error": f"semgrep not found in PATH or common locations{error_detail}",
    }


def check_wizcli() -> dict:
    """Verify WIZ CLI is installed and authenticated."""
    result = run_cmd(["wizcli", "version"], timeout=10)
    available = result["exit_code"] == 0
    version = ""
    if available:
        # Parse "Wiz CLI v0.105.0-c9f6a22, built 2025-11-19T12:35:08Z"
        for token in result["stdout"].strip().split():
            if token.startswith("v") and len(token) > 1:
                version = token.rstrip(",")
                break

    authenticated = False
    client_email = ""
    if available:
        auth_result = run_cmd(["wizcli", "auth", "--print-token"], timeout=10)
        if auth_result["exit_code"] == 0:
            # CRITICAL: wizcli returns exit 0 even when token is expired,
            # putting "No stored authentication data found" in STDERR.
            combined = auth_result["stdout"] + auth_result["stderr"]
            if "No stored authentication data" in combined or "not authenticated" in combined.lower():
                authenticated = False
            else:
                authenticated = True
                for line in auth_result["stdout"].splitlines():
                    stripped = line.strip()
                    if stripped.startswith("Client email:"):
                        client_email = stripped[len("Client email:"):].strip()

    return {
        "name": "wizcli",
        "available": available,
        "version": version or None,
        "authenticated": authenticated,
        "client_email": client_email or None,
    }


def check_glab() -> dict:
    """Verify GitLab CLI (glab) is available and authenticated."""
    # Try standard glab first
    result = run_cmd(["glab", "--version"], timeout=10)
    glab_path = "glab"

    if result["exit_code"] != 0:
        # Try common installation locations (Windows paths)
        # Try to run them, even if exists() returns False (handles exe files)
        common_paths = [
            r"C:\devhome\tools\gitlabcli\1.109.0\bin\glab.exe",
            r"C:\devhome\tools\gitlabcli\1.109.0\bin\glab",
            r"C:\devhome\tools\gitlabcli\current\bin\glab.exe",
            r"C:\devhome\tools\gitlabcli\current\bin\glab",
            str(Path.home() / ".local" / "bin" / "glab"),
        ]

        for path_str in common_paths:
            test_result = run_cmd([path_str, "--version"], timeout=10)
            if test_result["exit_code"] == 0:
                glab_path = path_str
                result = test_result
                break

    available = result["exit_code"] == 0
    version = result["stdout"].strip() if available else None

    authenticated = False
    host = None
    if available:
        # Check if configured with host
        auth_result = run_cmd([glab_path, "auth", "status"], timeout=10)
        if auth_result["exit_code"] == 0:
            authenticated = True
            # Try to extract host
            host_result = run_cmd([glab_path, "config", "get", "host"], timeout=5)
            host = host_result["stdout"].strip() if host_result["exit_code"] == 0 else None

    return {
        "name": "glab",
        "available": available,
        "version": version,
        "authenticated": authenticated,
        "host": host,
    }


# Installation instructions by platform
INSTALL_INSTRUCTIONS = {
    "python": {
        "darwin": "Install Python 3.12 via Homebrew: brew install python@3.12",
        "win32": "Install Python 3.12 via Dev CLI or the Barclays-approved Python distribution.",
    },
    "git": {
        "darwin": "Install git via Xcode CLI tools: xcode-select --install",
        "win32": "Git is typically bundled with Dev CLI. Run 'dev activate' to ensure it is available.",
    },
    "semgrep": {
        "darwin": "Install Semgrep via Homebrew: brew install semgrep",
        "win32": "Install Semgrep via pip: pip install semgrep",
    },
    "wizcli": {
        "darwin": "Install WIZ CLI via Homebrew: brew install --cask wizcli\n"
                  "Then authenticate:\n"
                  "  wizcli auth --use-device-code\n"
                  "For CI/CD (service account):\n"
                  "  export WIZ_CLIENT_ID=<client-id>\n"
                  "  export WIZ_CLIENT_SECRET=<secret>\n"
                  "  wizcli auth --id $WIZ_CLIENT_ID --secret $WIZ_CLIENT_SECRET",
        "win32": "Install WIZ CLI via Dev CLI: dev tool install wizcli\n"
                 "Then authenticate:\n"
                 "  wizcli auth --use-device-code\n"
                 "For CI/CD (service account):\n"
                 "  set WIZ_CLIENT_ID=<client-id>\n"
                 "  set WIZ_CLIENT_SECRET=<secret>\n"
                 "  wizcli auth --id %WIZ_CLIENT_ID% --secret %WIZ_CLIENT_SECRET%",
    },
    "glab": {
        "darwin": "Install GitLab CLI via Homebrew: brew install glab\n"
                  "Then configure:\n"
                  "  glab config set --global check_update false\n"
                  "  glab config set --global host https://app.gitlab.barcapint.com\n"
                  "  glab config set --global token YOUR_PERSONAL_ACCESS_TOKEN",
        "win32": "Install GitLab CLI via Dev CLI: Install gitlabcli using Dev CLI.\n"
                 "Then configure:\n"
                 "  glab config set --global token YOUR_PERSONAL_ACCESS_TOKEN\n"
                 "Or set environment variables:\n"
                 "  set GITLAB_HOST=https://app.gitlab.barcapint.com\n"
                 "  set GITLAB_TOKEN=YOUR_PERSONAL_ACCESS_TOKEN",
    },
}


def get_install_instruction(tool: str, plat: str) -> str:
    """Get platform-specific installation instruction for a tool."""
    instructions = INSTALL_INSTRUCTIONS.get(tool, {})
    # Normalize platform
    if plat == "linux":
        plat = "darwin"  # Use macOS instructions as fallback for Linux
    return instructions.get(plat, f"Contact your team for {tool} installation on {plat}.")


def main() -> None:
    import time
    start_time = time.time()
    input_data = read_json_input()

    require_semgrep = input_data.get("require_semgrep", True)
    require_glab = input_data.get("require_glab", True)
    require_git = input_data.get("require_git", True)
    require_wizcli = input_data.get("require_wizcli", False)
    require_barclays_setup = input_data.get("require_barclays_setup", True)

    plat = get_platform()
    progress("Preflight check — verifying required tools...")

    # Always check Python (we're running in it, but verify version)
    tools = {}
    missing = []
    install_instructions = {}

    # Python
    python_check = check_python()
    tools["python"] = python_check
    if python_check["available"]:
        progress_done(f"python {python_check['version']}")
    else:
        missing.append("python")
        install_instructions["python"] = get_install_instruction("python", plat)

    # Git
    if require_git:
        git_check = check_git()
        tools["git"] = git_check
        if git_check["available"]:
            progress_done(f"git {git_check['version']}")
        else:
            missing.append("git")
            install_instructions["git"] = get_install_instruction("git", plat)

    # Semgrep
    if require_semgrep:
        semgrep_check = check_semgrep()
        tools["semgrep"] = semgrep_check
        if semgrep_check["available"]:
            progress_done(f"semgrep {semgrep_check['version']}")
        else:
            missing.append("semgrep")
            install_instructions["semgrep"] = get_install_instruction("semgrep", plat)

    # WIZ CLI (bank's strategic security scanner)
    if require_wizcli:
        wizcli_check = check_wizcli()
        tools["wizcli"] = wizcli_check
        if not wizcli_check["available"]:
            missing.append("wizcli")
            install_instructions["wizcli"] = get_install_instruction("wizcli", plat)
        elif not wizcli_check["authenticated"]:
            missing.append("wizcli (not authenticated)")
            install_instructions["wizcli_auth"] = (
                "WIZ CLI is installed but not authenticated.\n"
                "Interactive (opens browser):\n"
                "  wizcli auth --use-device-code\n"
                "CI/CD (service account):\n"
                "  export WIZ_CLIENT_ID=<client-id>\n"
                "  export WIZ_CLIENT_SECRET=<secret>\n"
                "  wizcli auth --id $WIZ_CLIENT_ID --secret $WIZ_CLIENT_SECRET"
            )
        else:
            progress_done(f"wizcli {wizcli_check['version']} (authenticated as {wizcli_check['client_email']})")

    # GitLab CLI
    if require_glab:
        glab_check = check_glab()
        tools["glab"] = glab_check
        if not glab_check["available"]:
            missing.append("glab")
            install_instructions["glab"] = get_install_instruction("glab", plat)
        elif not glab_check["authenticated"]:
            missing.append("glab (not authenticated)")
            install_instructions["glab_auth"] = (
                "GitLab CLI is installed but not authenticated.\n"
                "Run: glab config set --global host https://app.gitlab.barcapint.com\n"
                "Run: glab config set --global token YOUR_PERSONAL_ACCESS_TOKEN\n"
                "Create token at: https://app.gitlab.barcapint.com/-/user_settings/personal_access_tokens"
            )

    # Mandatory Barclays user setup (hard gate — blocks the pipeline if incomplete)
    if require_barclays_setup:
        setup_check = check_barclays_setup()
        tools["barclays_setup"] = setup_check
        if not setup_check["available"]:
            missing.append("barclays_setup")
            install_instructions["barclays_setup"] = BARCLAYS_SETUP_INSTRUCTION

    # Telemetry dependencies (gRPC/OTLP) — CHECK-ONLY HARD GATE. detox exports every
    # run to the Barclays Observe platform, so these are a prerequisite. We do NOT
    # auto-install (predictable enterprise behaviour): if any are missing, preflight
    # BLOCKS the pipeline before any work starts, with manual install instructions.
    # Set require_telemetry_deps:false only for offline/air-gapped use or test harnesses.
    require_telemetry_deps = input_data.get("require_telemetry_deps", True)
    if require_telemetry_deps:
        deps_check = check_observe_deps()
        tools["observe_deps"] = deps_check
        if deps_check["available"]:
            progress_done("telemetry deps (grpcio, opentelemetry) found")
        else:
            missing.append("observe_deps")
            miss = ", ".join(deps_check["missing_packages"])
            progress_done(f"telemetry deps MISSING: {miss}")
            pip_hint = "Scripts\\pip.exe" if plat == "win32" else "bin/pip"
            install_instructions["observe_deps"] = (
                f"Required telemetry dependencies are not installed: {miss}.\n"
                "detox exports every run to the Barclays Observe platform, so these are "
                "mandatory. They are NOT installed automatically — install them once into "
                "the dedicated venv (pip uses your pip config / Barclays Nexus index):\n"
                "  python3 -m venv ~/.claude/observe_venv   (Windows: python -m venv %USERPROFILE%\\.claude\\observe_venv)\n"
                f"  ~/.claude/observe_venv/{pip_hint} install grpcio opentelemetry-sdk "
                "opentelemetry-exporter-otlp-proto-grpc\n"
                "Then re-run detox."
            )

    status = "success" if not missing else "missing_tools"

    write_json_output({
        "status": status,
        "platform": plat,
        "tools": tools,
        "missing": missing,
        "install_instructions": install_instructions,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
