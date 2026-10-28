#!/usr/bin/env python3
"""iOS Resource Scanner — extracts class references from storyboards, XIBs, plists, and assets.

Merged from garbage-collector-plugin storyboard_scanner.py, xib_scanner.py,
asset_catalog_scanner.py, and plist_scanner.py.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Set

try:
    import plistlib
except ImportError:
    plistlib = None


# Plist patterns that look like class names
CLASS_NAME_PATTERN = re.compile(
    r'^[A-Z][A-Za-z0-9]{2,}'
    r'(?:ViewController|View|Controller|Manager|Service|Coordinator|Cell|'
    r'Handler|Provider|Factory|Builder|Helper|Delegate|DataSource)$'
)

# Known plist keys that contain class references
CLASS_REFERENCE_KEYS = {
    "NSExtensionPrincipalClass",
    "UIMainStoryboardFile",
    "NSExtensionMainStoryboard",
    "principalClass",
    "customClass",
}


def scan_storyboard(file_path: str) -> List[Dict[str, Any]]:
    """Extract class and connection references from a storyboard or XIB file."""
    references = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        return references

    # Extract customClass references
    for elem in root.iter():
        custom_class = elem.get("customClass")
        if custom_class:
            references.append({
                "className": custom_class,
                "module": elem.get("customModule", ""),
                "sourceFile": file_path,
                "sourceType": _file_type(file_path),
                "referenceType": "customClass",
                "elementType": elem.tag,
                "storyboardIdentifier": elem.get("storyboardIdentifier", ""),
            })

        # Segue destinations
        if elem.tag == "segue":
            dest = elem.get("destination")
            if dest:
                references.append({
                    "className": None,
                    "destinationId": dest,
                    "sourceFile": file_path,
                    "sourceType": _file_type(file_path),
                    "referenceType": "segue",
                    "segueIdentifier": elem.get("identifier", ""),
                })

    # IBOutlet connections
    for outlet in root.iter("outlet"):
        references.append({
            "className": None,
            "sourceFile": file_path,
            "sourceType": _file_type(file_path),
            "referenceType": "outlet",
            "property": outlet.get("property", ""),
            "destination": outlet.get("destination", ""),
        })

    # IBAction connections
    for action in root.iter("action"):
        references.append({
            "className": None,
            "sourceFile": file_path,
            "sourceType": _file_type(file_path),
            "referenceType": "action",
            "selector": action.get("selector", ""),
            "eventType": action.get("eventType", ""),
        })

    return references


LEGACY_ACTION_LABEL = re.compile(r'<string key="label">([A-Za-z_]\w*:?)</string>')
WORD = re.compile(r"[A-Za-z_]\w*")


def scan_legacy_mentions(file_path: str, known_classes: Set[str],
                         already_found: Set[str]) -> List[Dict[str, Any]]:
    """Class names and action selectors in formats scan_storyboard doesn't read.

    Old-style XIBs (IBDocument archives) store classes as `<string>MyViewController</string>`
    and actions as `<string key="label">didTap:</string>`, not customClass/selector attributes.
    """
    try:
        text = Path(file_path).read_text(errors="replace")
    except (IOError, OSError):
        return []
    refs: List[Dict[str, Any]] = []
    for name in (set(WORD.findall(text)) & known_classes) - already_found:
        refs.append({"className": name, "sourceFile": file_path,
                     "sourceType": _file_type(file_path), "referenceType": "mention"})
    for selector in set(LEGACY_ACTION_LABEL.findall(text)):
        refs.append({"className": None, "sourceFile": file_path,
                     "sourceType": _file_type(file_path), "referenceType": "action",
                     "selector": selector, "eventType": "legacy"})
    return refs


def scan_storyboards_and_xibs(directory: str,
                              exclude_patterns: List[str] = None,
                              known_classes: Set[str] = None) -> List[Dict[str, Any]]:
    """Scan directory for all storyboard and XIB files."""
    exclude_patterns = exclude_patterns or ["Pods/", "Carthage/", ".build/", "DerivedData/"]
    all_references = []
    dir_path = Path(directory)

    for ext in ["*.storyboard", "*.xib"]:
        for file_path in dir_path.rglob(ext):
            path_str = str(file_path)
            if any(pat in path_str for pat in exclude_patterns):
                continue
            refs = scan_storyboard(str(file_path))
            if known_classes:
                found = {r["className"] for r in refs if r.get("className")}
                refs += scan_legacy_mentions(str(file_path), known_classes, found)
            all_references.extend(refs)

    return all_references


def scan_plists(directory: str, known_classes: Set[str] = None,
                exclude_patterns: List[str] = None) -> List[Dict[str, Any]]:
    """Scan plists for class name references."""
    if plistlib is None:
        return []

    exclude_patterns = exclude_patterns or ["Pods/", "Carthage/", ".build/", "DerivedData/"]
    all_references = []
    dir_path = Path(directory)

    for plist_path in dir_path.rglob("*.plist"):
        path_str = str(plist_path)
        if any(pat in path_str for pat in exclude_patterns):
            continue
        refs = _scan_single_plist(str(plist_path), known_classes or set())
        all_references.extend(refs)

    return all_references


def scan_asset_catalogs(directory: str,
                        exclude_patterns: List[str] = None) -> List[Dict[str, Any]]:
    """Scan .xcassets for named asset references."""
    exclude_patterns = exclude_patterns or ["Pods/", "Carthage/", ".build/"]
    assets = []
    dir_path = Path(directory)

    for contents_json in dir_path.rglob("Contents.json"):
        path_str = str(contents_json)
        if any(pat in path_str for pat in exclude_patterns):
            continue

        asset_dir = contents_json.parent
        asset_name = asset_dir.stem
        asset_type = _determine_asset_type(str(asset_dir))

        if asset_type:
            assets.append({
                "assetName": asset_name,
                "assetType": asset_type,
                "path": str(asset_dir),
            })

    return assets


def scan_all_resources(directory: str,
                       exclude_patterns: List[str] = None,
                       known_classes: Set[str] = None) -> Dict[str, Any]:
    """Scan all resource types and return combined results.

    This is the main entry point for resource scanning.
    """
    exclude = exclude_patterns or ["Pods/", "Carthage/", ".build/", "DerivedData/"]

    # Storyboards and XIBs
    ib_refs = scan_storyboards_and_xibs(directory, exclude, known_classes)

    # Plists
    plist_refs = scan_plists(directory, known_classes, exclude)

    # Assets (informational)
    assets = scan_asset_catalogs(directory, exclude)

    # Build class summary
    class_summary: Dict[str, int] = {}
    all_refs = ib_refs + plist_refs
    for ref in all_refs:
        cn = ref.get("className")
        if cn:
            class_summary[cn] = class_summary.get(cn, 0) + 1

    return {
        "references": all_refs,
        "classSummary": class_summary,
        "assets": assets,
        "summary": {
            "storyboard_xib_refs": len(ib_refs),
            "plist_refs": len(plist_refs),
            "asset_count": len(assets),
            "unique_classes_referenced": len(class_summary),
        },
    }


# --- Private helpers ---

def _scan_single_plist(file_path: str, known_classes: Set[str]) -> List[Dict[str, Any]]:
    """Find class name references in a single plist."""
    references = []
    try:
        with open(file_path, "rb") as f:
            plist = plistlib.load(f)
    except Exception:
        return references

    _scan_plist_value(plist, file_path, known_classes, references, key_path="")
    return references


def _scan_plist_value(value, file_path: str, known_classes: Set[str],
                      references: List[Dict[str, Any]], key_path: str):
    """Recursively scan plist values for class name matches."""
    if isinstance(value, str):
        if value in known_classes:
            references.append({
                "className": value,
                "sourceFile": file_path,
                "sourceType": "plist",
                "referenceType": "string_match",
                "keyPath": key_path,
            })
        elif CLASS_NAME_PATTERN.match(value):
            references.append({
                "className": value,
                "sourceFile": file_path,
                "sourceType": "plist",
                "referenceType": "pattern_match",
                "keyPath": key_path,
            })
    elif isinstance(value, dict):
        for k, v in value.items():
            new_path = f"{key_path}.{k}" if key_path else k
            if k in CLASS_REFERENCE_KEYS and isinstance(v, str):
                references.append({
                    "className": v,
                    "sourceFile": file_path,
                    "sourceType": "plist",
                    "referenceType": "known_key",
                    "keyPath": new_path,
                })
            else:
                _scan_plist_value(v, file_path, known_classes, references, new_path)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan_plist_value(item, file_path, known_classes, references, f"{key_path}[{i}]")


def _file_type(path: str) -> str:
    if path.endswith(".storyboard"):
        return "storyboard"
    elif path.endswith(".xib"):
        return "xib"
    return "unknown"


def _determine_asset_type(path: str) -> str:
    if ".imageset" in path:
        return "image"
    elif ".colorset" in path:
        return "color"
    elif ".dataset" in path:
        return "data"
    elif ".symbolset" in path:
        return "symbol"
    return ""


try:
    from .arbiter_meta import require_stamp, stamp, write_json
except ImportError:
    from arbiter_meta import require_stamp, stamp, write_json


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_resource_scanner.py <directory> [output.json] [--entities ENTITIES.json]")
        sys.exit(1)

    args = [a for a in sys.argv[1:]]
    known = None
    if "--entities" in args:
        i = args.index("--entities")
        with open(args[i + 1]) as f:
            known = {e["name"] for e in json.load(f).get("entities", []) if e.get("type") != "method"}
        del args[i:i + 2]
    directory = args[0]
    output_file = args[1] if len(args) > 1 else None

    print(f"🔍 Scanning iOS resources in: {directory}")
    results = scan_all_resources(directory, known_classes=known)

    summary = results["summary"]
    print(f"   Storyboard/XIB refs:    {summary['storyboard_xib_refs']}")
    print(f"   Plist refs:             {summary['plist_refs']}")
    print(f"   Asset catalog entries:  {summary['asset_count']}")
    print(f"   Unique classes found:   {summary['unique_classes_referenced']}")

    if output_file:
        results["generatedBy"] = stamp(["ios_resource_scanner.py"])
        write_json(output_file, results, compact=True)
        print(f"   Output: {output_file}")
