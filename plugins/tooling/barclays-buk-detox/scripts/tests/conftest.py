"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_telemetry_log(tmp_path, monkeypatch):
    """Keep events emitted during tests (e.g. phase events) out of ~/.detox/telemetry."""
    from scripts.telemetry import telemetry

    telemetry_dir = tmp_path / "telemetry"
    monkeypatch.setattr(telemetry, "TELEMETRY_DIR", telemetry_dir)
    monkeypatch.setattr(telemetry, "EVENTS_FILE", telemetry_dir / "events.jsonl")
