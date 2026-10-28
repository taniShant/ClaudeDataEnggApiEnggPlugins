#!/usr/bin/env python3
"""Post-removal compilation validation hook.

Validates that code compiles successfully after dead code removal.
Used as mandatory gate before committing removal task.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Tuple, Dict, Any

def validate_compilation(repo_path: str = ".", verbose: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that code compiles after removal.

    Args:
        repo_path: Path to repository
        verbose: Print detailed output

    Returns:
        Tuple of (success: bool, results: dict with details)
    """
    repo_path = Path(repo_path)
    results = {
        "compile_status": "unknown",
        "build_system": None,
        "duration_seconds": 0,
        "error_message": None,
        "stderr_output": ""
    }

    try:
        # Try Gradle first (modern Java projects)
        gradle_wrapper = repo_path / "gradlew"
        if gradle_wrapper.exists() or (repo_path / "build.gradle").exists():
            results["build_system"] = "gradle"
            if verbose:
                print("🔨 Using Gradle for compilation check...")

            result = subprocess.run(
                ["./gradlew", "clean", "build", "-x", "test", "--daemon"],
                cwd=repo_path,
                capture_output=True,
                timeout=600,
                text=True
            )

            if result.returncode == 0:
                results["compile_status"] = "success"
                if verbose:
                    print("✅ Gradle build successful")
                return True, results
            else:
                results["compile_status"] = "failure"
                results["error_message"] = "Gradle build failed"
                results["stderr_output"] = result.stderr[:500]  # First 500 chars
                if verbose:
                    print(f"❌ Gradle build failed:\n{result.stderr[:200]}...")
                return False, results

        # Try Maven fallback (traditional Java projects)
        pom = repo_path / "pom.xml"
        if pom.exists():
            results["build_system"] = "maven"
            if verbose:
                print("🔨 Using Maven for compilation check...")

            result = subprocess.run(
                ["mvn", "clean", "package", "-DskipTests", "-q"],
                cwd=repo_path,
                capture_output=True,
                timeout=600,
                text=True
            )

            if result.returncode == 0:
                results["compile_status"] = "success"
                if verbose:
                    print("✅ Maven build successful")
                return True, results
            else:
                results["compile_status"] = "failure"
                results["error_message"] = "Maven build failed"
                results["stderr_output"] = result.stderr[:500]
                if verbose:
                    print(f"❌ Maven build failed:\n{result.stderr[:200]}...")
                return False, results

        # No build system found
        results["compile_status"] = "skipped"
        results["error_message"] = "No build system detected (Gradle/Maven)"
        if verbose:
            print("⚠️ No build system found; skipping compilation check")
        return True, results  # Not a failure if no build system

    except subprocess.TimeoutExpired:
        results["compile_status"] = "timeout"
        results["error_message"] = "Compilation timed out (>10min)"
        if verbose:
            print("⏱️ Compilation check timed out")
        return False, results
    except Exception as e:
        results["compile_status"] = "error"
        results["error_message"] = str(e)
        if verbose:
            print(f"💥 Unexpected error: {e}")
        return False, results

if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    json_output = "--json" in sys.argv

    success, results = validate_compilation(repo, verbose=verbose)

    if json_output:
        print(json.dumps(results, indent=2))
    elif not verbose:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: Compilation {results['compile_status']}")

    sys.exit(0 if success else 1)
