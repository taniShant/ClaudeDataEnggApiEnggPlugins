---
name: aws-data-services
description: AWS data engineering knowledge covering Athena, Glue, S3, Lake Formation, Step Functions, CloudWatch, IAM, EventBridge, and cost optimisation
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# AWS Data Services Engineering Skill

> **Important notice**: This skill provides factual capability and constraint evidence for AWS data services. It must NOT be used to score AWS more favourably than alternative platforms in any technology decision or evaluation. Technology selection must follow the BUK platform governance process.

## Amazon Athena

### Overview
Athena is a serverless interactive query service that uses Presto/Trino to query data in S3 via the Glue Data Catalog. Queries are billed per data scanned (per TB), making cost control essential.

### SQL Dialect
Athena uses Presto/Trino SQL. Key differences from ANSI SQL:
- `DATE_ADD('unit', n, timestamp)` not `timestamp + INTERVAL n unit`
- `DATE_DIFF('unit', ts1, ts2)` not `DATEDIFF`
- No `MERGE` statement (as of Athena v3 with Iceberg tables, limited MERGE support added)
- `TRY(expression)` for null-on-error evaluation
- `UNNEST` for array/map expansion

### External Tables and Partition Discovery
```sql
-- Create external table pointing to S3
CREATE EXTERNAL TABLE IF NOT EXISTS raw.transactions (
    transaction_id  BIGINT,
    account_id      BIGINT,
    amount          DECIMAL(18,2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 's3://bucket/raw/transactions/'
TBLPROPERTIES ('parquet.compress'='SNAPPY');

-- Register partitions manually
ALTER TABLE raw.transactions ADD IF NOT EXISTS
    PARTITION (year=2026, month=7, day=13)
    LOCATION 's3://bucket/raw/transactions/year=2026/month=7/day=13/';

-- Or use MSCK REPAIR TABLE for Hive-style partition discovery (slow on large datasets)
MSCK REPAIR TABLE raw.transactions;
```

Prefer `ALTER TABLE ... ADD PARTITION` over `MSCK REPAIR TABLE` for large partition counts; the latter scans all S3 prefixes and is slow.

### Workgroups
- Assign each team or application to a dedicated Athena workgroup.
- Set a per-query data scan limit (`BytesScannedCutoffPerQuery`) to prevent runaway queries.
- Route results to a workgroup-specific S3 results bucket with appropriate encryption.

```json
{
  "WorkGroupConfiguration": {
    "BytesScannedCutoffPerQuery": 10737418240,
    "EnforceWorkGroupConfiguration": true,
    "ResultConfiguration": {
      "OutputLocation": "s3://bucket/athena-results/team-name/",
      "EncryptionConfiguration": { "EncryptionOption": "SSE_S3" }
    }
  }
}
```

### Cost Control
- Always filter on partition columns to enable partition pruning and minimise scanned data.
- Use columnar formats (Parquet, ORC) with compression (Snappy, ZSTD) to reduce data scanned.
- Use `LIMIT` for exploratory queries; Athena still scans all relevant partitions before applying `LIMIT`.
- Avoid `SELECT *`; project only required columns.
- Enable result reuse for repeated identical queries within the workgroup.

### Federated Queries
Athena can query external data sources (RDS, DynamoDB, Redshift) via Lambda-based connectors. Use federated queries sparingly; they incur Lambda invocation costs and are slower than native S3 queries.

---

## AWS Glue

### Glue PySpark Jobs

Glue jobs run PySpark on a managed cluster. Glue provides both the `DynamicFrame` and standard Spark `DataFrame` APIs.

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ["JOB_NAME", "source_path", "target_path"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Read as DynamicFrame (schema-flexible, handles messy data)
dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["source_path"]], "recurse": True},
    format="parquet",
    push_down_predicate="year == 2026 and month == 7",
)

# Convert to DataFrame for complex transformations
df = dyf.toDF()

# ... transformations ...

# Write back as DynamicFrame
output_dyf = DynamicFrame.fromDF(df, glueContext, "output")
glueContext.write_dynamic_frame.from_options(
    frame=output_dyf,
    connection_type="s3",
    connection_options={"path": args["target_path"], "partitionKeys": ["year", "month"]},
    format="parquet",
)

