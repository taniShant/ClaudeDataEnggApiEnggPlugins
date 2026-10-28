"""
Validate that generated PySpark transform code does not expose primary key
columns to NULL-producing patterns.

Catches four static (no-data-needed) null-risk patterns:
  A. PK column sourced from the nullable side of a LEFT JOIN without F.coalesce()
  B. PK column derived from F.when() chain without .otherwise() (Spark defaults to NULL)
  C. PK column derived from an opaque UDF inside spark.sql() (WARNING only)
  D. PK column listed in intent but never produced in transform output

Usage:
    python validate_pk_null_risk.py <transform_file.py> <mapping_parsed.json> <intent_identification.json> [--target-table <name>]

Exit codes:
    0 = no PK null risks detected
    1 = violations found (JSON printed to stdout)
    2 = usage/parse error
"""

import json
import re
import sys


# Audit columns always managed by TargetWriter — never PK candidates
AUDIT_COLUMNS = frozenset({
    "eff_start_date", "eff_end_date", "active",
    "dw_lod_tmp", "dw_upd_lod_tmp", "dw_bus_dt",
})


# ---------------------------------------------------------------------------
# Helpers: parse join structures
# ---------------------------------------------------------------------------

def extract_joins(code_lines):
    """
    Extract .join() calls from generated code.
    Returns list of {line, text, join_type, right_df}.
    """
    joins = []
    in_join = False
    join_start_line = 0
    paren_depth = 0
    join_buffer = ""

    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        if not in_join:
            join_match = re.search(r'\.join\(', line)
            if join_match:
                in_join = True
                join_start_line = idx + 1
                remainder = line[join_match.start():]
                paren_depth = remainder.count("(") - remainder.count(")")
                join_buffer = remainder
                if paren_depth <= 0:
                    in_join = False
                    joins.append(_parse_join_block(join_buffer, join_start_line))
                    join_buffer = ""
        else:
            paren_depth += line.count("(") - line.count(")")
            join_buffer += " " + line.strip()
            if paren_depth <= 0:
                in_join = False
                joins.append(_parse_join_block(join_buffer, join_start_line))
                join_buffer = ""

    return joins


def _parse_join_block(text, line):
    """
    Parse a .join(...) block to extract the right-side DataFrame name and
    the join type (inner, left, left_outer, etc.).
    """
    # Extract right DataFrame: .join(right_df, ...)
    right_match = re.search(r'\.join\(\s*(\w+)', text)
    right_df = right_match.group(1).lower() if right_match else None

    # Extract join type: "left", "left_outer", "inner", etc.
    join_type = "inner"  # Spark default
    type_match = re.search(
        r'(?:how\s*=\s*)?["\'](\w+)["\']\s*\)', text
    )
    if type_match:
        join_type = type_match.group(1).lower()

    # Also match explicit how= patterns deeper in the expression
    how_match = re.search(r'how\s*=\s*["\'](\w+)["\']', text)
    if how_match:
        join_type = how_match.group(1).lower()

    return {
        "line": line,
        "text": text,
        "join_type": join_type,
        "right_df": right_df,
    }


