"""
@barclays/plugin-observability — Python MetricsClient

Stdlib only (for file-based metrics): json, os, pathlib, threading, time
For Observe publishing (gRPC OTLP): grpcio + opentelemetry-exporter-otlp-proto-grpc

Usage — file-based metrics (no extra deps):
    from plugin_observability import MetricsClient

    metrics = MetricsClient(plugin_name="detox")
    metrics.increment_counter("detox_vulns_total", 5, labels={"severity": "high"})
    metrics.set_gauge("detox_validation_pass_rate", 0.91)
    metrics.record_histogram("detox_fix_duration_ms", 5234)
    metrics.record_event("detox.scan_complete", {"status": "success"})

    # Metrics auto-flush every 5 seconds in background thread
    # On shutdown:
    metrics.close()  # Final flush + stop background thread

Usage — send directly to Observe (requires grpcio + opentelemetry):
    from plugin_observability import send_to_observe

    send_to_observe(
        event_name="compass.epics_created",
        value="5",
        extra_attrs={"skill": "compass", "outcome": "success"},
    )

    # Or via MetricsClient:
    metrics = MetricsClient(plugin_name="compass")
    metrics.publish_to_observe("compass.epics_created", "5", extra_attrs={"skill": "compass"})

Install deps for Observe publishing:
    pip install grpcio opentelemetry-exporter-otlp-proto-grpc

The Barclays CA cert is read from the path in NODE_EXTRA_CA_CERTS (set in
settings.json env block). No download required.

Observe query to find events:
    filter labels.plugin_metric = "compass.epics_created"
    filter labels.barclays_user_id = "<your-barclays-id>"

Usage — fire-and-forget from hooks (returns in ~1ms, child survives parent exit):
    from plugin_observability import send_to_observe_async

    send_to_observe_async(
        event_name="astral.bash_rewrite",
        value="4000",
        extra_attrs={"tier": "heavy", "projected_tokens_saved": "4000"},
    )
"""

import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROCESS_TRACE_ID = str(uuid.uuid4())

LIBRARY_VERSION = "1.1.0"
HISTOGRAM_BOUNDS = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

_OBSERVE_VENV = Path.home() / ".claude" / "observe_venv"

# ---------------------------------------------------------------------------
# Certificate resolution — driven entirely by NODE_EXTRA_CA_CERTS env var.
# That variable is set in Barclays dev tooling on both Windows and macOS.
# Falls back to common system bundle locations so the library also works on
# macOS/Linux developer machines where the env var may not be set.
# ---------------------------------------------------------------------------

def _cert_path() -> Path:
    env = os.environ.get("NODE_EXTRA_CA_CERTS", "").strip()
    if env:
        p = Path(env)
        if p.exists():
            return p
        raise FileNotFoundError(
            f"[plugin_observability] NODE_EXTRA_CA_CERTS points to a missing file: {env}"
        )
    # System bundle fallbacks for macOS / Linux (no env var needed there)
    for candidate in (
        Path("/etc/ssl/cert.pem"),             # macOS, Alpine
        Path("/etc/ssl/certs/ca-certificates.crt"),  # Debian/Ubuntu
        Path("/etc/pki/tls/certs/ca-bundle.crt"),    # RHEL/CentOS
    ):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "[plugin_observability] No CA bundle found. "
        "Set NODE_EXTRA_CA_CERTS to the path of your corporate CA bundle."
    )


def _inject_venv_path() -> None:
    """Prepend ~/.claude/observe_venv site-packages to sys.path if the venv exists.

    Call this before importing grpcio/opentelemetry when running from a hook that
    may not have those packages on its default sys.path.
    """
    import glob as _glob
    if not _OBSERVE_VENV.exists():
        return
    if sys.platform == "win32":
        pattern = str(_OBSERVE_VENV / "Lib" / "site-packages")
    else:
        pattern = str(_OBSERVE_VENV / "lib" / "python*" / "site-packages")
    for sp in sorted(_glob.glob(pattern)):
        if sp not in sys.path:
            sys.path.insert(0, sp)

