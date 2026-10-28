---
name: streaming
description: Streaming and event processing knowledge covering Kafka, Flink, delivery semantics, patterns, observability, and DLQ handling
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Streaming and Event Processing Skill

## Apache Kafka

### Core Concepts

**Topic**: a named, ordered, partitioned log of messages. Consumers read from a topic; producers append to it.

**Partition**: the unit of parallelism. Messages within a partition are strictly ordered. Messages across partitions are not ordered. Partition count determines maximum consumer parallelism.

**Consumer group**: a set of consumers that cooperatively consume a topic. Each partition is assigned to exactly one consumer in the group at any time. Multiple consumer groups read the same topic independently.

**Offset**: a sequential identifier for each message within a partition. Consumers track their offset to know which messages have been processed.

### Producer Configuration

```java
Properties props = new Properties();
props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka:9092");
props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, KafkaAvroSerializer.class.getName());
props.put(ProducerConfig.ACKS_CONFIG, "all");               // wait for all ISR replicas
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);  // exactly-once at the producer
props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);
props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);
props.put("schema.registry.url", "http://schema-registry:8081");
```

### Consumer Configuration

```java
Properties props = new Properties();
props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka:9092");
props.put(ConsumerConfig.GROUP_ID_CONFIG, "payments-processor-v1");
props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);  // manual commit for reliability
props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, KafkaAvroDeserializer.class.getName());
props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);
props.put("schema.registry.url", "http://schema-registry:8081");
```

### Exactly-Once Semantics (EOS)
Kafka EOS requires:
1. Idempotent producers (`enable.idempotence=true`).
2. Transactions for producers that write to multiple partitions/topics atomically.
3. Consumers configured with `isolation.level=read_committed`.

```java
producer.initTransactions();
try {
    producer.beginTransaction();
    producer.send(record1);
    producer.send(record2);
    producer.sendOffsetsToTransaction(offsets, groupMetadata);
    producer.commitTransaction();
} catch (ProducerFencedException | OutOfOrderSequenceException e) {
    producer.close();  // fatal; restart required
} catch (KafkaException e) {
    producer.abortTransaction();
}
```

EOS carries a latency and throughput overhead. Use it only when duplicate or lost messages have material business impact.

### Schema Registry and Avro/Protobuf

Always register message schemas in a Schema Registry. Do not embed schema in message payloads or in application code.

```json
// Example Avro schema registered in Schema Registry
{
  "type": "record",
  "name": "PaymentEvent",
  "namespace": "com.barclays.buk.payments",
  "fields": [
    { "name": "payment_id",  "type": "string" },
    { "name": "account_id",  "type": "string" },
    { "name": "amount",      "type": { "type": "bytes", "logicalType": "decimal", "precision": 18, "scale": 2 } },
    { "name": "currency",    "type": "string" },
    { "name": "event_ts",    "type": { "type": "long", "logicalType": "timestamp-millis" } }
  ]
}
```

Schema compatibility modes:
- **BACKWARD** (default): new schema can read messages written with the previous schema.
- **FORWARD**: previous schema can read messages written with the new schema.
- **FULL**: both backward and forward compatible.
- **NONE**: no compatibility check. Do not use in production.

Use `BACKWARD_TRANSITIVE` or `FULL_TRANSITIVE` for strong guarantees across all schema versions.

### Retention and Compaction

| Policy | Behaviour | Use When |
|---|---|---|
| `delete` | Retain messages for `retention.ms`; delete older messages | Event streams; time-series data |
| `compact` | Retain only the most recent message per key; tombstones (null value) delete a key | Changelog streams; state materialisation |

```
retention.ms=604800000     # 7 days
retention.bytes=-1          # no byte-based limit
cleanup.policy=delete       # or compact, or delete,compact
```

### Dead Letter Queues (DLQ)
Route messages that cannot be processed (deserialization failure, business rule violation, downstream unavailability) to a DLQ topic. DLQ topics follow the naming convention `{source-topic}.DLT` or `{source-topic}.dlq`.

