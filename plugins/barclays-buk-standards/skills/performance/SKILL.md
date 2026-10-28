---
name: performance
description: BUK performance and NFR standards. Covers API tier latency budgets, VPT exit criteria by channel, timeout thresholds, and load testing requirements. Use when defining NFRs, reviewing service design, or implementing resilience patterns.
user-invocable: false
---

# BUK Performance Standards

> Source: BUK standard VPT (Volume and Performance Testing) NFRs — prescribed by Service.
> Success criteria are based on **average response times**, not percentile data.
> Alternative NFRs may apply where explicitly approved. All deviations must be documented in HLD/LLD.

---

## Section 1: API Tier Latency Budget

This cascade applies across all channels. Each tier's budget includes time spent in downstream tiers.

| API Tier | Description | Target | Aspiration | Risk if breached |
|---|---|---|---|---|
| **xAPI** (Experience) | Orchestration layer — DAF API | < 500ms (includes pAPI + sAPI time) | — | Thread exhaustion at channel; customer-facing timeout |
| **pAPI** (Process) | Process / workflow API | < 300ms (includes sAPI time) | — | xAPI will miss its 500ms budget |
| **sAPI** (System) | Domain / system of record API | < 100ms | < 20ms | pAPI misses 300ms → xAPI misses 500ms cascade failure |
| **Timeout threshold** | API Connect read/connect timeout | ≤ 500ms | — | Long-lived threads exhaust pool; service-wide slowdown or outage |

**Rule:** When implementing a new DAF API (xAPI/pAPI), always model the full cascade. If sAPI targets cannot be met, escalate before committing to xAPI SLA.

---

## Section 2: VPT Exit Criteria by Channel

These are the standard NFRs that must be met to exit VPT. They apply unless alternative approved NFRs are documented in the HLD.

### Barclays App (Mobile)

| NFR | New Changes | Existing Changes | Notes |
|---|---|---|---|
| Mobile Gateway response time | < 500ms | < 500ms or no worse than current | All exercised OP codes |
| Click-to-Load (end-to-end) | < 2000ms @ 3G / 500Kb/s incl. latency | < 2000ms or no worse than current | Measured at handset UI (Android + iOS) |
| xAPI response time | < 500ms | < 500ms or no worse than current | Includes pAPI + sAPI time |
| pAPI response time | < 300ms | < 300ms or no worse than current | Includes sAPI time |
| sAPI response time | < 100ms (aspiration < 20ms) | < 100ms or no worse than current | — |
| API Connect timeout | ≤ 500ms | ≤ 500ms or no worse than current | Connect and read timeout |
| Page weight | < 100KB per page | < 100KB per page | Out of scope for VPT; tested separately |

### Web (Online Banking / ROLB)

| NFR | New Changes | Existing Changes | Tools |
|---|---|---|---|
| Page load time (LCP) | < 2s | < 2s or no worse than current | Google Lighthouse, Chrome DevTools |
| Server-side application response | < 500ms | < 500ms or no worse than current | LoadRunner, JMeter, Chrome DevTools |
| xAPI response time | < 500ms | < 500ms or no worse than current | LoadRunner, JMeter, Chrome DevTools |
| pAPI response time | < 300ms | < 300ms or no worse than current | — |
| sAPI response time | < 100ms (aspiration < 20ms) | < 100ms or no worse than current | — |
| API Connect timeout | ≤ 500ms | ≤ 500ms or no worse than current | — |
| Overall page weight | < 1250KB compressed | < 1250KB or no worse than current | Google Lighthouse, Chrome DevTools |

---

## Section 3: Timeout and Retry Conventions

- API Connect and read timeout: **≤ 500ms** — aligns with xAPI budget
- Long-lived threads reduce available pool capacity; keep connections short-lived
- For retries: use exponential backoff with jitter; ensure downstream calls are idempotent before retrying
- Circuit breaker: trip on sustained latency above threshold, not only on errors — a slow sAPI degrades the full cascade

---

## Section 4: Load Testing Requirements

- VPT is a mandatory exit gate for production release
- Test must exercise all Operational Codes (OP codes) in scope
- For existing changes: regression baseline comparison is acceptable justification where absolute targets cannot be met
- Approved tools: LoadRunner, JMeter (backend); Google Lighthouse / Chrome DevTools (web frontend)
- Performance test environments must not use production data

---

## Section 5: Areas Still to Define

The following areas need source documents from BUK Principal Engineers:

- Throughput / TPS targets per channel (baseline and peak)
- Autoscaling trigger thresholds
- Cache TTL conventions (reference data vs. journey cache)
- Bulkhead and isolation patterns
- Capacity review process for new journeys

---

## How to Contribute

Raise additional source documents with BUK Principal Engineers. Suggested inputs:

- Capacity and throughput standards per channel
- DAF performance and resilience guidance
- Approved NFR deviation process documentation
