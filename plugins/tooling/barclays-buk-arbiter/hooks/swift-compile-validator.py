#!/usr/bin/env python3
"""Post-removal Swift compilation validation hook.

Validates that iOS code compiles after dead code removal.
Supports xcworkspace, xcodeproj, and SPM projects.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any


def validate_swift_compilation(repo_path: str = ".", scheme: str = None,
                               verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """Validate Swift/iOS compilation after removal.

    Args:
        repo_path: Path to iOS project
        scheme: Xcode scheme (auto-detected if None)
        verbose: Print detailed output

    Returns:
        Tuple of (success, results dict)
    """
    repo_path = Path(repo_path)
    results = {
        "compile_status": "unknown",
        "build_system": None,
        "scheme": scheme,
        "duration_seconds": 0,
        "error_message": None,
    }

    try:
        # Detect build system
        xcworkspaces = list(repo_path.glob("*.xcworkspace"))
        xcprojects = list(repo_path.glob("*.xcodeproj"))

        if xcworkspaces:
            results["build_system"] = "xcworkspace"
            cmd = ["xcodebuild", "build", "-workspace", str(xcworkspaces[0])]
            if scheme:
                cmd.extend(["-scheme", scheme])
            if verbose:
                print(f"🔨 Building workspace: {xcworkspaces[0].name}")

        elif xcprojects:
            results["build_system"] = "xcodeproj"
            cmd = ["xcodebuild", "build", "-project", str(xcprojects[0])]
            if scheme:
                cmd.extend(["-scheme", scheme])
            if verbose:
                print(f"🔨 Building project: {xcprojects[0].name}")

        elif (repo_path / "Package.swift").exists():
            results["build_system"] = "spm"
            cmd = ["swift", "build"]
            if verbose:
                print("🔨 Building SPM package")

        else:
            results["compile_status"] = "skipped"
            results["error_message"] = "No iOS build system detected"
            return True, results

        import time
        start = time.time()

        result = subprocess.run(
            cmd, cwd=str(repo_path),
            capture_output=True, text=True, timeout=900,
        )

        results["duration_seconds"] = round(time.time() - start, 1)

        if result.returncode == 0:
            results["compile_status"] = "success"
            if verbose:
                print(f"✅ Build successful ({results['duration_seconds']}s)")
            return True, results
        else:
            results["compile_status"] = "failure"
            results["error_message"] = result.stderr[:500] if result.stderr else "Build failed"
            if verbose:
                print(f"❌ Build failed:\n{result.stderr[:200]}")
            return False, results

    except subprocess.TimeoutExpired:
        results["compile_status"] = "timeout"
        results["error_message"] = "Build timed out (>15min)"
        return False, results
    except Exception as e:
        results["compile_status"] = "error"
        results["error_message"] = str(e)
        return False, results


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    scheme = None
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--scheme" and i + 1 < len(sys.argv):
            scheme = sys.argv[i + 1]

    success, results = validate_swift_compilation(repo, scheme=scheme, verbose=verbose)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
    elif not verbose:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: Swift compilation {results['compile_status']}")

    sys.exit(0 if success else 1)
