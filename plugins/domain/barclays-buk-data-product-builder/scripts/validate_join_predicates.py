"""
Validate that generated PySpark transform join conditions and literal values
match the locked predicates from session/extracted_predicates.json.

Catches LLM deviations where:
- Symmetric join keys are assumed (A.x = B.x instead of A.x = B.y)
- Literal values are substituted based on column semantics ('V' instead of 'Y')

Usage:
    python validate_join_predicates.py <transform_file.py> <extracted_predicates.json> [--target-table <name>]

Exit codes:
    0 = all join predicates and literals valid
    1 = violations found (JSON printed to stdout)
    2 = usage/parse error
"""

import json
import re
import sys


def extract_join_conditions(code_lines):
    """
    Extract all .join() calls and their ON condition expressions from generated code.
    Returns list of {line, left_refs, right_refs, condition_text, join_df_name}.
    """
    joins = []

    # Multi-line join detection: scan for .join( and collect until closing )
    in_join = False
    join_start_line = 0
    paren_depth = 0
    join_buffer = ""

    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        if not in_join:
            # Look for .join( start
            join_match = re.search(r'\.join\(', line)
            if join_match:
                in_join = True
                join_start_line = idx + 1
                # Count parens from the match position onwards
                remainder = line[join_match.start():]
                paren_depth = remainder.count("(") - remainder.count(")")
                join_buffer = remainder
                if paren_depth <= 0:
                    # Single-line join
                    in_join = False
                    joins.append({
                        "line": join_start_line,
                        "text": join_buffer.strip(),
                    })
                    join_buffer = ""
        else:
            paren_depth += line.count("(") - line.count(")")
            join_buffer += " " + line.strip()
            if paren_depth <= 0:
                in_join = False
                joins.append({
                    "line": join_start_line,
                    "text": join_buffer.strip(),
                })
                join_buffer = ""

    # Parse each join's condition to extract column references
    parsed_joins = []
    for join_info in joins:
        text = join_info["text"]
        col_refs = extract_column_refs_from_condition(text)
        parsed_joins.append({
            "line": join_info["line"],
            "text": text,
            "col_refs": col_refs,
        })

    return parsed_joins


def extract_column_refs_from_condition(join_text):
    """
    Extract column references from a join condition expression.
    Returns list of (table_or_alias, column_name) tuples found in the condition.
    """
    refs = []

    # Pattern: df_name["col"] or df_name['col']
    for m in re.finditer(r'(\w+)\[["\']([\w.]+)["\']\]', join_text):
        alias = normalize_alias(m.group(1))
        col = m.group(2)
        refs.append((alias, col))

    # Pattern: F.col("alias.col") or F.col("col")
    for m in re.finditer(r'F\.col\(["\']([^"\']+)["\']\)', join_text):
        val = m.group(1)
        if "." in val:
            parts = val.split(".", 1)
            refs.append((parts[0].lower(), parts[1]))
        else:
            refs.append((None, val))

    # Pattern: df.col_name == other.col_name (attribute access in join)
    for m in re.finditer(r'(\w+)\.(\w+)\s*==\s*(\w+)\.(\w+)', join_text):
        left_alias = normalize_alias(m.group(1))
        left_col = m.group(2)
        right_alias = normalize_alias(m.group(3))
        right_col = m.group(4)
        # Only add if these look like column references (not method calls)
        if left_col[0].islower() and right_col[0].islower():
            if left_col not in ("join", "filter", "select", "col", "lit"):
                refs.append((left_alias, left_col))
            if right_col not in ("join", "filter", "select", "col", "lit"):
                refs.append((right_alias, right_col))

    # Pattern: .join(df, ["col"] or ["col1", "col2"]) — list syntax (symmetric keys)
    list_match = re.search(r'\.join\(\s*\w+\s*,\s*\[([^\]]+)\]', join_text)
    if list_match:
        cols_str = list_match.group(1)
        col_names = [c.strip().strip("'\"") for c in cols_str.split(",")]
        for col_name in col_names:
            refs.append(("__list_syntax__", col_name))

    return refs


