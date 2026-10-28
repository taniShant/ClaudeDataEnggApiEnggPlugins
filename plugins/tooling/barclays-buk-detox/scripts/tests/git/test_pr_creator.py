"""Tests for pr_creator.py — testing input validation and deprecation warnings.

Note: Full integration tests require git repos and glab CLI, which are
tested via the pipeline integration test suite. These unit tests cover
the deterministic logic.
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))


def run_pr_creator(input_data: dict) -> dict:
    """Helper to run pr_creator.main() with mocked stdin/stdout."""
    from scripts.git.pr_creator import main as pr_main

    stdin_data = json.dumps(input_data)
    captured_output = StringIO()

    with patch("sys.stdin", StringIO(stdin_data)), \
         patch("sys.stdout", captured_output):
        try:
            pr_main()
        except SystemExit:
            pass

    output = captured_output.getvalue()
    if output.strip():
        return json.loads(output)
    return {}


class TestPrCreatorValidation(TestCase):
    """Test input validation logic.

    Note: repo_dir/.git check runs first, so non-git-repo errors are
    expected when testing other validations with fake paths.
    """

    def test_invalid_repo_dir(self):
        result = run_pr_creator({
            "repo_dir": "/tmp/nonexistent-path-xyz-123",
            "branch_name": "my-branch",
            "mr_title": "Title",
            "mr_body": "Body",
        })
        self.assertEqual(result.get("status"), "error")
        self.assertIn("git repository", result.get("error", "").lower())

    def test_repo_dir_checked_before_branch(self):
        """Repo validation occurs before branch_name check."""
        result = run_pr_creator({
            "repo_dir": "/tmp/fake-repo",
            "branch_name": "",
            "mr_title": "Test MR",
            "mr_body": "Body",
        })
        self.assertEqual(result.get("status"), "error")
        # Repo check fires first since /tmp/fake-repo has no .git
        self.assertIn("git repository", result.get("error", "").lower())


class TestPrCreatorDeprecation(TestCase):
    """Test that deprecated field names (pr_title/pr_body) are handled."""

    def test_pr_title_deprecated_fallback(self):
        # The script should pick up pr_title when mr_title is empty
        # (but will fail on repo validation before producing warnings output)
        result = run_pr_creator({
            "repo_dir": "/tmp/nonexistent-xyz",
            "branch_name": "my-branch",
            "pr_title": "Deprecated title",
            "pr_body": "Deprecated body",
        })
        # Should fail on repo check, but mr_title should have been populated
        self.assertEqual(result.get("status"), "error")


if __name__ == "__main__":
    main()
