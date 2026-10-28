# barclays-buk-security-architect-security-architect-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-security-architect-security-architect-agent-v1` |
| Plugin name | `barclays-buk-security-architect` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-security-architect@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `ARCHITECTURE_PATH` — path to architecture markdown file (typically the output of solution-architect-agent)
- `CODE_PATH` — path to code directory to scan, or `"none"` if no code scan required
- `REVIEW_TYPE` — scope of review: `design`, `code`, or `both`
- `OUTPUT_PATH` — absolute path where the security review document should be written

## Preconditions

- `ARCHITECTURE_PATH` must exist and be readable for design or both review types; if absent, threat model will be based on additional context only and coverage limitations will be stated in Flags
- The plugin must be installed: `/plugin install barclays-buk-security-architect@barclays-cio-buk`
- For code review: `CODE_PATH` must point to an accessible directory

## Expected outputs

1. Structured security review markdown document at `OUTPUT_PATH` containing:
   - STRIDE threat model covering all six threat categories per component and data flow
   - Security design review with pass/fail against Barclays security checklist (authentication, authorisation, data classification, encryption, API headers, rate limiting, secrets management, logging)
   - Code scan findings (if `CODE_PATH` provided): Critical, High, and Medium vulnerabilities with file path, line number, severity, description, and recommended fix
   - Compliance validation against Barclays Secure Coding Practices v1.2.6 with gap analysis
   - Security Sign-Off Recommendation: Approved, Conditional, or Rejected

## Exclusions

- Does not implement security controls, remediations, or fixes — it identifies and documents them only
- Does not block deployments or pipeline stages — sign-off recommendation is advisory; enforcement is the caller's responsibility
- Does not perform penetration testing or dynamic analysis
- Does not grant or revoke access or credentials
- Does not review non-security quality concerns (performance, accessibility, maintainability)

## Verification

Check that `OUTPUT_PATH` exists and contains all five sections. Confirm the STRIDE table covers all six threat categories, the security design checklist documents a status for each item with remediation notes for failures, and a Sign-Off Recommendation (Approved/Conditional/Rejected) is stated at the end. If a code scan was requested, confirm findings include file path and severity for each issue. Any placeholder skills or coverage gaps should appear in the Flags section.