# ---------------------------------------------------------------------------
# Endpoint resolution — all values read from env vars set in settings.json.
# No hardcoded fallbacks.
#
# OTEL_EXPORTER_OTLP_ENDPOINT  required, e.g. "https://metrics.example.intranet"
#   → stripped of scheme + :443 appended → "metrics.example.intranet:443" (gRPC)
# OTEL_SERVICE_NAME             optional, e.g. "claude-code"
# OTEL_SERVICE_VERSION          optional, e.g. "2.1.185"
# ---------------------------------------------------------------------------

def _resolve_endpoint() -> str:
    """Derive gRPC host:port from OTEL_EXPORTER_OTLP_ENDPOINT (required)."""
    raw = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not raw:
        raise EnvironmentError(
            "[plugin_observability] OTEL_EXPORTER_OTLP_ENDPOINT is not set. "
            "Add it to your .claude/settings.json env block."
        )
    # Strip scheme (https:// or http://)
    host = raw.split("//", 1)[-1].rstrip("/")
    # Append :443 if no port already present
    if ":" not in host:
        host = host + ":443"
    return host


_OBSERVE_ENDPOINT = _resolve_endpoint()


def _resolve_user_id() -> str:
    """
    Resolve Barclays user ID for use as a fallback when OTEL_RESOURCE_ATTRIBUTES is absent.
    Priority: barclays_user_id in OTEL_RESOURCE_ATTRIBUTES > USERNAME > USER > os.getlogin()
    """
    for part in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(","):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            if k.strip() == "barclays_user_id":
                return v.strip()
    uid = os.environ.get("USERNAME") or os.environ.get("USER", "")
    if not uid:
        try:
            uid = os.getlogin()
        except Exception:
            pass
    return uid


def _resolve_claude_user_id() -> str:
    """
    Read Claude Code's internal userID from ~/.claude.json.

    Claude Code generates a random 64-char hex ID on first run and persists it
    in ~/.claude.json as {"userID": "<64-char hex>"}. This is the value Claude
    sends as user.id in its own OTEL telemetry, so we mirror it here so plugin
    events land in the same user dimension in Observe.

    Falls back to an empty string if the file is missing or the field is absent.
    """
    try:
        claude_json = Path.home() / ".claude.json"
        if claude_json.exists():
            data = json.loads(claude_json.read_text(encoding="utf-8"))
            uid = data.get("userID", "")
            if isinstance(uid, str) and len(uid) == 64:
                return uid
    except Exception:
        pass
    return ""


def _build_resource_attrs() -> dict:
    """
    Build OTLP resource attributes dict from OTEL_RESOURCE_ATTRIBUTES env var.

    When the env var is present (e.g. settings.json injects
    barclays_user_id=<bnid>,barclays_cio=CCT,...) all its key=value pairs
    are included verbatim as resource attributes.

    When the env var is absent a minimal fallback is synthesised:
        barclays_user_id = USERNAME (always set on Barclays Windows)
    """
    base: Dict[str, str] = {
        "service.name":    os.environ.get("OTEL_SERVICE_NAME", ""),
        "service.version": os.environ.get("OTEL_SERVICE_VERSION", ""),
        "host.arch":       platform.machine().lower().replace("x86_64", "amd64"),
        "host.name":       platform.node(),
        "os.type":         platform.system().lower(),
        "os.version":      platform.version(),
    }
    # Drop empty strings so missing env vars don't emit blank resource attrs
    base = {k: v for k, v in base.items() if v}
    otel_attrs = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").strip()
    if otel_attrs:
        for part in otel_attrs.split(","):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                base[k.strip()] = v.strip()
    else:
        # Fallback: synthesise barclays_user_id so at least user filtering works in Observe
        uid = os.environ.get("USERNAME") or os.environ.get("USER", "")
        if not uid:
            try:
                uid = os.getlogin()
            except Exception:
                pass
        if uid:
            base["barclays_user_id"] = uid
    return base


_OBSERVE_DEPS = [
    "grpcio",
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp-proto-grpc",
]


def _ensure_observe_deps() -> bool:
    """
    Install gRPC/OTLP dependencies if not already present. Silent on success.
    Returns True if deps are available after the call, False if install failed.
    """
    _inject_venv_path()
    import importlib.util

    missing = []
    for mod, pkg in [
        ("grpc", "grpcio"),
        ("opentelemetry.sdk", "opentelemetry-sdk"),
        ("opentelemetry.exporter.otlp.proto.grpc", "opentelemetry-exporter-otlp-proto-grpc"),
    ]:
        try:
            if importlib.util.find_spec(mod) is None:
                missing.append(pkg)
        except (ModuleNotFoundError, ValueError):
            missing.append(pkg)

    if not missing:
        return True

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception as e:
        print(f"[plugin_observability] auto-install failed: {e}", file=sys.stderr)
        print(f"  Run manually: pip install {' '.join(missing)}", file=sys.stderr)
        return False


