#!/usr/bin/env python3
"""Detect JDK version for the target repository.

Scans build configuration files (build.gradle, build.gradle.kts, pom.xml,
gradle.properties, .java-version) to determine the JDK version in use.

Input (JSON stdin):
    {"repo_dir": "/path/to/repo"}

Output (JSON stdout):
    {
        "status": "success",
        "jdk_version": 17,
        "jdk_version_raw": "17",
        "detection_source": "build.gradle:sourceCompatibility",
        "is_java_project": true
    }
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, log, progress, progress_done
from scripts.core.errors import error_exit

# Regex patterns for build.gradle / build.gradle.kts
_RE_COMPAT = re.compile(
    r"(?:source|target)Compatibility\s*[=:]\s*['\"]?([\w.]+)['\"]?"
)
_RE_JAVA_VERSION = re.compile(r"JavaVersion\.VERSION_(\w+)")
_RE_JVM_TARGET = re.compile(r"jvmTarget\s*[=:]\s*['\"]?([\w.]+)['\"]?")

# Regex patterns for pom.xml
_RE_MAVEN_COMPILER_PROP = re.compile(
    r"<maven\.compiler\.(?:source|target)>([\d.]+)</maven\.compiler\.(?:source|target)>"
)
_RE_MAVEN_COMPILER_PLUGIN = re.compile(
    r"<(?:source|target)>([\d.]+)</(?:source|target)>"
)

# Regex patterns for gradle.properties
_RE_GRADLE_JAVA_VERSION = re.compile(r"^javaVersion\s*=\s*(.+)$", re.MULTILINE)
_RE_GRADLE_TOOLCHAIN = re.compile(
    r"^org\.gradle\.jvm\.toolchain\.version\s*=\s*(.+)$", re.MULTILINE
)


def normalize_jdk_version(raw: str) -> tuple[int | None, str | None]:
    """Normalize a raw JDK version string to (numeric_version, raw_string).

    Examples:
        "1.8"           -> (8, "1.8")
        "11"            -> (11, "11")
        "VERSION_1_8"   -> (8, "1.8")
        "VERSION_17"    -> (17, "17")
        "1_8"           -> (8, "1.8")
    """
    if not raw:
        return None, None

    cleaned = raw.strip().strip("'\"")

    # Handle JavaVersion enum constants: VERSION_1_8, VERSION_11, etc.
    version_prefix = "VERSION_"
    if cleaned.upper().startswith(version_prefix):
        cleaned = cleaned[len(version_prefix):]

    # Handle underscore notation: 1_8 -> 1.8
    if "_" in cleaned:
        cleaned = cleaned.replace("_", ".")

    # Handle legacy 1.x notation: 1.8 -> 8, 1.7 -> 7, 1.6 -> 6
    legacy_match = re.match(r"^1\.(\d+)$", cleaned)
    if legacy_match:
        numeric = int(legacy_match.group(1))
        return numeric, f"1.{legacy_match.group(1)}"

    # Handle plain numeric versions: 8, 11, 17, 21
    if re.match(r"^\d+$", cleaned):
        return int(cleaned), cleaned

    return None, None


def _read_file_safe(path: Path) -> str | None:
    """Read a file and return its contents, or None on any error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return None


def _detect_from_build_gradle(repo_path: Path) -> tuple[int | None, str | None, str | None]:
    """Check build.gradle for JDK version indicators.

    Returns (jdk_version, jdk_version_raw, detection_source) or (None, None, None).
    """
    gradle_file = repo_path / "build.gradle"
    content = _read_file_safe(gradle_file)
    if content is None:
        return None, None, None

    # Check sourceCompatibility / targetCompatibility
    match = _RE_COMPAT.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            field = "sourceCompatibility" if "source" in match.group(0).lower() else "targetCompatibility"
            return version, raw, f"build.gradle:{field}"

    # Check JavaVersion.VERSION_X
    match = _RE_JAVA_VERSION.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "build.gradle:JavaVersion"

    return None, None, None


def _detect_from_build_gradle_kts(repo_path: Path) -> tuple[int | None, str | None, str | None]:
    """Check build.gradle.kts for JDK version indicators.

    Returns (jdk_version, jdk_version_raw, detection_source) or (None, None, None).
    """
    gradle_file = repo_path / "build.gradle.kts"
    content = _read_file_safe(gradle_file)
    if content is None:
        return None, None, None

    # Check sourceCompatibility / targetCompatibility
    match = _RE_COMPAT.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            field = "sourceCompatibility" if "source" in match.group(0).lower() else "targetCompatibility"
            return version, raw, f"build.gradle.kts:{field}"

    # Check JavaVersion.VERSION_X
    match = _RE_JAVA_VERSION.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "build.gradle.kts:JavaVersion"

    # Check jvmTarget (Kotlin-specific)
    match = _RE_JVM_TARGET.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "build.gradle.kts:jvmTarget"

    return None, None, None


