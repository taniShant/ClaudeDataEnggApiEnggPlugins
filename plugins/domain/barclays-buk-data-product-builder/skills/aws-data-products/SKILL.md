---
name: aws-data-products
description: "AWS infrastructure constants for data product pipelines: account IDs per DP type/environment, the 4 S3 bucket naming patterns (Iceberg/Hive/Databricks/Application), and Spark Iceberg glue.id values. Use when constructing S3 paths, resolving AWS account numbers, or configuring Iceberg SparkConf."
user-invocable: false
owner: "tom.franklin@barclays.com"
review_cadence: quarterly
last_reviewed: 2026-08-18
---

**Source:** Tom Franklin | **Owner:** tom.franklin@barclays.com | **Review:** Quarterly | **Last reviewed:** 2026-08-18

# AWS Accounts & S3 Buckets

## When to Use This Skill

Use when:
- Constructing full S3 bucket paths using the 4 naming patterns
- Looking up AWS account IDs by DP type (FDP/CDP/BDP) and environment (dev/uat/prod)
- Setting Iceberg SparkConf glue.id values for Glue catalog configuration
- Determining the correct bucket pattern (Iceberg vs Hive vs Databricks vs Application)

Do NOT use for:
- Mapping target databases to feature teams → use `aws-tenancy`
- Databricks workspace/catalog/service principal config → use `databricks-tenancy`
- ITSI codes or Netcool component IDs → use `service-management`

---

### AWS Account Numbers

| DP Type | Platform | dev / sit | uat | prod |
|---|---|---|---|---|
| FDP / CDP | DDA | `767397940910` | `590184123059` | `194722397519` |
| BDP (standard) | BCA | `998403225349` | `105695603553` | `233301737440` |
| BDP `bdpcontrolit` | BCA (dedicated) | `867344451852` | `727646513080` | `205930629242` |
| Legacy CDDW | Legacy | `162979269039` | `225166083024` | `171998379038` |

### S3 Bucket Naming — Pattern 1 (Iceberg, Central Catalogue)

Used when `target_database` matches the **Iceberg Database** column in the tenancy registry.

```
<env_prefix>-pre-<bucket_shortname>-<account_id>-eu-west-1
```

| Environment | Prefix | FDP Example | BDP Example |
|---|---|---|---|
| dev / sit | `dev1` | `dev1-pre-fdpcustomer01-767397940910-eu-west-1` | `dev1-pre-bdpukmarketing01-998403225349-eu-west-1` |
| uat | `uat1` | `uat1-pre-fdpcustomer01-590184123059-eu-west-1` | `uat1-pre-bdpukmarketing01-105695603553-eu-west-1` |
| prod | `prd1` | `prd1-pre-fdpcustomer01-194722397519-eu-west-1` | `prd1-pre-bdpukmarketing01-233301737440-eu-west-1` |

### S3 Bucket Naming — Pattern 2 (Hive, Local Catalogue)

Used when `target_database` matches the **Hive Database** column in the tenancy registry.

```
<env_prefix>-<dp_type>-<name_part>-<account_id>-eu-west-1
```

| Environment | FDP Example | BDP Example |
|---|---|---|
| dev | `dev-fdp-customer-767397940910-eu-west-1` | `dev-bdp-marketing-998403225349-eu-west-1` |
| uat | `uat-fdp-customer-590184123059-eu-west-1` | `uat-bdp-marketing-105695603553-eu-west-1` |
| prod | `prd-fdp-customer-194722397519-eu-west-1` | `prd-bdp-marketing-233301737440-eu-west-1` |

**Exception — `bdpcontrolit`:**

| Environment | S3 Bucket |
|---|---|
| dev | `dev-bdp-controlit-867344451852-eu-west-1` |
| uat | `uat-bdp-controlit-727646513080-eu-west-1` |
| prod | `prod-bdp-controlit-205930629242-eu-west-1` |

### S3 Bucket Naming — Pattern 3 (Iceberg, Databricks)

Databricks writes Iceberg to S3 via Unity Catalog External Locations.

```
<env_prefix>-pre-<dp_type><tenancy_short_name>dbx01-<account_id>-eu-west-1
```

Examples (BCA/BDP account `233301737440`, tenancy `bdpukmarketing`):
- Prod: `prd1-pre-bdpukmarketingdbx01-233301737440-eu-west-1`
- Prod Parallel: `prd1-labd-preprod-bdpukmarketingdbx01-233301737440-eu-west-1`

### S3 Bucket Naming — Pattern 4 (Applications / Crypto Package)

```
s3://<env_prefix>-oth-bukapps-<account_id>-eu-west-1/projects/crypto/pkg/ProtectorTools-1.0-py3-none-any.whl
```

| Environment | DDA (FDP/CDP) | BCA (BDP) |
|---|---|---|
| dev / sit | `s3://dev-oth-bukapps-767397940910-eu-west-1/...` | `s3://dev-oth-bukapps-998403225349-eu-west-1/...` |
| uat | `s3://uat-oth-bukapps-590184123059-eu-west-1/...` | `s3://uat-oth-bukapps-105695603553-eu-west-1/...` |
| prod | `s3://prd-oth-bukapps-194722397519-eu-west-1/...` | `s3://prd-oth-bukapps-233301737440-eu-west-1/...` |

### Iceberg SparkConf `glue.id` (Must Match Account ID)

| DP Type | dev/sit | uat | prod |
|---|---|---|---|
| FDP / CDP (DDA) | `767397940910` | `590184123059` | `194722397519` |
| BDP (BCA) | `998403225349` | `105695603553` | `233301737440` |

---

## Related Skills

| Skill | Scope |
|-------|-------|
| `barclays-buk-data-product-builder:aws-tenancy` | Glue tenancy: team → database / bucket-shortname / BTB owner / datasetType |
| `barclays-buk-data-product-builder:databricks-tenancy` | Databricks tenancy: team → workspace / catalog / service principal |
| `barclays-buk-data-product-builder:service-management` | Runtime: ITSI codes, tool versions, state machines, known issues |

## Agent Self-Check

Before using this skill's data, verify:

- [ ] **Check 1**: account ID matches DP type+env
- [ ] **Check 2**: S3 bucket pattern applied correctly
- [ ] **Check 3**: Iceberg glue.id resolved
- [ ] **Check 4**: environment resolution complete
- [ ] **Check 5**: no cross-env values
