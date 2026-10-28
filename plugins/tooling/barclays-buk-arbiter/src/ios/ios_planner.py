#!/usr/bin/env python3
"""iOS Removal Planner — deterministic batching for iOS dead code removal.

Follows the same pattern as the Java planner but with iOS-specific batch sizes
and time estimates (compile time dominates in iOS).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


# iOS-specific batch sizes (larger than Java — iOS entities are more granular)
BATCH_SIZES = {
    "SAFE": 10,
    "LIKELY": 5,
    "UNCERTAIN": 1,
    "KEEP": 0,
}

# Validation tier per confidence category
VALIDATION_TIERS = {
    "SAFE": "compile",
    "LIKELY": "unit",
    "UNCERTAIN": "integration",
}

# Time estimates per batch (iOS xcodebuild dominates)
TIME_ESTIMATES_MINUTES = {
    "SAFE": 2,
    "LIKELY": 5,
    "UNCERTAIN": 10,
}


class IOSRemovalPlanner:
    """Plans iOS dead code removal in deterministic batches."""

    def __init__(self, confidence_data: Dict[str, Any]):
        self.confidence_data = confidence_data
        self.entities = confidence_data.get("entities", [])

    def plan(self, sprints: int = 2, scope: str = "all") -> Dict[str, Any]:
        """Generate batched removal plan.

        Args:
            sprints: Number of sprints to allocate
            scope: "all" or comma-separated categories (e.g., "SAFE,LIKELY")

        Returns:
            Plan dict with tasks, breakdown, and estimates
        """
        scoped_categories = self._filter_scope(scope)

        # Group entities by category. Objective-C candidates are listed for review
        # only — the executor has no syntax-aware ObjC removal yet.
        categories = {"SAFE": [], "LIKELY": [], "UNCERTAIN": [], "KEEP": []}
        review_only: Dict[str, List[Dict[str, Any]]] = {"SAFE": [], "LIKELY": [], "UNCERTAIN": []}
        for entity in self.entities:
            cat = entity.get("category", "KEEP")
            if entity.get("language") == "objc" and cat in review_only:
                if cat in scoped_categories:
                    review_only[cat].append(entity)
            elif cat in categories:
                categories[cat].append(entity)

        # Create batches
        tasks = []
        task_id = 1

        for category in ["SAFE", "LIKELY", "UNCERTAIN"]:
            if category not in scoped_categories:
                continue

            batch_size = BATCH_SIZES[category]
            group = categories[category]
            if not group or batch_size == 0:
                continue

            # Sort by confidence (highest first = safest first)
            group.sort(key=lambda e: e.get("confidenceScore", 0), reverse=True)

            for i in range(0, len(group), batch_size):
                batch = group[i:i + batch_size]
                tasks.append({
                    "taskId": task_id,
                    "category": category,
                    "validationTier": VALIDATION_TIERS[category],
                    "batchSize": len(batch),
                    "entities": [
                        {
                            "fullyQualifiedName": e.get("fullyQualifiedName", e.get("name", "")),
                            "name": e.get("name", ""),
                            "type": e.get("type", ""),
                            "file": e.get("file", ""),
                            "line": e.get("line", 0),
                            "confidenceScore": e.get("confidenceScore", 0),
                            "scoringReasons": e.get("scoringReasons") or e.get("deductionReasons", []),
                            "language": e.get("language", "swift"),
                            "owner": e.get("owner"),
                        }
                        for e in batch
                    ],
                    "status": "pending",
                })
                task_id += 1

        # Calculate breakdowns
        category_breakdown = {cat: len(ents) for cat, ents in categories.items()}
        task_breakdown = {}
        for task in tasks:
            cat = task["category"]
            task_breakdown[cat] = task_breakdown.get(cat, 0) + 1

        total_removable = sum(len(categories[c]) for c in ["SAFE", "LIKELY", "UNCERTAIN"])
        est_minutes = sum(
            task_breakdown.get(cat, 0) * mins
            for cat, mins in TIME_ESTIMATES_MINUTES.items()
        )

        # Sprint allocation (greedy bin-packing)
        sprint_allocation = self._allocate_sprints(tasks, sprints)

        return {
            "timestamp": datetime.now().isoformat(),
            "tasks": tasks,
            "categoryBreakdown": category_breakdown,
            "taskBreakdown": task_breakdown,
            "totalRemovable": total_removable,
            "totalBatches": len(tasks),
            "totalKeep": len(categories["KEEP"]),
            "estimatedTime": f"{est_minutes} minutes",
            "sprintAllocation": sprint_allocation,
            "reviewOnly": {
                "reason": "Objective-C removal is not automated yet — review these candidates",
                "counts": {cat: len(ents) for cat, ents in review_only.items()},
                "entities": [
                    {
                        "fullyQualifiedName": e.get("fullyQualifiedName", e.get("name", "")),
                        "type": e.get("type", ""),
                        "category": cat,
                        "confidenceScore": e.get("confidenceScore", 0),
                        "scoringReasons": e.get("scoringReasons") or e.get("deductionReasons", []),
                        "declarations": e.get("declarations", []),
                    }
                    for cat, ents in review_only.items()
                    for e in sorted(ents, key=lambda e: -e.get("confidenceScore", 0))
                ],
            },
        }

    def _filter_scope(self, scope: str) -> set:
        if scope == "all":
            return {"SAFE", "LIKELY", "UNCERTAIN"}
        return {s.strip().upper() for s in scope.split(",") if s.strip().upper() in BATCH_SIZES}

    def _allocate_sprints(self, tasks: List[Dict], sprints: int) -> Dict[str, List[int]]:
        """Allocate tasks to sprints using greedy bin-packing."""
        if not tasks or sprints <= 0:
            return {}

        sprint_loads = [0.0] * sprints
        allocation = {f"sprint_{i+1}": [] for i in range(sprints)}

        for task in tasks:
            cat = task["category"]
            effort = TIME_ESTIMATES_MINUTES.get(cat, 5)
            min_idx = min(range(sprints), key=lambda i: sprint_loads[i])
            allocation[f"sprint_{min_idx + 1}"].append(task["taskId"])
            sprint_loads[min_idx] += effort

        return allocation


def plan_ios_removals(confidence_data: Dict[str, Any],
                      sprints: int = 2, scope: str = "all") -> Dict[str, Any]:
    """Convenience function to plan iOS removals."""
    planner = IOSRemovalPlanner(confidence_data)
    return planner.plan(sprints=sprints, scope=scope)


try:
    from .arbiter_meta import require_stamp, stamp, write_json
except ImportError:
    from arbiter_meta import require_stamp, stamp, write_json


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_planner.py <CONFIDENCE.json> [--sprints N] [--scope SAFE,LIKELY] "
              "[--output PLAN.json] [--allow-unstamped]")
        sys.exit(1)

    confidence_path = sys.argv[1]
    sprints = 2
    scope = "all"

    for i, arg in enumerate(sys.argv):
        if arg == "--sprints" and i + 1 < len(sys.argv):
            sprints = int(sys.argv[i + 1])
        elif arg == "--scope" and i + 1 < len(sys.argv):
            scope = sys.argv[i + 1]

    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    with open(confidence_path) as f:
        confidence_data = json.load(f)
    require_stamp(confidence_data, "CONFIDENCE.json", "--allow-unstamped" in sys.argv)

    plan = plan_ios_removals(confidence_data, sprints=sprints, scope=scope)
    plan["generatedBy"] = stamp(["ios_planner.py"])
    plan["analysisGeneratedBy"] = confidence_data.get("generatedBy")

    print(f"📋 iOS Removal Plan")
    print(f"   Total removable: {plan['totalRemovable']}")
    print(f"   Total batches: {plan['totalBatches']}")
    print(f"   Estimated time: {plan['estimatedTime']}")

    for cat in ["SAFE", "LIKELY", "UNCERTAIN"]:
        count = plan["categoryBreakdown"].get(cat, 0)
        batches = plan["taskBreakdown"].get(cat, 0)
        if count > 0:
            print(f"   {cat}: {count} entities → {batches} batches")

    if output_path:
        write_json(output_path, plan)
        print(f"   Output: {output_path}")
    else:
        print(json.dumps(plan, indent=2))
