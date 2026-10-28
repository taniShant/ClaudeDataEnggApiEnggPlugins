"""Tests for detect_jdk_version.py."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.validators.detect_jdk_version import normalize_jdk_version, detect_jdk_version


class TestNormalizeJDKVersion(TestCase):
    """Test JDK version string normalisation."""

    def test_legacy_1_8(self):
        self.assertEqual(normalize_jdk_version("1.8"), (8, "1.8"))

    def test_legacy_1_7(self):
        self.assertEqual(normalize_jdk_version("1.7"), (7, "1.7"))

    def test_modern_11(self):
        self.assertEqual(normalize_jdk_version("11"), (11, "11"))

    def test_modern_17(self):
        self.assertEqual(normalize_jdk_version("17"), (17, "17"))

    def test_modern_21(self):
        self.assertEqual(normalize_jdk_version("21"), (21, "21"))

    def test_version_enum_1_8(self):
        self.assertEqual(normalize_jdk_version("VERSION_1_8"), (8, "1.8"))

    def test_version_enum_11(self):
        self.assertEqual(normalize_jdk_version("VERSION_11"), (11, "11"))

    def test_version_enum_17(self):
        self.assertEqual(normalize_jdk_version("VERSION_17"), (17, "17"))

    def test_bare_1_8_underscore(self):
        self.assertEqual(normalize_jdk_version("1_8"), (8, "1.8"))

    def test_invalid(self):
        self.assertEqual(normalize_jdk_version("abc"), (None, None))

    def test_empty(self):
        self.assertEqual(normalize_jdk_version(""), (None, None))


class TestDetectJDKVersionGradle(TestCase):
    """Test JDK version detection from Gradle build files."""

    def test_gradle_source_compatibility_1_8(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").write_text("""
plugins { id 'java' }
sourceCompatibility = '1.8'
targetCompatibility = '1.8'
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 8)
            self.assertTrue(result["is_java_project"])
            self.assertIn("build.gradle", result["detection_source"])

    def test_gradle_source_compatibility_11(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").write_text("""
sourceCompatibility = '11'
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 11)

    def test_gradle_java_version_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").write_text("""
sourceCompatibility = JavaVersion.VERSION_17
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 17)

    def test_gradle_kts_jvm_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle.kts").write_text("""
tasks.withType<KotlinCompile> {
    kotlinOptions.jvmTarget = "21"
}
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 21)


class TestDetectJDKVersionMaven(TestCase):
    """Test JDK version detection from Maven pom.xml."""

    def test_maven_compiler_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pom.xml").write_text("""<?xml version="1.0"?>
<project>
    <properties>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
    </properties>
</project>
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 8)
            self.assertTrue(result["is_java_project"])

    def test_maven_compiler_source_11(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pom.xml").write_text("""<?xml version="1.0"?>
<project>
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
    </properties>
</project>
""")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 11)


class TestDetectJDKVersionOtherSources(TestCase):
    """Test JDK version detection from .java-version and gradle.properties."""

    def test_java_version_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".java-version").write_text("1.8\n")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 8)
            self.assertIn(".java-version", result["detection_source"])

    def test_gradle_properties(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "gradle.properties").write_text("javaVersion=17\n")
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 17)


class TestDetectJDKVersionEdgeCases(TestCase):
    """Test edge cases: non-Java projects, missing versions, bad paths, priority."""

    def test_non_java_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "app.py").write_text("print('hello')")
            result = detect_jdk_version(tmp)
            self.assertIsNone(result["jdk_version"])
            self.assertFalse(result["is_java_project"])

    def test_java_files_but_no_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            src.mkdir()
            (src / "Main.java").write_text("public class Main {}")
            result = detect_jdk_version(tmp)
            self.assertIsNone(result["jdk_version"])
            self.assertTrue(result["is_java_project"])

    def test_nonexistent_directory(self):
        result = detect_jdk_version("/tmp/nonexistent-repo-path-xyz-12345")
        self.assertIsNone(result["jdk_version"])
        self.assertFalse(result["is_java_project"])

    def test_gradle_priority_over_maven(self):
        """Gradle detection takes priority over Maven."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "build.gradle").write_text("sourceCompatibility = '11'")
            (Path(tmp) / "pom.xml").write_text(
                "<project><properties>"
                "<maven.compiler.source>1.8</maven.compiler.source>"
                "</properties></project>"
            )
            result = detect_jdk_version(tmp)
            self.assertEqual(result["jdk_version"], 11)
            self.assertIn("build.gradle", result["detection_source"])


if __name__ == "__main__":
    main()
