# Telemetry Export (v2.6.2)

> **Telemetry is exported automatically to the Barclays Observe platform via gRPC OTLP.**
> Always on, fire-and-forget — the whole run in one batch at run end. No opt-out.

At pipeline end the Detox plugin sends the whole run to Observe in a single gRPC batch: the denormalized run summary (`detox.pipeline_run`, all `detox.*` fields) plus every granular per-phase event (each as its own `detox.<event_type>` record), all carrying Barclays identity/CIO as labels. It travels over gRPC OTLP to the strategic, platform-owned Barclays pipeline and lands in Observe. The transport library `scripts/telemetry/plugin_observability.py` is a faithful copy of the shared Barclays Observe library (same one the astral plugin uses), kept verbatim; the batch send (`send_many_to_observe`) lives in detox's own `scripts/telemetry/observe_batch.py`.

## How It Works

```
┌─────────────────────┐
│  Team A runs Detox   │──┐
│  otel_exporter.py    │  │   gRPC OTLP logs (TLS :443)
└─────────────────────┘  │        │
                          │        ▼
┌─────────────────────┐  │  ┌──────────────────────────────────────────────┐
│  Team B runs Detox   │──┼─▶│  Barclays Collector                           │
│  otel_exporter.py    │  │  │  metrics.dev-ai-tooling.barclays.intranet:443 │
└─────────────────────┘  │  └──────────────────────────────────────────────┘
                          │        │  FluentBit → CloudWatch
┌─────────────────────┐  │        ▼
│  Team C runs Detox   │──┘  ┌──────────────────────────────┐
│  otel_exporter.py    │     │  Observe (claude_code_client) │
└─────────────────────┘     └──────────────────────────────┘
```

### Key Design: one fire-and-forget Observe event per run

- **Strategic shared path** — the official Barclays Observe pipeline, not a plugin-owned Collector/S3.
- **Whole run in one batch** — `detox.pipeline_run` + every `detox.<event_type>` phase event, flushed in a single gRPC round-trip (`send_many_to_observe`).
- **Identity in record attributes** — `barclays_*` (user id, CIO, team, email) are injected from `OTEL_RESOURCE_ATTRIBUTES` as labels (resource attrs are overwritten by the collector, so identity must live on the record).
- **Never blocks the pipeline** — missing deps / unreachable endpoint / TLS failure = logged warning, run still succeeds.
- **gRPC/OTLP deps** — `grpcio`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc` in `~/.claude/observe_venv`. Mandatory CHECK-ONLY preflight prerequisite (pre-provisioned per machine, NOT auto-installed); a missing dep hard-stops the run.
- **CA trust** — read from `NODE_EXTRA_CA_CERTS` (Barclays CA bundle path); falls back to the system bundle, which usually lacks the Barclays internal CAs.

### Data Flow

1. Developer runs `/barclays-buk-detox:remediate`
2. `prepare_pipeline.py` writes the findings to `{repo}/.detox/state.json`; Stages 4-9 record fixes, tests and phase changes there through `pipeline_state.py` (each phase change also appends a `phase.*` event to `~/.detox/telemetry/events.jsonl`)
3. At pipeline end, `run_recorder.py` builds the run summary from the state file and writes it to `~/.detox/telemetry/runs.jsonl` (local)
4. `otel_exporter.py` flattens the run record and its events and calls `observe_batch.send_many_to_observe(...)` — the whole run in one gRPC batch
5. The event travels over gRPC OTLP → Barclays Collector → FluentBit → CloudWatch → Observe

No reconciler. No scheduled pipeline. No S3 bucket to own.

## Configuration

**Minimal.** Export is always on; a dedup hit yields exactly one event per `job_id`.
Endpoint defaults to `metrics.dev-ai-tooling.barclays.intranet:443` (detox default, applied in
`observe_batch.py`); CA trust comes from `NODE_EXTRA_CA_CERTS`; override the endpoint via
`OTEL_EXPORTER_OTLP_ENDPOINT` **in `~/.claude/settings.json` only — never a shell profile**
(a shell export silently routes to the wrong host). If the endpoint is unreachable or deps
are unavailable, the export fails silently and the run still succeeds. See the project
README "Observability & Telemetry → Export" for the one-time deps + CA bundle setup.

## Support

For questions, onboarding help, or feature requests — join the Detox Teams channel:

[Detox — General](https://teams.microsoft.com/l/channel/19%3A9GL7IOGlcyDTRMgstwSZCjVUv-wXKS-wB1e04lXiDvw1%40thread.tacv2/General?groupId=d6c698b2-28d9-4c29-9c68-6558353faabc&tenantId=c4b62f1d-01e0-4107-a0cc-5ac886858b23)
