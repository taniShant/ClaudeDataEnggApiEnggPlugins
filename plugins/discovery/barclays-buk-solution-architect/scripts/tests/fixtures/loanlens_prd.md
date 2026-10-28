---
title: "LoanLens — Multi-Lender Loan Comparison"
status: draft
created: 2026-10-01
updated: 2026-10-01
assumptions: 6
---

# Product Brief: LoanLens — Multi-Lender Loan Comparison

## Executive Summary

Borrowing £30,000 for a car should not require a spreadsheet, three browser tabs, and a finance degree. Today it does. Customers like Nathan — young, family-focused, cost-conscious — are left comparing headline APRs that may not reflect their actual rate, across lender websites that each present information differently, with no single view of what a loan will truly cost them month to month.

**LoanLens** is a multi-lender loan comparison experience embedded within the Barclays app and Online Banking. It lets customers enter their borrowing need, see personalised indicative rates from Barclays and the open market side by side, understand total cost of borrowing, and select the option that fits their life — all without leaving the Barclays ecosystem.

## The Problem

Nathan is 25, has two children, and needs £30,000 for a family car. His journey today results in fragmented comparison experience across multiple systems.

---

# PRD: LoanLens

## 0. Document Purpose

This PRD defines functional and non-functional requirements for LoanLens — a multi-lender loan comparison experience embedded within the Barclays app and Online Banking.

## 1. Vision

Barclays customers comparing personal loans today leave the Barclays ecosystem entirely — they Google, land on MoneySupermarket or Experian, compare generic representative APRs, and either overpay or damage their credit file applying to multiple lenders speculatively. LoanLens brings the comparison inside the bank.

## 2. Target User

**Jobs To Be Done**
- Functional: Compare personal loan options across lenders in one place, without multiple credit searches
- Emotional: Feel confident I'm getting the best deal for my family
- Contextual: Make this decision on my phone, between school runs

## 3. Glossary

- **Comparison View**: The primary results screen displaying loan options ranked by Total Cost of Credit
- **Loan Offer**: A single lender's loan product displayed in the Comparison View
- **Personalised Rate**: An indicative APR generated via Soft Credit Check, reflecting individual credit profile
- **Representative APR**: The rate at least 51% of approved applicants receive
- **Soft Credit Check**: A credit enquiry that does not appear on the customer's credit file
- **Total Cost of Credit**: The sum of all interest and fees paid over the full loan term

## 4. Features

### 4.1 Borrowing Input

**FR-1:** Loan Parameters Input — User can enter loan amount (£1,000–£50,000), purpose (Car, Home Improvement, Debt Consolidation, Holiday, Wedding, Other), and preferred term (1–7 years).

**FR-2:** Term Adjustment — User can adjust the loan term after initial input and see the Comparison View update within 2 seconds.

### 4.2 Soft Credit Check and Personalisation

**FR-3:** Consent and Soft Check Execution — System requests consent before executing soft enquiry. On consent, system returns a Personalised Rate, eligibility status, and affordability flags.

**FR-4:** Cached Eligibility — Soft Credit Check results are cached for 30 minutes. Term adjustments reuse cached data without re-executing.

### 4.3 Multi-Lender Comparison

**FR-5:** Comparison View Rendering — System displays ranked table ordered by Total Cost of Credit. Each row shows lender name, APR, Monthly Repayment, Total Cost, term, and fees.

**FR-6:** Data Freshness Labelling — Each Loan Offer displays freshness indicator. Rates older than 24 hours display an amber warning.

**FR-7:** Detail Comparison — User can select any two Loan Offers for side-by-side comparison showing monthly cash-flow impact and early repayment terms.

### 4.4 Selection and Handoff

**FR-8:** Barclays Selection Handoff — When user selects the Barclays Loan Offer, system hands off to existing loan application with pre-populated data.

**FR-9:** Competitor Selection Handoff — When user selects an Open-Market Lender, system displays confirmation and provides direct link to lender's application page.

### 4.5 Consumer Duty Compliance

**FR-10:** Information-Only Framing — All comparison UI copy uses information-only language. No recommendation language.

**FR-11:** Ranking Integrity — Ranking determined solely by Total Cost of Credit. No artificial advantage for Barclays offer.

**FR-12:** Vulnerable Customer Safeguard — When affordability concern detected, system surfaces free debt advice services before displaying results.

## 5. Non-Goals

- LoanLens is **not a credit broker**
- LoanLens does **not provide financial advice**
- Does **not cover secured lending, mortgages, credit cards, or car finance** in v1
- Does **not process applications for Open-Market Lenders** — links out only
- Does **not monetise via referral fees** in v1
- Does **not integrate Open Banking transaction data** for affordability enrichment in v1

## 6. MVP Scope

### In Scope
- Personal loans only (£1,000–£50,000)
- Barclays Personalised Rate via Soft Credit Check
- 3–5 Open-Market Lender Loan Offers
- Comparison View ranked by Total Cost of Credit
- Detail Comparison
- Barclays application handoff (pre-populated)
- Competitor outbound referral link

### Out of Scope for MVP
- Rate alerts or price monitoring
- In-app application completion for Open-Market Lenders
- Open Banking transaction-based affordability enrichment
- Multi-product comparison (credit cards, mortgages, car finance)

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Comparison-to-Barclays-application conversion rate | 15% |
| Lending journey retention (reduction in external comparison visits) | 20% reduction |
| Soft check completion rate | 80% |
| Comparison engagement depth (average time) | >90 seconds |
| Lending journey tNPS | +10 points |

## 8. Cross-Cutting NFRs

- **Performance**: Comparison View renders within 3 seconds (P95)
- **Availability**: 99.5% uptime during core hours
- **Security**: All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- **Accessibility**: WCAG 2.1 AA compliance
- **Data retention**: No user comparison data persisted beyond session

## 9. Integration and Dependencies

| System | Role |
|--------|------|
| barclayloan-calculator | Barclays APR/repayment calculation |
| ngcb-eligibilitycheck-api | Soft credit check / eligibility |
| calcafford-api | Affordability calculation |
| Aggregator API | Open-Market Lender rates (external partnership) |
| Barclays Loan Application | Post-comparison application flow |

## 10. Compliance and Regulatory

- **FCA Consumer Duty**: FR-10, FR-11, FR-12 encode minimum controls
- **Regulated advice boundary**: Information-only framing, no recommendation language
- **Credit search regulations**: Soft Credit Check complies with ICO, CRA agreements
- **Consumer Credit Act 1974**: Representative APR disclosure requirements

## 11. Assumptions

- 3-year term is most common UK personal loan term
- Aggregator API supports term-parameterised queries
- Barclays is willing to rank honestly even when offer not cheapest
- Barclays permits genuine outbound referral to competitors
- Success targets need baselining against current lending funnel

