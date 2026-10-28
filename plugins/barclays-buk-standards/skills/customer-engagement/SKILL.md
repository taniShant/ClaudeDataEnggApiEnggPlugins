---
name: customer-engagement
description: BUK Customer Engagement Standard v7.2 obligations. Covers communications approval process, target market obligations, NAPA triggers for comms, AI/ML fairness assessment (IVU), vulnerability in communications, and copywriting standards. Use when designing, drafting, approving, or reviewing any customer-facing communication.
user-invocable: false
---

# BUK Customer Engagement Standards

> Source: Customer Engagement Standard v7.2 (Barclays Internal).
> Also applies: BUK Retail Addendum (supplementary obligations for retail communications).
> Legal basis: FCA Consumer Duty Principle 12, Consumer Understanding outcome; FCA FG22/5 choice architecture and sludge obligations.
> Read alongside `barclays-buk-standards:consumer-duty` (CUNA process) and `barclays-buk-standards:vulnerable-customers` (vulnerability in comms).

---

## Section 1: What This Standard Covers

The Customer Engagement Standard governs all **customer-facing communications** produced by or on behalf of BUK. This includes:

- Marketing communications (digital, direct mail, email, in-app, push, SMS)
- Product and service information (key features documents, summary boxes, terms changes)
- Transactional and service communications (statements, alerts, notifications, receipts)
- Regulatory and legal communications (mandatory disclosures, FCA-required information)
- Complaint responses and resolution letters
- Decline, exit, and product withdrawal communications

**What is NOT covered:** internal staff communications, B2B communications with no retail customer audience, regulated financial promotions governed by a separate Financial Promotions Policy.

---

## Section 2: Core Communications Obligations

### 2.1 Consumer Duty — Consumer Understanding Outcome

Every communication must support the customer in making an **informed decision or understanding their situation**. It is not sufficient that a communication is technically accurate — it must be understood.

**Standards:**
- Use plain English — target a 9-year-old reading age (Government Digital Service benchmark)
- Avoid jargon; where technical terms are unavoidable, define them on first use
- Acronyms must be expanded on first use
- Active voice preferred over passive voice
- Short sentences (aim ≤25 words per sentence)
- One idea per paragraph
- Key information must be prominent — not buried in caveats or footnotes

### 2.2 Target Market

Every communication must be designed for its **intended target market**. Communications must not:
- Use language, imagery, or channels that systematically exclude segments of the target market
- Make assumptions about the financial literacy or digital capability of the target market that are not supported by evidence
- Ignore the vulnerability profile of the target market (see Section 4 and `barclays-buk-standards:vulnerable-customers`)

Where a communication could reach customers outside the intended target market, consider whether it will harm those customers and mitigate accordingly.

### 2.3 Channel Requirements

| Communication type | Channel requirements |
|---|---|
| High-consequence decisions (account closure, significant charges, penalty notices) | Must be available in at least one non-digital channel (letter, telephone) |
| Time-sensitive alerts | Digital channels are sufficient; must include a clear action path |
| Marketing | Must honour customer channel preferences and consent records |
| Regulatory / mandatory | Must be delivered in the channel specified by regulatory requirement; alternatives must be available for accessibility needs |

Digital-only communications are permissible with conditions:
- Customer has opted into digital communications
- Accessibility alternatives are available (large print, audio) where requested
- Customers cannot be effectively excluded from understanding their obligations

---

## Section 3: Communications Approval Process

All new or significantly changed customer communications must go through the BUK communications approval process before use.

### 3.1 Approval Route

```
Author → Subject Expert Review → CUNA Assessment → [Customer Testing if Significant]
       → BUK Comms Forum → Legal & Compliance (if required) → Final Approval
```

### 3.2 CUNA — Consumer Understanding Needs Assessment

The CUNA determines whether the communication requires customer testing. See `barclays-buk-standards:consumer-duty` Section 5 for full CUNA process.

**A communication is automatically Significant and requires customer testing if it:**
- Is the primary disclosure of material product terms or charges
- Changes a customer's existing product terms, fees, or conditions
- Is used in a high-volume campaign reaching more than [threshold — per BUK Comms Forum guidance]
- Relates to a product or service used by a segment with high vulnerability characteristics
- Is a decline, withdrawal, or exit communication for a product with a vulnerable customer base

### 3.3 NAPA Triggers for Communications

A communications change triggers a NAPA submission when:
- It represents a new communication type not previously in use for that product
- It is part of a new product launch
- It supports a material change to product features, pricing, or terms

Where a NAPA is required, the communications must be included in the CDA (Consumer Duty Assessment) Section A.5 review of customer understanding.

---

## Section 4: Vulnerability in Communications

Communications must be designed so that customers with characteristics of vulnerability can understand and act on them.

### 4.1 Obligations

- All high-consequence communications must be available in **alternative formats** on request:
  - Large print
  - Audio
  - Braille
  - Easy-read / simplified version
  - British Sign Language (BSL) video equivalent for complex disclosures
- Plain language baseline applies regardless of vulnerability — it benefits all customers
- Communications must not rush customers into decisions — avoid countdown timers, urgency framing, or prominence techniques that exploit inertia
- Where a communication requires a customer to take action, the action path must be accessible without requiring digital capability
- For communications to customers in financial difficulty: signpost to MoneyHelper, debt advice services, and Barclays own hardship support channels

