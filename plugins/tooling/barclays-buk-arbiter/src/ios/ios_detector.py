#!/usr/bin/env python3
"""iOS Project Detector — detects Swift/ObjC projects, build systems, and metadata.

Adapted from f_barclays-claude-code-plugins orchestrator/ios_detector.py.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class iOSProjectMetadata:
    """iOS project metadata."""
    is_ios_project: bool
    has_swift: bool
    has_objc: bool
    swift_file_count: int
    objc_file_count: int
    build_system: str  # xcworkspace, xcodeproj, spm, cocoapods, or none
    xcode_version: Optional[str]
    schemes: List[str]
    test_targets: List[str]
    ui_test_targets: List[str]


class iOSDetector:
    """Detects iOS project structure, languages, build system, and metadata."""

    EXCLUDE_PATTERNS = [
        "Pods/", "DerivedData/", "build/", ".build/",
        ".git/", "node_modules/", "Carthage/"
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()

    def detect_languages(self) -> dict:
        """Detect Swift and Objective-C files in project."""
        swift_files = list(self.project_path.rglob("*.swift"))
        objc_files = list(self.project_path.rglob("*.m"))
        objcpp_files = list(self.project_path.rglob("*.mm"))
        header_files = list(self.project_path.rglob("*.h"))

        # Filter by exclusions
        swift_files = [f for f in swift_files if not self._is_excluded(f)]
        objc_files = [f for f in objc_files if not self._is_excluded(f)]
        objcpp_files = [f for f in objcpp_files if not self._is_excluded(f)]
        header_files = [f for f in header_files if not self._is_excluded(f)]

        return {
            "swift_files": swift_files,
            "objc_files": objc_files,
            "objcpp_files": objcpp_files,
            "header_files": header_files,
            "has_swift": len(swift_files) > 0,
            "has_objc": len(objc_files) + len(objcpp_files) > 0,
        }

    def detect_build_system(self) -> dict:
        """Detect iOS build system (Xcode workspace, project, or SPM)."""
        # Check for CocoaPods workspace
        xcworkspaces = list(self.project_path.glob("*.xcworkspace"))
        if xcworkspaces:
            return {
                "system": "xcworkspace",
                "path": str(xcworkspaces[0]),
                "name": xcworkspaces[0].name,
            }

        # Check for Xcode project
        xcprojects = list(self.project_path.glob("*.xcodeproj"))
        if xcprojects:
            return {
                "system": "xcodeproj",
                "path": str(xcprojects[0]),
                "name": xcprojects[0].name,
            }

        # Check for Swift Package Manager
        if (self.project_path / "Package.swift").exists():
            return {
                "system": "spm",
                "path": str(self.project_path / "Package.swift"),
                "name": "Package.swift",
            }

        # Check for Podfile (CocoaPods without workspace)
        if (self.project_path / "Podfile").exists():
            return {
                "system": "cocoapods",
                "path": str(self.project_path / "Podfile"),
                "name": "Podfile",
            }

        return {"system": "none", "path": None, "name": None}

    def detect_xcode_version(self) -> Optional[str]:
        """Detect Xcode version."""
        try:
            result = subprocess.run(
                ["xcodebuild", "-version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Xcode"):
                        return line.split()[-1]
        except Exception:
            pass
        return None

    def detect_schemes(self) -> List[str]:
        """Detect Xcode schemes."""
        build_system = self.detect_build_system()
        if build_system["system"] not in ("xcworkspace", "xcodeproj"):
            return []

        try:
            args = ["xcodebuild", "-list", "-json"]
            if build_system["system"] == "xcworkspace":
                args.extend(["-workspace", build_system["path"]])
            else:
                args.extend(["-project", build_system["path"]])

            result = subprocess.run(
                args, capture_output=True, text=True,
                timeout=10, cwd=str(self.project_path),
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Handle both workspace and project response formats
                if "workspace" in data:
                    return data["workspace"].get("schemes", [])
                return data.get("project", {}).get("schemes", [])
        except Exception:
            pass
        return []

    def detect_test_targets(self) -> tuple:
        """Detect unit test and UI test targets from scheme names."""
        unit_tests = []
        ui_tests = []

        schemes = self.detect_schemes()
        for scheme in schemes:
            if "Test" in scheme or "test" in scheme:
                if "UI" in scheme or "ui" in scheme:
                    ui_tests.append(scheme)
                else:
                    unit_tests.append(scheme)

        return unit_tests, ui_tests

    def run_detection(self) -> iOSProjectMetadata:
        """Run all detection and return metadata."""
        languages = self.detect_languages()
        build_system = self.detect_build_system()
        xcode_version = self.detect_xcode_version()
        schemes = self.detect_schemes()
        unit_tests, ui_tests = self.detect_test_targets()

        is_ios_project = (
            languages["has_swift"] or languages["has_objc"]
        ) and build_system["system"] != "none"

        return iOSProjectMetadata(
            is_ios_project=is_ios_project,
            has_swift=languages["has_swift"],
            has_objc=languages["has_objc"],
            swift_file_count=len(languages["swift_files"]),
            objc_file_count=len(languages["objc_files"]) + len(languages["objcpp_files"]),
            build_system=build_system["system"],
            xcode_version=xcode_version,
            schemes=schemes,
            test_targets=unit_tests,
            ui_test_targets=ui_tests,
        )

    def _is_excluded(self, file_path: Path) -> bool:
        path_str = str(file_path)
        return any(pat in path_str for pat in self.EXCLUDE_PATTERNS)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: ios_detector.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]
    detector = iOSDetector(project_path)
    metadata = detector.run_detection()
    print(json.dumps(asdict(metadata), indent=2))


if __name__ == "__main__":
    main()