```java
// Example DLQ producer send on processing failure
try {
    process(record);
} catch (DeserializationException | BusinessRuleException e) {
    producer.send(new ProducerRecord<>(dlqTopicName, record.key(), record.value()));
    consumer.commitSync();  // commit original offset to avoid reprocessing
}
```

---

## Apache Flink

### DataStream API

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
env.setParallelism(4);
env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);

DataStream<PaymentEvent> payments = env
    .fromSource(
        KafkaSource.<PaymentEvent>builder()
            .setBootstrapServers("kafka:9092")
            .setTopics("payments")
            .setGroupId("flink-payments-processor")
            .setStartingOffsets(OffsetsInitializer.earliest())
            .setValueOnlyDeserializer(new AvroDeserializationSchema<>(PaymentEvent.class))
            .build(),
        WatermarkStrategy.<PaymentEvent>forBoundedOutOfOrderness(Duration.ofSeconds(10))
            .withTimestampAssigner((event, ts) -> event.getEventTs()),
        "payments-source"
    );
```

### Table API and SQL
```java
StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);

tableEnv.executeSql("""
    CREATE TABLE payments (
        payment_id  STRING,
        account_id  STRING,
        amount      DECIMAL(18, 2),
        event_ts    TIMESTAMP(3),
        WATERMARK FOR event_ts AS event_ts - INTERVAL '10' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'payments',
        'properties.bootstrap.servers' = 'kafka:9092',
        'format' = 'avro-confluent',
        'avro-confluent.url' = 'http://schema-registry:8081'
    )
""");
```

### Event Time vs Processing Time

| Time Semantic | Definition | Use When |
|---|---|---|
| Event time | Timestamp embedded in the event (when it happened) | Default for most analytics; handles out-of-order data correctly |
| Processing time | Wall-clock time when the event arrives at Flink | Only for latency-insensitive, ordered sources; simpler but incorrect for late data |
| Ingestion time | Time when Flink receives the event | Rarely used; intermediate between event and processing time |

Always prefer event time for data engineering pipelines. Use processing time only when the source has no reliable event timestamp.

### Watermarks
Watermarks signal that no events with a timestamp earlier than the watermark will arrive. They control when Flink closes windows and emits results.

```java
WatermarkStrategy.<PaymentEvent>forBoundedOutOfOrderness(Duration.ofSeconds(10))
    .withTimestampAssigner((event, ts) -> event.getEventTs())
    .withIdleness(Duration.ofMinutes(5))  // mark partition as idle to advance watermark when no records arrive
```

Set the bounded-out-of-orderness duration based on observed late-data distribution. Larger values reduce dropped late data but increase output latency.

### Windows

```java
// Tumbling window: non-overlapping fixed-size windows
payments
    .keyBy(PaymentEvent::getAccountId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new SumAmountAggregator());

// Sliding window: overlapping windows
payments
    .keyBy(PaymentEvent::getAccountId)
    .window(SlidingEventTimeWindows.of(Time.hours(1), Time.minutes(15)))
    .aggregate(new AverageAggregator());

// Session window: gaps in activity trigger window close
payments
    .keyBy(PaymentEvent::getAccountId)
    .window(EventTimeSessionWindows.withGap(Time.minutes(30)))
    .aggregate(new SessionAggregator());
```

### State Management
Flink maintains operator state in a configurable state backend:
- **HashMapStateBackend**: in-memory state; suitable for small state and development.
- **EmbeddedRocksDBStateBackend**: out-of-memory state stored on local disk; required for large state.

```java
env.setStateBackend(new EmbeddedRocksDBStateBackend(true));  // true = incremental checkpoints
env.getCheckpointConfig().setCheckpointStorage("s3://bucket/flink-checkpoints/");
```

### Checkpoints and Savepoints
- **Checkpoints**: automatic, periodic snapshots for recovery from failure. Taken every `checkpointing interval` ms.
- **Savepoints**: manual, portable snapshots. Used for planned upgrades, code changes, and A/B testing.

```java
// Checkpoint configuration
env.enableCheckpointing(60_000);  // every 60 seconds
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(5_000);
env.getCheckpointConfig().setCheckpointTimeout(120_000);
env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
env.getCheckpointConfig().setTolerableCheckpointFailureNumber(3);
env.getCheckpointConfig().setExternalizedCheckpointCleanup(
    ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
);
```

### Exactly-Once in Flink
Flink achieves exactly-once end-to-end by combining:
1. Flink checkpoint barriers (internal exactly-once processing).
2. Two-phase commit sink (e.g. `FlinkKafkaProducer` with `Semantic.EXACTLY_ONCE`).

### Side Outputs
Route late data or errors to a side output stream rather than discarding them:

```java
OutputTag<PaymentEvent> lateDataTag = new OutputTag<PaymentEvent>("late-data") {};

