# Barclays Internal Libraries - Version Reference (Parts A-D)

> **Versions in this file are the SOURCE OF TRUTH.** Do NOT override them with Nexus search results. Only use Nexus for libraries NOT listed in this file.
> **emm groupId preference:** When Nexus returns two variants, prefer the `emm` groupId.

---

## ⚠ CRITICAL BUILD VERSIONS — Read These First, Use These, Do NOT Search Nexus for These

| Property | Value | Usage |
|----------|-------|-------|
| `SDK3_VERSION` | `1.12.007` | `gradle.properties`: `SDK3_VERSION=1.12.007` |
| SDK3 BOM artifact | `com.barclays.api:sdk3:1.12.007` | `buildSrc/build.gradle` platform dependency |
| bap-bld-lib-plugin | BOM managed | Pulled in via SDK3 platform dependency — do NOT specify explicit version |
| Gradle wrapper version | `8.13` | `gradle/wrapper/gradle-wrapper.properties` |

**Gradle wrapper URL (exact):**
```
distributionUrl=https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
```

**buildSrc/build.gradle `dependencies` block (exact):**
```groovy
implementation(platform("com.barclays.api:sdk3:${sdkVersion}"))
implementation("com.barclays.api:bap-bld-lib-plugin")
implementation("com.barclays.api:bap-bld-lib-kotlin-int-test-gradle-plugin")
implementation("org.springframework.boot:spring-boot-gradle-plugin") {
    exclude group: 'ch.qos.logback', module: 'logback-classic'
}
```

**Mandatory `gradle.properties` entry (always add):**
```properties
DISABLE_OAS_GENERATION=true
```

**Do NOT search Nexus for `sdk3` versions or `bap-bld-lib-plugin` versions when these are documented here.** Only search Nexus for project-specific dependencies not listed in this file.

---

## Table of Contents

### Part A: Common Platform Libraries (39 libraries)
Shared across ALL Barclays projects - filters, tokenization, ODS, Triumph, encryption, resilience

