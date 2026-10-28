# Validator: consistency-validator

**Purpose**: Validate platform consistency, naming prefix conventions, and source layer promotion rules.

**Severity**: HALT (platform/layer violations) / WARNING (naming prefix mismatch).

**Platform**: Glue + Databricks

---

## Part A — Platform Consistency

### Platform-Artefact Mapping

| Artefact Pattern | Expected Platform |
|---|---|
| `*_mesh.json` | Glue only |
| `wrapper.py` | Glue only |
| `config.json` (table-level) | Glue only |
| `*_dtxog.json` | Glue only |
| `*_table_creation_utility.py` | Databricks only |
| `driver.py` | Databricks only |
| `config.yml` | Databricks only |
| `databricks.yml` | Databricks only |
| `*_job.yml` | Databricks only |
| `transform.py` | Both (platform-neutral) |

### Validation Logic

1. Read `session_state.platform`
2. Scan `session_state.artefact_status` for all generated artefact filenames
3. Check each artefact against the mapping table above
4. If Glue-only artefact found in Databricks session (or vice versa): HALT

### Pass Condition (Part A)

All artefacts match the session platform.

### Fail Action (Part A)

HALT:
```
❌ Platform consistency violation detected!
Session platform: Databricks
The following Glue-only artefacts were found:
  - {filename_1} (Glue-only artefact in a Databricks session)

This should not be possible — please report this as a plugin bug.
Start a new session with /init to recover.
```

---

## Part B — Naming Prefix

### Expected Prefixes

| Data Product Type | Expected Target DB Prefix |
|---|---|
| FDP | `fdp_` or `shared_fdp_` |
| CDP | `cdp_` or `shared_cdp_` |
| BDP | `bdp_` or `shared_bdp_` |

### Validation Logic

1. Read `session_state.expected_db_prefix` (set by data-product-type-router)
2. Read `mapping_parsed.json → target_database`
3. Check if `target_database.lower().startswith(expected_db_prefix)`

### Pass Condition (Part B)

`target_database` starts with the expected prefix for the selected data product type.

### Fail Action (Part B)

WARNING (non-blocking):
```
⚠️ Naming prefix warning:
   Target database `{target_database}` does not start with `{expected_db_prefix}` 
   (expected for {data_product_type}).
   
   If this is a legacy table name or a special case, confirm and continue.
   If the data product type is wrong, re-answer G1.5 with the correct type.
```

---

## Part C — Source Layer Consistency

### Layer Promotion Rules

| Data Product Type | Expected Source Layer | Allowed Source Prefixes | BLOCKED Prefixes |
|---|---|---|---|
| FDP | BASE / FDP / CDP | `e_*`, `bas_*` (BASE layer), `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*` | `bdp_*`, `shared_bdp_*` |
| CDP | FDP / CDP (BASE exceptionally) | `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*`; `e_*`, `bas_*` (WARNING, not blocked) | `bdp_*`, `shared_bdp_*` |
| BDP | FDP / CDP | `fdp_*`, `shared_fdp_*`, `cdp_*`, `shared_cdp_*` | `e_*`, `bas_*` (BASE), `bdp_*`, `shared_bdp_*` (another BDP) |

### Validation Logic

1. Read `session_state.expected_source_layer` and `session_state.data_product_type`
2. Read `session/mapping_parsed.json` → collect unique `database` values from `columns[].source_references[]`
3. For each unique source database prefix:
   - Classify: `e_*` or `bas_*` = BASE layer; `fdp_*` or `shared_fdp_*` = FDP; `cdp_*` or `shared_cdp_*` = CDP; `bdp_*` or `shared_bdp_*` = BDP
   - Check against allowed prefixes for the data product type:
     - FDP → allowed: BASE (`e_*`, `bas_*`), FDP (`fdp_*`, `shared_fdp_*`), CDP (`cdp_*`, `shared_cdp_*`)
     - CDP → allowed: FDP (`fdp_*`, `shared_fdp_*`), CDP (`cdp_*`, `shared_cdp_*`)
     - BDP → allowed: FDP (`fdp_*`, `shared_fdp_*`), CDP (`cdp_*`, `shared_cdp_*`)
