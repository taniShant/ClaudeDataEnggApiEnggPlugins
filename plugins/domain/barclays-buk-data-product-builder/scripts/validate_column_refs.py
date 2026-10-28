"""
Validate that generated PySpark transform code only references source columns
that exist in the mapping document (mapping_parsed.json).

Catches hallucinated/invented column names before they reach production.
Does NOT flag intermediate processing columns (e.g., from .withColumn(), .alias(),
window functions, aggregation outputs).

Usage:
    python validate_column_refs.py <transform_file.py> <mapping_parsed.json> [--target-table <name>]

Exit codes:
    0 = all column references valid
    1 = violations found (JSON printed to stdout)
    2 = usage/parse error
"""

import json
import re
import sys
from collections import defaultdict


# Audit columns always permitted (not from mapping)
AUDIT_COLUMNS = frozenset({
    "eff_start_date", "eff_end_date", "active",
    "dw_lod_tmp", "dw_upd_lod_tmp", "dw_bus_dt",
})

# Known intermediate column prefixes/names from standard patterns
INTERMEDIATE_PREFIXES = ("_rn", "_rank", "_salt", "_row_num", "_dedup", "_join_key")

# Spark built-in function outputs (not column references)
SPARK_FUNCTIONS = frozenset({
    "current_timestamp", "current_date", "monotonically_increasing_id",
    "spark_partition_id", "input_file_name",
})


def build_source_allowlist(mapping, target_table=None):
    """
    Build {alias: set(columns)} from mapping_parsed.json source_references
    AND extracted_join_predicates/extracted_literals (infrastructure columns).

    Infrastructure columns are needed for joins, dedup ordering, and filtering
    but do not appear as target column outputs — they only exist in
    transformation_logic free-text parsed by STEP 2.8 of /de-parse-mapping.
    """
    allowlist = defaultdict(set)
    columns = mapping.get("columns", [])

    for col in columns:
        # Source references (output-facing columns)
        for ref in col.get("source_references", []):
            table = ref.get("table", "").lower()
            column = ref.get("column", "").lower()
            if table and column:
                allowlist[table].add(column)

        # Extracted join predicates → infrastructure columns (join keys)
        for pred in (col.get("extracted_join_predicates") or []):
            if pred.get("confidence") in ("high", "medium"):
                lt = pred.get("left_table", "").lower()
                lc = pred.get("left_col", "").lower()
                rt = pred.get("right_table", "").lower()
                rc = pred.get("right_col", "").lower()
                if lt and lc:
                    allowlist[lt].add(lc)
                if rt and rc:
                    allowlist[rt].add(rc)

        # Extracted literals → filter/case-when columns
        for lit in (col.get("extracted_literals") or []):
            if lit.get("confidence") in ("high", "medium"):
                lit_col = (lit.get("column") or "").lower()
                if not lit_col:
                    continue
                # Attribute to alias that already contains this column
                attributed = any(
                    lit_col in cols for cols in allowlist.values()
                )
                if not attributed:
                    # Column not yet in any alias — cannot safely attribute;
                    # leave for AUDIT_COLUMNS or other mechanisms to cover
                    pass

    return dict(allowlist)


def build_target_allowlist(mapping):
    """
    Build set of valid target column names from mapping.
    """
    target_cols = set()
    for col in mapping.get("columns", []):
        name = col.get("target_column_name", "")
        if name:
            target_cols.add(name.lower())
    return target_cols | AUDIT_COLUMNS


def find_created_columns(code_lines, up_to_line):
    """
    Identify columns created by intermediate processing steps BEFORE the given line.
    These are legitimate — not invented source columns.
    """
    created = set()
    prior_code = "\n".join(code_lines[:up_to_line])

    # .withColumn("col_name", ...)
    for m in re.finditer(r'\.withColumn\(\s*["\']([^"\']+)["\']', prior_code):
        created.add(m.group(1).lower())

    # .alias("col_name") in expressions — column being created
    for m in re.finditer(r'\.alias\(\s*["\']([^"\']+)["\']', prior_code):
        created.add(m.group(1).lower())

    # F.col("x").alias("y") — y is created
    # .agg(F.sum("x").alias("total")) — total is created
    # These are already captured by the .alias() pattern above

    return created


def infer_alias_from_context(line, code_lines, line_idx):
    """
    Attempt to determine which source table alias a column reference belongs to.
    Returns alias (lowercase) or None if indeterminate.
    """
    # Pattern: self.alias_name reference on the same line
    alias_match = re.search(r'self\.(\w+)', line)
    if alias_match:
        alias = alias_match.group(1).lower()
        # Exclude known non-alias attributes
        if alias not in ("spark", "config", "curr_bus_dt", "audit", "operation",
                         "table_type", "reader", "writer", "source_data",
                         "staging_path"):
            return alias

    return None


def extract_fcol_references(code_lines):
    """
    Extract all F.col("column_name") references with line numbers and context.
    """
    refs = []
    pattern = re.compile(r'F\.col\(\s*["\']([^"\']+)["\']\s*\)')

    for idx, line in enumerate(code_lines):
        # Skip comments
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in pattern.finditer(line):
            refs.append({
                "col": m.group(1),
                "line": idx + 1,
                "line_text": line,
                "line_idx": idx,
            })
    return refs


def extract_bracket_access_references(code_lines):
    """
    Extract self.alias["column_name"] or self.alias['column_name'] references.
    """
    refs = []
    pattern = re.compile(r'self\.(\w+)\s*\[\s*["\'](\w+)["\']\s*\]')

    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in pattern.finditer(line):
            alias = m.group(1).lower()
            col = m.group(2)
            # Skip non-alias attributes
            if alias not in ("source_data", "config"):
                refs.append({
                    "col": col,
                    "alias": alias,
                    "line": idx + 1,
                    "line_text": line,
                    "line_idx": idx,
                })
    return refs