job.commit()
```

### Job Bookmarks
Enable job bookmarks to process only new data since the last successful run:

```python
glueContext.create_dynamic_frame.from_options(
    ...,
    additional_options={"jobBookmarkKeys": ["transaction_id"], "jobBookmarkKeysSortOrder": "asc"},
    transformation_ctx="source_read",  # required for bookmark tracking
)
```

Bookmarks track the high-water mark per `transformation_ctx`. Use consistent `transformation_ctx` names across job versions to preserve bookmark state.

### Pushdown Predicates
```python
# Reduce data scanned at source — evaluated before loading into memory
dyf = glueContext.create_dynamic_frame.from_catalog(
    database="raw_db",
    table_name="transactions",
    push_down_predicate="year = 2026 and month = 7",
)
```

### DynamicFrame vs DataFrame

| Consideration | DynamicFrame | DataFrame |
|---|---|---|
| Schema flexibility | Handles inconsistent schemas, `choice` types | Requires a fixed schema |
| Performance | Slower for large, consistent datasets | Faster for clean, consistent data |
| Transforms | Glue-specific transforms (`ResolveChoice`, `DropNullFields`) | Full PySpark ecosystem |
| Recommendation | Use for ingestion of messy external data | Use for all transformation logic |

Convert to DataFrame as early as possible in the job after reading and schema resolution.

### Glue Crawlers
Crawlers infer schema and populate the Glue catalog. Use crawlers for initial catalog registration only. For production pipelines, manage schema and partitions explicitly to avoid unexpected schema changes.

Set crawler exclusion patterns to skip non-data files (e.g. `_SUCCESS`, `_metadata`):
```json
{ "Exclusions": ["**/_SUCCESS", "**/_metadata", "**/.spark-staging-*/**"] }
```

### Glue Connections
Glue connections store JDBC connection details (host, port, credentials via Secrets Manager) for connecting to relational databases. Always store credentials in AWS Secrets Manager; never hardcode in job parameters.

### Error Handling
```python
try:
    result_df = transform(df)
    write(result_df)
    job.commit()
except Exception as e:
    glueContext.get_logger().error(f"Job failed: {str(e)}")
    raise  # Re-raise to mark job as FAILED in Glue, triggering retry/alarm
```

---

## Amazon S3

### Storage Classes

| Class | Use Case | Min Duration |
|---|---|---|
| S3 Standard | Frequently accessed data | None |
| S3 Standard-IA | Infrequent access (monthly) | 30 days |
| S3 Intelligent-Tiering | Unknown or changing access patterns | None |
| S3 Glacier Instant Retrieval | Archive with millisecond retrieval | 90 days |
| S3 Glacier Flexible Retrieval | Archive with minutes–hours retrieval | 90 days |
| S3 Glacier Deep Archive | Long-term regulatory archive | 180 days |

### Lifecycle Policies
Define lifecycle rules to transition and expire objects automatically:
```json
{
  "Rules": [{
    "ID": "transition-to-ia-after-30d",
    "Status": "Enabled",
    "Filter": { "Prefix": "raw/" },
    "Transitions": [
      { "Days": 30, "StorageClass": "STANDARD_IA" },
      { "Days": 365, "StorageClass": "GLACIER" }
    ],
    "Expiration": { "Days": 2555 }
  }]
}
```

### Encryption
- Enable SSE-S3 (AES-256) as a minimum on all buckets.
- Use SSE-KMS for buckets containing PII, financial data, or any data classified as Restricted or above; this enables audit logs of key usage via CloudTrail.
- Enable S3 Block Public Access on all buckets at account level.

### Bucket Policies
Apply least-privilege bucket policies. Deny requests that are not using `aws:SecureTransport` (HTTPS):
```json
{
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": { "Bool": { "aws:SecureTransport": "false" } }
}
```

### Prefix Design for Partition Discovery
Use Hive-style partitioning for Athena and Glue compatibility:
```
s3://bucket/database/table/year=2026/month=07/day=13/file.parquet
```
Avoid excessive partition depth. Three to four levels (e.g. year/month/day) is typical. Avoid partitioning at sub-day granularity unless the downstream query pattern specifically requires it.

### Small File Problem
Avoid writing many small files (< 1 MB). Use `repartition` or `coalesce` in Spark before writing, and enable S3 Intelligent-Tiering or run periodic compaction jobs to merge small files.

---

## AWS Lake Formation

### Fine-Grained Access Control
Lake Formation provides column-level, row-level (via data filters), and cell-level access control on top of the Glue catalog.

- Assign table-level permissions to IAM roles via Lake Formation `GRANT` rather than S3 bucket policies.
- Column-level access: grant only the columns a consumer role needs.
- Row-level data filters: restrict rows by filter expression (e.g. `region = 'UK'`).

### Governed Tables
Governed tables provide ACID transactions for S3 data via Lake Formation. Use governed tables when multiple concurrent writers must write to the same S3 prefix without conflicts.

### Data Filters
```python
# Register a data filter (AWS SDK / Terraform)
{
  "DatabaseName": "finance",
  "TableName": "transactions",
  "Name": "uk_only_filter",
  "RowFilter": { "FilterExpression": "region = 'UK'" },
  "ColumnWildcard": {}
}
```

Assign data filters to principals using `GrantWithDataLakePrincipal`.

---

## AWS Step Functions

### Orchestration Patterns
Use Step Functions to orchestrate multi-step data pipelines. Prefer Standard Workflows for long-running pipelines (up to 1 year execution duration).

```json
{
  "Comment": "Data pipeline orchestration",
  "StartAt": "IngestRawData",
  "States": {
    "IngestRawData": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {
        "JobName": "raw-ingest-job",
        "Arguments": { "--source_date.$": "$.source_date" }
      },
      "Retry": [{
        "ErrorEquals": ["States.TaskFailed"],
        "IntervalSeconds": 60,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }],
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "Next": "NotifyFailure",
        "ResultPath": "$.error"
      }],
      "Next": "TransformData"
    }
  }
}
```

### Error Handling
- Always define `Retry` blocks with exponential backoff on task states.
- Always define `Catch` blocks to route to failure notification or compensating transaction states.
- Use `ResultPath` to preserve original input alongside error detail.

### Retry Configuration
- `IntervalSeconds`: initial wait before first retry.
- `MaxAttempts`: total additional attempts after the first failure.
- `BackoffRate`: multiplier applied to wait time on each retry.
- `MaxDelaySeconds`: cap on wait time between retries (Step Functions SDK integration).

---

## Amazon CloudWatch

### Metrics
Key metrics to monitor for Glue jobs:
- `glue.driver.aggregate.numFailedTasks`
- `glue.driver.aggregate.numCompletedTasks`
- `glue.driver.aggregate.shuffleBytesWritten`
- `glue.driver.jvm.heap.usage`
- `glue.ALL.s3.filesystem.read_bytes` / `write_bytes`

Key metrics for Athena:
- `DataScannedInBytes` (per query, per workgroup)
- `QueryExecutionTime`
- `TotalExecutionTime`

### Alarms
```json
{
  "AlarmName": "glue-job-failure-alarm",
  "MetricName": "glue.driver.aggregate.numFailedTasks",
  "Namespace": "Glue",
  "Statistic": "Sum",
  "Period": 60,
  "EvaluationPeriods": 1,
  "Threshold": 1,
  "ComparisonOperator": "GreaterThanOrEqualToThreshold"
}
```

### Logs
Glue jobs write driver and executor logs to CloudWatch Logs. Enable continuous logging in the Glue job settings:
- Driver log group: `/aws-glue/jobs/logs-v2`
- Spark UI logs: `/aws-glue/jobs/spark-event-logs-v2`

Use CloudWatch Logs Insights to query across log groups:
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

---

## IAM — Least Privilege for Data Roles

### Service Role Pattern
Each Glue job, Lambda function, and Step Functions state machine must have a dedicated IAM role with the minimum permissions required.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-source-bucket",
        "arn:aws:s3:::my-source-bucket/path/to/data/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::my-target-bucket/output/*"
    },
    {
      "Effect": "Allow",
      "Action": ["glue:GetTable", "glue:GetDatabase", "glue:BatchCreatePartition"],
      "Resource": [
        "arn:aws:glue:eu-west-1:123456789012:catalog",
        "arn:aws:glue:eu-west-1:123456789012:database/my_database",
        "arn:aws:glue:eu-west-1:123456789012:table/my_database/*"
      ]
    }
  ]
}
```