4. Classify violation type: BLOCK or WARNING

### Severity Classification

**Mapping Supremacy applies:** Since the mapping document is the source of truth, a layer rule violation that exists in the mapping itself is NOT a generation defect — it is a mapping design decision.

| Scenario | Severity | Action |
|---|---|---|
| Source→target relationship **exists in `mapping_parsed.json`** and violates layer rules | **ADVISORY (WARNING)** | Log observation for human review. Do NOT halt. The mapping is authoritative. |
| Source→target relationship **does NOT exist in mapping** (hallucinated by generator) and violates layer rules | **BLOCK** | This is both a layer violation AND a mapping fidelity violation. Halt generation. |

### Advisory Conditions (mapping-specified layer violations)

| Violation | Message |
|---|---|
| FDP reading BDP layer (`bdp_*` or `shared_bdp_*`) — mapping-specified | "⚠️ Advisory: FDP reads from BDP source `{db}` — unconventional layer promotion, but mapping-specified." |
| CDP reading BASE layer (`e_*` or `bas_*`) — mapping-specified | "⚠️ Advisory: CDP reads from BASE source `{db}` — unconventional, but mapping-specified." |
| BDP reading BASE layer (`e_*` or `bas_*`) — mapping-specified | "⚠️ Advisory: BDP reads from BASE source `{db}` — unconventional, but mapping-specified." |
| BDP reading another BDP (`bdp_*` or `shared_bdp_*`) — mapping-specified | "⚠️ Advisory: BDP reads from another BDP source `{db}` — unconventional, but mapping-specified." |

### BLOCK Conditions (hallucinated source, NOT in mapping)

| Violation | Message |
|---|---|
| Any layer violation where the source database is NOT in `mapping_parsed.json` `source_references[]` | "❌ Layer violation on hallucinated source: `{db}` is not in the mapping document AND violates layer rules." |

### Pass Condition (Part C)

Either:
- All source database prefixes are allowed for the selected data product type, OR
- All layer-violating sources are mapping-specified (advisory only, no block)

### Fail Action (Part C)

BLOCK only for hallucinated (non-mapping) layer violations. User must re-run generation. Advisory observations are logged but do not halt the pipeline.

---

## Part E — Config/Driver Environment Alignment (Databricks Only)

### Purpose

Verify that `SUPPORTED_ENVS` in generated driver.py matches the `environments` keys in the co-located config.yml. A mismatch causes runtime failures: either the driver rejects a valid environment, or it accepts an environment that has no config resolution.

### Severity: BLOCK

### Validation Logic

1. For each generated driver file in `generated/databricks/src/Notebooks/{day0,day1}/{schema}_{table}/` (single-flow) or `generated/databricks/src/Notebooks/{day0,day1}/{source_system}/{schema}_{table}/` (multi-source-system):
   - Read co-located `{schema}_{table}_config.yml` → extract `list(config["environments"].keys())` → `config_envs`
   - Read `{schema}_{table}_driver.py` → determine `SUPPORTED_ENVS` derivation pattern:

     **Pattern A — Static tuple literal:**
     - Regex: `SUPPORTED_ENVS\s*=\s*\(([^)]+)\)` where the value is a comma-separated list of string literals
     - Extract tuple values → `driver_envs`
     - Compare: `set(config_envs) == set(driver_envs)` → if match, PASS; if mismatch, BLOCK

     **Pattern B — Dynamic config derivation:**
     - Regex: `SUPPORTED_ENVS\s*=\s*.*config\.get\("environments"` (detects `tuple(config.get("environments", {}).keys())` or `_env_keys if _env_keys else (...)`)
     - If this pattern is found, `SUPPORTED_ENVS` is derived from config at runtime and is inherently aligned with config.yml by construction.
     - If a fallback tuple is present (via `or (...)` or `if ... else (...)`), extract it → `fallback_envs`. Validate that `set(config_envs) <= set(fallback_envs)` (fallback must be a superset of config envs so it never rejects a valid environment). If fallback is NOT a superset → WARN (advisory, not blocking — the dynamic derivation takes precedence at runtime when config has environments).
     - PASS (dynamic derivation guarantees alignment when config.yml has an `environments` section).

     **Pattern C — Neither pattern found:**
     - BLOCK: `SUPPORTED_ENVS` uses an unrecognised derivation pattern. Cannot validate alignment.

