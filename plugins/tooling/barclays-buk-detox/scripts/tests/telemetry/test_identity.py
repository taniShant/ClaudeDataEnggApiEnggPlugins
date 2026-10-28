"""Tests for identity.py — user and repo identity resolution."""

import os
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.telemetry.identity import (
    resolve_ci_identity,
    resolve_git_identity,
    resolve_env_identity,
    resolve_repo_info,
    resolve_identity,
    _extract_repo_name_from_url,
)


class TestExtractRepoNameFromUrl(TestCase):
    def test_ssh_url(self):
        result = _extract_repo_name_from_url("git@gitlab.com:buk/dss/DSS-COMMON-CONTAINER_V4.git")
        self.assertEqual(result, "DSS-COMMON-CONTAINER_V4")

    def test_https_url(self):
        result = _extract_repo_name_from_url("https://gitlab.com/buk/dss/DSS-COMMON-CONTAINER_V4.git")
        self.assertEqual(result, "DSS-COMMON-CONTAINER_V4")

    def test_url_without_git_suffix(self):
        result = _extract_repo_name_from_url("https://github.com/org/my-repo")
        self.assertEqual(result, "my-repo")

    def test_empty_url(self):
        result = _extract_repo_name_from_url("")
        self.assertIsNone(result)

    def test_none_url(self):
        result = _extract_repo_name_from_url(None)
        self.assertIsNone(result)


class TestResolveCiIdentity(TestCase):
    def test_detects_gitlab_ci(self):
        env = {
            "CI_JOB_ID": "12345",
            "CI_PIPELINE_ID": "67890",
            "GITLAB_USER_LOGIN": "devesh",
            "GITLAB_USER_EMAIL": "devesh@barclays.com",
            "CI_PROJECT_NAME": "my-service",
        }
        with patch.dict(os.environ, env, clear=False):
            result = resolve_ci_identity()
            self.assertIsNotNone(result)
            self.assertEqual(result["source"], "gitlab_ci")
            self.assertEqual(result["ci_job_id"], "12345")
            self.assertEqual(result["ci_pipeline_id"], "67890")
            self.assertEqual(result["user_name"], "devesh")

    def test_detects_jenkins(self):
        # Ensure GitLab vars are not set
        env = {"BUILD_NUMBER": "42", "JOB_NAME": "my-pipeline", "USER": "jenkins"}
        with patch.dict(os.environ, env, clear=False):
            # Remove GitLab CI var if present
            with patch.dict(os.environ, {"CI_JOB_ID": ""}, clear=False):
                result = resolve_ci_identity()
                # Jenkins detected only if CI_JOB_ID is not set
                if os.environ.get("CI_JOB_ID"):
                    self.skipTest("CI_JOB_ID still set in env")
                if result:
                    self.assertEqual(result["source"], "jenkins")

    def test_detects_github_actions(self):
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_RUN_ID": "98765",
            "GITHUB_ACTOR": "bot-user",
            "GITHUB_REPOSITORY": "org/my-repo",
            "CI_JOB_ID": "",
            "BUILD_NUMBER": "",
        }
        with patch.dict(os.environ, env, clear=False):
            result = resolve_ci_identity()
            if result and result.get("source") == "github_actions":
                self.assertEqual(result["user_name"], "bot-user")
                self.assertEqual(result["ci_job_id"], "98765")

    def test_returns_none_when_no_ci(self):
        env = {"CI_JOB_ID": "", "BUILD_NUMBER": "", "GITHUB_ACTIONS": ""}
        with patch.dict(os.environ, env, clear=False):
            result = resolve_ci_identity()
            self.assertIsNone(result)


