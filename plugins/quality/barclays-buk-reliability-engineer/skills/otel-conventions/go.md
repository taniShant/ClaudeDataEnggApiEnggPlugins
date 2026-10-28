# Go — OTel Conventions

## Detection Patterns

A repo is Go if ANY of these are true:
- `go.mod` exists
- Root or `cmd/` contains `.go` files

**Build tool:** Go modules (`go.mod`) — no alternative detection needed.

**Framework detection (from go.mod requires):**
- `github.com/gin-gonic/gin` → Gin
- `github.com/go-chi/chi` → Chi
- `github.com/labstack/echo` → Echo
- `github.com/gorilla/mux` → Gorilla Mux
- `net/http` (stdlib) only → Standard library HTTP
- `google.golang.org/grpc` → gRPC

**Application type indicators:**
- HTTP API: any HTTP framework above, or `net/http` handlers
- Kafka consumer: `github.com/segmentio/kafka-go` or `github.com/confluentinc/confluent-kafka-go` or `github.com/IBM/sarama`

## OTel SDK Dependencies

Add these to `go.mod` (names only — `go get` resolves versions):

| Module | Purpose |
|--------|---------|
| `go.opentelemetry.io/otel` | Core OTel API |
| `go.opentelemetry.io/otel/sdk` | OTel SDK |
| `go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc` | OTLP trace exporter |
| `go.opentelemetry.io/otel/sdk/log` | Log SDK |
| `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` | OTLP log exporter |

For HTTP auto-instrumentation:
| `go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp` | HTTP client/server |
| `go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin` | Gin (if Gin) |
| `go.opentelemetry.io/contrib/instrumentation/github.com/go-chi/chi/otelchi` | Chi (if Chi) |
| `go.opentelemetry.io/contrib/instrumentation/github.com/labstack/echo/otelecho` | Echo (if Echo) |

For Kafka:
| `go.opentelemetry.io/contrib/instrumentation/github.com/segmentio/kafka-go/otelkafkago` | kafka-go propagation |
| `go.opentelemetry.io/contrib/instrumentation/github.com/IBM/sarama/otelsarama` | Sarama propagation |

## Structured Logging Configuration

### slog (recommended — stdlib, Go 1.21+)

```go
package logging

import (
    "context"
    "io"
    "log/slog"
    "os"

    "go.opentelemetry.io/otel/trace"
)

type OTelHandler struct {
    slog.Handler
}

func (h *OTelHandler) Handle(ctx context.Context, r slog.Record) error {
    span := trace.SpanFromContext(ctx)
    if span.IsRecording() {
        sc := span.SpanContext()
        r.AddAttrs(
            slog.String("TraceId", sc.TraceID().String()),
            slog.String("SpanId", sc.SpanID().String()),
        )
    }
    return h.Handler.Handle(ctx, r)
}

func NewLogger(w io.Writer) *slog.Logger {
    jsonHandler := slog.NewJSONHandler(w, &slog.HandlerOptions{
        ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
            switch a.Key {
            case slog.TimeKey:
                a.Key = "Timestamp"
            case slog.LevelKey:
                a.Key = "SeverityText"
            case slog.MessageKey:
                a.Key = "Body"
            }
            return a
        },
    })
    return slog.New(&OTelHandler{Handler: jsonHandler})
}
```

### zap alternative

```go
package logging

import (
    "go.uber.org/zap"
    "go.uber.org/zap/zapcore"
)

func NewZapLogger() (*zap.Logger, error) {
    config := zap.NewProductionConfig()
    config.EncoderConfig.TimeKey = "Timestamp"
    config.EncoderConfig.LevelKey = "SeverityText"
    config.EncoderConfig.MessageKey = "Body"
    config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
    config.EncoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder

    return config.Build()
}
```

For zap, correlation must be added via a wrapper that reads from context:

```go
func LogWithContext(ctx context.Context, logger *zap.Logger) *zap.Logger {
    span := trace.SpanFromContext(ctx)
    if span.IsRecording() {
        sc := span.SpanContext()
        return logger.With(
            zap.String("TraceId", sc.TraceID().String()),
            zap.String("SpanId", sc.SpanID().String()),
        )
    }
    return logger
}
```

## OTel SDK Initialization

Create `internal/otel/setup.go`:

```go
package otel

import (
    "context"
    "os"

    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func Setup(ctx context.Context) (func(context.Context) error, error) {
    res, _ := resource.Merge(
        resource.Default(),
        resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceName(os.Getenv("OTEL_SERVICE_NAME")),
            semconv.ServiceVersion(os.Getenv("BUILD_VERSION")),
            semconv.DeploymentEnvironmentName(os.Getenv("ENVIRONMENT")),
        ),
    )

    exporter, err := otlptracegrpc.New(ctx)
    if err != nil {
        return nil, err
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)

    return tp.Shutdown, nil
}
```

## Correlation IDs (Explicit Context)

Go passes context explicitly via `context.Context`. The OTel span is stored in the context — the slog handler (above) reads it via `trace.SpanFromContext(ctx)`.

**Critical:** All logging calls MUST pass context:

```go
// Correct — context carries trace info
slog.InfoContext(ctx, "processing payment", "amount", amount)

// Wrong — no context, no correlation
slog.Info("processing payment", "amount", amount)
```

This is the primary difference from other stacks — correlation is NOT automatic. The implement agent must ensure all `slog.Info` calls become `slog.InfoContext` calls.

## Bridge Pattern (Existing Logging)

If the repo already has zap or zerolog configured with custom outputs:
1. Keep existing output sinks — do NOT remove them
2. Add OTel-aware handler/core alongside existing ones (zap: `zapcore.NewTee`; slog: middleware handler)
3. Existing log destinations continue working unchanged

For zap (tee pattern):
```go
core := zapcore.NewTee(existingCore, otelCore)
logger := zap.New(core)
```

## Context Propagation

### HTTP (W3C Trace Context)

Use `otelhttp` middleware:

```go
// Server: wrap handler
handler = otelhttp.NewHandler(handler, "server")

// Client: wrap http.Client transport
client := &http.Client{
    Transport: otelhttp.NewTransport(http.DefaultTransport),
}
```

For Gin/Chi/Echo, use the framework-specific middleware (otelgin, otelchi, otelecho).

### Kafka

For kafka-go with `otelkafkago`:
```go
// Reader (consumer)
reader := kafka.NewReader(kafka.ReaderConfig{...})
// Wrap with OTel
msg, err := reader.ReadMessage(ctx) // context propagates automatically with instrumentation
```

For Sarama with `otelsarama`:
```go
// Wrap consumer handler
handler = otelsarama.WrapConsumerGroupHandler(handler)
```

## Common Detection Indicators (for Review Agent)

| Indicator | Means |
|-----------|-------|
| `go.uber.org/zap` in go.mod | Zap logger in use |
| `github.com/rs/zerolog` in go.mod | Zerolog in use |
| `log/slog` imports in source | slog in use (Go 1.21+) |
| `go.opentelemetry.io/otel` in go.mod | OTel already partially adopted |
| No structured logging (fmt.Println, log.Printf) | Unstructured — needs full foundation |
| `github.com/sirupsen/logrus` in go.mod | Logrus — recommend migration to slog |
