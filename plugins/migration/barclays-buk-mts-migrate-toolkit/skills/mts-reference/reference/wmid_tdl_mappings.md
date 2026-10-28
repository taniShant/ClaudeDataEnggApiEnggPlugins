# WMID to TDL Table Mappings

Convention: `WMID-XXXX-PRM` maps to `TDLXXXX` (or `TDKXXXX` for some strategy tables).

**TOO_MANY_ROWS confirmation:** Response classes (e.g., `CustomerResponse.java`) contain `TOO_MANY_ROWS_TDL*` constants that independently confirm table names.

## DataGroup → WMID → TDL Full Chain

This table shows the complete chain from Java DataGroup enum through WMID flag to mainframe TDL table, grouped by the Transaction class that uses them. Use this during Phase 1 (Step 1.11) to cross-validate extracted mappings, and during per-service documentation to build the DataGroup Chain visual.

### CustomerAllRetrieveTransaction Chain

| DataGroup Enum | WMID Parameter | TDL Table | Transaction(s) Using It |
|----------------|----------------|-----------|-------------------------|
| `CUSTOMER_DETAIL` | `WMID-CUST-PRM` | TDLCUST | CustomerAllRetrieveTransaction, CustomerRetrieveTransaction |
| `PERSONAL_DETAIL` | `WMID-CUST-PRM` | TDLCUST | CustomerAllRetrieveTransaction (compound) |
| `BUSINESS_DETAIL` | `WMID-CUST-PRM` | TDLCUST | CustomerAllRetrieveTransaction (compound) |
| `CRA_DETAILS` | `WMID-CUST-PRM` | TDLCUST | CustomerAllRetrieveTransaction (compound) |
| `PERSONAL_CUSTOMER_DETAIL` | `WMID-PCUS-PRM` | TDLPCUS | CustomerAllRetrieveTransaction |
| `CONTACT_POINT` | `WMID-CTPT-PRM` | TDLCTPT | CustomerAllRetrieveTransaction |
| `LOCATION` | `WMID-CULO-PRM` | TDLCULO | CustomerAllRetrieveTransaction |
| `SEGMENT` | `WMID-CSEG-PRM` | TDLCSEG | CustomerAllRetrieveTransaction |
| `INCOME` | `WMID-INCM-PRM` | TDLINCM | CustomerAllRetrieveTransaction |
| `EMAIL_ADDRESS` | `WMID-EMAD-PRM` | TDLEMAD | CustomerAllRetrieveTransaction |
| `EMPLOYMENT` | `WMID-CUEM-PRM` | TDLCUEM | CustomerAllRetrieveTransaction |
| `MISC_ACCOUNT_HOLDING` | `WMID-MAHO-PRM` | TDLMAHO | CustomerAllRetrieveTransaction |
| `BANK_ACCOUNT_HOLDING` | `WMID-BAHO-PRM` | TDLBAHO | CustomerAllRetrieveTransaction |
| `CARD_ACCOUNT_HOLDING` | `WMID-CAHO-PRM` | TDLCAHO | CustomerAllRetrieveTransaction |
| `BARCLAYCARD_HOLDING` | `WMID-BARH-PRM` | TDLBARH | CustomerAllRetrieveTransaction |
| `CARD_CROSS_REF` | `WMID-CCAX-PRM` | TDLCCAX | CustomerAllRetrieveTransaction |
| `ADDITIONAL_PRODUCT_HOLDING` | `WMID-ADPR-PRM` | TDLADPR | CustomerAllRetrieveTransaction |
| `KYC_PERSONAL_DETAIL` | `WMID-PCKD-PRM` | TDLPCKD | CustomerAllRetrieveTransaction |
| `KYC_SUMMARY` | `WMID-CUKD-PRM` | TDLCUKD | CustomerAllRetrieveTransaction |
| `RELATIONSHIP` | `WMID-CURL-PRM` | TDLCURL | CustomerAllRetrieveTransaction |
| `COMMITMENT` | `WMID-CUCM-PRM` | TDLCUCM | CustomerAllRetrieveTransaction |
| `EDUCATION` | `WMID-EDUD-PRM` | TDLEDUD | CustomerAllRetrieveTransaction |
| `DEPENDANT` | `WMID-DEPD-PRM` | TDLDPDT | CustomerAllRetrieveTransaction |
| `LIFE_EVENT` | `WMID-CULE-PRM` | TDLCULE | CustomerAllRetrieveTransaction |
| `COMPETITOR_PRODUCT_HOLDING` | `WMID-CPDH-PRM` | TDLCPDH | CustomerAllRetrieveTransaction |
| `RELATED_BUSINESS_UNIT` | `WMID-CBUR-PRM` | TDLCBUR | CustomerAllRetrieveTransaction |
| `CONTACT_METHOD_EXCLUSION` | `WMID-CCME-PRM` | TDLCCME | CustomerAllRetrieveTransaction |
| `CREDIT_STRATEGY` | `WMID-DCCS-PRM` | TDKDCCS | CustomerAllRetrieveTransaction |
| `CUSTOMER_CREDIT_STRATEGY` | `WMID-JCCS-PRM` | TDKJCCS | CustomerAllRetrieveTransaction |
| `RELATED_EMPLOYEE` | `WMID-CUER-PRM` | TDLCUER | CustomerAllRetrieveTransaction |
| `RESERVED_ACCOUNT` | `WMID-RAHO-PRM` | TDLRAHO | CustomerAllRetrieveTransaction |
| `REGISTRATION` | `WMID-CURG-PRM` | TDLCURG | CustomerAllRetrieveTransaction |