def normalize_df_name(name):
    """
    Normalize a DataFrame variable name to its base alias.
    E.g., 'customer_response_df' → 'customer_response'
    """
    n = name.lower()
    for suffix in ("_df", "_filtered", "_deduped", "_prepared", "_src", "_raw"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    return n


# ---------------------------------------------------------------------------
# Helpers: trace PK column derivation
# ---------------------------------------------------------------------------

def find_pk_derivation(pk_col, code_lines):
    """
    Trace how a PK column is produced in the transform code.
    Returns {found: bool, line: int|None, expression: str|None, method: str|None}.
    method is one of: 'withColumn', 'alias', 'select_position', 'spark_sql', None
    """
    pk_lower = pk_col.lower()

    # Pattern 1: .withColumn("pk_col", expr)
    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        match = re.search(
            r'\.withColumn\(\s*["\']' + re.escape(pk_col) + r'["\']\s*,\s*(.+)',
            line, re.IGNORECASE,
        )
        if match:
            # Collect multi-line expression
            expr = _collect_expression(code_lines, idx, match.start())
            return {"found": True, "line": idx + 1, "expression": expr, "method": "withColumn"}

    # Pattern 2: .alias("pk_col") — the column is created as an alias of an expression
    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        match = re.search(
            r'\.alias\(\s*["\']' + re.escape(pk_col) + r'["\']\s*\)',
            line, re.IGNORECASE,
        )
        if match:
            # Walk backwards to find the start of this expression
            expr = _collect_expression_backwards(code_lines, idx)
            return {"found": True, "line": idx + 1, "expression": expr, "method": "alias"}

    # Pattern 3: F.col("pk_col") in final .select() without explicit alias
    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        match = re.search(
            r'F\.col\(\s*["\']' + re.escape(pk_col) + r'["\']\s*\)',
            line, re.IGNORECASE,
        )
        if match:
            return {"found": True, "line": idx + 1, "expression": line.strip(), "method": "select_position"}

    # Pattern 4: Column appears inside spark.sql() block
    in_sql = False
    sql_start = 0
    sql_buffer = ""
    for idx, line in enumerate(code_lines):
        if re.search(r'spark\.sql\(\s*(?:"""|\'{3}|")', line):
            in_sql = True
            sql_start = idx + 1
            sql_buffer = line
        elif in_sql:
            sql_buffer += "\n" + line
            if re.search(r'(?:"""|\'\'\')\s*\)', line):
                in_sql = False
                if re.search(re.escape(pk_col), sql_buffer, re.IGNORECASE):
                    return {"found": True, "line": sql_start, "expression": sql_buffer.strip(), "method": "spark_sql"}
                sql_buffer = ""

    return {"found": False, "line": None, "expression": None, "method": None}


def _collect_expression(code_lines, start_idx, match_pos):
    """Collect a potentially multi-line expression starting from start_idx."""
    line = code_lines[start_idx]
    expr = line.strip()
    # Simple heuristic: if parens are unbalanced, grab subsequent lines
    depth = expr.count("(") - expr.count(")")
    i = start_idx + 1
    while depth > 0 and i < len(code_lines):
        expr += " " + code_lines[i].strip()
        depth += code_lines[i].count("(") - code_lines[i].count(")")
        i += 1
    return expr


def _collect_expression_backwards(code_lines, alias_idx):
    """Walk backwards from an .alias() line to capture the full expression."""
    result = [code_lines[alias_idx].strip()]
    i = alias_idx - 1
    while i >= 0:
        line = code_lines[i].strip()
        if not line or line.startswith("#"):
            break
        result.insert(0, line)
        # Stop when we find a clear expression start
        if re.match(r'(F\.|df\.|self\.|[a-z_]+\s*=)', line):
            break
        i -= 1
    return " ".join(result)


# ---------------------------------------------------------------------------
# Check A: LEFT JOIN nullable side without F.coalesce()
# ---------------------------------------------------------------------------

def check_left_join_null_risk(pk_col, derivation, joins, code_lines):
    """
    Check if a PK column sources from the nullable (right) side of a
    LEFT JOIN without a protecting F.coalesce() wrapper.
    """
    if not derivation["found"]:
        return None

    expr = derivation["expression"] or ""
    expr_lower = expr.lower()

    # Identify all nullable-side DataFrames (right side of LEFT JOINs)
    nullable_dfs = set()
    for join in joins:
        if join["join_type"] in ("left", "left_outer"):
            if join["right_df"]:
                nullable_dfs.add(join["right_df"])
                nullable_dfs.add(normalize_df_name(join["right_df"]))

    if not nullable_dfs:
        return None

    # Check if the expression references a nullable-side DataFrame
    references_nullable = False
    for ndf in nullable_dfs:
        # Check for df["col"], df.col, or F.col("col") in context of nullable df
        if re.search(r'\b' + re.escape(ndf) + r'\b', expr_lower):
            references_nullable = True
            break

    if not references_nullable:
        # Also check: if the PK column comes from a source whose df variable
        # name matches a nullable df — trace F.col("pk_col") usage
        for ndf in nullable_dfs:
            # Look for assignment: ndf = .join(...)  then  F.col("pk_col") used after
            for idx, line in enumerate(code_lines):
                if re.search(r'\b' + re.escape(ndf) + r'\b', line.lower()):
                    if re.search(r'F\.col\(\s*["\']' + re.escape(pk_col) + r'["\']', line, re.IGNORECASE):
                        references_nullable = True
                        break
            if references_nullable:
                break

    if not references_nullable:
        return None

    # Check if F.coalesce() wraps the pk column reference
    has_coalesce = bool(
        re.search(
            r'F\.coalesce\([^)]*' + re.escape(pk_col),
            expr, re.IGNORECASE,
        )
    )

    if has_coalesce:
        return None

    # Also check broader code context — coalesce might be on a subsequent withColumn
    pk_lower = pk_col.lower()
    for line in code_lines:
        if re.search(r'F\.coalesce\(', line) and re.search(
            r'["\']' + re.escape(pk_col) + r'["\']', line, re.IGNORECASE
        ):
            has_coalesce = True
            break

    if has_coalesce:
        return None

    return {
        "line": derivation["line"],
        "column": pk_col,
        "type": "pk_left_join_null_risk",
        "severity": "BLOCKING",
        "issue": (
            f"PK column '{pk_col}' may source from the nullable side of a LEFT JOIN "
            f"(right-side DataFrames: {sorted(nullable_dfs)}) without F.coalesce() protection. "
            f"If the join does not match, this PK column will be NULL."
        ),
        "fix": f"Wrap with F.coalesce(F.col('{pk_col}'), F.lit(<default>)) or verify source guarantees match.",
    }


# ---------------------------------------------------------------------------
# Check B: F.when() without .otherwise()
# ---------------------------------------------------------------------------

def check_when_without_otherwise(pk_col, derivation, code_lines):
    """
    Check if a PK column is derived from an F.when() chain that ends
    without .otherwise() — Spark returns NULL for unmatched rows.
    """
    if not derivation["found"]:
        return None

    expr = derivation["expression"] or ""

    # Does the expression involve F.when()?
    if not re.search(r'F\.when\(', expr):
        return None

    # Check if .otherwise() is present
    if re.search(r'\.otherwise\(', expr):
        return None

    # If the expression is inside a .withColumn() or ends with .alias(),
    # and contains F.when() but no .otherwise(), flag it.
    return {
        "line": derivation["line"],
        "column": pk_col,
        "type": "pk_when_without_otherwise",
        "severity": "BLOCKING",
        "issue": (
            f"PK column '{pk_col}' is derived from F.when() without .otherwise(). "
            f"Spark returns NULL for rows that match no condition."
        ),
        "fix": f"Add .otherwise(F.lit(<default>)) to the F.when() chain for '{pk_col}'.",
    }


# ---------------------------------------------------------------------------
# Check C: UDF-derived PK column (WARNING only)
# ---------------------------------------------------------------------------

def check_udf_derived_pk(pk_col, derivation):
    """
    Check if a PK column is derived through a UDF (cloud_api_udf_* inside
    spark.sql()). UDFs are opaque — cannot prove they won't return NULL.
    """
    if not derivation["found"]:
        return None

    if derivation["method"] != "spark_sql":
        return None

    expr = derivation["expression"] or ""
    if not re.search(r'cloud_api_udf_', expr, re.IGNORECASE):
        return None

    return {
        "line": derivation["line"],
        "column": pk_col,
        "type": "pk_udf_derived",
        "severity": "WARNING",
        "issue": (
            f"PK column '{pk_col}' is derived through a UDF inside spark.sql(). "
            f"UDF behaviour is opaque — cannot statically verify it never returns NULL."
        ),
        "fix": f"Add a COALESCE() wrapper inside the SQL or an F.coalesce() after the spark.sql() result.",
    }


# ---------------------------------------------------------------------------
# Check D: PK column not produced in output
# ---------------------------------------------------------------------------

def check_pk_not_produced(pk_col, derivation):
    """
    Check if a PK column is never produced by the transform.
    """
    if derivation["found"]:
        return None

    return {
        "line": None,
        "column": pk_col,
        "type": "pk_not_produced",
        "severity": "BLOCKING",
        "issue": (
            f"PK column '{pk_col}' is listed in intent_identification.json but "
            f"not found in any .withColumn(), .alias(), F.col(), or spark.sql() "
            f"expression in the generated transform."
        ),
        "fix": f"Ensure the transform produces '{pk_col}' in its output .select().",
    }


# ---------------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------------

def get_pk_columns(intent_path, target_table=None):
    """
    Load primary_key_columns from intent_identification.json.
    If target_table is specified, filter to that table entry.
    """
    with open(intent_path, "r", encoding="utf-8") as f:
        intent = json.load(f)

    # intent_identification.json is an array of target table entries
    if not isinstance(intent, list):
        intent = [intent]

    pk_columns = []
    for entry in intent:
        if target_table:
            if entry.get("target_table", "").lower() != target_table.lower():
                continue
        pks = entry.get("primary_key_columns", [])
        pk_columns.extend(pks)

    # Deduplicate while preserving order
    seen = set()
    result = []
    for pk in pk_columns:
        pk_lower = pk.lower()
        if pk_lower not in seen:
            seen.add(pk_lower)
            result.append(pk)
    return result


def validate(transform_path, mapping_path, intent_path, target_table=None):
    """
    Main validation: check all PK columns for null-risk patterns.
    Returns list of violation dicts.
    """
    # Load PK columns
    pk_columns = get_pk_columns(intent_path, target_table)

    if not pk_columns:
        return []

    # Filter out audit columns — they are TargetWriter-managed, not PK candidates
    pk_columns = [pk for pk in pk_columns if pk.lower() not in AUDIT_COLUMNS]

    if not pk_columns:
        return []

    # Load transform code
    with open(transform_path, "r", encoding="utf-8") as f:
        code = f.read()
    code_lines = code.splitlines()

    # Parse join structures (needed for Check A)
    joins = extract_joins(code_lines)

    violations = []

    for pk_col in pk_columns:
        # Trace how this PK column is derived
        derivation = find_pk_derivation(pk_col, code_lines)

        # Check D first (if not found, skip other checks for this column)
        d_violation = check_pk_not_produced(pk_col, derivation)
        if d_violation:
            violations.append(d_violation)
            continue

        # Check A: LEFT JOIN nullable side
        a_violation = check_left_join_null_risk(pk_col, derivation, joins, code_lines)
        if a_violation:
            violations.append(a_violation)

        # Check B: F.when() without .otherwise()
        b_violation = check_when_without_otherwise(pk_col, derivation, code_lines)
        if b_violation:
            violations.append(b_violation)

        # Check C: UDF-derived (WARNING only)
        c_violation = check_udf_derived_pk(pk_col, derivation)
        if c_violation:
            violations.append(c_violation)

    return violations


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python validate_pk_null_risk.py <transform.py> "
            "<mapping_parsed.json> <intent_identification.json> "
            "[--target-table <name>]",
            file=sys.stderr,
        )
        sys.exit(2)

    transform_path = sys.argv[1]
    mapping_path = sys.argv[2]
    intent_path = sys.argv[3]
    target_table = None

    if "--target-table" in sys.argv:
        idx = sys.argv.index("--target-table")
        if idx + 1 < len(sys.argv):
            target_table = sys.argv[idx + 1]

    try:
        violations = validate(transform_path, mapping_path, intent_path, target_table)
    except FileNotFoundError as e:
        print(f"Error: File not found — {e}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON — {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if violations:
        print(json.dumps(violations, indent=2))
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
