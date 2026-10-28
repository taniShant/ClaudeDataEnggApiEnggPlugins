# ODS API Catalogue (Seed Data)

This file provides a seed mapping between MTS gateway methods and their candidate ODS replacement APIs across multiple sources (Confluence spaces and GitLab). Used by the `/api-replacement-match` command to fast-track candidate discovery before falling back to CQL/GitLab search.

---

## Catalogue Metadata

| Property | Value |
|---|---|
| Last full refresh | 2026-04-02 |
| Entries | 28 Confluence pages (pcbcooiit) + 30 COOCUSTCRM pages + 2000+ Backstage components (live clone of `developmentForProd` branch; `backstage_catalogue_index.md` as static fallback) + 7 additional Confluence spaces (see "Additional API Sources v1.3" section) |
| Search layers | 13 total: Backstage + pcbcooiit + PCBICCAPIS + COOCUSTCRM + GRPQRTUKBA + BCDUKCAPI + EST + DCMDEV + APITECHDES (x2) + EMMAPIS (x2) + EPZOSCON + Deep Investigation |
| Auto-refresh available | Requires Confluence MCP tools (`/refresh-ods-catalogue`) |
| Staleness threshold | 30 days — `/api-replacement-match` warns if exceeded |

---

## API Hierarchy & Search Priority

### API Layer Taxonomy

Barclays uses a three-tier API architecture. When searching for an ODS replacement, **always search for the highest-level API first** (Process/Domain), then fall back to System APIs only if no higher-level match exists.

| Layer | Type | Suffix | Purpose | Read/Write | Search Priority |
|---|---|---|---|---|---|
| 1 (highest) | Process API | pAPI | Business process orchestration, multi-step workflows | Both | Search FIRST |
| 2 | Domain API | dAPI | Domain-specific business logic, aggregation across systems | Both | Search SECOND |
| 3 | Internal API | iAPI | Internal-facing APIs for specific capabilities | Both | Search THIRD |
| 4 | External API | xAPI | External-facing APIs (third parties, channels) | Read | Search FOURTH |
| 5 (lowest) | System API | sAPI | Direct data access to a single backend system | **Read-heavy** (enquiry) | Search LAST |

**Key rule:** ODS APIs (branded "ODS Retail ...") are **primarily System APIs (sAPI)** that provide **read/enquiry** operations against backend data sources. For **write operations**, look for dedicated System APIs (e.g., CAMS card setup sAPI) or Domain APIs that orchestrate writes across multiple systems.

### Call Flow

```
FullServe Application / Channel
  ↓
Process APIs (pAPI) — e.g., cct-custnotepad-api
  ↓
Domain APIs (dAPI) — e.g., cc-domain-qry-account, cc-domain-qry-customer
  ↓
System APIs (sAPI) — e.g., sodscustenq, sodsaccountsenq, sodsproductsenq
  ↓
Backend Systems (UKBA, CS, CAMS, Triumph, etc.)
```

### Known API Endpoints by Layer

**ODS System APIs (sAPI) — Read/Enquiry:**

| API Name | Endpoint Prefix | Version | Backend | Purpose |
|---|---|---|---|---|
| ODS Retail Customer Enquiry | sodscustenq | v4 | CS, UKBA | Customer data retrieval |
| ODS Retail Customer Data Enquiry | sodscustenq | v4 | CS | Customer screening/data |
| ODS Retail Account Enquiry | sodsaccountsenq | v3 | UKBA | Account data retrieval |
| ODS Retail Product Holdings | sodsproductsenq | v3 | CS, UKBA, PFS | Product holdings data |
| ODS Retail Card Enquiry | sodscardsaccountinfo | v1 | UKBA | Card data retrieval |
| ODS Reference Data Enquiry | sodsreferenceenq | v3 | CS | Reference/cross-reference data |
| ODS CAMS Declined Transactions | sodscamstransenq | v3 | CAMS | Declined transaction data |
| ODS Customer Locate Enquiry | — | — | CS | Customer locate by account |
| ODS Retail Membership | — | — | Triumph | Membership data |

**Barclaycard Domain APIs (dAPI) — Read/Enquiry:**

| API Name | Endpoint Prefix | Version | Purpose |
|---|---|---|---|
| Account Enquiry | cc-domain-qry-account | v6 | Barclaycard account data |
| Customer Enquiry | cc-domain-qry-customer | v8 | Barclaycard customer data |
| Device Enquiry | cc-domain-qry-device | v6 | Device/token data |
| Communication Preference | cc-domain-qry-comm-pref | v4 | Contact preferences |
| Payment Enquiry | cc-query-payment-api | v4 | Payment data |
| Reward Enquiry | cc-query-reward-api | v2 | Reward/loyalty data |
| Billing Enquiry | cc-qry-billing-api | v4 | Billing/statement data |

**Process & Internal APIs (pAPI/iAPI) — Read + Write:**

