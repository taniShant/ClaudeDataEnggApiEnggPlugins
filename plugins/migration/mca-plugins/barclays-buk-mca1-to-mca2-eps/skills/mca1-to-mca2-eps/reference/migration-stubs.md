# MCA1 Migration Stubs Catalog (Behavior-Preservation Strategy ONLY)

> **WARNING: This file applies ONLY to the behavior-preservation strategy.**
> **The aggressive strategy (used by `mca1-to-mca2-eps-agent`) does NOT use stubs.**
> **If you are running the aggressive migration, IGNORE this entire file.**
> **Replace every MCA1 type with its MCA2 equivalent directly — do NOT create stub classes.**

## Purpose

When MCA1 libraries (`scp-eps-libs-customer`, `scp-eps-core-comm`) are removed during migration,
preserved business logic that references their types will fail to compile. **Stubs** are minimal
local POJO replacements that preserve the API surface used by business logic, allowing it to
compile and run under MCA2 without modification.

Under behavior-preservation strategy, stubs are **expected and acceptable**. They are not a sign
of incomplete migration — they are a deliberate bridge that lets preserved business logic compile
while the framework is replaced around it.

---

## Stub Rules

1. Every stub MUST include a `@MCA2-STUB` header comment with the original FQN
2. Every stub MUST implement `java.io.Serializable` if the original was serializable
3. Every stub MUST include only the fields/methods actually used by the consuming app
4. Stubs go in `<project-package>/migration/stubs/` package
5. Stubs use the MCA2 package prefix: `com.barclays.mca.eps.<project>.migration.stubs`

---

## Complete Stub Inventory

### Stubs from Pilot 1 (scp-eps-audit, 8 stubs)

| Stub Class | Original FQN | Purpose | Fields/Methods |
|---|---|---|---|
| `UserBean` | `com.barclays.scp.eps.common.beans.UserBean` | User context — populated via IOLContextAdapter | `userId`, `userName`, `staffNumber`, `branchCode`, `groupId`, `locale`, `channel` (inner `ChannelBean`) |
| `CodedValueBean` | `com.barclays.scp.eps.common.beans.CodedValueBean` | Reference data key-value | `code`, `decode` |
| `CodeDecodeBean` | `com.barclays.scp.eps.common.beans.CodeDecodeBean` | Reference data key-value | `code`, `decode` |
| `DataInterface` | `com.barclays.scp.eps.common.utils.DataInterface` | Reference data lookup | `getCodeDecodeBeans(key)`, `getCodedValueBeans(key, params)` |
| `ReferenceDataHelper` | `com.barclays.scp.eps.common.utils.ReferenceDataHelper` | Reference data decode lookup | `getDecodeValue(code, decoderClass)` |
| `ReferenceData` | `com.barclays.scp.eps.common.utils.ReferenceData` | Reference data access | `getDecoder()` |
| `RestConnectorRequestBean` | `com.barclays.scp.eps.common.restconnector.beans.RestConnectorRequestBean` | REST request container | `service`, `data`, `headers`, `params`, `requestType`, `responseClass` |
| `RestConnectorResponseBean` | `com.barclays.scp.eps.common.restconnector.beans.RestConnectorResponseBean` | REST response container | `response`, `status` |

### Additional Stubs from Pilot 2 (scp-eps-bal-and-enq, 11 new)

