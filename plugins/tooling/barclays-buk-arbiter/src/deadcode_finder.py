#!/usr/bin/env python3
"""Dead code candidate finder. Identifies unreachable entities from call graph."""

from typing import Dict, List, Any, Set
import json

def find_dead_code_candidates(call_graph: Dict) -> Dict[str, Any]:
    """
    Find unreachable entities in call graph.

    A dead code candidate is an entity (method, class, field) that:
    - Is not reachable from any entry point
    - Has zero incoming edges in the call graph
    - Is not explicitly marked as KEEP

    Args:
        call_graph: Call graph from analyzer with nodes, edges, entry_points, reachable

    Returns:
        Dictionary categorizing candidates by confidence tier
    """
    # Extract entry points and reachable entities
    entry_points = set(call_graph.get("entry_points", []))
    reachable = set(call_graph.get("reachable_entities", []))
    all_nodes = {node["name"] for node in call_graph.get("nodes", [])}

    # Unreachable entities are candidates
    unreachable = all_nodes - reachable

    # Apply confidence scoring
    candidates = {
        "SAFE": [],        # 3.0-4.0: private, no annotations
        "LIKELY": [],      # 2.0-2.9: may have indirect usage
        "UNCERTAIN": [],   # 1.0-1.9: ambiguous, needs review
        "KEEP": [],        # <1.0: too risky
    }

    confidence_scores = call_graph.get("confidence_scores", {})

    for entity in unreachable:
        score = confidence_scores.get(entity, 2.5)

        if score >= 3.0:
            candidates["SAFE"].append(entity)
        elif score >= 2.0:
            candidates["LIKELY"].append(entity)
        elif score >= 1.0:
            candidates["UNCERTAIN"].append(entity)
        else:
            candidates["KEEP"].append(entity)

    return {
        "candidates": candidates,
        "total_unreachable": len(unreachable),
        "total_safe": len(candidates["SAFE"]),
        "total_likely": len(candidates["LIKELY"]),
        "total_uncertain": len(candidates["UNCERTAIN"]),
        "total_keep": len(candidates["KEEP"]),
        "confidence_scores": confidence_scores,
    }

def categorize_by_confidence(candidates: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Categorize candidates and estimate effort.

    Returns:
        Dictionary with effort estimates per category
    """
    return {
        "SAFE": {
            "count": len(candidates.get("SAFE", [])),
            "batch_size": 5,
            "effort_per_task_hours": 0.75,
            "risk": "low",
            "validation": "compile + unit tests",
        },
        "LIKELY": {
            "count": len(candidates.get("LIKELY", [])),
            "batch_size": 3,
            "effort_per_task_hours": 1.5,
            "risk": "medium",
            "validation": "compile + unit + integration tests",
        },
        "UNCERTAIN": {
            "count": len(candidates.get("UNCERTAIN", [])),
            "batch_size": 1,
            "effort_per_task_hours": 3.0,
            "risk": "high",
            "validation": "compile + full test suite + manual review",
        },
        "KEEP": {
            "count": len(candidates.get("KEEP", [])),
            "batch_size": 0,
            "effort_per_task_hours": 0,
            "risk": "critical",
            "validation": "do not remove",
        },
    }
