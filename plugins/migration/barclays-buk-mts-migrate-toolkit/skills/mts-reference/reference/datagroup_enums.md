# DataGroup Enum Types

DataGroup enums control which data segments are requested from the mainframe via EGS gateways. Each enum constant maps to a `WMID-*-PRM` flag in the outbound message, which in turn targets a specific TDL table on the mainframe.

## CustomerDataGroup (egs_customer)

Used by `CustomerGateway.findByPrimaryKey()` and related customer retrieval methods. Each enum constant triggers a `WMID-*-PRM` flag in the transaction's ROP message, causing the mainframe to return data from the corresponding TDL table.

### Full Enum Constant Table

| Enum Constant | WMID Parameter | TDL Table | Description |
|---------------|----------------|-----------|-------------|
| `CUSTOMER_DETAIL` | `WMID-CUST-PRM` | TDLCUST | Core customer record (name, type, status) |
| `PERSONAL_DETAIL` | `WMID-CUST-PRM` | TDLCUST | Personal customer fields (compound condition — shares WMID with CUSTOMER_DETAIL) |
| `BUSINESS_DETAIL` | `WMID-CUST-PRM` | TDLCUST | Business customer fields (compound condition) |
| `CRA_DETAILS` | `WMID-CUST-PRM` | TDLCUST | CRA-specific customer fields (compound condition) |
| `PERSONAL_CUSTOMER_DETAIL` | `WMID-PCUS-PRM` | TDLPCUS | Extended personal customer detail |
| `CONTACT_POINT` | `WMID-CTPT-PRM` | TDLCTPT | Contact points (phone, fax) |
| `LOCATION` | `WMID-CULO-PRM` | TDLCULO | Customer locations / addresses |
| `SEGMENT` | `WMID-CSEG-PRM` | TDLCSEG | Customer segments (propositions, marketing segments) |
| `INCOME` | `WMID-INCM-PRM` | TDLINCM | Income details |
| `EMAIL_ADDRESS` | `WMID-EMAD-PRM` | TDLEMAD | Email addresses |
| `EMPLOYMENT` | `WMID-CUEM-PRM` | TDLCUEM | Employment history |
| `MISC_ACCOUNT_HOLDING` | `WMID-MAHO-PRM` | TDLMAHO | Miscellaneous account holdings |
| `BANK_ACCOUNT_HOLDING` | `WMID-BAHO-PRM` | TDLBAHO | Bank account holdings (UKBA) |
| `CARD_ACCOUNT_HOLDING` | `WMID-CAHO-PRM` | TDLCAHO | Card account holdings |
| `BARCLAYCARD_HOLDING` | `WMID-BARH-PRM` | TDLBARH | Barclays Bank card holdings (legacy) |
| `CARD_CROSS_REF` | `WMID-CCAX-PRM` | TDLCCAX | Card cross-reference (newer) |
| `ADDITIONAL_PRODUCT_HOLDING` | `WMID-ADPR-PRM` | TDLADPR | Additional product holdings |
| `KYC_PERSONAL_DETAIL` | `WMID-PCKD-PRM` | TDLPCKD | KYC personal details |
| `KYC_SUMMARY` | `WMID-CUKD-PRM` | TDLCUKD | KYC summary |
| `RELATIONSHIP` | `WMID-CURL-PRM` | TDLCURL | Relationship details |
| `COMMITMENT` | `WMID-CUCM-PRM` | TDLCUCM | Commitment details |
| `EDUCATION` | `WMID-EDUD-PRM` | TDLEDUD | Education details |
| `DEPENDANT` | `WMID-DEPD-PRM` | TDLDPDT | Dependant details |
| `LIFE_EVENT` | `WMID-CULE-PRM` | TDLCULE | Life events |
| `COMPETITOR_PRODUCT_HOLDING` | `WMID-CPDH-PRM` | TDLCPDH | Competitor product holdings |
| `RELATED_BUSINESS_UNIT` | `WMID-CBUR-PRM` | TDLCBUR | Related business units |
| `CONTACT_METHOD_EXCLUSION` | `WMID-CCME-PRM` | TDLCCME | Contact method exclusions |
| `CREDIT_STRATEGY` | `WMID-DCCS-PRM` | TDKDCCS | Credit strategy (TDK prefix) |
| `CUSTOMER_CREDIT_STRATEGY` | `WMID-JCCS-PRM` | TDKJCCS | Customer credit strategy (TDK prefix) |
| `RELATED_EMPLOYEE` | `WMID-CUER-PRM` | TDLCUER | Related employees |
| `RESERVED_ACCOUNT` | `WMID-RAHO-PRM` | TDLRAHO | Reserved account details |
| `REGISTRATION` | `WMID-CURG-PRM` | TDLCURG | Customer registrations |
| `CUSTOMER_ALERT` | `WMID-CUAG-PRM` | TDLCUAG | Customer alerts |
| `CUSTOMER_PREFERENCE` | `WMID-CUPF-PRM` | TDLCUPF | Customer preferences |
| `CUSTOMER_INTERACTION` | `WMID-CUIN-PRM` | TDLCUIN | Customer interactions |
| `CUSTOMER_NOTE` | `WMID-CUNO-PRM` | TDLCUNO | Customer notes |
| `MARKETING_CONSENT` | `WMID-MKCO-PRM` | TDLMKCO | Marketing consent |
| `VULNERABILITY` | `WMID-VULN-PRM` | TDLVULN | Vulnerability indicators |
| `CUSTOMER_OFFER` | `WMID-CUOF-PRM` | TDLCUOF | Customer offers |
| `PENSION_DETAIL` | `WMID-PENS-PRM` | TDLPENS | Pension details |
| `SAVINGS_DETAIL` | `WMID-SAVD-PRM` | TDLSAVD | Savings details |
| `MORTGAGE_DETAIL` | `WMID-MRTG-PRM` | TDLMRTG | Mortgage details |
| `INSURANCE_DETAIL` | `WMID-INSD-PRM` | TDLINSD | Insurance details |
| `INVESTMENT_DETAIL` | `WMID-INVD-PRM` | TDLINVD | Investment details |
| `LOAN_DETAIL` | `WMID-LOAD-PRM` | TDLLOAD | Loan details |
| `OVERDRAFT_DETAIL` | `WMID-OVRD-PRM` | TDLOVRD | Overdraft details |
| `DIRECT_DEBIT` | `WMID-DIRD-PRM` | TDLDIRD | Direct debit details |
| `STANDING_ORDER` | `WMID-STOD-PRM` | TDLSTOD | Standing order details |
| `REGULAR_PAYMENT` | `WMID-RGPY-PRM` | TDLRGPY | Regular payment details |
| `TAX_DETAIL` | `WMID-TAXD-PRM` | TDLTAXD | Tax details |
| `BENEFIT_DETAIL` | `WMID-BENE-PRM` | TDLBENE | Benefit details |
| `EXPENSE_DETAIL` | `WMID-EXPN-PRM` | TDLEXPN | Expense details |
| `AFFORDABILITY` | `WMID-AFFD-PRM` | TDLAFFD | Affordability data |
| `PRODUCT_HOLDING_SUMMARY` | `WMID-PHSM-PRM` | TDLPHSM | Product holding summary |
| `CUSTOMER_RISK` | `WMID-CRSK-PRM` | TDLCRSK | Customer risk indicators |
| `CUSTOMER_EVENT` | `WMID-CUEV-PRM` | TDLCUEV | Customer events |
| `CUSTOMER_TASK` | `WMID-CUTK-PRM` | TDLCUTK | Customer tasks |
| `CUSTOMER_DOCUMENT` | `WMID-CDOC-PRM` | TDLCDOC | Customer documents |
| `CUSTOMER_CHANNEL` | `WMID-CCHN-PRM` | TDLCCHN | Customer channel preferences |
| `CUSTOMER_DEVICE` | `WMID-CDVC-PRM` | TDLCDVC | Customer device registrations |
| `THIRD_PARTY_PROVIDER` | `WMID-TPPR-PRM` | TDLTPPR | Third party provider access |
| `OPEN_BANKING` | `WMID-OPBK-PRM` | TDLOPBK | Open banking consent |
| `CUSTOMER_MANDATE` | `WMID-CMND-PRM` | TDLCMND | Customer mandates |
| `CUSTOMER_POWER_OF_ATTORNEY` | `WMID-CPOA-PRM` | TDLCPOA | Power of attorney details |
| `CUSTOMER_DECEASED` | `WMID-CDCD-PRM` | TDLCDCD | Deceased customer details |
| `CUSTOMER_BEREAVEMENT` | `WMID-CBRV-PRM` | TDLCBRV | Bereavement details |
| `CUSTOMER_FRAUD` | `WMID-CFRD-PRM` | TDLCFRD | Fraud indicators |
| `CUSTOMER_COMPLAINT` | `WMID-CCMP-PRM` | TDLCCMP | Complaint details |
| `CUSTOMER_SANCTION` | `WMID-CSNC-PRM` | TDLCSNC | Sanctions screening |
| `CUSTOMER_PEP` | `WMID-CPEP-PRM` | TDLCPEP | Politically exposed person check |
| `CUSTOMER_AML` | `WMID-CAML-PRM` | TDLCAML | Anti money laundering indicators |
| `CUSTOMER_IDENTITY_VERIFICATION` | `WMID-CIDV-PRM` | TDLCIDV | Identity verification status |
| `CUSTOMER_DIGITAL_IDENTITY` | `WMID-CDID-PRM` | TDLCDID | Digital identity records |
| `CUSTOMER_CONSENT` | `WMID-CCON-PRM` | TDLCCON | Consent records |

