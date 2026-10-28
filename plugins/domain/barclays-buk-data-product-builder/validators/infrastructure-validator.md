# Validator: infrastructure-validator

**Purpose**: Validate S3 locations and detect cross-environment value contamination in generated artefacts.

**Severity**: WARNING (S3 violations) / FLAG (cross-env contamination) — generation continues; user should fix before deployment.

**Platform**: Glue + Databricks

---

## Part A — S3 Location Validation

### Rules

#### Bucket Name Rules (AWS S3)

- 3–63 characters
- Lowercase letters, numbers, and hyphens only
- Must not start or end with a hyphen
- Must not contain consecutive hyphens
- Must not be formatted as an IP address
- Pattern: `^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$`

#### Prefix/Path Rules

- Must not start with `/` (S3 prefixes are relative, not absolute)
- Must not contain `..` (path traversal)
- Allowed characters: letters, numbers, `/`, `-`, `_`, `.`
- Must not end with `/` (avoid ambiguity with directory-like paths)

#### Bucket Name Pattern for BUK CDAO (informational check — warning only)

Expected patterns:
- Pattern 1 (Iceberg): `{env_prefix}-pre-{bucket_shortname}-{account_id}-eu-west-1`
- Pattern 2 (Hive): `{env_prefix}-{tenancy}-{account_id}-eu-west-1`

### Validation Checks

For each S3 location in `session_state.mesh_json_s3_locations` and dtxog config:

1. Bucket name conforms to AWS naming rules
2. Bucket name matches expected BUK CDAO pattern (informational warning if not)
3. Prefix does not start with `/`
4. Prefix does not contain `..`

### Pass Condition (Part A)

All S3 values conform to AWS naming rules.

### Fail Action (Part A)

WARNING — list invalid values:
```
⚠️ S3 location validation warnings:
  dev bucket '{value}' — {specific violation}
  prd prefix '{value}' — must not start with /
```

---

## Part B — Cross-Environment Value Detection

### Checks

#### Check 1 — Account ID Cross-Contamination

Check each env block in dtxog config:

| Section | Allowed Account ID Pattern |
|---|---|
| `dev` | DDA dev: `767397940910`; BCA dev: `998403225349` |
| `uat` | DDA uat: `590184123059`; BCA uat: `105695603553` |
| `prd` | DDA prd: `194722397519`; BCA prd: `233301737440` |

If a dev account ID (e.g. `767397940910`) appears in the `prd` block: VIOLATION.

#### Check 2 — S3 Bucket Env Prefix Cross-Contamination

S3 bucket names contain env prefix:
- `dev1-pre-*`, `dev-*` → should appear only in dev sections
- `uat1-pre-*`, `uat-*` → should appear only in uat sections
- `prd1-pre-*`, `prd-*` → should appear only in prd sections

If a `dev-*` bucket name appears in a `prd` section: VIOLATION.

#### Check 3 — State Machine Env Tags

State machine names should not contain opposite-env identifiers:
- `*-dev` state machine in `prd` section → VIOLATION

#### Check 4 — package-file Paths

Crypto `.whl` package-file S3 paths contain env prefix:
- `dev-oth-bukapps-*` must appear only in `dev` section
- `uat-oth-bukapps-*` must appear only in `uat` section
- `prd-oth-bukapps-*` must appear only in `prd` section

### Pass Condition (Part B)

No cross-environment values detected.

### Fail Action (Part B)

FLAG violation (not halt):
```
⚠️ Cross-environment value detected in {filename}:
  prd section contains dev account ID '767397940910' — should be '194722397519'
  prd section contains dev S3 bucket 'dev-fdp-mortgage-767397940910-eu-west-1'
  
  Fix these before deploying to production.
```
