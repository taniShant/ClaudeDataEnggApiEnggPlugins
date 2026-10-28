#!/usr/bin/env python3
"""
OpenAPI Anomaly Analyzer
Analyzes generated OpenAPI files for constraint violations and regex pattern issues.

Regex compliance rules follow Barclays CISO policy:
  https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns
"""
import yaml
import os
import re as _re
from pathlib import Path
from datetime import datetime
import sys

def create_result(result_type, **kwargs):
    base = {
        'file': kwargs.get('file', ''),
        'property_path': kwargs.get('property_path', ''),
        'type': result_type,
        'issue': kwargs.get('issue', ''),
        'has_pattern': kwargs.get('has_pattern', 'N/A'),
        'has_minLength': kwargs.get('has_minLength', 'N/A'),
        'has_maxLength': kwargs.get('has_maxLength', 'N/A'),
        'description': kwargs.get('description', 'N/A')[:100]
    }
    if result_type == 'regex-pattern':
        base['pattern'] = kwargs.get('pattern', '')[:50]
        base['validation_rule'] = 'ASC/596524483'
    return base


# CSO-approved patterns with RFC exemptions — exempt from standard checks
_CSO_APPROVED_PATTERNS = {
    # Email: RFC 5321/5322 exemption — % ? ~ + permitted in local-part.
    # IMPORTANT: This exact pattern is also defined in references/design-oas/reference/rules.md
    # under "String Properties → Email". Update BOTH if CSO revises the approved pattern.
    # CSO reference: https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns
    r'^(?=.{1,256}$)^([a-zA-Z0-9.!#$%&\'*+\/=?^_`~-]{1,64})@(([a-zA-Z0-9-]{1,180}(\.[a-zA-Z0-9-]{1,62}){1,9}))$',
}


