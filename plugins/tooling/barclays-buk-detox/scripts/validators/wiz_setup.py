#!/usr/bin/env python3
"""WIZ CLI setup — check, install (with consent), and authenticate.

Cross-platform: macOS (brew), Windows (Dev CLI / winget), Linux (Dev CLI / curl).

Input (JSON stdin):
    {
        "auto_install": false,
        "auto_auth": false
    }

Output (JSON stdout):
    {
        "status": "ready" | "installed" | "skipped" | "failed",
        "installed": true,
        "authenticated": true,
        "version": "v0.105.0",
        "client_email": "user@barclays.com",
        "platform": "darwin",
        "install_method": "brew" | "dev_cli" | "curl" | "already_installed",
        "auth_method": "device_code" | "service_account" | "already_authenticated",
        "actions_taken": ["installed wizcli via brew", "authenticated via device code"]
    }
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


# --- Platform detection ---

def get_platform() -> str:
    """Return normalized platform: 'darwin', 'win32', or 'linux'."""
    return sys.platform


def is_ci_environment() -> bool:
    """Check if running in a CI/CD pipeline."""
    ci_vars = ["CI", "GITLAB_CI", "JENKINS_URL", "TEAMCITY_VERSION", "GITHUB_ACTIONS"]
    return any(os.environ.get(var) for var in ci_vars)


# --- Install methods per platform ---

INSTALL_COMMANDS = {
    "darwin": [
        {
            "name": "brew",
            "check": ["brew", "--version"],
            "install": ["brew", "install", "--cask", "wizcli"],
            "description": "Homebrew (brew install --cask wizcli)",
        },
    ],
    "linux": [
        {
            "name": "dev_cli",
            "check": ["dev", "--version"],
            "install": ["dev", "tool", "install", "wizcli"],
            "description": "Dev CLI (dev tool install wizcli)",
        },
        {
            "name": "curl",
            "check": ["curl", "--version"],
            "install": [
                "bash", "-c",
                "curl -fL -o /tmp/wizcli https://downloads.wiz.io/wizcli/latest/wizcli-linux-amd64 "
                "&& chmod +x /tmp/wizcli && sudo mv /tmp/wizcli /usr/local/bin/wizcli",
            ],
            "description": "Direct download via curl",
        },
    ],
    "win32": [
        {
            "name": "dev_cli",
            "check": ["dev", "--version"],
            "install": ["dev", "tool", "install", "wizcli"],
            "description": "Dev CLI (dev tool install wizcli)",
        },
        {
            "name": "winget",
            "check": ["winget", "--version"],
            "install": ["winget", "install", "--id", "Wiz.WizCLI", "--accept-source-agreements"],
            "description": "winget (winget install Wiz.WizCLI)",
        },
    ],
}


# --- Core functions ---

def check_installed() -> dict:
    """Check if wizcli is already installed."""
    result = run_cmd(["wizcli", "version"], timeout=10)
    if result["exit_code"] != 0:
        return {"installed": False, "version": ""}

    version = ""
    for token in result["stdout"].strip().split():
        if token.startswith("v") and len(token) > 1:
            version = token.rstrip(",")
            break

    return {"installed": True, "version": version}


def check_authenticated() -> dict:
    """Check if wizcli is authenticated.

    CRITICAL: wizcli auth --print-token returns exit 0 even when the token
    is expired or missing, putting "No stored authentication data found" in
    STDERR (not stdout). We must check BOTH streams.
    """
    result = run_cmd(["wizcli", "auth", "--print-token"], timeout=10)
    if result["exit_code"] != 0:
        return {"authenticated": False, "client_email": "", "expires_at": ""}

    # Check for explicit "not authenticated" messages in BOTH stdout and stderr
    combined = result["stdout"] + result["stderr"]
    if "No stored authentication data" in combined or "not authenticated" in combined.lower():
        return {"authenticated": False, "client_email": "", "expires_at": "", "expired": True}

    client_email = ""
    expires_at = ""
    for line in result["stdout"].splitlines():
        stripped = line.strip()
        if stripped.startswith("Client email:"):
            client_email = stripped[len("Client email:"):].strip()
        elif stripped.startswith("Expires at:"):
            expires_at = stripped[len("Expires at:"):].strip()

    return {"authenticated": True, "client_email": client_email, "expires_at": expires_at}


def find_install_method(plat: str) -> dict | None:
    """Find the first available install method for the platform."""
    methods = INSTALL_COMMANDS.get(plat, [])
    for method in methods:
        check = run_cmd(method["check"], timeout=10)
        if check["exit_code"] == 0:
            return method
    return None


def install_wizcli(plat: str) -> dict:
    """Attempt to install wizcli using the best available method.

    Returns {"success": bool, "method": str, "output": str}.
    """
    method = find_install_method(plat)
    if not method:
        return {
            "success": False,
            "method": "none",
            "output": f"No install method available for {plat}. "
                      f"Please install manually: https://docs.wiz.io/wiz-docs/docs/wiz-cli-overview",
        }

    progress(f"Installing wizcli via {method['description']}...")
    result = run_cmd(method["install"], timeout=300)

    if result["exit_code"] != 0:
        return {
            "success": False,
            "method": method["name"],
            "output": result["stderr"][:500] or result["stdout"][:500],
        }

    # Verify installation
    verify = check_installed()
    if not verify["installed"]:
        return {
            "success": False,
            "method": method["name"],
            "output": "Install command succeeded but wizcli not found on PATH after install.",
        }

    progress_done(f"wizcli {verify['version']} installed via {method['name']}")
    return {
        "success": True,
        "method": method["name"],
        "version": verify["version"],
        "output": f"Installed wizcli {verify['version']} via {method['description']}",
    }


def authenticate_wizcli_device_code() -> dict:
    """Authenticate via device code flow (interactive — opens browser).

    Returns {"success": bool, "method": str, "client_email": str}.
    """
    progress("Authenticating wizcli via device code (will open browser)...")
    result = run_cmd(["wizcli", "auth", "--use-device-code"], timeout=120)

    if result["exit_code"] != 0:
        return {
            "success": False,
            "method": "device_code",
            "client_email": "",
            "output": result["stderr"][:500],
        }

    # Verify
    auth = check_authenticated()
    if auth["authenticated"]:
        progress_done(f"Authenticated as {auth['client_email']}")
        return {
            "success": True,
            "method": "device_code",
            "client_email": auth["client_email"],
        }

    return {
        "success": False,
        "method": "device_code",
        "client_email": "",
        "output": "Auth command succeeded but wizcli not authenticated after.",
    }


def authenticate_wizcli_service_account() -> dict:
    """Authenticate via service account (CI/CD — env vars).

    Returns {"success": bool, "method": str, "client_email": str}.
    """
    client_id = os.environ.get("WIZ_CLIENT_ID", "")
    client_secret = os.environ.get("WIZ_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return {
            "success": False,
            "method": "service_account",
            "client_email": "",
            "output": "WIZ_CLIENT_ID and WIZ_CLIENT_SECRET environment variables not set.",
        }

    progress("Authenticating wizcli via service account...")
    result = run_cmd(
        ["wizcli", "auth", "--id", client_id, "--secret", client_secret],
        timeout=30,
    )

    if result["exit_code"] != 0:
        return {
            "success": False,
            "method": "service_account",
            "client_email": "",
            "output": result["stderr"][:500],
        }

    auth = check_authenticated()
    if auth["authenticated"]:
        progress_done(f"Authenticated as {auth['client_email']} (service account)")
        return {
            "success": True,
            "method": "service_account",
            "client_email": auth["client_email"],
        }

    return {
        "success": False,
        "method": "service_account",
        "client_email": "",
        "output": "Auth command succeeded but wizcli not authenticated after.",
    }


def get_install_instructions(plat: str) -> str:
    """Get human-readable install instructions for the platform."""
    if plat == "darwin":
        return (
            "  macOS:\n"
            "    brew install --cask wizcli\n"
            "    wizcli auth --use-device-code"
        )
    elif plat == "win32":
        return (
            "  Windows:\n"
            "    Option 1: dev tool install wizcli    (via Dev CLI)\n"
            "    Option 2: winget install Wiz.WizCLI\n"
            "    Then: wizcli auth --use-device-code"
        )
    else:
        return (
            "  Linux:\n"
            "    Option 1: dev tool install wizcli    (via Dev CLI)\n"
            "    Option 2: curl -fL -o /tmp/wizcli https://downloads.wiz.io/wizcli/latest/wizcli-linux-amd64 "
            "&& chmod +x /tmp/wizcli && sudo mv /tmp/wizcli /usr/local/bin/wizcli\n"
            "    Then: wizcli auth --use-device-code"
        )


def get_auth_instructions() -> str:
    """Get human-readable auth instructions."""
    return (
        "  Interactive (opens browser):\n"
        "    wizcli auth --use-device-code\n"
        "\n"
        "  CI/CD (service account):\n"
        "    export WIZ_CLIENT_ID=<your-client-id>\n"
        "    export WIZ_CLIENT_SECRET=<your-secret>\n"
        "    wizcli auth --id $WIZ_CLIENT_ID --secret $WIZ_CLIENT_SECRET"
    )


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    auto_install = input_data.get("auto_install", False)
    auto_auth = input_data.get("auto_auth", False)

    plat = get_platform()
    ci = is_ci_environment()
    actions_taken: list[str] = []

    progress("Checking WIZ CLI setup...")

    # --- Step 1: Check if installed ---
    install_info = check_installed()

    if install_info["installed"]:
        progress_done(f"wizcli {install_info['version']} found")
        install_method = "already_installed"
    elif auto_install:
        # User consented to install
        install_result = install_wizcli(plat)
        if install_result["success"]:
            install_info = {"installed": True, "version": install_result.get("version", "")}
            install_method = install_result["method"]
            actions_taken.append(f"Installed wizcli via {install_method}")
        else:
            # Install failed
            write_json_output({
                "status": "failed",
                "installed": False,
                "authenticated": False,
                "version": "",
                "client_email": "",
                "platform": plat,
                "install_method": install_result["method"],
                "auth_method": "none",
                "actions_taken": actions_taken,
                "error": install_result["output"],
                "install_instructions": get_install_instructions(plat),
            }, start_time=start_time)
            return
    else:
        # Not installed, no consent to install
        write_json_output({
            "status": "skipped",
            "installed": False,
            "authenticated": False,
            "version": "",
            "client_email": "",
            "platform": plat,
            "install_method": "none",
            "auth_method": "none",
            "actions_taken": [],
            "install_instructions": get_install_instructions(plat),
            "message": "WIZ CLI not installed. Pass auto_install: true to install, or install manually.",
        }, start_time=start_time)
        return

    # --- Step 2: Check if authenticated ---
    auth_info = check_authenticated()

    if auth_info["authenticated"]:
        progress_done(f"Authenticated as {auth_info['client_email']}")
        auth_method = "already_authenticated"
    elif auto_auth:
        # Try service account first (CI/CD), then device code (interactive)
        if ci:
            auth_result = authenticate_wizcli_service_account()
        else:
            auth_result = authenticate_wizcli_device_code()

        if auth_result["success"]:
            auth_info = {"authenticated": True, "client_email": auth_result["client_email"]}
            auth_method = auth_result["method"]
            actions_taken.append(f"Authenticated via {auth_method}")
        else:
            write_json_output({
                "status": "failed",
                "installed": True,
                "authenticated": False,
                "version": install_info["version"],
                "client_email": "",
                "platform": plat,
                "install_method": install_method,
                "auth_method": auth_result["method"],
                "actions_taken": actions_taken,
                "error": auth_result.get("output", "Authentication failed"),
                "auth_instructions": get_auth_instructions(),
            }, start_time=start_time)
            return
    else:
        write_json_output({
            "status": "skipped",
            "installed": True,
            "authenticated": False,
            "version": install_info["version"],
            "client_email": "",
            "platform": plat,
            "install_method": install_method,
            "auth_method": "none",
            "actions_taken": actions_taken,
            "auth_instructions": get_auth_instructions(),
            "message": "WIZ CLI installed but not authenticated. Pass auto_auth: true to authenticate, or authenticate manually.",
        }, start_time=start_time)
        return

    # --- Ready ---
    status = "ready" if install_method == "already_installed" and auth_method == "already_authenticated" else "installed"
    progress_done(f"WIZ CLI ready — {install_info['version']} as {auth_info['client_email']}")

    write_json_output({
        "status": status,
        "installed": True,
        "authenticated": True,
        "version": install_info["version"],
        "client_email": auth_info["client_email"],
        "platform": plat,
        "install_method": install_method,
        "auth_method": auth_method,
        "actions_taken": actions_taken,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
