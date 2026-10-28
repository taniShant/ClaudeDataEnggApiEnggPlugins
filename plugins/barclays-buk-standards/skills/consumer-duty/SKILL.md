---
name: consumer-duty
description: Barclays Consumer Duty standards for BUK product and service delivery. Covers FCA Consumer Duty obligations, Consumer Duty Assessment (CDA) structure, CUNA requirements, NAPA submissions, ORAC management, and FCA FG22/5 requirements including sludge prohibition, algorithm fairness, co-manufacturer obligations, and board assessment content. Use when generating, reviewing, or validating product requirements, customer communications, or governance artefacts.
user-invocable: false
---

# BUK Consumer Duty Standards

> **Strawman — owned by BUK Principal Engineers.**
> Derived from Barclays CDA documentation: CDA – Products & Services v6 (11/05/2026), CDA – Product Withdrawal v1.0 (21/04/2026), Consumer Understanding Comms Forums and Content v3 (Sept 2025), and CDA CoPilot Guidance FINAL.
> Also incorporates: FCA FG22/5, "Final non-Handbook Guidance for Firms on the Consumer Duty," July 2022.
> Source documents are Restricted — Internal.
> Also read alongside `barclays-buk-standards:vulnerable-customers` — FCA FG21/1 builds the foundation for vulnerability obligations within Consumer Duty.

---

## 1. Core Principle

The FCA Consumer Duty requires Barclays to deliver **good outcomes** for retail customers across four outcome areas:

| Outcome Area | What it means |
|---|---|
| **Products & Services** | Products are designed to meet the needs of the target market |
| **Price & Value** | Customers receive fair value — price is proportionate to benefit |
| **Consumer Understanding** | Communications are clear and support informed decisions |
| **Consumer Support** | Customers can get the help they need, when they need it |

Every product, service, journey, and communication must be assessed against these four areas. The Product Owner has **full accountability** for the accuracy and completion of all Consumer Duty artefacts. AI tools can assist with drafting and structuring — they do not replace human judgement or oversight.

**The overarching standard (FCA FG22/5, para 1.7):**
> "Firms should act to deliver good outcomes for retail customers... Firms should consider whether the outcomes their customers receive reflect the standard they would expect if they were the customer."

**The "same standards" test (FCA FG22/5, para 5.3):**
Firms must have monitoring capabilities that match the sophistication of their sales and revenue capabilities. If a firm can measure customer acquisition in granular detail, it must apply equivalent capability to measuring customer outcomes.

**Literacy baseline (FCA FG22/5 / GDS standard):**
1 in 7 UK adults have literacy skills at or below the level expected of a 9–11 year old. 17.7 million adults (34%) have poor or low numeracy with financial concepts. Mass-market products must communicate at the Government Digital Service benchmark: write for a 9-year-old reading age.

---

## 2. Consumer Duty Assessment (CDA)

The CDA is the primary regulatory artefact. It is mandatory at:
- **New product launch** (NAPA submission)
- **Material product change** (trigger event)
- **Annual review** (on-sale and closed book products)
- **Product withdrawal**

### 2.1 CDA Types

| CDA Type | When to use |
|---|---|
| **Products & Services CDA** | On-sale and closed book products, product-specific journeys, NAPA submissions |
| **Product Withdrawal CDA** | When withdrawing or restricting access to a product or service |
| **Product Distribution Assessment** | When Barclays acts solely as distributor of insurance products (not this CDA type) |

### 2.2 CDA Structure — Products & Services

The CDA has three sections. All sections are required for on-sale/off-sale assessments. NAPA submissions require sections marked ✅ below.

**Section A — Customer Needs & Product/Service Design**

| # | Area | Key questions | NAPA |
|---|---|---|---|
| 1 | Target Market | Who is the product designed for? Does distribution reach them? How are vulnerable customers supported? | ✅ |
| 2 | Product Family | How does this product sit alongside others in the range? | ✅ |
| 3 | Product/Service Features | What features deliver value? How are they aligned to target market needs? Are features sustainable? | ✅ |
| 4 | Limitations, Fees & Non-Financial Costs | What limitations exist? Are fees proportionate? Could pricing cause harm? | ✅ |
| 5 | Customer Understanding | Are communications timely and clear? Is CUNA required? Are vulnerable customers considered? | ✅ |
| 6 | Customer Support | What support channels exist? Are there unreasonable barriers to exit or switch? | ✅ |
| 7 | Pricing, Business Model & Income | How is the product priced? Is income generation causing harm or unfair advantage? | ✅ |