def _get_grpc_credentials() -> Any:
    """Return grpc.ssl_channel_credentials using the corporate CA bundle."""
    import grpc
    bundle = _cert_path()
    root_certs = bundle.read_bytes()
    return grpc.ssl_channel_credentials(root_certificates=root_certs)


def send_to_observe(
    event_name: str,
    value: str,
    session_id: str = "",
    extra_attrs: Optional[Dict[str, str]] = None,
) -> bool:
    """
    Send a custom plugin metric to the Barclays Observe claude_code_client dataset.

    Pipeline: gRPC OTLP logs -> OTEL Collector -> FluentBit -> CloudWatch -> Observe
    Dataset:  app/logs/developer ai tooling/claude_code_client

    The Barclays CA cert is read from NODE_EXTRA_CA_CERTS (set in settings.json).
    No download required.

    Args:
        event_name:  Dotted event/metric name, e.g. "compass.epics_created"
        value:       Metric value (numeric string or any string)
        session_id:  Claude session ID (optional, auto-read from CLAUDE_SESSION_ID env)
        extra_attrs: Additional labels that appear as labels.* in Observe

    Returns:
        True on success, False on failure (never raises)

    Requires:
        pip install grpcio opentelemetry-exporter-otlp-proto-grpc

    Example:
        send_to_observe("compass.epics_created", "5", extra_attrs={"skill": "compass"})
    """
    if not _ensure_observe_deps():
        return False

    try:
        from opentelemetry.sdk.resources import Resource
        # SDK v1.x uses public path; older builds used private _logs path
        try:
            from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk.logs.export import SimpleLogRecordProcessor
        except ImportError:
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # type: ignore[no-redef]
            from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor  # type: ignore[no-redef]
        try:
            from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
        except ImportError:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter  # type: ignore[no-redef]

        credentials = _get_grpc_credentials()

        sid = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID", "") or os.environ.get("CLAUDE_SESSION_ID", "")
        tid = sid or _PROCESS_TRACE_ID
        resource = Resource.create(_build_resource_attrs())
        exporter = OTLPLogExporter(endpoint=_OBSERVE_ENDPOINT, credentials=credentials, insecure=False)
        # Use SimpleLogRecordProcessor (synchronous) — appropriate for single-shot hook processes.
        # BatchLogRecordProcessor is for long-running services and can drop records on abrupt exit.
        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

        handler = LoggingHandler(level=logging.INFO, logger_provider=provider)

        # Use a fresh logger name each call to avoid handler accumulation across repeated calls
        # in long-running processes (each call creates a new provider/channel).
        import uuid as _uuid
        logger_name = f"jarvis.plugin.{event_name}.{_uuid.uuid4().hex[:8]}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(handler)

        # Suppress Python source-location fields (code.file.path etc.) from leaking into Observe labels
        handler.addFilter(lambda r: (
            setattr(r, "pathname", "") or
            setattr(r, "filename", "") or
            setattr(r, "funcName", "") or
            setattr(r, "lineno", 0) or
            True
        ))

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Parse OTEL_RESOURCE_ATTRIBUTES into attrs so they land in labels.*
        # (The collector pipeline replaces resource attrs with its own — identity must be in log record attrs.)
        identity: Dict[str, str] = {}
        for part in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(","):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                identity[k.strip()] = v.strip()
        if not identity:
            uid = os.environ.get("USERNAME") or os.environ.get("USER", "")
            if uid:
                identity["barclays_user_id"] = uid

        # sid/tid computed above before resource build; uid resolved here after identity is parsed.
        uid = _resolve_claude_user_id() or identity.get("barclays_user_id", os.environ.get("USERNAME") or os.environ.get("USER", ""))

        attrs: Dict[str, Any] = {
            "event.name":      event_name,
            "event.timestamp": now_iso,
            "event.sequence":  1,
            "session.id":      sid,
            "user.id":         uid,
            "trace.id":        tid,
            "app.version":     os.environ.get("OTEL_SERVICE_VERSION", ""),
            "terminal.type":   "cli",
            "plugin_metric":   event_name,
            "plugin_value":    str(value),
            **identity,
        }
        for k, v in (extra_attrs or {}).items():
            attrs[k] = str(v)

        logger.info(event_name, extra=attrs)
        provider.force_flush(timeout_millis=5000)
        provider.shutdown()
        return True

    except Exception as e:
        import sys
        print(f"[plugin_observability] send_to_observe failed: {e}", file=sys.stderr)
        return False