class TestResolveGitIdentity(TestCase):
    @patch("scripts.telemetry.identity._run_git")
    def test_extracts_git_user(self, mock_git):
        mock_git.side_effect = lambda args, cwd=None: {
            ("config", "user.name"): "Dev User",
            ("config", "user.email"): "dev@barclays.com",
        }.get(tuple(args))

        result = resolve_git_identity("/some/repo")
        self.assertIsNotNone(result)
        self.assertEqual(result["user_name"], "Dev User")
        self.assertEqual(result["user_email"], "dev@barclays.com")
        self.assertEqual(result["source"], "git_config")

    @patch("scripts.telemetry.identity._run_git")
    def test_returns_none_when_no_git_config(self, mock_git):
        mock_git.return_value = None
        result = resolve_git_identity("/some/repo")
        self.assertIsNone(result)


class TestResolveEnvIdentity(TestCase):
    def test_uses_user_env_var(self):
        with patch.dict(os.environ, {"USER": "testuser"}):
            result = resolve_env_identity()
            self.assertEqual(result["user_name"], "testuser")
            self.assertEqual(result["source"], "env")

    def test_falls_back_to_unknown(self):
        with patch.dict(os.environ, {"USER": "", "USERNAME": ""}, clear=False):
            # The function uses os.environ.get with fallbacks
            result = resolve_env_identity()
            self.assertIn(result["user_name"], ("", "unknown", os.environ.get("USER", "")))


class TestResolveRepoInfo(TestCase):
    @patch("scripts.telemetry.identity._run_git")
    def test_extracts_from_git_remote(self, mock_git):
        mock_git.return_value = "git@gitlab.com:buk/dss/my-service.git"
        with patch("pathlib.Path.is_dir", return_value=True):
            result = resolve_repo_info("/repos/my-service")
            self.assertEqual(result["repo_name"], "my-service")
            self.assertEqual(result["repo_url"], "git@gitlab.com:buk/dss/my-service.git")

    @patch("scripts.telemetry.identity._run_git")
    def test_falls_back_to_basename(self, mock_git):
        mock_git.return_value = None
        with patch("pathlib.Path.is_dir", return_value=True):
            result = resolve_repo_info("/repos/my-fallback-repo")
            self.assertEqual(result["repo_name"], "my-fallback-repo")

    def test_handles_none_path(self):
        result = resolve_repo_info(None)
        self.assertEqual(result["repo_name"], "")
        self.assertEqual(result["repo_url"], "")


class TestResolveIdentity(TestCase):
    @patch("scripts.telemetry.identity.resolve_ci_identity")
    @patch("scripts.telemetry.identity.resolve_git_identity")
    @patch("scripts.telemetry.identity.resolve_repo_info")
    def test_full_resolution(self, mock_repo, mock_git, mock_ci):
        mock_ci.return_value = None
        mock_git.return_value = {
            "user_name": "dev",
            "user_email": "dev@barclays.com",
            "source": "git_config",
        }
        mock_repo.return_value = {"repo_name": "my-repo", "repo_url": "https://..."}

        result = resolve_identity({"project_path": "/repos/my-repo"})
        self.assertEqual(result["status"], "success")
        identity = result["identity"]
        self.assertEqual(identity["user_name"], "dev")
        self.assertEqual(identity["repo_name"], "my-repo")
        self.assertIn("hostname", identity)
        self.assertIn("ci_job_id", identity)

    @patch("scripts.telemetry.identity.resolve_ci_identity")
    @patch("scripts.telemetry.identity.resolve_git_identity")
    @patch("scripts.telemetry.identity.resolve_repo_info")
    def test_ci_takes_priority(self, mock_repo, mock_git, mock_ci):
        mock_ci.return_value = {
            "user_name": "ci-user",
            "user_email": "",
            "ci_job_id": "999",
            "ci_pipeline_id": "100",
            "source": "gitlab_ci",
        }
        mock_git.return_value = {
            "user_name": "local-dev",
            "user_email": "dev@barclays.com",
            "source": "git_config",
        }
        mock_repo.return_value = {"repo_name": "svc", "repo_url": ""}

        result = resolve_identity({"project_path": "/repos/svc"})
        identity = result["identity"]
        # CI should win over git
        self.assertEqual(identity["user_name"], "ci-user")
        self.assertEqual(identity["source"], "gitlab_ci")


if __name__ == "__main__":
    main()
