# Node.js (TypeScript) — OTel Conventions

## Detection Patterns

A repo is Node.js if ANY of these are true:
- `package.json` exists at root or in a module directory
- `tsconfig.json` exists
- `src/` contains `.ts` or `.js` files

**Build tool detection:**
- `package-lock.json` → npm
- `yarn.lock` → yarn
- `pnpm-lock.yaml` → pnpm

**Framework detection (from package.json dependencies):**
- `express` → Express
- `fastify` → Fastify
- `@nestjs/core` → NestJS
- `koa` → Koa
- `hapi` or `@hapi/hapi` → Hapi

**Application type indicators:**
- HTTP API: any HTTP framework above in dependencies
- Kafka consumer: `kafkajs` or `node-rdkafka` in dependencies

## OTel SDK Dependencies

Add these to `package.json` (names only — let lockfile manage versions):

| Package | Purpose |
|---------|---------|
| `@opentelemetry/sdk-node` | Core OTel SDK for Node.js |
| `@opentelemetry/exporter-trace-otlp-grpc` | OTLP trace exporter |
| `@opentelemetry/exporter-logs-otlp-grpc` | OTLP log exporter |
| `@opentelemetry/resources` | Resource attributes |
| `@opentelemetry/semantic-conventions` | Standard attribute names |

For Pino integration:
| `@opentelemetry/instrumentation-pino` | Pino → OTel bridge |

For Winston integration:
| `@opentelemetry/instrumentation-winston` | Winston → OTel bridge |

For HTTP auto-instrumentation:
| `@opentelemetry/instrumentation-http` | HTTP client/server spans |
| `@opentelemetry/instrumentation-express` | Express-specific spans (if Express) |
| `@opentelemetry/instrumentation-fastify` | Fastify-specific spans (if Fastify) |

For Kafka:
| `@opentelemetry/instrumentation-kafkajs` | KafkaJS context propagation |

## Structured Logging Configuration

### Pino (recommended for Node.js)

Create or update the Pino logger configuration:

```typescript
import pino from 'pino';

const logger = pino({
  formatters: {
    level(label) {
      return { SeverityText: label.toUpperCase() };
    },
    log(object) {
      return {
        ...object,
        Timestamp: new Date().toISOString(),
      };
    },
  },
  messageKey: 'Body',
  timestamp: false,
  mixin() {
    const span = trace.getActiveSpan();
    if (span) {
      const ctx = span.spanContext();
      return {
        TraceId: ctx.traceId,
        SpanId: ctx.spanId,
      };
    }
    return {};
  },
});
```

### Winston alternative

```typescript
import winston from 'winston';
import { trace } from '@opentelemetry/api';

const logger = winston.createLogger({
  format: winston.format.combine(
    winston.format((info) => {
      const span = trace.getActiveSpan();
      if (span) {
        const ctx = span.spanContext();
        info.TraceId = ctx.traceId;
        info.SpanId = ctx.spanId;
      }
      info.Timestamp = new Date().toISOString();
      info.SeverityText = info.level.toUpperCase();
      info.Body = info.message;
      return info;
    })(),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()],
});
```

## OTel SDK Initialization

Create `src/instrumentation.ts` (loaded before app code via `--require` or `--import`):

```typescript
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-grpc';
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-grpc';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || 'unknown',
    [ATTR_SERVICE_VERSION]: process.env.BUILD_VERSION || 'unknown',
    'deployment.environment': process.env.ENVIRONMENT || 'local',
  }),
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317',
  }),
  logRecordExporter: new OTLPLogExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317',
  }),
  instrumentations: [
    new HttpInstrumentation(),
    new PinoInstrumentation(),
  ],
});

sdk.start();
```

## Correlation IDs (AsyncLocalStorage)

The OTel Node.js SDK uses `AsyncLocalStorage` internally. When `@opentelemetry/instrumentation-pino` or `@opentelemetry/instrumentation-winston` is registered, it automatically injects `trace_id` and `span_id` into log records.

**Manual alternative** (if not using instrumentation packages): use the `mixin` pattern shown above to read from `trace.getActiveSpan()`.

## Bridge Pattern (Existing Logging)

If the repo already has Pino/Winston configured with custom transports:
1. Keep existing transports — do NOT remove them
2. Add the OTel instrumentation package alongside
3. Existing log destinations (file, stdout, cloud transport) continue working
4. OTel becomes an additional export path via the SDK

## Context Propagation

### HTTP (W3C Trace Context)

`@opentelemetry/instrumentation-http` automatically:
- Extracts `traceparent` from inbound requests
- Injects `traceparent` into outbound `http`/`https` calls and `fetch`

No manual code required when the instrumentation is registered in `instrumentation.ts`.

### Kafka (KafkaJS)

With `@opentelemetry/instrumentation-kafkajs`:
- Consumer: automatically extracts trace context from Kafka message headers
- Producer: automatically injects trace context into Kafka message headers

No manual code required when registered.

## Common Detection Indicators (for Review Agent)

| Indicator | Means |
|-----------|-------|
| `pino` in package.json | Pino logger in use |
| `winston` in package.json | Winston logger in use |
| `bunyan` in package.json | Legacy logger — recommend migration to Pino |
| `@opentelemetry/*` in package.json | OTel already partially adopted |
| `dd-trace` in package.json | Datadog tracing — consider OTel migration |
| `pino-pretty` in devDependencies | Pino in use with dev formatting |
| Custom `transports` in Pino config | Existing log destinations to preserve |