| API Name | Endpoint Prefix | Version | Purpose |
|---|---|---|---|
| Customer Notepad | cct-custnotepad-api | v1.1 | Notepad read/write (pAPI) |
| Customer Notepads v2 | cust-notepads-sAPI | v2.0 | Notepad read/write (sAPI) |
| Avios Badge | aviosserv-iapi | v1 | Avios badge data (iAPI) |
| Avios Enquiry | aviosserv-iapi | v3 | Avios enquiry (iAPI) |
| All Account View | allaccountview-iapi | v3.4 | Aggregated account view (iAPI) |
| Customer MIFID | customermifid-iapi | v1 | MIFID compliance data (iAPI) |
| Colleague Notepad | customernotepad-iapi | v1 | Colleague notepad access (iAPI) |

---

## Backend Source Systems

Data flows from these mainframe/backend systems through the API layers above. When matching an MTS service to an ODS replacement, knowing which backend system is involved narrows the candidate search.

| System Code | Full Name | Domain | Data Types |
|---|---|---|---|
| **CS** | Customer Systems | Customer | Customer details, addresses, contact info, segments, screening |
| **UKBA** | UK Banking Application | Accounts | Current accounts, savings accounts, mortgages — balances, limits, status |
| **CAMS** | Card Account Management System | Debit Cards | Debit card plastic data, card setup |
| **Triumph** | Triumph (Premium/Membership) | Credit Cards / Membership | Credit card data (credit limits), membership programmes (Avios) |
| **ALS** | ALS Loans System | Loans | Personal loans, loan accounts |
| **PFS** | Product/Financial Services | Products | Product holdings aggregation, financial product data |
| **SOLD** | SOLD System | Foreign Currency | Foreign currency products (classified as misc products) |
| **FNZ** | FNZ Systems | Investments | Investment accounts, ISAs |
| **NGCB** | Next Gen Cloud Banking | Cloud Products | Product-level info from AWS cloud |
| **CMOD** | IBM Content Manager OnDemand | Documents | Customer correspondence, statements, document retrieval |
| **OWEK** | OWEK (Document Management) | Documents | Related to CMOD — document management workflows |
| **Barclaycard** | Barclaycard | Credit Cards | Credit card issuing, Barclaycard-specific data |

### Product Type to Backend System Mapping

When an MTS service accesses product/account data, the backend system depends on the product type:

| Product Type | Backend System | Holding Table | PDT_ACC_CLS_CDE | Notes |
|---|---|---|---|---|
| Current Accounts | UKBA | TDLBAHO | — | Fetched from UKBA mainframe |
| Savings Accounts | UKBA | TDLBAHO | SV | Fetched from UKBA mainframe |
| Mortgages | UKBA | TDLBAHO | — | UKBA mortgage system |
| Personal Loans | ALS | TDLMAHO | LN | Fetched from ALS system (misc holdings) |
| Credit Cards | Triumph / Barclaycard | TDLCAHO | CA | Credit limit from Triumph; card data from Barclaycard |
| Debit Cards | CAMS | TDLCCAX / TDLCCRA | — | Card plastic from CAMS system |
| Foreign Currency | SOLD | TDLMAHO | — | Classified as misc products |
| Investments | FNZ | TDLMAHO | ID | Investment accounts from FNZ |
| Insurance Policies | — | TDLMAHO | — | Linked via misc holdings |
| NGCB Products | NGCB (AWS) | — | — | Product-level info from AWS cloud |

**Holdings table key:**
- **BAHO** (TDLBAHO) = **Bank Account Holdings** → UKBA accounts (current, savings, mortgages). Has `pdt_cde` with start/end dates.
- **MAHO** (TDLMAHO) = **Misc Account Holdings** → Everything else — loans (ALS), insurance, investments (FNZ), foreign currency (SOLD). Linked to non-UKBA systems.
- **CAHO** (TDLCAHO) = **Card Account Holdings** → Credit cards (Barclaycard/Triumph). Gold, Mastercard, etc. with start/end dates, primary account holder flag (0=main, 1=supplementary).

### TDL Table Reference

Detailed reference for each TDL table including its DB schema, backend system, and data content.

**Test Bed Schemas:**

| Schema Pattern | Test Bed | Example | Notes |
|---|---|---|---|
| `dly0apd` | Test Bed A | `dly0apd.tdlpcus` | Production-like data |
| `dly0a5d` | Test Bed 5 | `dly0a5d.tdlcust` | Alternate test bed |
| `dly0agd` | Test Bed G | `dly0agd.tdlcust` | Full customer data set |
| `dlyr05d` | Ref Data Test Bed 5 | `dlyr05d.tdlmrdt` | Reference data tables |

