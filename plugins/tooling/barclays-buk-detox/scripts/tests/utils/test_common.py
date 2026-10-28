"""Tests for common.py shared utilities."""

import json
import os
import sys
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.utils.common import (
    claude_config_dir,
    load_barclays_attributes,
    sanitize_pat,
    write_json_output,
    resolve_path,
    shell_quote,
    progress,
    progress_done,
    SEVERITY_ORDER,
    SEVERITY_LEVELS,
)


class TestSanitizePat(TestCase):
    def test_removes_pat_from_text(self):
        with patch.dict(os.environ, {"GIT_PAT": "secret123token"}):
            result = sanitize_pat("Cloning with token secret123token in URL")
            self.assertNotIn("secret123token", result)
            self.assertIn("***REDACTED***", result)

    def test_no_pat_returns_unchanged(self):
        with patch.dict(os.environ, {"GIT_PAT": ""}):
            text = "No token here"
            result = sanitize_pat(text)
            self.assertEqual(result, text)

    def test_custom_env_var(self):
        with patch.dict(os.environ, {"CUSTOM_PAT": "mytoken"}):
            result = sanitize_pat("auth mytoken used", "CUSTOM_PAT")
            self.assertNotIn("mytoken", result)
            self.assertIn("***REDACTED***", result)

    def test_pat_not_in_text_returns_unchanged(self):
        with patch.dict(os.environ, {"GIT_PAT": "secret123"}):
            result = sanitize_pat("no match here")
            self.assertEqual(result, "no match here")

    def test_gitlab_token_env_var_redacted(self):
        with patch.dict(os.environ, {"GITLAB_TOKEN": "gl_secret_abc", "GIT_PAT": ""}):
            result = sanitize_pat("token is gl_secret_abc here")
            self.assertNotIn("gl_secret_abc", result)
            self.assertIn("***REDACTED***", result)

    def test_github_token_env_var_redacted(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "gh_tok_xyz", "GIT_PAT": ""}):
            result = sanitize_pat("using gh_tok_xyz for auth")
            self.assertNotIn("gh_tok_xyz", result)
            self.assertIn("***REDACTED***", result)

    def test_glpat_pattern_redacted(self):
        with patch.dict(os.environ, {"GIT_PAT": ""}):
            token = "glpat-" + "a" * 30
            result = sanitize_pat(f"Authorization: Bearer {token}")
            self.assertNotIn(token, result)
            self.assertIn("***REDACTED***", result)

    def test_ghp_pattern_redacted(self):
        with patch.dict(os.environ, {"GIT_PAT": ""}):
            token = "ghp_" + "A" * 36
            result = sanitize_pat(f"token={token}")
            self.assertNotIn(token, result)
            self.assertIn("***REDACTED***", result)

    def test_short_glpat_not_redacted(self):
        """Tokens shorter than 20 chars after prefix should not match (avoid false positives)."""
        with patch.dict(os.environ, {"GIT_PAT": ""}):
            short_token = "glpat-short"
            result = sanitize_pat(f"value={short_token}")
            self.assertIn(short_token, result)


class TestRunCmdLogSanitization(TestCase):
    """Verify that run_cmd sanitizes PAT values from log output (M1 fix)."""

    def test_pat_not_logged_in_verbose_mode(self):
        """When DETOX_VERBOSE is set and cmd contains PAT, it should be redacted."""
        import io
        from scripts.utils.common import run_cmd

        with patch.dict(os.environ, {"DETOX_VERBOSE": "1", "GIT_PAT": "supersecretpat"}):
            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                run_cmd(
                    ["git", "-c", "http.extraHeader=Authorization: Bearer supersecretpat", "status"],
                    timeout=5,
                )
            logged = stderr_capture.getvalue()
            self.assertNotIn("supersecretpat", logged)
            if logged:  # Only check if verbose logging produced output
                self.assertIn("***REDACTED***", logged)


class TestWriteJsonOutputDurationMs(TestCase):
    def test_includes_duration_ms_when_start_time_provided(self):
        import time
        start = time.time() - 0.05  # 50ms ago
        captured = StringIO()
        with patch("sys.stdout", captured):
            write_json_output({"status": "success"}, start_time=start)
        result = json.loads(captured.getvalue())
        self.assertIn("duration_ms", result)
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)

    def test_no_duration_ms_when_start_time_not_provided(self):
        captured = StringIO()
        with patch("sys.stdout", captured):
            write_json_output({"status": "success"})
        result = json.loads(captured.getvalue())
        self.assertNotIn("duration_ms", result)

    def test_duration_ms_not_added_to_non_dict(self):
        captured = StringIO()
        with patch("sys.stdout", captured):
            write_json_output([1, 2, 3], start_time=0.0)
        result = json.loads(captured.getvalue())
        self.assertEqual(result, [1, 2, 3])


