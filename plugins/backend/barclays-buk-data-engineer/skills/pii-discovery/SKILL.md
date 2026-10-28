---
name: pii-discovery
description: PII discovery knowledge covering BUK PII taxonomy, detection methods, confidence levels, classification output format, PCI-DSS scope, and GDPR special categories
user-invocable: false
owner: BUK Data Engineering Practice
effective_date: 2026-07-13
review_cadence: quarterly
status: approved
---

# PII Discovery Skill

## Governing Principles

1. **Never include discovered sensitive values in outputs.** Classification outputs must describe the nature and location of PII only. The actual data values must never appear in classification results, logs, or responses.
2. **Approved scanners only.** PII discovery must use tooling approved by the BUK Data Privacy and Information Security teams.
3. **Ambiguous or high-impact results require human review.** Automated classification is an input to human decision-making, not a final determination.
4. **Data minimisation.** The purpose of PII discovery is to enable data minimisation, appropriate access controls, and regulatory compliance — not to aggregate PII.

---

## What Constitutes PII in the BUK Context

Personal data is any information that can identify, directly or indirectly, a living individual. In the BUK financial services context, the following categories apply:

### Direct Identifiers
| Category | Examples | Notes |
|---|---|---|
| Full name | `first_name`, `last_name`, `full_name`, `display_name` | First name alone is usually not PII in isolation; in combination with other attributes it becomes identifying |
| National Insurance number | `ni_number`, `nino`, `national_insurance` | Unique UK government identifier; high sensitivity |
| Date of birth | `dob`, `date_of_birth`, `birth_date` | In combination with name or postcode, highly identifying |
| Postal address | `address_line_1`, `postcode`, `city`, `full_address` | All components individually and in combination |
| Phone number | `phone`, `mobile`, `telephone`, `contact_number` | Including international format |
| Email address | `email`, `email_address`, `contact_email` | Direct identifier; also used for account linkage |
| IP address | `ip_address`, `client_ip`, `source_ip` | Can identify an individual or household; GDPR-covered |
| Location data | `latitude`, `longitude`, `gps_coords`, `geolocation` | Precise location data is PII; broad regional data may not be |
| Biometric data | fingerprint templates, voice prints, facial recognition data | GDPR special category |
| Health / medical data | `health_condition`, `medical_history`, `disability_flag` | GDPR special category |

### Financial Identifiers
| Category | Examples | Notes |
|---|---|---|
| Bank account number | `account_number`, `bban` | In combination with sort code, uniquely identifies an account |
| Sort code | `sort_code` | Alone identifies the bank branch; combined with account number identifies the individual |
| Card number (PAN) | `card_number`, `pan`, `primary_account_number` | PCI-DSS in scope; see section below |
| CVV / CVV2 / CVC | `cvv`, `cvc`, `security_code` | PCI-DSS; must never be stored post-authorisation |
| Card expiry date | `expiry_date`, `card_expiry` | PCI-DSS sensitive authentication data |
| Track data | Magnetic stripe data; EMV chip data | PCI-DSS; must never be stored |
| PIN | Card PIN; PIN block | PCI-DSS; must never be stored |
| IBAN | `iban` | International bank account number; identifies individual account |
| BIC/SWIFT | `bic`, `swift_code` | Identifies institution, not individual; lower sensitivity |

---

## Detection Methods

### 1. Column Naming Heuristics
Match column names against a known vocabulary of PII-indicative names using exact match, substring match, and fuzzy matching.

```python
PII_COLUMN_NAME_PATTERNS = {
    "FULL_NAME": [
        r"^(full_)?name$", r"^first_name$", r"^last_name$", r"^surname$",
        r"^forename$", r"^given_name$", r"^display_name$"
    ],
    "EMAIL": [r"email", r"e_mail"],
    "PHONE": [r"phone", r"mobile", r"telephone", r"tel$"],
    "DOB": [r"dob$", r"date_of_birth", r"birth_date", r"birthdate"],
    "NI_NUMBER": [r"ni_?num", r"nino", r"national_insurance"],
    "POSTCODE": [r"postcode", r"post_code", r"zip"],
    "SORT_CODE": [r"sort_?code"],
    "ACCOUNT_NUMBER": [r"account_num", r"acc_?num", r"account_no"],
    "CARD_NUMBER": [r"pan$", r"card_num", r"card_no", r"primary_account"],
    "CVV": [r"cvv", r"cvc", r"security_code", r"card_verification"],
    "IP_ADDRESS": [r"ip_addr", r"client_ip", r"source_ip", r"remote_addr"],
}
```