**Customer Tables (CS):**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TDLCUST` | dly0agd | CS | All customers (master) | Customer ID, type |
| `TDLPCUS` | dly0apd / dly0agd | CS | Personal customers | Personal details, name, DOB |
| `TDLBCUS` | dly0agd | CS | Business customers | Business name, registration |
| `TDLCSEG` | dly0agd | CS | Customer segments | `low_seg_cde` (e.g., BM% = business markers), `grp_seg_cde` (e.g., WLA = wealth customer, voice security markers, mobile banking) |
| `TDLCURL` | dly0agd | CS | Customer relationships | Reference to business account as relationship (e.g., director) |
| `TDLCTPT` | dly0agd | CS | Contact details | Customer contact points (phone, email, address) |

**Account / Holdings Tables:**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TDLBAHO` | dly0apd | UKBA | Bank Account Holdings | `pdt_cde` (product code), start/end dates. Current + savings accounts. |
| `TDLMAHO` | dly0apd | Various | Misc Account Holdings | `PDT_ACC_CLS_CDE` — LN=loans(ALS), ID=investments(FNZ), etc. Insurance policies, foreign currency(SOLD). |
| `TDLCAHO` | dly0apd | Triumph/Barclaycard | Card Account Holdings | Credit cards — gold, mastercard. Start/end dates. Primary holder flag (0=main, 1=supplementary). |

**Card Tables:**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TDLCCAX` | dly0apd | CAMS | Debit cards (alternate) | Debit card data |
| `TDLCCRA` | dly0agd | CAMS | Debit cards | Debit card details |

**Membership & Channel Tables:**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TDLCUML` | dly0agd | CS | Membership | Online banking, telephone banking membership |
| `TCRMDCC` | dly0agd | Triumph | Membership-channel link | Links membership to channel. Channel 1 = telephony. |

**Reference Data Tables:**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TDLMRDT` | dlyr05d | CS | Reference data (master) | Codes, descriptions, lookups |
| `TUKPROD` | dly0agd | UKBA | Product reference | `pdt_cde` (product code), short/full name. `pdt_cls_cde`: current account, SV=savings, LO=loan, ID=investment, CA=credit card. |
| `VI_TUKMRDT` | — | UKBA | Reference data view | View over UKBA reference data |
| `TDLEMSG` | dlyr05d | CS | Error messages | Error/message lookups |

**Audit Tables:**

| Table | Schema | Backend | Description | Key Columns |
|---|---|---|---|---|
| `TSOAD02` | dly0agd | CS | Audit data | `AUD_DAT` (audit date) |
| `TSOAD03` | dly0agd | CS | Audit events | `eventid`, `idv_type_cde` (verification method — how customer was verified, IMPORTANT), `AUD_TYP_CDE` (always 'E' for read operations) |

---

## Sources

| # | Source | Type | Identifier | Notes |
|---|---|---|---|---|
| 1 | pcbcooiit Confluence space | Confluence | Space: `pcbcooiit`, Parent: 507590733 | Primary ODS API LLD pages (28+ pages) |
| 2 | COOCUSTCRM Confluence space | Confluence | Space: `COOCUSTCRM`, Parent: 1798520644 | COO Customer CRM z/OS Connect sAPIs (30+ pages, read+write support) |
| 3 | Backstage Catalogue | Live clone (preferred) / Local file (fallback) | Live: `backstage_clone.py` clones `developmentForProd` branch (2000+ components). Fallback: `backstage_catalogue_index.md` (static snapshot) | Comprehensive BUK API registry. Includes name, system, domain, tags, description, Confluence URLs, GitLab slugs |

### Additional API Sources (v1.3)

| # | Source | Space | Parent Page ID | Scope | Trigger Condition |
|---|---|---|---|---|---|
| 4 | PCBICCAPIS | `PCBICCAPIS` | 1228557435 | TC 31 API Catalog (pAPIs, dAPIs, iAPIs) | Always (process/domain APIs) |
| 5 | GRPQRTUKBA | `GRPQRTUKBA` | 1087522407 | UKBA API Design Reference | UKBA tables/IMS codes detected |
| 6 | BCDUKCAPI | `BCDUKCAPI` | 1276948367 | Cards & Lending API Catalogue | Cards/Lending SOAP stubs detected |
| 7 | EST | `EST` | 559035965 | Open Banking APIs | Account/payment/consent/PSD2 services |
| 8 | DCMDEV | `DCMDEV` | 737076546 | DCM APIs | Document/correspondence/CMOD services |
| 9 | APITECHDES (Index) | `APITECHDES` | 1311225934 | API Index — master cross-reference | Always (master catalogue) |
| 10 | APITECHDES (Digital) | `APITECHDES` | 1311226039 | Digital Channels API Design - Published | Customer-facing digital services |
| 11 | EMMAPIS | `EMMAPIS` | 2214221355 | EMM API Design - Published | Customer insights/marketing/eligibility |
| 12 | EMMAPIS (sub) | `EMMAPIS` | 2214221813 | Customer Insights Process API - v1 | Known sub-page for insights pAPI |
| 13 | EPZOSCON | `EPZOSCON` | 954298640 | EP z/OS Connect API Catalogue | Payments, Branch Accounting, Debit Cards, UKBA (broader than COOCUSTCRM) |

**Confluence URLs for reference:**
- EST: `https://confluence.barcapint.com/spaces/EST/pages/559035965/Open+Banking+APIs`
- DCMDEV: `https://confluence.barcapint.com/spaces/DCMDEV/pages/737076546/DCM+Application+Programming+Interfaces+APIs`
- APITECHDES (Index): `https://confluence.barcapint.com/spaces/APITECHDES/pages/1311225934/API+Index`
- APITECHDES (Digital): `https://confluence.barcapint.com/spaces/APITECHDES/pages/1311226039/Digital+Channels+API+Design+-+Published`
- EMMAPIS: `https://confluence.barcapint.com/spaces/EMMAPIS/pages/2214221355/API+Design+-+Published`
- EMMAPIS (sub): `https://confluence.barcapint.com/spaces/EMMAPIS/pages/2214221813/Customer+Insights+Process+API+-+v1`
- EPZOSCON: `https://confluence.barcapint.com/spaces/EPZOSCON/pages/954298640/API+Catalogue`