**Section B — Customer Outcomes Analysis**

| # | Area | Key questions | NAPA |
|---|---|---|---|
| 8A | Data Analysis (existing products) | Use data across 7 themes to evidence good outcomes. Are known risks being mitigated? | — |
| 8B | Data Analysis (new products/NAPA) | Use customer research and testing to forecast outcomes. | ✅ |
| 9 | Benchmarking | Is the product an outlier vs competitors on fees, features, or limitations? | — |
| 10 | Future Monitoring | What KIs will monitor outcomes? At what frequency? | ✅ |

**The 7 outcome themes for data analysis:**
1. Target Market adherence
2. Product Family (if applicable)
3. Product/Service Features utilisation
4. Impact of limitations, fees/charges and non-financial costs
5. Customer Understanding
6. Customer Support
7. Pricing, Business Model & Income Generation

**Section C — Risks to Good Customer Outcomes**

| # | Area | What to include |
|---|---|---|
| 11 | Risks & Mitigation | Risk description, existing mitigants, RICM rating, new actions required, residual risk |
| 12 | Trailing Actions | Risk reference, action, timing, governance forum for monitoring |
| 13 | Harms & Issues | ORAC reference, issue summary, remediating action, closure date |

**Executive Summary & MD Attestation** — completed last. MD must select one of three conclusions:
1. Product is delivering good outcomes and fair value
2. New risks identified — actions in place will provide effective mitigation
3. Potential risks identified requiring further investigation — product continues while investigation proceeds

### 2.3 CDA Structure — Product Withdrawal

Used when withdrawing or restricting access to a product. Additional considerations beyond the standard CDA:

**Section A — Customer Needs during Withdrawal**
- Can customers continue to use features during withdrawal? For how long?
- Are accrued benefits/rewards protected through the withdrawal period?
- Are customers being given adequate time and information to consider alternatives?
- Are there unreasonable barriers to exit or switch?
- Are communications tailored for vulnerable customer groups?
- Has the FCA been engaged if withdrawal significantly impacts vulnerable customers or overall market supply?

**Section B — Customer Outcomes Analysis**
- Data must show the impact of withdrawal across customer groups
- Must specifically consider customers with characteristics of vulnerability
- Must forecast complaints and communication responses

**Executive Summary conclusion** must confirm customers will receive good outcomes *through the period of product withdrawal*.

---

## 3. FCA FG22/5 — Specific Firm Obligations

These obligations apply to all product design, journey design, and commercial decision-making and supplement the CDA process.

### 3.1 Sludge — Prohibited Practices

**Sludge** is defined as friction that exploits customer inertia or creates unnecessary barriers to acting in their interests. Unlike **appropriate friction** (e.g. confirmation screens to prevent accidental irreversible actions), sludge is a breach of the Consumer Duty.

**Prohibited examples (FCA FG22/5, para 8.5–8.8):**

| Practice | Why prohibited |
|---|---|
| Requiring customers to cancel by phone only when they signed up online | Asymmetric friction that exploits inertia |
| Burying cancellation/unsubscribe options in menus or fine print | Obscures exit path |
| Making forbearance options hard to find or access | Exploits financial distress |
| Discreet or pre-selected radio buttons that retain a product or add charges | Choice architecture designed against customer interests |
| Multi-step login requirements before accessing complaint or exit flows | Disproportionate barrier |
| Long hold times or repeated call transfers for cancellation requests | Operational friction designed to deter |
| Complex language or excessive steps for straightforward decisions | Cognitive burden without benefit to customer |

**Appropriate friction (permitted):**
- Confirmation screens for irreversible actions (transfers, account closure)
- Multi-factor authentication to prevent fraud
- Cooling-off period disclosures
- Prominent risk warnings for investment products

When designing any cancellation, complaint, exit, switching, or forbearance journey, a sludge impact assessment is required. Flag for legal/compliance review if any of the above patterns are present.

### 3.2 Algorithms and AI — Fairness Obligations

Using algorithms or machine learning models in product decisions, pricing, or customer communications is subject to the Consumer Duty's good outcomes obligation.

**FCA FG22/5, para 11.4:**
> "Using an algorithm that embeds historical bias, or that amplifies existing bias against a group of customers, is a breach of the crosscutting rule requiring firms to act in good faith."