Column name heuristics yield medium confidence. They should always be combined with data profiling.

### 2. Regex Pattern Matching
Apply regex patterns to a data sample (never the full dataset; use a statistically representative sample).

```python
import re

REGEX_PATTERNS = {
    "NI_NUMBER": re.compile(
        r"^(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{2}[0-9]{6}[ABCD]$",
        re.IGNORECASE
    ),
    "UK_POSTCODE": re.compile(
        r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}$",
        re.IGNORECASE
    ),
    "UK_PHONE": re.compile(
        r"^(\+44|0044|0)[\s\-]?[1-9][\d\s\-]{8,12}$"
    ),
    "EMAIL": re.compile(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    ),
    "SORT_CODE": re.compile(
        r"^\d{2}[\-\s]?\d{2}[\-\s]?\d{2}$"
    ),
    "ACCOUNT_NUMBER": re.compile(
        r"^\d{8}$"
    ),
    "CARD_NUMBER_LUHN": None,  # Use Luhn check, not regex alone
    "IP_V4": re.compile(
        r"^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$"
    ),
    "IP_V6": re.compile(
        r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    ),
}
```

For card numbers, always apply the Luhn algorithm in addition to a regex length/digit check. Do not use regex alone.

```python
def luhn_check(number: str) -> bool:
    digits = [int(d) for d in reversed(number.replace(" ", "").replace("-", ""))]
    return sum(
        d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2)
        for i, d in enumerate(digits)
    ) % 10 == 0
```

### 3. ML Classifiers
Named entity recognition (NER) models can identify PII in free-text columns (e.g. notes, comments, addresses stored as unstructured text). Use only approved NLP models from the BUK approved tooling register.

ML classifiers are appropriate when:
- The column contains unstructured or semi-structured text.
- Regex patterns would have unacceptably high false positive rates.

ML classifiers alone do not constitute sufficient evidence for a high-confidence classification. Combine with data profiling and human review.

### 4. Data Profiling
Profile a representative sample of column values:
- Data type distribution.
- Distinct value count and cardinality.
- NULL rate.
- Value length distribution.
- Percentage of values matching each regex pattern.

```python
def profile_column(df, column_name: str, sample_size: int = 10000) -> dict:
    sample = df.select(column_name).dropna().limit(sample_size)
    values = [row[0] for row in sample.collect()]
    return {
        "column": column_name,
        "sample_size": len(values),
        "distinct_count": len(set(values)),
        "null_rate": (sample_size - len(values)) / sample_size,
        "avg_length": sum(len(str(v)) for v in values) / max(len(values), 1),
        "regex_match_rates": {
            name: sum(1 for v in values if pattern.match(str(v))) / max(len(values), 1)
            for name, pattern in REGEX_PATTERNS.items()
            if pattern is not None
        },
    }
```

### 5. Metadata Labels
Check existing metadata labels, column comments, data catalog tags, and lineage provenance for existing PII classifications. Lineage from a known PII source is an evidence signal for classification.

---

## Confidence Levels and Evidence Requirements

| Confidence Level | Definition | Evidence Required |
|---|---|---|
| HIGH | Strong evidence from multiple independent methods | Column name heuristic + regex match rate >= 80% on sample, OR existing approved classification in data catalog |
| MEDIUM | Moderate evidence; plausible but not certain | Column name heuristic OR regex match rate 30–80% on sample, OR ML classifier score >= 0.75 |
| LOW | Weak evidence; possible but uncertain | Single weak signal (e.g. regex match rate < 30%, or ambiguous column name only) |
| NONE | No evidence of PII | No signals detected across all methods |

All HIGH confidence results should be reviewed and confirmed by the data owner or a privacy SME before a final classification is recorded.

---

## Classification Output Format

Classification outputs must use the following structure. The `evidence_state` field summarises the signals without including any actual data values.

```json
{
  "table": "finance.transactions",
  "column": "account_sort_code",
  "classification": "SORT_CODE",
  "pii_category": "FINANCIAL_IDENTIFIER",
  "pci_dss_scope": false,
  "gdpr_special_category": false,
  "method": ["column_name_heuristic", "regex_pattern"],
  "confidence": "HIGH",
  "evidence_state": "Column name matches sort_code heuristic pattern. Regex pattern matched 94% of sampled non-null values. Column length distribution consistent with sort code format (6-8 chars).",
  "requires_human_review": false,
  "reviewed_by": null,
  "reviewed_at": null,
  "scan_run_id": "scan-2026-07-13-001",
  "scanned_at": "2026-07-13T10:00:00Z"
}
```