def check_regex_compliance(pattern_value):
    """
    Check a regex pattern against Barclays CISO policy.
    Reference: https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns

    CSO-approved patterns (e.g. email with RFC exemptions) skip all checks.
    Returns a list of issue strings (empty = compliant).
    """
    if pattern_value in _CSO_APPROVED_PATTERNS:
        return []

    issues = []

    # 1. Must start with ^
    if not pattern_value.startswith('^'):
        issues.append('Pattern must start with ^')

    # 2. Must end with $
    if not pattern_value.endswith('$'):
        issues.append('Pattern must end with $')

    # 3. .* and .+ are dangerous wildcards — must never be used
    #    Strip character classes first to avoid false positives on [.+] or [.*]
    _stripped_for_wildcard = _re.sub(r'\[[^\]]*\]', '', pattern_value)
    if '.*' in _stripped_for_wildcard or '.+' in _stripped_for_wildcard:
        issues.append('Pattern uses .* or .+ wildcard — must never be used')

    # 4. Bare . outside character class/group must be escaped as \.
    #    e.g. ^([a-z].[A-Z])$ is bad — the . matches anything
    stripped_classes = _re.sub(r'\[[^\]]*\]', '', pattern_value)   # remove char classes
    stripped_groups  = _re.sub(r'\([^)]*\)',  '', stripped_classes) # remove groups
    bare_dot = _re.sub(r'\\\.', '', stripped_groups)                # remove escaped dots
    if '.' in bare_dot:
        issues.append('Bare . outside character class matches any character — escape as \\. or move inside []')

    # 5. + or * outside character classes — greedy, conflicts with min/max
    #    Per Confluence ASC/596524483: use {n,m} instead of + or *
    #    Strip char classes and quantifiers first, then check for bare + or *
    stripped = _re.sub(r'\[[^\]]*\]', '', pattern_value)   # remove char classes
    stripped = _re.sub(r'\{[^}]*\}',  '', stripped)        # remove {n,m} quantifiers
    stripped = _re.sub(r'\\\+|\\\*', '', stripped)         # remove escaped + and *
    stripped = _re.sub(r'\([^)]*\)',  '', stripped)        # remove groups (innermost first)
    if _re.search(r'[+*]', stripped):
        issues.append('Pattern uses + or * outside character class — use {n,m} bounded quantifier instead')

    # 6. {n,} with no upper bound — forbidden
    if _re.search(r'\{\d+,\s*\}', pattern_value):
        issues.append('Pattern uses {n,} with no upper bound — always specify a maximum')

    # 7. Forbidden mixed-case ranges: [A-z], [Z-a], [A-a], [a-Z] etc.
    #    These pass unsafe characters in ASCII 90–97 range ([ \ ] ^ _ `)
    if _re.search(r'\[[^\]]*[A-Z]-[a-z][^\]]*\]|\[[^\]]*[a-z]-[A-Z][^\]]*\]', pattern_value):
        issues.append('Forbidden mixed-case range (e.g. [A-z]) — allows unsafe characters in ASCII 90-97')

    # 8. Dangerous uppercase meta-characters inside character classes
    #    [\S] matches any non-whitespace, [\W] matches any non-word, [\D] matches any non-digit
    if _re.search(r'\[(?:[^\]]*\\[SWD][^\]]*)\]', pattern_value):
        issues.append('Dangerous meta-character \\S, \\W or \\D inside character class — matches too broadly')

    # 9. Forbidden literal characters inside character classes
    #    Per ASC policy: < > | % : ; ? ~
    #    Exception: email fields have CSO exemption for % ? ~ + per RFC 5321/5322
    #    We flag all here; email pattern is pre-approved and exempt
    forbidden_in_class = ['<', '>', '|', '%', ':', ';', '?', '~']
    char_classes = _re.findall(r'\[([^\]]+)\]', pattern_value)
    found_forbidden = []
    for char_class in char_classes:
        for char in forbidden_in_class:
            if char in char_class and char not in found_forbidden:
                found_forbidden.append(char)
    if found_forbidden:
        issues.append(f"Forbidden characters in character class: {', '.join(found_forbidden)} — requires CSO exemption")

    # 10. Symbol ranges between non-alphanumeric chars — e.g. [ -/] allows space(32) to /(47)
    #     Only flag ranges where BOTH ends are non-alphanumeric, non-underscore symbols.
    #     Safe ranges: a-z, A-Z, 0-9. Unsafe: space-/, !-@, etc.
    for char_class_content in _re.findall(r'\[([^\]]*)\]', pattern_value):
        symbol_ranges = _re.findall(r'([ !-/:-@\[-`{-~])-([ !-/:-@\[-`{-~])', char_class_content)
        if symbol_ranges:
            issues.append(f'Symbol range in character class allows unsafe characters: {symbol_ranges}')

    # 11a. Escaped hyphen \- inside character class is ambiguous.
    #      Some scanners interpret [\-'] as a range from \ (ASCII 92) to ' (ASCII 39).
    #      Rule: never use \- inside []; place the hyphen at the END of the class instead.
    #      Detect: \- appearing inside any character class [ ... ]
    char_classes = _re.findall(r'\[[^\]]+\]', pattern_value)
    for cls in char_classes:
        cls_inner = cls[1:-1]  # strip [ and ]
        if _re.search(r'\\-', cls_inner):
            issues.append(
                r'Escaped hyphen \- inside character class is ambiguous — '
                r'place hyphen at END of class instead: [abc-] not [ab\-c]'
            )
            break

    # 11. ReDoS-prone patterns: (a+)+  ([a-zA-Z]+)*  (a|aa)+  (a|a?)+
    redos_patterns = [
        (r'\([^)]+\+\)\+', '(X+)+ pattern causes ReDoS'),
        (r'\([^)]+\]\+\)\*', '([...]+)* pattern causes ReDoS'),
        (r'\([^|)]+\|[^|)]+\)\+', '(X|Y)+ pattern may cause ReDoS'),
    ]
    for redos_re, msg in redos_patterns:
        if _re.search(redos_re, pattern_value):
            issues.append(msg)

    # 12. Positive lookahead (?=...) — should be avoided per policy
    if '(?=' in pattern_value:
        issues.append('Positive lookahead (?=...) should be avoided — use {n,m} quantifiers instead')

    return issues