---

## Direct Mappings

Known MTS-to-ODS API correspondences derived from the LLD parent page mapping table and manual analysis.

| MTS Gateway Method | EGS Transaction | COBOL Txn | ODS API Name | Page ID | ODS Endpoint | Verified |
|---|---|---|---|---|---|---|
| CustomerGateway.findByPrimaryKey() | CustomerAllRetrieveTransaction | TDLQCU / TDLXCUM0 | ODS Retail Customer Enquiry API | 879235084 | /sodscustenq/4/v4/customers/{customerId} | 2026-03-19 |
| CustomerGateway.retrieveCustomerScreeningDecision() | CustomerScreeningTransaction | TDL1MSM0 | ODS Retail Customer Data Enquiry sAPI | 852701158 | /v3/customers/{customerId} | 2026-03-19 |
| AccountGateway.findByKeySet() | MultiAccountEnquiryTransactionV1/V2 | TGJ1MA/TGJ2MA | ODS Retail Account Enquiry sAPI | 868819677 | /v3/accounts/{accountIds} | 2026-03-19 |
| AccountGateway.findByPrimaryKey() | GenericEnquiryTransactionV7 | TGJ7OG | ODS Retail Account Enquiry sAPI | 868819677 | /v3/accounts/{sc+accno} | 2026-03-19 |
| CustomerGateway.findPfsDataByCustomerId() | PfsRetrieveTransaction | TDL3PF | ODS Retail Product Holdings and Account Data sAPI | 603131476 | /v3/customers/{customerId}/productHoldings | 2026-03-19 |
| MembershipGateway.findByToken() | RetrieveMemberTransactionVA | TCRAREM0 | ODS Retail Membership sAPI | 863005911 | /v3/memberships/{custId} | 2026-03-19 |
| CustomerGateway.findByAccount() | CustomerLocateByNumberTransactionV3 | TDL3CAM | ODS Customer Locate Enquiry System API | 1199869988 | /v3/customers/{sc+accno} | 2026-03-19 |

---

## All ODS API Pages by Source

### Source 1: pcbcooiit Space (Parent: 507590733)

Children of parent page 507590733 in the `pcbcooiit` space. Used for keyword-based candidate matching when no direct mapping exists.

