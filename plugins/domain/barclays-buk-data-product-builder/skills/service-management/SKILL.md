---
name: service-management
description: "Operational reference for pipeline deployment: ITSI codes (IT Service Identifiers for Netcool alerting) per tenancy/environment, DTX state machine naming, crypto API endpoint URLs, runtime versions (Glue 4.0, PySpark 3.3+, Iceberg 1.2+), and known issues/workarounds. Use when populating ITSI/compid fields, selecting runtime versions, or diagnosing deployment errors."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-08-18
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-08-18

# Operational Reference — ITSI, Versions, Gotchas

## ITSI & Netcool Components

### Tenancy ITSI & Netcool Component Mapping

| Tenancy | dev ITSI | uat ITSI | prd ITSI | prd Netcool Compid |
|---|---|---|---|---|
| `complaints` | `SNSVC0069877` | `SNSVC0069872` | `SNSVC0069873` | `BUKFDPCONSCOMP` |
| `customer` | `SNSVC0070020` | `SNSVC0070017` | `SNSVC0069880` | `BUKFDPCONSCUST` |
| `fdpnps` | `SNSVC0071863` | `SNSVC0071866` | `SNSVC0071776` | `BUKFDPTNPS` |
| `cdpcustomer` | `SNSVC0072039` | `SNSVC0072045` | `SNSVC0072042` | `CDPBUKCONSCUST` |
| `cdpchannels` | `SNSVC0072645` | `SNSVC0072642` | `SNSVC0073325` | `CDPBUKCHANNELS` |
| `fdpchnlcc` | `SNSVC0072645` | `SNSVC0072642` | `SNSVC0073325` | `FDPBUKCHANCC` |
| `fdpbrnchchnl` | `SNSVC0072756` | `SNSVC0072755` | `SNSVC0073319` | `FDPBUKBRANCHAN` |
| `fdpmortgage` | `SNSVC0072836` | `SNSVC0072837` | `SNSVC0073328` | `FDPBUKMORT` |
| `fdpukloans` | `SNSVC0072926` | `SNSVC0072929` | `SNSVC0073315` | `FDPBUKCONSLOANS` |
| `fdpdigital` | `SNSVC0072843` | `SNSVC0072838` | `SNSVC0073310` | `FDPBUKDIGICHAN` |
| `fdpukcards` | `SNSVC0072630` | `SNSVC0072627` | `SNSVC0073314` | `FDPBUKUKCARDS` |
| `fdpbusbank` | `SNSVC0073660` | `SNSVC0073663` | `SNSVC0073648` | `FDPBUKBUSBANK` |
| `fdpbpf` | `SNSVC0074162` | `SNSVC0074168` | `SNSVC0074165` | `BUKFDPBPF` |
| `fdpcolrcvy` | `SNSVC0074526` | `SNSVC0074525` | `SNSVC0074534` | `DEFAULT-PROD` |
| `cdpproddom` | `SNSVC0074824` | `SNSVC0074822` | `SNSVC0074821` | `DEFAULT` |
| `fdpsavings` | `SNSVC0076382` | `SNSVC0076404` | `SNSVC0076402` | `FDPBUKSAVINGS` |
| `fdpcurrentaccount` | `SNSVC0076076` | `SNSVC0076170` | `SNSVC0076074` | `BUKFDPCURRACCTOD` |
| `fdpprodins` | `SNSVC0076216` | `SNSVC0076214` | `SNSVC0076172` | `DEFAULT` |
| `fdpcommchnl` | `SNSVC0077456` | `SNSVC0077454` | `SNSVC0077458` | `BUKMARTECHDP` |
| `fdpbbfx` | `SNSVC0079176` | `SNSVC0079182` | `SNSVC0079180` | `DEFAULT` |
| `fdpbbcu` | `SNSVC0079186` | `SNSVC0079174` | `SNSVC0079172` | `DEFAULT` |
| `fdpbbsa` | `SNSVC0079184` | `SNSVC0079170` | `SNSVC0079178` | `DEFAULT` |
| `cdpnps` | `SNSVC0071863` | `SNSVC0071866` | `SNSVC0071776` | `BUKCDPTNPS` |
| `cdpbusbank` | `SNSVC0079846` | `SNSVC0079850` | `SNSVC0079852` | `DEFAULT` |
| `cdpcmplnts` | `SNSVC0069877` | `SNSVC0069872` | `SNSVC0071779` | `CDPBUKCONSCOMP` |
| `fdpsaukba` | `SNSVC0088641` | `SNSVC0088639` | `SNSVC0088643` | `DEFAULT` |

### Default Fallback Values

- If tenancy not found: use `DEFAULT-DEV` for dev/sit/uat, `DEFAULT-PROD` for prod
- If no custom compid: use `DEFAULT`

### Per-Job ITSI Overrides

Some tenancies use different ITSI codes for specific jobs within the same environment. When this applies, it is documented in the tenancy's domain knowledge file. Example:
- `fdpcurrentaccount` UAT: main ITSI = `SNSVC0076170`, but Balance BAU job uses `SNSVC0074822`