def _detect_from_pom_xml(repo_path: Path) -> tuple[int | None, str | None, str | None]:
    """Check pom.xml for JDK version indicators.

    Returns (jdk_version, jdk_version_raw, detection_source) or (None, None, None).
    """
    pom_file = repo_path / "pom.xml"
    content = _read_file_safe(pom_file)
    if content is None:
        return None, None, None

    # Check <maven.compiler.source/target> in properties
    match = _RE_MAVEN_COMPILER_PROP.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "pom.xml:maven.compiler.source"

    # Check <source>/<target> inside maven-compiler-plugin configuration
    match = _RE_MAVEN_COMPILER_PLUGIN.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            tag = "source" if "source" in match.group(0) else "target"
            return version, raw, f"pom.xml:maven-compiler-plugin:{tag}"

    return None, None, None


def _detect_from_gradle_properties(repo_path: Path) -> tuple[int | None, str | None, str | None]:
    """Check gradle.properties for JDK version indicators.

    Returns (jdk_version, jdk_version_raw, detection_source) or (None, None, None).
    """
    props_file = repo_path / "gradle.properties"
    content = _read_file_safe(props_file)
    if content is None:
        return None, None, None

    # Check javaVersion=VALUE
    match = _RE_GRADLE_JAVA_VERSION.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "gradle.properties:javaVersion"

    # Check org.gradle.jvm.toolchain.version=VALUE
    match = _RE_GRADLE_TOOLCHAIN.search(content)
    if match:
        version, raw = normalize_jdk_version(match.group(1))
        if version is not None:
            return version, raw, "gradle.properties:org.gradle.jvm.toolchain.version"

    return None, None, None


def _detect_from_java_version_file(repo_path: Path) -> tuple[int | None, str | None, str | None]:
    """Check .java-version file at repo root.

    Returns (jdk_version, jdk_version_raw, detection_source) or (None, None, None).
    """
    version_file = repo_path / ".java-version"
    content = _read_file_safe(version_file)
    if content is None:
        return None, None, None

    first_line = content.strip().splitlines()[0].strip() if content.strip() else ""
    if first_line:
        version, raw = normalize_jdk_version(first_line)
        if version is not None:
            return version, raw, ".java-version"

    return None, None, None


# Detection functions in priority order
_DETECTORS = [
    _detect_from_build_gradle,
    _detect_from_build_gradle_kts,
    _detect_from_pom_xml,
    _detect_from_gradle_properties,
    _detect_from_java_version_file,
]


def detect_jdk_version(repo_path: str | Path) -> dict:
    """Detect the JDK version from build configuration files.

    Checks files in priority order and returns the first match.

    Returns:
        Dict with jdk_version, jdk_version_raw, detection_source, is_java_project.
    """
    repo_path = Path(repo_path)
    # Try each detector in priority order
    for detector in _DETECTORS:
        version, raw, source = detector(repo_path)
        if version is not None:
            log(f"JDK version detected: {version} (raw={raw}) from {source}")
            return {
                "jdk_version": version,
                "jdk_version_raw": raw,
                "detection_source": source,
                "is_java_project": True,
            }

    # Fallback: check for .java files (use Path.rglob for Python 3.9 compat)
    log("No JDK version found in build files, checking for .java files")
    java_files = next(repo_path.rglob("*.java"), None)
    if java_files is not None:
        log(f"Found .java files (e.g. {java_files}), marking as Java project")
        return {
            "jdk_version": None,
            "jdk_version_raw": None,
            "detection_source": None,
            "is_java_project": True,
        }

    log("No .java files found, not a Java project")
    return {
        "jdk_version": None,
        "jdk_version_raw": None,
        "detection_source": None,
        "is_java_project": False,
    }


def main() -> None:
    start_time = time.time()
    input_data = read_json_input()

    repo_dir = input_data.get("repo_dir", "")
    if not repo_dir:
        error_exit("repo_dir is required", "input_validation")

    repo_path = Path(repo_dir)
    if not repo_path.is_dir():
        error_exit(f"Directory not found: {repo_dir}", "dir_check")

    # Detect JDK version
    progress("Detecting JDK version...")
    result = detect_jdk_version(repo_path)

    if result["jdk_version"] is not None:
        progress_done(
            f"JDK {result['jdk_version']} detected from {result['detection_source']}"
        )
    elif result["is_java_project"]:
        progress_done("Java project detected but JDK version not found in build config")
    else:
        progress_done("Not a Java project")

    write_json_output({
        "status": "success",
        **result,
    }, start_time=start_time)


if __name__ == "__main__":
    main()
