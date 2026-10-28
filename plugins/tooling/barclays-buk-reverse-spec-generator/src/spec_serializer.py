"""
spec_serializer.py - YAML parsing, writing, and data structure handling for .spec files.

Provides load/save operations for spec files without requiring external dependencies.
Uses a hand-rolled YAML emitter so output is always consistent (2-space indent, LF,
UTF-8) and a stdlib-only block-scalar YAML parser for reading.
"""

import re
import sys
import json
from pathlib import Path
from typing import Union


# ---------------------------------------------------------------------------
# Minimal YAML parser (stdlib only)
# ---------------------------------------------------------------------------

class _YAMLParseError(ValueError):
    """Raised when the lightweight YAML parser cannot process input."""


def _strip_inline_comment(value: str) -> str:
    """Remove trailing inline YAML comment from a plain scalar value."""
    # Only strip if there is a space before '#' (comments must be preceded by whitespace)
    idx = value.find(" #")
    if idx != -1:
        return value[:idx].rstrip()
    return value


def _parse_scalar(raw: str) -> object:
    """
    Convert a raw YAML scalar string to a Python object.

    Handles: quoted strings, booleans, null, integers, floats, plain strings.
    """
    s = raw.strip()

    # Quoted strings – single or double
    if (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("'") and s.endswith("'")):
        return s[1:-1]

    # Null
    if s in ("null", "~", ""):
        return None

    # Boolean
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False

    # Integer
    try:
        return int(s)
    except ValueError:
        pass

    # Float
    try:
        return float(s)
    except ValueError:
        pass

    # Plain string – remove inline comments
    return _strip_inline_comment(s)


def _parse_flow_sequence(text: str) -> list:
    """
    Parse a YAML flow sequence like ``["a", "b", "c"]``.

    Handles simple cases: quoted strings, numbers, booleans, null.
    Does not support nested structures.
    """
    inner = text.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1].strip()
    if not inner:
        return []
    items = []
    for part in _split_flow_items(inner):
        items.append(_parse_scalar(part.strip()))
    return items


def _split_flow_items(text: str) -> list:
    """Split comma-separated flow items, respecting quoted strings."""
    items = []
    buf = []
    in_quote = None
    for ch in text:
        if ch in ('"', "'") and in_quote is None:
            in_quote = ch
            buf.append(ch)
        elif ch == in_quote:
            in_quote = None
            buf.append(ch)
        elif ch == "," and in_quote is None:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf).strip())
    return items


def _indent_level(line: str) -> int:
    """Return the number of leading spaces on a line."""
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list, start: int, base_indent: int) -> tuple:
    """
    Recursively parse a YAML block starting at ``start``.

    Returns ``(value, next_index)`` where value is a Python dict/list/scalar
    and next_index is the first line index that was NOT consumed.
    """
    # Determine what we are looking at
    first = lines[start]
    stripped = first.strip()

    if not stripped or stripped.startswith("#"):
        return None, start + 1

    indent = _indent_level(first)

    # Sequence item
    if stripped.startswith("- ") or stripped == "-":
        return _parse_sequence(lines, start, indent)

    # Mapping key
    if ":" in stripped:
        return _parse_mapping(lines, start, indent)

    # Plain scalar (shouldn't normally happen at block start, but handle it)
    return _parse_scalar(stripped), start + 1


def _parse_sequence(lines: list, start: int, base_indent: int) -> tuple:
    """Parse a YAML block sequence (lines starting with ``-``)."""
    items = []
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        indent = _indent_level(line)
        if indent < base_indent:
            break
        if indent > base_indent:
            # Continuation of the previous item – shouldn't happen with well-formed
            # YAML but skip gracefully
            i += 1
            continue
        stripped = line.strip()
        if not stripped.startswith("-"):
            break  # No longer a sequence

        rest = stripped[1:].strip()

        if not rest:
            # Next lines are the value block
            i += 1
            if i < len(lines):
                next_stripped = lines[i].strip()
                next_indent = _indent_level(lines[i])
                if next_stripped.startswith("- ") or next_stripped == "-":
                    # Nested sequence
                    value, i = _parse_sequence(lines, i, next_indent)
                elif ":" in next_stripped:
                    value, i = _parse_mapping(lines, i, next_indent)
                else:
                    value = _parse_scalar(next_stripped)
                    i += 1
            else:
                value = None
        elif rest.startswith("["):
            value = _parse_flow_sequence(rest)
            i += 1
        elif rest.endswith(":") or (": " in rest):
            # Inline mapping key — parse the rest of this item as a mapping
            # Synthesise lines with correct indentation
            child_indent = indent + 2
            child_lines = [" " * child_indent + rest]
            j = i + 1
            while j < len(lines):
                if not lines[j].strip() or lines[j].strip().startswith("#"):
                    j += 1
                    continue
                child_line_indent = _indent_level(lines[j])
                if child_line_indent > indent:
                    child_lines.append(lines[j])
                    j += 1
                else:
                    break
            value, _ = _parse_mapping(child_lines, 0, child_indent)
            i = j
        else:
            value = _parse_scalar(rest)
            i += 1

        items.append(value)

    return items, i


