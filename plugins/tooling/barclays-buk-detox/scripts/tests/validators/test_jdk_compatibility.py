"""Tests for JDK compatibility validator."""

import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.jdk_compatibility import JDKCompatibilityValidator


class TestJDKCompatibilityValidator(TestCase):
    def test_detect_gradle_jdk_source_compatibility(self):
        """Test detecting JDK from Gradle sourceCompatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            build_gradle = Path(tmpdir) / "build.gradle"
            build_gradle.write_text("""
plugins {
    id 'java'
}

sourceCompatibility = '11'

dependencies {
    implementation 'org.springframework:spring-core:5.3.0'
}
""")
            validator = JDKCompatibilityValidator(tmpdir)
            result = validator._detect_gradle_jdk()

            self.assertIsNotNone(result)
            self.assertEqual(result["detected_version"], 11)
            self.assertEqual(result["confidence"], "high")

    def test_detect_maven_jdk_compiler_source(self):
        """Test detecting JDK from Maven compiler.source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pom_xml = Path(tmpdir) / "pom.xml"
            pom_xml.write_text("""<?xml version="1.0"?>
<project>
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
    </properties>
</project>
""")
            validator = JDKCompatibilityValidator(tmpdir)
            result = validator._detect_maven_jdk()

            self.assertIsNotNone(result)
            self.assertEqual(result["detected_version"], 17)
            self.assertEqual(result["confidence"], "high")

    def test_detect_jdk_default_fallback(self):
        """Test default fallback when no JDK detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = JDKCompatibilityValidator(tmpdir)
            result = validator.detect_jdk_version()

            # If Java is available, it will detect that; otherwise falls back to 8
            self.assertIn(result["detected_version"], [8, 11, 17, 21])
            self.assertIn(result["source"], ["default", "runtime"])

    def test_check_compatibility_spring_webmvc_jdk8(self):
        """Test Spring WebMVC 5.3 compatibility with JDK 8."""
        validator = JDKCompatibilityValidator(".")
        result = validator.check_compatibility(
            "org.springframework:spring-webmvc", "5.3.39", 8
        )

        self.assertTrue(result["compatible"])
        self.assertEqual(result["min_jdk_required"], 8)

    def test_check_compatibility_spring_webmvc_jdk6_fails(self):
        """Test Spring WebMVC 5.3 incompatibility with JDK 6."""
        validator = JDKCompatibilityValidator(".")
        result = validator.check_compatibility(
            "org.springframework:spring-webmvc", "5.3.39", 6
        )

        self.assertFalse(result["compatible"])
        self.assertEqual(result["min_jdk_required"], 8)

    def test_check_compatibility_spring_6_requires_java17(self):
        """Test Spring 6.0 requires JDK 17."""
        validator = JDKCompatibilityValidator(".")
        result = validator.check_compatibility(
            "org.springframework:spring-core", "6.0.0", 11
        )

        self.assertFalse(result["compatible"])
        self.assertEqual(result["min_jdk_required"], 17)

    def test_check_compatibility_spring_6_with_java17(self):
        """Test Spring 6.0 compatibility with JDK 17."""
        validator = JDKCompatibilityValidator(".")
        result = validator.check_compatibility(
            "org.springframework:spring-core", "6.0.0", 17
        )

        self.assertTrue(result["compatible"])
        self.assertEqual(result["min_jdk_required"], 17)

    def test_check_compatibility_unknown_artifact(self):
        """Test unknown artifact assumes compatible."""
        validator = JDKCompatibilityValidator(".")
        result = validator.check_compatibility(
            "com.unknown:unknown-lib", "1.0.0", 8
        )

        self.assertTrue(result["compatible"])
        self.assertIsNone(result["min_jdk_required"])

    def test_check_compatibility_jackson_all_versions(self):
        """Test Jackson compatibility across versions."""
        validator = JDKCompatibilityValidator(".")

        # Jackson 2.15+ requires JDK 8
        for version in ["2.15.0", "2.16.0", "2.17.0", "2.18.0", "2.19.4"]:
            result = validator.check_compatibility(
                "com.fasterxml.jackson.core:jackson-databind", version, 8
            )
            self.assertTrue(result["compatible"], f"Jackson {version} should work with JDK 8")

    def test_check_compatibility_tomcat_versions(self):
        """Test Tomcat version compatibility."""
        validator = JDKCompatibilityValidator(".")

        # Tomcat 9.0 requires JDK 8
        result = validator.check_compatibility(
            "org.apache.tomcat.embed:tomcat-embed-core", "9.0.121", 8
        )
        self.assertTrue(result["compatible"])

        # Tomcat 10.0 requires JDK 11
        result = validator.check_compatibility(
            "org.apache.tomcat.embed:tomcat-embed-core", "10.0.0", 11
        )
        self.assertTrue(result["compatible"])

        result = validator.check_compatibility(
            "org.apache.tomcat.embed:tomcat-embed-core", "10.0.0", 8
        )
        self.assertFalse(result["compatible"])

        # Tomcat 11.0 requires JDK 17
        result = validator.check_compatibility(
            "org.apache.tomcat.embed:tomcat-embed-core", "11.0.0", 17
        )
        self.assertTrue(result["compatible"])

        result = validator.check_compatibility(
            "org.apache.tomcat.embed:tomcat-embed-core", "11.0.0", 11
        )
        self.assertFalse(result["compatible"])


if __name__ == "__main__":
    main()