> **Note:** This table covers the most commonly observed enum constants. Actual enum availability depends on the `egs_customer` JAR version in use. During Phase 1 discovery (Steps 1.10-1.11), the agent extracts the *actual* enum values from the project's specific JAR version. This table serves as a reference for gap-filling when source JARs are unavailable.

### Compound DataGroup Conditions

Some Transaction constructors use compound conditions where multiple DataGroup enums trigger the same WMID parameter. This is a Java-side optimisation — the mainframe sees only one flag.

| WMID Parameter | DataGroup Enums (any triggers it) | TDL Table |
|----------------|-----------------------------------|-----------|
| `WMID-CUST-PRM` | `CUSTOMER_DETAIL`, `PERSONAL_DETAIL`, `BUSINESS_DETAIL`, `CRA_DETAILS` | TDLCUST |

> **Pattern:** In the Transaction constructor, these appear as:
> ```
> if (request.isRequested(CustomerDataGroup.CUSTOMER_DETAIL)
>     || request.isRequested(CustomerDataGroup.PERSONAL_DETAIL)
>     || request.isRequested(CustomerDataGroup.BUSINESS_DETAIL)
>     || request.isRequested(CustomerDataGroup.CRA_DETAILS)) {
>     addField("WMID-CUST-PRM", "Y");
> }
> ```
> Phase 1 Step 1.11 captures these compound conditions automatically.