| Stub Class | Original FQN | Purpose | Fields/Methods |
|---|---|---|---|
| `CustomerBean` | `com.barclays.scp.eps.common.beans.CustomerBean` | Customer context — populated via IOLContextAdapter | `customerId`, `customerClass`, `customerName` |
| `AccountBean` | `com.barclays.scp.eps.common.beans.AccountBean` | Account context — populated via IOLContextAdapter | `sortCode`, `accountNumber`, `productType` (CodeDecodeBean) |
| `AccountKeyBean` | `com.barclays.scp.eps.common.beans.AccountKeyBean` | Account identifier | `sortCode`, `accountNumber` |
| `ConfigContextBean` | `com.barclays.scp.eps.common.beans.ConfigContextBean` | Configuration context | `configContextAttributes` (Map) |
| `SecureContextBean` | `com.barclays.scp.eps.common.beans.SecureContextBean` | Secure context | `secureContextAttributes` (Map) |
| `EpsResponseBean` | `com.barclays.scp.eps.common.beans.EpsResponseBean` | MCA1 response base class | `messages` (List&lt;EpsMessageBean&gt;), `addMessage()` |
| `EpsMessageBean` | `com.barclays.scp.eps.common.beans.EpsMessageBean` | Error/warning/info message | `code`, `text`, `type` |
| `EpsApplicationException` | `com.barclays.scp.eps.common.exceptionhandling.exceptions.EpsApplicationException` | MCA1 exception with error DTOs list | `errorDtosList` (List&lt;EpsMessageBean&gt;), constructors |
| `MessageBeanHelper` | `com.barclays.scp.eps.common.exceptionhandling.utils.MessageBeanHelper` | Error message builder | `addErrorMessageToList()`, `addWarningMessageToList()`, `addInformationMessageToList()` |
| `EpsSeverityType` | `com.barclays.scp.eps.common.constants.EpsSeverityType` | Severity enum | `ERROR`, `WARNING`, `INFORMATION` with `getCode()` |
| `IOLContextAdapter` | (new — no MCA1 original) | Bridges IOLSchema to stub beans | `extractUserBean()`, `extractCustomerBean()`, `extractAccountBean()`, `extractConfigContextBean()`, `extractSecureContextBean()` |

### Domain-Specific Stubs (project-specific, create as needed)

These stubs are project-specific — not every project will need them. Create them following the
same pattern as framework stubs (POJO with `@MCA2-STUB` header, only used fields, `Serializable`).

| Stub Class | Purpose | Fields/Methods | Create When |
|---|---|---|---|
| `AccountStatusBean` | Account status lookup | `statusCode`, `statusDescription` | Business logic checks account status codes |
| `AccountKeyBean` | Account identifier pair | `sortCode`, `accountNumber` | Business logic references account key composites |
| `AccountsForServiceIdRequestBean` | Service ID request | `serviceId`, `accountType` | Business logic builds service-ID-based lookups |
| `AccountsForServiceIdResponseBean` | Service ID response | `accounts` (List) | Business logic processes service ID results |
| `AuditConstants` | Audit string constants | `SERVICE_START`, `ERROR_API`, etc. | Migrate from MCA1 constants class; convert to MCA2 constants |
| `AuditRequestBean` | Audit request wrapper | `auditAction`, `auditData` | Business logic constructs audit requests |

**Template:** Use the same pattern as Category 2 (Reference Data Beans) — simple Serializable POJO
with `@MCA2-STUB` header, fields, and getters/setters. No special behavior.

---

## IOLContextAdapter Pattern

The `IOLContextAdapter` is the key bridge between MCA2's `IOLSchema` and preserved business logic
that expects MCA1 bean types. It is **not a stub of an existing MCA1 class** — it is new code
created during migration.

### When to Use IOLContextAdapter

Use when preserved business logic:
- Reads fields from `UserBean` (userId, channel, staffNumber, branchCode, etc.)
- Reads fields from `CustomerBean` (customerId, customerClass)
- Reads fields from `AccountBean` (sortCode, accountNumber)
- Reads fields from `ConfigContextBean` or `SecureContextBean`

### When NOT to Use IOLContextAdapter

Do not use when:
- Writing new MCA2 code — use `IOLSchema` directly
- The logic only needs correlation ID — use `contextProvider.getCorrelationId()`
- The logic only needs a single field — access `iolContext.getUserContext()` directly

### Template