| Page ID | Title | Keywords |
|---|---|---|
| 852701158 | ODS Retail Customer Data Enquiry sAPI | customer, CS, TDLCUST, TDLPCUS, TDLBAHO, TDLMAHO, TDLCAHO |
| 879235084 | ODS Retail Customer Enquiry API | customer, TDLBAHO, TDLMAHO, TDLCAHO, TDLBARH, TDLRAHO, TDLCURL, TDLBAJT, TDLXCUM0, TDLYCUM0, CS, UKBA, z/OS Combined Retrieve |
| 868819677 | ODS Retail Account Enquiry sAPI LLD | account, UKBA, balances, MAE, TGJ1MA, TGJ2MA, TGJ7OG |
| 603131476 | ODS Retail Product Holdings and Account Data sAPI LLD | TDLBAHO, TDLMAHO, productHoldings, CS, UKBA, PFS |
| 863005911 | ODS Retail Membership sAPI LLD | membership, Triumph, TCRAREM0 |
| 1199869988 | ODS Customer Locate Enquiry System API | locate, customer, TDL3CAM |
| 1901673378 | ODS Retail Card Enquiry sAPI LLD | cards, credit card, UKBA |
| 823393406 | ODS Retail Entitlements Enquiry sAPI | entitlements |
| 748686498 | ODS Retail Transaction Enquiry V5 | transactions, history |
| 600754944 | ODS Reference Data Enquiry sAPI | reference data |
| 3818258575 | ODS Product Holding and Account Data Enquiry API v4 | PHAD v4, productHoldings, TDLBAHO, TDLMAHO |
| 785961061 | ODS Retail Entity Beneficiaries System API LLD | beneficiaries, entity, account |
| 2251699755 | ODS Cards Device Enquiry API LLD | cards, device, enquiry |
| 1415824141 | ODS GraphQL API LLD | GraphQL, aggregation |
| 2117124890 | ODS Cards Account Information API - LLD | cards, account information, CAMS |
| 1122395530 | ODS Retail RPS Enquiry sAPI LLD | RPS, retail, enquiry |
| 3719915412 | L2_BUKL2DIGI-967 - ODS Bereavement MCA2 migration | bereavement, MCA2, MTS replacement |
| 507590733 | ODS API LLD Parent Page | index, all APIs |
| 918585340 | ODS Retail SOLD Transaction Enquiry sAPI LLD | SOLD, transaction, foreign currency |
| 2018021097 | ODS Retail SOLD Accounts Enquiry sAPI LLD | SOLD, accounts, enquiry, foreign currency |
| 822758105 | ODS Retail SOLD Accounts Enquiry sAPI LLD (older) | SOLD, accounts, enquiry (older version) |
| 2229551050 | ODS Retail Customer Insights sAPI LLD | customer insights, segments, analytics |
| 785965261 | ODS Retail Preferences Enquiry sAPI LLD | preferences, contact, marketing consent, TDLCCME |
| 3897657884 | ODS Retail Product Holding and Account Data sAPI - Field Mapping | PHAD, field mapping, TDLBAHO, TDLMAHO |
| 603151803 | ODS Retail Product Holding and Account Data sAPI Specification | PHAD specification, productHoldings |
| 697410076 | ODS Retail Customer Enquiry (Devices) sAPI LLD | customer, devices, enquiry |
| 673377471 | ODS Retail Stop Cheque sAPI LLD | stop cheque, account |
| 713994225 | ODS Customer Credit Risk Bureau Enquiry sAPI LLD | credit risk, bureau, enquiry |
| 968094106 | ODS NGCB Account Enquiry sAPI LLD | NGCB, cloud banking, account |
| 650286564 | ODS Retail Customer Locate Enquiry sAPI | customer locate, TDL3CAM |
| 2177172726 | Retrieve Cat and SubCat Details sAPI LLD | category, sub-category, details |

### Source 2: COOCUSTCRM Space (Parent: 1798520644)

Children of the "API Documentation" page (1798520644) in the `COOCUSTCRM` space. Covers COO Customer CRM z/OS Connect sAPIs. These are distinct from the ODS retail APIs in pcbcooiit — they provide **z/OS Connect system APIs** that often support **both read AND write operations** against the Barclays mainframe.

**IMPORTANT for write operations:** COOCUSTCRM sAPIs are the primary source for write/update API candidates. Always search here for MTS methods containing create/update/modify/set/delete.

| Page ID | Title | Keywords | Read/Write |
|---|---|---|---|
| 1798520644 | API Documentation (Parent) | CRM, COO, customer, API index | — |
| 3852609006 | cust-coreCustomerDetails-sAPI-v14.0 Documentation | core customer details, sAPI, customer, TDLCUST, TDLPCUS, update | **Read+Write** |
| 3008859229 | cust-coreCustomerDetails-sAPI-v13.0 Documentation | core customer details, sAPI, v13 | Read+Write |
| 2529409135 | cust-coreCustomerDetails-sAPI-v12.0 Documentation | core customer details, sAPI, v12 | Read+Write |
| 2846624604 | cust-coreCustomerDetails-sAPI-v9.3 Documentation | core customer details, sAPI, v9.3 | Read+Write |
| 2911224643 | cust-coreCustomerDetails-sAPI-v9.2 Documentation | core customer details, sAPI, v9.2 | Read+Write |
| 2164463698 | cust-membershipMaintenance-sAPI-v1.0 Documentation | membership, maintenance, sAPI, WMID, update | **Write** |
| 1850479771 | cust-customerPreferences-sAPI-v1.1 Documentation | preferences, contact method exclusions, marketing consent, update | **Read+Write** |
| 3519157596 | cust-salesAndCreditStrategy-sAPI-v1.0 Documentation | sales, credit strategy, sAPI | Read |
| 2519147208 | cust-markerAuditDetails-sAPI-v1.0 Documentation | marker, audit, sAPI, TSOAD | Read |
| 3869364420 | cust-notepads-sAPI-v3.0 Documentation | notepads, sAPI | Read+Write |
| 3489855661 | cust-delegatedAuthority-sAPI-v2.0 Documentation | delegated authority, sAPI | Read |
| 3805456113 | cust-thirdParty-sAPI-v2.0 Documentation | third party, sAPI | Read |
| 1981650914 | cust-thirdParty-sAPI-v1.2 Documentation | third party, sAPI, v1.2 | Read |
| 2036556786 | cust-accountHoldingEvents-sAPI-v1.0 Documentation | account holding, events, sAPI | Read |
| 2691519244 | cust-customerLocate-sAPI-v1.1 Documentation | customer locate, sAPI, TDL3CAM | Read |
| 2819361412 | cust-nonSourceCrossReferenceManagement-sAPI-v1 Documentation | cross reference, management, sAPI | Read+Write |
| 2755553460 | cust-singleSignOnDetails-sAPI-v1.0 Documentation | SSO, single sign on, sAPI | Read |
| 2198074687 | cust-applicationDetails-sAPI-v2.0 Documentation | application details, sAPI | Read |
| 1999671376 | cust-PINSentryDevices-sAPI-v1 Documentation | PINSentry, devices, sAPI, verification | Read |
| 2799684734 | cust-usageTypeAccountRefund-sAPI-v1 Documentation | usage type, account refund, sAPI | Write |
| 2616131338 | cust-vafRewardTransaction-sAPI-v2.0 Documentation | VAF, reward, transaction, sAPI | Read |
| 2804335454 | cust-createCustomer-sAPI-v1.0 Documentation | create customer, sAPI | **Write** |
| 2807830834 | cust-productPointers-sAPI-v1.0 Documentation | product pointers, sAPI | Read |
| 2770415410 | cust-vafPackages-sAPI-v1.1 Documentation | VAF, packages, sAPI | Read |
| 2719477617 | cust-vafEligibility-sAPI-v1.1 Documentation | VAF, eligibility, sAPI | Read |
| 2792965467 | cust-vafRewardsAgreements-sAPI-v2.1 Documentation | VAF, rewards, agreements, sAPI | Read |
| 2625163286 | cust-productRefData-sAPI-v1.0 Documentation | product reference data, sAPI | Read |
| 2003130804 | cust-productRefData-sAPI-v1.1 Documentation | product reference data, sAPI, v1.1 | Read |
| 2005034758 | cust-customerTax-sAPI-v1.0 Documentation | customer tax, sAPI | Read |
| 2726464481 | cust-vafQuotePolicy-sAPI-v1.0 Documentation | VAF, quote, policy, sAPI | Read |
| 2625164542 | Cool Boxed API Documentation | cool boxed, API, CRM | Read |
| 1809762161 | Decommissioned Template - cust-applicationDetails-sAPI-v1.1 Documentation | decommissioned, application details | — |