> This chain table is populated during Phase 1 Step 1.11. The above entries are the reference baseline — the actual set depends on which DataGroups each Command class requests.

### Compound DataGroup Conditions

Some DataGroup enums share the same WMID parameter. The Transaction constructor uses OR conditions — if **any** of the listed DataGroups is requested, the WMID flag is set.

| WMID Parameter | Triggering DataGroups | TDL Table | Notes |
|----------------|-----------------------|-----------|-------|
| `WMID-CUST-PRM` | `CUSTOMER_DETAIL`, `PERSONAL_DETAIL`, `BUSINESS_DETAIL`, `CRA_DETAILS` | TDLCUST | Most common compound condition. All four DataGroups share one mainframe table. |

> **Impact on documentation:** When a Command requests `PERSONAL_DETAIL`, the per-service doc should show both the DataGroup requested AND the WMID flag actually set (which may differ in name). The compound condition table above resolves this mapping.

## WMID → TDL Quick Reference

This is the canonical mapping from WMID parameter to TDL table name. Use for quick lookups when you already know the WMID parameter.

| WMID Parameter | TDL Table | Description |
|----------------|-----------|-------------|
| `WMID-CUST-PRM` | TDLCUST | Customer Detail |
| `WMID-PCUS-PRM` | TDLPCUS | Personal Customer Detail |
| `WMID-CTPT-PRM` | TDLCTPT | Contact Points |
| `WMID-CULO-PRM` | TDLCULO | Customer Locations/Addresses |
| `WMID-CSEG-PRM` | TDLCSEG | Customer Segments |
| `WMID-INCM-PRM` | TDLINCM | Income Details |
| `WMID-EMAD-PRM` | TDLEMAD | Email Addresses |
| `WMID-CUEM-PRM` | TDLCUEM | Customer Employment |
| `WMID-MAHO-PRM` | TDLMAHO | Miscellaneous Account Holdings |
| `WMID-BAHO-PRM` | TDLBAHO | Bank Account Holdings (UKBA) |
| `WMID-CAHO-PRM` | TDLCAHO | Card Account Holdings |
| `WMID-BARH-PRM` | TDLBARH | Barclays Bank Card Holdings (legacy) |
| `WMID-CCAX-PRM` | TDLCCAX | Card Cross-reference (newer) |
| `WMID-ADPR-PRM` | TDLADPR | Additional Product Holdings |
| `WMID-PCKD-PRM` | TDLPCKD | KYC Personal Details |
| `WMID-CUKD-PRM` | TDLCUKD | KYC Summary |
| `WMID-CURL-PRM` | TDLCURL | Relationship Details |
| `WMID-CUCM-PRM` | TDLCUCM | Commitment Details |
| `WMID-EDUD-PRM` | TDLEDUD | Education Details |
| `WMID-DEPD-PRM` | TDLDPDT | Dependant Details |
| `WMID-CULE-PRM` | TDLCULE | Life Events |
| `WMID-CPDH-PRM` | TDLCPDH | Competitor Product Holdings |
| `WMID-CBUR-PRM` | TDLCBUR | Related Business Units |
| `WMID-CCME-PRM` | TDLCCME | Contact Method Exclusions |
| `WMID-DCCS-PRM` | TDKDCCS | Credit Strategy |
| `WMID-JCCS-PRM` | TDKJCCS | Customer Credit Strategy |
| `WMID-CUER-PRM` | TDLCUER | Related Employees |
| `WMID-RAHO-PRM` | TDLRAHO | Reserved Account Details |
| `WMID-CURG-PRM` | TDLCURG | Customer Registrations |