"""Tests for repo_setup.py."""

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import scripts.git.repo_setup as repo_setup
from scripts.git.repo_setup import (
    is_git_url,
    extract_repo_name,
    find_fresh_dir,
    validate_branch_name,
    generate_branch_name,
    update_gitignore,
    GITIGNORE_ENTRIES,
    MAX_FRESH_DIR_ATTEMPTS,
)

SCRIPTS = Path(__file__).resolve().parent.parent.parent


class TestIsGitUrl(TestCase):
    def test_https(self):
        self.assertTrue(is_git_url("https://app.gitlab.barcapint.com/org/repo.git"))

    def test_git_ssh(self):
        self.assertTrue(is_git_url("git@github.com:org/repo.git"))

    def test_local_path(self):
        self.assertFalse(is_git_url("/home/user/repos/my-repo"))

    def test_relative_path(self):
        self.assertFalse(is_git_url("./my-repo"))


class TestExtractRepoName(TestCase):
    def test_https_with_git_suffix(self):
        self.assertEqual(
            extract_repo_name("https://app.gitlab.barcapint.com/org/my-repo.git"),
            "my-repo",
        )

    def test_https_without_git_suffix(self):
        self.assertEqual(
            extract_repo_name("https://app.gitlab.barcapint.com/org/my-repo"),
            "my-repo",
        )

    def test_ssh_url(self):
        self.assertEqual(
            extract_repo_name("git@github.com:org/my-repo.git"),
            "my-repo",
        )

    def test_empty_path(self):
        self.assertEqual(extract_repo_name("https://example.com/"), "repo")


class TestFindFreshDir(TestCase):
    def test_returns_base_name_if_not_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = find_fresh_dir("my-project", Path(tmp))
            self.assertEqual(result, Path(tmp) / "my-project")

    def test_increments_if_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "my-project").mkdir()
            result = find_fresh_dir("my-project", Path(tmp))
            self.assertEqual(result, Path(tmp) / "my-project-1")

    def test_increments_multiple(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "my-project").mkdir()
            (Path(tmp) / "my-project-1").mkdir()
            (Path(tmp) / "my-project-2").mkdir()
            result = find_fresh_dir("my-project", Path(tmp))
            self.assertEqual(result, Path(tmp) / "my-project-3")


class TestValidateBranchName(TestCase):
    def test_valid_simple(self):
        self.assertTrue(validate_branch_name("feature/my-branch"))

    def test_valid_with_numbers(self):
        self.assertTrue(validate_branch_name("remediate-cwe-89-79-20260429-143000"))

    def test_empty(self):
        self.assertFalse(validate_branch_name(""))

    def test_too_long(self):
        self.assertFalse(validate_branch_name("a" * 256))

    def test_double_dot(self):
        self.assertFalse(validate_branch_name("feature..branch"))

    def test_starts_with_slash(self):
        self.assertFalse(validate_branch_name("/feature"))

    def test_ends_with_slash(self):
        self.assertFalse(validate_branch_name("feature/"))

    def test_space(self):
        self.assertFalse(validate_branch_name("feature branch"))

    def test_tilde(self):
        self.assertFalse(validate_branch_name("feature~1"))

    def test_caret(self):
        self.assertFalse(validate_branch_name("feature^1"))

    def test_colon(self):
        self.assertFalse(validate_branch_name("feature:branch"))

    def test_question_mark(self):
        self.assertFalse(validate_branch_name("feature?"))

    def test_asterisk(self):
        self.assertFalse(validate_branch_name("feature*"))

    def test_backslash(self):
        self.assertFalse(validate_branch_name("feature\\branch"))

    def test_dot_lock_ending(self):
        self.assertFalse(validate_branch_name("feature.lock"))


class TestGenerateBranchName(TestCase):
    def test_single_cwe(self):
        branch = generate_branch_name(["CWE-89"])
        self.assertIn("remediate-cwe-89-", branch)

    def test_multiple_cwes_sorted(self):
        branch = generate_branch_name(["CWE-89", "CWE-79", "CWE-22"])
        # Should be sorted: 22-79-89
        self.assertIn("22-79-89", branch)

    def test_deduplicates(self):
        branch = generate_branch_name(["CWE-89", "CWE-89"])
        # Should only appear once
        self.assertEqual(branch.count("89"), 1)

    def test_truncates_long_list(self):
        cwes = [f"CWE-{i}" for i in range(1, 50)]
        branch = generate_branch_name(cwes)
        self.assertLessEqual(len(branch), 150)


