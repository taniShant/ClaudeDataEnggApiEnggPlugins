"""Tests for resolve_skill.py."""

import re
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.utils.resolve_skill import (
    CWE_DIR, SKILLS_DIR, resolve_cwe, resolve_language, resolve_named,
)


class TestResolveCwe(TestCase):
    def test_zero_padded_folder(self):
        self.assertTrue(resolve_cwe("CWE-79")["path"].endswith("cwe-079-xss/SKILL.md"))

    def test_unpadded_folder_not_confused_with_padded(self):
        self.assertIn("cwe-95-code-injection", resolve_cwe("CWE-95")["path"])
        self.assertIn("cwe-094-code-injection", resolve_cwe("94")["path"])

    def test_four_digit_folder(self):
        self.assertIn("cwe-1188-", resolve_cwe("cwe-1188")["path"])

    def test_unknown_cwe_uses_fallback(self):
        r = resolve_cwe("CWE-99999")
        self.assertTrue(r["fallback"])
        self.assertTrue(r["path"].endswith("cwe-generic-fallback/SKILL.md"))

    def test_every_cwe_folder_resolves_to_itself(self):
        for d in CWE_DIR.glob("cwe-*"):
            m = re.match(r"cwe-(\d+)-", d.name)
            if m:
                self.assertEqual(resolve_cwe(m.group(1))["path"], str(d / "SKILL.md"))


class TestResolveLanguageAndNamed(TestCase):
    def test_language_alias(self):
        self.assertTrue(resolve_language("TS")["path"].endswith("typescript-fix-patterns/SKILL.md"))

    def test_unknown_language(self):
        self.assertIsNone(resolve_language("cobol")["path"])

    def test_named_skill(self):
        self.assertEqual(resolve_named("analysis/dependency-analyzer")["path"],
                         str((SKILLS_DIR / "analysis/dependency-analyzer/SKILL.md").resolve()))

    def test_named_skill_rejects_traversal(self):
        self.assertIsNone(resolve_named("../../etc")["path"])


if __name__ == "__main__":
    main()
