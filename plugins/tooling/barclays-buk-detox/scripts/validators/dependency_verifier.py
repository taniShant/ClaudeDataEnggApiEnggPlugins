#!/usr/bin/env python3
"""CWE-937 dependency resolution verifier for all ecosystems.

Resolves the dependency tree for a given repository and checks whether a
vulnerable package version has been removed and (optionally) a safe version
is present.

Input (JSON stdin):
    {
        "repo_dir": "/path/to/repo",
        "package_name": "log4j:log4j",
        "vulnerable_version": "1.2.17",
        "safe_version": "1.2.26",
        "ecosystem": "gradle"
    }
    Note: "ecosystem" is optional — auto-detected from repo_dir if omitted.

Output (JSON stdout):
    {
        "status": "success",
        "verdict": "PASS",
        "ecosystem": "gradle",
        "vulnerable_version_found": false,
        "safe_version_found": true,
        "method": "dep_tree",
        "detail": "log4j:log4j:1.2.17 not found in resolved dependencies"
    }
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, run_cmd, log, progress, progress_done
from scripts.core.errors import error_exit


ECOSYSTEM_COMMANDS: dict[str, dict] = {
    "gradle": {
        "indicators": ["build.gradle", "build.gradle.kts", "settings.gradle"],
        "dep_cmd_wrapper": ["./gradlew", "dependencies", "--configuration", "runtimeClasspath"],
        "dep_cmd_direct": ["gradle", "dependencies", "--configuration", "runtimeClasspath"],
    },
    "maven": {
        "indicators": ["pom.xml"],
        "dep_cmd": ["mvn", "dependency:tree", "-DoutputType=text"],
    },
    "npm": {
        "indicators": ["package.json", "package-lock.json"],
        "dep_cmd": ["npm", "ls", "--all", "--json"],
    },
    "pip": {
        "indicators": ["requirements.txt", "pyproject.toml", "setup.py"],
        "dep_cmd": ["pip", "show"],  # + package_name appended at runtime
    },
    "go": {
        "indicators": ["go.mod"],
        "dep_cmd": ["go", "list", "-m", "all"],
    },
    "dotnet": {
        "indicators": ["*.csproj", "*.sln"],
        "dep_cmd": ["dotnet", "list", "package", "--include-transitive"],
    },
    "cargo": {
        "indicators": ["Cargo.toml"],
        "dep_cmd": ["cargo", "tree"],
    },
}

# Priority order for ecosystem detection
_ECOSYSTEM_PRIORITY = ["gradle", "maven", "npm", "pip", "go", "dotnet", "cargo"]


def detect_ecosystem(repo_dir: str) -> str | None:
    """Detect build ecosystem from repo directory.

    Returns ecosystem name or None.
    Checks for indicator files in priority order: gradle > maven > npm > pip > go > dotnet > cargo.
    """
    repo_path = Path(repo_dir)
    for name in _ECOSYSTEM_PRIORITY:
        indicators = ECOSYSTEM_COMMANDS[name]["indicators"]
        for indicator in indicators:
            if "*" in indicator:
                if list(repo_path.glob(indicator)):
                    return name
            else:
                if (repo_path / indicator).exists():
                    return name
    return None


def get_dep_command(ecosystem: str, repo_dir: str, package_name: str | None = None) -> list[str]:
    """Get the dependency resolution command for the ecosystem.

    For gradle: checks if ./gradlew exists (uses wrapper), otherwise uses gradle directly.
    For pip: appends package_name to the command.
    Returns command as list[str].
    """
    eco = ECOSYSTEM_COMMANDS.get(ecosystem)
    if eco is None:
        return []

    if ecosystem == "gradle":
        if (Path(repo_dir) / "gradlew").exists():
            return list(eco["dep_cmd_wrapper"])
        return list(eco["dep_cmd_direct"])

    cmd = list(eco["dep_cmd"])

    if ecosystem == "pip" and package_name:
        cmd.append(package_name)

    return cmd


def resolve_dep_tree(
    repo_dir: str,
    ecosystem: str,
    package_name: str | None = None,
    timeout: int = 120,
) -> dict:
    """Run the ecosystem's dependency resolution command.

    Returns {"status": "success"|"error", "output": str, "ecosystem": str}.
    """
    cmd = get_dep_command(ecosystem, repo_dir, package_name)
    if not cmd:
        return {
            "status": "error",
            "output": f"No command configured for ecosystem: {ecosystem}",
            "ecosystem": ecosystem,
        }

    log(f"Resolving dependency tree — ecosystem={ecosystem}, cmd={cmd}")
    result = run_cmd(cmd, cwd=Path(repo_dir), timeout=timeout)

    combined = result["stdout"] + result["stderr"]

    if result["exit_code"] != 0:
        # npm ls returns non-zero when there are peer-dep warnings but still emits JSON
        if ecosystem == "npm" and result["stdout"].strip():
            return {"status": "success", "output": result["stdout"], "ecosystem": ecosystem}
        return {"status": "error", "output": combined, "ecosystem": ecosystem}

    return {"status": "success", "output": combined, "ecosystem": ecosystem}


def check_version_absent(dep_output: str, package_name: str, vulnerable_version: str) -> bool:
    """Check if the vulnerable version is NOT present in the dependency tree output.

    Handles various output formats:
    - Gradle: 'group:artifact:version' patterns
    - Maven: '[INFO]    +- group:artifact:jar:version'
    - npm JSON: {"version": "x.y.z"} in nested dependencies
    - pip: 'Version: x.y.z' line
    - Go: 'module/path vx.y.z' lines
    - dotnet: '> PackageName  version' lines
    - Cargo: 'crate vx.y.z' lines

    Returns True if the vulnerable version is NOT found (meaning fix worked).
    """
    return not _version_in_output(dep_output, package_name, vulnerable_version)


def check_version_present(dep_output: str, package_name: str, safe_version: str) -> bool:
    """Check if the safe version IS present in the dependency tree output.

    Same format handling as check_version_absent.
    Returns True if the safe version IS found.
    """
    return _version_in_output(dep_output, package_name, safe_version)


def _version_in_output(dep_output: str, package_name: str, version: str) -> bool:
    """Return True if the given package+version combination appears in dep_output.

    Covers Gradle, Maven, npm JSON, pip, Go, dotnet, and Cargo output formats.
    """
    escaped_version = re.escape(version)

    # --- npm: attempt to parse JSON first ---
    if dep_output.strip().startswith("{"):
        try:
            npm_data = json.loads(dep_output)
            return _npm_json_has_version(npm_data, version)
        except json.JSONDecodeError:
            pass  # Fall through to text-based checks

    # Derive a short artifact name from 'group:artifact' or plain 'name'
    short_name = package_name.split(":")[-1] if ":" in package_name else package_name
    escaped_short = re.escape(short_name)

    # Gradle: group:artifact:version  (e.g. log4j:log4j:1.2.17)
    if re.search(rf"{re.escape(package_name)}:{escaped_version}", dep_output):
        return True

    # Gradle/generic: artifactName:version
    if re.search(rf"{escaped_short}:{escaped_version}", dep_output):
        return True

    # Maven: group:artifact:jar:version  or  group:artifact:version (text tree)
    # Handles arbitrary intermediate type/scope segments separated by colons.
    if re.search(rf"{escaped_short}(?::[^\s:]+)*:{escaped_version}", dep_output):
        return True

    # pip: 'Version: x.y.z'
    if re.search(rf"Version:\s+{escaped_version}", dep_output, re.IGNORECASE):
        return True

    # Go: 'module/path vx.y.z'
    if re.search(rf"{escaped_short}\s+v?{escaped_version}", dep_output):
        return True

    # dotnet: '> PackageName  version'
    if re.search(rf">\s+{escaped_short}\s+{escaped_version}", dep_output, re.IGNORECASE):
        return True

    # Cargo: 'crate vx.y.z'
    if re.search(rf"{escaped_short}\s+v{escaped_version}", dep_output):
        return True

    return False


def _npm_json_has_version(node: dict, version: str) -> bool:
    """Recursively walk npm ls --json output to find a specific version."""
    if node.get("version") == version:
        return True
    for dep in node.get("dependencies", {}).values():
        if _npm_json_has_version(dep, version):
            return True
    return False


def parse_sbom_for_package(sbom_data: dict, package_name: str) -> dict | None:
    """Parse a CycloneDX JSON SBOM to find a specific package.

    Returns {"name": str, "version": str, "purl": str} or None if not found.

    SBOM format:
        sbom_data["components"] is a list of
        {"name": "...", "group": "...", "version": "...", "purl": "..."}

    package_name can be 'group:name' (Maven) or just 'name' (npm, pip, etc.).
    """
    components = sbom_data.get("components", [])
    if not isinstance(components, list):
        return None

    # Parse package_name into optional group and name parts
    if ":" in package_name:
        group_part, name_part = package_name.split(":", 1)
    else:
        group_part = None
        name_part = package_name

    for component in components:
        comp_name = component.get("name", "")
        comp_group = component.get("group", "")

        if group_part is not None:
            # Match on both group and name
            if comp_group == group_part and comp_name == name_part:
                return {
                    "name": comp_name,
                    "version": component.get("version", ""),
                    "purl": component.get("purl", ""),
                }
        else:
            # Match on name only
            if comp_name == name_part:
                return {
                    "name": comp_name,
                    "version": component.get("version", ""),
                    "purl": component.get("purl", ""),
                }

    return None


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    package_name = input_data.get("package_name", "")
    vulnerable_version = input_data.get("vulnerable_version", "")
    safe_version = input_data.get("safe_version", "")
    ecosystem = input_data.get("ecosystem")  # optional

    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")
    if not Path(repo_dir).is_dir():
        error_exit(f"Directory not found: {repo_dir}", "dir_check")
    if not package_name:
        error_exit("package_name is required", "input_validation")
    if not vulnerable_version:
        error_exit("vulnerable_version is required", "input_validation")

    # --- Detect ecosystem if not supplied ---
    if not ecosystem:
        progress("Detecting ecosystem...")
        ecosystem = detect_ecosystem(repo_dir)
        if ecosystem is None:
            write_json_output({
                "status": "success",
                "verdict": "ERROR",
                "ecosystem": None,
                "vulnerable_version_found": None,
                "safe_version_found": None,
                "method": "dep_tree",
                "detail": "Could not detect build ecosystem in repo_dir.",
            }, start_time=start_time)
            return
        log(f"Detected ecosystem: {ecosystem}")

    # --- Resolve dependency tree ---
    progress(f"Resolving dependency tree ({ecosystem})...")
    dep_result = resolve_dep_tree(repo_dir, ecosystem, package_name)

    if dep_result["status"] == "error":
        progress_done("ERROR — dependency resolution failed")
        write_json_output({
            "status": "success",
            "verdict": "ERROR",
            "ecosystem": ecosystem,
            "vulnerable_version_found": None,
            "safe_version_found": None,
            "method": "dep_tree",
            "detail": f"Dependency resolution failed: {dep_result['output'][:500]}",
        }, start_time=start_time)
        return

    dep_output = dep_result["output"]

    # --- Check versions ---
    vulnerable_found = not check_version_absent(dep_output, package_name, vulnerable_version)
    safe_found = check_version_present(dep_output, package_name, safe_version) if safe_version else None

    # --- Verdict ---
    if not vulnerable_found and (safe_found is True or safe_version == ""):
        verdict = "PASS"
        detail = f"{package_name}:{vulnerable_version} not found in resolved dependencies"
        if safe_found:
            detail += f"; {package_name}:{safe_version} confirmed present"
    elif vulnerable_found:
        verdict = "FAIL"
        detail = f"{package_name}:{vulnerable_version} still present in resolved dependencies"
    else:
        # vulnerable absent but safe not confirmed
        verdict = "PASS"
        detail = f"{package_name}:{vulnerable_version} not found in resolved dependencies"
        if safe_version and not safe_found:
            verdict = "PARTIAL"
            detail += f"; safe version {safe_version} not confirmed present"

    progress_done(f"Dependency verification {verdict} — {package_name}")

    write_json_output({
        "status": "success",
        "verdict": verdict,
        "ecosystem": ecosystem,
        "vulnerable_version_found": vulnerable_found,
        "safe_version_found": safe_found,
        "method": "dep_tree",
        "detail": detail,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