class TestShellQuote(TestCase):
    def test_safe_string(self):
        result = shell_quote("hello")
        self.assertEqual(result, "hello")

    def test_string_with_spaces(self):
        result = shell_quote("hello world")
        self.assertIn("hello world", result)
        # Should be quoted
        self.assertTrue(result.startswith("'") or result.startswith('"'))

    def test_string_with_special_chars(self):
        result = shell_quote("$(rm -rf /)")
        self.assertNotEqual(result, "$(rm -rf /)")


class TestResolvePath(TestCase):
    def test_absolute_path_unchanged(self):
        result = resolve_path("/tmp/foo")
        self.assertEqual(result, "/tmp/foo")

    def test_relative_with_root(self):
        result = resolve_path("src/main.py", "/home/user/project")
        self.assertEqual(result, "/home/user/project/src/main.py")

    def test_relative_without_root(self):
        result = resolve_path("src/main.py")
        self.assertTrue(Path(result).is_absolute())


class TestProgress(TestCase):
    def test_progress_writes_to_stderr(self):
        captured = StringIO()
        with patch("sys.stderr", captured):
            progress("Parsing report...")
        output = captured.getvalue()
        self.assertIn("[DETOX]", output)
        self.assertIn("▸", output)
        self.assertIn("Parsing report...", output)

    def test_progress_done_writes_to_stderr(self):
        captured = StringIO()
        with patch("sys.stderr", captured):
            progress_done("Build passed")
        output = captured.getvalue()
        self.assertIn("[DETOX]", output)
        self.assertIn("✓", output)
        self.assertIn("Build passed", output)

    def test_progress_does_not_write_to_stdout(self):
        stdout_captured = StringIO()
        with patch("sys.stdout", stdout_captured):
            progress("should not appear on stdout")
        self.assertEqual(stdout_captured.getvalue(), "")

    def test_progress_done_does_not_write_to_stdout(self):
        stdout_captured = StringIO()
        with patch("sys.stdout", stdout_captured):
            progress_done("should not appear on stdout")
        self.assertEqual(stdout_captured.getvalue(), "")

    def test_progress_not_gated_by_env_var(self):
        captured = StringIO()
        with patch.dict(os.environ, {"DETOX_VERBOSE": ""}, clear=False):
            with patch("sys.stderr", captured):
                progress("always visible")
        self.assertIn("always visible", captured.getvalue())


class TestConstants(TestCase):
    def test_severity_order_completeness(self):
        for level in SEVERITY_LEVELS:
            self.assertIn(level, SEVERITY_ORDER)

    def test_severity_ordering(self):
        self.assertGreater(SEVERITY_ORDER["critical"], SEVERITY_ORDER["high"])
        self.assertGreater(SEVERITY_ORDER["high"], SEVERITY_ORDER["medium"])
        self.assertGreater(SEVERITY_ORDER["medium"], SEVERITY_ORDER["low"])
        self.assertGreater(SEVERITY_ORDER["low"], SEVERITY_ORDER["info"])


class TestClaudeConfigDir(TestCase):
    def test_defaults_to_home_dot_claude(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
            self.assertEqual(claude_config_dir(), Path.home() / ".claude")

    def test_honours_claude_config_dir(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/tmp/cfg"}):
            self.assertEqual(claude_config_dir(), Path("/tmp/cfg"))

    def test_barclays_attributes_read_from_config_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "settings.json").write_text(json.dumps(
                {"env": {"OTEL_RESOURCE_ATTRIBUTES": "barclays_cio=BUK,other=x"}}))
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": d}):
                os.environ.pop("OTEL_RESOURCE_ATTRIBUTES", None)
                self.assertEqual(load_barclays_attributes(), {"barclays_cio": "BUK"})


    def test_barclays_attributes_fall_back_to_home(self):
        # Setup script wrote ~/.claude/settings.json; CLAUDE_CONFIG_DIR points elsewhere.
        import tempfile
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cfg:
            Path(home, ".claude").mkdir()
            Path(home, ".claude", "settings.json").write_text(json.dumps(
                {"env": {"OTEL_RESOURCE_ATTRIBUTES": "barclays_cio=BUK"}}))
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg}), \
                 patch("scripts.utils.common.Path.home", return_value=Path(home)):
                os.environ.pop("OTEL_RESOURCE_ATTRIBUTES", None)
                self.assertEqual(load_barclays_attributes(), {"barclays_cio": "BUK"})

    def test_barclays_gate_blocks_when_setup_missing(self):
        import tempfile
        from scripts.utils.common import check_barclays_setup
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cfg:
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg}), \
                 patch("scripts.utils.common.Path.home", return_value=Path(home)):
                os.environ.pop("OTEL_RESOURCE_ATTRIBUTES", None)
                result = check_barclays_setup()
        self.assertFalse(result["available"])
        self.assertEqual(len(result["missing_keys"]), 4)


if __name__ == "__main__":
    main()