def analyze_yaml_file(file_path):
    results = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)

        def walk(schema, path, file_name, visited=None):
            """
            Depth-first walker. Handles:
              - type: string / integer / number  — check constraints
              - type: object with properties     — recurse into each property
              - allOf / anyOf / oneOf            — recurse into each sub-schema
              - $ref                             — skip (resolved at runtime)
              - array items                      — recurse into items schema
            Uses `visited` set to guard against circular $ref chains.
            """
            if not isinstance(schema, dict):
                return
            if visited is None:
                visited = set()

            # Skip $ref — resolved at runtime, not our job to follow here
            if '$ref' in schema:
                return

            # Cycle guard for inline re-use
            schema_id = id(schema)
            if schema_id in visited:
                return
            visited.add(schema_id)

            prop_type = schema.get('type')

            # --- string ---
            if prop_type == 'string':
                has_enum = 'enum' in schema
                has_maxLength = 'maxLength' in schema
                has_minLength = 'minLength' in schema
                has_pattern = 'pattern' in schema

                if has_pattern:
                    pattern_value = schema.get('pattern', '')
                    issues = check_regex_compliance(pattern_value)
                    if issues:
                        results.append(create_result(
                            'regex-pattern',
                            file=file_name,
                            property_path=path,
                            issue='; '.join(issues),
                            pattern=pattern_value,
                            description=schema.get('description', 'N/A')
                        ))

                # Enum exemption — canonical definition in rules.md (String Properties section):
                # enum fields need NO other constraints (no minLength/maxLength/pattern)
                if not has_enum:
                    missing = []
                    if not has_maxLength:
                        missing.append('maxLength')
                    if not has_minLength:
                        missing.append('minLength')
                    if not has_pattern:
                        missing.append('pattern')
                    if missing:
                        results.append(create_result(
                            'string',
                            file=file_name,
                            property_path=path,
                            issue=f"Missing {', '.join(missing)}",
                            has_pattern='Yes' if has_pattern else 'No',
                            has_minLength='Yes' if has_minLength else 'No',
                            has_maxLength='Yes' if has_maxLength else 'No',
                            description=schema.get('description', 'N/A')
                        ))

            # --- integer / number ---
            elif prop_type in ['integer', 'number']:
                has_maximum = 'maximum' in schema
                has_minimum = 'minimum' in schema
                if not has_maximum or not has_minimum:
                    missing = []
                    if not has_maximum:
                        missing.append('maximum')
                    if not has_minimum:
                        missing.append('minimum')
                    results.append(create_result(
                        prop_type,
                        file=file_name,
                        property_path=path,
                        issue=f"Missing {', '.join(missing)}",
                        description=schema.get('description', 'N/A')
                    ))

            # --- boolean ---
            elif prop_type == 'boolean':
                has_deprecated = 'deprecated' in schema
                has_nullable = 'nullable' in schema
                if not has_deprecated or not has_nullable:
                    missing = []
                    if not has_deprecated:
                        missing.append('deprecated')
                    if not has_nullable:
                        missing.append('nullable')
                    results.append(create_result(
                        'boolean',
                        file=file_name,
                        property_path=path,
                        issue=f"Missing {', '.join(missing)}",
                        description=schema.get('description', 'N/A')
                    ))

            # --- object: recurse into properties ---
            if prop_type == 'object' or 'properties' in schema:
                for prop_name, prop_def in schema.get('properties', {}).items():
                    walk(prop_def, f"{path}.{prop_name}", file_name, visited)

            # --- array: check minItems/maxItems + recurse into items ---
            if prop_type == 'array':
                has_minItems = 'minItems' in schema
                has_maxItems = 'maxItems' in schema
                if not has_minItems or not has_maxItems:
                    missing = []
                    if not has_minItems:
                        missing.append('minItems')
                    if not has_maxItems:
                        missing.append('maxItems')
                    results.append(create_result(
                        'array',
                        file=file_name,
                        property_path=path,
                        issue=f"Missing {', '.join(missing)}",
                        description=schema.get('description', 'N/A')
                    ))
                if 'items' in schema:
                    walk(schema['items'], f"{path}[]", file_name, visited)

            # --- allOf / anyOf / oneOf: recurse into each sub-schema ---
            for combiner in ('allOf', 'anyOf', 'oneOf'):
                for i, sub_schema in enumerate(schema.get(combiner, [])):
                    walk(sub_schema, f"{path}[{combiner}[{i}]]", file_name, visited)

        file_name = os.path.basename(file_path)

        if isinstance(content, dict):
            # Case 1: root has 'properties' directly (inline/flat schema)
            if 'properties' in content or any(k in content for k in ('allOf', 'anyOf', 'oneOf')):
                for prop_name, prop_def in content.get('properties', {}).items():
                    walk(prop_def, prop_name, file_name)
                for combiner in ('allOf', 'anyOf', 'oneOf'):
                    for i, sub_schema in enumerate(content.get(combiner, [])):
                        walk(sub_schema, f"[{combiner}[{i}]]", file_name)
            else:
                # Case 2: Barclays named-root format — root keys are schema names
                # e.g. { OpenAccountRequest: { type: object, properties: {...} } }
                for schema_name, schema_def in content.items():
                    if isinstance(schema_def, dict):
                        walk(schema_def, schema_name, file_name)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return results