### 4.2 The "Tell Us Once" Principle

If a customer has disclosed vulnerability information, subsequent communications must reflect this:
- Preferred format must be used where on record
- Preferred contact channel must be used where on record
- Communications must not require the customer to re-disclose circumstances already on file

---

## Section 5: AI and Machine Learning in Communications

### 5.1 AI/ML Fairness — IVU Assessment

Where AI or machine learning is used to **generate, personalise, or select** customer communications, an **Identified Vulnerable and Underserved (IVU) fairness assessment** is mandatory before deployment.

**The IVU assessment must cover:**
- Does the AI system produce systematically different outputs for customers with protected characteristics?
- Does personalisation result in some customers receiving materially worse information than others?
- Could the AI system amplify existing bias in customer data (e.g. lower-income segments receiving less informative communications)?
- Are communications generated for vulnerable customers reviewed by a human before sending?

This assessment is separate from the CUNA — it is an algorithm fairness assessment, not a readability test.

### 5.2 Human Review Requirements

AI-generated or AI-selected communications at volume must include:
- A defined human review process for edge cases and flagged outputs
- A sampling methodology to check quality across customer segments
- Clear escalation path where the AI produces outputs that may harm vulnerable customers
- Audit trail of which outputs were AI-generated vs human-authored

### 5.3 Prohibited AI Uses in Communications

- Generating communications that apply psychological pressure or exploit cognitive bias
- Personalising urgency, fear, or scarcity cues based on customer vulnerability signals
- Using historical complaint or vulnerability data to tailor communications in a way that exploits rather than supports the customer
- Generating regulatory or legal disclosure text without human review and sign-off

---

## Section 6: Copywriting Standards

### 6.1 Language and Tone

- **Active voice**: "We'll charge you £10" not "A charge of £10 will be applied"
- **Customer-first framing**: Lead with what the customer needs to do or know, not with Barclays' position
- **Present tense** for current product features and obligations
- **Future tense** for changes taking effect in future
- **No weasel words**: avoid "may", "could", "potentially" in statements of fact
- **Quantify**: "You'll pay £10 per month" not "You may pay a monthly fee"
- **No double negatives**: "You can cancel at any time" not "You will not be prevented from cancelling"

### 6.2 Formatting Conventions

- **Headers**: use to signal key sections; do not use headers as substitutes for clear prose
- **Bullet lists**: use for three or more parallel items; do not use for single items or continuous narrative
- **Bold**: use for genuinely critical information only — overuse destroys emphasis
- **Underlining**: only for hyperlinks — do not underline for emphasis (accessible design requirement)
- **ALL CAPS**: avoid; use sparingly if required for regulatory labels ("IMPORTANT" in specific contexts only)
- **Tables**: use for comparative information; include column headers; do not use tables to structure non-comparative content

### 6.3 Numbers and Figures

- Spell out numbers one through nine; use numerals for 10 and above
- Percentages: always use numeral + "%" (e.g. 5%)
- Currency: always use numeral + £ symbol (e.g. £10, not ten pounds)
- Dates: day month year format (e.g. 24 June 2026) — no ordinals ("24th")
- Phone numbers: use spaces for readability (e.g. 0800 123 4567)

### 6.4 Regulatory Labels and Required Text

Some communications require FCA-mandated text that must not be abbreviated, paraphrased, or omitted:
- ISA annual subscription limit reminders
- Cooling-off period notices
- Risk warnings on investment products
- FSCS protection statements where applicable

These must be reviewed by Legal & Compliance before use and must not be edited after approval.

---

## Section 7: BUK Retail Addendum — Supplementary Obligations

The BUK Retail Addendum applies supplementary requirements to retail customer communications beyond the general Customer Engagement Standard. Key provisions:

- **High-street brand obligations**: Barclays and Barclaycard visual identity standards apply to all communications — do not use non-standard logo treatments or colour deviations (see `barclays-buk-standards:brand`)
- **Vulnerability flag**: Communications for products with a known high-vulnerability customer base (basic bank accounts, overdrafts, some credit products) require vulnerability review as standard — not only when flagged
- **Proactive understanding check**: For products likely to be purchased by vulnerable consumers, firms must proactively check understanding — do not assume that providing information constitutes understanding

---

## Section 8: Agent Self-Check — Before Finalising Any Communication

When producing customer communications, confirm:

- [ ] Plain English — 9-year-old reading age baseline applied
- [ ] No jargon or unexplained acronyms
- [ ] Target market identified and communication designed for that market
- [ ] Vulnerability profile of target market considered
- [ ] Alternative formats available for high-consequence communications
- [ ] No rush mechanisms or urgency framing that exploits inertia
- [ ] Action path accessible without digital capability where required
- [ ] CUNA assessment completed — significance determined
- [ ] Customer testing completed if communication is Significant
- [ ] BUK Comms Forum approval obtained
- [ ] If AI-generated or AI-personalised: IVU fairness assessment completed
- [ ] Regulatory / FCA-mandated text included verbatim where required
- [ ] Legal & Compliance reviewed where required
- [ ] Channel matches customer preferences and accessibility needs
- [ ] If customer has vulnerability on file: preferred format and channel used
