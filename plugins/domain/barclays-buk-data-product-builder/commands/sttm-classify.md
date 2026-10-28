---
description: Classify STTM scenario type based on target table evidence
disable-model-invocation: false
---

# /sttm-classify — Classify STTM Scenario

Determine the scenario type for a target table based on available evidence.

## Description

Quick classification without full generation. Useful for understanding what type of mapping will be produced before committing to full generation.

## Arguments

- `--target`: Path to target schema. Default: `input/target_schema.xlsx`
- `--code`: Path to SQL code (optional)

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

---

1. Read target template to extract column list
2. Read SQL code (if available) to detect patterns
3. Gather evidence for EACH of the 4 axes independently:
   - Data Product Type axis: Check database prefix (fdp_/cdp_/bdp_/shared_fdp_/shared_cdp_/shared_bdp_), source layer, explicit declaration
   - Table Type axis: Check for SCD columns, MERGE pattern, explicit table_type, default Transactional
   - Crypto Aspect axis: Check for protect/unprotect UDFs, crypto registry, default None
   - IO Mode axis: Check for batch vs streaming indicators, ingestion frequency, default Batch
4. Spawn `sttm-scenario-classifier-agent` with evidence organized by axis
5. Report 4-axis classification with per-axis confidence and evidence
6. **Update session state**: If `output/sttm_session_state.json` exists, update the `classification` block:
   ```json
   {
     "data_product_type": "<result>",
     "data_product_type_confidence": <score>,
     "table_type": "<result>",
     "table_type_confidence": <score>,
     "crypto_aspect": "<result>",
     "crypto_aspect_confidence": <score>,
     "classified_at": "<ISO 8601 timestamp>"
   }
   ```

## Output

```
4-Axis Classification:

  Axis 1 - Data Product Type: FDP (Foundational Data Product)
    Confidence: 0.99
    Evidence: database prefix fdp_, sources from raw layer

  Axis 2 - Table Type: NonTransactional_SCD2
    Confidence: 0.95
    Evidence: SCD columns present (eff_start_date, eff_end_date, active)

  Axis 3 - Crypto Aspect: Detokenize
    Confidence: 0.90
    Evidence: unprotect UDF detected in SQL

  Derived Properties:
    Audit columns: eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp
    Target Table Type value: scd2
    Validation rules enabled: SC1-SC4, SC6-SC7
    Structured format required: false
```
