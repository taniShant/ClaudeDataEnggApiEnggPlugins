#!/usr/bin/env python3
"""iOS Removal Executor — safe removal with backup branch and auto-rollback.

Adapted from f_barclays-claude-code-plugins arbiter_remove_ios.py.

Removal is syntax-aware for Swift: each entity's declaration is re-located with
tree-sitter in the file's current state, and its full line range (attributes and
doc comments included) is removed. Every attempt is appended to an outcome ledger
(.arbiter/swift/OUTCOMES.jsonl) so predictions can be compared with real results
— see ios_calibration_report.py.
"""

import json
import re
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from .ast_reference_scanner import SWIFT_LANGUAGE
    from .ios_call_graph_analyzer import _extract_swift_entities_ast
    from .arbiter_meta import plugin_version, require_stamp, stamp
except ImportError:
    from ast_reference_scanner import SWIFT_LANGUAGE
    from ios_call_graph_analyzer import _extract_swift_entities_ast
    from arbiter_meta import plugin_version, require_stamp, stamp

if SWIFT_LANGUAGE is not None:
    from tree_sitter import Parser

TYPE_KINDS = ("class", "struct", "enum", "protocol", "actor")
OUTCOMES_FILE = Path(".arbiter") / "swift" / "OUTCOMES.jsonl"
LOGS_DIR = Path(".arbiter") / "swift" / "logs"
MAX_BUILDS_PER_BATCH = 12  # bisection budget per batch (each is a full build)

# xcodebuild settings; override with --destination / --build-timeout
BUILD_DESTINATION = "generic/platform=iOS Simulator"  # no code signing needed
TEST_DESTINATION: Optional[str] = None  # None = first available iPhone simulator
BUILD_TIMEOUT = 3600  # large apps can take a long time to build cold

# Compiler errors that name the symbol that went missing
COMPILER_ERROR_PATTERNS = [
    re.compile(r"cannot find (?:type )?'(\w+)' in scope"),
    re.compile(r"has no member '(\w+)'"),
    re.compile(r"no type named '(\w+)'"),
    re.compile(r"use of undeclared (?:type|identifier) '(\w+)'"),
    re.compile(r"no visible @interface .* declares the selector '(\w+)"),
    re.compile(r"Build input file cannot be found: '[^']*/(\w+)\.swift'"),
]


