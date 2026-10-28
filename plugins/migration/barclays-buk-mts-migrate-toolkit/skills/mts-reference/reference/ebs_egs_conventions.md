# EBS/EGS Conventions

## JAR Naming

| Jar Type | Example | Purpose |
|----------|---------|---------|
| **EBS** (Enterprise Business Service) | `ebs_custpersonal`, `ebs_saleenquiry` | Contain Command classes, service interfaces, EDOs, helper classes |
| **EGS** (Enterprise Gateway Service) | `egs_customer`, `egs_ukba` | Contain gateway access classes that talk to mainframe |
| **EGS ODS MF** (ODS Mainframe) | `egs_odsmfcustomer`, `egs_odsmfukba` | Contain Transaction classes with WMID parameter-to-TDL table mappings |
| **EGS SQL Mapper** | `egs_product` | Gateway + SQL mapper classes (e.g., ProductEao, ProductMapper) — uses DB2 SQL, not WMID/TDL. Contains table names as SQL constants. |
| **EBS Common** | `ebs_custcommon`, `ebs_salecommon` | Shared EDOs, converters, helper classes across EBS jars |
| **CGS** (Connector Gateway Service) | `bus-unit-emp`, `screeningenquiry` | Thin wrappers around EGS gateway interfaces. Contain Command classes but NO Transaction classes. |

## Package Conventions

- **EBS JARs:** `ebs_<domain>` (group: `com.barclays.ebs.<domain>` or `com.barclays.services.<domain>` or `com.barclays.cgs2.*`)
- **EGS gateway JARs:** `egs_odsmf<domain>`

## Class Hierarchy Patterns

- **Service hierarchy:** `<Name>Service.java` (interface) -> `<Name>ServiceImpl.java` -> `<Name>BaseImpl.java`
- **Command classes:** `PascalCase(methodName) + "Command.java"` (found in BaseImpl wiring)
- **EDOs:** `PascalCase(methodName) + "RequestEdo.java"` / `"ResponseEdo.java"`

## SERVICE_NAME to EBS/EGS Artifact Mapping

Use this table to resolve a `SERVICE_NAME` constant (from a `doService()` call) to the corresponding EBS, EGS ODS MF, and EGS Gateway artifacts. The primary resolution method is the import package of the class containing `SERVICE_NAME`.

| SERVICE_NAME | EBS Artifact | EGS ODS MF Artifact | EGS Gateway Artifact | Import Package Pattern |
|---|---|---|---|---|
| `PersonalCustomerService` | `ebs_custpersonal` | `egs_odsmfcustomer` | `egs_customer` | `com.barclays.ebs.custpersonal.*` |
| `NonPersonalCustomerService` | `ebs_custnonpersonal` | `egs_odsmfcustomer` | `egs_customer` | `com.barclays.ebs.custnonpersonal.*` |
| `CustomerMarkersService` | `ebs_custmarkers` | `egs_odsmfcustomer` | `egs_customer` | `com.barclays.ebs.custmarkers.*` |
| `CustomerLocateService` | `ebs_custlocate` | — | `egs_customer` | `com.barclays.ebs.custlocate.*` |
| `CustomerUpdateService` | `cust-update` (CGS) | — | `egs_customer` | `com.barclays.services.customer.*` |
| `ScreeningEnquiryService` | `screeningenquiry` (CGS) | — | `egs_customer` | `com.barclays.services.screening.*` |
| `CustomerHoldingsService` | `ebs_custholdings` | `egs_odsmfcustomer` | `egs_customer` | `com.barclays.ebs.custholdings.*` |
| `BusinessUnitService` | `bus-unit-emp` (CGS) | — | `egs_customer` | `com.barclays.services.business.*` |
| `EnquiryService` | Multiple (by package) | Multiple | — | `com.barclays.ebs.enquiry.*` |
| `UkbaService` | `ebs_ukba` | `egs_odsmfukba` | — | `com.barclays.ebs.ukba.*` |
| `SaleEnquiryService` | `ebs_saleenquiry` | `egs_odsmfsale` | — | `com.barclays.ebs.saleenquiry.*` |
| `ProductService` | `ebs_product` | — | `egs_product` (SQL mapper) | `com.barclays.ebs.product.*` |
| `LifecycleService` | `ebs_lifecycle` | `egs_odsmfcustomer` | — | `com.barclays.ebs.lifecycle.*` |

**Resolution algorithm:**
1. From `doService(SomeClass.SERVICE_NAME, ...)`, read the import for `SomeClass`
2. Match the import package prefix to the Import Package Pattern column
3. The EBS Artifact column gives the source JAR containing Command classes
4. The EGS ODS MF Artifact column gives the JAR containing Transaction classes (with WMID/TDL mappings)
5. **When EGS ODS MF is `—`**, use the EGS Gateway Artifact column instead — it may contain Transaction classes directly (e.g., `egs_customer` has Transaction classes + ROP/RIP files)

**Note:** This table covers the most common mappings. For services not listed here, resolve by inspecting the import package and matching to `build.gradle` dependency names.

## CGS JAR Resolution

CGS JARs (e.g., `bus-unit-emp`, `screeningenquiry`, `cust-update`) are thin wrappers around EGS gateway interfaces. They contain Command classes but **no** Transaction classes or TDL table names. To extract mainframe data for a CGS service:

1. Identify the Gateway interface the CGS Command class calls (e.g., `CustomerGateway`)
2. Map that Gateway to its EGS artifact using the table above (e.g., `CustomerGateway` → `egs_customer`)
3. Extract Transaction classes from that EGS artifact using the standard Tier 1/2/3 approach

## Gradle Cache Path

Source JARs for EBS/EGS dependencies can be found at:
```
~/.gradle/caches/modules-2/files-2.1/<group>/<artifact>/<version>/<hash>/
```

To extract a class from a source JAR:
```bash
unzip -p <sources-jar> "**/SomeService.java" 2>/dev/null | grep SERVICE_NAME
```