SingleOutputStreamOperator<Result> mainStream = payments
    .keyBy(PaymentEvent::getAccountId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .sideOutputLateData(lateDataTag)
    .aggregate(new SumAmountAggregator());

DataStream<PaymentEvent> lateStream = mainStream.getSideOutput(lateDataTag);
lateStream.addSink(new LateDataDlqSink());
```

---

## Streaming Patterns

### Event Sourcing
Persist every state change as an immutable event in an append-only event log. Reconstruct current state by replaying events. The event log is the source of truth.

### CQRS (Command Query Responsibility Segregation)
Separate the write model (commands that produce events) from the read model (materialized views optimised for queries). Common in event-sourced systems. The event stream populates one or more read projections.

### Saga Pattern
Coordinate a distributed transaction across multiple services using a sequence of local transactions. Each step produces an event. If a step fails, compensating events roll back previous steps. Use orchestration (central coordinator) or choreography (each service reacts to events).

### Outbox Pattern
Avoid dual writes (write to DB and publish to Kafka in the same operation) by writing events to an outbox table in the same DB transaction as the domain change. A separate process (CDC or polling publisher) reads the outbox and publishes to Kafka.

```sql
-- Outbox table
CREATE TABLE outbox_events (
    id            UUID      NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id  VARCHAR(100) NOT NULL,
    event_type    VARCHAR(100) NOT NULL,
    payload       JSONB     NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at  TIMESTAMP
);
```

### Change Data Capture (CDC)
Capture row-level database changes and publish them as events. Common tools: Debezium (Kafka Connect source connector). CDC enables event-driven pipelines without application code changes.

---

## Delivery Semantics

| Semantic | Producer Behaviour | Consumer Behaviour | Duplicates? | Lost Messages? | Use When |
|---|---|---|---|---|---|
| At-most-once | Fire and forget | Auto-commit before processing | No | Possible | Metrics, telemetry where occasional loss is acceptable |
| At-least-once | Retry on failure | Commit after processing | Possible | No | Default for most business pipelines; consumers must be idempotent |
| Exactly-once | Idempotent + transactional | Read committed; transactional commit | No | No | Financial transactions, audit logs; incurs overhead |

---

## Micro-Batch vs True Streaming

| Aspect | Micro-Batch (Spark Structured Streaming) | True Streaming (Flink, Kafka Streams) |
|---|---|---|
| Latency | Seconds (trigger interval) | Sub-second to milliseconds |
| Throughput | High (batch efficiency) | High (continuous processing) |
| Exactly-once | Yes (with Delta or compatible sinks) | Yes (with checkpoints + transactional sinks) |
| Operational complexity | Lower | Higher |
| Recommended for | SLA >= 30 seconds; existing Spark expertise | Low-latency CEP, real-time fraud detection, sub-second dashboards |

---

## Backpressure Handling

Backpressure occurs when downstream consumers are slower than upstream producers. Correct handling:
- In Kafka: consumers slow the consumption rate naturally via `max.poll.records` and processing time. Lag accumulates in the partition offset.
- In Flink: backpressure propagates upstream through the network buffer mechanism. Monitor with the Flink Web UI backpressure metric. Scale out operators or optimise slow processing functions.
- Never drop messages to relieve backpressure without an explicit DLQ or discard policy.

---

## Ordering Guarantees

Kafka provides ordering within a partition only. To preserve global ordering:
- Use a single partition (reduces throughput).
- Or accept that global order is not preserved and design consumers to be order-independent.

For event-time ordering across partitions, use Flink with watermarks, which re-orders events within the watermark bound.

---

## Schema Evolution in Streaming

Use a Schema Registry with backward compatibility mode. Consumers built to the old schema must be able to read messages written with the new schema.

Rules:
- Adding a new field with a default value is backward compatible.
- Removing a field is forward compatible but breaks backward compatibility unless the field had a default.
- Changing a field type is never compatible.
- Renaming a field is not compatible; use an alias instead.

Test schema changes against all registered consumer schemas before deploying a producer change.

---

## Replay and Reprocessing

Design consumers to support full replay from offset 0 (or a specific offset/timestamp). Requirements:
- Idempotent consumers (processing the same message twice produces the same result).
- Stateful consumers must support state reset or replay with a fresh consumer group.
- Sinks must support upsert or deduplication.

To replay from a specific point:
```bash
# Reset consumer group offset to a timestamp
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group my-group \
  --topic payments \
  --reset-offsets \
  --to-datetime 2026-07-01T00:00:00.000 \
  --execute
```

---

## Observability

### Key Metrics to Monitor

| Metric | Source | Alert Threshold |
|---|---|---|
| Consumer lag | Kafka (`kafka.consumer.fetch-manager-metrics.records-lag-max`) | Growing lag over time |
| Producer record send rate | Kafka | Drop below baseline throughput |
| Producer error rate | Kafka (`record-error-rate`) | Any non-zero value |
| Throughput (records/s) | Kafka, Flink | Drop below SLA threshold |
| Checkpoint duration | Flink | Exceeds checkpoint interval |
| Checkpoint failures | Flink | Any non-zero value |
| Backpressure ratio | Flink Web UI | > 50% sustained |
| DLQ message count | Kafka DLQ topic | Any growth in DLQ lag |

### Consumer Lag Monitoring
```bash
# Command-line consumer lag check
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --group payments-processor-v1 \
  --describe

# Output: TOPIC, PARTITION, CURRENT-OFFSET, LOG-END-OFFSET, LAG, CONSUMER-ID, HOST
```

---

## DLQ Patterns

A Dead Letter Queue captures messages that cannot be processed after all retry attempts.

Structure:
- DLQ topic name: `{source-topic}.DLT` (Spring Kafka convention) or `{source-topic}.dlq`
- DLQ message envelope should include: original payload, error type, error message, original topic, partition, offset, consumer group, timestamp of failure.

```json
{
  "original_topic": "payments",
  "original_partition": 3,
  "original_offset": 100042,
  "consumer_group": "payments-processor-v1",
  "error_type": "DeserializationException",
  "error_message": "Unrecognised field 'legacy_field'",
  "failed_at": "2026-07-13T10:15:00Z",
  "payload": "<base64-encoded original bytes>"
}
```

Implement a DLQ reprocessing mechanism that allows operators to replay or discard DLQ messages after the root cause is resolved.

---

## Idempotent Consumers

Every consumer must produce the same final state regardless of how many times a message is processed. Implementation strategies:
- **Natural idempotency**: the operation is inherently idempotent (e.g. set a value, not increment).
- **Deduplication on primary/unique key**: upsert by message key; second processing is a no-op.
- **Processed message log**: track processed message IDs in a store; skip if already seen (expensive; use only when other strategies are not viable).

---

## Graceful Shutdown

Streaming consumers and processors must handle shutdown signals (SIGTERM) gracefully:
1. Stop consuming new messages.
2. Finish processing in-flight messages.
3. Commit offsets (or flush checkpoints in Flink).
4. Close connections and release resources.

```python
# Python Kafka consumer graceful shutdown
import signal

running = True

def shutdown(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, shutdown)

try:
    while running:
        records = consumer.poll(timeout_ms=1000)
        for tp, messages in records.items():
            for msg in messages:
                process(msg)
        consumer.commit()
finally:
    consumer.close()
```