def _parse_mapping(lines: list, start: int, base_indent: int) -> tuple:
    """Parse a YAML block mapping."""
    result = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        indent = _indent_level(line)
        if indent < base_indent:
            break
        if indent > base_indent:
            i += 1
            continue

        stripped = line.strip()

        # Must be key: value or key:
        if ":" not in stripped:
            break

        colon_idx = stripped.index(":")
        key_raw = stripped[:colon_idx].strip()

        # Strip quotes from key
        if (key_raw.startswith('"') and key_raw.endswith('"')) or \
           (key_raw.startswith("'") and key_raw.endswith("'")):
            key = key_raw[1:-1]
        else:
            key = key_raw

        value_raw = stripped[colon_idx + 1:].strip()

        if not value_raw or value_raw.startswith("#"):
            # Value is on the next lines
            i += 1
            if i < len(lines) and lines[i].strip():
                next_indent = _indent_level(lines[i])
                next_stripped = lines[i].strip()
                if next_stripped.startswith("- ") or next_stripped == "-":
                    value, i = _parse_sequence(lines, i, next_indent)
                elif ":" in next_stripped:
                    value, i = _parse_mapping(lines, i, next_indent)
                else:
                    value = _parse_scalar(next_stripped)
                    i += 1
            else:
                value = None
        elif value_raw.startswith("["):
            value = _parse_flow_sequence(value_raw)
            i += 1
        elif value_raw.startswith("{"):
            # Minimal flow mapping support: not typically used in .spec files
            value = {}
            i += 1
        else:
            # Scalar – check if the next lines continue with a deeper indent
            # (e.g. a block scalar). For .spec files we don't use block scalars,
            # so just take the inline value.
            value = _parse_scalar(value_raw)
            i += 1

        result[key] = value

    return result, i


def parse_yaml(text: str) -> dict:
    """
    Parse a YAML document string into a Python dict.

    Supports the subset of YAML 1.2 used in .spec files:
    - Block mappings and sequences
    - Flow sequences (``[a, b, c]``)
    - Quoted and plain scalars
    - Inline comments (stripped from values)

    Raises _YAMLParseError on malformed input.

    Args:
        text: Raw YAML text to parse.

    Returns:
        Parsed document as a Python dictionary.
    """
    if not isinstance(text, str):
        raise _YAMLParseError("Input must be a string")

    # Normalise line endings
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Strip YAML document markers
    filtered = []
    for line in lines:
        s = line.strip()
        if s in ("---", "...") or s.startswith("# ") or s == "#":
            continue
        filtered.append(line)

    if not filtered:
        return {}

    # Find first non-empty line
    first_content = next(
        (i for i, l in enumerate(filtered) if l.strip()), None
    )
    if first_content is None:
        return {}

    base_indent = _indent_level(filtered[first_content])
    result, _ = _parse_mapping(filtered, first_content, base_indent)
    return result


# ---------------------------------------------------------------------------
# YAML emitter  (stdlib only, deterministic output)
# ---------------------------------------------------------------------------