def execute_ios_removal(plan_path: str, project_path: str,
                        scheme: str = None, target_task: int = None,
                        dry_run: bool = False, commit: bool = True,
                        max_batches: int = None, stop_on_failure: bool = False,
                        allow_unstamped: bool = False) -> Dict[str, Any]:
    """Execute iOS dead code removal from a plan file.

    Args:
        plan_path: Path to PLAN.json
        project_path: Path to iOS project (main repo; submodules are handled)
        scheme: Xcode scheme for validation
        target_task: Specific task ID to run (None = pending tasks in order)
        dry_run: Preview without removing
        commit: Git commit each batch that passes validation
        max_batches: Run at most this many pending batches
        stop_on_failure: Stop after the first batch with failed entities
            (default: continue — failed batches are restored, later ones are independent)
        allow_unstamped: Accept a plan not produced by the plugin's planner

    Returns:
        Removal log with batch and per-entity results
    """
    project_path = Path(project_path).resolve()

    with open(plan_path) as f:
        plan = json.load(f)
    require_stamp(plan, "PLAN.json", allow_unstamped)

    tasks = plan.get("tasks", [])
    pending = [t for t in tasks if t.get("status") == "pending"]

    if not pending:
        return {"status": "complete", "message": "All batches already completed"}

    if target_task:
        pending = [t for t in pending if t["taskId"] == target_task]
        if not pending:
            return {"status": "error", "message": f"Task {target_task} not found or completed"}
    if max_batches:
        pending = pending[:max_batches]

    if SWIFT_LANGUAGE is None:
        return {"status": "blocked", "message": "tree-sitter-swift not installed — "
                "run: pip install tree-sitter tree-sitter-swift"}

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = project_path / LOGS_DIR

    if not dry_run:
        dirty = _dirty_repos(project_path)
        if dirty:
            return {"status": "blocked", "message": "Uncommitted changes to tracked files in: "
                    + ", ".join(dirty) + ". Commit or stash them before running arbiter-remove "
                    "(untracked files are ignored)."}
        # Baseline: the project must build before any removal
        if not _validate_environment(project_path, scheme, log_dir / f"{run_id}-baseline.log"):
            return {"status": "blocked", "message": "ENVIRONMENT_BLOCKED: project does not build before "
                    f"removal — see {LOGS_DIR}/{run_id}-baseline.log. Fix the build "
                    "(pod install, Xcode version, …) before running arbiter-remove."}

    # Create backup branch (main repo and submodules)
    backup_branch = None
    if not dry_run:
        backup_branch = _create_backup(project_path)

    removal_log = {
        "runId": run_id,
        "timestamp": datetime.now().isoformat(),
        "projectPath": str(project_path),
        "dryRun": dry_run,
        "backupBranch": backup_branch,
        "logsDir": str(log_dir),
        "generatedBy": stamp(["ios_removal_executor.py"]),
        "batches": [],
    }

    total_removed = 0
    environment_broken = False
    removed_types: Set[Tuple[str, str]] = set()  # (file, type name) removed in this run

    for task in pending:
        batch_result = _execute_batch(project_path, task, scheme, dry_run, log_dir, run_id,
                                      removed_types)
        removal_log["batches"].append(batch_result)
        if not dry_run:
            _append_outcomes(project_path, run_id, task, batch_result)

        for t in tasks:
            if t["taskId"] == task["taskId"] and not dry_run:
                t["status"] = "environment_blocked" if batch_result.get("environmentBroken") else "completed"
                t["outcomes"] = batch_result["outcomes"]

        total_removed += batch_result["entitiesRemoved"]
        if commit and not dry_run and batch_result["entitiesRemoved"]:
            batch_result["commits"] = _commit_batch(project_path, task, batch_result, run_id)

        if batch_result.get("environmentBroken"):
            environment_broken = True
            break
        if stop_on_failure and batch_result["failures"]:
            break

    # Save updated plan (dry runs leave the plan untouched)
    if not dry_run:
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)

    failures = [f for b in removal_log["batches"] for f in b["errors"]]
    removal_log["totalRemoved"] = total_removed
    removal_log["failureSummary"] = failures
    removal_log["status"] = ("environment_blocked" if environment_broken
                             else "success" if not any(b["failures"] for b in removal_log["batches"])
                             else "completed_with_failures")
    return removal_log


class _BatchRun:
    """Applies a batch, validates, and narrows down failures.

    On a failing build: remove now-superfluous SwiftLint disable comments in touched
    files and re-validate; then drop entities named in compiler errors; then halve
    the remainder until every entity is either validated or isolated as a failure.
    Every validation's output is saved under .arbiter/swift/logs/.
    """

    def __init__(self, project_path: Path, task: Dict, scheme: Optional[str],
                 log_dir: Path, run_id: str):
        self.project_path = project_path
        self.task = task
        self.scheme = scheme
        self.log_dir = log_dir
        self.run_id = run_id
        self.builds_left = MAX_BUILDS_PER_BATCH
        self.validations = 0
        self.outcomes: Dict[str, Dict[str, Any]] = {}
        self.kept_files: Set[Path] = set()
        self.environment_broken = False
        self.last_stage: Optional[str] = None
        self.lint_fixes: List[str] = []

    def validate(self, label: str) -> Dict[str, Any]:
        self.builds_left -= 1
        self.validations += 1
        result = _run_validation(self.project_path, self.task["category"], self.scheme)
        self.last_stage = result["stage"] or self.last_stage
        _save_log(self.log_dir / f"{self.run_id}-task{self.task['taskId']}-"
                                 f"{self.validations:02d}-{label}.log", result["output"])
        return result

    def run(self, entities: List[Dict]) -> List[Dict]:
        if self.environment_broken:
            for e in entities:
                self.outcomes[_key(e)] = {"outcome": "rolled_back", "attributed": False,
                                          "detail": "not attempted — build environment broken"}
            return []
        if self.builds_left <= 0:
            for e in entities:
                self.outcomes[_key(e)] = {"outcome": "rolled_back", "attributed": False,
                                          "detail": f"build budget ({MAX_BUILDS_PER_BATCH}) exhausted"}
            return []

        snapshots: Dict[Path, Optional[bytes]] = {}
        attempt = _apply_removals(self.project_path, entities, False, snapshots)
        applied = [e for e in entities if attempt[_key(e)]["outcome"] == "removed"]
        for e in entities:
            if e not in applied:
                self.outcomes[_key(e)] = attempt[_key(e)]
        if not applied:
            return []

        result = self.validate(f"{len(applied)}-entities")
        if not result["passed"]:
            fixed = _fix_superfluous_lint_disables(result["output"], snapshots)
            if fixed:
                self.lint_fixes += fixed
                result = self.validate("lint-fix")
        if result["passed"]:
            for e in applied:
                self.outcomes[_key(e)] = attempt[_key(e)]
            self.kept_files |= set(snapshots)
            return applied

        _restore(snapshots)
        stage = result["stage"] or "build"
        culprits = _attribute_failures(result["output"], applied)
        for e in applied:
            if e["name"] in culprits:
                self.outcomes[_key(e)] = {"outcome": f"{stage}_failed", "attributed": True,
                                          "detail": culprits[e["name"]]}
        rest = [e for e in applied if e["name"] not in culprits]
        if culprits:
            return self.run(rest)

        if len(rest) == 1:
            # Isolated — but make sure the build environment itself still works
            if not self._baseline_ok():
                self.environment_broken = True
                self.outcomes[_key(rest[0])] = {"outcome": "rolled_back", "attributed": False,
                                                "detail": "build environment broken (baseline fails)"}
                return []
            self.outcomes[_key(rest[0])] = {
                "outcome": f"{stage}_failed", "attributed": True,
                "detail": "isolated by bisection — " + _first_error(result["output"])}
            return []

        middle = len(rest) // 2
        kept = self.run(rest[:middle])
        return kept + self.run(rest[middle:])

    def _baseline_ok(self) -> bool:
        if getattr(self, "_baseline_checked", False):
            return True
        self._baseline_checked = True
        self.builds_left -= 1
        passed, output = _validate_compile(self.project_path, self.scheme)
        _save_log(self.log_dir / f"{self.run_id}-task{self.task['taskId']}-baseline-recheck.log", output)
        return passed