**Search guidance:** When the agent queries COOCUSTCRM, use these CQL patterns:
- Customer detail read/write: `space = "COOCUSTCRM" AND text ~ "coreCustomerDetails"`
- Membership maintenance: `space = "COOCUSTCRM" AND text ~ "membershipMaintenance"`
- Customer preferences/exclusions: `space = "COOCUSTCRM" AND text ~ "customerPreferences"`
- Marker/audit: `space = "COOCUSTCRM" AND text ~ "markerAudit"`
- Write operations: `space = "COOCUSTCRM" AND text ~ "update OR create OR maintain"`

### Source 3: Backstage Catalogue (2000+ Components)

**Primary:** Live clone of `developmentForProd` branch via `backstage_clone.py` (Step 1.95). Cloned to `/tmp/software-catalogue-templates/components/`. This is the preferred source — always up-to-date with ~2000+ YAML component files.

**Fallback:** `backstage_catalogue_index.md` — a pre-indexed pipe-delimited static snapshot. Used only when the live clone fails (network/auth issues).

**Last static index refresh:** 2026-03-25

**What's included per component:** Name, Title, System, Domain, Tags, Description, Confluence URL, GitLab Slug.

**Key stats (from static index — live repo may have more):**
- 52 components with `system: buk/ods` (the ODS sAPIs)
- 28 distinct BUK domains
- 326 sAPI, 225 iAPI, 228 xAPI, 223 pAPI
- 973 components have Confluence documentation links
- 1883 components have GitLab source repo slugs

**Usage:** The `/api-replacement-match` command first clones the live repo (Step 1.95) and greps YAML files directly. If clone fails, it falls back to the static index file (using `Grep` tool).

**Refreshing static index:** Run `/refresh-ods-catalogue` which re-clones the `developmentForProd` branch and regenerates `backstage_catalogue_index.md`.

---

## Keyword Index

Quick lookup index mapping common search terms to page IDs. Used by Layer 1 seed matching.

