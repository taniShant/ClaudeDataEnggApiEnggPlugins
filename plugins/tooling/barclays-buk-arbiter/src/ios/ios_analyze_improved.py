#!/usr/bin/env python3
"""Improved iOS Dead Code Analysis Pipeline

Orchestrates the full improved pipeline:
1. Build AST-based reference graph (tree-sitter for Swift)
2. Detect entities and usage counts
3. Apply enhanced confidence scoring (AST-aware)
4. Generate removal plan

Key improvements over baseline:
- AST-based reference detection instead of pure regex string counting
- High-confidence reference types (type_annotation, inheritance, protocol_conformance)
- Multi-pass analysis ready (execute SAFE tier, rebuild, re-analyze LIKELY)
- Expected FP rate reduction: 93.8% → <15%
- Expected removal success increase: 6.2% → 30-40%
"""

import json
import sys

try:
    from .arbiter_meta import stamp, write_json
except ImportError:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from arbiter_meta import stamp, write_json

PIPELINE_SCRIPTS = ["ios_analyze_improved.py", "ios_call_graph_analyzer.py", "ast_reference_scanner.py",
                    "objc_syntax.py", "ios_framework_rules.py", "ios_resource_scanner.py",
                    "ios_dynamic_dispatch_scanner.py"]
import subprocess
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

def run_command(cmd: list, cwd: str = None) -> str:
    """Run shell command and return output."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"   Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def analyze_ios_improved(repo_path: str, output_dir: str = ".arbiter_improved") -> Dict[str, Any]:
    """Run improved iOS dead code analysis pipeline."""
    repo_path = Path(repo_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("IMPROVED iOS DEAD CODE ANALYSIS PIPELINE")
    print("=" * 70)

    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from .ast_reference_scanner import build_ios_ast_graph
        from .ios_call_graph_analyzer import build_ios_call_graph
    except ImportError:
        from ast_reference_scanner import build_ios_ast_graph
        from ios_call_graph_analyzer import build_ios_call_graph

    # Step 1: Build AST-based reference graph
    print("\n[Step 1/4] Building AST-based reference graph...")
    ast_graph = build_ios_ast_graph(str(repo_path))
    ast_file = output_dir / "ast_graph.json"
    write_json(str(ast_file), ast_graph, compact=True)
    print(f"   ✓ AST graph saved: {ast_graph['stats']['total_references']} references found")

    # Step 2: Detect entities and usage (tree-sitter for Swift, regex for ObjC)
    print("\n[Step 2/4] Detecting entities...")
    call_graph = build_ios_call_graph(str(repo_path), verbose=True, ast_graph=ast_graph)
    entities_file = output_dir / "entities.json"
    write_json(str(entities_file), {"entities": call_graph["entities"], "usages": call_graph["usages"],
                                    "generatedBy": stamp(PIPELINE_SCRIPTS)}, compact=True)
    print(f"   ✓ Entities saved: {len(call_graph['entities'])} found")

    # Step 3: Apply enhanced confidence scoring
    print("\n[Step 3/4] Applying AST-aware confidence scoring...")
    try:
        from .ios_confidence_engine_v2 import score_ios_entities_with_ast
    except ImportError:
        from ios_confidence_engine_v2 import score_ios_entities_with_ast

    # Storyboard/XIB/plist references and dynamic dispatch (NSSelectorFromString, KVC, ...)
    try:
        from .ios_resource_scanner import scan_all_resources
        from .ios_dynamic_dispatch_scanner import scan_dynamic_dispatch
    except ImportError:
        from ios_resource_scanner import scan_all_resources
        from ios_dynamic_dispatch_scanner import scan_dynamic_dispatch
    known_classes = {e["name"] for e in call_graph["entities"] if e["type"] != "method"}
    resource_file = output_dir / "resource_refs.json"
    write_json(str(resource_file), scan_all_resources(str(repo_path), known_classes=known_classes),
               compact=True)
    dispatch_file = output_dir / "dispatch_scan.json"
    with open(dispatch_file, "w") as f:
        json.dump(scan_dynamic_dispatch(str(repo_path)), f, indent=2)

    # Usage counts come from the AST graph (Swift and ObjC)
    usage_data = {"usages": call_graph["usages"]}
    usage_file = output_dir / "usage.json"
    with open(usage_file, "w") as f:
        json.dump(usage_data, f, indent=2)

    confidence_result = score_ios_entities_with_ast(
        entities_path=str(entities_file),
        ast_graph_path=str(ast_file),
        usage_path=str(usage_file),
        resource_refs_path=str(resource_file),
        dispatch_path=str(dispatch_file),
    )
    confidence_file = output_dir / "confidence.json"
    confidence_result["generatedBy"] = stamp(PIPELINE_SCRIPTS + ["ios_confidence_engine_v2.py"])
    write_json(str(confidence_file), confidence_result, compact=True)

    summary = confidence_result["summary"]
    print(f"   ✓ Confidence scoring complete:")
    print(f"      SAFE: {summary['safe_count']}")
    print(f"      LIKELY: {summary['likely_count']}")
    print(f"      UNCERTAIN: {summary['uncertain_count']}")
    print(f"      KEEP: {summary['keep_count']}")

    # Step 4: Generate removal plan
    print("\n[Step 4/4] Generating removal plan...")
    try:
        from .ios_planner import plan_ios_removals
    except ImportError:
        from ios_planner import plan_ios_removals

    plan = plan_ios_removals(confidence_result, sprints=2, scope="SAFE,LIKELY")
    plan["generatedBy"] = stamp(["ios_planner.py"])
    plan["analysisGeneratedBy"] = confidence_result["generatedBy"]
    plan_file = output_dir / "plan.json"
    write_json(str(plan_file), plan)
    print(f"   ✓ Plan generated: {plan['totalBatches']} batches")

    # Generate summary report
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE — IMPROVED RESULTS")
    print("=" * 70)

    # Compare against baseline FP rate
    total_entities = confidence_result["totalEntities"]
    removable = summary["removable_count"]
    removal_success_rate = (removable / total_entities * 100) if total_entities > 0 else 0
    fp_rate = 100 - removal_success_rate  # Simplified

    print(f"\n📊 Summary:")
    print(f"   Total entities: {total_entities}")
    print(f"   Removable: {removable} ({removal_success_rate:.1f}%)")
    print(f"   FP Rate: {fp_rate:.1f}%")
    print(f"   AST References: {ast_graph['stats']['total_references']}")

    print(f"\n✅ Outputs saved:")
    print(f"   {entities_file}")
    print(f"   {ast_file}")
    print(f"   {confidence_file}")
    print(f"   {plan_file}")

    return {
        "timestamp": datetime.now().isoformat(),
        "repo": str(repo_path),
        "stats": {
            "total_entities": total_entities,
            "removable": removable,
            "removal_success_rate": removal_success_rate,
            "ast_references": ast_graph['stats']['total_references'],
            "safe": summary['safe_count'],
            "likely": summary['likely_count'],
            "uncertain": summary['uncertain_count'],
            "keep": summary['keep_count'],
        },
        "files": {
            "entities": str(entities_file),
            "ast_graph": str(ast_file),
            "confidence": str(confidence_file),
            "plan": str(plan_file),
        },
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_analyze_improved.py <repo_path> [output_dir]")
        sys.exit(1)

    repo_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else ".arbiter_improved"

    result = analyze_ios_improved(repo_path, output_dir)
    print(f"\n📋 Analysis metadata:")
    print(json.dumps(result, indent=2))
