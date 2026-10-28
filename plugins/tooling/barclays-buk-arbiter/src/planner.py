#!/usr/bin/env python3
"""Deterministic removal planning for dead code analysis.

Converts analysis output (candidates, confidence scores) into batched removal tasks
with effort estimation and sprint allocation. All logic is deterministic (no LLM reasoning).
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import math
import yaml


class RemovalPlanner:
    """Plans removal tasks from dead code analysis results."""

    # Batch sizes by confidence category
    BATCH_SIZES = {
        "SAFE": 5,
        "LIKELY": 3,
        "UNCERTAIN": 1,
    }

    # Effort estimates (hours per task) by confidence category
    EFFORT_HOURS = {
        "SAFE": (0.5, 1.0),      # 0.5-1h per task
        "LIKELY": (1.0, 2.0),    # 1-2h per task
        "UNCERTAIN": (2.0, 4.0), # 2-4h per task
    }

    def __init__(self, analysis_output: Dict[str, Any]):
        """Initialize planner with analysis results.

        Args:
            analysis_output: From arbiter-analyze agent (candidates, confidence_scores, categories)
        """
        self.analysis = analysis_output
        self.candidates = analysis_output.get("candidates", [])
        self.categories = analysis_output.get("categories", {})
        self.confidence_scores = analysis_output.get("confidence_scores", {})
        self.tasks: List[Dict[str, Any]] = []
        self.task_counter = 0

    def plan(self, sprints: int = 2, scope: str = "all") -> Dict[str, Any]:
        """Generate removal plan.

        Args:
            sprints: Number of sprints to allocate work
            scope: "all" or comma-separated categories (e.g., "SAFE,LIKELY")

        Returns:
            Removal plan dict (YAML-serializable)
        """
        # Filter by scope
        scoped_categories = self._filter_scope(scope)

        # Batch by category
        self.tasks = []
        self.task_counter = 0

        for category in ["SAFE", "LIKELY", "UNCERTAIN"]:
            if category not in scoped_categories:
                continue

            entities = self.categories.get(category, [])
            if not entities:
                continue

            batch_size = self.BATCH_SIZES[category]
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i+batch_size]
                self._create_task(category, batch)

        # Allocate to sprints
        sprint_allocation = self._allocate_sprints(sprints)

        # Calculate total effort
        total_effort = sum(task.get("estimated_effort_hours", 1.0) for task in self.tasks)

        # Build plan dict
        plan = {
            "workflow_id": f"plan-{datetime.now().isoformat()}",
            "total_effort_hours": round(total_effort, 1),
            "task_count": len(self.tasks),
            "categories": {
                cat: len(self.categories.get(cat, []))
                for cat in ["SAFE", "LIKELY", "UNCERTAIN"]
            },
            "tasks": self.tasks,
            "sprint_allocation": sprint_allocation,
        }

        return plan

    def _filter_scope(self, scope: str) -> set:
        """Parse scope filter string."""
        if scope == "all":
            return {"SAFE", "LIKELY", "UNCERTAIN"}

        categories = set()
        for cat in scope.split(","):
            cat = cat.strip().upper()
            if cat in ["SAFE", "LIKELY", "UNCERTAIN"]:
                categories.add(cat)

        return categories or {"SAFE", "LIKELY", "UNCERTAIN"}

    def _create_task(self, category: str, entities: List[str]) -> None:
        """Create a removal task for a batch of entities.

        Args:
            category: Confidence category (SAFE, LIKELY, UNCERTAIN)
            entities: List of entity names to remove (must not be empty)

        Raises:
            ValueError: If entities list is empty
        """
        if not entities:
            raise ValueError(
                f"Cannot create removal task for {category}: empty entity list. "
                "Empty batches should not reach _create_task(). "
                "This indicates a bug in the batching logic."
            )

        self.task_counter += 1
        task_id = f"T{self.task_counter:03d}"

        # Calculate average confidence for this batch
        confidences = [
            self.confidence_scores.get(entity, 2.0)
            for entity in entities
        ]
        confidence_avg = sum(confidences) / len(confidences) if confidences else 2.0

        # Estimate effort (use midpoint of range)
        effort_range = self.EFFORT_HOURS.get(category, (1.0, 2.0))
        # EFFORT_HOURS is per-task (entire batch), not per-entity.
        # Ranges already account for batch review overhead.
        # SAFE (0.5-1h): Single task removing up to 5 entities
        # LIKELY (1-2h): Single task removing up to 3 entities
        # UNCERTAIN (2-4h): Single task removing 1 entity
        # No additional batch_size_factor multiplier needed - would cause double-counting.
        estimated_effort = (effort_range[0] + effort_range[1]) / 2

        # Define validation gates
        rollback_gates = ["compile-check", "unit-test-check"]
        if category in ["LIKELY", "UNCERTAIN"]:
            rollback_gates.append("integration-test-check")

        task = {
            "task_id": task_id,
            "category": category,
            "entities": entities,
            "confidence_avg": round(confidence_avg, 2),
            "estimated_effort_hours": round(estimated_effort, 1),
            "rollback_gates": rollback_gates,
            "dependencies": [],
            "sprint_assignment": None,  # Set during sprint allocation
        }

        self.tasks.append(task)

    def _allocate_sprints(self, sprints: int) -> Dict[str, List[str]]:
        """Allocate tasks to sprints based on effort estimation.

        Uses greedy algorithm to distribute effort evenly across sprints.
        """
        if not self.tasks or sprints <= 0:
            return {}

        # Initialize sprint buckets
        sprint_efforts = [0.0] * sprints
        sprint_tasks = {f"sprint_{i+1}": [] for i in range(sprints)}

        # Sort tasks by effort (descending) for better packing
        sorted_tasks = sorted(self.tasks, key=lambda t: t.get("estimated_effort_hours", 1.0), reverse=True)

        # Greedy bin packing: assign each task to least-loaded sprint
        for task in sorted_tasks:
            effort = task.get("estimated_effort_hours", 1.0)

            # Find sprint with lowest current effort
            min_sprint_idx = min(range(sprints), key=lambda i: sprint_efforts[i])
            min_sprint_name = f"sprint_{min_sprint_idx + 1}"

            sprint_tasks[min_sprint_name].append(task["task_id"])
            sprint_efforts[min_sprint_idx] += effort
            task["sprint_assignment"] = min_sprint_idx + 1

        return sprint_tasks

    def to_yaml(self, plan_dict: Dict[str, Any] = None) -> str:
        """Convert plan to YAML format using PyYAML for safe escaping.

        Args:
            plan_dict: Optional plan dict. If None, generates plan from current state.

        Returns:
            YAML string with all special characters properly escaped.
        """
        if plan_dict is None:
            # If no plan provided, we need tasks to be set
            # If plan() hasn't been called, this will fail - that's expected
            if not self.tasks:
                return ""
            plan_dict = {
                "workflow_id": f"plan-{datetime.now().isoformat()}",
                "total_effort_hours": round(sum(task.get("estimated_effort_hours", 1.0) for task in self.tasks), 1),
                "task_count": len(self.tasks),
                "categories": {
                    cat: len(self.categories.get(cat, []))
                    for cat in ["SAFE", "LIKELY", "UNCERTAIN"]
                },
                "tasks": self.tasks,
                "sprint_allocation": self._allocate_sprints(2),
            }

        # Use yaml.dump() for safe handling of special characters (: # | > quotes, etc.)
        # sort_keys=False preserves the order of keys
        # default_flow_style=False uses block style (more readable)
        return yaml.dump(plan_dict, default_flow_style=False, sort_keys=False)


def plan_removals(analysis_output: Dict[str, Any], sprints: int = 2, scope: str = "all") -> Dict[str, Any]:
    """Convenience function to plan removals in one call.

    Args:
        analysis_output: From arbiter-analyze agent
        sprints: Number of sprints
        scope: Category filter

    Returns:
        Removal plan dict
    """
    planner = RemovalPlanner(analysis_output)
    return planner.plan(sprints=sprints, scope=scope)


if __name__ == "__main__":
    # Example usage for testing
    sample_analysis = {
        "candidates": [
            "com.example.LegacyClass",
            "com.example.OldMethod",
            "com.example.DeprecatedUtil",
        ],
        "confidence_scores": {
            "com.example.LegacyClass": 3.8,
            "com.example.OldMethod": 2.5,
            "com.example.DeprecatedUtil": 1.2,
        },
        "categories": {
            "SAFE": ["com.example.LegacyClass", "com.example.AnotherSafe"],
            "LIKELY": ["com.example.OldMethod"],
            "UNCERTAIN": ["com.example.DeprecatedUtil"],
        },
    }

    plan = plan_removals(sample_analysis, sprints=2)
    print(json.dumps(plan, indent=2))