| Keyword | Source 1 Page IDs | Backstage Catalogue | Backend System |
|---|---|---|---|
| TDLBAHO | 879235084, 603131476, 852701158, 3818258575 | Grep `backstage_catalogue_index.md` for domain/system matches | UKBA |
| TDLMAHO | 879235084, 603131476, 852701158, 3818258575 | Grep `backstage_catalogue_index.md` for domain/system matches | Various (ALS, FNZ, SOLD) |
| TDLCAHO | 879235084, 852701158 | Grep `backstage_catalogue_index.md` for domain/system matches | Triumph/Barclaycard |
| TDLBARH | 879235084 | — | CS |
| TDLRAHO | 879235084 | — | CS |
| TDLCURL | 879235084 | — | CS |
| TDLBAJT | 879235084 | — | CS |
| TDLCUST | 852701158 | — | CS |
| TDLPCUS | 852701158 | — | CS |
| TDLBCUS | — | — | CS |
| TDLCSEG | — | — | CS |
| TDLCTPT | — | — | CS |
| TDLCUML | — | — | CS |
| TDLCCAX | — | — | CAMS |
| TDLCCRA | — | — | CAMS |
| TDLMRDT | — | — | CS (ref data) |
| TDLEMSG | — | — | CS (ref data) |
| TDLXCUM0 | 879235084 | — | CS |
| TDLYCUM0 | 879235084 | — | CS |
| TCRMDCC | — | — | Triumph |
| TSOAD02 | — | — | CS (audit) |
| TSOAD03 | — | — | CS (audit) |
| TUKPROD | — | — | UKBA (ref data) |
| customer | 852701158, 879235084, 1199869988 | Grep index: 121 entries in `buk-domain-customer-party` | CS |
| account | 868819677, 603131476, 3818258575 | Grep index: 53 entries in `buk-domain-current-account` | UKBA |
| productHoldings | 603131476, 3818258575 | Grep index: 52 entries in `buk-domain-aggregated-customer-holdings` | CS, UKBA, PFS |
| membership | 863005911 | Grep index for "membership" in name/description | Triumph |
| screening | 852701158 | — | CS |
| locate | 1199869988 | — | CS |
| cards | 1901673378 | Grep index for "card" in name/description/tags | CAMS, Triumph |
| entitlements | 823393406 | — | — |
| transactions | 748686498 | Grep index for "transaction" in name/description | UKBA |
| reference data | 600754944 | Grep index: 11 entries in `buk-domain-reference-data` | CS |
| address | — | Grep index for "address" in name/description | CS |
| cardholder | — | Grep index for "cardholder" in name/description | CAMS |
| payment | — | Grep index: 38 entries in `buk-domain-payment-initiation` | UKBA |
| PIN | — | Grep index for "pin" in name/description | CAMS |
| offers | — | Grep index: 2 entries in `buk-domain-offer-management` | — |
| disputes | — | Grep index for "dispute" in name/description | — |
| device | 2251699755 | Grep index for "device" in name/description | — |
| credit | — | Grep index: 25 entries in `buk-domain-customer-credit-and-risk-rating` | UKBA, Triumph |
| rate | — | Grep index for "rate" in name/description | UKBA |
| flag | — | Grep index for "flag" in name/description | CS |
| statement | — | Grep index for "statement" in name/description | UKBA |
| reward | — | Grep index: 19 entries in `buk-domain-loyalty-and-rewards` | Triumph |
| affordability | — | Grep index for "affordability" in name/description | UKBA |
| mortgage | — | Grep index: 59 entries in `buk-domain-secured-lending` | UKBA |
| loan | — | Grep index: 148 entries in `buk-domain-unsecured-lending` | ALS |
| savings | — | Grep index: 9 entries in `buk-domain-savings` | UKBA |
| debit card | — | Grep index for "debit" in name/description | CAMS |
| credit card | 1901673378 | Grep index for "credit-card" or "creditcard" in name | Triumph/Barclaycard |
| foreign currency | — | Grep index for "currency" in name/description | SOLD |
| investment | — | Grep index: 26 entries in `buk-domain-investing` | FNZ |
| insurance | — | Grep index: 16 entries in `buk-domain-insurance` | — (via MAHO) |
| correspondence | — | Grep index: 12 entries in `buk-domain-documents` | CMOD |
| segments | — | Grep index for "segment" in name/description | CS |
| contact | — | Grep index for "contact" in name/description | CS |
| audit | — | Grep index for "audit" in name/description | CS |
| beneficiaries | 785961061 | Grep index for "beneficiar" in name/description | — |
| GraphQL | 1415824141 | Grep index for "graphql" in name/tags | — |
| RPS | 1122395530 | Grep index for "rps" in name/description | — |
| bereavement | 3719915412 | Grep index: 3 entries in `buk-domain-bereavements` | — |
| core customer details | — | Grep index for "core-customer" or "coreCustomer" in name | CS |
| CRM | COOCUSTCRM:1798520644, 3852609006, 3869364420, 3489855661, 3805456113, 3519157596, 2625164542, 2164463698, 1850479771, 2519147208, 2036556786, 2691519244, 2819361412, 2755553460, 2804335454 | Grep index: 25 entries in `buk-domain-customer-case-management` | — |
| preferences | 785965261 | COOCUSTCRM: 1850479771 | CS |
| marketing consent | 785965261 | COOCUSTCRM: 1850479771 | CS |
| TDLCCME | 879235084 | COOCUSTCRM: 1850479771 | CS |
| marker audit | — | COOCUSTCRM: 2519147208 | CS |
| SOLD | 918585340, 2018021097, 822758105 | — | SOLD |
| customer insights | 2229551050 | — | CS |
| NGCB | 968094106 | — | NGCB |
| stop cheque | 673377471 | — | UKBA |
| credit risk bureau | 713994225 | — | CS |
| PINSentry | — | COOCUSTCRM: 1999671376 | CS |
| tax | — | COOCUSTCRM: 2005034758 | CS |
| membership maintenance | — | COOCUSTCRM: 2164463698 | Triumph |
| create customer | — | COOCUSTCRM: 2804335454 | CS |
| update customer | — | COOCUSTCRM: 3852609006 | CS |