- [A.1 System Parent POM Group](#a1-system-parent-pom-group)
- [A.2 Core Parent POM Group](#a2-core-parent-pom-group)
- [A.3 Common Parent POM Group](#a3-common-parent-pom-group)
- [A.4 Common Libraries Migration Patterns](#a4-common-libraries-migration-patterns)

### Part B: System Components (564 libraries)
Domain-specific business logic - ODS wrappers, commands, queries

- [B.1 ODS Wrapper Components](#b1-ods-wrapper-components)
- [B.2 System Command Components](#b2-system-command-components)
- [B.3 System Query Components](#b3-system-query-components)
- [B.4 Domain-Specific Libraries](#b4-domain-specific-libraries)
- [B.5 System Components Migration Patterns](#b5-system-components-migration-patterns)

### Part C: Quick Reference
- [C.1 Version Upgrade Quick Reference](#c1-version-upgrade-quick-reference)
- [C.2 Critical Upgrades](#c2-critical-upgrades)
- [C.3 Troubleshooting](#c3-troubleshooting)

### Part D: EMM Domain Libraries
Enterprise Mobile Management domain libraries

- [D.1 EMM Common Core Libraries](#d1-emm-common-core-libraries)
- [D.2 BAP BLD Libraries](#d2-bap-bld-libraries)
- [D.3 GroupId Migration Reference](#d3-groupid-migration-reference)

### Part E: JDK21 Tracker Additions (222 libraries)
Additional entries from the JDK Migration Tracker — not previously documented

- [E.1 ODS Wrapper Components (JDK21)](#e1-ods-wrapper-components-jdk21)
- [E.2 System Command Components (JDK21)](#e2-system-command-components-jdk21)
- [E.3 System Query Components (JDK21)](#e3-system-query-components-jdk21)
- [E.5 BPF Process Components (JDK21)](#e5-bpf-process-components-jdk21)

---

# PART A: COMMON PLATFORM LIBRARIES

## Executive Summary

39 core libraries organized under 3 parent POMs, used across all Barclays API projects.

**Key Metrics:**
- **Total Libraries:** 39 core common libraries
- **Organized Under:** 3 parent POMs (system-parent-pom, core-parent-pom, common-parent-pom)
- **Pre-Java 17 Versions:** SDK2 compatible (Java 8-based)
- **Java 17+ Versions:** SDK3 compatible (Java 21-based)

---

## A.1 System Parent POM Group

Foundation POM for SDK3 platform configuration.

| Sr | Library | Java 17+ |
|----|---------|----------|
| A | **system-parent-pom** | 1.0.+ |

---

## A.2 Core Parent POM Group

7 fundamental utilities used across the platform.

| Sr | Library | Java 17+ |
|----|---------|----------|
| 1 | core-components | 1.1-000 |
| 2 | core-query-service-api | 2.0.+ |
| 3 | common-core | 1.0.+ |
| 4 | system-core | 7.1-001 |
| 5 | common-context-api | 2.0.+ |
| 6 | core-mapping | **2.0.+** |
| 7 | common-thread | 2.0.+ |

**Dependency Chain:**
```
core-parent-pom:1.0.+
├─ core-components:1.1-000
├─ core-query-service-api:2.0.+
├─ common-core:1.0.+
├─ system-core:7.1-001
├─ common-context-api:2.0.+
├─ core-mapping:2.0.+
└─ common-thread:2.0.+
```

---

## A.3 Common Parent POM Group

31 libraries covering filtering, tokenization, exceptions, ODS, Triumph, and security.

### A.3.1 Core Filter & Context (CRITICAL)

| Sr | Library | Java 17+ |
|----|---------|----------|
| 1 | core-jsonapi-web | **5.2-001** |
| 2 | common-context | **2.0.+** |
| 3 | common-filter | **5.0.+** |

**SDK3 Notes:**
- `common-filter:5.0.+` is the **MANDATORY** upgrade target
- `common-filter:4.1.+` (SDK2) contains `DefaultFilterBootstrap` extending SDK2 classes
- See lessons_learnt/cards_api.md Card 7 for detailed migration guidance

### A.3.2 Tokenization & Encryption

| Sr | Library | Java 17+ |
|----|---------|----------|
| 4 | common-uuid | 2.0.+ |
| 5 | common-tokenisation | 2.0.+ |
| 6 | core-tokenise | 2.0.+ |
| 7 | domain-core-tokenization-uuid | **7.1-001** |
| 8 | domain-core-tokenization-protegrity | **8.2-002** |
| 9 | core-secure-value-tokenizer | 5.0.+ |

**Key Migration Notes:**
- **domain-core-tokenization-uuid:7.1-001** - Fixed UUID detokenization for request body attributes
  - Requires: `uuid.packageName=<your.package.name>` in tokenization.properties
- **domain-core-tokenization-protegrity:8.2-002** - Enhanced Protegrity integration

### A.3.3 Exception & Service Core

| Sr | Library | Java 17+ |
|----|---------|----------|
| 10 | core-exception-model | 2.0.+ |
| 11 | executor-core | **2.0.+** |
| 12 | core-secure-object | 2.1-000 |
| 13 | domain-service-core | 4.0.+ |

### A.3.4 Triumph Integration

| Sr | Library | Java 17+ |
|----|---------|----------|
| 14 | triumph-atom-builder | 3.0.+ |
| 15 | triumph-executor-core | 5.0.+ |
| 16 | core-triumph | **9.1-000** |
| 17 | triumph-atom-uamemod2 | (No update) |
| 18 | system-cmd-memorandum | 6.0.+ |
| 19 | stub-triumph | 3.0.+ |

**SDK3 Considerations:**
- **core-triumph:9.1-000** - Updated for Spring Boot 3.5.+ integration
- **Note:** Group ID changed from `com.barclaycard.digital` to `com.barclaycard.digital.core`

### A.3.5 ODS Integration

| Sr | Library | Java 17+ |
|----|---------|----------|
| 20 | system-core-ods | **6.1-001** |
| 21 | core-ods-query-service | 4.0.+ |
| 22 | system-core-datasource | 7.1-000 |
| 23 | system-core-resilliency | N/A |

**SDK3 Notes:**
- `system-core-datasource:7.1-000` uses HikariCP with Java 21 APIs
- `system-core-resilliency:3.0.+` - **DEPRECATED** - Use resilience4j instead

### A.3.6 Resilience & Observability (NEW)

| Sr | Library | Java 17+ |
|----|---------|----------|
| 24 | system-core-resilience4j | **1.0.+** |

**Features:**
- Custom propagator copies request context to resilience4j threads
- Configuration for circuit breaker, bulkhead, time limiter
- Replaces deprecated Hystrix-based resilience

### A.3.7 Web & Domain Services

| Sr | Library | Java 17+ |
|----|---------|----------|
| 25 | domain-web-core | 9.0.+ |
| 26 | domain-service-core-api | 1.0.+ |
| 27 | test-utilities | **8.0-000** |

### A.3.8 Cryptography & Security

#### SecurityFilter - Jakarta EE Migration (CRITICAL)

| Sr | Library | Java 17+ |
|----|---------|----------|
| 27a | **securityFilter** | **7.0.0-RELEASE** |

**SDK3 Migration (MANDATORY):**
```gradle
// SDK2 (javax.servlet)
implementation 'com.barclays.security:securityFilter:6.x'

// SDK3 (jakarta.servlet) - REQUIRED
implementation 'com.barclays.security:securityFilter:7.0.0-RELEASE'
```

**Error Without Upgrade:**
```
java.lang.NoClassDefFoundError: javax/servlet/Filter
ClassCastException: cannot be cast to jakarta.servlet.Filter
```

#### Other Security Libraries

| Sr | Library | Java 17+ |
|----|---------|----------|
| 28 | system-cmd-protegrity | 5.1-000 |
| 29 | domain-core-agnostic-gateway | **5.1-000** |
| 30 | domain-core-protegrity | 3.1-000 |
| 31 | core-ssl | 2.0.+ |
| 32 | core-bcag-encryption | 7.0.+ |
| 33 | core-bcag-encryption-api | 1.0.+ |
| 34 | core-jose | 4.0.+ |
| 35 | core-jose-api | 1.0.+ |
| 36 | domain-core-hybrid-decryption | 3.1-000 |
| 37 | domain-core-hybrid-decryption-api | 1.0.+ |

### A.3.9 Rules Engine

| Sr | Library | Java 17+ |
|----|---------|----------|
| 38 | common-rules-api | 2.0.+ |
| 39 | common-rules-impl | 3.0.+ |

### A.3.10 Specialized Libraries

| Sr | Library | Java 17+ |
|----|---------|----------|
| 40 | core-bem | 4.0.+ |
| 41 | core-falcon | 3.0.+ |
| 42 | core-falcon-api | 1.0.+ |
| 43 | common-mastercard-logger | 2.0.+ |
| 44 | common-mastercard-decryptor | 2.0.+ |
| 45 | system-core-sdh | 2.0-000 |
| 46 | core-thread-cache | 2.0.+ |

---

## A.4 Common Libraries Migration Patterns

### Core Filter & Context

```gradle
// SDK2
implementation 'com.barclaycard.digital:common-filter:4.1.+'
implementation 'com.barclaycard.digital:common-context:1.3.+'
implementation 'com.barclaycard.digital:core-jsonapi-web:4.4.+'

// SDK3
implementation 'com.barclaycard.digital:common-filter:5.0.+'      // CRITICAL
implementation 'com.barclaycard.digital:common-context:2.0.+'
implementation 'com.barclaycard.digital:core-jsonapi-web:5.2-001'
```

### Tokenization

```gradle
// SDK2
implementation 'com.barclaycard.digital:domain-core-tokenization-protegrity:6.1.+'
implementation 'com.barclaycard.digital:domain-core-tokenization-uuid:5.0.+'

// SDK3
implementation 'com.barclaycard.digital:domain-core-tokenization-protegrity:8.2-002'
implementation 'com.barclaycard.digital:domain-core-tokenization-uuid:7.1-001'
```

### Triumph Messaging

```gradle
// SDK2
implementation 'com.barclaycard.digital:core-triumph:8.3.+'

// SDK3 - NOTE: Group ID changed!
implementation 'com.barclaycard.digital.core:core-triumph:9.1-000'
```

### Resilience (Hystrix → Resilience4j)

```gradle
// SDK2 - DEPRECATED
implementation 'com.barclaycard.digital:system-core-resilliency:3.0.+'

// SDK3 - Modern replacement
implementation 'com.barclaycard.digital:system-core-resilience4j:1.0.+'
```

### ODS Integration

```gradle
// SDK2
implementation 'com.barclaycard.digital:system-core-ods:5.3.+'

// SDK3
implementation 'com.barclaycard.digital:system-core-ods:6.1-001'
```

### Data Mapping

```gradle
// SDK2
implementation 'com.barclaycard.digital:core-mapping:1.0.+'

// SDK3
implementation 'com.barclaycard.digital:core-mapping:2.0.+'
```

### Encryption Gateway

```gradle
// SDK2
implementation 'com.barclaycard.digital:domain-core-agnostic-gateway:4.1.+'

// SDK3
implementation 'com.barclaycard.digital:domain-core-agnostic-gateway:5.1-000'
```

### Testing Utilities

```gradle
// SDK2
testImplementation 'com.barclaycard.digital:test-utilities:6.2.+'

// SDK3
testImplementation 'com.barclaycard.digital:test-utilities:8.0-000:tests'
```

---

# PART B: SYSTEM COMPONENTS

## Executive Summary

564 system component libraries used for core business logic, ODS integration, Triumph messaging, and domain-specific services.

**Key Metrics:**
- **Total System Components:** 564 libraries
- **Merged Status:** 450+ components (79.8%)
- **Categories:** ODS wrappers, system commands, system queries, domain libraries

> **Warning: AGENT NOTE - NOT EXHAUSTIVE:**
> This list contains **representative examples** (~120 common components). For artifacts NOT listed here:
> 1. Use **Nexus lookup** (see [Nexus Version Lookup Reference](nexus_version_lookup.md))
> 2. Use **wildcard version pattern** `X.0.+` (e.g., `5.0.+` for Java 17+ versions)
>
> **Version Pattern:** Most `com.barclaycard.digital` system libraries follow `X.0.+` pattern for Java 17+

---

## B.1 ODS Wrapper Components

45+ wrapper components for querying the Operational Data Store (ODS).

### B.1.1 Account & Billing Data Wrappers

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 1 | core-memo | 3.0.+ |
| 2 | core-memo-api | 1.0.+ |
| 3 | ods-wrapper-get-account-data | 4.0.+ |
| 4 | ods-wrapper-get-account-detail | 5.0.+ |
| 5 | ods-wrapper-get-minimum-payment-statement | 4.0.+ |

### B.1.2 Cardholder Details Wrappers

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 6 | ods-wrapper-get-cardholder-address-history-by-account | 2.0.+ |
| 7 | ods-wrapper-get-cardholder-address-history-by-cardholderid | 2.0.+ |
| 8 | ods-wrapper-get-cardholder-details | 2.0.+ |
| 9 | ods-wrapper-get-cardholder-details-by-account | 4.0.+ |
| 10 | ods-wrapper-get-cardholder-identifier-by-device | 3.0.+ |
| 11 | ods-wrapper-get-cardholders-pin-history-by-accountnumber | 2.0.+ |
| 12 | ods-wrapper-get-customer-long-name | 3.0.+ |
| 13 | ods-wrapper-get-primary-cardholder-detail | 2.0.+ |
| 14 | ods-wrapper-get-primary-cardholder-identifier | 4.0.+ |

### B.1.3 Credit & Financial Wrappers

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 15 | ods-wrapper-get-credit-limit-history | 3.0.+ |
| 16 | ods-wrapper-get-CVMScore-details | 2.0.+ |
| 17 | ods-wrapper-get-plastic-info-history | 3.0.+ |
| 18 | ods-wrapper-get-plastic-recent-history | 2.0.+ |

### B.1.4 PIN & Security Wrappers

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 19 | ods-wrapper-get-pin-details-product-info-by-accountnumber | 3.0.+ |
| 20 | ods-wrapper-get-pin-details-product-info-by-cardnumber | 3.0.+ |
| 21 | ods-wrapper-get-product-detail-information | 2.0.+ |
| 22 | ods-wrapper-get-rate-information | 2.0.+ |

### B.1.5 Other Wrappers

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 23 | ods-wrapper-get-experimentation-info | 3.0.+ |
| 24 | ods-wrapper-get-form-factors-details | 3.0.+ |
| 25 | ods-wrapper-get-link-account-details | 4.0.+ |
| 26 | ods-wrapper-get-status-parameter-table-details | 1.0.+ |

---

## B.2 System Command Components

150+ command components that execute business operations.

### B.2.1 Account & Status Management

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 1 | system-cmd-account-status | 4.0.+ |
| 2 | system-cmd-as2-customer | 4.0.+ |
| 3 | system-cmd-customer-address | 4.0.+ |
| 4 | system-cmd-customer-personal-details | 4.0.+ |
| 5 | system-cmd-email-address | 4.0.+ |
| 6 | system-cmd-kyc-status | 4.0.+ |
| 7 | system-cmd-lost-and-stolen | 5.0.+ |
| 8 | system-cmd-occupation | 4.0.+ |
| 9 | system-cmd-order-card | 5.0.+ |
| 10 | system-cmd-phonenumber | 4.0.+ |

### B.2.2 Payment & Direct Debit Management

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 11 | system-cmd-directdebit | 3.0-001 |
| 12 | system-cmd-payment-management | 5.0-001 |
| 13 | system-common-directdebit | 4.1-003 |
| 14 | system-common-payment | 3.1-000 |
| 15 | payment-management-common | 2.1-000 |

### B.2.3 PIN & Security Commands

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 16 | system-cmd-create-token | 4.0.+ |
| 17 | system-cmd-pinview | 4.0.+ |
| 18 | system-cmd-token-activation-request | 3.0.+ |
| 19 | system-cmd-update-current-token-status | 3.0.+ |
| 20 | system-cmd-validate-pin | 4.0.+ |

### B.2.4 Offer & Reward Management

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 21 | system-cmd-account-cashback-api | 4.0.+ |
| 22 | system-cmd-account-cashback-triumph | 4.0.+ |
| 23 | system-cmd-account-offers-api | 5.0.+ |
| 24 | system-cmd-account-offers-ods | 5.0.+ |
| 25 | system-cmd-account-promo-api | 4.0.+ |
| 26 | system-cmd-account-promo-triumph | 4.0.+ |
| 27 | system-cmd-cashback-optin-offers-api | 4.0.+ |
| 28 | system-cmd-cashback-redemption-rwd | 4.0-001 |
| 29 | system-cmd-decline-offer-api | 4.0.+ |
| 30 | system-cmd-decline-offer-triumph | 4.0.+ |
| 31 | system-cmd-offers-preferences | 5.0.+ |
| 32 | system-common-offers | 4.0.+ |
| 33 | common-hvt-core | 6.0.+ |

### B.2.5 Utility & Helper Commands

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 34 | system-bem-payment-pojo-util | 2.0.+ |
| 35 | system-bem-pinview-pojo-util | 4.0.+ |
| 36 | system-cmd-activity | 4.0.+ |
| 36 | system-cmd-activity-pv | 4.0.+ |
| 37 | system-cmd-activity-rwd | 4.0-000 |
| 38 | system-cmd-communication-preferences | 4.0-001 |
| 39 | system-cmd-dummy-auth-ujasath2 | 5.0-000 |
| 40 | system-cmd-offers-details-api | 4.0.+ |
| 41 | system-cmd-offers-details-triumph | 4.0.+ |
| 42 | system-cmd-ogone-payment | 5.0-000 |
| 43 | system-cmd-payment-security-access-log | 4.0-000 |
| 44 | system-cmd-product-transfer | 3.0.+ |
| 45 | core-address-utils | 4.0.+ |
| 46 | common-hash-utils | 2.0.+ |
| 47 | core-protegrity-encryption | 7.0.+ |
| 48 | domain-core-json-encryption | 4.0.+ |

### B.2.6 Account Balance & Transfer Commands

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 49 | system-cmd-account-move-balance | 2.0-001 |
| 50 | system-cmd-account-store-references | 2.0.+ |
| 51 | system-cmd-account-swap | 2.0.+ |

---

## B.3 System Query Components

200+ query components that retrieve business data.

### B.3.1 Core Account Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 1 | system-qry-account-affordability-api | 5.0.+ |
| 2 | system-qry-account-api | 4.0.+ |
| 3 | system-qry-account-details | 5.0-000 |
| 4 | system-qry-account-details-api | 7.3-000 |
| 5 | system-qry-account-offer-details-api | 6.0.+ |
| 6 | system-qry-account-runtime | 4.0.+ |
| 7 | system-qry-cardholder-account | 12.0.+ |
| 8 | system-qry-cardholder-account-runtime | 10.1-000 |

### B.3.2 Card & Cardholder Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 9 | system-qry-cardholder-account-api | 12.0.+ |
| 10 | system-qry-cardholder-details | 3.0.+ |
| 11 | system-qry-cardholder-name | 4.0.+ |
| 12 | system-qry-cardholder-relationships | 8.0.+ |
| 13 | system-qry-cardholder-status | 5.0-000 |
| 14 | system-qry-cardsec-account | 4.1-001 |

### B.3.3 Transaction & Fee Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 15 | system-qry-card-account-cross-reference | 4.0.+ |
| 16 | system-qry-customer-accounts | 3.0.+ |
| 17 | system-qry-pay-amount-percentage | 8.0.+ |
| 18 | system-qry-debitcard-management | 3.0.+ |
| 19 | system-qry-directdebit | 4.0.+ |
| 20 | system-qry-lifecycle | 4.0.+ |

### B.3.4 Balance & Credit Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 21 | system-qry-account-credit-details-api | 5.0.+ |
| 22 | system-qry-account-creditlimithistory | 4.0.+ |
| 23 | system-qry-account-finance-details-api | 5.0.+ |
| 24 | system-qry-account-markers | 4.0-000 |
| 25 | system-qry-indirect-balances-details | 5.0.+ |
| 26 | system-qry-instant-credit | 5.0.+ |

### B.3.5 Address & Customer Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 27 | system-qry-address-history | 6.0.+ |
| 28 | system-qry-customer-address | 4.0.+ |
| 29 | system-qry-customer-name | 4.0-000 |
| 30 | system-qry-email-address | 4.0.+ |

### B.3.6 Device & Mobile Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 31 | system-qry-device-history-api | 4.0.+ |
| 32 | system-qry-registered-mobile-devices | 4.0.+ |

### B.3.7 Statement & Billing Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 33 | system-qry-latest-statement-account-rwd | 5.0-000 |

### B.3.8 Offer & Reward Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 34 | system-qry-cashback-offers-api | 5.0.+ |
| 35 | system-qry-offer-details-api | 6.0.+ |
| 36 | system-qry-promo-offers-api | 5.0.+ |
| 37 | system-qry-reward-transactions-details | 5.0-000 |
| 38 | system-qry-bne-api | 1.0.+ |
| 39 | system-qry-offer-common-util-api | 2.0.+ |

### B.3.9 PIN & Security Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 40 | system-qry-pin-change-history | 5.0.+ |
| 41 | system-qry-pin-status | 4.0.+ |
| 42 | system-qry-pinview-as2db | 4.0.+ |
| 43 | system-qry-cvm-score-details | 4.0.+ |
| 44 | system-qry-cvv-validation | 4.0.+ |
| 45 | system-qry-cardsec-cvv | 4.0.+ |

### B.3.10 Token & Payment Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 46 | system-qry-mastercard-decrypt | 5.0-000 |
| 47 | system-qry-mastercard-token-activation-request | 3.0-000 |
| 48 | system-qry-token-details | 3.0-000 |
| 49 | system-qry-token-history | 3.0-000 |
| 50 | system-cmd-dummy-auth | 5.0.+ |
| 51 | system-qry-payment-configuration | 4.0-002 |
| 52 | system-qry-payment-management | 4.0-001 |

### B.3.11 Product & Reference Queries

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 53 | system-qry-card-name-code | 5.0.+ |
| 54 | system-qry-product-code-profile | 3.0.+ |
| 55 | system-qry-product-detail | 3.0.+ |
| 56 | system-qry-reference-data-api | 5.0.+ |
| 57 | system-qry-product-category-rwd | 4.0-000 |
| 58 | system-qry-static-data-hub | 5.1-001 |
| 59 | system-qry-validate-fulfilment-oms | 5.0-001 |

---

## B.4 Domain-Specific Libraries

### B.4.1 Core Infrastructure

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 1 | system-core-datasource | 7.0.+ |
| 2 | system-core-hystrix | 4.0.+ |
| 3 | system-core-types | 4.0.+ |

### B.4.2 Payment & Direct Debit Domain

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 4 | payment-common | TBD |
| 5 | system-cmd-payment-management | 5.0-001 |
| 6 | system-common-payment | 3.1-000 |
| 7 | system-qry-payment-configuration | 4.0-002 |
| 8 | system-qry-payment-management | 4.0-001 |
| 9 | payment-management-common | 2.1-000 |

### B.4.3 Card Security Domain

| Sr | Component | Java 17+ |
|----|-----------|----------|
| 10 | system-qry-cardsec-account | 4.1-001 |
| 11 | system-qry-cardsec-cvv | 4.0.+ |

---

## B.5 System Components Migration Patterns

### Payment Domain

```gradle
// SDK2
implementation 'com.barclays.api:system-cmd-payment-management:4.0.+'
implementation 'com.barclays.api:system-common-payment:2.0.+'

// SDK3
implementation 'com.barclays.api:system-cmd-payment-management:5.0-001'
implementation 'com.barclays.api:system-common-payment:3.1-000'
```

### Direct Debit Domain

```gradle
// SDK2
implementation 'com.barclays.api:system-cmd-directdebit:2.2.+'
implementation 'com.barclays.api:system-common-directdebit:3.0.+'

// SDK3
implementation 'com.barclays.api:system-cmd-directdebit:3.0-001'
implementation 'com.barclays.api:system-common-directdebit:4.1-003'
```

### Cardholder Account Queries

```gradle
// SDK2
implementation 'com.barclays.api:system-qry-cardholder-account:11.0.+'
implementation 'com.barclays.api:system-qry-cardholder-account-api:11.0.+'

// SDK3
implementation 'com.barclays.api:system-qry-cardholder-account:12.0.+'
implementation 'com.barclays.api:system-qry-cardholder-account-api:12.0.+'

// NEW in SDK3
implementation 'com.barclays.api:system-qry-cardholder-account-runtime:10.1-000'
```

### ODS Wrappers

```gradle
// SDK2
implementation 'com.barclays.api:ods-wrapper-get-account-data:3.0.+'
implementation 'com.barclays.api:ods-wrapper-get-cardholder-details:1.1.+'

// SDK3
implementation 'com.barclays.api:ods-wrapper-get-account-data:4.0.+'
implementation 'com.barclays.api:ods-wrapper-get-cardholder-details:2.0.+'
```

### PIN & Validation

```gradle
// SDK2
implementation 'com.barclays.api:system-cmd-validate-pin:3.0.+'
implementation 'com.barclays.api:system-qry-pin-status:3.0.+'

// SDK3
implementation 'com.barclays.api:system-cmd-validate-pin:4.0.+'
implementation 'com.barclays.api:system-qry-pin-status:4.0.+'
```

---

# PART C: QUICK REFERENCE

## C.1 Version Upgrade Quick Reference

### Common Platform Libraries

| Artifact | SDK2 | SDK3 | Priority |
|----------|------|------|----------|
| common-filter | 4.1.+ | 5.0.+ | **CRITICAL** |
| common-context | 1.3.+ | 2.0.+ | High |
| executor-core | 1.1.+ | 2.0.+ | High |
| core-jsonapi-web | 4.4.+ | 5.2-001 | High |
| domain-core-tokenization-protegrity | 6.1.+ | 8.2-002 | High |
| domain-core-tokenization-uuid | 5.0.+ | 7.1-001 | High |
| core-triumph | 8.3.+ | 9.1-000 | High |
| system-core-ods | 5.3.+ | 6.1-001 | High |
| core-mapping | 1.0.+ | 2.0.+ | Medium |
| domain-core-agnostic-gateway | 4.1.+ | 5.1-000 | Medium |
| test-utilities | 6.2.+ | 8.0-000:tests | Medium |
| system-core-resilience4j | N/A | 1.0.+ | NEW |
| securityFilter | 6.x | 7.0.0-RELEASE | **CRITICAL** |

### System Components

| Artifact | SDK2 | SDK3 | Priority |
|----------|------|------|----------|
| system-cmd-payment-management | 4.0.+ | 5.0-001 | High |
| system-common-payment | 2.0.+ | 3.1-000 | High |
| system-qry-cardholder-account | 11.0.+ | 12.0.+ | High |
| system-qry-cardholder-account-api | 11.0.+ | 12.0.+ | High |
| system-cmd-directdebit | 2.2.+ | 3.0-001 | Medium |
| system-common-directdebit | 3.0.+ | 4.1-003 | Medium |
| ods-wrapper-get-account-data | 3.0.+ | 4.0.+ | Medium |
| system-cmd-validate-pin | 3.0.+ | 4.0.+ | Medium |

---

## C.2 Critical Upgrades

### 1. common-filter:5.0.+ (MANDATORY)

**Why Critical:**
- 4.1.+ contains SDK2 bootstrap classes
- 5.0.+ uses SDK3 base libraries
- Will cause `ClassNotFoundException` if not upgraded

### 2. securityFilter:7.0.0-RELEASE (MANDATORY)

**Why Critical:**
- 6.x uses `javax.servlet.Filter`
- 7.0.0-RELEASE uses `jakarta.servlet.Filter`
- Will cause `ClassCastException` if not upgraded

### 3. core-triumph:9.1-000 (GROUP ID CHANGED)

**Important:**
```gradle
// SDK2
implementation 'com.barclaycard.digital:core-triumph:8.3.+'

// SDK3 - Group ID changed!
implementation 'com.barclaycard.digital.core:core-triumph:9.1-000'
```

### 4. system-core-resilience4j:1.0.+ (REPLACES HYSTRIX)

**Important:**
```gradle
// SDK2 - DEPRECATED
implementation 'com.barclaycard.digital:system-core-resilliency:3.0.+'

// SDK3 - Modern replacement
implementation 'com.barclaycard.digital:system-core-resilience4j:1.0.+'
```

---

## C.3 Troubleshooting

### Issue: NoClassDefFoundError for common-filter classes

**Solution:** Verify `common-filter:5.0.+` is on classpath (not 4.1.+)

Run `$GRADLE_CMD dependencies --configuration runtimeClasspath` and use the Grep tool to search the output for `common-filter`.

### Issue: ClassCastException for jakarta.servlet.Filter

**Solution:** Upgrade securityFilter to 7.0.0-RELEASE
```gradle
implementation 'com.barclays.security:securityFilter:7.0.0-RELEASE'
```

### Issue: Protegrity tokenization fails

**Solution:** Ensure `domain-core-tokenization-protegrity:8.2-002` is used

### Issue: UUID detokenization fails in request body

**Solution:** Add to `tokenization.properties`:
```properties
uuid.packageName=com.your.package.name
```

### Issue: Circuit breaker not working

**Solution:** Use `system-core-resilience4j:1.0.+` instead of deprecated Hystrix

### Issue: Triumph messaging fails

**Solution:** Update to new group ID:
```gradle
implementation 'com.barclaycard.digital.core:core-triumph:9.1-000'
```

---

# PART D: EMM DOMAIN LIBRARIES

## D.1 EMM Common Core Libraries

Enterprise Mobile Management (EMM) domain libraries with different groupId.

**GroupId:** `com.barclays.api.emm.common.core` (migrated from various SDK2 groupIds — see D.3)

| Sr | Library | Java 17+ |
|----|---------|----------|
| 1 | api-rps-transactions | **2.2.+** |
| 2 | api-mainframe-connector | **1.5.+** |
| 3 | api-referencedata-connector | **1.2.+** |
| 4 | api-bcag-connector | **1.2.+** |
| 5 | ldap-connector | **1.3.+** |
| 6 | api-core-cache | **2.1.+** |
| 7 | api-ukba-transactions | **2.2.+** |
| 8 | api-ssca-transactions | **1.1.+** |
| 9 | api-core-data | **1.1.+** |
| 10 | outbound-external-gateway | **2.1.+** |
| 11 | core-context | **2.2.+** |
| 12 | api-core-utility | **1.1.+** |
| 13 | api-als-transactions | **1.1.+** |
| 14 | api-core-error-handler | **1.5.+** |
| 15 | api-connector-data | **1.2.+** |
| 16 | api-tiaaas-connector | **2.1.+** |

**GroupId:** `com.barclays.api.emm.common.utility`

| Sr | Library | Java 17+ |
|----|---------|----------|
| 16 | lending-api-utils | **1.1.+** |

### EMM Migration Pattern

```gradle
// SDK2 (OLD groupId: com.barclays.iapi.core)
implementation 'com.barclays.iapi.core:api-ukba-transactions:2.0.+'

// SDK3 (NEW groupId: com.barclays.api.emm.common.core)
implementation 'com.barclays.api.emm.common.core:api-ukba-transactions:2.2.+'
```

For the full SDK2→SDK3 groupId mapping, see [barclays_internal_libraries_capl.md](barclays_internal_libraries_capl.md).

---

## D.2 BAP BLD Libraries

Additional BAP BLD libraries for logging and REST API support.

| Sr | Library | GroupId | Version |
|----|---------|---------|---------|
| 1 | bap-bld-lib-logging | com.barclays.api | 1.3.+ |
| 2 | bap-bld-lib-restapi | com.barclays.api | 1.4.+ |
| 3 | bap-bld-lib-payload | com.barclays.api | BOM managed |
| 4 | bap-bld-lib-restclient | com.barclays.api | BOM managed |
| 5 | bap-bld-lib-health | com.barclays.api | BOM managed |
| 6 | bap-bld-lib-common | com.barclays.api | BOM managed |

### BAP BLD Migration Pattern

```gradle
// SDK2 (OLD)
implementation 'com.barclays.api:api-core-logging:2.1.+'

// SDK3 (NEW - artifact name changed!)
implementation 'com.barclays.api:bap-bld-lib-logging:1.3.+'
```

**Important:** The artifact name changed from `api-core-logging` to `bap-bld-lib-logging`.

### Java Import Changes

```java
// SDK2 (OLD)
import com.barclays.api.core.logging.LogFactory;
import com.barclays.api.core.logging.Logger;

// SDK3 (NEW)
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
```

---

## D.3 GroupId Migration Reference

### Complete GroupId Mappings (Barclays Internal Only)

> **AGENT INSTRUCTION -- Identifying Legacy GroupIds:**
> For dependencies listed in this table, apply the documented old->new groupId mapping directly.
> For any `com.barclays.*` or `com.barclaycard.*` dependency **not** listed in this table, search Nexus by `artifactId` -- if Nexus returns the same artifact under multiple groupIds, prefer the variant with `emm` in the groupId (see `emm` groupId preference note at the top of this file).

| Old GroupId | New GroupId | Artifacts |
|-------------|-------------|-----------|
| `com.barclays.iapi.core` | `com.barclays.api.emm.common.core` | api-rps-transactions, api-mainframe-connector, api-referencedata-connector, api-bcag-connector, ldap-connector, api-core-cache, api-ukba-transactions, api-ssca-transactions, api-core-data |
| `com.barclaycard.bpf.process` | `com.barclays.api.emm.common.core` | outbound-external-gateway, core-context, api-core-error-handler |
| `com.barclays.iapi.lending` | `com.barclays.api.emm.common.utility` | lending-api-utils |
| `com.barclays.iapi.loans` | `com.barclays.api.emm.common.core` | api-als-transactions |
| `com.barclays.common.api` | `com.barclays.api.emm.common.core` | api-core-utility |
| `com.barclays.api` (api-core-logging) | `com.barclays.api` (bap-bld-lib-logging) | Artifact name changed |
| `com.barclaycard.digital` | `com.barclaycard.digital.core` | core-triumph (only) |

### Validation Commands

Use the Grep tool (or `search_in_files_by_text` MCP tool) for these validations. See CLAUDE.md for tool guidance.

- **Check for old EMM group IDs:** Grep for `com.barclays.iapi.core` in `build.gradle` -- Expected: No matches (all should be `com.barclays.api.emm.common.core`)
- **Check for old BPF process group IDs:** Grep for `com.barclaycard.bpf.process` in `build.gradle` -- Expected: No matches (all should be `com.barclays.api.emm.common.core`)
- **Check for old lending/common group IDs:** Grep for `com.barclays.iapi.lending` and `com.barclays.common.api` in `build.gradle` -- Expected: No matches (migrated to `com.barclays.api.emm.common.*`)
- **Check for old logging dependency:** Grep for `api-core-logging` in `build.gradle` -- Expected: No matches (should be `bap-bld-lib-logging`)
- **Check for old SDK2 dependencies:** Grep for `api-core-boot|api-core-utils|api-core-properties|api-mesh-client-connector` in `build.gradle` -- Expected: No matches (all should be replaced with SDK3 equivalents)

---

**Document Version:** 1.4
**Last Updated:** 2026-03-03
**Total Libraries:** 870+ (39 common platform + 564 system components + EMM domain + IBM MQ + BAP BLD + 222 JDK21 tracker additions)
**Document Type:** Agent-Optimized SDK3 Reference Specification

---

# PART E: JDK21 TRACKER ADDITIONS

> **Source:** JDK Migration Tracker.xlsx (System Jars sheet)
> **GroupId:** `com.barclaycard.digital` for E.1–E.4, `com.barclaycard.bpf.process` for E.5
> **Note:** These entries have JDK21 versions confirmed from the tracker.

---

## E.1 ODS Wrapper Components (JDK21)

**GroupId:** `com.barclaycard.digital`

| Sr | Component | Java 17+ |
|----|-----------|---------|
| 1 | ods-wrapper-get-disputes-details | 2.0-000 |

## E.2 System Command Components (JDK21)

**GroupId:** `com.barclaycard.digital`

| Sr | Component | Java 17+ |
|----|-----------|---------|
| 1 | system-cmd-account-move-balance-api | 1.0.+ |
| 2 | system-cmd-account-status-api | 1.1-000 |
| 3 | system-cmd-account-store-references-api | 1.0.+ |
| 4 | system-cmd-account-swap-api | 1.0.+ |
| 5 | system-cmd-activity-api | 1.0.+ |
| 6 | system-cmd-activity-dd | 4.0-000 |
| 7 | system-cmd-activity-pv-api | 1.0.+ |
| 8 | system-cmd-activity-rwd-api | 1.0-000 |
| 9 | system-cmd-as2-customer-api | 1.0.+ |
| 10 | system-cmd-authorised-user | 4.0.+ |
| 11 | system-cmd-authorised-user-api | 1.0.+ |
| 12 | system-cmd-bt-mt-details | 4.0-000 |
| 13 | system-cmd-cashback-optin-offers-triumph | 4.0.+ |
| 14 | system-cmd-cashback-redemption-rwd-api | 1.0-001 |
| 15 | system-cmd-copy-statement-api | 2.0-000 |
| 16 | system-cmd-copy-statement-triumph | 2.0-000 |
| 17 | system-cmd-create-token-api | 3.0.+ |
| 18 | system-cmd-customer-address-api | 1.0.+ |
| 19 | system-cmd-customer-personal-details-api | 1.0.+ |
| 20 | system-cmd-dummy-auth-api | 1.0.+ |
| 21 | system-cmd-email-address-api | 1.0.+ |
| 22 | system-cmd-kyc-status-api | 1.0.+ |
| 23 | system-cmd-lost-and-stolen-api | 1.0.+ |
| 24 | system-cmd-memorandum-api | 1.1-000 |
| 25 | system-cmd-nmon-event | 4.0.+ |
| 26 | system-cmd-nmon-event-api | 4.0.1-000 |
| 27 | system-cmd-occupation-api | 1.0.+ |
| 28 | system-cmd-order-card-api | 1.0.+ |
| 29 | system-cmd-phonenumber-api | 1.0.+ |
| 30 | system-cmd-product-transfer-api | 3.0.+ |
| 31 | system-cmd-rate-optin-offers-api | 3.0.+ |
| 32 | system-cmd-rate-optin-offers-triumph | 4.0.+ |
| 33 | system-cmd-token-activation-request-api | 3.0.+ |
| 34 | system-cmd-token-status-update | 2.2-000 |
| 35 | system-cmd-token-status-update-api | 1.0-000 |
| 36 | system-cmd-unlock-pin-api | 1.0.+ |
| 37 | system-cmd-update-current-token-status-api | 1.0-000 |
| 38 | system-cmd-update-letter-preferences | 2.0-000 |
| 39 | system-cmd-validate-pin-api | 1.0.+ |
| 40 | system-common-payment-api | 1.0-000 |

## E.3 System Query Components (JDK21)

**GroupId:** `com.barclaycard.digital`

| Sr | Component | Java 17+ |
|----|-----------|---------|
| 1 | system-qry-account-affordability-exp | 5.0.+ |
| 2 | system-qry-account-affordability-ods | 5.0.+ |
| 3 | system-qry-account-benefit-details | 4.0.+ |
| 4 | system-qry-account-credit-details-ods | 6.0.+ |
| 5 | system-qry-account-credit-details-runtime | 6.0.+ |
| 6 | system-qry-account-credit-details-triumph | 6.0.+ |
| 7 | system-qry-account-creditlimithistory-api | 5.0.+ |
| 8 | system-qry-account-details-ods | 7.0.+ |
| 9 | system-qry-account-details-runtime | 7.0.+ |
| 10 | system-qry-account-details-triumph | 7.0.+ |
| 11 | system-qry-account-finance-details-ods | 5.0.+ |
| 12 | system-qry-account-finance-details-runtime | 5.0.+ |
| 13 | system-qry-account-finance-details-triumph | 5.0.+ |
| 14 | system-qry-account-markers-api | 3.0-000 |
| 15 | system-qry-account-membership-fees | 2.0-000 |
| 16 | system-qry-account-membership-fees-api | 2.0-000 |
| 17 | system-qry-account-ods | 4.0.+ |
| 18 | system-qry-account-offer-details-ods | 6.0.+ |
| 19 | system-qry-account-offer-details-runtime | 6.0.+ |
| 20 | system-qry-account-relationships | 4.0.+ |
| 21 | system-qry-account-relationships-api | 6.0.+ |
| 22 | system-qry-account-relationships-ods | 5.0.+ |
| 23 | system-qry-account-relationships-runtime | 6.0.+ |
| 24 | system-qry-account-selfservice-eligibility | 4.0.+ |
| 25 | system-qry-account-selfservice-eligibility-api | 5.0.+ |
| 26 | system-qry-account-status | 8.0.+ |
| 27 | system-qry-account-status-api | 7.0.+ |
| 28 | system-qry-account-status-ods | 7.0.+ |
| 29 | system-qry-account-status-runtime | 7.0.+ |
| 30 | system-qry-account-transaction-fees-api | 2.0-000 |
| 31 | system-qry-account-triumph | 4.0.+ |
| 32 | system-qry-address-history-api | 7.0.+ |
| 33 | system-qry-address-history-ods | 7.0.+ |
| 34 | system-qry-address-history-runtime | 7.0.+ |
| 35 | system-qry-alert-preference | 4.0-000 |
| 36 | system-qry-bankvalidator | 4.0-000 |
| 37 | system-qry-bne | 5.0.+ |
| 38 | system-qry-bt-mt-details | 5.0-000 |
| 39 | system-qry-card-account-cross-reference-api | 4.0.+ |
| 40 | system-qry-card-holder-plastic-history | 3.0.+ |
| 41 | system-qry-card-holder-plastic-history-api | 5.0.+ |
| 42 | system-qry-card-name-code-api | 3.0.+ |
| 43 | system-qry-card-nickname-as2db | 5.0.+ |
| 44 | system-qry-card-nickname-as2db-api | 1.0.+ |
| 45 | system-qry-cardholder-account-activation-api | 4.0-000 |
| 46 | system-qry-cardholder-account-activation-triumph | 4.0-002 |
| 47 | system-qry-cardholder-account-details-rwd | 4.0-000 |
| 48 | system-qry-cardholder-account-details-rwd-api | 1.0-000 |
| 49 | system-qry-cardholder-account-ods | 10.0.+ |
| 50 | system-qry-cardholder-details-api | 1.0.+ |
| 51 | system-qry-cardholder-details-capis | 5.0.+ |
| 52 | system-qry-cardholder-details-dd | 3.0-000 |
| 53 | system-qry-cardholder-name-api | 4.0.+ |
| 54 | system-qry-cardholder-relationships-api | 7.0.+ |
| 55 | system-qry-cardholder-relationships-cmd | 4.0.+ |
| 56 | system-qry-cardholder-relationships-cmd-api | 1.0.+ |
| 57 | system-qry-cardholder-status-api | 3.1.+ |
| 58 | system-qry-cardholder-status-ods | 4.1.+ |
| 59 | system-qry-cardholder-status-runtime | 4.0.+ |
| 60 | system-qry-cardsec-account-api | 1.0.+ |
| 61 | system-qry-cashback-offers-ods | 5.0.+ |
| 62 | system-qry-cashback-offers-triumph | 5.0.+ |
| 63 | system-qry-credit-info | 7.0-000 |
| 64 | system-qry-credit-limit-info | 4.0.1-001 |
| 65 | system-qry-customer-accounts-api | 3.0.+ |
| 66 | system-qry-customer-address-api | 6.1-000 |
| 67 | system-qry-customer-address-exp | 6.0.+ |
| 68 | system-qry-customer-address-ods | 6.0.+ |
| 69 | system-qry-customer-address-pm | 3.0-001 |
| 70 | system-qry-customer-address-runtime | 6.0.+ |
| 71 | system-qry-cvm-score-details-api | 4.0.+ |
| 72 | system-qry-cvm-score-details-ods | 4.0.+ |
| 73 | system-qry-cvm-score-details-runtime | 4.0.+ |
| 74 | system-qry-cvv-validation-api | 1.0.+ |
| 75 | system-qry-device-history-exp | 5.0.+ |
| 76 | system-qry-device-history-ods | 4.0.+ |
| 77 | system-qry-device-history-runtime | 4.0.+ |
| 78 | system-qry-disputes-details | 2.0-000 |
| 79 | system-qry-disputes-details-api | 2.0-000 |
| 80 | system-qry-disputes-details-ods | 2.0-000 |
| 81 | system-qry-disputes-details-runtime | 2.0-001 |
| 82 | system-qry-email-address-api | 4.0.+ |
| 83 | system-qry-flag-details | 4.0.+ |
| 84 | system-qry-flag-details-api | 5.0.+ |
| 85 | system-qry-indirect-balances-details-rwd-api | 1.0-000 |
| 86 | system-qry-instant-credit-api | 5.0.+ |
| 87 | system-qry-journal-details | 4.0.+ |
| 88 | system-qry-journal-details-api | 1.0.+ |
| 89 | system-qry-kyc-status | 4.0.+ |
| 90 | system-qry-kyc-status-api | 1.0.+ |
| 91 | system-qry-latest-statement-account-rwd-api | 1.0-000 |
| 92 | system-qry-letter-preferences | 4.0-000 |
| 93 | system-qry-mastercard-decrypt-api | 1.0-001 |
| 94 | system-qry-mastercard-token-activation-request-api | 1.0-000 |
| 95 | system-qry-mastercard-validate-card | 3.0-000 |
| 96 | system-qry-offer-details-ods | 6.0.+ |
| 97 | system-qry-offer-details-runtime | 6.0.+ |
| 98 | system-qry-offer-elig-check-api | 2.0.4-000 |
| 99 | system-qry-offer-enterprise-api | 3.1-000 |
| 100 | system-qry-offer-mgmt-ods-api | 2.0.3-000 |
| 101 | system-qry-offline-passcode-status | 4.0.+ |
| 102 | system-qry-offline-passcode-status-api | 4.0.+ |
| 103 | system-qry-pay-amount-percentage-api | 6.0.+ |
| 104 | system-qry-pay-amount-percentage-ods | 6.0.+ |
| 105 | system-qry-pay-amount-percentage-runtime | 5.0.+ |
| 106 | system-qry-payment-status-api | 4.0.+ |
| 107 | system-qry-payment-status-ods | 3.0.+ |
| 108 | system-qry-pcli-account-details-crm | 7.0.+ |
| 109 | system-qry-pin-change-history-api | 4.0.+ |
| 110 | system-qry-pin-change-history-ods | 4.0.+ |
| 111 | system-qry-pin-change-history-runtime | 4.0.+ |
| 112 | system-qry-pin-history | 6.0.+ |
| 113 | system-qry-pin-history-api | 5.0.+ |
| 114 | system-qry-pin-history-ods | 6.0.+ |
| 115 | system-qry-pin-history-runtime | 5.0.+ |
| 116 | system-qry-pin-status-api | 1.0.+ |
| 117 | system-qry-pinview-as2db-api | 1.0.+ |
| 118 | system-qry-product-category-bav | 5.0-000 |
| 119 | system-qry-product-category-rwd-api | 1.0-000 |
| 120 | system-qry-product-code-profile-api | 3.0.+ |
| 121 | system-qry-product-detail-api | 3.0.+ |
| 122 | system-qry-product-detail-ods | 3.0.+ |
| 123 | system-qry-product-detail-runtime | 2.0.+ |
| 124 | system-qry-product-transfer-tags | 3.0.+ |
| 125 | system-qry-product-transfer-tags-api | 3.0.+ |
| 126 | system-qry-product-transfer-types | 3.0.+ |
| 127 | system-qry-product-transfer-types-api | 3.0.+ |
| 128 | system-qry-promo-offers-ods | 5.0.+ |
| 129 | system-qry-promo-offers-runtime | 5.0.+ |
| 130 | system-qry-promo-offers-triumph | 5.0.+ |
| 131 | system-qry-rate-information | 3.0.+ |
| 132 | system-qry-rate-information-api | 3.0.+ |
| 133 | system-qry-rate-information-ods | 3.0.+ |
| 134 | system-qry-rate-information-runtime | 2.0-000 |
| 135 | system-qry-reference-data-ods | 5.0.+ |
| 136 | system-qry-reference-data-runtime | 5.0.+ |
| 137 | system-qry-registered-mobile-devices-api | 1.0.+ |
| 138 | system-qry-reward-transactions-details-api | 2.0-001 |
| 139 | system-qry-reward-transactions-details-ods | 2.0-000 |
| 140 | system-qry-reward-transactions-details-runtime | 2.0-000 |
| 141 | system-qry-statement-benefit-details-bav | 5.0-000 |
| 142 | system-qry-statement-date-transaction-details | 2.0-001 |
| 143 | system-qry-statement-date-transaction-details-api | 2.0-000 |
| 144 | system-qry-statement-date-transaction-details-ods | 2.0-000 |
| 145 | system-qry-statement-date-transaction-details-runtime | 2.0-000 |
| 146 | system-qry-statement-reward-details-rwd-api | 1.0-000 |
| 147 | system-qry-token-activation-request | 3.0-002 |
| 148 | system-qry-token-activation-request-api | 1.0-000 |
| 149 | system-qry-token-details-api | 1.0-000 |
| 150 | system-qry-token-history-api | 1.0-000 |
| 151 | system-qry-visa-rewards-encryption | 1.1-000 |
| 152 | system-qry-visa-rewards-encryption-api | 1.1-000 |
| 153 | system-query-account-summary-api | 4.0.+ |
| 154 | system-query-account-summary-exp | 4.0.+ |
| 155 | system-query-annual-statement-dates-api | 2.0-000 |
| 156 | system-query-annual-statement-dates-ods | 2.0-000 |
| 157 | system-query-annual-statement-dates-runtime | 2.0-000 |
| 158 | system-query-annual-statement-dates-triumph | 2.0-000 |
| 159 | system-query-billing-account-status-api | 4.0-001 |
| 160 | system-query-billing-account-status-exp | 4.0-000 |
| 161 | system-query-billing-account-status-ods | 4.0-000 |
| 162 | system-query-billing-account-status-runtime | 4.0-000 |
| 163 | system-query-cardholder-relationships-api | 5.0.+ |
| 164 | system-query-cardholder-relationships-exp | 5.0.+ |
| 165 | system-query-cardholder-relationships-ods | 5.0.+ |
| 166 | system-query-cardholder-relationships-runtime | 5.0.+ |
| 167 | system-query-loan-promo-balance-details-runtime | 2.0-000 |
| 168 | system-query-loan-promo-balance-details-triumph | 2.0-000 |
| 169 | system-query-offers-preferences | 4.0.+ |
| 170 | system-query-online-date | 3.0.+ |
| 171 | system-query-statement-availabledates-noas2db-runtime | 2.0-000 |

## E.5 BPF Process Components (JDK21)

**GroupId:** `com.barclaycard.bpf.process`
> **Note:** No groupId change required for these artifacts — same groupId in SDK2 and SDK3.

| Sr | Component | Java 17+ |
|----|-----------|---------|
| 1 | core-ods | 2.1.0-000 |
| 2 | core-soap | 2.0.0-000 |
| 3 | core-tiaa-authorization | 1.2.1-000 |
| 4 | system-api-centrac | 1.1-001 |
| 5 | system-api-dm | 2.1-002 |
| 6 | system-customer-enquiry-ods | 2.1.0-000 |
| 7 | system-ngcb-service | 2.4-002 |
| 8 | system-post-transaction | 3.0-000 |
| 9 | system-smartpay | 2.7-003 |
| 10 | system-transaction-db | 2.4-006 |

---

**Document Version:** Updated with JDK21 Tracker data
**Last Updated:** 2026-03-03
**New Entries:** 222 (212 com.barclaycard.digital + 10 com.barclaycard.bpf.process)