def _execute_batch(project_path: Path, task: Dict, scheme: Optional[str],
                   dry_run: bool, log_dir: Path, run_id: str,
                   removed_types: Optional[Set[Tuple[str, str]]] = None) -> Dict[str, Any]:
    """Execute a single removal batch; failing entities are isolated, the rest kept."""
    entities = task["entities"]
    start_time = time.time()

    if dry_run:
        outcomes = _apply_removals(project_path, entities, True, {})
        for o in outcomes.values():
            if o["outcome"] == "removed":
                o["outcome"] = "would_remove"
        run = None
    else:
        run = _BatchRun(project_path, task, scheme, log_dir, run_id)
        run.run(entities)
        outcomes = run.outcomes

    # Members whose type went in this batch or an earlier one were removed with it
    removed_types = removed_types if removed_types is not None else set()
    removed_types |= {(e.get("file"), e.get("name")) for e in entities
                      if e.get("type") in TYPE_KINDS
                      and outcomes.get(_key(e), {}).get("outcome") in ("removed", "would_remove")}
    for e in entities:
        o = outcomes.get(_key(e), {})
        if (o.get("outcome") == "skipped" and e.get("owner")
                and (e.get("file"), e["owner"]) in removed_types):
            o.update({"outcome": "would_remove" if dry_run else "removed",
                      "detail": f"removed with its parent {e['owner']}"})

    removed = [e for e in entities if outcomes.get(_key(e), {}).get("outcome") == "removed"]
    failed = [k for k, o in outcomes.items()
              if o["outcome"] in ("build_failed", "tests_failed", "rolled_back")]
    errors = [
        f"{o['outcome']}: {key} — {o['detail']}"
        for key, o in outcomes.items() if o["outcome"] not in ("removed", "would_remove")
    ]

    return {
        "taskId": task["taskId"],
        "category": task["category"],
        "success": not failed,
        "failures": len(failed),
        "entitiesRemoved": len(removed),
        "entities": [_key(e) for e in removed] if not dry_run else
                    [k for k, o in outcomes.items() if o["outcome"] == "would_remove"],
        "outcomes": outcomes,
        "errors": errors,
        "validationPassed": not failed,
        "validationStage": run.last_stage if run else None,
        "validations": run.validations if run else 0,
        "lintFixes": run.lint_fixes if run else [],
        "keptFiles": sorted(str(p) for p in run.kept_files) if run else [],
        "environmentBroken": bool(run and run.environment_broken),
        "time": round(time.time() - start_time, 2),
        "dryRun": dry_run,
    }