def send_to_observe_async(
    event_name: str,
    value: str,
    session_id: str = "",
    extra_attrs: Optional[Dict[str, str]] = None,
) -> None:
    """
    Fire-and-forget variant of send_to_observe.

    Spawns a detached subprocess so the caller returns immediately (~1ms).
    The child process survives the parent's exit and completes the gRPC send.

    Use this from hooks where blocking 3-8s for a synchronous gRPC call is unacceptable.
    Falls back silently on spawn failure.

    Args:
        event_name:  Dotted event/metric name, e.g. "astral.bash_rewrite"
        value:       Metric value (numeric string or any string)
        session_id:  Claude session ID (optional, auto-read from CLAUDE_SESSION_ID env)
        extra_attrs: Additional labels that appear as labels.* in Observe

    Example:
        send_to_observe_async("astral.bash_rewrite", "4000", extra_attrs={"tier": "heavy"})
    """
    import json as _json
    hooks_dir = str(Path(__file__).parent)
    payload = _json.dumps({
        "event_name": event_name,
        "value": value,
        "session_id": session_id,
        "extra_attrs": extra_attrs or {},
    })
    script = (
        "import sys, json; "
        "sys.path.insert(0, sys.argv[1]); "
        "from plugin_observability import send_to_observe; "
        "d = json.loads(sys.argv[2]); "
        "send_to_observe(d['event_name'], d['value'], d.get('session_id',''), d.get('extra_attrs'))"
    )
    kwargs: Dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen([sys.executable, "-c", script, hooks_dir, payload], **kwargs)
    except Exception:
        pass


