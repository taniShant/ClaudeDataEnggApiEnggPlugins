# Barclays Internal Libraries — CAPL Group Migration Rules

> CAPL-specific dependency migration rules (EMM groupId changes).

---

## CAPL Dependencies That MUST BE MODIFIED

These dependencies exist in SDK2 but require **groupId/artifactId/version changes** for SDK3:

### EMM Core Libraries (GroupId Migration)

> **Note:** These are Barclays internal libraries migrating to `com.barclays.api.emm.common.core` or `com.barclays.api.emm.common.utility`. Source groupIds include: `com.barclays.iapi.core`, `com.barclaycard.bpf.process`, `com.barclays.iapi.lending`, `com.barclays.common.api`, `com.barclays.iapi.loans`

| SDK2 Dependency | SDK3 Dependency | Version |
|-----------------|-----------------|---------|
| `com.barclays.iapi.core:api-rps-transactions` | `com.barclays.api.emm.common.core:api-rps-transactions` | `2.2.001` |
| `com.barclays.iapi.core:api-mainframe-connector` | `com.barclays.api.emm.common.core:api-mainframe-connector` | `1.5.004` |
| `com.barclays.iapi.core:api-referencedata-connector` | `com.barclays.api.emm.common.core:api-referencedata-connector` | `1.2.010` |
| `com.barclays.iapi.core:api-bcag-connector` | `com.barclays.api.emm.common.core:api-bcag-connector` | `1.2.013` |
| `com.barclays.iapi.core:ldap-connector` | `com.barclays.api.emm.common.core:ldap-connector` | `1.3.001` |
| `com.barclays.iapi.core:api-core-cache` | `com.barclays.api.emm.common.core:api-core-cache` | `2.1.005` |
| `com.barclays.iapi.core:api-ukba-transactions` | `com.barclays.api.emm.common.core:api-ukba-transactions` | `2.2.003` |
| `com.barclays.iapi.core:api-ssca-transactions` | `com.barclays.api.emm.common.core:api-ssca-transactions` | `1.1.002` |
| `com.barclays.iapi.core:api-core-data` | `com.barclays.api.emm.common.core:api-core-data` | `1.1.003` |
| `com.barclaycard.bpf.process:outbound-external-gateway` | `com.barclays.api.emm.common.core:outbound-external-gateway` | `2.1.001` |
| `com.barclaycard.bpf.process:core-context` | `com.barclays.api.emm.common.core:core-context` | `2.2.001` |
| `com.barclays.iapi.lending:lending-api-utils` | `com.barclays.api.emm.common.utility:lending-api-utils` | `1.1.028` |
| `com.barclays.common.api:api-core-utility` | `com.barclays.api.emm.common.core:api-core-utility` | `1.1.002` |
| `com.barclays.iapi.loans:api-als-transactions` | `com.barclays.api.emm.common.core:api-als-transactions` | `1.1.001` |
| `com.barclaycard.bpf.process:api-core-error-handler` | `com.barclays.api.emm.common.core:api-core-error-handler` | `1.5.001` |
| `com.barclays.api.emm.common.core:api-connector-data` | `com.barclays.api.emm.common.core:api-connector-data` | `1.2.001` |

**Agent Action:**
```gradle
// BEFORE (SDK2)
implementation 'com.barclays.iapi.core:api-ukba-transactions:1.0.0'

// AFTER (SDK3) - MODIFY groupId and version
implementation 'com.barclays.api.emm.common.core:api-ukba-transactions:2.2.003'
```

---

## Agent Workflow for CAPL Group

When processing CAPL project dependencies:

1. **REMOVE** obsolete SDK2 dependencies per `sdk2_to_sdk3_migration_specification.md` Section 3.3
2. **MODIFY** CAPL-specific dependencies from the table above (groupId/artifactId/version changes)
3. **VERIFY** new version in Nexus before modifying
4. **NEVER** duplicate dependencies — always replace existing entries

---

**Document Version:** 2.1
**Last Updated:** 2026-03-03
**Group:** capl