def _apply_removals(project_path: Path, entities: List[Dict], dry_run: bool,
                    snapshots: Dict[Path, Optional[bytes]]) -> Dict[str, Dict[str, Any]]:
    """Remove entities file by file, bottom-up so earlier line numbers stay valid."""
    outcomes: Dict[str, Dict[str, Any]] = {}
    by_file: Dict[str, List[Dict]] = {}
    for e in entities:
        by_file.setdefault(e.get("file", ""), []).append(e)

    for file_entities in by_file.values():
        for entity in sorted(file_entities, key=lambda e: e.get("line", 0), reverse=True):
            outcome, detail = _remove_entity(project_path, entity, snapshots, dry_run)
            outcomes[_key(entity)] = {"outcome": outcome, "detail": detail, "attributed": False}
    return outcomes


def _remove_entity(project_path: Path, entity: Dict,
                   snapshots: Dict[Path, Optional[bytes]], dry_run: bool) -> Tuple[str, str]:
    """Remove a single entity's declaration. Returns (outcome, detail)."""
    file_path = entity.get("file", "")
    full_path = project_path / file_path
    if not file_path or not full_path.exists():
        return "skipped", "file not found"

    if entity.get("language", "swift") != "swift":
        return "skipped", "syntax-aware removal not supported for Objective-C yet"

    if Parser(SWIFT_LANGUAGE).parse(full_path.read_bytes()).root_node.has_error:
        return "skipped", "file contains syntax the parser can't fully read — remove manually"

    decl = _locate_declaration(project_path, full_path, entity)
    if decl is None:
        return "skipped", "declaration not found in current file (removed with its parent?)"
    if not decl.get("ownsLines"):
        return "skipped", "declaration shares lines with other code"

    content = full_path.read_bytes()
    lines = content.split(b"\n")
    start, end = decl["startLine"], decl["endLine"]

    if entity.get("type") in TYPE_KINDS:
        # Pre-removal member scan — mandatory before removing a type
        decl_text = b"\n".join(lines[start - 1:end]).decode(errors="replace")
        active_refs = _scan_members(decl_text, full_path, project_path, entity.get("name", ""))
        if active_refs:
            summary = "; ".join(
                f"{name}: {refs[0][0]}:{refs[0][1]}" for name, refs in active_refs[:3]
            )
            return "blocked", f"{len(active_refs)} member(s) with external callers — {summary}"

    if dry_run:
        return "removed", f"lines {start}-{end}"

    snapshots.setdefault(full_path, content)
    del lines[start - 1:end]
    # Avoid leaving a double blank line, or a blank line before `}`, where the declaration was
    if 1 < start <= len(lines) and not lines[start - 2].strip():
        following = lines[start - 1].strip() if start <= len(lines) else b""
        if not following:
            del lines[start - 1]
        elif following.startswith(b"}"):
            del lines[start - 2]
    new_content = b"\n".join(lines)
    full_path.write_bytes(new_content)

    if _only_imports_left(new_content):
        if _referenced_by_xcodeproj(project_path, full_path.name):
            return "removed", (f"lines {start}-{end}; file now empty — remove "
                               f"{full_path.name} from the Xcode project")
        full_path.unlink()
        return "removed", f"lines {start}-{end}; file deleted"
    return "removed", f"lines {start}-{end}"


def _locate_declaration(project_path: Path, full_path: Path, entity: Dict) -> Optional[Dict]:
    """Find the entity's declaration in the file as it is now (plan line numbers may be stale)."""
    candidates = [
        e for e in _extract_swift_entities_ast(full_path, project_path)
        if e["name"] == entity.get("name") and e["type"] == entity.get("type")
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda e: abs(e["line"] - entity.get("line", 0)))


def _only_imports_left(content: bytes) -> bool:
    tree = Parser(SWIFT_LANGUAGE).parse(content)
    return all(
        n.type in ("import_declaration", "comment", "multiline_comment")
        for n in tree.root_node.named_children
    )


