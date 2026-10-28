"""Tests for atomic_commit.py."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.git.atomic_commit import (
    build_subject,
    is_secret_file,
    SECRET_FILE_NAMES,
    SECRET_FILE_EXTENSIONS,
)

SCRIPTS = Path(__file__).resolve().parent.parent.parent


class TestBuildSubject(TestCase):
    """Commit subjects stay within 72 chars and never cut a word in half."""

    def test_short_description_unchanged(self):
        self.assertEqual(build_subject("CWE-89", "Parameterize SQL"), "fix(CWE-89): Parameterize SQL")

    def test_jira_prefix(self):
        self.assertEqual(build_subject("CWE-89", "Fix", "ABC-1"), "ABC-1 fix(CWE-89): Fix")

    def test_long_description_cut_at_word_boundary(self):
        desc = "Upgrade jackson-databind to 2.18.10 to fix Jackson 8 CVEs (com.fasterxml.jackson.core)"
        subject = build_subject("CWE-937", desc)
        self.assertLessEqual(len(subject), 72)
        self.assertTrue(subject.endswith("..."))
        body = subject[len("fix(CWE-937): "):-3]
        self.assertTrue(desc.startswith(body))
        # The cut lands on a word boundary of the original description
        self.assertEqual(desc[len(body)], " ")
        self.assertNotIn("(com.fa", subject)

    def test_single_long_word_hard_cut(self):
        subject = build_subject("CWE-937", "x" * 100)
        self.assertEqual(len(subject), 72)
        self.assertTrue(subject.endswith("..."))

    def test_exactly_72_chars_unchanged(self):
        head = "fix(CWE-79): "
        desc = "a" * (72 - len(head))
        self.assertEqual(build_subject("CWE-79", desc), head + desc)


class TestIsSecretFile(TestCase):
    """Test secret file detection patterns."""

    def test_env_file(self):
        self.assertTrue(is_secret_file(".env"))

    def test_env_local(self):
        self.assertTrue(is_secret_file(".env.local"))

    def test_env_production(self):
        self.assertTrue(is_secret_file(".env.production"))

    def test_env_custom(self):
        # .env.* pattern
        self.assertTrue(is_secret_file(".env.staging"))

    def test_credentials_json(self):
        self.assertTrue(is_secret_file("credentials.json"))

    def test_secrets_json(self):
        self.assertTrue(is_secret_file("secrets.json"))

    def test_service_account(self):
        self.assertTrue(is_secret_file("service-account.json"))

    def test_id_rsa(self):
        self.assertTrue(is_secret_file("id_rsa"))

    def test_id_ed25519(self):
        self.assertTrue(is_secret_file("id_ed25519"))

    def test_pem_extension(self):
        self.assertTrue(is_secret_file("server.pem"))

    def test_key_extension(self):
        self.assertTrue(is_secret_file("private.key"))

    def test_p12_extension(self):
        self.assertTrue(is_secret_file("cert.p12"))

    def test_pfx_extension(self):
        self.assertTrue(is_secret_file("cert.pfx"))

    def test_jks_extension(self):
        self.assertTrue(is_secret_file("keystore.jks"))

    def test_keystore_extension(self):
        self.assertTrue(is_secret_file("app.keystore"))

    def test_htpasswd(self):
        self.assertTrue(is_secret_file(".htpasswd"))

    def test_netrc(self):
        self.assertTrue(is_secret_file(".netrc"))

    # Non-secret files
    def test_normal_python(self):
        self.assertFalse(is_secret_file("main.py"))

    def test_normal_json(self):
        self.assertFalse(is_secret_file("package.json"))

    def test_normal_config(self):
        self.assertFalse(is_secret_file("config.yaml"))

    def test_normal_js(self):
        self.assertFalse(is_secret_file("index.js"))

    def test_readme(self):
        self.assertFalse(is_secret_file("README.md"))

    def test_path_with_directory(self):
        self.assertTrue(is_secret_file("/home/user/.env"))

    def test_path_with_directory_non_secret(self):
        self.assertFalse(is_secret_file("/home/user/app.py"))

    def test_case_insensitive(self):
        # Uppercase should still match (names lowercased in function)
        self.assertTrue(is_secret_file(".ENV"))
        self.assertTrue(is_secret_file("CREDENTIALS.JSON"))


class TestSecretPatternCompleteness(TestCase):
    """Verify pattern sets are non-empty and well-formed."""

    def test_names_set_non_empty(self):
        self.assertGreater(len(SECRET_FILE_NAMES), 5)

    def test_extensions_set_non_empty(self):
        self.assertGreater(len(SECRET_FILE_EXTENSIONS), 3)

    def test_extensions_all_start_with_dot(self):
        for ext in SECRET_FILE_EXTENSIONS:
            self.assertTrue(ext.startswith("."), f"Extension missing dot: {ext}")


class TestAtomicCommitTrailer(TestCase):
    # Server-side push checks require the Co-Authored-By trailer on every commit.
    def _git(self, *args, cwd):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    def test_commit_message_ends_with_co_author_trailer(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._git("init", "-q", "-b", "main", cwd=tmp)
            self._git("config", "user.email", "t@t", cwd=tmp)
            self._git("config", "user.name", "t", cwd=tmp)
            fixed = Path(tmp) / "app.py"
            fixed.write_text("x = 1\n")
            inp = {"cwe_id": "CWE-89", "files": [str(fixed)], "description": "Parameterize SQL query",
                   "repo_dir": tmp, "verification_result": {"verdict": "PASS"}}
            out = subprocess.run([sys.executable, str(SCRIPTS / "git" / "atomic_commit.py")],
                                 input=json.dumps(inp), capture_output=True, text=True, timeout=60)
            self.assertEqual(json.loads(out.stdout)["status"], "success", out.stderr)
            message = self._git("log", "-1", "--format=%B", cwd=tmp).stdout.strip()
            self.assertEqual(message.splitlines()[-1], "Co-Authored-By: Claude")


if __name__ == "__main__":
    main()