Fields:
- `table`: fully qualified table name.
- `column`: column name only.
- `classification`: detected PII type.
- `pii_category`: high-level grouping (DIRECT_IDENTIFIER, FINANCIAL_IDENTIFIER, SPECIAL_CATEGORY, etc.).
- `pci_dss_scope`: boolean; true if the classification falls within PCI-DSS card data scope.
- `gdpr_special_category`: boolean; true for Article 9 special categories (health, biometric, etc.).
- `method`: list of detection methods that produced evidence.
- `confidence`: HIGH, MEDIUM, LOW, or NONE.
- `evidence_state`: human-readable description of the evidence, containing NO actual data values.
- `requires_human_review`: true for MEDIUM and LOW confidence, and for all GDPR special categories and PCI-DSS scope items.
- `reviewed_by` / `reviewed_at`: populated after human review.

---

## PCI-DSS Scope

The following data elements fall within PCI-DSS scope and are subject to the most stringent controls:

### Cardholder Data (CHD)
| Element | Storage Permitted | Notes |
|---|---|---|
| Primary Account Number (PAN) | Yes (if protected) | Must be masked when displayed; encrypted at rest and in transit |
| Cardholder name | Yes | Less sensitive; still requires protection |
| Service code | Yes | Two or three digit code on magnetic stripe |
| Expiry date | Yes | Required for transaction processing; must be protected |

### Sensitive Authentication Data (SAD)
| Element | Storage Permitted | Notes |
|---|---|---|
| Full magnetic stripe data | NO — never | Must not be stored after authorisation under any circumstances |
| CAV2 / CVC2 / CVV2 / CID | NO — never | Must not be stored after authorisation |
| PIN / PIN block | NO — never | Must never be stored |
| EMV chip data | NO — never | Full chip data must not be stored |

Any column identified as potentially containing SAD must be flagged for immediate escalation to the PCI compliance team. Do not attempt to classify or sample SAD further.

### Masking Requirements
When displaying PAN, the maximum number of digits that may be displayed is:
- First 6 digits + last 4 digits (industry standard).
- Example: `4111 11** **** 1111`

---

## GDPR Special Categories (Article 9)

The following data categories receive heightened protection under GDPR and require explicit legal basis and Data Protection Impact Assessment (DPIA):

| Category | Examples in banking context |
|---|---|
| Racial or ethnic origin | Customer ethnicity data (if collected) |
| Political opinions | Customer affiliation data |
| Religious or philosophical beliefs | Data from religious institution transactions |
| Trade union membership | Payroll deductions to trade unions |
| Genetic data | Not typically held in banking |
| Biometric data (for ID purposes) | Biometric authentication data |
| Health data | Medical insurance payments, disability disclosure |
| Sex life or sexual orientation | Not typically held in banking |

Any column identified as potentially containing GDPR special category data must be flagged for mandatory human review and must not be processed further without legal basis confirmation.

---

## Data Minimisation Principle

PII discovery feeds into data minimisation decisions:
1. **Is the column necessary?** If the PII column is not required for the stated business purpose, it should not be collected or retained.
2. **Can it be pseudonymised?** Replace direct identifiers with reversible tokens for analytical use cases.
3. **Can it be anonymised?** Apply k-anonymity, differential privacy, or aggregation to prevent re-identification. Anonymised data is no longer personal data under GDPR.
4. **What is the retention period?** PII must be deleted or anonymised when the retention period expires.

---

## Handling Ambiguous and High-Impact Results

### Ambiguous Results
A result is ambiguous when:
- Multiple PII types are plausible (e.g. an 8-digit numeric column could be an account number or a staff ID).
- Confidence is LOW or MEDIUM.
- The column name provides no signal.

**Action**: Flag as `requires_human_review: true`. Include the top candidate classifications and the evidence for each. Do not assign a definitive classification.

### High-Impact Results
A result is high-impact when:
- The classification is GDPR special category.
- The classification is PCI-DSS SAD.
- The column exists in a system classified as critical or highly regulated.
- The data volume is large (millions of rows).

**Action**: Escalate immediately to the data owner, the privacy SME, and (for PCI-DSS SAD) the PCI compliance team. Do not proceed with further automated processing of the column.

---

## Approved Scanners

PII discovery tooling must be approved by the BUK Information Security and Data Privacy teams before use. Unapproved tools must not be used to scan production data. Consult the BUK Approved Tooling Register for the current list of approved scanners.

When in doubt, raise a request through the BUK Data Privacy team before initiating any automated PII scan on a production dataset.