def _referenced_by_xcodeproj(project_path: Path, file_name: str) -> bool:
    """Any Xcode project lists the file — including Pods/Pods.xcodeproj, which lists the
    sources of development pods (`pod 'X', :path => 'X'`), and the superproject's
    projects when project_path is a submodule."""
    roots = [project_path] + [r for r in _superproject_roots(project_path) if r != project_path]
    for root in roots:
        for pbxproj in root.rglob("project.pbxproj"):
            try:
                if file_name in pbxproj.read_text(errors="replace"):
                    return True
            except (IOError, OSError):
                continue
    return False


def _superproject_roots(path: Path) -> List[Path]:
    roots = []
    try:
        out = subprocess.run(["git", "rev-parse", "--show-superproject-working-tree"],
                             cwd=str(path), capture_output=True, text=True, timeout=30).stdout.strip()
        if out:
            roots.append(Path(out))
    except Exception:
        pass
    return roots


def _scan_members(decl_text: str, file_path: Path, project_path: Path,
                  type_name: str) -> List[Tuple[str, List[Tuple[str, int, str]]]]:
    """Find members declared in decl_text that are referenced outside this file.

    Returns list of (member_name, [(ref_file, ref_line, ref_text)]) for members
    that have external callers. Empty list means safe to remove.
    """
    member_names: set = set()

    # Functions/methods
    for m in re.finditer(r'\bfunc\s+([A-Za-z_]\w*)', decl_text):
        member_names.add(m.group(1))

    # Properties
    for m in re.finditer(r'\b(?:var|let)\s+([A-Za-z_]\w*)', decl_text):
        name = m.group(1)
        # Skip common Swift keywords that look like properties
        if name not in ("self", "super", "nil", "true", "false", "some", "none"):
            member_names.add(name)

    # Nested types
    for m in re.finditer(r'\b(?:class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)', decl_text):
        if m.group(1) not in ("func", "var", "let", "subscript"):
            member_names.add(m.group(1))

    member_names.discard(type_name)
    active_refs: List[Tuple[str, List[Tuple[str, int, str]]]] = []

    for name in sorted(member_names):
        # Skip very short names (likely false positives)
        if len(name) <= 2:
            continue

        try:
            result = subprocess.run(
                ["grep", "-rnw", "--include=*.swift", "--include=*.m", "--include=*.mm",
                 "--include=*.h", "--exclude-dir=Pods", "--exclude-dir=.git",
                 "--exclude-dir=DerivedData", "--exclude-dir=.arbiter",
                 name, str(project_path)],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            continue

        if result.returncode != 0:
            continue

        refs: List[Tuple[str, int, str]] = []
        for line in result.stdout.strip().split("\n"):
            # Parse grep output: file:line:text
            parts = line.split(":", 2)
            if len(parts) < 3 or Path(parts[0]).resolve() == file_path.resolve():
                continue
            try:
                refs.append((parts[0], int(parts[1]), parts[2]))
            except ValueError:
                continue

        if refs:
            active_refs.append((name, refs))

    return active_refs


def _attribute_failures(build_output: str, removed: List[Dict]) -> Dict[str, str]:
    """Map removed entity names to the first compiler error that names them."""
    removed_names = {e["name"] for e in removed}
    culprits: Dict[str, str] = {}
    for line in build_output.splitlines():
        if "error" not in line:
            continue
        for pattern in COMPILER_ERROR_PATTERNS:
            for name in pattern.findall(line):
                if name in removed_names and name not in culprits:
                    culprits[name] = line.strip()[:300]
    return culprits


def _restore(snapshots: Dict[Path, Optional[bytes]]) -> None:
    """Put back every file a batch touched (re-creating deleted files)."""
    for path, content in snapshots.items():
        path.write_bytes(content)


def _key(entity: Dict) -> str:
    return (f"{entity.get('file', '')}::{entity.get('type', '')}::"
            f"{entity.get('name', '')}::{entity.get('line', 0)}")


def _append_outcomes(project_path: Path, run_id: str, task: Dict, batch: Dict) -> None:
    """Append one line per attempted entity: what we predicted and what happened."""
    ledger = project_path / OUTCOMES_FILE
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a") as f:
        for entity in task["entities"]:
            outcome = batch["outcomes"].get(_key(entity), {})
            f.write(json.dumps({
                "runId": run_id,
                "timestamp": datetime.now().isoformat(),
                "batchId": task["taskId"],
                "predictedCategory": task["category"],
                "confidenceScore": entity.get("confidenceScore"),
                "scoringReasons": entity.get("scoringReasons", []),
                "name": entity.get("name"),
                "type": entity.get("type"),
                "file": entity.get("file"),
                "line": entity.get("line"),
                "language": entity.get("language", "swift"),
                "outcome": outcome.get("outcome", "unknown"),
                "attributed": outcome.get("attributed", False),
                "detail": outcome.get("detail", ""),
                "validationStage": batch.get("validationStage"),
                "pluginVersion": plugin_version(),
            }) + "\n")


def _git(cwd: Path, *args: str, check: bool = False, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, check=check)


def _submodule_paths(project_path: Path) -> List[Path]:
    """Initialised submodules (recursive), as absolute paths."""
    try:
        out = _git(project_path, "submodule", "foreach", "--quiet", "--recursive",
                   "echo $toplevel/$sm_path").stdout
    except Exception:
        return []
    return [Path(line.strip()) for line in out.splitlines() if line.strip()]


def _dirty_repos(project_path: Path) -> List[str]:
    """Repos (main + submodules) with uncommitted changes to tracked files.

    Untracked files and submodule pointer differences are ignored; each
    submodule's own tracked changes are checked separately.
    """
    dirty = []
    try:
        main = _git(project_path, "status", "--porcelain", "--untracked-files=no",
                    "--ignore-submodules=all", "--", ".", ":(exclude).arbiter").stdout
        if main.strip():
            dirty.append(".")
        for sub in _submodule_paths(project_path):
            if _git(sub, "status", "--porcelain", "--untracked-files=no").stdout.strip():
                dirty.append(str(sub.relative_to(project_path)))
    except Exception:
        pass
    return dirty


def _owning_repo(path: Path) -> Path:
    try:
        return Path(_git(path.parent if not path.is_dir() else path,
                         "rev-parse", "--show-toplevel").stdout.strip())
    except Exception:
        return path.parent


def _commit_batch(project_path: Path, task: Dict, batch: Dict, run_id: str) -> Dict[str, str]:
    """Commit a passing batch in every repo that owns a changed file.

    Files inside submodules are committed in the submodule (on a branch named after
    the main repo's branch if the submodule is on a detached HEAD); the main repo
    then commits the updated submodule pointers together with its own files.
    Returns {repo: short sha}.
    """
    removed_lines, other_lines = [], []
    for entity in task["entities"]:
        o = batch["outcomes"].get(_key(entity), {})
        line = f"- {entity.get('name')} ({task['taskId']}): {entity.get('file')} — {o.get('detail', '')}"
        if o.get("outcome") == "removed":
            removed_lines.append(line)
        else:
            other_lines.append(f"{line} [{o.get('outcome')}]")
    message = (
        f"arbiter: remove batch {task['taskId']} ({task['category']})\n\n"
        "Removed:\n" + "\n".join(removed_lines) +
        ("\n\nNot removed:\n" + "\n".join(other_lines) if other_lines else "") +
        f"\n\nSurviving removals: {len(removed_lines)} of {len(task['entities'])} entities"
    )

    by_repo: Dict[Path, List[Path]] = {}
    for f in (Path(p) for p in batch.get("keptFiles", [])):
        by_repo.setdefault(_owning_repo(f), []).append(f)

    main_branch = _git(project_path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    commits: Dict[str, str] = {}
    pointer_paths: List[str] = []
    for repo, files in by_repo.items():
        if repo == project_path:
            continue
        try:
            if _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "HEAD":
                _switch_to_branch(repo, main_branch, run_id)
            _git(repo, "add", "-A", "--", *[str(f.relative_to(repo)) for f in files], check=True)
            _git(repo, "commit", "-m", message, check=True)
            commits[str(repo.relative_to(project_path))] = _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
            pointer_paths.append(str(repo.relative_to(project_path)))
        except Exception as e:
            commits[str(repo.relative_to(project_path))] = f"commit failed: {e}"

    main_files = [str(f.relative_to(project_path)) for f in by_repo.get(project_path, [])]
    if main_files or pointer_paths:
        try:
            _git(project_path, "add", "-A", "--", *main_files, *pointer_paths, check=True)
            subject = message if main_files else message.replace(
                "arbiter: remove", "arbiter: update submodules for", 1)
            _git(project_path, "commit", "-m", subject, check=True)
            commits["."] = _git(project_path, "rev-parse", "--short", "HEAD").stdout.strip()
        except Exception as e:
            commits["."] = f"commit failed: {e}"
    return commits


def _switch_to_branch(repo: Path, branch: str, run_id: str) -> str:
    """Leave a detached HEAD so commits land on a branch (no file changes)."""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    existing = _git(repo, "rev-parse", "--verify", "--quiet", branch).stdout.strip()
    if not existing:
        _git(repo, "switch", "-c", branch, check=True)
        return branch
    if existing == head:
        _git(repo, "switch", branch, check=True)
        return branch
    alt = f"{branch}-arbiter-{run_id}"
    _git(repo, "switch", "-c", alt, check=True)
    return alt


def _validate_environment(project_path: Path, scheme: Optional[str], log_path: Path) -> bool:
    """Baseline: the project must build before any removal (output saved to log_path)."""
    print("[pre-check] Baseline build before any removal...", file=sys.stderr)
    passed, output = _validate_compile(project_path, scheme)
    _save_log(log_path, output)
    if passed:
        print("[pre-check] Baseline OK — project builds.", file=sys.stderr)
        return True
    print(f"[ENVIRONMENT_BLOCKED] Baseline build failed — see {log_path}", file=sys.stderr)
    print("  Fix infrastructure (pod install, Xcode version, etc.) before running arbiter-remove.",
          file=sys.stderr)
    return False


def _save_log(path: Path, output: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output or "")


def _first_error(output: str) -> str:
    for line in (output or "").splitlines():
        if "error:" in line:
            return line.strip()[:300]
    return "no compiler error line found"


SUPERFLUOUS_LINT = re.compile(
    r"^(?P<file>/[^:\n]+\.swift):(?P<line>\d+):\d+: (?:warning|error): .*?"
    r"(?:Superfluous Disable Command|superfluous_disable_command).*?'(?P<rule>[\w_]+)'", re.MULTILINE)
LINT_DISABLE = re.compile(r"//\s*swiftlint:disable(?::(?:next|this|previous))?\s+(?P<rules>[\w_ ]+)")


def _fix_superfluous_lint_disables(output: str, snapshots: Dict[Path, Optional[bytes]]) -> List[str]:
    """Drop `// swiftlint:disable <rule>` comments that a removal made superfluous.

    Only files this attempt touched are edited (they are already snapshotted, so a
    rollback restores them). Returns a description of each fix.
    """
    fixes = []
    for m in SUPERFLUOUS_LINT.finditer(output or ""):
        path = Path(m.group("file")).resolve()
        if path not in {p.resolve() for p in snapshots} or not path.exists():
            continue
        lines = path.read_text().split("\n")
        idx = int(m.group("line")) - 1
        if not 0 <= idx < len(lines):
            continue
        directive = LINT_DISABLE.search(lines[idx])
        if not directive:
            continue
        rules = [r for r in directive.group("rules").split() if r != m.group("rule")]
        if rules:
            lines[idx] = lines[idx][:directive.start("rules")] + " ".join(rules) + lines[idx][directive.end("rules"):]
        elif lines[idx][:directive.start()].strip():
            lines[idx] = lines[idx][:directive.start()].rstrip()
        else:
            del lines[idx]
        path.write_text("\n".join(lines))
        fixes.append(f"{path.name}:{idx + 1} removed superfluous swiftlint:disable {m.group('rule')}")
    return fixes


def _run_validation(project_path: Path, category: str, scheme: Optional[str]) -> Dict[str, Any]:
    """Run xcodebuild validation appropriate for the category."""
    # Always compile
    passed, output = _validate_compile(project_path, scheme)
    if not passed:
        return {"passed": False, "stage": "build", "output": output}

    # Unit tests for LIKELY/UNCERTAIN
    if category in ("LIKELY", "UNCERTAIN"):
        passed, output = _validate_tests(project_path, scheme)
        if not passed:
            return {"passed": False, "stage": "tests", "output": output}

    return {"passed": True, "stage": None, "output": ""}


def _xcode_target_args(project_path: Path) -> Optional[List[str]]:
    xcworkspaces = list(project_path.glob("*.xcworkspace"))
    xcprojects = list(project_path.glob("*.xcodeproj"))
    if xcworkspaces:
        return ["-workspace", str(xcworkspaces[0])]
    if xcprojects:
        return ["-project", str(xcprojects[0])]
    return None


def _validate_compile(project_path: Path, scheme: Optional[str]) -> Tuple[bool, str]:
    """Run xcodebuild to validate compilation. Returns (passed, build output)."""
    cmd = ["xcodebuild", "build"]

    # Detect build system
    target_args = _xcode_target_args(project_path)
    if target_args:
        cmd.extend(target_args)
    elif (project_path / "Package.swift").exists():
        # SPM project
        cmd = ["swift", "build"]

    if scheme and cmd[0] == "xcodebuild":
        cmd.extend(["-scheme", scheme])
    if cmd[0] == "xcodebuild" and BUILD_DESTINATION:
        cmd.extend(["-destination", BUILD_DESTINATION])

    try:
        result = subprocess.run(
            cmd, cwd=str(project_path),
            capture_output=True, text=True, timeout=BUILD_TIMEOUT,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def _validate_tests(project_path: Path, scheme: Optional[str]) -> Tuple[bool, str]:
    """Run unit tests to validate no regressions. Returns (passed, test output)."""
    cmd = ["xcodebuild", "test"]

    target_args = _xcode_target_args(project_path)
    if target_args:
        cmd.extend(target_args)
    elif (project_path / "Package.swift").exists():
        cmd = ["swift", "test"]

    if scheme and cmd[0] == "xcodebuild":
        cmd.extend(["-scheme", scheme])
    if cmd[0] == "xcodebuild":
        destination = TEST_DESTINATION or _default_test_destination()
        if destination:
            cmd.extend(["-destination", destination])

    try:
        result = subprocess.run(
            cmd, cwd=str(project_path),
            capture_output=True, text=True, timeout=BUILD_TIMEOUT * 2,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def _default_test_destination() -> Optional[str]:
    """First available iPhone simulator, e.g. 'platform=iOS Simulator,id=<udid>'."""
    try:
        result = subprocess.run(["xcrun", "simctl", "list", "devices", "available", "-j"],
                                capture_output=True, text=True, timeout=60)
        devices = json.loads(result.stdout).get("devices", {})
    except Exception:
        return None
    for runtime in sorted(devices, reverse=True):  # newest iOS runtime first
        if "iOS" not in runtime:
            continue
        for device in devices[runtime]:
            if device.get("name", "").startswith("iPhone"):
                return f"platform=iOS Simulator,id={device['udid']}"
    return None


def _create_backup(project_path: Path) -> Optional[str]:
    """Create a git backup branch in the main repo and every submodule before removal."""
    try:
        branch_name = f"arbiter-backup-ios-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        _git(project_path, "branch", branch_name, timeout=30)
        for sub in _submodule_paths(project_path):
            _git(sub, "branch", branch_name, timeout=30)
        return branch_name
    except Exception:
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 ios_removal_executor.py <PLAN.json> <project_path> "
              "[--scheme X] [--batch N | --task ID] [--dry-run] [--no-commit] [--stop-on-failure] "
              "[--destination D] [--test-destination D] [--build-timeout SECONDS] "
              "[--max-builds-per-batch N] [--allow-unstamped]")
        sys.exit(1)
    if sys.version_info < (3, 10):
        sys.exit("❌ Python 3.10+ required — use the interpreter printed by resolve_env.py")

    plan_path = sys.argv[1]
    project_path = sys.argv[2]
    scheme = None
    target_task = None
    max_batches = None

    def opt(flag: str) -> Optional[str]:
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv[:-1] else None

    scheme = opt("--scheme")
    if opt("--task"):
        target_task = int(opt("--task"))
    if opt("--batch"):
        max_batches = int(opt("--batch"))
    if opt("--destination"):
        BUILD_DESTINATION = opt("--destination")
    if opt("--test-destination"):
        TEST_DESTINATION = opt("--test-destination")
    if opt("--build-timeout"):
        BUILD_TIMEOUT = int(opt("--build-timeout"))
    if opt("--max-builds-per-batch"):
        MAX_BUILDS_PER_BATCH = int(opt("--max-builds-per-batch"))

    result = execute_ios_removal(plan_path, project_path, scheme=scheme,
                                 target_task=target_task, dry_run="--dry-run" in sys.argv,
                                 commit="--no-commit" not in sys.argv,
                                 max_batches=max_batches,
                                 stop_on_failure="--stop-on-failure" in sys.argv,
                                 allow_unstamped="--allow-unstamped" in sys.argv)
    print(json.dumps(result, indent=2))
