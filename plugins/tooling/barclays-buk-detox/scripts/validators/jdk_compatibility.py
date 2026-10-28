#!/usr/bin/env python3
"""Detect repository JDK version and validate dependency compatibility."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output, progress, progress_done
from scripts.core.errors import error_exit


class JDKCompatibilityValidator:
    """Detect repo JDK version and validate library compatibility."""

    # Mapping of artifact patterns to their min JDK versions
    MIN_JDK_REQUIREMENTS = {
        # Spring Framework
        "org.springframework:spring-webmvc": {
            "5.3": 8, "6.0": 17,  # Spring 6.0 requires Java 17
        },
        "org.springframework:spring-core": {
            "5.3": 8, "6.0": 17,
        },
        "org.springframework:spring-context": {
            "5.3": 8, "6.0": 17,
        },
        # Apache Commons
        "org.apache.commons:commons-text": {"1.10": 8, "1.11": 8},
        # Jackson
        "com.fasterxml.jackson.core:jackson-databind": {
            "2.15": 8, "2.16": 8, "2.17": 8, "2.18": 8, "2.19": 8,
        },
        "com.fasterxml.jackson.core:jackson-core": {
            "2.15": 8, "2.16": 8, "2.17": 8, "2.18": 8, "2.19": 8,
        },
        # Log4j
        "org.apache.logging.log4j:log4j-core": {
            "2.17": 8, "2.20": 8, "2.23": 8,
        },
        "ch.qos.reload4j:reload4j": {"1.2": 8},
        # Netty
        "io.netty:netty-codec": {"4.1": 8},
        # SnakeYAML
        "org.yaml:snakeyaml": {"1.32": 8, "2.0": 8, "2.1": 8},
        # Jersey
        "org.glassfish.jersey.core:jersey-common": {"2.41": 8, "2.42": 8},
        # Tomcat
        "org.apache.tomcat.embed:tomcat-embed-core": {
            "9.0": 8, "10.0": 11, "11.0": 17,
        },
    }

    def __init__(self, repo_root: str):
        """Initialize with repository root path."""
        self.repo_root = Path(repo_root)

    def detect_jdk_version(self) -> dict:
        """
        Detect JDK version from build files and source configuration.

        Returns dict with:
        {
            "detected_version": 11,  # The JDK version
            "source": "gradle|maven|pom|source_compatibility|java_version",
            "confidence": "high|medium|low",
            "raw_value": "11",
            "file_path": "/path/to/file"
        }
        """
        # Try Gradle
        gradle_result = self._detect_gradle_jdk()
        if gradle_result and gradle_result.get("detected_version"):
            return {**gradle_result, "source": "gradle"}

        # Try Maven
        maven_result = self._detect_maven_jdk()
        if maven_result and maven_result.get("detected_version"):
            return {**maven_result, "source": "maven"}

        # Try JVM version at runtime
        jvm_version = self._detect_runtime_jdk()
        if jvm_version:
            return {
                "detected_version": jvm_version,
                "source": "runtime",
                "confidence": "medium",
                "raw_value": str(jvm_version),
                "file_path": None,
            }

        return {
            "detected_version": 8,  # Default conservative fallback
            "source": "default",
            "confidence": "low",
            "raw_value": "8",
            "file_path": None,
        }

    def _detect_gradle_jdk(self) -> dict | None:
        """Detect JDK from build.gradle or gradle.properties."""
        build_gradle = self.repo_root / "build.gradle"
        if build_gradle.exists():
            content = build_gradle.read_text()
            # sourceCompatibility = '11'
            match = re.search(r"sourceCompatibility\s*=\s*['\"](\d+)['\"]", content)
            if match:
                return {
                    "detected_version": int(match.group(1)),
                    "confidence": "high",
                    "raw_value": match.group(1),
                    "file_path": str(build_gradle),
                }
            # java.sourceCompatibility = 11
            match = re.search(r"java\.sourceCompatibility\s*=\s*(\d+)", content)
            if match:
                return {
                    "detected_version": int(match.group(1)),
                    "confidence": "high",
                    "raw_value": match.group(1),
                    "file_path": str(build_gradle),
                }

        # Check gradle.properties
        gradle_props = self.repo_root / "gradle.properties"
        if gradle_props.exists():
            content = gradle_props.read_text()
            match = re.search(r"javaVersion\s*=\s*(\d+)", content)
            if match:
                return {
                    "detected_version": int(match.group(1)),
                    "confidence": "high",
                    "raw_value": match.group(1),
                    "file_path": str(gradle_props),
                }

        return None

    def _detect_maven_jdk(self) -> dict | None:
        """Detect JDK from pom.xml."""
        pom_xml = self.repo_root / "pom.xml"
        if not pom_xml.exists():
            return None

        content = pom_xml.read_text()

        # <maven.compiler.source>11</maven.compiler.source>
        match = re.search(r"<maven\.compiler\.source>(\d+)</maven\.compiler\.source>", content)
        if match:
            return {
                "detected_version": int(match.group(1)),
                "confidence": "high",
                "raw_value": match.group(1),
                "file_path": str(pom_xml),
            }

        # <source>11</source> in properties
        match = re.search(r"<source>(\d+)</source>", content)
        if match:
            return {
                "detected_version": int(match.group(1)),
                "confidence": "high",
                "raw_value": match.group(1),
                "file_path": str(pom_xml),
            }

        return None

    def _detect_runtime_jdk(self) -> int | None:
        """Detect JDK from running JVM."""
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stderr or result.stdout

            # Extract version: "openjdk version "11.0.15"" or "java version "1.8.0_302""
            match = re.search(r'version "(\d+)(?:\.(\d+))?', output)
            if match:
                major = int(match.group(1))
                # Handle Java 8 format (version "1.8" means Java 8)
                if major == 1:
                    minor = int(match.group(2)) if match.group(2) else 0
                    return minor
                return major
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def check_compatibility(self, artifact: str, version: str, jdk_version: int) -> dict:
        """
        Check if artifact version is compatible with JDK version.

        Args:
            artifact: Full artifact ID (group:artifact)
            version: Artifact version
            jdk_version: JDK major version (e.g., 11, 17)

        Returns:
        {
            "compatible": True|False,
            "artifact": "group:artifact",
            "version": "1.2.3",
            "jdk_version": 11,
            "min_jdk_required": 8|11|17,
            "reason": "Library requires JDK 17 but repo uses JDK 11"
        }
        """
        # Extract major.minor from version (e.g., "2.23.1" -> "2.23")
        version_parts = version.split(".")
        version_major_minor = f"{version_parts[0]}.{version_parts[1]}" if len(version_parts) >= 2 else version

        # Check if we have requirements for this artifact
        if artifact not in self.MIN_JDK_REQUIREMENTS:
            # No specific requirements known, assume compatible
            return {
                "compatible": True,
                "artifact": artifact,
                "version": version,
                "jdk_version": jdk_version,
                "min_jdk_required": None,
                "reason": "No compatibility constraints known (assume compatible)",
            }

        requirements = self.MIN_JDK_REQUIREMENTS[artifact]

        # Find the closest matching version constraint
        min_jdk = None
        for req_version in sorted(requirements.keys(), reverse=True):
            if version.startswith(req_version):
                min_jdk = requirements[req_version]
                break

        if min_jdk is None:
            # No specific version match; use oldest requirement
            min_jdk = min(requirements.values())

        compatible = jdk_version >= min_jdk

        return {
            "compatible": compatible,
            "artifact": artifact,
            "version": version,
            "jdk_version": jdk_version,
            "min_jdk_required": min_jdk,
            "reason": (
                f"Compatible" if compatible
                else f"Library requires JDK {min_jdk} but repo uses JDK {jdk_version}"
            ),
        }


def main() -> None:
    """CLI for JDK compatibility checking."""
    inp = read_json_input()

    repo_root = inp.get("repo_root")
    mode = inp.get("mode", "detect")  # detect|check
    artifact = inp.get("artifact")
    version = inp.get("version")

    if not repo_root:
        error_exit("repo_root is required", "input_validation")

    validator = JDKCompatibilityValidator(repo_root)

    if mode == "detect":
        progress("Detecting JDK version from repository configuration...")
        jdk_info = validator.detect_jdk_version()
        progress_done(
            f"Detected JDK {jdk_info['detected_version']} "
            f"(source: {jdk_info['source']}, confidence: {jdk_info['confidence']})"
        )
        write_json_output({
            "status": "success",
            "jdk": jdk_info,
        })

    elif mode == "check":
        if not artifact or not version:
            error_exit("artifact and version are required for check mode", "input_validation")

        progress(f"Detecting JDK version...")
        jdk_info = validator.detect_jdk_version()
        jdk_version = jdk_info["detected_version"]

        progress(f"Checking compatibility: {artifact}:{version} with JDK {jdk_version}")
        compatibility = validator.check_compatibility(artifact, version, jdk_version)

        if compatibility["compatible"]:
            progress_done(f"Compatible: {compatibility['reason']}")
        else:
            progress_done(f"Incompatible: {compatibility['reason']}")

        write_json_output({
            "status": "success",
            "jdk": jdk_info,
            "compatibility": compatibility,
        })

    else:
        error_exit(f"Unknown mode: {mode}", "input_validation")


if __name__ == "__main__":
    main()
