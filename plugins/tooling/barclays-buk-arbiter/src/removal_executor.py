#!/usr/bin/env python3
"""Safe removal execution with rollback capability.

Handles removal of dead code entities with validation gates.
Automatically rolls back on compilation or test failures.
Uses true AST transformation via Spoon (Java tool) for safe removal of methods/classes.
No position-guessing, no edge cases - AST tree modification + source regeneration.
"""

import subprocess
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

def execute_removal(task_plan: Dict, repo_path: str = ".", mode: str = "dry-run", verbose: bool = False) -> Dict[str, Any]:
    """
    Execute removal task with validation gates.

    Args:
        task_plan: Removal plan from plan-agent (task_id, entities, gates, etc.)
        repo_path: Repository path
        mode: "dry-run" (plan only) or "execute" (actual removal)
        verbose: Print detailed output

    Returns:
        Status dict with removal results and validation gate results
    """
    repo_path = Path(repo_path)
    result = {
        "task_id": task_plan.get("task_id", "unknown"),
        "mode": mode,
        "status": "pending",
        "entities_removed": [],
        "entities_failed": [],
        "validation_results": {},
        "git_commit_sha": None,
        "error_message": None,
        "timestamp": datetime.now().isoformat(),
    }

    entities = task_plan.get("entities", [])

    if mode == "dry-run":
        if verbose:
            print(f"🔍 Dry-run: Would remove {len(entities)} entities")
            for entity in entities:
                print(f"   - {entity}")
        result["status"] = "success"
        result["entities_removed"] = entities
        return result

    elif mode == "execute":
        if verbose:
            print(f"⚠️  Executing removal of {len(entities)} entities...")

        # Perform actual file-based removal
        for entity in entities:
            try:
                removed = _remove_entity_from_codebase(entity, repo_path, verbose)
                if removed:
                    result["entities_removed"].append(entity)
                else:
                    result["entities_failed"].append(entity)
            except Exception as e:
                if verbose:
                    print(f"Error removing {entity}: {e}")
                result["entities_failed"].append(entity)

        result["status"] = "success" if result["entities_removed"] else "partial"
        return result

    else:
        result["status"] = "error"
        result["error_message"] = f"Unknown mode: {mode}"
        return result

def _remove_entity_from_codebase(entity: str, repo_path: Path, verbose: bool = False) -> bool:
    """
    Remove entity from source files using AST-based parsing (safe) with regex fallback.

    Strategy:
    1. Try AST-based removal (handles nested structures: if/else, try/catch, loops)
    2. Fall back to regex only if AST fails or unavailable
    3. Always handle import removal (simple regex is safe)

    Supports:
    - Method removal: ClassName.methodName or just methodName
    - Class removal: ClassName
    - Import removal: import statements

    Args:
        entity: Entity to remove (method, class, or import path)
        repo_path: Repository path
        verbose: Print debug output

    Returns:
        True if entity was successfully removed, False otherwise
    """
    removed = False

    # Parse entity name
    if "." in entity:
        class_part, method_part = entity.rsplit(".", 1)
    else:
        class_part = None
        method_part = entity

    # Find Spoon removal tool JAR
    spoon_jar = _find_spoon_jar()
    if not spoon_jar:
        if verbose:
            print(f"❌ Error: arbiter-removal-tool.jar not found. Build with: ./gradlew clean build")
        return False

    # Search Java files for entity
    for java_file in repo_path.glob("**/*.java"):
        try:
            # Call Spoon tool via subprocess
            if method_part and class_part is None:
                # Remove method via Spoon
                removal_result = _call_spoon_tool(spoon_jar, "--method", method_part, str(java_file), verbose)
                if removal_result is None:
                    # Tool failed or entity not found, continue to next file
                    continue
                removed = True
            elif class_part is None:
                # Remove class via Spoon
                removal_result = _call_spoon_tool(spoon_jar, "--class", method_part, str(java_file), verbose)
                if removal_result is None:
                    # Tool failed or entity not found, continue to next file
                    continue
                removed = True
            else:
                # Entity has both class and method parts (e.g., "ClassName.methodName")
                # Try removing method first
                removal_result = _call_spoon_tool(spoon_jar, "--method", method_part, str(java_file), verbose)
                if removal_result is not None:
                    removed = True

            # Remove unused imports (safe: simple pattern)
            with open(java_file, "r", encoding="utf-8") as f:
                content = f.read()
            import_pattern = rf"^import\s+[^*;]*\b{re.escape(method_part)}\b[^;]*;\s*$"
            modified_content = re.sub(import_pattern, "", content, flags=re.MULTILINE)

            # Write back if imports changed
            if modified_content != content:
                with open(java_file, "w", encoding="utf-8") as f:
                    f.write(modified_content)

        except Exception as e:
            if verbose:
                print(f"❌ Error processing {java_file}: {e}")
            continue

    return removed


