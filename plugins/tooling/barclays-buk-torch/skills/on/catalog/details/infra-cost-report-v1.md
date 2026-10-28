# infra-cost-report-v1

| Field | Value |
| --- | --- |
| Capability ID | `infra-cost-report-v1` |
| Plugin name | `infra-cost-tools` |
| Component type | tool-plugin |
| Owner | finops-team |
| Action scope | read-only |
| Invocation mode | tool/agent — no slash command |
| Installation / release | infra-cost-tools >= 1.4.0; install on request via go/finops-plugin; requires approved cost-explorer IAM role |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- AWS account ID or account alias to query
- Time range: ISO 8601 start and end dates (default: current calendar month)
- Optional: service filter (e.g., restrict to EC2, RDS, or a named cost-allocation tag value)
- Optional: granularity — `daily` or `monthly` (default: `monthly`)

## Preconditions

- The caller's environment has valid AWS credentials with the approved `finops:ReadCostExplorer` IAM policy
- The target account ID is within the caller's permitted billing scope
- Cost Explorer is enabled on the target account (it is not enabled by default on new AWS accounts)

## Expected outputs

- Structured cost breakdown by service and time period, returned as a tool result in the conversation
- Total spend, top-five cost drivers, and month-over-month delta where prior-period data is available
- No files written to disk; results are returned in-context only

## Exclusions

- Does not produce forecasts or budget recommendations
- Does not cover non-AWS infrastructure costs (GCP, Azure, on-premises)
- Does not modify cost allocation tags, budgets, or alerts
- Does not provide per-resource granularity; service-level aggregation only

## Verification

After the tool returns results, verify the reported total against the AWS Cost Explorer console for the same account, time range, and granularity. The check applies to the query parameters recorded in the tool result. Discrepancies greater than 1% in the total should be reported to the `finops-team` owner.