2. Aggregate results across all driver/config pairs.

### Pass Condition (Part E)

For EVERY driver/config pair: `SUPPORTED_ENVS` is either (A) a static tuple matching config.yml environment keys exactly, or (B) dynamically derived from config at runtime.

### Fail Action (Part E)

**BLOCK (Pattern A mismatch):**
```
❌ Config/Driver environment mismatch detected!
   Driver: {schema}_{table}_driver.py
     SUPPORTED_ENVS = {driver_envs}  (static tuple)
   Config: {schema}_{table}_config.yml
     environments keys = {config_envs}

   The driver will reject valid environments or accept unconfigured ones.
   Fix: Re-run /gen-driver to synchronise SUPPORTED_ENVS with config.yml.
```

**BLOCK (Pattern C — unknown derivation):**
```
❌ Cannot validate SUPPORTED_ENVS in {schema}_{table}_driver.py
   SUPPORTED_ENVS is neither a static tuple nor derived from config.get("environments").
   Manual review required. Fix: Re-run /gen-driver.
```

**WARN (Pattern B — fallback not superset, advisory only):**
```
⚠️ SUPPORTED_ENVS fallback tuple in {schema}_{table}_driver.py
   does not cover all config environments.
   Fallback: {fallback_envs}
   Config:   {config_envs}
   Missing from fallback: {config_envs - fallback_envs}
   This is advisory — at runtime, the dynamic derivation takes precedence
   when config.yml has environments. Fallback only activates if environments
   section is empty or missing.
```

### Skip Condition

- Platform = Glue → skip entirely (Glue has no SUPPORTED_ENVS pattern)
- No driver files found → skip (not yet generated)

---

## Part D — Domain Knowledge Tenancy Consistency

### Validation Logic

1. Read `session_state.tenancy_name`
2. Read `session_state.domain_knowledge_validated_tenancy`
3. If both are non-null AND they differ → HALT

### Pass Condition (Part D)

Either:
- No domain knowledge loaded (`domain_knowledge_validated_tenancy` is null), OR
- `domain_knowledge_validated_tenancy == tenancy_name`

### Fail Action (Part D)

HALT:
```
❌ Cross-tenancy domain knowledge detected!
Session tenancy: {tenancy_name}
Domain knowledge tenancy: {domain_knowledge_validated_tenancy}

Domain knowledge from a different tenancy would inject incorrect business rules.
Re-run /init with correct --domain-knowledge path or fix tenancy registry.
```

---

## Part F — Rolling Deletion Internal Consistency

### Purpose

Validate that the `rolling_deletion` config section is internally consistent and does not conflict with the table type.

### Severity: ERROR

### Validation Logic

**When**: `rolling_deletion` section present in generated config.

1. If `rolling_deletion.enabled` is `true`, then `rolling_deletion.predicate` MUST be a non-empty string
2. If `rolling_deletion.enabled` is `false`, the predicate field may be empty or absent (section is a no-op)
3. The `rolling_deletion` section must NOT coexist with `table_type == "NonTransactional_SCD2"` (cross-ref: `cdc-presence-assertion-validator` Check 8)

### Pass Condition (Part F)

Either:
- `rolling_deletion` section is absent from config, OR
- All three rules above are satisfied

### Fail Action (Part F)

ERROR:
```
❌ Rolling deletion internal consistency violation!
   {specific rule violated}
   
   Rule 1: enabled=true requires non-empty predicate string
   Rule 2: enabled=false allows empty/absent predicate (no-op)
   Rule 3: rolling_deletion must not coexist with NonTransactional_SCD2 table_type
   Fix: Correct the rolling_deletion section or remove it if table_type is SCD2.
```
