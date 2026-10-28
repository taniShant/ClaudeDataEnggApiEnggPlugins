# Python — OTel Conventions

## Detection Patterns

A repo is Python if ANY of these are true:
- `requirements.txt` exists
- `pyproject.toml` exists with `[project]` or `[tool.poetry]` section
- `setup.py` or `setup.cfg` exists
- `src/` or root contains `.py` files

**Build tool detection:**
- `pyproject.toml` with `[tool.poetry]` → Poetry
- `pyproject.toml` with `[build-system]` using `hatchling`/`setuptools` → pip with pyproject
- `requirements.txt` without pyproject.toml → pip with requirements file
- `Pipfile` → pipenv

**Framework detection:**
- `flask` in dependencies → Flask
- `fastapi` in dependencies → FastAPI
- `django` in dependencies → Django
- `starlette` in dependencies → Starlette

**Application type indicators:**
- HTTP API: any web framework above in dependencies
- Kafka consumer: `confluent-kafka` or `kafka-python` or `aiokafka` in dependencies

## OTel SDK Dependencies

Add these (names only — let lockfile/constraints manage versions):

| Package | Purpose |
|---------|---------|
| `opentelemetry-sdk` | Core OTel SDK |
| `opentelemetry-exporter-otlp` | OTLP exporter (traces + logs) |
| `opentelemetry-api` | OTel API |

For stdlib logging bridge:
| `opentelemetry-instrumentation-logging` | stdlib logging → OTel bridge |

For structlog:
| `opentelemetry-instrumentation-logging` | Works with structlog via stdlib integration |

For HTTP auto-instrumentation:
| `opentelemetry-instrumentation-flask` | Flask spans (if Flask) |
| `opentelemetry-instrumentation-fastapi` | FastAPI spans (if FastAPI) |
| `opentelemetry-instrumentation-django` | Django spans (if Django) |
| `opentelemetry-instrumentation-requests` | requests library outbound |
| `opentelemetry-instrumentation-httpx` | httpx outbound |

For Kafka:
| `opentelemetry-instrumentation-confluent-kafka` | Confluent Kafka propagation |
| `opentelemetry-instrumentation-kafka-python` | kafka-python propagation |

## Structured Logging Configuration

### structlog (recommended)

```python
import structlog
from opentelemetry import trace

def add_otel_context(logger, method_name, event_dict):
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["TraceId"] = format(ctx.trace_id, "032x")
        event_dict["SpanId"] = format(ctx.span_id, "016x")
    return event_dict

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        add_otel_context,
        structlog.processors.TimeStamper(fmt="iso", key="Timestamp"),
        structlog.processors.EventRenamer("Body"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
```

### stdlib logging

```python
import logging
import json
from datetime import datetime, timezone
from opentelemetry import trace

class OTelJsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "SeverityText": record.levelname,
            "SeverityNumber": self._severity_number(record.levelno),
            "Body": record.getMessage(),
            "Resource.service.name": os.environ.get("OTEL_SERVICE_NAME", "unknown"),
        }
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            log_entry["TraceId"] = format(ctx.trace_id, "032x")
            log_entry["SpanId"] = format(ctx.span_id, "016x")
        return json.dumps(log_entry)

    def _severity_number(self, levelno):
        mapping = {10: 5, 20: 9, 30: 13, 40: 17, 50: 21}
        return mapping.get(levelno, 9)
```

## OTel SDK Initialization

Create `src/otel_setup.py` (imported at application startup):

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
import os

def configure_otel():
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "unknown"),
        ResourceAttributes.SERVICE_VERSION: os.environ.get("BUILD_VERSION", "unknown"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "local"),
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
```

## Correlation IDs (Context Variables)

Python's `contextvars` module underpins the OTel SDK's context propagation. When using `opentelemetry-instrumentation-flask` (or FastAPI/Django equivalent), the SDK automatically creates spans for inbound requests — making `trace.get_current_span()` available throughout the request lifecycle.

The structlog processor or stdlib formatter shown above reads from this automatically.

## Bridge Pattern (Existing Logging)

If the repo already has logging configured (custom handlers, file rotation, cloud sinks):
1. Keep existing handlers — do NOT remove them
2. Add OTel log handler alongside existing ones
3. Use the structured formatter (above) on all handlers for schema consistency
4. Existing log destinations continue working unchanged

```python
import logging
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Add OTel handler alongside existing handlers
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter())
)
handler = logging.getLogger()
# Existing handlers remain — OTel export is additive
```

## Context Propagation

### HTTP (W3C Trace Context)

Framework instrumentations automatically:
- Extract `traceparent` from inbound requests
- Inject `traceparent` into outbound `requests`/`httpx` calls

No manual code required when instrumentations are registered.

### Kafka

With `opentelemetry-instrumentation-confluent-kafka`:
- Consumer: extracts trace context from Kafka message headers
- Producer: injects trace context into Kafka message headers

For manual propagation (if instrumentation doesn't cover your Kafka client):

```python
from opentelemetry.propagate import inject, extract
from opentelemetry import context

# Producer: inject context into headers
headers = {}
inject(headers)
producer.produce(topic, value=msg, headers=headers)

# Consumer: extract context from headers
ctx = extract(message.headers())
token = context.attach(ctx)
try:
    process_message(message)
finally:
    context.detach(token)
```

## Common Detection Indicators (for Review Agent)

| Indicator | Means |
|-----------|-------|
| `structlog` in dependencies | structlog in use |
| `logging.config` in code | stdlib logging configured |
| `python-json-logger` in dependencies | Already structured JSON (may be ECS) |
| `opentelemetry-*` in dependencies | OTel already partially adopted |
| `ddtrace` in dependencies | Datadog tracing — consider OTel migration |
| `jaeger-client` in dependencies | Legacy Jaeger — migrate to OTel |
| `LOGGING` dict in Django settings | Django logging configuration |