## AccountDataGroup (egs_ukba)

Used by `AccountGateway.findByKeySet()`. UKBA account details (balances, limits, status) accessed via MAE V3 field-selector bitmask. Unlike CustomerDataGroup, AccountDataGroup uses a **bitmask pattern** rather than individual WMID flags — each DataGroup sets bits in a field-selector word that tells the mainframe which data segments to return.

Key enum constants include: `ACCOUNT_DETAIL`, `BALANCE`, `LIMIT`, `STATUS`, `INTEREST_RATE`, `PRODUCT_DETAIL`, `MANDATE`, `DIRECT_DEBIT`, `STANDING_ORDER`, `TRANSACTION_HISTORY`.

> AccountDataGroup mappings are extracted during Phase 1 from the `egs_ukba` or `egs_odsmfukba` source JAR when available.

## PfsDataGroup (egs_customer)

Used by `CustomerGateway.findPfsDataByCustomerId()`. Personal Financial Summary data (mortgages, savings, investments). Uses the same WMID flag pattern as CustomerDataGroup but targets PFS-specific TDL tables.

Key enum constants include: `PFS_MORTGAGE`, `PFS_SAVINGS`, `PFS_INVESTMENT`, `PFS_INSURANCE`, `PFS_LOAN`, `PFS_PENSION`.

## ProductDataGroup (egs_product)

Used by `ProductGateway.findByPrimaryKey()`. Product details via direct DB2 SQL on `TI_TUKPROD`. This DataGroup does **not** use mainframe transactions — it queries DB2 directly.

Key enum constants include: `PRODUCT_DETAIL`, `PRODUCT_FEATURE`, `PRODUCT_RATE`, `PRODUCT_FEE`.