---
description: "Conditional optimization rules based on source volumetrics — broadcast joins for lookup tables (<10MB), repartitioning for large joins (>50GB), and skew mitigation strategies."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Volumetric Optimization Rules (Phase 5.6)

Loaded conditionally when `scoped_volumetrics` is non-null.

**Input:** `session/scoped_volumetrics_{target_table}.json` — loaded in GATHER phase (Turn 1) per the Reference Files section above. The command layer (`/gen-transform` STEP 0.6) pre-computes per-table volumetric context including role classification and optimization signals.

**Activation:** Phase 5.6 is ACTIVE only when `scoped_volumetrics` is non-null (command layer passed volumetric context). If null → skip this phase entirely.

If volumetric data is available for the source tables used by the current target table, apply these rules during code generation:

```
VOLUMETRIC OPTIMIZATION RULES:

1. BROADCAST JOINS (LOOKUP TABLES ONLY — never main/driver source):
   - broadcast_hint = true AND table is a LOOKUP source → wrap with F.broadcast() in join
   - estimated_size_gb < 0.01 (10MB) AND table is a LOOKUP source → auto-broadcast
   - NEVER F.broadcast() the MAIN/driver source table — config `cdc.broadcast_source`
     handles broadcast at the CDC merge layer via TargetWriter/run_cdc
   - MAIN = source table from which majority of target columns derive (most source_references)
   - LOOKUP = table joined to enrich 1-2 columns; typically *_ref, *_decode, *_dim, *_lookup
   - If uncertain whether MAIN or LOOKUP → treat as MAIN (do NOT broadcast) — safer default
   - Example: df_result = df_driver.join(F.broadcast(df_lookup), on="key", how="left")

2. REPARTITION FOR LARGE JOINS:
   - estimated_size_gb > 50 AND multiple sources joined → repartition both sides by join key
     before the join: df_a.repartition("join_key"), df_b.repartition("join_key")
   - If source volumetric `primary_key` is available → use it as repartition key
     (aligns data co-location with join/window partition keys)
   - estimated_rows > 100M → add .repartition(total_cores, "pk_col") before heavy window
     operations (temporal stitching, ROW_NUMBER dedup)

3. PARTITION PRUNING:
   - If source volumetric `partition_key` is available → verify that config.json/yml
     filters already include partition column predicates for early pruning.
   - Config filters TAKE PRECEDENCE — do NOT override or duplicate filters already
     declared in config.json/yml. Volumetric partition_key is informational only;
     use it to VALIDATE config completeness, not to inject additional filters.
   - If config has no filter on the partition_key column → log ADVISORY suggesting
     the analyst add a partition filter to config for performance (non-blocking).

4. TABLE TYPE AWARENESS:
   - table_type = "NonTransactional_SCD2" → entity-state tables with SCD2 history tracking; temporal stitching rules apply; CDC merge derives eff_start_date, eff_end_date, active; active filter applied by SourceReader from config — do NOT duplicate in transform
   - table_type = "NonTransactional_SCD1" → entity-state tables with overwrite-in-place; NO temporal stitching; NO CDC processing; NO eff_start_date/eff_end_date/active derivation; writer calls SCD1 UPSERT (derives only dw_lod_tmp, dw_upd_lod_tmp)
   - table_type = "Transactional" → append-only event/fact tables; no temporal stitching; partition by dw_bus_dt

5. COALESCE BEFORE WRITE:
   - estimated_size_gb < 1 → coalesce(1) before write (small output = fewer files)
   - estimated_size_gb 1-10 → coalesce(4)
   - estimated_size_gb > 10 → no coalesce (let Spark manage partitions)

6. LINEAGE BREAK ACTIVATION:
   - total_day0_gb > 50 OR total_day1_gb > 10 → enable lineage breaks (uncommented, active code)
     using parquet persist/reload pattern:
       df.write.mode("overwrite").parquet(f"{_lineage_break_path}/step_name")
       df = self.spark.read.parquet(f"{_lineage_break_path}/step_name")
   - total_day0_gb > 100 → additionally consider staging writes
     (write/read parquet to self.staging_path between major transformation stages)
   - Domain knowledge mentions "OOM"/"checkpoint"/"staging" → enable regardless of thresholds
   - NOTE: Do NOT use spark.sparkContext.setCheckpointDir() or df.checkpoint() —
     blocked on Shared Access Mode / Serverless ([JVM_ATTRIBUTE_NOT_SUPPORTED])

PRECEDENCE: Domain knowledge performance hints OVERRIDE these volumetric defaults.
If domain knowledge specifies broadcast/repartition/coalesce for a specific table,
use domain knowledge values. Volumetric rules are FALLBACK when domain knowledge
is silent on performance for a given source.
```

**If `scoped_volumetrics` is null (command layer did not provide volumetric context):** Skip Phase 5.6 entirely — no performance assumptions. Do NOT attempt to read `session/source_volumetrics.json` directly; the command layer handles scoping and role classification.
