"""Tests for Nexus client."""

import json
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.nexus.nexus_client import NexusClient


class TestNexusClient(TestCase):
    def setUp(self):
        self.client = NexusClient("https://nexus.example.com")

    def test_build_search_url(self):
        """Test search URL construction."""
        url = self.client._build_search_url(
            "org.apache.logging.log4j", "log4j-core", "2.23.1"
        )
        self.assertIn("service/rest/v1/search", url)
        self.assertIn("org.apache.logging.log4j", url)
        self.assertIn("log4j-core", url)
        self.assertIn("2.23.1", url)

    def test_build_search_url_without_version(self):
        """Test search URL without version."""
        url = self.client._build_search_url("org.apache.commons", "commons-text")
        self.assertIn("service/rest/v1/search", url)
        self.assertNotIn("version=", url)

    @patch("urllib.request.urlopen")
    def test_check_artifact_exists_found(self, mock_urlopen):
        """Test artifact check when found."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "items": [{"version": "2.23.1", "artifact": "log4j-core"}]
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.check_artifact_exists(
            "org.apache.logging.log4j", "log4j-core", "2.23.1"
        )
        self.assertTrue(result)

    @patch("urllib.request.urlopen")
    def test_check_artifact_exists_not_found(self, mock_urlopen):
        """Test artifact check when not found."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"items": []}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = self.client.check_artifact_exists(
            "org.apache.logging.log4j", "log4j-core", "2.23.1"
        )
        self.assertFalse(result)

    @patch("urllib.request.urlopen")
    def test_list_available_versions(self, mock_urlopen):
        """Test listing versions."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "items": [
                {"version": "2.23.1"},
                {"version": "2.23.0"},
                {"version": "2.22.1"},
            ]
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        versions = self.client.list_available_versions(
            "org.apache.logging.log4j", "log4j-core"
        )
        self.assertEqual(versions, ["2.23.1", "2.23.0", "2.22.1"])


class TestNexusCache(TestCase):
    def test_same_url_requested_once(self):
        c = NexusClient("https://nexus.example.com")
        with patch.object(c, "_make_request_uncached", return_value={"items": []}) as raw:
            for _ in range(5):
                c._make_request("https://nexus.example.com/x")
        self.assertEqual(raw.call_count, 1)

    def test_failures_cached_and_reraised(self):
        c = NexusClient("https://nexus.example.com")
        with patch.object(c, "_make_request_uncached", side_effect=RuntimeError("down")) as raw:
            for _ in range(3):
                with self.assertRaises(RuntimeError):
                    c._make_request("https://nexus.example.com/y")
        self.assertEqual(raw.call_count, 1)


if __name__ == "__main__":
    main()
