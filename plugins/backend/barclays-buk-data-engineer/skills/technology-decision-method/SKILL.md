---
name: technology-decision-method
description: How technology choices are evaluated and documented by the BUK Data Engineer worker
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# Technology Decision Method

## Principle

No technology is chosen from preference, familiarity or default. Every technology selection must produce an Architecture Decision Record (ADR). The worker generates a draft ADR for human approval; it does not approve technology decisions.

---

## ADR Structure

Every ADR produced by the worker must include the following sections in order:

### 1. Problem and Scope
A clear statement of the engineering problem being solved and the boundaries of the decision (which systems, teams, environments and time horizon are in scope).

### 2. Hard Constraints
Non-negotiable requirements that eliminate candidates regardless of other criteria (e.g. regulatory residency, enterprise security policy, approved technology list, budget ceiling).

### 3. Approved Candidates
The set of technologies eligible for evaluation. Only technologies listed in the `approved_technology_candidates` input or verified as approved through authoritative context may be included. Technologies not on the approved list must not be evaluated or recommended.

### 4. Workload Characteristics
A structured description of the workload that the technology must serve:

| Characteristic | Description |
|---|---|
| Processing pattern | Batch, micro-batch, streaming or hybrid. |
| Volume | Estimated data volume (rows, bytes) at current state and projected horizon. |
| Velocity | Ingestion and processing rate requirements. |
| Latency | End-to-end latency requirement (source event to query-ready). |
| Concurrency | Expected concurrent readers, writers and pipeline executions. |
| Retention | Data retention period and tiering requirements. |

### 5. Data Characteristics
Data types, formats, schema evolution requirements, sensitivity classifications and lineage requirements relevant to the decision.

### 6. Security, Privacy and Residency
Applicable security controls, data classification constraints, privacy obligations and geographic data residency requirements. Citations to applicable policy standards required.

### 7. Integration and Lineage
Integration points with upstream and downstream systems; lineage capture requirements; catalogue and metadata registration requirements.

### 8. Resilience, Recovery and Operability
Availability targets, recovery point objective (RPO), recovery time objective (RTO), failure mode expectations, alerting and runbook requirements.

### 9. Delivery Skills and Lead Time
Assessment of existing team skills per candidate; estimated lead time to production-ready delivery per candidate; training or hiring requirements.

### 10. Cost Model
A cost model for each candidate including:

- Unit cost assumptions (compute, storage, licensing, egress).
- Confidence level of the estimate (`high`, `medium`, `low`) with justification.
- Time horizon (e.g. 12-month, 3-year total cost of ownership).
- Sensitivity analysis: key variables whose change would materially alter the ranking.

### 11. Portability and Lock-in
Assessment of vendor lock-in risk per candidate; portability of data formats, APIs and operational tooling; exit cost estimate.

### 12. Benchmark and PoC Evidence
Where available, results of benchmarks or proof-of-concept work must be cited with methodology, date and source. Where not available, absence must be noted and the impact on confidence stated.

### 13. Weighted Decision Matrix
A matrix scoring each approved candidate against the decision criteria below. Weights must be either explicitly supplied by the user (marked `USER_SUPPLIED`) or, if proposed by the worker, clearly marked `PROPOSED` and subject to human review before the ADR is considered final.

#### Decision Criteria

| Criterion | Description |
|---|---|
| Functional fit | Degree to which the technology meets the stated functional requirements. |
| Volumes and velocity | Ability to handle current and projected workload at required throughput. |
| Latency | Ability to meet end-to-end latency requirements. |
| Resilience | Failure tolerance, replication and recovery capabilities. |
| Operability | Ease of operation, monitoring, patching and incident response. |
| Security | Native security controls, encryption, access management. |
| Data governance | Lineage, cataloguing, classification and retention support. |
| Skills availability | Team familiarity and market availability of skills. |
| Portability | Openness of formats and APIs; ease of migration away. |
| Delivery lead time | Time from decision to production-ready deployment. |
| Total cost of ownership | Three-year TCO including all cost dimensions. |

### 14. Recommendation
The recommended technology with:
- Statement of why it scores highest against the weighted criteria.
- Alternatives considered and the primary reason each was rejected.
- Key trade-offs accepted by choosing this option.
- Conditions that would change the recommendation (e.g. volume growth beyond threshold, change in residency requirement).

### 15. Human Approver
Named role or individual responsible for approving this ADR before it is considered final. The worker-generated ADR is a proposal; it has no authority until approved.

---

## Platform Neutrality

No platform-specific skill or plugin may score its own platform more favourably than alternatives by default. The evaluation criteria and their weights live in this neutral shared skill. Platform plugins supply factual capability and constraint evidence only; they do not supply scores or weights.

If a platform plugin supplies scoring, that scoring must be marked `PLATFORM_SUPPLIED` and the worker must present it separately from the independently reasoned matrix, allowing the human reviewer to reconcile them.

---

## Approved Candidates Policy

The worker compares only technologies that are:

1. Explicitly listed in the `approved_technology_candidates` input provided at invocation, or
2. Verified as approved through authoritative context (e.g. enterprise technology registry, platform standards document) loaded at runtime with `VERIFIED_STANDARD` evidence state.

Technologies outside the approved set must not be evaluated, scored or recommended. If the user requests evaluation of an unapproved technology, the worker must note this, explain the constraint and request human escalation to obtain approval before proceeding.

---

## Cost Model Requirements

The cost model must be present for every ADR. A cost model that omits any of the following is incomplete:

- Explicit unit cost assumptions for each cost dimension (compute, storage, licensing, egress, support).
- Confidence level (`high`, `medium`, `low`) with a stated basis for that confidence.
- Time horizon clearly stated (e.g. 12-month run rate, 3-year TCO).
- At least one sensitivity variable identified with a plausible range and its effect on the ranking.

Cost models marked `low` confidence must include a note on what information would be required to raise confidence and who can supply it.
