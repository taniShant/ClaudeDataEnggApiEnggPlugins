#!/usr/bin/env python3
"""Dynamic Dispatch Scanner — finds runtime selector and class references.

Detects patterns that bypass static analysis:
1. NSSelectorFromString(@"methodName")
2. NSClassFromString(@"ClassName")
3. performSelector patterns
4. Data-driven selector dispatch
5. value(forKey:) / setValue(_:forKey:) KVC patterns
6. String-constructed selectors

Adapted from garbage-collector-plugin dispatch_scanner.py.
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple


# Regex patterns for dynamic dispatch detection
NSSELECTOR_PATTERN = re.compile(
    r'NSSelectorFromString\s*\(\s*@?"([^"]+)"\s*\)'
)
NSCLASS_PATTERN = re.compile(
    r'NSClassFromString\s*\(\s*@?"([^"]+)"\s*\)'
)
SELECTOR_ASSIGNMENT_PATTERN = re.compile(
    r'\.selector\s*=\s*(?:@?"([^"]+)"|#selector\(([^)]+)\))'
)
PERFORM_SELECTOR_PATTERN = re.compile(
    r'performSelector\s*:\s*(?:@selector\(([^)]+)\)|NSSelectorFromString\s*\(\s*@?"([^"]+)"\s*\))'
)
KVC_PATTERN = re.compile(
    r'(?:value|setValue)\s*\(\s*(?:forKey|forKeyPath)\s*:\s*"([^"]+)"\s*\)'
)
SELECTOR_CONCAT_PATTERN = re.compile(
    r'(?:selector|sel|action)\w*\s*=\s*"(didSelect|handle|on|action|navigate|start|show|present)(\w*)"'
)
SELECTOR_INTERPOLATION_PATTERN = re.compile(
    r'"(didSelect|handle|on|action|navigate|start|show|present)[^"]*\\[\(]'
)


class DynamicDispatchScanner:
    """Scans iOS project for dynamic dispatch patterns."""

    def __init__(self, repo_path: str, exclude_patterns: List[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.exclude = exclude_patterns or [
            "Pods/", "Carthage/", ".build/", "DerivedData/",
            "node_modules/", ".arbiter/"
        ]

    def scan(self) -> Dict[str, Any]:
        """Scan for all dynamic dispatch patterns. Returns structured results."""
        results = {
            "nsselector_refs": [],
            "nsclass_refs": [],
            "data_driven_selectors": [],
            "perform_selector_refs": [],
            "kvc_refs": [],
            "selector_construction": [],
            "summary": {},
        }

        swift_files = list(self.repo_path.rglob("*.swift"))
        objc_m_files = list(self.repo_path.rglob("*.m"))
        objc_h_files = list(self.repo_path.rglob("*.h"))

        all_files = swift_files + objc_m_files + objc_h_files
        all_files = [f for f in all_files if not self._is_excluded(f)]

        for file_path in all_files:
            self._scan_file(file_path, results)

        results["summary"] = {
            "nsselector_count": len(results["nsselector_refs"]),
            "nsclass_count": len(results["nsclass_refs"]),
            "data_driven_count": len(results["data_driven_selectors"]),
            "perform_selector_count": len(results["perform_selector_refs"]),
            "kvc_count": len(results["kvc_refs"]),
            "selector_construction_count": len(results["selector_construction"]),
            "files_scanned": len(all_files),
            "total_dynamic_refs": (
                len(results["nsselector_refs"]) +
                len(results["nsclass_refs"]) +
                len(results["data_driven_selectors"]) +
                len(results["perform_selector_refs"]) +
                len(results["kvc_refs"]) +
                len(results["selector_construction"])
            ),
        }

        return results

    def _scan_file(self, file_path: Path, results: Dict[str, Any]):
        """Scan a single file for dynamic dispatch patterns."""
        try:
            content = file_path.read_text(errors="replace")
        except (IOError, OSError):
            return

        rel_path = str(file_path.relative_to(self.repo_path))

        for line_num, line in enumerate(content.split("\n"), start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # NSSelectorFromString
            for match in NSSELECTOR_PATTERN.finditer(line):
                results["nsselector_refs"].append({
                    "selectorName": match.group(1),
                    "file": rel_path,
                    "line": line_num,
                    "pattern": "NSSelectorFromString",
                    "riskLevel": "high",
                })

            # NSClassFromString
            for match in NSCLASS_PATTERN.finditer(line):
                class_name = match.group(1)
                if "." in class_name:
                    class_name = class_name.split(".")[-1]
                results["nsclass_refs"].append({
                    "className": class_name,
                    "fullName": match.group(1),
                    "file": rel_path,
                    "line": line_num,
                    "pattern": "NSClassFromString",
                    "riskLevel": "high",
                })

            # Data-driven selector assignment
            for match in SELECTOR_ASSIGNMENT_PATTERN.finditer(line):
                selector_name = match.group(1) or match.group(2)
                if selector_name:
                    if "." in selector_name:
                        selector_name = selector_name.split(".")[-1]
                    results["data_driven_selectors"].append({
                        "selectorName": selector_name,
                        "file": rel_path,
                        "line": line_num,
                        "pattern": "selector_assignment",
                        "riskLevel": "high",
                    })

            # performSelector
            for match in PERFORM_SELECTOR_PATTERN.finditer(line):
                selector_name = match.group(1) or match.group(2)
                if selector_name:
                    results["perform_selector_refs"].append({
                        "selectorName": selector_name,
                        "file": rel_path,
                        "line": line_num,
                        "pattern": "performSelector",
                        "riskLevel": "medium",
                    })

            # KVC
            for match in KVC_PATTERN.finditer(line):
                results["kvc_refs"].append({
                    "propertyName": match.group(1),
                    "file": rel_path,
                    "line": line_num,
                    "pattern": "KVC",
                    "riskLevel": "medium",
                })

            # Dynamic selector construction
            for match in SELECTOR_CONCAT_PATTERN.finditer(line):
                results["selector_construction"].append({
                    "prefix": match.group(1),
                    "suffix": match.group(2),
                    "constructedSelector": match.group(1) + match.group(2) if match.group(2) else match.group(1) + "*",
                    "file": rel_path,
                    "line": line_num,
                    "pattern": "string_construction",
                    "riskLevel": "high",
                })

            # Interpolation-based selector
            for match in SELECTOR_INTERPOLATION_PATTERN.finditer(line):
                results["selector_construction"].append({
                    "prefix": match.group(1),
                    "suffix": "*",
                    "constructedSelector": match.group(1) + "*",
                    "file": rel_path,
                    "line": line_num,
                    "pattern": "string_interpolation",
                    "riskLevel": "high",
                })

    def _is_excluded(self, file_path: Path) -> bool:
        path_str = str(file_path)
        return any(pat in path_str for pat in self.exclude)


def scan_dynamic_dispatch(repo_path: str,
                          exclude_patterns: List[str] = None) -> Dict[str, Any]:
    """Public entry point: scan a repo for dynamic dispatch patterns."""
    scanner = DynamicDispatchScanner(repo_path, exclude_patterns)
    return scanner.scan()


def build_protected_names(scan_results: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """Extract protected method/class names from scan results."""
    protected_selectors: Set[str] = set()
    protected_classes: Set[str] = set()

    for ref in scan_results.get("nsselector_refs", []):
        protected_selectors.add(ref["selectorName"].rstrip(":"))
    for ref in scan_results.get("data_driven_selectors", []):
        protected_selectors.add(ref["selectorName"].rstrip(":"))
    for ref in scan_results.get("perform_selector_refs", []):
        protected_selectors.add(ref["selectorName"].rstrip(":"))
    for ref in scan_results.get("nsclass_refs", []):
        protected_classes.add(ref["className"])
    for ref in scan_results.get("kvc_refs", []):
        protected_selectors.add(ref["propertyName"])

    return protected_selectors, protected_classes


try:
    from .arbiter_meta import require_stamp, stamp, write_json
except ImportError:
    from arbiter_meta import require_stamp, stamp, write_json


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_dynamic_dispatch_scanner.py <repo_path> [output.json]")
        sys.exit(1)

    repo_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"🔍 Scanning dynamic dispatch patterns in: {repo_path}")
    results = scan_dynamic_dispatch(repo_path)

    summary = results["summary"]
    print(f"   NSSelectorFromString:  {summary['nsselector_count']}")
    print(f"   NSClassFromString:     {summary['nsclass_count']}")
    print(f"   Data-driven selectors: {summary['data_driven_count']}")
    print(f"   performSelector:       {summary['perform_selector_count']}")
    print(f"   KVC refs:              {summary['kvc_count']}")
    print(f"   Selector construction: {summary['selector_construction_count']}")
    print(f"   Total dynamic refs:    {summary['total_dynamic_refs']}")
    print(f"   Files scanned:         {summary['files_scanned']}")

    if output_file:
        results["generatedBy"] = stamp(["ios_dynamic_dispatch_scanner.py"])
        write_json(output_file, results)
        print(f"   Output: {output_file}")