**Requirements:**
- Algorithms used in customer-facing decisions must be assessed for bias against protected characteristics (age, disability, gender, race, religion, sexual orientation)
- Pricing algorithms must not systematically disadvantage vulnerable customers or groups
- AI/ML models generating customer communications must be assessed for fairness — not just accuracy
- Algorithm performance must be included in Consumer Duty monitoring — disaggregate outcomes by customer group
- Where an algorithm produces unexplained disparate impact, the firm must investigate and rectify
- Document algorithm design decisions and their relationship to customer outcomes

This obligation applies to: credit decisions, pricing engines, marketing segmentation, chatbot responses, fraud detection actions, document generation tools, and recommendation engines.

### 3.3 Choice Architecture

The way choices are presented to customers is a regulated activity. Firms must not use design to steer customers toward outcomes that benefit the firm at the customer's expense.

**Obligations (FCA FG22/5, para 8.3–8.4):**
- Default options must be set in the **customer's best interest**, not the firm's commercial interest
- Prominence of options must not systematically favour higher-margin products unless they genuinely deliver better value
- Multi-option journeys must present alternatives **fairly** — equal visual weight unless there is a customer-interest justification
- Complexity must not be added to alternatives to make the preferred option appear superior
- Pre-selection must never be used for products, add-ons, or fees unless the pre-selected option is in the customer's interest

This applies to: savings account defaults, insurance opt-ins, investment risk selection defaults, overdraft limits, paper vs digital statement choices.

### 3.4 Declining Customers — Obligations Persist

When a customer is declined for a product or service, the Consumer Duty does not end at the point of refusal.

**Requirements:**
- Signpost customers to alternative products, services, or support (e.g. debt advice, basic bank accounts, MoneyHelper)
- Communicate decline clearly — do not leave the customer uncertain about the outcome or next steps
- Ensure the decline journey does not create sludge that prevents the customer from seeking help
- Consider whether the decline decision itself could be reviewed for algorithmic bias (see 3.2)

### 3.5 Co-Manufacturer Written Agreement

Where two or more firms jointly manufacture a product, a **written agreement** is mandatory.

**FCA FG22/5, para 4.9:**
> "Where a firm is acting as a co-manufacturer... firms need to agree in writing how they will fulfil their respective Consumer Duty obligations."

**Required content:**
- Clear allocation of responsibility for each Consumer Duty outcome area
- Data sharing arrangements (including how monitoring data flows between parties)
- Escalation path when one firm identifies a consumer harm the other must remediate
- Process for annual review and CDA update

This applies to: co-branded products, white-label arrangements, embedded insurance, product partnerships with third parties, API-distributed products.

---

## 4. Annual Board Assessment

The Consumer Duty requires firms to produce an annual board assessment of whether the firm is delivering good outcomes.

**Required content (FCA FG22/5, para 12.3):**
1. **Monitoring results** — what data was collected across all four outcome areas, disaggregated by customer group
2. **Poor outcomes identified** — what evidence of harm or potential harm was found
3. **Root causes by group** — what explains any differences in outcomes between customer groups
4. **Actions taken** — what was done to remediate poor outcomes
5. **Future strategy** — how monitoring and product design will be improved

Boards must be able to evidence that they have considered outcomes for **vulnerable customers specifically** — not just the aggregate customer base.

---

## 5. Consumer Understanding Needs Assessment (CUNA)

CUNA is mandatory for all **significant new or amended customer communications**. It determines whether customer testing is required.

| Assessment | Trigger | Focus |
|---|---|---|
| **CDA** | Annually and at trigger events (new product, material change) | Product, journey, service, overall customer outcomes |
| **CUNA** | All significant new/amended communications; periodic reviews | Communication clarity and customer understanding |

### CUNA Significance Test

Communications are classified as **significant** or **non-significant** via Workfront:

- **Significant** → requires customer testing to confirm understanding; goes to BUK Comms Forum
- **Non-significant** → managed by Campaign Manager or Journey/Product Owner; approved at BUK Comms Forum

### BUK Comms Forum

Reviews and approves customer communications for accuracy and Consumer Duty compliance. Requires:
- Documented evidence and completed CUNA
- Multiple stakeholder sign-off (including Legal & Compliance where relevant)
- Subject expert validation

**Communication types covered:** customer letters/emails, SMS/push/in-app notifications, multi-channel campaigns, regulatory updates, service change communications.

---

## 6. NAPA (New and Pipeline Approval)

NAPA is the governance submission for new products. The CDA is a required input. Key NAPA-specific requirements:

- The CDA must be updated iteratively throughout the design and development process — not completed at the end
- Customer research and testing must be included to demonstrate forecast outcomes (not retrospective data)
- Section 10 (Future Monitoring) is mandatory — KIs must be defined before launch
- The product owner updates the assessment as learnings and insights are gained through the development cycle

---

## 7. Risk Management

### RICM Risk Rating

All risks in Section C must be rated using RICM (Risk, Impact, Control, Monitoring). The rating determines the urgency and governance of mitigating actions.

### ORAC (Operational Risk and Control)

Where an issue has been identified that is causing actual detriment to consumers (a **Harm**):
- An ORAC must be raised
- Existing BAU triage and issue management processes must be followed
- The CDA Section C must reference the ORAC number, issue summary, remediating action, and closure date

### Trailing Actions

All actions arising from Section C must be captured as Trailing Actions with:
- Reference to the risk they relate to
- Specific action and next steps
- Timing and monitoring approach
- The governance forum through which progress will be monitored

---

## 8. Consumer Duty Checklist

Use this when reviewing product requirements, communications, or governance artefacts:

### Product & Requirements
- [ ] Target market defined — needs, objectives, and characteristics documented
- [ ] Vulnerable customer considerations addressed (see `barclays-buk-standards:vulnerable-customers`)
- [ ] Product features clearly mapped to target market needs
- [ ] Fees and charges are proportionate and transparent
- [ ] Pricing model does not cause foreseeable harm or unfair advantage
- [ ] Exit/switching barriers identified and justified
- [ ] Default options set in customer's best interest — not firm's commercial interest
- [ ] If co-manufactured: written agreement in place covering all four Consumer Duty outcome areas
- [ ] Declining customers: signposting to alternatives is included in the decline journey

### Sludge and Journey Design
- [ ] Cancellation/exit/forbearance journeys reviewed for sludge — no asymmetric friction
- [ ] Cancellation channel matches sign-up channel (no phone-only cancellation for online sign-up)
- [ ] No pre-selected options that add charges or retain products against customer interest
- [ ] Complaints and exit flows accessible without excessive authentication barriers
- [ ] Where friction is present, it is documented as "appropriate friction" with a customer-interest justification

### Algorithms and AI
- [ ] Algorithms in customer decisions assessed for bias against protected characteristics
- [ ] Algorithm/AI output disaggregated by customer group in monitoring plan
- [ ] Pricing algorithms reviewed for systematic disadvantage to vulnerable groups
- [ ] AI-generated communications reviewed for fairness, not just accuracy
- [ ] Algorithm design decisions documented in relation to Consumer Duty outcomes

### Communications (CUNA)
- [ ] CUNA completed for all new or significantly changed communications
- [ ] Significant communications have gone through customer testing
- [ ] Communications use plain language — tested against 9-year-old reading age baseline
- [ ] Communications tailored for vulnerable customer groups
- [ ] BUK Comms Forum approval obtained where required

### Data & Outcomes
- [ ] Data analysis covers all 7 outcome themes
- [ ] Outcomes disaggregated by customer group — monitoring capability matches sales capability
- [ ] KIs defined for ongoing monitoring
- [ ] Benchmarking completed — product is not an outlier on fees or features

### Risk & Governance
- [ ] All risks captured with RICM rating
- [ ] Existing mitigants assessed for effectiveness
- [ ] Trailing actions have owners, timings, and governance forum assigned
- [ ] Any harms have ORAC references and remediation plans
- [ ] Executive Summary conclusion supported by evidence from the assessment
- [ ] MD attestation completed last

### NAPA Specific
- [ ] CDA updated iteratively through design — not completed at end
- [ ] Customer research and testing included for Section 8B
- [ ] Future monitoring (Section 10) defined before submission

### Annual Board Assessment
- [ ] Monitoring results included, disaggregated by customer group
- [ ] Poor outcomes and root causes identified — including by group
- [ ] Actions taken to remediate documented
- [ ] Vulnerable customer outcomes specifically addressed (not just aggregate)

---

## 9. Areas for Specialist Extension

This skill covers the BUK Consumer Duty baseline. The following areas need extension by the relevant teams:

- **Product Owners** — product-specific target market definitions, known vulnerability profiles per product line
- **Legal & Compliance** — regulatory change triggers, FCA engagement thresholds
- **Data & Analytics** — approved KI frameworks and data sources per product family
- **Communications** — CUNA significance thresholds and BUK Comms Forum process detail
