#!/usr/bin/env python3
"""iOS Confidence Engine — scores entities for dead code removal safety.

Uses the arbiter 0-4 scale:
  Base score: 4.0 (assume unused until proven otherwise).
  Deductions applied based on usage signals, framework patterns, and resource references.
  Categories: SAFE (3.0-4.0), LIKELY (2.0-2.9), UNCERTAIN (1.0-1.9), KEEP (<1.0).

Adapted from garbage-collector-plugin ios_confidence_engine.py, rescaled to 0-4.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set

try:
    from .objc_syntax import swift_base_names
    from .arbiter_meta import require_stamp, stamp, usage_data_problem, write_json
except ImportError:
    from objc_syntax import swift_base_names
    from arbiter_meta import require_stamp, stamp, usage_data_problem, write_json

try:
    from .ios_framework_rules import (
        ALWAYS_KEEP_METHODS,
        FRAMEWORK_MANAGED_ANNOTATIONS,
        FRAMEWORK_SUPERCLASSES,
        FRAMEWORK_PROTOCOLS,
        REACT_NATIVE_PATTERNS,
    )
except ImportError:
    from ios_framework_rules import (
        ALWAYS_KEEP_METHODS,
        FRAMEWORK_MANAGED_ANNOTATIONS,
        FRAMEWORK_SUPERCLASSES,
        FRAMEWORK_PROTOCOLS,
        REACT_NATIVE_PATTERNS,
    )


# Arbiter 0-4 scale thresholds
BASE_SCORE = 4.0
SAFE_THRESHOLD = 3.0
LIKELY_THRESHOLD = 2.0
UNCERTAIN_THRESHOLD = 1.0


class IOSConfidenceEngine:
    """Scores iOS entities for dead code removal confidence."""

    def __init__(self, entities_path: str, usage_path: str = None,
                 resource_refs_path: str = None, dispatch_path: str = None):
        self.entities = self._load_json(entities_path)
        # ENTITIES.json from ios_call_graph_analyzer.py already carries the usage counts
        self.usage_data = (self._load_json(usage_path) if usage_path
                           else {k: v for k, v in self.entities.items() if k == "usages"})
        self.resource_refs = self._load_json(resource_refs_path) if resource_refs_path else {}
        self.dispatch_data = self._load_json(dispatch_path) if dispatch_path else {}

        # Build lookup sets
        self.resource_classes = self._build_resource_class_set()
        self.resource_selectors = self._build_resource_selector_set()
        self.usage_counts = self._build_usage_counts()
        self.protected_selectors, self.protected_classes = self._build_dispatch_sets()

    def score_all(self) -> Dict[str, Any]:
        """Score all entities and return categorized results."""
        scored_entities = []
        entities = self.entities.get("entities", [])

        for entity in entities:
            scored = self._score_entity(entity)
            scored_entities.append(scored)

        # Categorize
        safe = [e for e in scored_entities if e["category"] == "SAFE"]
        likely = [e for e in scored_entities if e["category"] == "LIKELY"]
        uncertain = [e for e in scored_entities if e["category"] == "UNCERTAIN"]
        keep = [e for e in scored_entities if e["category"] == "KEEP"]

        return {
            "totalEntities": len(scored_entities),
            "entities": scored_entities,
            "categories": {
                "SAFE": {"count": len(safe), "entities": safe},
                "LIKELY": {"count": len(likely), "entities": likely},
                "UNCERTAIN": {"count": len(uncertain), "entities": uncertain},
                "KEEP": {"count": len(keep), "entities": keep},
            },
            "summary": {
                "safe_count": len(safe),
                "likely_count": len(likely),
                "uncertain_count": len(uncertain),
                "keep_count": len(keep),
                "removable_count": len(safe) + len(likely) + len(uncertain),
            },
        }

    def _score_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Apply confidence scoring to a single entity."""
        score = BASE_SCORE
        reasons: List[str] = []
        name = entity.get("name", "")
        fqn = entity.get("fullyQualifiedName", name)

        # Test code: always keep
        if entity.get("isTestCode", False):
            return self._make_scored(entity, 0, "KEEP", ["Test code — never remove"])

        # ObjC method whose selector the SDK or a Pod declares: an override or a
        # protocol method the framework calls
        if entity.get("implementsFrameworkSelector", False):
            return self._make_scored(entity, 0, "KEEP", [entity.get(
                "frameworkReason", f"Framework selector (SDK/Pods declare {name})")])

        # Methods of a type the code calls via NSSelectorFromString(<runtime string>)
        if entity.get("dynamicDispatchClass"):
            return self._make_scored(entity, 0, "KEEP", [
                f"Runtime-built selector: methods of {entity['dynamicDispatchClass']} "
                "are called via NSSelectorFromString(<string>)"])

        # Always-keep lifecycle methods
        if self._is_always_keep_method(name):
            return self._make_scored(entity, 0, "KEEP", [f"iOS lifecycle method: {name}"])

        # React Native bridge detection
        for pattern in REACT_NATIVE_PATTERNS:
            if pattern in str(entity.get("annotations", [])):
                return self._make_scored(entity, 0, "KEEP",
                                         [f"React Native bridge: {pattern}"])

        # Usage from call graph
        usage_count = self.usage_counts.get(fqn, 0)
        if usage_count > 0:
            return self._make_scored(entity, 0, "KEEP",
                                     [f"Used in call graph ({usage_count} references)"])

        # Type whose members are mentioned elsewhere: the executor would block it anyway
        if entity.get("externalMemberCount"):
            deduction = 1.5
            score -= deduction
            reasons.append(f"-{deduction}: Members mentioned in other files "
                           f"({', '.join(entity.get('externalMembers', []))})")

        # Storyboard/XIB references
        if name in self.resource_classes:
            deduction = 2.5
            score -= deduction
            reasons.append(f"-{deduction}: Referenced in storyboard/XIB")
        if entity.get("type") == "method" and (
                name in self.resource_selectors or name.split(":")[0] in self.resource_selectors):
            deduction = 2.5
            score -= deduction
            reasons.append(f"-{deduction}: Action connected in storyboard/XIB")

        # Dynamic dispatch protection
        base_name = name.split("(")[0] if "(" in name else name
        entity_type = entity.get("type", "")
        if entity_type in ("class", "struct", "enum") and name in self.protected_classes:
            deduction = 2.0
            score -= deduction
            reasons.append(f"-{deduction}: NSClassFromString target")
        elif entity_type in ("method", "function", "property") and base_name in self.protected_selectors:
            deduction = 1.5
            score -= deduction
            reasons.append(f"-{deduction}: Dynamic dispatch target")

        # Framework annotations
        for annotation in entity.get("annotations", []):
            if annotation in FRAMEWORK_MANAGED_ANNOTATIONS:
                rule = FRAMEWORK_MANAGED_ANNOTATIONS[annotation]
                deduction = rule["deduction"]
                if deduction >= 4.0:
                    return self._make_scored(entity, 0, "KEEP",
                                             [f"Entry point: {annotation}"])
                if deduction > 0:
                    score -= deduction
                    reasons.append(f"-{deduction}: {rule['reason']} ({annotation})")

        # @objc exposure (if not already deducted via annotation)
        if entity.get("isObjCExposed", False) and not any("@objc" in r for r in reasons):
            deduction = 1.5
            score -= deduction
            reasons.append(f"-{deduction}: ObjC-exposed (runtime may call it)")

        # Inheritance from framework superclasses
        superclass = entity.get("inheritsFrom")
        if superclass and superclass in FRAMEWORK_SUPERCLASSES:
            rule = FRAMEWORK_SUPERCLASSES[superclass]
            if rule["deduction"] >= 4.0:
                return self._make_scored(entity, 0, "KEEP", [rule["reason"]])
            score -= rule["deduction"]
            reasons.append(f"-{rule['deduction']}: {rule['reason']}")

        # Protocol conformances
        for protocol in entity.get("protocolConformances", []):
            # UIApplicationDelegate/UIWindowSceneDelegate live in the superclass table but are
            # adopted as protocols (`class AppDelegate: UIResponder, UIApplicationDelegate`)
            rule = FRAMEWORK_PROTOCOLS.get(protocol) or FRAMEWORK_SUPERCLASSES.get(protocol)
            if rule:
                if rule["deduction"] >= 4.0:
                    return self._make_scored(entity, 0, "KEEP", [rule["reason"]])
                score -= rule["deduction"]
                reasons.append(f"-{rule['deduction']}: {rule['reason']}")

        # Extension members are globally callable — penalise scoring
        if entity.get("isExtensionMember", False):
            deduction = 1.5
            score -= deduction
            reasons.append(f"-{deduction}: Extension member — globally callable, requires member-level grep before removal")

        # Public/open access (may be used from other modules)
        access = entity.get("accessLevel", "internal")
        if access in ("public", "open"):
            deduction = 1.0
            score -= deduction
            reasons.append(f"-{deduction}: Public/open access (may be used externally)")

        # Override methods are called by superclass
        if entity.get("isOverride", False):
            deduction = 2.0
            score -= deduction
            reasons.append(f"-{deduction}: Override method (called by superclass)")

        # Clamp score
        score = max(0.0, min(4.0, score))

        # Categorize
        category = self._categorize(score)

        if not reasons:
            reasons.append("No usage signals detected — candidate for removal")

        return self._make_scored(entity, score, category, reasons)

    def _is_always_keep_method(self, name: str) -> bool:
        """Check if method name matches an always-keep pattern."""
        if name in ALWAYS_KEEP_METHODS:
            return True
        # Strip parameter labels for matching
        base_name = name.split("(")[0] if "(" in name else name
        return base_name in ALWAYS_KEEP_METHODS

    def _categorize(self, score: float) -> str:
        if score >= SAFE_THRESHOLD:
            return "SAFE"
        elif score >= LIKELY_THRESHOLD:
            return "LIKELY"
        elif score >= UNCERTAIN_THRESHOLD:
            return "UNCERTAIN"
        else:
            return "KEEP"

    def _make_scored(self, entity: Dict, score: float, category: str,
                     reasons: List[str]) -> Dict[str, Any]:
        return {
            "name": entity.get("name", ""),
            "fullyQualifiedName": entity.get("fullyQualifiedName", entity.get("name", "")),
            "type": entity.get("type", ""),
            "file": entity.get("file", ""),
            "line": entity.get("line", 0),
            "language": entity.get("language", "swift"),
            "confidenceScore": round(score, 2),
            "category": category,
            "deductionReasons": reasons,
            "accessLevel": entity.get("accessLevel", "internal"),
            "isObjCExposed": entity.get("isObjCExposed", False),
            "isExtensionMember": entity.get("isExtensionMember", False),
            "annotations": entity.get("annotations", []),
            "declarations": entity.get("declarations", []),
            "owner": entity.get("owner"),
        }

    def _build_resource_class_set(self) -> Set[str]:
        """Build set of class names referenced in storyboards/XIBs/plists."""
        refs = self.resource_refs.get("references", [])
        return {r["className"] for r in refs if r.get("className")}

    def _build_resource_selector_set(self) -> Set[str]:
        """Action selectors connected in storyboards/XIBs, plus their Swift names."""
        names: Set[str] = set()
        for ref in self.resource_refs.get("references", []):
            selector = ref.get("selector") if ref.get("referenceType") == "action" else None
            if selector:
                names |= {selector, selector.split(":")[0]} | swift_base_names(selector)
        return names

    def _build_usage_counts(self) -> Dict[str, int]:
        """Build usage count lookup from usage data."""
        counts = {}
        for usage in self.usage_data.get("usages", []):
            fqn = usage.get("fullyQualifiedName", "")
            counts[fqn] = usage.get("usageCount", 0)
        return counts

    def _build_dispatch_sets(self) -> tuple:
        """Build protected names from dynamic dispatch scan results."""
        protected_selectors: Set[str] = set()
        protected_classes: Set[str] = set()

        for ref in self.dispatch_data.get("nsselector_refs", []):
            protected_selectors.add(ref.get("selectorName", "").rstrip(":"))
        for ref in self.dispatch_data.get("data_driven_selectors", []):
            protected_selectors.add(ref.get("selectorName", "").rstrip(":"))
        for ref in self.dispatch_data.get("perform_selector_refs", []):
            protected_selectors.add(ref.get("selectorName", "").rstrip(":"))
        for ref in self.dispatch_data.get("kvc_refs", []):
            protected_selectors.add(ref.get("propertyName", ""))
        for ref in self.dispatch_data.get("nsclass_refs", []):
            protected_classes.add(ref.get("className", ""))

        return protected_selectors, protected_classes

    @staticmethod
    def _load_json(path: str) -> Dict:
        if not path or not Path(path).exists():
            return {}
        with open(path) as f:
            return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Arbiter iOS Confidence Scorer (0-4 scale)")
    parser.add_argument("--entities", required=True, help="Path to ENTITIES.json")
    parser.add_argument("--usage", help="Path to USAGE.json (default: the `usages` in ENTITIES.json)")
    parser.add_argument("--resources", help="Path to resource_refs.json (optional)")
    parser.add_argument("--dispatch", help="Path to dispatch_scan.json (optional)")
    parser.add_argument("--output", required=True, help="Output path for CONFIDENCE.json")
    parser.add_argument("--slim", action="store_true",
                        help="Write only SAFE/LIKELY/UNCERTAIN entities (KEEP is counted, not listed)")
    parser.add_argument("--allow-unstamped", action="store_true",
                        help="Accept an ENTITIES.json not produced by the plugin's analyzer")

    args = parser.parse_args()

    print("🎯 Arbiter iOS Confidence Scorer")
    print(f"   Entities: {args.entities}")
    print(f"   Usage data: {args.usage or args.entities + ' (usages)'}")
    if args.resources:
        print(f"   Resource refs: {args.resources}")
    if args.dispatch:
        print(f"   Dispatch scan: {args.dispatch}")
    print()

    engine = IOSConfidenceEngine(args.entities, args.usage, args.resources, args.dispatch)
    require_stamp(engine.entities, "ENTITIES.json", args.allow_unstamped)
    problem = usage_data_problem(engine.entities, engine.usage_data)
    if problem:
        # Without usage data every entity scores as unused — refuse rather than mislabel it SAFE
        raise SystemExit(f"❌ {problem}. Re-run ios_call_graph_analyzer.py, or pass --usage.")
    results = engine.score_all()
    results["generatedBy"] = stamp(["ios_confidence_engine.py", "ios_framework_rules.py"])
    if args.slim:
        results["entities"] = [e for e in results["entities"] if e["category"] != "KEEP"]
        if isinstance(results.get("categories", {}).get("KEEP"), dict):
            results["categories"]["KEEP"]["entities"] = []  # count kept, list dropped
        results["slim"] = True

    write_json(args.output, results, compact=True)

    summary = results["summary"]
    print(f"✅ Scoring complete (arbiter 0-4 scale)")
    print(f"   Total entities: {results['totalEntities']}")
    print(f"   SAFE (3.0-4.0):      {summary['safe_count']}")
    print(f"   LIKELY (2.0-2.9):    {summary['likely_count']}")
    print(f"   UNCERTAIN (1.0-1.9): {summary['uncertain_count']}")
    print(f"   KEEP (<1.0):         {summary['keep_count']}")
    print(f"   Output: {args.output}")


if __name__ == "__main__":
    main()