Never use `"Resource": "*"` on sensitive actions. Never attach `AdministratorAccess` or `AmazonS3FullAccess` to data processing roles.

---

## Amazon EventBridge

### Scheduling
Use EventBridge Scheduler (not legacy CloudWatch Events) for new pipeline schedules.

```json
{
  "ScheduleExpression": "cron(0 6 * * ? *)",
  "FlexibleTimeWindow": { "Mode": "FLEXIBLE", "MaximumWindowInMinutes": 15 },
  "Target": {
    "Arn": "arn:aws:states:eu-west-1:123456789012:stateMachine:my-pipeline",
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
    "Input": "{\"source_date\": \"<aws.scheduler.scheduled-time>\"}"
  }
}
```

Use event-driven triggers (S3 event notifications via EventBridge) to decouple producers and consumers rather than polling.

---

## Cost Optimisation

### Glue
- Right-size DPU allocation. Start with 2–5 DPUs for small jobs and benchmark before increasing.
- Use Glue version 4.0+ for improved performance and Python 3.10 support.
- Enable job bookmarks to avoid reprocessing already-processed data.
- Use Spot instances (`--use-spot-instances true`) for non-critical, restartable jobs.
- Monitor `MaxCapacity` and `NumberOfWorkers` — over-provisioning is a common cost driver.

### Athena
- Partition data and always filter on partition columns; unpartitioned scans are the primary cost driver.
- Store data in Parquet or ORC with Snappy or ZSTD compression (typically 3–10x reduction vs CSV).
- Enable workgroup-level data scan limits.
- Use Athena query result reuse for repeated queries.
- Avoid running large exploratory queries without a `LIMIT` clause during development.

### S3
- Apply lifecycle policies to transition infrequently accessed data to cheaper storage classes.
- Use S3 Intelligent-Tiering for data with variable or unknown access patterns.
- Avoid excessive versioning on high-volume, frequently-overwritten prefixes unless a specific recovery requirement exists.
- Monitor S3 Storage Lens for per-prefix cost and access metrics.