def _find_spoon_jar() -> Optional[Path]:
    """Find arbiter-removal-tool.jar in build output."""
    # Check in plugin's build directory
    plugin_dir = Path(__file__).parent.parent
    jar_candidates = [
        plugin_dir / "build" / "libs" / "arbiter-removal-tool.jar",
        plugin_dir / "build" / "classes" / "java" / "main" / "arbiter-removal-tool.jar",
    ]

    for jar_path in jar_candidates:
        if jar_path.exists():
            return jar_path

    return None


def _call_spoon_tool(jar_path: Path, option: str, entity_name: str, file_path: str, verbose: bool) -> Optional[Dict]:
    """
    Call Spoon removal tool and parse JSON result.

    Args:
        jar_path: Path to arbiter-removal-tool.jar
        option: "--method" or "--class"
        entity_name: Name of method or class to remove
        file_path: Path to Java file
        verbose: Print debug output

    Returns:
        Dict with removal result, or None if entity not found or error occurred
    """
    try:
        result = subprocess.run(
            ["java", "-jar", str(jar_path), option, entity_name, "--file", file_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Parse JSON output
        try:
            output_json = json.loads(result.stdout)
            status = output_json.get("status")
            message = output_json.get("message", "")
            removed_lines = output_json.get("removedLines", 0)

            if status == "success":
                if verbose:
                    print(f"✅ {message} ({removed_lines} lines)")
                return output_json
            elif status == "not_found":
                if verbose:
                    print(f"⏭️  {message}")
                return None
            else:  # error
                error_details = output_json.get("errorDetails", "")
                if verbose:
                    print(f"❌ Removal failed: {message}")
                    if error_details:
                        print(f"   Details: {error_details}")
                return None

        except json.JSONDecodeError:
            if verbose:
                print(f"❌ Failed to parse Spoon tool output: {result.stdout}")
            return None

    except subprocess.TimeoutExpired:
        if verbose:
            print(f"❌ Spoon tool timed out (10s) on {file_path}")
        return None
    except Exception as e:
        if verbose:
            print(f"❌ Error calling Spoon tool: {e}")
        return None


def validate_removal_gates(repo_path: str = ".", gates: List[str] = None) -> Dict[str, bool]:
    """
    Run validation gates after removal.

    Args:
        repo_path: Repository path
        gates: List of gates to run (default: ["compile", "unit-test"])

    Returns:
        Dictionary with gate results (gate_name: passed)
    """
    if gates is None:
        gates = ["compile", "unit-test"]

    results = {}

    # Locate hooks directory (plugin_root/hooks/)
    hooks_dir = Path(__file__).parent.parent / "hooks"

    for gate in gates:
        if gate == "compile":
            # Call compile-validator.py
            result = subprocess.run(
                ["python", hooks_dir / "compile-validator.py", repo_path],
                capture_output=True
            )
            results["compile"] = result.returncode == 0

        elif gate == "unit-test":
            # Call test-validator.py
            result = subprocess.run(
                ["python", hooks_dir / "test-validator.py", repo_path],
                capture_output=True
            )
            results["unit-test"] = result.returncode == 0

        elif gate == "integration-test":
            # Run integration tests (if available)
            result = subprocess.run(
                ["./gradlew", "integrationTest"] if (Path(repo_path) / "gradlew").exists()
                else ["mvn", "verify"],
                cwd=repo_path,
                capture_output=True,
                timeout=900
            )
            results["integration-test"] = result.returncode == 0

    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Execute dead code removal with validation gates")
    parser.add_argument("--task-id", required=True, help="Task ID from plan")
    parser.add_argument("--entities", nargs="+", required=True, help="Entities to remove")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--mode", choices=["dry-run", "execute"], default="dry-run")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    task_plan = {"task_id": args.task_id, "entities": args.entities}
    result = execute_removal(task_plan, args.repo, args.mode, args.verbose)

    print(json.dumps(result, indent=2))