```java
/*
 * @MCA2-STUB: Bridges MCA2 IOLSchema to MCA1 stub beans.
 * Replaces: EpsServiceHelper.getUserBean(request), etc.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import com.barclays.global.mca.libs.context.data.IOLSchema;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.*;

public final class IOLContextAdapter {
    private static final Logger LOG = LoggerFactory.getLogger(IOLContextAdapter.class);
    private IOLContextAdapter() {}

    public static UserBean extractUserBean(IOLSchema iolContext) {
        UserBean userBean = new UserBean();
        if (iolContext == null || iolContext.getUserContext() == null) {
            LOG.warn("IOLSchema or UserContext is null; returning empty UserBean");
            return userBean;
        }
        Object userCtx = iolContext.getUserContext();
        if (userCtx instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) userCtx;
            userBean.setUserId(safeString(map.get("userId")));
            userBean.setUserName(safeString(map.get("userName")));
            userBean.setStaffNumber(safeString(map.get("staffNumber")));
            userBean.setBranchCode(safeString(map.get("branchCode")));
            userBean.setGroupId(safeString(map.get("groupId")));
            userBean.setLocale(safeString(map.get("locale")));
            // Channel sub-object
            UserBean.ChannelBean channelBean = new UserBean.ChannelBean();
            Object channelObj = map.get("channel");
            if (channelObj instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> cMap = (Map<String, Object>) channelObj;
                channelBean.setId(safeInt(cMap.get("id")));
                channelBean.setCode(safeString(cMap.get("code")));
                channelBean.setDecode(safeString(cMap.get("decode")));
            }
            userBean.setChannel(channelBean);
        }
        return userBean;
    }

    public static CustomerBean extractCustomerBean(IOLSchema iolContext) {
        CustomerBean bean = new CustomerBean();
        if (iolContext == null || iolContext.getCustomerContext() == null) return bean;
        Object custCtx = iolContext.getCustomerContext();
        if (custCtx instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) custCtx;
            bean.setCustomerId(safeString(map.get("customerId")));
            bean.setCustomerClass(safeString(map.get("customerClass")));
            bean.setCustomerName(safeString(map.get("customerName")));
        }
        return bean;
    }

    public static AccountBean extractAccountBean(IOLSchema iolContext) {
        List<AccountBean> list = extractAccountBeanList(iolContext);
        return list.isEmpty() ? new AccountBean() : list.getFirst();
    }

    public static List<AccountBean> extractAccountBeanList(IOLSchema iolContext) {
        List<AccountBean> beans = new ArrayList<>();
        if (iolContext == null || iolContext.getAccountContext() == null) return beans;
        Object acctCtx = iolContext.getAccountContext();
        if (acctCtx instanceof List) {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> list = (List<Map<String, Object>>) acctCtx;
            for (Map<String, Object> map : list) {
                AccountBean bean = new AccountBean();
                bean.setSortCode(safeString(map.get("sortCode")));
                bean.setAccountNumber(safeString(map.get("accountNumber")));
                beans.add(bean);
            }
        }
        return beans;
    }

    public static ConfigContextBean extractConfigContextBean(IOLSchema iolContext) {
        ConfigContextBean bean = new ConfigContextBean();
        if (iolContext == null || iolContext.getConfigContext() == null) return bean;
        Object configCtx = iolContext.getConfigContext();
        if (configCtx instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) configCtx;
            Map<String, String> attrs = new HashMap<>();
            for (Map.Entry<String, Object> e : map.entrySet()) {
                attrs.put(e.getKey(), safeString(e.getValue()));
            }
            bean.setConfigContextAttributes(attrs);
        }
        return bean;
    }

    public static SecureContextBean extractSecureContextBean(IOLSchema iolContext) {
        SecureContextBean bean = new SecureContextBean();
        if (iolContext == null || iolContext.getSecureContext() == null) return bean;
        Object secCtx = iolContext.getSecureContext();
        if (secCtx instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) secCtx;
            Map<String, String> attrs = new HashMap<>();
            for (Map.Entry<String, Object> e : map.entrySet()) {
                attrs.put(e.getKey(), safeString(e.getValue()));
            }
            bean.setSecureContextAttributes(attrs);
        }
        return bean;
    }

    private static String safeString(Object obj) {
        return obj == null ? null : obj.toString();
    }

    private static int safeInt(Object obj) {
        if (obj == null) return 0;
        if (obj instanceof Number) return ((Number) obj).intValue();
        try { return Integer.parseInt(obj.toString()); } catch (NumberFormatException e) { return 0; }
    }
}
```

---

## Stub Templates by Category

### Category 1: Context Beans (UserBean, CustomerBean, AccountBean)

These are populated at runtime by `IOLContextAdapter.extractXxx(iolContext)`.

```java
/*
 * @MCA2-STUB: Migration stub for com.barclays.scp.eps.common.beans.UserBean
 * Populated from IOLSchema at runtime via IOLContextAdapter.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import java.io.Serializable;

public class UserBean implements Serializable {
    private static final long serialVersionUID = 1L;
    private String userId;
    private String userName;
    private String staffNumber;
    private String branchCode;
    private String groupId;
    private String locale;
    private ChannelBean channel;

    // Getters/setters for all fields

    public static class ChannelBean implements Serializable {
        private static final long serialVersionUID = 1L;
        private int id;
        private String code;
        private String decode;
        // Getters/setters
    }
}
```

