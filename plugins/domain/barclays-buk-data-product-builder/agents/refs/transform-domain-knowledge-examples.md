---
description: "Conditional usage rules for domain knowledge as soft context in transforms — covers source type quirks, naming conventions, filters, join hints, and SCD2 defaults without overriding hard constraints."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Domain Knowledge Soft Context — Transform Generation (Phase 5)

**Load condition:** Only read this file if `scoped_domain_knowledge` is not null and not "No specific domain knowledge for this table".

## Usage Rules

**CRITICAL**: Use both domain knowledge AND additional context as CONTEXT, never as override.

**From domain_knowledge_text** (advisory — never overrides mapping Excel):
- Source column type quirks → explicit CASTs in SQL
- Team naming conventions → intermediate DataFrame suffixes (`_lrf`, `_cast`, `_joined`)
- Business filter rules → inline PySpark comments + filter expressions
- Broadcast join hints → `F.broadcast()` on known small lookup tables
- SCD2 defaults (eff_end_date format) → use if mapping doesn't specify
- Source system quirks → apply CASTs for known type mismatches

**From additional_context in mapping document** (per target table):
- Business context → use in docstrings + comments
- Quality rules → use in filter conditions + validation comments
- Known data issues → add comments warning about specific value patterns
- Expected grain / cardinality hints → document in comments

**From table_description in mapping document** (per target table):
- Purpose / usage context → use in class docstrings
- Key business stakeholders → document for audit trail
- SCD2 configuration hints → use if not explicit in columns
- Partition strategy hints → inform partition_col determination

## Example Usage

```python
class account_wm_transform_day0:
    """
    Day 0 transformation for account_wm
    
    Business Purpose (from mapping.table_description):
      Central repository of active mortgage accounts across all channels.
      Used by portfolio analytics and risk reporting.
    
    Additional Context (from mapping.additional_context):
      Source system has duplicate transactions for accounts opened mid-month.
      Filter by transaction_type = 'POSTED' only.
      Apply SCD2 with eff_end_date = 3499-12-31 per domain standards.
    
    Domain Knowledge Context (from domain knowledge MD):
      e_ilp_db tables have legacy _lst_mod_dte in UTC; convert to GMT+0.
      Small lookup table: rates_fees_wm < 10K rows → use broadcast join.
    """
    
    def transformation(self):
        # From mapping.additional_context: Filter duplicate transactions
        # Keeping only POSTED transactions (business rule)
        filtered_df = source_df.filter(F.col('transaction_type') == 'POSTED')
        
        # From domain knowledge: Cast legacy date column from UTC to DATE
        # e_ilp_db._lst_mod_dte is in UTC; domain standards require GMT+0
        transformed_df = filtered_df.withColumn(
            'eff_start_date',
            F.to_date(F.col('_lst_mod_dte')).cast('DATE')
        )
        
        # From domain knowledge: rates_fees_wm is small < 10K rows
        # Use broadcast join for optimization
        joined_df = transformed_df.join(
            F.broadcast(rates_df),
            'rate_id'
        )
        
        return joined_df
```

## Hierarchy of Authority

1. **Mapping Excel** (transformation_logic, column definitions) — PRIMARY
2. **Domain Knowledge MD** (hints, quirks, conventions) — ADVISORY
3. **Additional Context** (business rules, quality notes) — ADVISORY
4. **Table Description** (purpose, grain hints) — ADVISORY

**NEVER override** mapping logic based on domain knowledge. Use domain knowledge to ADD context (comments, CASTs, hints) not to CHANGE what's in the mapping.