class TestUpdateGitignore(TestCase):
    def test_creates_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            result = update_gitignore(repo_dir)
            self.assertTrue(result)
            content = (repo_dir / ".gitignore").read_text()
            for entry in GITIGNORE_ENTRIES:
                self.assertIn(entry, content)

    def test_appends_missing_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            gitignore = repo_dir / ".gitignore"
            gitignore.write_text("node_modules/\n")
            result = update_gitignore(repo_dir)
            self.assertTrue(result)
            content = gitignore.read_text()
            self.assertIn("node_modules/", content)
            for entry in GITIGNORE_ENTRIES:
                self.assertIn(entry, content)

    def test_no_change_if_already_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            gitignore = repo_dir / ".gitignore"
            gitignore.write_text("\n".join(GITIGNORE_ENTRIES) + "\n")
            result = update_gitignore(repo_dir)
            self.assertFalse(result)

    def test_ignores_detox_state_dir(self):
        # .detox/ holds pipeline-state.json and the Wiz baseline scan — never commit it.
        self.assertIn(".detox/", GITIGNORE_ENTRIES)

    def test_adds_newline_if_file_doesnt_end_with_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)
            gitignore = repo_dir / ".gitignore"
            gitignore.write_text("node_modules/")  # No trailing newline
            update_gitignore(repo_dir)
            content = gitignore.read_text()
            # Should have newline before detox entries
            self.assertIn("node_modules/\n", content)


class TestBarclaysSetupHardGate(TestCase):
    """repo_setup.main() must HARD-BLOCK (exit non-zero) when the mandatory
    Barclays user setup is incomplete — the code-level backstop that does not
    depend on the orchestrator agent following Stage 0 prose."""

    ALL = ("barclays_user_id=B01,barclays_cio=DIGITAL,"
           "barclays_team=OB,barclays_user_email=x@y.com")
    NO_CIO = "barclays_user_id=B01,barclays_team=OB,barclays_user_email=x@y.com"

    def _run_main(self, payload: dict):
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        code = None
        with patch.object(sys, "stdin", stdin), patch.object(sys, "stdout", stdout):
            try:
                repo_setup.main()
            except SystemExit as e:
                code = e.code
        parsed = None
        for line in stdout.getvalue().strip().splitlines():
            try:
                parsed = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
        return parsed, code

    def test_missing_cio_blocks(self):
        with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": self.NO_CIO}):
            parsed, code = self._run_main({"repo_url": "."})
        self.assertEqual(code, 1)
        self.assertEqual(parsed.get("stage"), "barclays_setup")
        self.assertIn("barclays_cio", parsed.get("error", ""))

    def test_no_setup_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True), \
                 patch("scripts.utils.common.Path.home", return_value=Path(tmp)):
                parsed, code = self._run_main({"repo_url": "."})
        self.assertEqual(code, 1)
        self.assertEqual(parsed.get("stage"), "barclays_setup")

    def test_skip_flag_bypasses_gate(self):
        with patch.dict(os.environ, {}, clear=True):
            parsed, code = self._run_main({"skip_barclays_setup": True, "repo_url": ""})
        self.assertEqual(parsed.get("stage"), "input_validation")

    def test_complete_setup_passes_gate(self):
        with patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": self.ALL}):
            parsed, code = self._run_main({"repo_url": ""})
        self.assertNotEqual(parsed.get("stage"), "barclays_setup")


class TestRepoSetupBaseBranch(TestCase):
    def _git(self, *args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    def _setup(self, repo, extra=None):
        inp = {"repo_url": repo, **(extra or {})}
        out = subprocess.run([sys.executable, str(SCRIPTS / "git" / "repo_setup.py")],
                             input=json.dumps(inp), capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout)

    def _repo(self, tmp, branch):
        self._git("init", "-q", "-b", branch, cwd=tmp)
        self._git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "i", cwd=tmp)

    def test_local_repo_reports_checked_out_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp, "release/1.3.1")
            with patch.dict("os.environ", {}):
                out = self._setup(tmp, {"skip_barclays_setup": True})
            self.assertEqual(out.get("status"), "success", out)
            self.assertEqual(out["base_branch"], "release/1.3.1")

    def test_explicit_base_branch_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp, "develop")
            out = self._setup(tmp, {"skip_barclays_setup": True, "base_branch": "main"})
            self.assertEqual(out["base_branch"], "main")


if __name__ == "__main__":
    main()