### Category 2: Reference Data Beans (CodedValueBean, CodeDecodeBean)

Simple key-value POJOs used by validation and mapping logic.

```java
/*
 * @MCA2-STUB: Migration stub for com.barclays.scp.eps.common.beans.CodedValueBean
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import java.io.Serializable;

public class CodedValueBean implements Serializable {
    private static final long serialVersionUID = 1L;
    private String code;
    private String decode;

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getDecode() { return decode; }
    public void setDecode(String decode) { this.decode = decode; }
}
```

### Category 3: Error/Response Framework (EpsResponseBean, EpsMessageBean, EpsApplicationException)

Used by business logic that builds error responses or catches MCA1 exceptions.

```java
/*
 * @MCA2-STUB: Migration stub for EpsResponseBean.
 * Base response class used by business logic that calls getMessages()/addMessage().
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

public class EpsResponseBean implements Serializable {
    private static final long serialVersionUID = 1L;
    private List<EpsMessageBean> messages = new ArrayList<>();

    public List<EpsMessageBean> getMessages() { return messages; }
    public void setMessages(List<EpsMessageBean> messages) { this.messages = messages; }
    public void addMessage(EpsMessageBean message) {
        if (this.messages == null) this.messages = new ArrayList<>();
        this.messages.add(message);
    }
}
```

```java
/*
 * @MCA2-STUB: Migration stub for EpsApplicationException.
 * Preserved because business logic catches this and inspects errorDtosList.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import java.util.ArrayList;
import java.util.List;

public class EpsApplicationException extends RuntimeException {
    private static final long serialVersionUID = 1L;
    private List<EpsMessageBean> errorDtosList = new ArrayList<>();

    public EpsApplicationException() { super(); }
    public EpsApplicationException(String message) { super(message); }
    public EpsApplicationException(String message, Throwable cause) { super(message, cause); }
    public EpsApplicationException(Throwable cause) { super(cause); }

    public List<EpsMessageBean> getErrorDtosList() { return errorDtosList; }
    public void setErrorDtosList(List<EpsMessageBean> errorDtosList) { this.errorDtosList = errorDtosList; }
}
```

### Category 4: Message Builder (MessageBeanHelper)

Used by business logic that calls `addErrorMessageToList()`.

```java
/*
 * @MCA2-STUB: Migration stub for MessageBeanHelper.
 * Provides addErrorMessageToList / addWarningMessageToList / addInformationMessageToList.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class MessageBeanHelper {
    private static final Logger LOG = LoggerFactory.getLogger(MessageBeanHelper.class);

    public void addErrorMessageToList(EpsResponseBean responseBean, String code, UserBean userBean) {
        EpsMessageBean msg = new EpsMessageBean();
        msg.setCode(code);
        msg.setText("Error: " + code);
        msg.setType("error");
        responseBean.addMessage(msg);
        LOG.debug("Added error message: {}", code);
    }

    public void addErrorMessageToList(EpsResponseBean responseBean, String code, String text) {
        EpsMessageBean msg = new EpsMessageBean();
        msg.setCode(code);
        msg.setText(text);
        msg.setType("error");
        responseBean.addMessage(msg);
    }

    public void addWarningMessageToList(EpsResponseBean responseBean, String code, UserBean userBean) {
        EpsMessageBean msg = new EpsMessageBean();
        msg.setCode(code);
        msg.setText("Warning: " + code);
        msg.setType("warning");
        responseBean.addMessage(msg);
    }

    public void addInformationMessageToList(EpsResponseBean responseBean, String code, UserBean userBean) {
        EpsMessageBean msg = new EpsMessageBean();
        msg.setCode(code);
        msg.setText("Info: " + code);
        msg.setType("information");
        responseBean.addMessage(msg);
    }
}
```

### Category 5: Reference Data Access (DataInterface, ReferenceDataHelper, ReferenceData)