Always check domain knowledge for per-job overrides before defaulting to the single ITSI in the table above.

---

## State Machines (DTX Orchestration)

### Naming Convention

```
dtx-sm-glue-byoc-{tenancy}
```

All Glue BYOC jobs within a tenancy share a single state machine. The tenancy name matches the Feature Team Name from the tenancy skill registry.

**Examples:**
- `dtx-sm-glue-byoc-fdpcurrentaccount`
- `dtx-sm-glue-byoc-fdpmortgage`
- `dtx-sm-glue-byoc-fdpukloans`
- `dtx-sm-glue-byoc-fdpchnlcc`

**Exceptions:**
- BDP tenancies on BCA accounts may use: `dtx-sm-glue-byoc-{tenancy}` or `dtx-sm-bca-{tenancy}` — confirm with platform team
- Databricks tenancies do not use DTX state machines

---

## Crypto API Endpoints (Per Environment)

| Environment | API Endpoint URL |
|---|---|
| dev | `https://rvv79qtyhc.execute-api.eu-west-1.amazonaws.com/development/v1` |
| uat | `https://b3sdxfbp85.execute-api.eu-west-1.amazonaws.com/qa/v1` |
| prd | `https://l3s21rqu32.execute-api.eu-west-1.amazonaws.com/production/v1` |

These are the authoritative crypto API endpoint URLs for all tenancies (same endpoints regardless of tenancy). Used to populate `session_state.env_config.{env}.crypto_api_endpoint_url` during `/de-parse-mapping` STEP 2.6.

Downstream usage: config.json crypto block (`api_endpoint_url` per env).

---

## Versions & Dependencies

### AWS Glue & PySpark

- **AWS Glue:** 4.0
- **PySpark:** 3.3+
- **Apache Iceberg:** 1.2+

### Databricks

- **Databricks Runtime:** 16.4.x-scala2.12
- **Foundation Library Version:** 0.1.5
- **Foundation Library URL:** https://nexus-amazon-pdn.barclays.intranet/repository/barclays-read-conda/barclays_sdw/databricks/0.1.5/databricks_foundation-0.1.5-py3-none-any.whl
- **Python:** 3.9+
- **Apache Iceberg:** 1.2+ (native support)

### DTX Framework

- **DTX Version:** Latest stable (deployed by platform team)
- **DTX-SQL:** Supported for SQL-based transformations
- **BYOC:** Supported for custom PySpark code

### Crypto & Security

- **ProtectorTools Version:** 1.0-py3-none-any.whl
- **AWS Secrets Manager:** Used for secret storage (never hardcode)

---

## Lessons Learned & Gotchas

### Known Issues & Workarounds

1. **`bdpcontrolit` Dedicated Accounts**
   - Does NOT use standard BCA accounts
   - Has its own dedicated account IDs (see aws skill, exception table)
   - Always verify tenancy before looking up account

2. **Old Tenancy Names**
   - Some legacy references use old names (may cause S3 bucket lookup failures)
   - Always use Feature Team Name from current tenancy registry (tenancy skill)


3. **Iceberg Database Availability**
   - Not all tenancies have Iceberg databases
   - Check "Iceberg Database" column in tenancy registry (marks unavailable)
   - `fdprefdata`, `fdprewards`, `fdpdormancy`, `fdpbbcase`, `cdpukpayments`, `cdprgltry` have no Iceberg databases

4. **Hive Database Availability**
   - Some FDP/CDP only have Iceberg, no Hive legacy tables
   - `fdpcolrcvy` and `fdpsaukba` have NO Hive database (Iceberg only)
   - Check table before generating DDL

5. **Shared ITSI Values**
   - Some tenancies share ITSI codes across dev/uat but have different prod codes
   - Always confirm environment before resolving ITSI
   - Example: `fdpchnlcc` and `cdpchannels` share dev/uat ITSI but have different prd compids

6. **S3 Bucket Pattern Selection**

   - Pattern 1 (Iceberg): Use when `target_database` matches the Iceberg Database column in tenancy registry
   - Pattern 2 (Hive): Use when `target_database` matches the Hive Database column in tenancy registry
   - Pattern 3 (Databricks): Use for Databricks-only deployments
   - Wrong pattern leads to bucket not found error

7. **Environment Prefix Consistency**
   - dev / sit = `dev1` (Pattern 1) or `dev` (Pattern 2)
   - uat = `uat1` (Pattern 1) or `uat` (Pattern 2)
   - prod = `prd1` (Pattern 1) or `prd` (Pattern 2)
   - Note: `prod` (Patterns 2 & 3) vs `prd1` (Pattern 1)

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: ITSI codes match tenancy+env
- [ ] **Check 2**: runtime versions current
- [ ] **Check 3**: state machine naming correct
- [ ] **Check 4**: crypto API endpoints resolved
- [ ] **Check 5**: known issues checked
