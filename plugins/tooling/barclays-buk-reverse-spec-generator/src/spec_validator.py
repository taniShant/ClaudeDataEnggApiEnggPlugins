"""
spec_validator.py - Validates .spec file dictionaries against the reverse-spec-generator schema.

All validation is performed against the rules defined in format-reference.md:

- Required root fields: version, module, description
- Identifier naming: snake_case for module/behavior/rule/constraint/property names,
  PascalCase for entity names
- Content length: descriptions 10-500 characters
- Allowed property types: string, number, boolean, null, array, object
- Allowed constraint types: limit, invariant, dependency, timeout
- List sections must have at least 1 item when present
- given/when/then in behaviors: at least 1 non-empty string each
- Examples (if present): must have input and output fields
- Enums: non-empty, distinct values

Usage::

    from spec_validator import validate_spec, ValidationResult

    result = validate_spec(spec_dict, path="myfile.spec")
    if not result.valid:
        for error in result.errors:
            print(error)
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Identifier patterns
# ---------------------------------------------------------------------------

_SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_CAMEL_CASE_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")
_MAX_IDENTIFIER_LEN = 64

_ALLOWED_PROPERTY_TYPES = {"string", "number", "boolean", "null", "array", "object"}
_ALLOWED_CONSTRAINT_TYPES = {"limit", "invariant", "dependency", "timeout"}

_DESC_MIN_LEN = 10
_DESC_MAX_LEN = 500


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """
    Result of validating a spec file.

    Attributes:
        valid: True if no errors were found.
        errors: List of human-readable error messages.
        warnings: List of advisory (non-blocking) messages.
        path: Optional path of the file that was validated.
    """
    valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    path: Optional[str] = None

    def add_error(self, message: str) -> None:
        """Record an error and mark the result as invalid."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Record a non-blocking warning."""
        self.warnings.append(message)

    def summary(self) -> str:
        """Return a one-line summary of the validation outcome."""
        if self.valid:
            return f"OK: {self.path or '<spec>'}"
        return (
            f"INVALID: {self.path or '<spec>'} — "
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        )

    def __str__(self) -> str:
        parts = [self.summary()]
        for e in self.errors:
            parts.append(f"  ERROR  {e}")
        for w in self.warnings:
            parts.append(f"  WARN   {w}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Low-level field helpers
# ---------------------------------------------------------------------------

def _is_non_empty_string(value: object) -> bool:
    """Return True if value is a non-empty, non-whitespace-only string."""
    return isinstance(value, str) and bool(value.strip())


def _check_description(result: ValidationResult, desc: object,
                        context: str) -> None:
    """Validate a description field value and record any errors."""
    if not isinstance(desc, str):
        result.add_error(f"{context}: description must be a string (got {type(desc).__name__})")
        return
    stripped = desc.strip()
    if not stripped:
        result.add_error(f"{context}: description must not be empty or whitespace-only")
        return
    if len(stripped) < _DESC_MIN_LEN:
        result.add_error(
            f"{context}: description is too short "
            f"(min {_DESC_MIN_LEN} chars, got {len(stripped)})"
        )
    if len(stripped) > _DESC_MAX_LEN:
        result.add_error(
            f"{context}: description is too long "
            f"(max {_DESC_MAX_LEN} chars, got {len(stripped)})"
        )
    if desc != stripped:
        result.add_warning(
            f"{context}: description has leading/trailing whitespace"
        )


def _check_snake_case_name(result: ValidationResult, name: object,
                            context: str) -> bool:
    """
    Validate that name is a valid snake_case identifier.

    Returns True if valid, False otherwise (after recording the error).
    """
    if not isinstance(name, str):
        result.add_error(f"{context}: name must be a string (got {type(name).__name__})")
        return False
    if not name.strip():
        result.add_error(f"{context}: name must not be empty")
        return False
    if len(name) > _MAX_IDENTIFIER_LEN:
        result.add_error(
            f"{context}: name '{name}' exceeds max length of {_MAX_IDENTIFIER_LEN} chars"
        )
        return False
    if not _SNAKE_CASE_RE.match(name):
        result.add_error(
            f"{context}: name '{name}' must be snake_case "
            f"(lowercase letters, digits, underscores; must start with letter or underscore)"
        )
        return False
    return True


def _check_pascal_case_name(result: ValidationResult, name: object,
                             context: str) -> bool:
    """
    Validate that name is a valid PascalCase identifier.

    Returns True if valid, False otherwise (after recording the error).
    """
    if not isinstance(name, str):
        result.add_error(f"{context}: name must be a string (got {type(name).__name__})")
        return False
    if not name.strip():
        result.add_error(f"{context}: name must not be empty")
        return False
    if len(name) > _MAX_IDENTIFIER_LEN:
        result.add_error(
            f"{context}: name '{name}' exceeds max length of {_MAX_IDENTIFIER_LEN} chars"
        )
        return False
    if not _PASCAL_CASE_RE.match(name):
        result.add_error(
            f"{context}: name '{name}' must be PascalCase "
            f"(starts with uppercase letter, only letters and digits)"
        )
        return False
    return True


def _check_camel_case_name(result: ValidationResult, name: object,
                            context: str) -> None:
    """Validate that name is camelCase (used for entity property names)."""
    if not isinstance(name, str):
        result.add_error(f"{context}: name must be a string (got {type(name).__name__})")
        return
    if len(name) > _MAX_IDENTIFIER_LEN:
        result.add_error(
            f"{context}: name '{name}' exceeds max length of {_MAX_IDENTIFIER_LEN} chars"
        )
        return
    if not (_CAMEL_CASE_RE.match(name) or _SNAKE_CASE_RE.match(name)):
        result.add_warning(
            f"{context}: property name '{name}' is recommended to be camelCase "
            f"(starts with lowercase letter, only letters and digits)"
        )


def _check_non_empty_string_list(result: ValidationResult, lst: object,
                                  context: str, field_name: str) -> None:
    """Validate that a field is a list of at least one non-empty string."""
    if not isinstance(lst, list):
        result.add_error(
            f"{context}: '{field_name}' must be a list "
            f"(got {type(lst).__name__})"
        )
        return
    if len(lst) == 0:
        result.add_error(f"{context}: '{field_name}' must contain at least one item")
        return
    for i, item in enumerate(lst):
        if not isinstance(item, str):
            result.add_error(
                f"{context}: '{field_name}[{i}]' must be a string "
                f"(got {type(item).__name__})"
            )
        elif not item.strip():
            result.add_error(
                f"{context}: '{field_name}[{i}]' must not be empty or whitespace-only"
            )


# ---------------------------------------------------------------------------
# Section validators
# ---------------------------------------------------------------------------

def _validate_property(result: ValidationResult, prop: object,
                        entity_name: str, prop_idx: int) -> None:
    """Validate a single entity property dict."""
    ctx = f"entities['{entity_name}'].properties[{prop_idx}]"

    if not isinstance(prop, dict):
        result.add_error(f"{ctx}: each property must be a mapping (got {type(prop).__name__})")
        return

    # name
    _check_camel_case_name(result, prop.get("name", ""), ctx)

    # type
    ptype = prop.get("type")
    if ptype is None:
        result.add_error(f"{ctx}: 'type' is required")
    elif not isinstance(ptype, str):
        result.add_error(f"{ctx}: 'type' must be a string (got {type(ptype).__name__})")
    elif ptype.strip().lower() not in _ALLOWED_PROPERTY_TYPES:
        result.add_error(
            f"{ctx}: 'type' must be one of {sorted(_ALLOWED_PROPERTY_TYPES)} "
            f"(got '{ptype}')"
        )

    # description
    if "description" not in prop:
        result.add_error(f"{ctx}: 'description' is required")
    else:
        _check_description(result, prop["description"], ctx)

    # required (optional boolean)
    if "required" in prop and not isinstance(prop["required"], bool):
        result.add_error(
            f"{ctx}: 'required' must be a boolean "
            f"(got {type(prop['required']).__name__})"
        )

    # enum (optional, non-empty, distinct)
    if "enum" in prop:
        enum_val = prop["enum"]
        if not isinstance(enum_val, list):
            result.add_error(f"{ctx}: 'enum' must be a list")
        elif len(enum_val) == 0:
            result.add_error(f"{ctx}: 'enum' must contain at least one value")
        else:
            seen = set()
            for ev in enum_val:
                ev_str = str(ev)
                if ev_str in seen:
                    result.add_error(f"{ctx}: 'enum' contains duplicate value '{ev}'")
                seen.add(ev_str)


def _validate_entity(result: ValidationResult, entity: object,
                      entity_idx: int) -> None:
    """Validate a single entity dict."""
    ctx = f"entities[{entity_idx}]"

    if not isinstance(entity, dict):
        result.add_error(f"{ctx}: each entity must be a mapping (got {type(entity).__name__})")
        return

    # name – PascalCase
    name = entity.get("name", "")
    name_ok = _check_pascal_case_name(result, name, ctx)
    if name_ok:
        ctx = f"entities['{name}']"

    # description
    if "description" not in entity:
        result.add_error(f"{ctx}: 'description' is required")
    else:
        _check_description(result, entity["description"], ctx)

    # properties – required when entity is defined
    if "properties" not in entity:
        result.add_error(f"{ctx}: 'properties' is required")
    elif not isinstance(entity["properties"], list):
        result.add_error(f"{ctx}: 'properties' must be a list")
    elif len(entity["properties"]) == 0:
        result.add_error(f"{ctx}: 'properties' must contain at least one item")
    else:
        for idx, prop in enumerate(entity["properties"]):
            _validate_property(result, prop, name or str(entity_idx), idx)


def _validate_behavior(result: ValidationResult, behavior: object,
                        beh_idx: int) -> None:
    """Validate a single behavior dict."""
    ctx = f"behaviors[{beh_idx}]"

    if not isinstance(behavior, dict):
        result.add_error(f"{ctx}: each behavior must be a mapping (got {type(behavior).__name__})")
        return

    # name – snake_case
    name = behavior.get("name", "")
    name_ok = _check_snake_case_name(result, name, ctx)
    if name_ok:
        ctx = f"behaviors['{name}']"

    # description
    if "description" not in behavior:
        result.add_error(f"{ctx}: 'description' is required")
    else:
        _check_description(result, behavior["description"], ctx)

    # given / when / then – all required, at least one item each
    for field_name in ("given", "when", "then"):
        if field_name not in behavior:
            result.add_error(f"{ctx}: '{field_name}' is required")
        else:
            _check_non_empty_string_list(result, behavior[field_name], ctx, field_name)

    # examples – optional
    if "examples" in behavior:
        examples = behavior["examples"]
        if not isinstance(examples, list):
            result.add_error(f"{ctx}: 'examples' must be a list")
        else:
            for i, ex in enumerate(examples):
                ex_ctx = f"{ctx}.examples[{i}]"
                if not isinstance(ex, dict):
                    result.add_error(
                        f"{ex_ctx}: each example must be a mapping "
                        f"(got {type(ex).__name__})"
                    )
                    continue
                for required_field in ("input", "output"):
                    if required_field not in ex:
                        result.add_error(
                            f"{ex_ctx}: '{required_field}' is required"
                        )
                    elif not _is_non_empty_string(str(ex[required_field])):
                        result.add_error(
                            f"{ex_ctx}: '{required_field}' must be a non-empty string"
                        )


def _validate_rule(result: ValidationResult, rule: object,
                   rule_idx: int) -> None:
    """Validate a single rule dict."""
    ctx = f"rules[{rule_idx}]"

    if not isinstance(rule, dict):
        result.add_error(f"{ctx}: each rule must be a mapping (got {type(rule).__name__})")
        return

    # name – snake_case
    name = rule.get("name", "")
    name_ok = _check_snake_case_name(result, name, ctx)
    if name_ok:
        ctx = f"rules['{name}']"

    # description
    if "description" not in rule:
        result.add_error(f"{ctx}: 'description' is required")
    else:
        _check_description(result, rule["description"], ctx)

    # condition
    if "condition" not in rule:
        result.add_error(f"{ctx}: 'condition' is required")
    elif not _is_non_empty_string(rule["condition"]):
        result.add_error(f"{ctx}: 'condition' must be a non-empty string")

    # action
    if "action" not in rule:
        result.add_error(f"{ctx}: 'action' is required")
    elif not _is_non_empty_string(rule["action"]):
        result.add_error(f"{ctx}: 'action' must be a non-empty string")


def _validate_constraint(result: ValidationResult, constraint: object,
                          cons_idx: int) -> None:
    """Validate a single constraint dict."""
    ctx = f"constraints[{cons_idx}]"

    if not isinstance(constraint, dict):
        result.add_error(
            f"{ctx}: each constraint must be a mapping (got {type(constraint).__name__})"
        )
        return

    # name – snake_case
    name = constraint.get("name", "")
    name_ok = _check_snake_case_name(result, name, ctx)
    if name_ok:
        ctx = f"constraints['{name}']"

    # description
    if "description" not in constraint:
        result.add_error(f"{ctx}: 'description' is required")
    else:
        _check_description(result, constraint["description"], ctx)

    # type
    ctype = constraint.get("type")
    if ctype is None:
        result.add_error(f"{ctx}: 'type' is required")
    elif not isinstance(ctype, str):
        result.add_error(f"{ctx}: 'type' must be a string (got {type(ctype).__name__})")
    elif ctype not in _ALLOWED_CONSTRAINT_TYPES:
        result.add_error(
            f"{ctx}: 'type' must be one of {sorted(_ALLOWED_CONSTRAINT_TYPES)} "
            f"(got '{ctype}')"
        )

    # value
    if "value" not in constraint:
        result.add_error(f"{ctx}: 'value' is required")
    elif not _is_non_empty_string(str(constraint["value"])):
        result.add_error(f"{ctx}: 'value' must be a non-empty string")


# ---------------------------------------------------------------------------
# Root-level section list validator
# ---------------------------------------------------------------------------

def _validate_section_list(result: ValidationResult, spec: dict,
                             section: str, item_validator,
                             min_items: int = 1) -> None:
    """
    Validate a top-level list section (entities, behaviors, rules, constraints).

    Args:
        result: ValidationResult to append errors/warnings to.
        spec: Root spec dictionary.
        section: Key name of the section.
        item_validator: Callable(result, item, index) for each list item.
        min_items: Minimum number of items required when the section is present.
    """
    if section not in spec:
        return  # Optional section; absence is fine
    items = spec[section]
    if not isinstance(items, list):
        result.add_error(f"'{section}' must be a list (got {type(items).__name__})")
        return
    if len(items) < min_items:
        result.add_error(
            f"'{section}' must contain at least {min_items} item(s) when present"
        )
        return
    for idx, item in enumerate(items):
        item_validator(result, item, idx)


# ---------------------------------------------------------------------------
# YAML format validator (works on raw text)
# ---------------------------------------------------------------------------

def validate_yaml_format(text: str) -> list:
    """
    Check raw YAML text for format compliance (encoding, line endings, indentation).

    This does not parse the YAML; it performs mechanical checks that would be
    lost after parsing.

    Args:
        text: Raw file text (already decoded to str).

    Returns:
        List of format error strings.  Empty list means format is compliant.
    """
    errors = []

    # LF line endings – detect CR
    if "\r\n" in text or "\r" in text:
        errors.append("File must use LF (Unix) line endings, not CRLF or CR")

    lines = text.split("\n")
    for i, line in enumerate(lines, start=1):
        # Trailing whitespace
        if line != line.rstrip():
            errors.append(f"Line {i}: trailing whitespace")
        # Tabs
        if "\t" in line:
            errors.append(f"Line {i}: tab character found; use 2-space indentation")
        # Indentation must be a multiple of 2
        stripped = line.lstrip(" ")
        n_spaces = len(line) - len(stripped)
        if stripped and n_spaces % 2 != 0:
            errors.append(
                f"Line {i}: odd indentation ({n_spaces} space(s)); "
                f"must use 2-space increments"
            )

    return errors


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def validate_spec(spec: dict, path: Optional[str] = None,
                  raw_text: Optional[str] = None) -> ValidationResult:
    """
    Validate a parsed spec dictionary against the reverse-spec-generator schema.

    Args:
        spec: Parsed spec dictionary (e.g. from spec_serializer.load_spec).
        path: Optional file path for richer error messages.
        raw_text: Optional raw file text for YAML format validation.

    Returns:
        ValidationResult with valid flag, errors list, and warnings list.
    """
    result = ValidationResult(path=path)

    if not isinstance(spec, dict):
        result.add_error("Spec must be a YAML mapping at the root level")
        return result

    # --- Raw format checks --------------------------------------------------
    if raw_text is not None:
        for fmt_error in validate_yaml_format(raw_text):
            result.add_error(fmt_error)

    # --- version ------------------------------------------------------------
    version = spec.get("version")
    if version is None:
        result.add_error("Required field 'version' is missing")
    elif str(version) != "1.0":
        result.add_error(
            f"'version' must be \"1.0\" (got '{version}')"
        )

    # --- module -------------------------------------------------------------
    module = spec.get("module")
    if module is None:
        result.add_error("Required field 'module' is missing")
    else:
        _check_snake_case_name(result, module, "'module'")

    # --- description --------------------------------------------------------
    description = spec.get("description")
    if description is None:
        result.add_error("Required field 'description' is missing")
    else:
        _check_description(result, description, "'description'")

    # --- At least one optional section must be present ----------------------
    optional_sections = {"entities", "behaviors", "rules", "constraints"}
    present_sections = optional_sections & set(spec.keys())
    if not present_sections:
        result.add_error(
            "Spec must define at least one of: entities, behaviors, rules, constraints"
        )

    # --- entities -----------------------------------------------------------
    _validate_section_list(result, spec, "entities", _validate_entity)

    # --- behaviors ----------------------------------------------------------
    _validate_section_list(result, spec, "behaviors", _validate_behavior)

    # --- rules --------------------------------------------------------------
    _validate_section_list(result, spec, "rules", _validate_rule)

    # --- constraints --------------------------------------------------------
    _validate_section_list(result, spec, "constraints", _validate_constraint)

    # --- Unknown top-level keys (advisory) ----------------------------------
    known_keys = {"version", "module", "description",
                  "entities", "behaviors", "rules", "constraints"}
    for key in spec:
        if key not in known_keys:
            result.add_warning(f"Unknown top-level field '{key}' will be ignored")

    return result


def validate_spec_file(path: str) -> ValidationResult:
    """
    Load and validate a .spec file from disk, including format checks.

    This is a convenience wrapper that handles file I/O and wires in
    raw_text so that YAML format violations are also reported.

    Args:
        path: Filesystem path to the .spec file.

    Returns:
        ValidationResult with all errors and warnings found.
    """
    # Deferred import to avoid a hard dependency; spec_serializer lives in
    # the same package.
    try:
        from spec_serializer import load_spec, parse_yaml, _YAMLParseError
    except ImportError:
        # Fallback when run from the validator directory
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        from spec_serializer import load_spec, parse_yaml, _YAMLParseError

    result = ValidationResult(path=path)

    from pathlib import Path
    file_path = Path(path)

    if not file_path.exists():
        result.add_error(f"File not found: {path}")
        return result

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        result.add_error(f"File is not valid UTF-8: {exc}")
        return result

    try:
        spec = parse_yaml(raw_text)
    except _YAMLParseError as exc:
        result.add_error(f"YAML parse error: {exc}")
        return result
    except Exception as exc:
        result.add_error(f"Unexpected parse error: {exc}")
        return result

    # Merge with a fresh ValidationResult that carries the path
    full_result = validate_spec(spec, path=path, raw_text=raw_text)
    return full_result
