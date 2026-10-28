#!/usr/bin/env python3
"""
OpenAPI Anomaly Analyzer
Analyzes generated OpenAPI files for constraint violations and E-02-02 pattern issues
"""
import yaml
import os
from pathlib import Path
from datetime import datetime
import sys

def create_result(result_type, **kwargs):
    """Factory function to create standardized result dictionaries"""
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
    # Add type-specific fields
    if result_type == 'regex-pattern':
        base['pattern'] = kwargs.get('pattern', '')[:50]
        base['validation_rule'] = 'E-02-02'
    return base

def analyze_yaml_file(file_path):
    """Analyze a YAML file for properties without proper constraints"""
    results = []

    try:
        with open(file_path, 'r') as f:
            content = yaml.safe_load(f)

        def check_property(prop_def, prop_name, file_name):
            """Check a single property definition"""
            if not isinstance(prop_def, dict):
                return

            # Skip $ref properties
            if '$ref' in prop_def:
                return

            prop_type = prop_def.get('type')

            # Check string properties
            if prop_type == 'string':
                has_enum = 'enum' in prop_def
                has_maxLength = 'maxLength' in prop_def
                has_minLength = 'minLength' in prop_def
                has_pattern = 'pattern' in prop_def

                # E-02-02: Check regex pattern compliance
                if has_pattern:
                    pattern_value = prop_def.get('pattern', '')
                    issues = []

                    # Must start with ^
                    if not pattern_value.startswith('^'):
                        issues.append('Pattern must start with ^')

                    # Must end with $ (best practice)
                    if not pattern_value.endswith('$'):
                        issues.append('Pattern should end with $')

                    # Must not use .* or .+ wildcards
                    if '.*' in pattern_value or '.+' in pattern_value:
                        issues.append('Pattern must not use .* or .+ wildcards')

                    # Must not contain forbidden characters as literals in character classes
                    import re
                    forbidden_literals = ['<', '>', ':', ';', '|', '%', '~']
                    char_classes = re.findall(r'\[([^\]]+)\]', pattern_value)
                    found_forbidden = []
                    for char_class in char_classes:
                        for char in forbidden_literals:
                            if char in char_class and char not in found_forbidden:
                                found_forbidden.append(char)
                    if found_forbidden:
                        issues.append(f"Contains forbidden characters: {', '.join(found_forbidden)}")

                    if issues:
                        results.append(create_result(
                            'regex-pattern',
                            file=file_name,
                            property_path=prop_name,
                            issue='; '.join(issues),
                            pattern=pattern_value,
                            description=prop_def.get('description', 'N/A')
                        ))

                # Check for complete string constraints
                # Rule: String must have maxLength AND minLength AND (pattern OR enum)
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
                            property_path=prop_name,
                            issue=f"Missing {', '.join(missing)}",
                            has_pattern='Yes' if has_pattern else 'No',
                            has_minLength='Yes' if has_minLength else 'No',
                            has_maxLength='Yes' if has_maxLength else 'No',
                            description=prop_def.get('description', 'N/A')
                        ))

            # Check integer/number properties
            elif prop_type in ['integer', 'number']:
                has_maximum = 'maximum' in prop_def
                has_minimum = 'minimum' in prop_def

                if not has_maximum or not has_minimum:
                    missing = []
                    if not has_maximum:
                        missing.append('maximum')
                    if not has_minimum:
                        missing.append('minimum')

                    results.append(create_result(
                        prop_type,
                        file=file_name,
                        property_path=prop_name,
                        issue=f"Missing {', '.join(missing)}",
                        description=prop_def.get('description', 'N/A')
                    ))

            # Check object properties recursively
            elif prop_type == 'object' and 'properties' in prop_def:
                for nested_name, nested_def in prop_def['properties'].items():
                    check_property(nested_def, f"{prop_name}.{nested_name}", file_name)

        # Start analysis
        file_name = os.path.basename(file_path)

        # Check root properties
        if isinstance(content, dict) and 'properties' in content:
            for prop_name, prop_def in content['properties'].items():
                check_property(prop_def, prop_name, file_name)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return results

def main():
    if len(sys.argv) > 1:
        oas_dir = sys.argv[1]
    else:
        oas_dir = "src/main/resources/oas"

    all_results = []

    # Find all YAML files
    yaml_files = list(Path(oas_dir).rglob("*.yaml"))
    print(f"Scanning {len(yaml_files)} YAML files in {oas_dir}...")

    for yaml_file in yaml_files:
        results = analyze_yaml_file(yaml_file)
        all_results.extend(results)

    # Sort by type, then file, then property
    all_results.sort(key=lambda x: (x['type'], x['file'], x['property_path']))

    # Print summary
    print(f"\n## OpenAPI Property Constraint Anomalies")
    print(f"Total findings: {len(all_results)}\n")

    # Write to MD file in project root directory
    project_root = Path.cwd()
    output_file = project_root / 'openapi-anomalies.md'

    with open(output_file, 'w') as f:
        f.write("# OpenAPI Anomalies\n\n")
        f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Project Directory**: {project_root}\n\n")
        f.write(f"**Files Scanned**: {len(yaml_files)}\n\n")
        f.write(f"**Total Anomalies Found**: {len(all_results)}\n\n")

        if all_results:
            f.write("## Issues Found\n\n")

            f.write("### String Properties Without Complete Constraints\n\n")
            string_issues = [r for r in all_results if r['type'] == 'string']
            if string_issues:
                f.write("**Barclays Requirement**: String properties must have `maxLength` AND `minLength` AND (`pattern` OR `enum`).\n\n")
                f.write("| File | Property Path | Missing Constraints | Has maxLength | Has minLength | Has Pattern | Description |\n")
                f.write("|------|---------------|---------------------|---------------|---------------|-------------|-------------|\n")
                for r in string_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | {r.get('has_maxLength', 'No')} | {r['has_minLength']} | {r['has_pattern']} | {desc} |\n")
            else:
                f.write("✅ All string properties have complete constraints.\n")

            f.write("\n### Numeric Properties Without Bounds\n\n")
            numeric_issues = [r for r in all_results if r['type'] in ['integer', 'number']]
            if numeric_issues:
                f.write("| File | Property Path | Type | Issue | Description |\n")
                f.write("|------|---------------|------|-------|-------------|\n")
                for r in numeric_issues:
                    desc = r['description'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['type']} | {r['issue']} | {desc} |\n")
            else:
                f.write("✅ All numeric properties have minimum and maximum.\n")

            f.write("\n### Regex Pattern Violations (E-02-02)\n\n")
            regex_issues = [r for r in all_results if r['type'] == 'regex-pattern']
            if regex_issues:
                f.write("**Barclays CSO Requirement**: Regex patterns must start with `^` and must not use `.\\*` or `.+` wildcards.\n\n")
                f.write("| File | Property Path | Issue | Current Pattern | Description |\n")
                f.write("|------|---------------|-------|-----------------|-------------|\n")
                for r in regex_issues:
                    desc = r['description'].replace('|', '\\|')
                    pattern = r['pattern'].replace('|', '\\|')
                    f.write(f"| {r['file']} | {r['property_path']} | {r['issue']} | `{pattern}` | {desc} |\n")
            else:
                f.write("✅ All regex patterns are compliant with E-02-02.\n")
        else:
            f.write("✅ **No anomalies found** - all properties have proper constraints.\n")

    print(f"✅ Analysis saved to: {output_file}")

    # Return exit code based on whether issues were found
    return len(all_results)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count == 0 else 1)
