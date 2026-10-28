# security-scan-v1

| Field | Value |
| --- | --- |
| Capability ID | `security-scan-v1` |
| Plugin name | `security-tools` |
| Component type | skill-user-only |
| Owner | appsec-team |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | security-tools >= 3.0.0; provisioned to all engineers via the baseline plugin set; see go/appsec-scanner for access troubleshooting |
| Native command | `/security-tools:run-security-scan` |
| Skill name | `run-security-scan` |

## Description

Run a full security scan of the repository using the approved scanner, produce a findings report, and open tracked issues for any findings above the configured severity threshold.

## When to use

Use before a major release, after introducing a new dependency or infrastructure component, or when a security review is explicitly required. Not for quick dependency audits during routine development; use the lightweight advisory check for that.

## Inputs

- Repository root path (defaults to the current working directory if not specified)
- Target scan profile: `full`, `dependencies-only`, or `secrets-only` (default: `full`)
- Severity threshold for issue creation: `critical`, `high`, or `medium` (default: `high`)
- Optional: list of paths to exclude from the scan

## Preconditions

- The approved scanner binary is installed and reachable on `PATH`
- The caller has read access to all files under the target path
- The issue tracker integration is configured (required only for automatic issue creation)
- The repository has no uncommitted changes that would prevent a clean scan baseline (advisory; scan proceeds regardless)

## Expected outputs

- Machine-readable findings file at `.security/scan-results-<timestamp>.json`
- Human-readable summary printed to the terminal: total findings by severity, new findings since last scan, scanner version, and scan duration
- Tracked issues created in the configured issue tracker for findings at or above the severity threshold (only when the integration is available)

## Exclusions

- Does not perform penetration testing or dynamic application security testing (DAST)
- Does not remediate findings; produces a findings report only
- Does not scan running services or containers, only source artefacts in the repository
- Does not replace a formal third-party security audit

## Verification

After the workflow completes, confirm that `.security/scan-results-<timestamp>.json` exists and is well-formed JSON. Re-run the scanner CLI directly on a known-vulnerable test fixture (`test/fixtures/security/known-vuln/`) and verify the output contains the expected finding ID. This check applies to the scanner version recorded in the output file.