```java
/*
 * @MCA2-STUB: Migration stub for DataInterface.
 * Provides getCodeDecodeBeans() and getCodedValueBeans() for reference data lookup.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

import java.util.Collections;
import java.util.List;

public class DataInterface {
    public List<CodeDecodeBean> getCodeDecodeBeans(String key) {
        // @MCA2-REVIEW-DATA-ASSEMBLY: Reference data lookup — needs REST API or cache
        return Collections.emptyList();
    }

    public List<CodedValueBean> getCodedValueBeans(String key, Object... params) {
        // @MCA2-REVIEW-DATA-ASSEMBLY: Reference data lookup — needs REST API or cache
        return Collections.emptyList();
    }
}
```

### Category 6: Severity Enum

```java
/*
 * @MCA2-STUB: Migration stub for EpsSeverityType.
 */
package com.barclays.mca.eps.<project>.migration.stubs;

public enum EpsSeverityType {
    ERROR("error"),
    WARNING("warning"),
    INFORMATION("information");

    private final String code;
    EpsSeverityType(String code) { this.code = code; }
    public String getCode() { return code; }
}
```

---

## When to Use Stubs vs. Direct MCA2 Replacements

| Scenario | Use Stub? | Use MCA2 Direct? |
|---|---|---|
| Business logic reads `userBean.getUserId()` | Yes — `UserBean` stub + `IOLContextAdapter` | No |
| Business logic calls `msgBeanHelper.addErrorMessageToList()` | Yes — `MessageBeanHelper` stub | No |
| Business logic extends `EpsResponseBean` | Yes — `EpsResponseBean` stub | No |
| Business logic catches `EpsApplicationException` | Yes — `EpsApplicationException` stub | No |
| Controller needs to return response envelope | No | Yes — use `Response<T>` |
| Service needs IOL context for REST headers | No | Yes — use `contextProvider.getIOLContext()` directly |
| Service dispatches to backend | No | Yes — use `restClient.callRest()` |
| New validation logic being added | No | Yes — use `IOLSchema` directly |

---

## Stub Graduation Guide

Stubs are acceptable as a permanent part of the migrated codebase. However, they can be
removed incrementally as the team refactors business logic:

### Phase 1: Immediate Migration (stubs created)
All preserved business logic compiles using stubs. Framework is MCA2.

### Phase 2: IOLContextAdapter Graduation
Replace `IOLContextAdapter.extractUserBean()` calls with direct `IOLSchema` access
where the logic is simple enough:

```java
// Before (with stub)
UserBean user = IOLContextAdapter.extractUserBean(iolContext);
String userId = user.getUserId();

// After (graduated — stub no longer needed for this usage)
String userId = ((Map<String, Object>) iolContext.getUserContext()).get("userId").toString();
```

### Phase 3: MessageBeanHelper Graduation
Replace `MessageBeanHelper.addErrorMessageToList()` with MCA2 `Message` objects:

```java
// Before (with stub)
msgBeanHelper.addErrorMessageToList(responseBean, "ERR001", userBean);

// After (graduated)
throw new RequestException(Message.create("ERR001", "Validation failed"));
```

### Phase 4: EpsResponseBean Graduation
Replace domain beans that extend `EpsResponseBean` with plain POJOs:

```java
// Before (with stub)
public class MyResponse extends EpsResponseBean { ... }

// After (graduated)
public class MyResponse { /* plain POJO — errors via framework exceptions */ }
```

### Graduation Decision Criteria

| Stub | Graduate When | Keep If |
|---|---|---|
| `UserBean` + `IOLContextAdapter` | Logic is simple field access | Logic does complex user context processing |
| `CustomerBean` | Logic is simple field access | Logic does customer classification |
| `AccountBean` | Logic is simple field access | Logic does account type routing |
| `EpsResponseBean` | Response model refactored to plain POJOs | Business logic extensively uses `getMessages()`/`addMessage()` |
| `MessageBeanHelper` | Error handling refactored to MCA2 exceptions | Business logic has 50+ error code paths |
| `EpsApplicationException` | Exception handling refactored to MCA2 types | Business logic catches and inspects `errorDtosList` |
| `CodedValueBean`/`CodeDecodeBean` | Reference data migrated to EHCache or REST | Used throughout validation logic |
| `DataInterface`/`ReferenceDataHelper` | Reference data migrated to REST API | Core to business validation |
