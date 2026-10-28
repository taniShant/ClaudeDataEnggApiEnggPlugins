#!/usr/bin/env python3
"""CLI entry point for iOS entity discovery.

Orchestrates: project detection → call graph → resource scan → dispatch scan → confidence scoring.
Writes all artifacts to .arbiter/swift/.
"""

import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ios.ios_detector import iOSDetector
from ios.ios_call_graph_analyzer import build_ios_call_graph
from ios.ios_resource_scanner import scan_all_resources
from ios.ios_dynamic_dispatch_scanner import scan_dynamic_dispatch
from ios.ios_confidence_engine import IOSConfidenceEngine


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 discover-ios.py <project_path> [--quick] [--verbose]")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()
    quick = "--quick" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if not project_path.exists():
        print(f"❌ Path not found: {project_path}")
        sys.exit(1)

    print("🔍 ARBITER iOS — Discovery & Analysis")
    print("━" * 50)
    print(f"   Project: {project_path}")
    print()

    # Step 1: Detect project
    print("  [1/5] Detecting iOS project...")
    detector = iOSDetector(str(project_path))
    metadata = detector.run_detection()

    if not metadata.is_ios_project:
        print("❌ Not an iOS project (no Swift/ObjC files or no build system)")
        sys.exit(1)

    print(f"        Swift files: {metadata.swift_file_count}")
    print(f"        ObjC files: {metadata.objc_file_count}")
    print(f"        Build system: {metadata.build_system}")
    print()

    # Create output directory
    arbiter_dir = project_path / ".arbiter" / "swift"
    arbiter_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Build call graph
    print("  [2/5] Building call graph...")
    call_graph = build_ios_call_graph(str(project_path), verbose=verbose)
    entities_path = arbiter_dir / "ENTITIES.json"
    with open(entities_path, "w") as f:
        json.dump(call_graph, f, indent=2)
    print(f"        Entities found: {call_graph['stats']['total_entities']}")
    print(f"        Usage edges: {call_graph['stats']['usage_edges']}")
    print()

    # Step 3: Scan resources
    print("  [3/5] Scanning storyboards, XIBs, plists...")
    resource_refs = scan_all_resources(str(project_path))
    resources_path = arbiter_dir / "RESOURCE_REFS.json"
    with open(resources_path, "w") as f:
        json.dump(resource_refs, f, indent=2)
    print(f"        Storyboard/XIB refs: {resource_refs['summary']['storyboard_xib_refs']}")
    print(f"        Plist refs: {resource_refs['summary']['plist_refs']}")
    print()

    # Step 4: Scan dynamic dispatch
    print("  [4/5] Scanning dynamic dispatch patterns...")
    dispatch_results = scan_dynamic_dispatch(str(project_path))
    dispatch_path = arbiter_dir / "DISPATCH_SCAN.json"
    with open(dispatch_path, "w") as f:
        json.dump(dispatch_results, f, indent=2)
    print(f"        Dynamic refs found: {dispatch_results['summary']['total_dynamic_refs']}")
    print()

    # Step 5: Score confidence
    print("  [5/5] Scoring confidence (arbiter 0-4 scale)...")
    engine = IOSConfidenceEngine(
        entities_path=str(entities_path),
        usage_path=str(entities_path),  # Usage is in entities file
        resource_refs_path=str(resources_path),
        dispatch_path=str(dispatch_path),
    )
    confidence = engine.score_all()
    confidence_path = arbiter_dir / "CONFIDENCE.json"
    with open(confidence_path, "w") as f:
        json.dump(confidence, f, indent=2)

    summary = confidence["summary"]
    print(f"        SAFE (3.0-4.0):      {summary['safe_count']}")
    print(f"        LIKELY (2.0-2.9):    {summary['likely_count']}")
    print(f"        UNCERTAIN (1.0-1.9): {summary['uncertain_count']}")
    print(f"        KEEP (<1.0):         {summary['keep_count']}")
    print()

    # Summary
    print("━" * 50)
    print("✅ Discovery & Analysis complete")
    print(f"   Artifacts: {arbiter_dir}/")
    print(f"   Next step: /arbiter-plan-ios")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
