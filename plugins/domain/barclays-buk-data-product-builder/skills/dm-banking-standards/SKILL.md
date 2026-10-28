---
description: "Domain knowledge for UK retail and commercial banking — FCA Consumer Duty rules, product taxonomy (mortgages, cards, savings, loans), regulatory terminology, and banking-specific data conventions used by the BRA agent."
user-invocable: false
owner: "Satish Khanna <satish.khanna@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-21
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-09-21

# DM Banking Standards

Domain knowledge for Business Requirements Analysis in UK retail and commercial banking.

---

## FCA Consumer Duty (PS22/9)

> See `barclays-buk-standards:consumer-duty` for full CDA structure, CUNA, NAPA, and FG22/5 obligations.

---

## PROD Rules (Product Governance)

| Rule | Requirement | Data Need |
|------|-------------|-----------|
| PROD 4.2 | Manufacturers must define **target market** for each product | Target market definitions per product, customer segment mappings |
| PROD 4.3 | Must monitor product performance **against target market** | Outcome metrics, product-customer performance data |
| PROD 4.4 | Must take **remedial action** if product delivers poor outcomes | Action triggers, thresholds, remediation records |
| PROD 7.3 | Distributors must obtain target market info from manufacturers | Distributor-manufacturer data sharing, eligibility rule propagation |

---

## Vulnerability Framework (FG21/1)

> See `barclays-buk-standards:vulnerable-customers` for FCA FG21/1 guidance, TEXAS model, and inclusive design obligations.

---

## GDPR / Data Protection

| Principle | Requirement for Data Models |
|-----------|-----------------------------|
| **Lawfulness** | Every data point must have a documented lawful basis (consent, contract, legitimate interest, legal obligation) |
| **Purpose limitation** | Data collected for one purpose cannot be repurposed without compatible basis |
| **Data minimisation** | Only collect data points with a documented business need |
| **Accuracy** | Must have data quality expectations (completeness, timeliness, correctness) |
| **Storage limitation** | Every data point must have a defined retention period |
| **Integrity & confidentiality** | PII and Sensitive data must be classified and protected |
| **Accountability** | Must maintain processing records (Article 30) and evidence compliance |

### Data Sensitivity Classification

| Level | Examples | Handling |
|-------|----------|---------|
| **PII** | Name, address, DOB, NI number, contact details | Encryption at rest, masking in non-prod, DSAR-ready |
| **Special Category** | Health data, racial/ethnic origin, biometric | Explicit consent or legal obligation; additional safeguards |
| **Confidential** | Account balances, transaction history, credit scores | Role-based access, audit logging |
| **Internal** | Product codes, system identifiers, process flags | Standard access controls |

---

## PSD2 / Open Banking

| Aspect | Requirement | Data Implication |
|--------|-------------|------------------|
| **Account access** | TPPs can access account data with customer consent | Consent records, TPP authorisation logs, API call audit |
| **Payment initiation** | TPPs can initiate payments with customer consent | Payment instruction audit, fraud monitoring per channel |
| **Strong Customer Authentication** | SCA required for electronic payments and account access | Authentication method, SCA exemption flags, challenge events |
| **Data sharing** | Must share account data in standardised formats | Data standardisation, API field mappings, format compliance |

---

## Treating Customers Fairly (TCF)

Legacy framework (pre-Consumer Duty) — still referenced in internal governance:

| Outcome | Description |
|---------|-------------|
| TCF-1 | Customers can be confident they are dealing with firms where fair treatment is central |
| TCF-2 | Products and services are designed to meet the needs of identified customer groups |
| TCF-3 | Customers are provided with clear information before, during, and after sale |
| TCF-4 | Advice is suitable and takes account of customer circumstances |
| TCF-5 | Products perform as firms have led customers to expect |
| TCF-6 | Customers do not face unreasonable post-sale barriers |

---

## Competitor Benchmarks

### HSBC

