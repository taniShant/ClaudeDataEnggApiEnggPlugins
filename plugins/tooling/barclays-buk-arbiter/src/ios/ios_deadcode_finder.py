#!/usr/bin/env python3
"""iOS Dead Code Finder — identifies unreachable entities from call graph + resources + dispatch.

Combines call graph analysis, resource references, and dynamic dispatch data
to identify entities that are genuinely unreachable.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set


def find_ios_dead_code_candidates(
    call_graph: Dict[str, Any],
    resource_refs: Dict[str, Any] = None,
    dispatch_scan: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Identify dead code candidates from analysis data.

    Args:
        call_graph: Output from ios_call_graph_analyzer.build_ios_call_graph()
        resource_refs: Output from ios_resource_scanner.scan_all_resources()
        dispatch_scan: Output from ios_dynamic_dispatch_scanner.scan_dynamic_dispatch()

    Returns:
        Candidates dict with entities grouped by reachability status
    """
    entities = call_graph.get("entities", [])
    usages = call_graph.get("usages", [])
    entry_points = call_graph.get("entryPoints", [])

    # Build sets of referenced names
    used_names = _build_used_names(usages)
    resource_names = _build_resource_names(resource_refs or {})
    dispatch_names = _build_dispatch_names(dispatch_scan or {})
    entry_point_names = {ep["name"] for ep in entry_points}

    # Classify entities
    unreachable = []
    reachable = []
    test_only = []

    for entity in entities:
        name = entity.get("name", "")
        fqn = entity.get("fullyQualifiedName", name)

        # Skip test code
        if entity.get("isTestCode", False):
            test_only.append(entity)
            continue

        # Check all reference sources
        is_used = (
            fqn in used_names or
            name in used_names or
            name in resource_names or
            name in dispatch_names or
            name in entry_point_names
        )

        if is_used:
            reachable.append(entity)
        else:
            unreachable.append(entity)

    return {
        "candidates": unreachable,
        "reachable": reachable,
        "testOnly": test_only,
        "summary": {
            "total_entities": len(entities),
            "unreachable_count": len(unreachable),
            "reachable_count": len(reachable),
            "test_only_count": len(test_only),
            "dead_code_percentage": round(
                len(unreachable) / max(len(entities), 1) * 100, 1
            ),
        },
    }


def _build_used_names(usages: List[Dict]) -> Set[str]:
    """Extract names that have usage references."""
    used = set()
    for usage in usages:
        fqn = usage.get("fullyQualifiedName", "")
        if usage.get("usageCount", 0) > 0:
            used.add(fqn)
    return used


def _build_resource_names(resource_refs: Dict) -> Set[str]:
    """Extract class names from resource references."""
    names = set()
    for ref in resource_refs.get("references", []):
        cn = ref.get("className")
        if cn:
            names.add(cn)
    return names


def _build_dispatch_names(dispatch_scan: Dict) -> Set[str]:
    """Extract protected names from dynamic dispatch scan."""
    names = set()
    for ref in dispatch_scan.get("nsselector_refs", []):
        names.add(ref.get("selectorName", "").rstrip(":"))
    for ref in dispatch_scan.get("nsclass_refs", []):
        names.add(ref.get("className", ""))
    for ref in dispatch_scan.get("data_driven_selectors", []):
        names.add(ref.get("selectorName", "").rstrip(":"))
    for ref in dispatch_scan.get("perform_selector_refs", []):
        names.add(ref.get("selectorName", "").rstrip(":"))
    for ref in dispatch_scan.get("kvc_refs", []):
        names.add(ref.get("propertyName", ""))
    return names


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_deadcode_finder.py <call_graph.json> [resource_refs.json] [dispatch.json]")
        sys.exit(1)

    call_graph_path = sys.argv[1]
    resource_path = sys.argv[2] if len(sys.argv) > 2 else None
    dispatch_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(call_graph_path) as f:
        call_graph = json.load(f)

    resource_refs = None
    if resource_path:
        with open(resource_path) as f:
            resource_refs = json.load(f)

    dispatch_scan = None
    if dispatch_path:
        with open(dispatch_path) as f:
            dispatch_scan = json.load(f)

    results = find_ios_dead_code_candidates(call_graph, resource_refs, dispatch_scan)
    summary = results["summary"]

    print(f"🔍 Dead code analysis complete")
    print(f"   Total entities: {summary['total_entities']}")
    print(f"   Unreachable:    {summary['unreachable_count']} ({summary['dead_code_percentage']}%)")
    print(f"   Reachable:      {summary['reachable_count']}")
    print(f"   Test-only:      {summary['test_only_count']}")

    print(json.dumps(results, indent=2))