class MetricsClient:
    """
    Records plugin metrics in-memory and periodically writes them to disk as OTLP JSON.
    Non-blocking: background thread handles flushes.
    """

    def __init__(
        self,
        plugin_name: str,
        service_name: Optional[str] = None,
        flush_interval_s: float = 5.0,
    ):
        """
        Args:
            plugin_name: Directory name under ~/.metrics/ (e.g., "detox")
            service_name: Sets resource.service.name in OTLP; defaults to plugin_name
            flush_interval_s: Background flush interval in seconds (default 5.0)
        """
        self._plugin_name = plugin_name
        self._service_name = service_name or plugin_name
        self._flush_interval = flush_interval_s

        # Compute metrics file path
        self._metrics_file = Path.home() / ".metrics" / plugin_name / "metrics.json"

        # Internal state
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._events: List[Dict[str, Any]] = []

        # Background flush thread
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._background_flush, daemon=True)
        self._thread.start()

        # Background publish thread (optional)
        self._publish_enabled = False
        self._publish_interval = 60.0
        self._collector_url: Optional[str] = None
        self._publish_thread: Optional[threading.Thread] = None

    @staticmethod
    def _make_key(name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """
        Compose metric key from name and labels.
        Format: "metricName|||label1=val1,label2=val2" (labels sorted by key)
        """
        if not labels:
            return f"{name}|||"

        sorted_labels = ",".join(
            f"{k}={v}" for k, v in sorted(labels.items())
        )
        return f"{name}|||{sorted_labels}"

    def increment_counter(
        self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter (monotonic, always increases)."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge (point-in-time value, replaces previous)."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram value (distribution, all values kept)."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def record_event(
        self, name: str, attributes: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a structured event."""
        ts_nano = str(int(time.time_ns()))
        event = {
            "name": name,
            "attributes": attributes or {},
            "timestampNano": ts_nano,
        }
        with self._lock:
            self._events.append(event)

    def flush(self) -> None:
        """Synchronously write metrics to file.
        Clears event queue but keeps counters/gauges/histograms (cumulative).
        """
        with self._lock:
            payload = self._build_otlp()
            events_snapshot = self._events[:]
            self._events = []

        try:
            self._atomic_write(payload)
        except Exception as e:
            if os.environ.get("CLAUDE_METRICS_DEBUG") == "true":
                print(f"[metrics] flush failed: {e}", flush=True)

    def close(self) -> None:
        """Stop background threads and flush."""
        self._stop_event.set()
        self._publish_enabled = False
        self._thread.join(timeout=10)
        if self._publish_thread:
            self._publish_thread.join(timeout=10)
        self.flush()

    # --- Internal methods ---

    def _background_flush(self) -> None:
        """Background thread: flush periodically without raising."""
        while not self._stop_event.wait(self._flush_interval):
            try:
                self.flush()
            except Exception:
                pass  # Never crash the background thread

    def _build_otlp(self) -> dict:
        """Build OTLP payload from current state (called under lock)."""
        time_nano = str(int(time.time_ns()))
        metrics: List[Dict[str, Any]] = []

        # Counters
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            metrics.append({
                "name": name,
                "sum": {
                    "isMonotonic": True,
                    "aggregationTemporality": 1,
                    "dataPoints": [
                        {
                            "timeUnixNano": time_nano,
                            "asInt": str(int(value)),
                            "attributes": self._labels_to_attributes(labels),
                        }
                    ],
                },
            })

        # Gauges
        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            metrics.append({
                "name": name,
                "gauge": {
                    "dataPoints": [
                        {
                            "timeUnixNano": time_nano,
                            "asDouble": value,
                            "attributes": self._labels_to_attributes(labels),
                        }
                    ],
                },
            })

        # Histograms
        for key, values in self._histograms.items():
            name, labels = self._parse_key(key)
            bucket_counts, total_sum, count = self._compute_histogram_buckets(values)
            metrics.append({
                "name": name,
                "histogram": {
                    "aggregationTemporality": 1,
                    "dataPoints": [
                        {
                            "timeUnixNano": time_nano,
                            "count": str(count),
                            "sum": total_sum,
                            "bucketCounts": [str(c) for c in bucket_counts],
                            "explicitBounds": HISTOGRAM_BOUNDS,
                            "attributes": self._labels_to_attributes(labels),
                        }
                    ],
                },
            })

        # Build payload
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self._service_name}},
                            {"key": "service.version", "value": {"stringValue": LIBRARY_VERSION}},
                        ],
                    },
                    "scopeMetrics": [
                        {
                            "scope": {
                                "name": "barclays-plugin-observability",
                                "version": LIBRARY_VERSION,
                            },
                            "metrics": metrics,
                        }
                    ],
                }
            ]
        }

    @staticmethod
    def _parse_key(key: str) -> tuple:
        """Parse metric key back to (name, labels_dict).
        Format: "metricName|||label1=val1,label2=val2"
        """
        parts = key.split("|||")
        name = parts[0]
        label_str = parts[1] if len(parts) > 1 else ""

        labels = {}
        if label_str:
            for pair in label_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    labels[k] = v

        return name, labels

    @staticmethod
    def _labels_to_attributes(labels: Dict[str, str]) -> List[Dict[str, Any]]:
        """Convert labels to OTLP attributes array."""
        return [
            {"key": k, "value": {"stringValue": v}} for k, v in labels.items()
        ]

    @staticmethod
    def _compute_histogram_buckets(
        values: List[float],
    ) -> tuple:
        """
        Compute histogram bucket counts from values and explicit bounds.
        Returns: (bucket_counts, sum, count)
        """
        bucket_counts = [0] * (len(HISTOGRAM_BOUNDS) + 1)
        total_sum = 0

        for value in values:
            total_sum += value
            placed = False

            for i, bound in enumerate(HISTOGRAM_BOUNDS):
                if value <= bound:
                    bucket_counts[i] += 1
                    placed = True
                    break

            if not placed:
                bucket_counts[-1] += 1

        return bucket_counts, total_sum, len(values)

    def _atomic_write(self, payload: dict) -> None:
        """Atomically write OTLP payload to file."""
        # Create parent directories
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        tmp_file = self._metrics_file.parent / f".metrics.tmp.{os.getpid()}.{int(time.time_ns())}"

        try:
            tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_file.chmod(0o600)
            # Atomic replace
            tmp_file.replace(self._metrics_file)
        except Exception:
            # Clean up temp file if it exists
            try:
                tmp_file.unlink()
            except Exception:
                pass
            raise

    def publish(self, collector_url: Optional[str] = None) -> None:
        """
        POST metrics directly to OTEL collector endpoint.

        Args:
            collector_url: OTEL collector URL (default from env var or localhost)

        Does not raise; logs errors if CLAUDE_METRICS_DEBUG is set.
        """
        url = collector_url or os.environ.get('OTEL_COLLECTOR_URL')
        if not url:
            if os.environ.get('CLAUDE_METRICS_DEBUG') == 'true':
                print('[metrics] OTEL_COLLECTOR_URL not set; publish() is a no-op', flush=True)
            return
        payload = self._build_otlp()

        headers = {
            'Content-Type': 'application/json',
        }
        api_key = os.environ.get('OTEL_API_KEY')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        # Retry logic: exponential backoff
        import urllib.request
        import urllib.error
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=5) as response:
                    if 200 <= response.status < 300:
                        if os.environ.get('CLAUDE_METRICS_DEBUG') == 'true':
                            print(f'[metrics] published to {url}', flush=True)
                        return
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                else:
                    if os.environ.get('CLAUDE_METRICS_DEBUG') == 'true':
                        print(f'[metrics] publish to {url} failed: {e}', flush=True)

    def publish_to_observe(
        self,
        event_name: str,
        value: str,
        session_id: str = "",
        extra_attrs: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send a single named event directly to the Barclays Observe dataset via gRPC OTLP.

        This is the recommended method for plugin agents to emit custom metrics that appear
        in Observe under: app/logs/developer ai tooling/claude_code_client

        The Barclays CA cert is fetched and cached automatically — no setup required.

        Observe APL query to find your events:
            filter labels.plugin_metric = "<event_name>"
            filter labels.barclays_user_id = "<your-barclays-id>"

        Args:
            event_name:  Dotted name, e.g. "compass.epics_created"
            value:       Metric value as string, e.g. "5"
            session_id:  Optional Claude session ID
            extra_attrs: Dict of extra labels; appear as labels.* in Observe

        Returns:
            True on success, False on failure (never raises)

        Example:
            metrics = MetricsClient(plugin_name="compass")
            metrics.publish_to_observe("compass.epics_created", "3", extra_attrs={"outcome": "success"})
        """
        return send_to_observe(
            event_name=event_name,
            value=value,
            session_id=session_id,
            extra_attrs=extra_attrs,
        )

    def enable_scheduled_publish(self, collector_url: Optional[str] = None, interval_s: Optional[float] = None) -> None:
        """
        Enable background thread for periodic OTEL publishing.

        Args:
            collector_url: OTEL collector URL (default from OTEL_COLLECTOR_URL env var)
            interval_s: Publish interval in seconds (default from OTEL_PUBLISH_INTERVAL_S env var or 300.0 = 5 min)
        """
        # Resolve interval: param > env var > default (5 minutes = 300 seconds)
        if interval_s is None:
            env_interval = os.environ.get('OTEL_PUBLISH_INTERVAL_S')
            if env_interval:
                try:
                    interval_s = float(env_interval)
                    if interval_s <= 0:
                        interval_s = 300.0
                except (ValueError, TypeError):
                    interval_s = 300.0
            else:
                interval_s = 300.0

        self._publish_enabled = True
        self._publish_interval = interval_s
        self._collector_url = collector_url or os.environ.get('OTEL_COLLECTOR_URL')

        if os.environ.get('CLAUDE_METRICS_DEBUG') == 'true':
            print(f'[metrics] scheduled publish enabled: interval_s={interval_s}, url={self._collector_url}', flush=True)

        if self._publish_thread:
            self._publish_enabled = False
            self._publish_thread.join(timeout=5)

        self._publish_thread = threading.Thread(target=self._background_publish, daemon=True)
        self._publish_thread.start()

    def _background_publish(self) -> None:
        """Background thread: publish metrics periodically."""
        while self._publish_enabled:
            time.sleep(self._publish_interval)
            try:
                self.publish(self._collector_url)
            except Exception:
                pass  # Never crash background thread

    def get_state(self) -> dict:
        """Get read-only snapshot of current metrics state."""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {k: list(v) for k, v in self._histograms.items()},
                'events': list(self._events),
            }

    def reset(self) -> None:
        """Clear all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._events.clear()