def normalize_alias(df_name):
    """
    Normalize a DataFrame variable name to the source table alias.
    E.g., 'customer_response_df' → 'customer_response'
          'customer_response_filtered' → 'customer_response'
          'customer_response' → 'customer_response'
    """
    name = df_name.lower()
    # Strip common suffixes
    for suffix in ("_df", "_filtered", "_deduped", "_prepared", "_src", "_raw"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def check_join_predicates(parsed_joins, locked_predicates):
    """
    Verify that each locked join predicate is correctly represented in generated code.
    Returns list of violation dicts.
    """
    violations = []

    for pred in locked_predicates:
        left_table = pred["left_table"].lower()
        left_col = pred["left_col"].lower()
        right_table = pred["right_table"].lower()
        right_col = pred["right_col"].lower()
        source_text = pred.get("source_text", "")

        # Find the join that should contain this predicate
        found = False
        for join_info in parsed_joins:
            col_refs = join_info["col_refs"]
            if not col_refs:
                continue

            # Check if this join uses list syntax (valid for symmetric predicates)
            list_cols = [ref[1] for ref in col_refs if ref[0] == "__list_syntax__"]
            if list_cols:
                # List syntax valid IFF left_col == right_col and col is in the list
                if left_col == right_col and left_col in [c.lower() for c in list_cols]:
                    found = True
                    break

            # Check if both tables appear in this join's references
            aliases_in_join = {ref[0] for ref in col_refs if ref[0]}
            left_match = left_table in aliases_in_join
            right_match = right_table in aliases_in_join

            if not (left_match or right_match):
                continue

            # This join involves at least one of our tables — check the predicate
            # Look for left_col on left_table side
            left_col_found = any(
                ref[0] == left_table and ref[1].lower() == left_col
                for ref in col_refs
            )
            # Look for right_col on right_table side
            right_col_found = any(
                ref[0] == right_table and ref[1].lower() == right_col
                for ref in col_refs
            )

            if left_col_found and right_col_found:
                found = True
                break

            # Check for the SWAPPED case (wrong column on wrong side)
            # e.g., locked says A.x = B.y but code has A.x = B.x (used left col on right)
            wrong_right = any(
                ref[0] == right_table and ref[1].lower() == left_col
                for ref in col_refs
            )
            wrong_left = any(
                ref[0] == left_table and ref[1].lower() == right_col
                for ref in col_refs
            )

            if left_col_found and wrong_right and not right_col_found:
                # Right side uses left's column name — symmetric key assumption!
                violations.append({
                    "line": join_info["line"],
                    "type": "join_predicate_mismatch",
                    "locked": f"{pred['left_table']}.{pred['left_col']} {pred['operator']} {pred['right_table']}.{pred['right_col']}",
                    "issue": f"RIGHT side uses '{left_col}' but LOCKED specifies '{right_col}' "
                             f"(symmetric key assumption detected)",
                    "source_text": source_text,
                    "expected_right_col": pred["right_col"],
                    "actual_right_col": pred["left_col"],
                })
                found = True  # Don't also report as missing
                break

            if wrong_left and right_col_found and not left_col_found:
                violations.append({
                    "line": join_info["line"],
                    "type": "join_predicate_mismatch",
                    "locked": f"{pred['left_table']}.{pred['left_col']} {pred['operator']} {pred['right_table']}.{pred['right_col']}",
                    "issue": f"LEFT side uses '{right_col}' but LOCKED specifies '{left_col}' "
                             f"(column swap detected)",
                    "source_text": source_text,
                    "expected_left_col": pred["left_col"],
                    "actual_left_col": pred["right_col"],
                })
                found = True
                break

            # Partial match — one side correct, other side has different column
            if left_col_found and not right_col_found:
                # Find what column IS on the right side for this table
                right_cols_found = [
                    ref[1] for ref in col_refs if ref[0] == right_table
                ]
                actual_right = right_cols_found[0] if right_cols_found else "UNKNOWN"
                violations.append({
                    "line": join_info["line"],
                    "type": "join_predicate_mismatch",
                    "locked": f"{pred['left_table']}.{pred['left_col']} {pred['operator']} {pred['right_table']}.{pred['right_col']}",
                    "issue": f"RIGHT side uses '{actual_right}' but LOCKED specifies '{right_col}'",
                    "source_text": source_text,
                    "expected_right_col": pred["right_col"],
                    "actual_right_col": actual_right,
                })
                found = True
                break

            if right_col_found and not left_col_found:
                left_cols_found = [
                    ref[1] for ref in col_refs if ref[0] == left_table
                ]
                actual_left = left_cols_found[0] if left_cols_found else "UNKNOWN"
                violations.append({
                    "line": join_info["line"],
                    "type": "join_predicate_mismatch",
                    "locked": f"{pred['left_table']}.{pred['left_col']} {pred['operator']} {pred['right_table']}.{pred['right_col']}",
                    "issue": f"LEFT side uses '{actual_left}' but LOCKED specifies '{left_col}'",
                    "source_text": source_text,
                    "expected_left_col": pred["left_col"],
                    "actual_left_col": actual_left,
                })
                found = True
                break

        if not found:
            # Join predicate not found at all in generated code
            violations.append({
                "line": None,
                "type": "join_predicate_missing",
                "locked": f"{pred['left_table']}.{pred['left_col']} {pred['operator']} {pred['right_table']}.{pred['right_col']}",
                "issue": "Locked join predicate not found in generated code",
                "source_text": source_text,
            })

    return violations


def extract_literal_values(code_lines):
    """
    Extract literal comparison values from generated code.
    Returns list of {line, column, value, context, line_text}.
    """
    literals = []

    for idx, line in enumerate(code_lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        # F.col("col") == 'value' or == "value"
        for m in re.finditer(
            r'F\.col\(["\'](\w+)["\']\)\s*==\s*["\']([^"\']+)["\']', line
        ):
            literals.append({
                "line": idx + 1,
                "column": m.group(1),
                "value": m.group(2),
                "context": "filter_or_when",
                "line_text": line.strip(),
            })

        # F.col("col") == numeric
        for m in re.finditer(
            r'F\.col\(["\'](\w+)["\']\)\s*==\s*(\d+(?:\.\d+)?)\b', line
        ):
            literals.append({
                "line": idx + 1,
                "column": m.group(1),
                "value": m.group(2),
                "context": "filter_or_when",
                "line_text": line.strip(),
            })

        # df["col"] == 'value' or == "value"
        for m in re.finditer(
            r'\w+\[["\']([\w.]+)["\']\]\s*==\s*["\']([^"\']+)["\']', line
        ):
            literals.append({
                "line": idx + 1,
                "column": m.group(1),
                "value": m.group(2),
                "context": "filter_or_when",
                "line_text": line.strip(),
            })

        # .isin(["val1", "val2"]) or .isin(['val1', 'val2'])
        for m in re.finditer(r'F\.col\(["\'](\w+)["\']\).*?\.isin\(\[([^\]]+)\]\)', line):
            col = m.group(1)
            values_raw = m.group(2)
            values = [v.strip().strip("'\"") for v in values_raw.split(",")]
            literals.append({
                "line": idx + 1,
                "column": col,
                "value": values,
                "context": "isin",
                "line_text": line.strip(),
            })

        # ~F.col("col").isin([...]) — NOT IN
        for m in re.finditer(r'~\s*F\.col\(["\'](\w+)["\']\)\.isin\(\[([^\]]+)\]\)', line):
            col = m.group(1)
            values_raw = m.group(2)
            values = [v.strip().strip("'\"") for v in values_raw.split(",")]
            literals.append({
                "line": idx + 1,
                "column": col,
                "value": values,
                "context": "not_isin",
                "line_text": line.strip(),
            })

        # F.lit("value") with .alias context
        for m in re.finditer(r'F\.lit\(["\']([^"\']+)["\']\)', line):
            literals.append({
                "line": idx + 1,
                "column": None,
                "value": m.group(1),
                "context": "lit_assignment",
                "line_text": line.strip(),
            })

    return literals


def check_literal_values(code_literals, locked_literals):
    """
    Verify that locked literal values are correctly used in generated code.
    Returns list of violation dicts.
    """
    violations = []

    for locked in locked_literals:
        locked_col = locked.get("column")
        locked_value = locked.get("value")
        locked_operator = locked.get("operator", "=")
        source_text = locked.get("source_text", "")
        target_column = locked.get("target_column", "")

        if locked_col is None and locked_operator == "hardcode":
            # Check that F.lit(locked_value) appears somewhere
            found = any(
                lit["context"] == "lit_assignment"
                and _values_match(lit["value"], locked_value)
                for lit in code_literals
            )
            if not found:
                # Check if a DIFFERENT value is used as F.lit for this target
                wrong_lits = [
                    lit for lit in code_literals
                    if lit["context"] == "lit_assignment"
                    and not _values_match(lit["value"], locked_value)
                ]
                if wrong_lits:
                    violations.append({
                        "line": wrong_lits[0]["line"],
                        "type": "literal_value_mismatch",
                        "locked_value": locked_value,
                        "actual_value": wrong_lits[0]["value"],
                        "column": locked_col,
                        "target_column": target_column,
                        "issue": f"Hardcoded value '{wrong_lits[0]['value']}' does not match "
                                 f"locked value '{locked_value}'",
                        "source_text": source_text,
                    })
            continue

        if locked_col is None:
            continue

        locked_col_lower = locked_col.lower()

        # Find code literals that reference this column
        matching_code_lits = [
            lit for lit in code_literals
            if lit["column"] and lit["column"].lower() == locked_col_lower
        ]

        if not matching_code_lits:
            # Column not found in any literal comparison — may be okay
            # (could be in config-suppressed filter, or handled differently)
            continue

        # Check values
        if locked_operator in ("IN", "NOT IN"):
            # Locked value is a list
            expected_context = "isin" if locked_operator == "IN" else "not_isin"
            relevant = [
                lit for lit in matching_code_lits
                if lit["context"] in ("isin", "not_isin")
            ]
            for lit in relevant:
                if isinstance(lit["value"], list) and isinstance(locked_value, list):
                    if not _list_values_match(lit["value"], locked_value):
                        violations.append({
                            "line": lit["line"],
                            "type": "literal_value_mismatch",
                            "locked_value": locked_value,
                            "actual_value": lit["value"],
                            "column": locked_col,
                            "target_column": target_column,
                            "issue": f"IN/NOT IN values {lit['value']} do not match "
                                     f"locked values {locked_value}",
                            "source_text": source_text,
                        })
        else:
            # Single value comparison
            relevant = [
                lit for lit in matching_code_lits
                if lit["context"] == "filter_or_when"
            ]
            for lit in relevant:
                if not _values_match(lit["value"], locked_value):
                    violations.append({
                        "line": lit["line"],
                        "type": "literal_value_mismatch",
                        "locked_value": locked_value,
                        "actual_value": lit["value"],
                        "column": locked_col,
                        "target_column": target_column,
                        "issue": f"Value '{lit['value']}' does not match "
                                 f"locked value '{locked_value}'",
                        "source_text": source_text,
                    })

    return violations


def check_symmetric_key_ambiguity(parsed_joins):
    """Check 4: Detect expression-syntax joins where left_col == right_col."""
    violations = []
    for join_info in parsed_joins:
        col_refs = join_info["col_refs"]
        if not col_refs:
            continue
        # Skip list-syntax joins (already correct)
        if any(ref[0] == "__list_syntax__" for ref in col_refs):
            continue
        # Check for equality pairs with same column name
        for i in range(0, len(col_refs) - 1, 2):
            left_ref = col_refs[i]
            right_ref = col_refs[i + 1] if i + 1 < len(col_refs) else None
            if right_ref is None:
                continue
            left_alias, left_col = left_ref
            right_alias, right_col = right_ref
            if (left_col.lower() == right_col.lower() and
                    left_alias and right_alias and left_alias != right_alias):
                violations.append({
                    "line": join_info["line"],
                    "type": "symmetric_key_ambiguity",
                    "column": left_col,
                    "issue": f"Expression syntax for symmetric key '{left_col}' creates "
                             f"duplicate columns. Use list syntax ['{left_col}'] instead.",
                })
    return violations


def _values_match(actual, expected):
    """Compare values allowing for type coercion (string '123' vs int 123)."""
    if actual == expected:
        return True
    # String comparison (case-sensitive — intentional for literal fidelity)
    return str(actual) == str(expected)


def _list_values_match(actual_list, expected_list):
    """Compare two value lists (order-insensitive, case-sensitive)."""
    return sorted(str(v) for v in actual_list) == sorted(str(v) for v in expected_list)


def validate(transform_path, predicates_path, target_table=None):
    """
    Main validation: check join predicates and literal values against locked constraints.
    Returns list of violation dicts.
    """
    # Load extracted predicates
    with open(predicates_path, "r", encoding="utf-8") as f:
        predicates = json.load(f)

    locked_joins = predicates.get("join_predicates", [])
    locked_literals = predicates.get("literals", [])

    # Load transform code
    with open(transform_path, "r", encoding="utf-8") as f:
        code = f.read()
    code_lines = code.splitlines()

    violations = []

    # Check 1: Join predicate structure
    if locked_joins:
        parsed_joins = extract_join_conditions(code_lines)
        join_violations = check_join_predicates(parsed_joins, locked_joins)
        violations.extend(join_violations)

    # Check 2: Literal value fidelity
    if locked_literals:
        code_literals = extract_literal_values(code_lines)
        literal_violations = check_literal_values(code_literals, locked_literals)
        violations.extend(literal_violations)

    # Check 4: Symmetric key ambiguity detection (always runs)
    parsed_joins_all = extract_join_conditions(code_lines)
    ambiguity_violations = check_symmetric_key_ambiguity(parsed_joins_all)
    violations.extend(ambiguity_violations)

    return violations


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python validate_join_predicates.py <transform.py> "
            "<extracted_predicates.json> [--target-table <name>]",
            file=sys.stderr,
        )
        sys.exit(2)

    transform_path = sys.argv[1]
    predicates_path = sys.argv[2]
    target_table = None

    if "--target-table" in sys.argv:
        idx = sys.argv.index("--target-table")
        if idx + 1 < len(sys.argv):
            target_table = sys.argv[idx + 1]

    try:
        violations = validate(transform_path, predicates_path, target_table)
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