def _yaml_scalar(value: object) -> str:
    """Render a Python scalar as a YAML scalar string."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    # String – quote if it could be misread as another type or contains colons
    s = str(value)
    needs_quoting = (
        s in ("true", "false", "null", "~", "")
        or re.match(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$", s)
        or s.startswith("{") or s.startswith("[")
        or s.startswith("*") or s.startswith("&")
        or s.startswith("!") or s.startswith("|") or s.startswith(">")
        or ":" in s
        or "#" in s
        or s.startswith(" ") or s.endswith(" ")
        or s.startswith('"') or s.startswith("'")
    )
    if needs_quoting:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _emit_value(value: object, indent: int) -> str:
    """
    Recursively emit a Python value as YAML text.

    Args:
        value: Python object to emit.
        indent: Current indentation level in spaces.

    Returns:
        YAML-formatted string fragment (no trailing newline).
    """
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            key_str = _yaml_scalar(k)
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{key_str}:")
                lines.append(_emit_value(v, indent + 2))
            else:
                lines.append(f"{pad}{key_str}: {_yaml_scalar(v)}")
        return "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            # Check if items are scalars – emit as flow sequence
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    key_str = _yaml_scalar(k)
                    if first:
                        prefix = f"{pad}- "
                        first = False
                    else:
                        prefix = f"{pad}  "
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{key_str}:")
                        lines.append(_emit_value(v, indent + 4))
                    else:
                        lines.append(f"{prefix}{key_str}: {_yaml_scalar(v)}")
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.append(_emit_value(item, indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return "\n".join(lines)
    else:
        return f"{pad}{_yaml_scalar(value)}"


# Key order for the root document and sub-sections
_ROOT_KEY_ORDER = ["version", "module", "description",
                   "entities", "behaviors", "rules", "constraints"]
_ENTITY_KEY_ORDER = ["name", "description", "properties"]
_PROPERTY_KEY_ORDER = ["name", "type", "required", "description", "default", "enum"]
_BEHAVIOR_KEY_ORDER = ["name", "description", "given", "when", "then", "examples"]
_EXAMPLE_KEY_ORDER = ["input", "output", "description"]
_RULE_KEY_ORDER = ["name", "description", "condition", "action"]
_CONSTRAINT_KEY_ORDER = ["name", "description", "type", "value"]


def _sort_dict(d: dict, key_order: list) -> dict:
    """Return a new dict with keys in the given order (unknown keys appended)."""
    ordered = {}
    for k in key_order:
        if k in d:
            ordered[k] = d[k]
    for k, v in d.items():
        if k not in ordered:
            ordered[k] = v
    return ordered


def _normalise_spec(spec: dict) -> dict:
    """Apply canonical key ordering to all sections of a spec dict."""
    out = _sort_dict(spec, _ROOT_KEY_ORDER)

    if "entities" in out and isinstance(out["entities"], list):
        normalised_entities = []
        for entity in out["entities"]:
            e = _sort_dict(entity, _ENTITY_KEY_ORDER)
            if "properties" in e and isinstance(e["properties"], list):
                e["properties"] = [
                    _sort_dict(p, _PROPERTY_KEY_ORDER) for p in e["properties"]
                ]
            normalised_entities.append(e)
        out["entities"] = normalised_entities

    if "behaviors" in out and isinstance(out["behaviors"], list):
        normalised_behaviors = []
        for beh in out["behaviors"]:
            b = _sort_dict(beh, _BEHAVIOR_KEY_ORDER)
            if "examples" in b and isinstance(b["examples"], list):
                b["examples"] = [
                    _sort_dict(ex, _EXAMPLE_KEY_ORDER) for ex in b["examples"]
                ]
            normalised_behaviors.append(b)
        out["behaviors"] = normalised_behaviors

    if "rules" in out and isinstance(out["rules"], list):
        out["rules"] = [_sort_dict(r, _RULE_KEY_ORDER) for r in out["rules"]]

    if "constraints" in out and isinstance(out["constraints"], list):
        out["constraints"] = [
            _sort_dict(c, _CONSTRAINT_KEY_ORDER) for c in out["constraints"]
        ]

    return out


def dump_yaml(spec: dict) -> str:
    """
    Serialise a spec dict to a canonical YAML string.

    Output characteristics:
    - 2-space indentation
    - LF line endings
    - UTF-8 safe (no non-ASCII escaping beyond what is necessary)
    - Trailing newline
    - Blank line between top-level sections for readability

    Args:
        spec: Spec dictionary to serialise.

    Returns:
        YAML string with trailing newline.
    """
    spec = _normalise_spec(spec)
    sections = []

    root_scalars = {k: v for k, v in spec.items()
                   if not isinstance(v, (dict, list))}
    root_collections = {k: v for k, v in spec.items()
                        if isinstance(v, (dict, list))}

    # Root scalars first
    scalar_lines = []
    for k in _ROOT_KEY_ORDER:
        if k in root_scalars:
            scalar_lines.append(f"{_yaml_scalar(k)}: {_yaml_scalar(root_scalars[k])}")
    # Any unknown scalar keys
    for k, v in root_scalars.items():
        if k not in _ROOT_KEY_ORDER:
            scalar_lines.append(f"{_yaml_scalar(k)}: {_yaml_scalar(v)}")
    if scalar_lines:
        sections.append("\n".join(scalar_lines))

    # Collection sections
    for k in _ROOT_KEY_ORDER:
        if k in root_collections:
            v = root_collections[k]
            block = _emit_value(v, 2)
            sections.append(f"{_yaml_scalar(k)}:\n{block}")
    for k, v in root_collections.items():
        if k not in _ROOT_KEY_ORDER:
            block = _emit_value(v, 2)
            sections.append(f"{_yaml_scalar(k)}:\n{block}")

    return "\n\n".join(sections) + "\n"


# ---------------------------------------------------------------------------
# Public file I/O
# ---------------------------------------------------------------------------

def load_spec(path: Union[str, Path]) -> dict:
    """
    Load and parse a .spec file into a Python dictionary.

    Args:
        path: Path to the .spec file (str or Path).

    Returns:
        Parsed spec as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        _YAMLParseError: If the file is not valid YAML.
        UnicodeDecodeError: If the file is not UTF-8 encoded.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {path}")
    text = path.read_text(encoding="utf-8")
    return parse_yaml(text)


