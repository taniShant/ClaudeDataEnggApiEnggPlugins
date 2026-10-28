"""Tests for usage_report.py — aggregation engine and report renderer."""

import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.telemetry.usage_report import (
    parse_period,
    load_runs,
    compute_aggregates,
    format_duration,
    render_bar,
    render_table,
    render_html,
    generate_report,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestParsePeriod(TestCase):
    def test_7d(self):
        from datetime import datetime, timezone
        start, end = parse_period("7d")
        self.assertAlmostEqual((end - start).days, 7, delta=1)

    def test_30d(self):
        start, end = parse_period("30d")
        from datetime import datetime, timezone
        self.assertAlmostEqual((end - start).days, 30, delta=1)

    def test_90d(self):
        start, end = parse_period("90d")
        self.assertAlmostEqual((end - start).days, 90, delta=1)

    def test_all(self):
        from datetime import datetime
        start, end = parse_period("all")
        self.assertEqual(start, datetime.min.replace(tzinfo=start.tzinfo))


class TestFormatDuration(TestCase):
    def test_seconds(self):
        self.assertEqual(format_duration(5000), "5s")
        self.assertEqual(format_duration(45000), "45s")

    def test_minutes(self):
        self.assertEqual(format_duration(90000), "1m 30s")
        self.assertEqual(format_duration(330000), "5m 30s")

    def test_hours(self):
        self.assertEqual(format_duration(3660000), "1h 01m")

    def test_zero(self):
        self.assertEqual(format_duration(0), "—")

    def test_none(self):
        self.assertEqual(format_duration(None), "—")


class TestRenderBar(TestCase):
    def test_full(self):
        result = render_bar(1.0, width=5)
        self.assertEqual(result, "▓▓▓▓▓")

    def test_empty(self):
        result = render_bar(0.0, width=5)
        self.assertEqual(result, "░░░░░")

    def test_half(self):
        result = render_bar(0.5, width=10)
        self.assertEqual(result, "▓▓▓▓▓░░░░░")


class TestLoadRuns(TestCase):
    def test_loads_fixture_data(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            # Use a very old date to load all
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)
            self.assertEqual(len(runs), 5)
            self.assertEqual(runs[0]["job_id"], "a1b2c3d4")
            self.assertEqual(runs[0]["repo_name"], "DSS-COMMON-CONTAINER_V4")

    def test_filters_by_time(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            # Only after Aug 22
            after = datetime(2026, 8, 22, tzinfo=timezone.utc)
            runs = load_runs(after)
            self.assertLess(len(runs), 5)
            for run in runs:
                self.assertGreaterEqual(run["started_at"], "2026-08-22")

    def test_returns_empty_for_missing_file(self):
        from datetime import datetime, timezone
        with patch("scripts.telemetry.usage_report.RUNS_FILE", Path("/nonexistent/runs.jsonl")):
            runs = load_runs(datetime(2020, 1, 1, tzinfo=timezone.utc))
            self.assertEqual(runs, [])


class TestComputeAggregates(TestCase):
    def test_with_fixture_data(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        report = compute_aggregates(runs, "30d", start, end)

        # Usage
        self.assertEqual(report["usage"]["total_runs"], 5)
        self.assertEqual(report["usage"]["unique_users"], 3)
        self.assertEqual(report["usage"]["unique_repos"], 4)
        self.assertEqual(report["usage"]["most_active_user"]["name"], "deveshkumar")

        # Effectiveness
        self.assertGreater(report["effectiveness"]["fix_success_rate"], 0)
        self.assertGreater(report["effectiveness"]["cwes_remediated"], 0)

        # Security
        self.assertGreater(len(report["security_posture"]["top_cwes"]), 0)
        self.assertIn("CWE-79", [c["cwe"] for c in report["security_posture"]["top_cwes"]])

        # Cost
        self.assertGreater(report["cost"]["total_agent_invocations"], 0)

        # Errors
        self.assertEqual(report["errors"]["failure_count"], 1)

        # Repos
        self.assertGreater(len(report["repos"]), 0)
        self.assertEqual(report["repos"][0]["name"], "DSS-COMMON-CONTAINER_V4")

        # Contributing Step 5
        self.assertEqual(report["contributing_step5"]["invocation_count"], 5)
        self.assertGreater(report["contributing_step5"]["flag_frequency"], 0)

    def test_empty_runs(self):
        from datetime import datetime, timezone
        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        report = compute_aggregates([], "30d", start, end)
        self.assertEqual(report["usage"]["total_runs"], 0)
        self.assertEqual(report["usage"]["unique_users"], 0)
        self.assertNotIn("savings", report)  # financial metrics removed
        self.assertEqual(report["onboarding"]["total_repos_onboarded"], 0)

    def test_includes_onboarding_data(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            report = compute_aggregates(runs, "30d", start, end)

        onboarding = report["onboarding"]
        self.assertGreater(onboarding["total_repos_onboarded"], 0)
        self.assertEqual(onboarding["total_repos_onboarded"], 4)  # 4 unique repos in fixture
        self.assertIn("repos_with_first_run", onboarding)
        self.assertGreater(len(onboarding["repos_with_first_run"]), 0)
        # Each entry has name and first_run
        first_entry = onboarding["repos_with_first_run"][0]
        self.assertIn("name", first_entry)
        self.assertIn("first_run", first_entry)

    def test_no_financial_metrics(self):
        """ROI/savings and $ cost estimates must be gone — telemetry is pure-tech."""
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)
        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            report = compute_aggregates(runs, "30d", start, end)
        self.assertNotIn("savings", report)
        self.assertNotIn("estimated_budget_cap_usd", report.get("cost", {}))
        # cost section keeps neutral technical fields only
        self.assertIn("total_agent_invocations", report["cost"])
        self.assertIn("model_distribution", report["cost"])

    def test_includes_derived_rates(self):
        """effectiveness carries the pure-tech derived rates."""
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)
        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            report = compute_aggregates(runs, "30d", start, end)
        eff = report["effectiveness"]
        for key in ("remediation_rate", "fix_success_rate", "fix_failure_rate",
                    "deferral_rate", "validation_pass_rate", "test_pass_rate"):
            self.assertIn(key, eff)
            self.assertGreaterEqual(eff[key], 0.0)
            self.assertLessEqual(eff[key], 1.0)

    def test_aggregates_reason_maps(self):
        """deferred_by_reason / unverified_by_reason merge-sum across runs."""
        from datetime import datetime, timezone
        runs = [
            {"status": "completed", "vulns_total": 8, "fixes_attempted": 3,
             "vulns_deferred_by_reason": {"manual": 3, "not_applicable": 2},
             "fixes_unverified_by_reason": {"still_detected": 1, "fix_failed": 1},
             "repo_name": "a", "user_name": "u", "started_at": "2026-08-10T00:00:00Z", "ended_at": "2026-08-10T00:05:00Z"},
            {"status": "completed", "vulns_total": 4, "fixes_attempted": 2,
             "vulns_deferred_by_reason": {"manual": 1, "dependency": 1},
             "fixes_unverified_by_reason": {"still_detected": 1},
             "repo_name": "b", "user_name": "u", "started_at": "2026-08-11T00:00:00Z", "ended_at": "2026-08-11T00:05:00Z"},
        ]
        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        report = compute_aggregates(runs, "30d", start, end)
        sp = report["security_posture"]
        self.assertEqual(sp["deferred_by_reason"], {"manual": 4, "not_applicable": 2, "dependency": 1})
        self.assertEqual(sp["unverified_by_reason"], {"still_detected": 2, "fix_failed": 1})


class TestRenderTable(TestCase):
    def test_produces_ascii_output(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        report = compute_aggregates(runs, "30d", start, end)
        table = render_table(report)

        self.assertIn("DETOX USAGE DASHBOARD", table)
        self.assertIn("USAGE OVERVIEW", table)
        self.assertIn("PERFORMANCE", table)
        self.assertIn("EFFECTIVENESS", table)
        self.assertIn("DSS-COMMON-CONTAINER_V4", table)
        self.assertIn("ONBOARDING", table)
        self.assertIn("USAGE PROFILE", table)
        self.assertIn("Remediation Rate:", table)
        self.assertIn("Deferral Rate:", table)
        # Financial content must be gone
        self.assertNotIn("COST SAVED", table)
        self.assertNotIn("ROI:", table)
        self.assertNotIn("Net Savings:", table)


class TestRenderHtml(TestCase):
    def test_produces_valid_html(self):
        from datetime import datetime, timezone
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            after = datetime(2020, 1, 1, tzinfo=timezone.utc)
            runs = load_runs(after)

        start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        end = datetime(2026, 8, 28, tzinfo=timezone.utc)
        report = compute_aggregates(runs, "30d", start, end)
        html = render_html(report)

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Detox Usage Report", html)
        self.assertIn("Total Runs", html)
        self.assertIn("Fix Rate", html)
        self.assertIn("</html>", html)
        # Should be self-contained
        self.assertIn("<style>", html)
        self.assertNotIn("href=", html)  # No external CSS


class TestGenerateReport(TestCase):
    def test_json_format(self):
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            result = generate_report({"period": "all", "format": "json"})
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["format"], "json")
            report = result["report"]
            self.assertIn("usage", report)
            self.assertIn("performance", report)
            self.assertIn("effectiveness", report)

    def test_table_format(self):
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
            result = generate_report({"period": "all", "format": "table"})
            self.assertEqual(result["status"], "success")
            self.assertIn("DETOX USAGE DASHBOARD", result["rendered"])

    def test_html_format_writes_file(self):
        fixture = FIXTURES_DIR / "sample_runs.jsonl"
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            with patch("scripts.telemetry.usage_report.RUNS_FILE", fixture):
                result = generate_report({
                    "period": "all",
                    "format": "html",
                    "output": str(output_path),
                })
                self.assertEqual(result["status"], "success")
                self.assertTrue(output_path.exists())
                content = output_path.read_text()
                self.assertIn("<!DOCTYPE html>", content)


if __name__ == "__main__":
    main()