- Product suitability monitoring via automated MI dashboards
- Monthly outcome testing across full product estate
- Customer journey tracking from acquisition to closure
- Digital-first eligibility checking with real-time decisions
- Global consistency framework adapted per jurisdiction

### Lloyds Banking Group

- Fair value assessment framework across brands (Lloyds, Halifax, BoS)
- Vulnerability detection through NLP on customer interactions
- Product lifecycle management with automated sunset triggers
- Customer outcome scoring model (proprietary)
- Integrated data platform consolidating retail and commercial

### Santander UK

- Product governance committee with data-driven agenda
- Eligibility engine refreshed daily with multi-factor scoring
- Closed product monitoring via dedicated analytical team
- Customer segmentation model incorporating propensity and risk
- TCF scorecard embedded in product design process

### NatWest Group

- Purpose-led product design with sustainability overlay
- Customer vulnerability index across all channels
- Open Banking data enrichment for affordability
- Real-time eligibility decisioning via API-first architecture
- Regulatory reporting automation (Consumer Duty board packs)

### Nationwide

- Member value framework replacing pure profit metrics
- Product simplification programme reducing legacy complexity
- Mutual-specific outcome testing (member vs shareholder value)
- Digital savings platform with behavioural nudges
- Mortgage affordability model incorporating future rate scenarios

---

## Product Taxonomy — Typical Data Attributes

### Current Accounts

Account type, sort code, account number, opening date, status, overdraft limit, arranged/unarranged usage, fee structure, transaction volumes, average balance, dormancy indicators, channel usage (branch, digital, telephone), switching indicators (CASS in/out)

### Savings

Product type (easy access, fixed term, ISA, regular saver), interest rate (AER, gross), bonus rate, bonus expiry, balance tiers, withdrawal restrictions, maturity date, tax wrapper status, annual allowance usage, customer engagement (last login, last transaction)

### Mortgages

Product type (fixed, variable, tracker, offset), loan amount, property value, LTV ratio, interest rate, term remaining, monthly payment, arrears status, forbearance flags, payment holidays, ERC applicability, property type, postcode, valuation date

### Personal Loans

Loan type (secured/unsecured), purpose, principal amount, outstanding balance, APR, term, monthly instalment, payment status, arrears stage, collections flag, write-off indicator, top-up eligibility, consolidation history

### Credit Cards

Card type (reward, balance transfer, purchase), credit limit, available balance, statement balance, APR (purchase, cash, BT), promotional rates, minimum payment, payment behaviour (full/minimum/between), utilisation ratio, over-limit indicators, reward points balance, annual fee

### Insurance (Life, Home, Travel)

Policy type, cover level, sum assured/insured, premium amount, payment frequency, renewal date, claims history, claims status, claim amount, exclusions, endorsements, special terms, cancellation date, cancellation reason, cooling-off usage

### Business Banking

Business type (sole trader, limited, partnership), SIC code, sector classification, turnover band, account type (BCA, business savings, merchant), lending facilities, invoice finance, asset finance, relationship manager, segmentation tier, digital adoption score, product holding count

---

## Agent Self-Check

Before completing a business requirement document, verify:

- [ ] **Consumer Duty coverage**: At least one of the four outcomes is addressed with specific data points (see `barclays-buk-standards:consumer-duty`)
- [ ] **Target market defined**: The requirement specifies which customer segments are in scope
- [ ] **Vulnerability considered**: Vulnerability drivers are assessed for relevance; if not applicable, state why (see `barclays-buk-standards:vulnerable-customers`)
- [ ] **Regulatory traceability**: Every requirement traces to a regulatory driver or business objective
- [ ] **Sensitivity classified**: Every data point has a sensitivity level (PII / Special Category / Confidential / Internal)
- [ ] **Temporal need stated**: Every data point specifies current-only, historical, or event-based tracking
- [ ] **Competitor context**: At least one competitor benchmark is referenced where relevant
- [ ] **Retention period**: Data retention expectations are documented or flagged as a gap