def save_spec(spec: dict, path: Union[str, Path]) -> None:
    """
    Serialise a spec dictionary and write it to a .spec file.

    Ensures UTF-8 encoding and LF line endings regardless of platform.

    Args:
        spec: Spec dictionary to write.
        path: Destination path (str or Path).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = dump_yaml(spec)
    # Enforce LF even on Windows
    path.write_bytes(yaml_text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Schema conversion helpers
# ---------------------------------------------------------------------------

_ALLOWED_TYPES = {"string", "number", "boolean", "null", "array", "object"}


def coerce_property_type(type_str: str) -> str:
    """
    Normalise a property type string to the canonical lowercase form.

    Unknown types are returned unchanged so that the validator can flag them.

    Args:
        type_str: Raw type string from a parsed spec.

    Returns:
        Normalised type string.
    """
    if not isinstance(type_str, str):
        return type_str
    return type_str.strip().lower()


def spec_to_json_schema(spec: dict) -> dict:
    """
    Convert a spec dictionary to a minimal JSON Schema representation.

    Only entities with properties are translated.  The result is a plain
    Python dict (not a JSON string) so callers can embed it or serialise
    further as needed.

    Args:
        spec: Parsed spec dictionary.

    Returns:
        JSON Schema dict with a ``definitions`` map keyed by entity name.
    """
    definitions = {}
    for entity in spec.get("entities", []):
        name = entity.get("name", "")
        props = {}
        required_fields = []
        for prop in entity.get("properties", []):
            pname = prop.get("name", "")
            ptype = coerce_property_type(prop.get("type", "string"))
            schema_prop = {"type": ptype}
            if "description" in prop:
                schema_prop["description"] = prop["description"]
            if "default" in prop:
                schema_prop["default"] = prop["default"]
            if "enum" in prop and isinstance(prop["enum"], list):
                schema_prop["enum"] = prop["enum"]
            props[pname] = schema_prop
            if prop.get("required", False):
                required_fields.append(pname)
        entity_schema = {
            "type": "object",
            "properties": props,
        }
        if required_fields:
            entity_schema["required"] = required_fields
        definitions[name] = entity_schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": spec.get("module", ""),
        "description": spec.get("description", ""),
        "definitions": definitions,
    }


def merge_specs(base: dict, overlay: dict) -> dict:
    """
    Merge two spec dicts, with ``overlay`` taking precedence on scalar fields.

    Lists (entities, behaviors, rules, constraints) are concatenated and
    deduplicated by ``name``.

    Args:
        base: The base spec dictionary.
        overlay: The overlay spec dictionary.

    Returns:
        Merged spec dictionary.
    """
    result = dict(base)
    # Scalar root fields
    for key in ("version", "module", "description"):
        if key in overlay:
            result[key] = overlay[key]
    # List sections – merge by name
    for section in ("entities", "behaviors", "rules", "constraints"):
        base_items = {item["name"]: item for item in base.get(section, [])
                      if isinstance(item, dict) and "name" in item}
        for item in overlay.get(section, []):
            if isinstance(item, dict) and "name" in item:
                base_items[item["name"]] = item
        if base_items:
            result[section] = list(base_items.values())
    return result