def is_known_exception(col_name):
    """
    Check if a column name is a known exception that should not be flagged.
    """
    col_lower = col_name.lower()

    # Audit columns
    if col_lower in AUDIT_COLUMNS:
        return True

    # Spark function names
    if col_lower in SPARK_FUNCTIONS:
        return True

    # Intermediate prefixes
    if any(col_lower.startswith(prefix) for prefix in INTERMEDIATE_PREFIXES):
        return True

    return False


def extract_output_columns(code_lines):
    """
    Extract all column names that the transform produces in its final output.
    Includes columns from .alias(), .withColumn(), and the final .select().
    """
    output_cols = set()

    # .alias("col_name") — column being created for output
    for line in code_lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in re.finditer(r'\.alias\(\s*["\']([^"\']+)["\']', line):
            output_cols.add(m.group(1).lower())

    # .withColumn("col_name", ...) — intermediate or output column
    for line in code_lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in re.finditer(r'\.withColumn\(\s*["\']([^"\']+)["\']', line):
            output_cols.add(m.group(1).lower())

    # F.col("col_name") in final .select() — direct pass-through
    for line in code_lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for m in re.finditer(r'F\.col\(\s*["\']([^"\']+)["\']', line):
            output_cols.add(m.group(1).lower())

    return output_cols


def validate_coverage(transform_path, mapping_path, target_table=None):
    """
    Check 4: Verify all mapping target columns are produced by the transform.
    Returns list of violation dicts for missing columns.
    """
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    target_cols = set()
    for col in mapping.get("columns", []):
        name = col.get("target_column_name", "")
        if name:
            target_cols.add(name.lower())

    with open(transform_path, "r", encoding="utf-8") as f:
        code = f.read()
    code_lines = code.splitlines()

    output_cols = extract_output_columns(code_lines)

    violations = []
    for col in sorted(target_cols):
        # Skip audit columns — TargetWriter handles these for Day1
        if col in AUDIT_COLUMNS:
            continue
        if col not in output_cols:
            violations.append({
                "line": None,
                "column": col,
                "type": "mapping_row_not_produced",
                "issue": (
                    f"Target column '{col}' exists in mapping_parsed.json but is "
                    f"NOT present in the generated transform output "
                    f"(no .alias() or .withColumn() produces it)"
                ),
            })

    return violations


def validate(transform_path, mapping_path, target_table=None):
    """
    Main validation: check all column references in transform against mapping allowlist.
    Returns list of violation dicts.
    """
    # Load mapping
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    source_allowlist = build_source_allowlist(mapping, target_table)
    target_allowlist = build_target_allowlist(mapping)

    # Load transform code
    with open(transform_path, "r", encoding="utf-8") as f:
        code = f.read()
    code_lines = code.splitlines()

    violations = []

    # Check F.col() references
    fcol_refs = extract_fcol_references(code_lines)
    for ref in fcol_refs:
        col_name = ref["col"]
        col_lower = col_name.lower()
        line_idx = ref["line_idx"]

        # Skip known exceptions
        if is_known_exception(col_name):
            continue

        # Skip if column was created by intermediate processing
        created = find_created_columns(code_lines, line_idx)
        if col_lower in created:
            continue

        # Skip if this is a target column reference (e.g., in final .select or .alias)
        if col_lower in target_allowlist:
            continue

        # Determine alias context
        alias = infer_alias_from_context(ref["line_text"], code_lines, line_idx)

        # Check against source allowlist
        if alias and alias in source_allowlist:
            if col_lower not in source_allowlist[alias]:
                violations.append({
                    "line": ref["line"],
                    "column": col_name,
                    "alias": alias,
                    "type": "invented_source_column",
                    "available": sorted(source_allowlist[alias]),
                })
        elif alias is None:
            # No alias context — check across ALL source tables
            found_in_any = any(
                col_lower in cols for cols in source_allowlist.values()
            )
            if not found_in_any and col_lower not in target_allowlist:
                violations.append({
                    "line": ref["line"],
                    "column": col_name,
                    "alias": None,
                    "type": "invented_column_no_alias",
                    "available_tables": {
                        alias: sorted(cols)
                        for alias, cols in source_allowlist.items()
                    },
                })

    # Check bracket access references (self.alias["col"])
    bracket_refs = extract_bracket_access_references(code_lines)
    for ref in bracket_refs:
        col_name = ref["col"]
        col_lower = col_name.lower()
        alias = ref["alias"]
        line_idx = ref["line_idx"]

        if is_known_exception(col_name):
            continue

        created = find_created_columns(code_lines, line_idx)
        if col_lower in created:
            continue

        if alias in source_allowlist:
            if col_lower not in source_allowlist[alias]:
                violations.append({
                    "line": ref["line"],
                    "column": col_name,
                    "alias": alias,
                    "type": "invented_source_column",
                    "available": sorted(source_allowlist[alias]),
                })

    return violations


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python validate_column_refs.py <transform.py> <mapping_parsed.json> "
            "[--target-table <name>] [--check-coverage]",
            file=sys.stderr,
        )
        sys.exit(2)

    transform_path = sys.argv[1]
    mapping_path = sys.argv[2]
    target_table = None
    check_coverage = "--check-coverage" in sys.argv

    if "--target-table" in sys.argv:
        idx = sys.argv.index("--target-table")
        if idx + 1 < len(sys.argv):
            target_table = sys.argv[idx + 1]

    try:
        violations = validate(transform_path, mapping_path, target_table)
        if check_coverage:
            coverage_violations = validate_coverage(
                transform_path, mapping_path, target_table
            )
            violations.extend(coverage_violations)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if violations:
        print(json.dumps(violations, indent=2))
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