def main():
    if len(sys.argv) > 1:
        oas_dir = sys.argv[1]
    else:
        oas_dir = "src/main/resources/oas"

    all_results = []

    # Skip openapi.yaml — it uses OAS path structure, not Barclays component schema format.
    # Inline parameter schemas in openapi.yaml are checked manually via G9 at Step 8.
    yaml_files = [f for f in Path(oas_dir).rglob("*.yaml") if f.name != "openapi.yaml"]
    print(f"Scanning {len(yaml_files)} component YAML files in {oas_dir}...")

    for yaml_file in yaml_files:
        results = analyze_yaml_file(yaml_file)
        all_results.extend(results)

    all_results.sort(key=lambda x: (x['type'], x['file'], x['property_path']))

    print(f"\n## OpenAPI Property Constraint Anomalies")
    print(f"Total findings: {len(all_results)}\n")

    # Write report to the scanned directory, not CWD
    output_dir = Path(oas_dir)
    output_file = output_dir / 'openapi-anomalies.md'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# OpenAPI Anomalies\n\n")
        f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Output Directory**: {output_dir}\n\n")
        f.write(f"**Files Scanned**: {len(yaml_files)}\n\n")
        f.write(f"**Total Anomalies Found**: {len(all_results)}\n\n")
        f.write("**Regex policy**: https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns\n\n")

        if all_results:
            f.write("## Issues Found\n\n")

            f.write("### String Properties Without Complete Constraints\n\n")
            string_issues = [r for r in all_results if r['type'] == 'string']
            if string_issues:
                f.write("**Rule**: Non-enum string properties must have `maxLength` + `minLength` + `pattern`. Enum fields need no other constraints.\n\n")
                f.write("| File | Property Path | Missing Constraints | Has maxLength | Has minLength | Has Pattern | Description |\n")
                f.write("|------|---------------|---------------------|---------------|---------------|-------------|-------------|\n")
                for r in string_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | {r.get('has_maxLength', 'No')} | {r['has_minLength']} | {r['has_pattern']} | {desc} |\n")
            else:
                f.write("OK All string properties have complete constraints.\n")

            f.write("\n### Array Properties Without Item Bounds\n\n")
            array_issues = [r for r in all_results if r['type'] == 'array']
            if array_issues:
                f.write("| File | Property Path | Issue | Description |\n")
                f.write("|------|---------------|-------|-------------|\n")
                for r in array_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | {desc} |\n")
            else:
                f.write("OK All array properties have minItems and maxItems.\n")

            f.write("\n### Boolean Properties Missing deprecated/nullable\n\n")
            boolean_issues = [r for r in all_results if r['type'] == 'boolean']
            if boolean_issues:
                f.write("**Rule**: Boolean properties must have `deprecated: false` and `nullable: false`.\n\n")
                f.write("| File | Property Path | Issue | Description |\n")
                f.write("|------|---------------|-------|-------------|\n")
                for r in boolean_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | {desc} |\n")
            else:
                f.write("OK All boolean properties have deprecated and nullable.\n")

            f.write("\n### Numeric Properties Without Bounds\n\n")
            numeric_issues = [r for r in all_results if r['type'] in ['integer', 'number']]
            if numeric_issues:
                f.write("| File | Property Path | Type | Issue | Description |\n")
                f.write("|------|---------------|------|-------|-------------|\n")
                for r in numeric_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['type']} | {r['issue']} | {desc} |\n")
            else:
                f.write("OK All numeric properties have minimum and maximum.\n")

            f.write("\n### Regex Pattern Violations\n\n")
            regex_issues = [r for r in all_results if r['type'] == 'regex-pattern']
            if regex_issues:
                f.write("**Policy**: https://confluence.barcapint.com/spaces/ASC/pages/596524483/REGEX+Examples+and+Patterns\n\n")
                f.write("| File | Property Path | Issue | Current Pattern | Description |\n")
                f.write("|------|---------------|-------|-----------------|-------------|\n")
                for r in regex_issues:
                    desc = r['description'].replace('|', '\\|')
                    pattern = r['pattern'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | `{pattern}` | {desc} |\n")
            else:
                f.write("OK All regex patterns comply with Barclays CISO policy.\n")
        else:
            f.write("OK **No anomalies found** - all properties have proper constraints.\n")

    print(f"OK Analysis saved to: {output_file}")

    return len(all_results)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