---

## ODS GraphQL API — Field-Level Reference Source

The ODS GraphQL API (`sodsgraphql`) provides a unified query interface across all ODS source systems. Its **schema files are self-documenting** — every field includes a `**Lineage**` annotation showing the exact source system table and column. Use this as a **fallback reference** when REST API candidates have metadata-only or partial documentation, or when field-level verification is needed against source system mappings.

**GitLab:** `barclays/ods-apis/app/sodsgraphql` (branch: `release/1.16`)
**Schema path:** `src/main/resources/schema/`
**Confluence LLD:** [Enquiry Domain GraphQL Process API LLD](https://confluence.barcapint.com/spaces/pcbcooiit/pages/971994013/Enquiry+Domain+GraphQL+Process+API+LLD)
**Endpoint:** `v3/graphql`

### Source System → GraphQL Schema Mapping

| MTS Source System | Schema File | GraphQL Type | Query Path |
|-------------------|-------------|--------------|------------|
| CS / UKBA | `retail-account-detail.graphql` | `BranchAccountHolding`, `BranchAccount` | `retailCustomer.productHolding.branchAccountHoldings` |
| ALS | `retail-account-detail.graphql` | `AlsAccountHolding` | `retailCustomer.productHolding.alsAccountHoldings` |
| ILP (Mortgages) | `retail-account-detail.graphql` | `IlpAccountHolding` | `retailCustomer.productHolding.ilpAccountHoldings` |
| SOLD | `retail-account-detail.graphql` | `SoldAccountHolding` | `retailCustomer.productHolding.soldAccountHoldings` |
| Triumph (Cards) | `cards-account-detail.graphql` | `CardAccountDetail` | `cardCustomer` / `cardAccount` |
| CAMS (Debit Cards) | `retail-account-detail.graphql` | `DebitCard` | `retailCustomer...branchAccount.debitCards` |
| Historical Balances | `history-balance-details.graphql` | `BalanceDetailsCollection` | `historicalBalanceByAccountNumber(sourceSystem: ALS/ILP/SOLD/UKBA/TRIUMPH/BPF)` |

### How to Use for Field Verification

Fetch the schema file via GitLab MCP:
```
mcp__Gitlab__get_file_contents(
  project_id="barclays/ods-apis/app/sodsgraphql",
  file_path="src/main/resources/schema/<schema-file>.graphql",
  ref="release/1.16"
)
```

Each field in the schema has a documentation block like:
```graphql
"""
Outstanding Principal \
**Since   :** 1.9 \
**Lineage :** Derived Field;
IF TEJVRT01.RT_PROC_STAT EQUAL 'CF' AND TEJVRT02.RT_TOT_PRIN EQUAL ZERO
THEN USE TEJVRT02.RT_TOT_COFF_AMT ELSE TEJVRT02.RT_TOT_PRIN
"""
outstandingPrincipal: BigDecimal
```

Match the `**Lineage**` source table/column against the MTS service doc's DAG fields or TDL tables to confirm field equivalence.

### ALS Design Reference

For ALS-specific field mappings (loans), see: [GraphQL Design - PWR45500 - ALS Data](https://confluence.barcapint.com/spaces/pcbcooiit/pages/1563096900/GraphQL+Design+-+PWR45500+-+ALS+Data)

---

## Maintenance Notes

- To add new mappings, update the **Direct Mappings** table and the **Keyword Index**.
- Page IDs are from the Barclays internal Confluence instance (`confluence.barcapint.com`).
- **pcbcooiit pages:** Refresh by listing children of page 507590733 via Confluence API.
- **COOCUSTCRM pages:** Use `confluence_search` with `search_pages: ["1798520644"]` and `search_descendants: true`. All 30+ pages are now pre-indexed above.
- **Backstage Catalogue (Source 3):** At runtime, `backstage_clone.py` clones the `developmentForProd` branch of `barclays/software-catalogue/software-catalog-templates` for live grep (Layer 1A). The static `backstage_catalogue_index.md` is a fallback (Layer 1B). To refresh the static index, run `/refresh-ods-catalogue`.
- **Additional spaces (v1.3):** EST, DCMDEV, APITECHDES, EMMAPIS, EPZOSCON — validated by parent page ID. Use `confluence_search` with `search_pages` and `search_descendants: true` to list children.
- The `/api-replacement-match` command uses: Layer 1 (Backstage live clone or static index), Layer 2 (this seed catalogue + pcbcooiit), Layer 3 (PCBICCAPIS), Layer 4 (COOCUSTCRM), Layer 5 (GRPQRTUKBA), Layer 6 (BCDUKCAPI), Layers 7a-7e (EST, DCMDEV, APITECHDES, EMMAPIS, EPZOSCON — conditional), Layer 8 (Deep Investigation).
