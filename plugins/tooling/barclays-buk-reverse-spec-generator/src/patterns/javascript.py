"""
patterns/javascript.py - JavaScript / TypeScript BDD spec extraction.

Extracts spec components from JavaScript and TypeScript source code using
JS/TS-aware regex patterns.

Supported constructs:
    Entities:
        - ES6 ``class Foo {`` definitions → EntityDict with field properties
        - TypeScript ``interface Foo {`` / ``type Foo = {`` → EntityDict
        - ``@typedef`` in JSDoc comments → EntityDict

    Behaviors:
        - ``function foo(...)`` / ``async function foo(...)`` → BehaviorDict
        - Arrow functions: ``const foo = (...) =>`` → BehaviorDict
        - Class methods: ``methodName(...) {`` → BehaviorDict
        - Exported async/sync functions → higher confidence
        - JSDoc comment parsing (@param, @returns, @throws, @async, @deprecated)

    Rules:
        - ``if``/``else if`` with rule-language comment above
        - Guard patterns: ``if (!cond) { throw new Error(...); }``
        - Inline ``// RULE:`` / ``// BUSINESS RULE:`` annotations

    Constraints:
        - ``const MAX_X = 123`` (uppercase) → limit constraint
        - ``throw new Error("...")`` / ``throw new TypeError(...)`` → invariant
        - Timeout patterns: ``setTimeout(fn, 30000)`` → timeout
        - TypeScript ``readonly`` field with value → invariant

Confidence tiers (JS-specific):
    1.0 - Exported function with full JSDoc (@param + @returns)
    0.9 - Exported function with summary JSDoc
    0.85 - TypeScript typed function (return type + params)
    0.8  - async function (visible async contract)
    0.75 - Regular function / method with partial hints
    0.6  - Arrow function with no annotation
    0.5  - Inferred from naming alone
"""

from __future__ import annotations

import re
import sys
import os

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from spec_extractor import (
    BaseExtractor,
    EntityDict,
    BehaviorDict,
    RuleDict,
    ConstraintDict,
    PropertyDict,
    _to_snake_case,
    _to_pascal_case,
    _truncate_description,
    _normalize_type,
    _clean_identifier,
)


# ---------------------------------------------------------------------------
# JavaScript / TypeScript compiled patterns
# ---------------------------------------------------------------------------

# ES6 class definition
_JS_CLASS_RE = re.compile(
    r"(?:^|\n)\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?"
    r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+extends\s+[A-Za-z_][A-Za-z0-9_.]*(?:<[^>]*)?)?"
    r"\s*\{",
    re.MULTILINE,
)

# TypeScript interface definition
_TS_INTERFACE_RE = re.compile(
    r"(?:^|\n)\s*(?:export\s+)?interface\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+extends\s+[A-Za-z_][A-Za-z0-9_, <>.]*)?",
    re.MULTILINE,
)

# TypeScript type alias: type Foo = { ... }
_TS_TYPE_ALIAS_RE = re.compile(
    r"(?:^|\n)\s*(?:export\s+)?type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*="
    r"\s*\{",
    re.MULTILINE,
)

# Regular function declaration (including async, generator)
_JS_FUNC_DECL_RE = re.compile(
    r"(?:^|\n)(?P<pre_ws>\s*)(?:export\s+(?:default\s+)?)?"
    r"(?P<async>async\s+)?function\s*\*?\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)"
    r"(?:\s*:\s*(?P<return_type>[A-Za-z_][\w<>\[\] |&?]*))?"
    r"\s*\{",
    re.MULTILINE,
)

# Arrow function: const name = async (...) => ...
_JS_ARROW_RE = re.compile(
    r"(?:^|\n)(?P<pre_ws>\s*)(?:export\s+)?(?:const|let|var)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?::\s*(?P<ts_type>[A-Za-z_][\w<>\[\] |&?]*))?\s*=\s*"
    r"(?P<async>async\s+)?"
    r"\((?P<params>[^)]*)\)"
    r"(?:\s*:\s*(?P<return_type>[A-Za-z_][\w<>\[\] |&?]*))?\s*=>\s*"
    r"(?:\{|[^\n{;])",
    re.MULTILINE,
)

# Class method (inside class body)
_JS_METHOD_RE = re.compile(
    r"^\s*(?:(?:static|async|get|set|#|override|abstract|public|private|protected|"
    r"readonly)\s+)*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)"
    r"(?:\s*:\s*(?P<return_type>[A-Za-z_][\w<>\[\] |&?]*))?\s*\{",
    re.MULTILINE,
)

# JSDoc block: /** ... */
_JSDOC_RE = re.compile(r"/\*\*\s*(?P<content>.*?)\*/", re.DOTALL)

# JSDoc tags
_JSDOC_PARAM_RE = re.compile(
    r"@param(?:eter)?\s+(?:\{(?P<type>[^}]+)\}\s+)?(?P<name>[\w.[\]]+)\s*(?P<desc>[^\n@]*)"
)
_JSDOC_RETURN_RE = re.compile(
    r"@returns?\s+(?:\{(?P<type>[^}]+)\}\s*)?(?P<desc>[^\n@]*)"
)
_JSDOC_THROWS_RE = re.compile(
    r"@throws?\s+(?:\{(?P<type>[^}]+)\}\s*)?(?P<desc>[^\n@]*)"
)
_JSDOC_TYPEDEF_RE = re.compile(
    r"@typedef\s+\{[^}]+\}\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)
_JSDOC_PROP_RE = re.compile(
    r"@property\s+\{(?P<type>[^}]+)\}\s+(?P<name>\w+)\s+(?P<desc>[^\n@]*)"
)
_JSDOC_ASYNC_RE = re.compile(r"@async\b")
_JSDOC_DEPRECATED_RE = re.compile(r"@deprecated\s*(?P<msg>[^\n@]*)")

# TypeScript field in interface/type body: name?: Type; or name: Type;
_TS_FIELD_RE = re.compile(
    r"^\s*(?:readonly\s+)?(?P<name>[a-z_][A-Za-z0-9_]*)\??\s*:\s*"
    r"(?P<type>[A-Za-z_][\w<>\[\] |&?]*)\s*[;,]?$",
    re.MULTILINE,
)

# JS class field (TC39): name = value  or  #name = value (private)
_JS_CLASS_FIELD_RE = re.compile(
    r"^\s*(?:(?:static|readonly|#|private|public|protected)\s+)*"
    r"(?P<name>[a-z_#][A-Za-z0-9_]*)"
    r"(?:\s*:\s*(?P<type>[A-Za-z_][\w<>\[\] |&?]*))?"
    r"(?:\s*=\s*(?P<default>[^\n;{]+))?;",
    re.MULTILINE,
)

# throw new Error/TypeError/RangeError("message")
_JS_THROW_RE = re.compile(
    r"throw\s+(?:new\s+)?(?P<exc>[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)?)\s*"
    r"\(\s*(?:`(?P<tmsg>[^`]{5,})`|['\"](?P<msg>[^'\"]{5,})['\"])?\s*\)",
)

# const UPPER_CONSTANT = value (module-level)
_JS_CONST_RE = re.compile(
    r"(?:^|\n)(?:export\s+)?const\s+(?P<name>[A-Z][A-Z0-9_]{2,})\s*=\s*"
    r"(?P<value>[^\n;,]+)",
    re.MULTILINE,
)

# setTimeout / setInterval pattern
_JS_TIMEOUT_RE = re.compile(
    r"(?:setTimeout|setInterval)\s*\([^,]+,\s*(?P<ms>\d{3,})\s*\)",
)

# Guard: if (!cond) { throw new Error(...) }
_JS_GUARD_RE = re.compile(
    r"if\s*\(\s*(?P<negated>!)?(?P<cond>[^)]+)\)\s*\{?\s*\n?\s*throw\s+",
    re.MULTILINE,
)

# if/else if for rule extraction
_JS_IF_RE = re.compile(r"^\s*(?:}?\s*else\s+)?if\s*\((?P<expr>[^)]+)\)", re.MULTILINE)


# ---------------------------------------------------------------------------
# JSDoc parser
# ---------------------------------------------------------------------------

class _JSDoc:
    """
    Minimal parser for JSDoc comment blocks.

    Attributes:
        summary:    First paragraph of the JSDoc.
        params:     Dict mapping param name → {type, description}.
        returns:    Dict with {type, description}.
        throws:     List of {type, description} dicts.
        is_async:   True if ``@async`` tag is present.
        deprecated: Deprecation message if present.
        typedefs:   List of ``@typedef`` name strings.
        properties: List of ``@property`` dicts.
    """

    def __init__(self, raw: str) -> None:
        self.summary: str = ""
        self.params: dict = {}
        self.returns: dict = {}
        self.throws: list = []
        self.is_async: bool = False
        self.deprecated: str = ""
        self.typedefs: list = []
        self.properties: list = []
        self._parse(raw)

    def _parse(self, text: str) -> None:
        """Parse raw JSDoc content into structured fields."""
        # Strip leading * from each line
        lines = []
        for line in text.split("\n"):
            stripped = re.sub(r"^\s*\*+\s?", "", line).strip()
            lines.append(stripped)

        # Summary: everything before the first @tag
        summary_parts = []
        for line in lines:
            if line.startswith("@"):
                break
            if line:
                summary_parts.append(line)
        self.summary = " ".join(summary_parts)

        full = "\n".join(lines)

        # @param
        for m in _JSDOC_PARAM_RE.finditer(full):
            name = m.group("name").lstrip("[").rstrip("]").split(".")[0]
            self.params[name] = {
                "type": m.group("type") or "",
                "description": m.group("desc").strip(),
            }

        # @returns / @return
        m = _JSDOC_RETURN_RE.search(full)
        if m:
            self.returns = {
                "type": m.group("type") or "",
                "description": m.group("desc").strip(),
            }

        # @throws
        for m in _JSDOC_THROWS_RE.finditer(full):
            self.throws.append({
                "type": m.group("type") or "Error",
                "description": m.group("desc").strip(),
            })

        # @async
        self.is_async = bool(_JSDOC_ASYNC_RE.search(full))

        # @deprecated
        m = _JSDOC_DEPRECATED_RE.search(full)
        if m:
            self.deprecated = m.group("msg").strip()

        # @typedef
        for m in _JSDOC_TYPEDEF_RE.finditer(full):
            self.typedefs.append(m.group("name"))

        # @property
        for m in _JSDOC_PROP_RE.finditer(full):
            self.properties.append({
                "name": m.group("name"),
                "type": m.group("type"),
                "description": m.group("desc").strip(),
            })


def _extract_jsdoc_before(source: str, offset: int) -> _JSDoc | None:
    """
    Find and parse the JSDoc comment immediately before the given offset.

    Args:
        source: Full JavaScript / TypeScript source text.
        offset: Character offset of the construct to find JSDoc for.

    Returns:
        :class:`_JSDoc` instance or None if no JSDoc found.
    """
    pre = source[:offset]
    last_start = pre.rfind("/**")
    if last_start == -1:
        return None
    last_end = pre.find("*/", last_start)
    if last_end == -1:
        return None

    # Ensure nothing significant between comment and current construct
    between = pre[last_end + 2:].strip()
    # Allow only decorators, blank lines, export keywords
    if re.search(r"(?:class|function|const|let|var)\s+\w", between):
        return None

    raw = source[last_start + 3:last_end]
    doc = _JSDoc(raw)
    if not (doc.summary or doc.params or doc.returns):
        return None
    return doc


# ---------------------------------------------------------------------------
# Type system helpers
# ---------------------------------------------------------------------------

def _parse_ts_type(raw: str) -> str:
    """
    Convert a TypeScript type annotation to a canonical spec type.

    Handles:
        - Union types: ``string | null`` → first non-null type
        - Generic: ``Array<T>`` / ``T[]`` → array
        - ``Record<K, V>`` / ``Map<K, V>`` → object
        - ``Promise<T>`` → unwrap T
        - Literal: ``'active' | 'inactive'`` → string

    Args:
        raw: Raw TypeScript type string.

    Returns:
        Canonical spec type string.
    """
    s = raw.strip()

    # Promise<T> → unwrap
    m = re.match(r"Promise\s*<\s*(.+)\s*>", s)
    if m:
        return _parse_ts_type(m.group(1))

    # Array<T> or T[]
    if re.match(r"Array\s*<", s) or s.endswith("[]"):
        return "array"
    if re.match(r"(?:ReadonlyArray|Set|Iterable|Iterator|Generator)\s*<", s):
        return "array"

    # Record<K,V>, Map<K,V>, object
    if re.match(r"(?:Record|Map|WeakMap|Object)\s*<", s):
        return "object"

    # Union type: string | null | undefined
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        non_null = [p for p in parts if p.lower() not in ("null", "undefined", "never")]
        if non_null:
            # Check for string literal union
            if all(p.startswith("'") or p.startswith('"') for p in non_null):
                return "string"
            return _parse_ts_type(non_null[0])
        return "null"

    # Intersection type: A & B → object
    if "&" in s:
        return "object"

    # String literal
    if s.startswith("'") or s.startswith('"'):
        return "string"

    # Tuple
    if s.startswith("[") and s.endswith("]"):
        return "array"

    # TypeScript primitives
    ts_map = {
        "string": "string", "number": "number", "boolean": "boolean",
        "any": "object", "unknown": "object", "never": "null",
        "void": "null", "undefined": "null", "null": "null",
        "object": "object", "symbol": "string", "bigint": "number",
    }
    if s.lower() in ts_map:
        return ts_map[s.lower()]

    return _normalize_type(s)


# ---------------------------------------------------------------------------
# Parameter list parser
# ---------------------------------------------------------------------------

def _parse_js_params(
    param_str: str,
    doc: _JSDoc | None = None,
) -> list:
    """
    Parse a JavaScript / TypeScript parameter list.

    Handles:
        - Plain: ``name``
        - TypeScript annotated: ``name: Type``
        - Default: ``name = default`` or ``name: Type = default``
        - Destructured: ``{ a, b }`` → treated as ``object`` type
        - Rest: ``...items`` → ``array`` type
        - Optional: ``name?`` (TypeScript)

    Args:
        param_str: Raw parameter string between parentheses.
        doc: Parsed JSDoc for description enrichment.

    Returns:
        List of :class:`PropertyDict` instances.
    """
    if not param_str.strip():
        return []

    parts = _split_js_params(param_str)
    props = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        name = "param"
        ptype = "string"
        default = None
        confidence = 0.7
        is_rest = False

        # Rest parameter: ...items
        if part.startswith("..."):
            is_rest = True
            part = part[3:]

        # Destructured object: { a, b }
        if part.startswith("{"):
            props.append(PropertyDict(
                name="options",
                type="object",
                required=True,
                description="Destructured parameter object",
                confidence=0.6,
            ))
            continue

        # Destructured array: [a, b]
        if part.startswith("["):
            props.append(PropertyDict(
                name="items",
                type="array",
                required=True,
                description="Destructured array parameter",
                confidence=0.6,
            ))
            continue

        # Strip default value
        if "=" in part and "=>" not in part:
            param_part, default_raw = part.split("=", 1)
            default = default_raw.strip()
            part = param_part.strip()

        # TypeScript: name?: Type or name: Type
        optional = part.endswith("?")
        part = part.rstrip("?")

        if ":" in part:
            name_part, type_part = part.split(":", 1)
            name = _clean_identifier(name_part.strip())
            ptype = _parse_ts_type(type_part.strip())
            confidence = 0.85
        else:
            name = _clean_identifier(part)
            confidence = 0.65

        # Enrich from JSDoc
        desc = ""
        if doc and name in doc.params:
            param_info = doc.params[name]
            desc = _truncate_description(param_info.get("description", ""), 100)
            if param_info.get("type"):
                ptype = _parse_ts_type(param_info["type"])
            confidence = min(1.0, confidence + 0.15)

        props.append(PropertyDict(
            name=name,
            type="array" if is_rest else ptype,
            required=(default is None and not optional and not is_rest),
            description=desc or f"Parameter {name}",
            default=default,
            confidence=confidence,
        ))

    return props


def _split_js_params(param_str: str) -> list:
    """
    Split a JS/TS parameter string on top-level commas.

    Respects nesting inside ``<>``, ``[]``, ``()``, ``{}`` and template
    literals.

    Args:
        param_str: Raw parameter string.

    Returns:
        List of parameter sub-strings.
    """
    parts = []
    buf = []
    depth = 0
    in_template = False
    for ch in param_str:
        if ch == "`":
            in_template = not in_template
            buf.append(ch)
        elif in_template:
            buf.append(ch)
        elif ch in ("<", "(", "[", "{"):
            depth += 1
            buf.append(ch)
        elif ch in (">", ")", "]", "}"):
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


# ---------------------------------------------------------------------------
# JavaScript extractor
# ---------------------------------------------------------------------------

class JavaScriptExtractor(BaseExtractor):
    """
    JavaScript / TypeScript spec extractor.

    Understands modern JS/TS constructs including:
    - ES6 class definitions → entities
    - TypeScript interfaces / type aliases → entities
    - ``function``, arrow function, class methods → behaviors
    - JSDoc comments with @param / @returns / @throws
    - TypeScript type annotations
    - async/await patterns
    - Error throwing patterns → constraints
    - Uppercase constant declarations → limit constraints

    Args:
        confidence_threshold: Minimum confidence to include an item.
        module_name: Override module name.
        skip_private: Skip methods/fields prefixed with ``_`` or ``#``.
        max_behaviors: Maximum number of behaviors per file.
        max_rules: Maximum number of rules per file.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        module_name: str = None,
        skip_private: bool = True,
        max_behaviors: int = 40,
        max_rules: int = 20,
    ) -> None:
        super().__init__(confidence_threshold, module_name)
        self.skip_private = skip_private
        self.max_behaviors = max_behaviors
        self.max_rules = max_rules

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def extract_entities(self, source: str) -> list:
        """
        Extract ES6 classes, TypeScript interfaces, and type aliases as entities.

        Processing:
        - ``class Foo`` → EntityDict with class field properties
        - ``interface Foo`` → EntityDict with interface member properties
        - ``type Foo = { ... }`` → EntityDict with type member properties
        - ``@typedef`` in JSDoc → EntityDict with ``@property`` members

        Skips test/mock/utility classes.

        Args:
            source: JavaScript / TypeScript source code text.

        Returns:
            List of :class:`EntityDict` instances.
        """
        entities = []
        seen_names: set = set()

        # ES6 classes
        for match in _JS_CLASS_RE.finditer(source):
            raw_name = match.group("name")
            if self._should_skip_class(raw_name):
                continue

            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            doc = _extract_jsdoc_before(source, match.start())
            summary = doc.summary if doc else ""
            desc = _truncate_description(summary) if summary else f"JavaScript class {raw_name}"

            confidence = 0.9 if doc else 0.7
            props = self._extract_class_members(source, match.end())

            entities.append(EntityDict(
                name=pascal,
                description=desc,
                properties=props,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        # TypeScript interfaces
        for match in _TS_INTERFACE_RE.finditer(source):
            raw_name = match.group("name")
            if self._should_skip_class(raw_name):
                continue

            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            doc = _extract_jsdoc_before(source, match.start())
            summary = doc.summary if doc else ""
            desc = _truncate_description(summary) if summary else (
                f"TypeScript interface {raw_name}"
            )

            props = self._extract_interface_members(source, match.end())
            confidence = 1.0 if doc else 0.85  # Interfaces are explicit contracts

            entities.append(EntityDict(
                name=pascal,
                description=desc,
                properties=props,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        # TypeScript type aliases
        for match in _TS_TYPE_ALIAS_RE.finditer(source):
            raw_name = match.group("name")
            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            doc = _extract_jsdoc_before(source, match.start())
            summary = doc.summary if doc else ""
            desc = _truncate_description(summary) if summary else (
                f"TypeScript type {raw_name}"
            )

            props = self._extract_interface_members(source, match.end())
            confidence = 0.85 if props else 0.7

            entities.append(EntityDict(
                name=pascal,
                description=desc,
                properties=props,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        # @typedef in JSDoc
        for match in _JSDOC_RE.finditer(source):
            raw = match.group("content")
            doc = _JSDoc(raw)
            for typedef_name in doc.typedefs:
                pascal = _to_pascal_case(typedef_name)
                if pascal in seen_names:
                    continue
                seen_names.add(pascal)

                props = []
                for prop in doc.properties:
                    props.append(PropertyDict(
                        name=prop["name"],
                        type=_parse_ts_type(prop["type"]),
                        required=True,
                        description=_truncate_description(prop["description"]) or (
                            f"Property {prop['name']}"
                        ),
                        confidence=0.9,
                    ))

                entities.append(EntityDict(
                    name=pascal,
                    description=_truncate_description(doc.summary) or (
                        f"JSDoc typedef {typedef_name}"
                    ),
                    properties=props,
                    confidence=0.9 if props else 0.7,
                ))

        return entities

    def _should_skip_class(self, name: str) -> bool:
        """Return True if a class should be excluded from entity extraction."""
        lower = name.lower()
        return any(
            lower.endswith(s) or lower.startswith(s)
            for s in ("test", "mock", "stub", "fake", "fixture", "spec",
                      "helper", "util", "mixin", "abstract")
        )

    def _extract_class_members(self, source: str, class_body_start: int) -> list:
        """
        Extract class fields from an ES6/TypeScript class body.

        Args:
            source: Full source text.
            class_body_start: Character offset after the class ``{``.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        body = self._extract_brace_block(source, class_body_start - 1)
        if not body:
            return []

        props = []
        seen: set = set()

        for match in _JS_CLASS_FIELD_RE.finditer(body):
            name = match.group("name")
            # Skip private fields (#name)
            if name.startswith("#") and self.skip_private:
                continue
            if name.startswith("_") and self.skip_private:
                continue
            if name in seen:
                continue
            seen.add(name)

            raw_type = match.group("type") or ""
            ptype = _parse_ts_type(raw_type) if raw_type else "string"
            default = match.group("default")
            if default:
                default = default.strip().rstrip(";,")

            props.append(PropertyDict(
                name=name.lstrip("#"),
                type=ptype,
                required=(default is None),
                description=f"Class field {name}",
                default=default,
                confidence=0.8 if raw_type else 0.65,
            ))

        return props[:20]

    def _extract_interface_members(self, source: str, def_end: int) -> list:
        """
        Extract member declarations from a TypeScript interface or type body.

        Args:
            source: Full source text.
            def_end: Character offset after the interface/type keyword.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        body = self._extract_brace_block(source, def_end)
        if not body:
            return []

        props = []
        seen: set = set()

        for match in _TS_FIELD_RE.finditer(body):
            name = match.group("name")
            if name in seen:
                continue
            seen.add(name)

            raw_line = match.group(0)
            optional = "?" in raw_line.split(":")[0]

            props.append(PropertyDict(
                name=name,
                type=_parse_ts_type(match.group("type")),
                required=not optional,
                description=f"Member {name}",
                confidence=0.9,
            ))

        return props[:20]

    def _extract_brace_block(self, source: str, hint: int) -> str:
        """
        Extract text between matching braces starting near ``hint``.

        Args:
            source: Full source text.
            hint: Character offset to search for ``{`` from.

        Returns:
            Content between braces (inclusive), or empty string.
        """
        start = source.find("{", hint)
        if start == -1:
            return ""
        depth = 0
        pos = start
        while pos < min(len(source), start + 15000):
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
                if depth == 0:
                    return source[start:pos + 1]
            pos += 1
        return source[start:]

    # ------------------------------------------------------------------
    # Behavior extraction
    # ------------------------------------------------------------------

    def extract_behaviors(self, source: str) -> list:
        """
        Extract JavaScript / TypeScript functions and methods as behaviors.

        Captures:
        - Regular ``function`` declarations
        - Arrow functions assigned to ``const`` / ``let``
        - Class instance methods (from class body scanning)

        Skips:
        - Private methods (``_name`` or ``#name``) when ``skip_private=True``
        - ``constructor``, ``toString``, ``valueOf``
        - Test functions (``test_``, ``it(``, ``describe(``, ``should``)

        Args:
            source: JavaScript / TypeScript source code text.

        Returns:
            List of :class:`BehaviorDict` instances.
        """
        behaviors = []
        seen_names: set = set()

        skip_names = {"constructor", "toString", "valueOf", "hasOwnProperty",
                      "render", "componentDidMount", "componentWillUnmount"}

        # Function declarations
        for match in _JS_FUNC_DECL_RE.finditer(source):
            if len(behaviors) >= self.max_behaviors:
                break

            raw_name = match.group("name")
            if self._should_skip_func(raw_name, skip_names):
                continue

            snake_name = _to_snake_case(raw_name)
            if snake_name in seen_names:
                continue
            seen_names.add(snake_name)

            is_async = bool(match.group("async"))
            is_exported = "export" in (source[max(0, match.start() - 10):match.start()])
            return_type_raw = match.group("return_type") or ""
            params_str = match.group("params") or ""

            doc = _extract_jsdoc_before(source, match.start())
            params = _parse_js_params(params_str, doc)
            return_type = _parse_ts_type(return_type_raw) if return_type_raw else ""

            behavior = self._build_behavior(
                snake_name, raw_name, params, doc, return_type,
                is_async, is_exported, source, match.start(),
            )
            behaviors.append(behavior)

        # Arrow functions
        for match in _JS_ARROW_RE.finditer(source):
            if len(behaviors) >= self.max_behaviors:
                break

            raw_name = match.group("name")
            if self._should_skip_func(raw_name, skip_names):
                continue

            snake_name = _to_snake_case(raw_name)
            if snake_name in seen_names:
                continue
            seen_names.add(snake_name)

            is_async = bool(match.group("async"))
            is_exported = "export" in (source[max(0, match.start() - 10):match.start()])
            return_type_raw = match.group("return_type") or ""
            params_str = match.group("params") or ""

            doc = _extract_jsdoc_before(source, match.start())
            params = _parse_js_params(params_str, doc)
            return_type = _parse_ts_type(return_type_raw) if return_type_raw else ""

            behavior = self._build_behavior(
                snake_name, raw_name, params, doc, return_type,
                is_async, is_exported, source, match.start(),
                is_arrow=True,
            )
            behaviors.append(behavior)

        return behaviors

    def _should_skip_func(self, name: str, skip_names: set) -> bool:
        """Return True if a function should be excluded."""
        if name in skip_names:
            return True
        if self.skip_private and (name.startswith("_") or name.startswith("#")):
            return True
        lower = name.lower()
        if lower.startswith(("test", "it_", "describe_", "spec_")):
            return True
        # Skip single-char names (callbacks, etc.)
        if len(name) <= 1:
            return True
        return False

    def _build_behavior(
        self,
        snake_name: str,
        raw_name: str,
        params: list,
        doc: _JSDoc | None,
        return_type: str,
        is_async: bool,
        is_exported: bool,
        source: str,
        offset: int,
        is_arrow: bool = False,
    ) -> BehaviorDict:
        """
        Construct a :class:`BehaviorDict` from extracted function metadata.

        Args:
            snake_name: snake_case function name.
            raw_name: Original function name from source.
            params: Parsed parameter list.
            doc: Parsed JSDoc (may be None).
            return_type: Canonical return type.
            is_async: Whether function is async.
            is_exported: Whether function is exported.
            source: Full source text (for line number).
            offset: Character offset of the function.
            is_arrow: Whether this is an arrow function.

        Returns:
            :class:`BehaviorDict` instance.
        """
        human = re.sub(r"_", " ", snake_name)

        # Description
        if doc and doc.summary:
            desc = _truncate_description(doc.summary)
            confidence = 1.0 if doc.params else 0.9
        elif is_async and return_type:
            desc = f"Asynchronously executes {raw_name}"
            confidence = 0.85
        elif return_type:
            desc = f"Executes {raw_name} and returns {return_type}"
            confidence = 0.8
        elif is_exported:
            desc = f"Exported function {raw_name}"
            confidence = 0.75
        else:
            desc = f"Performs {raw_name} operation"
            confidence = 0.6

        if doc and doc.deprecated:
            confidence = max(0.3, confidence - 0.3)

        # GWT
        given, when, then_ = self._build_js_gwt(
            raw_name, params, doc, return_type, is_async,
        )

        # Examples from JSDoc @example
        examples = []
        if doc and "@example" in str(doc.summary):
            # Light extraction of @example content
            ex_match = re.search(r"@example\s*\n\s*(?P<code>[^\n@]+)", str(doc.summary))
            if ex_match:
                examples.append({
                    "input": ex_match.group("code").strip(),
                    "output": "see function documentation",
                })

        return BehaviorDict(
            name=snake_name,
            description=desc,
            given=given,
            when=when,
            then=then_,
            examples=examples,
            confidence=confidence,
            source_line=source[:offset].count("\n") + 1,
        )

    def _build_js_gwt(
        self,
        func_name: str,
        params: list,
        doc: _JSDoc | None,
        return_type: str,
        is_async: bool,
    ) -> tuple:
        """
        Build Given / When / Then for a JavaScript function.

        Args:
            func_name: Raw function name.
            params: Parsed parameter list.
            doc: Parsed JSDoc (may be None).
            return_type: Canonical return type.
            is_async: Whether function is async.

        Returns:
            Tuple of (given_list, when_list, then_list).
        """
        snake = _to_snake_case(func_name)
        human = re.sub(r"_", " ", snake)
        async_qualifier = "asynchronously " if is_async else ""

        given: list = []
        when: list = []
        then_: list = []

        # Given: parameter preconditions
        for p in params[:4]:
            if doc and p.name in doc.params:
                info = doc.params[p.name]
                desc = info.get("description", "")
                if desc:
                    given.append(f"{p.name} is provided: {desc[:80]}")
                    continue
            if p.required:
                given.append(f"{p.name} is provided")
            else:
                given.append(f"{p.name} is optional (defaults to {p.default or 'undefined'})")

        if not given:
            given = ["required dependencies are available"]

        # When
        when = [f"{human} is {async_qualifier}called"]

        # Then
        if doc and doc.returns:
            ret_desc = doc.returns.get("description", "")
            if ret_desc:
                then_.append(_truncate_description(ret_desc, 100))
            elif doc.returns.get("type"):
                then_.append(f"{doc.returns['type']} is returned")
        elif return_type and return_type not in ("null", "object"):
            if is_async:
                then_.append(f"Promise resolves with {return_type}")
            else:
                then_.append(f"{return_type} result is returned")
        else:
            then_.append(f"{human} completes successfully")

        if doc:
            for throw_info in doc.throws[:2]:
                t = throw_info.get("type", "Error")
                d = throw_info.get("description", "")
                if d:
                    then_.append(f"throws {t}: {d[:60]}")
                else:
                    then_.append(f"throws {t} on invalid input")

        return given[:5], when[:2], then_[:5]

    # ------------------------------------------------------------------
    # Rule extraction
    # ------------------------------------------------------------------

    def extract_rules(self, source: str) -> list:
        """
        Extract JavaScript business rules from conditional logic.

        Strategies:
        1. ``if``/``else if`` with rule-language JSDoc/comment above
        2. Guard clauses: ``if (!cond) { throw new Error(...) }``
        3. Explicit ``// RULE:`` or ``// BUSINESS RULE:`` comments

        Args:
            source: JavaScript / TypeScript source code text.

        Returns:
            List of :class:`RuleDict` instances.
        """
        rules = []
        seen_names: set = set()
        lines = source.split("\n")

        rule_re = re.compile(
            r"\b(must|should|cannot|require[sd]?|ensure[sd]?|valid|enforce|"
            r"guard|restrict|allow|deny|prevent|reject|check|assert|verify|"
            r"only if|except when)\b",
            re.IGNORECASE,
        )

        # Strategy 1: if/else if with rule-language comment
        for i, line in enumerate(lines):
            if len(rules) >= self.max_rules:
                break

            if not re.match(r"^\s*(?:}\s*else\s+)?if\s*\(", line):
                continue

            comment = self._get_preceding_comment(lines, i)
            if not comment or not rule_re.search(comment):
                continue

            cond_match = re.match(r"^\s*(?:}\s*else\s+)?if\s*\((?P<expr>[^)]+)\)", line)
            condition = (
                f"when {cond_match.group('expr').strip()}" if cond_match
                else "when condition is met"
            )

            name = self._derive_rule_name(comment)
            if name in seen_names:
                continue
            seen_names.add(name)

            rules.append(RuleDict(
                name=name,
                description=_truncate_description(comment),
                condition=condition[:200],
                action=f"then {_truncate_description(comment, 80)}",
                confidence=0.6,
                source_line=i + 1,
            ))

        # Strategy 2: guard clauses
        for match in _JS_GUARD_RE.finditer(source):
            if len(rules) >= self.max_rules:
                break

            negated = match.group("negated") or ""
            cond = match.group("cond").strip()
            full_cond = f"!{cond}" if negated else cond
            line_no = source[:match.start()].count("\n") + 1

            name = _to_snake_case(f"guard_{cond[:30]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            rules.append(RuleDict(
                name=name,
                description=f"Guard clause: validates that {cond}",
                condition=f"when {full_cond}",
                action="then throw Error",
                confidence=0.65,
                source_line=line_no,
            ))

        # Strategy 3: explicit RULE: comments
        rule_comment_re = re.compile(
            r"^\s*//\s*(?:RULE|BUSINESS RULE|POLICY)\s*:\s*(?P<text>.+)$",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in rule_comment_re.finditer(source):
            if len(rules) >= self.max_rules:
                break

            text = match.group("text").strip()
            name = self._derive_rule_name(text)
            if name in seen_names:
                continue
            seen_names.add(name)

            rules.append(RuleDict(
                name=name,
                description=_truncate_description(text),
                condition="when rule condition is met",
                action=f"then {_truncate_description(text, 80)}",
                confidence=0.7,
            ))

        return rules

    def _get_preceding_comment(self, lines: list, line_index: int) -> str:
        """
        Extract JS single-line comments (``// ...``) immediately above a line.

        Args:
            lines: All source lines.
            line_index: 0-based target line index.

        Returns:
            Combined comment text, or empty string.
        """
        parts = []
        i = line_index - 1
        while i >= 0 and not lines[i].strip():
            i -= 1
        while i >= 0 and re.match(r"^\s*//", lines[i]):
            parts.insert(0, re.sub(r"^\s*//+\s*", "", lines[i]).strip())
            i -= 1
        return " ".join(parts)

    def _derive_rule_name(self, text: str) -> str:
        """
        Derive a snake_case rule name from comment text.

        Args:
            text: Source text.

        Returns:
            snake_case rule name.
        """
        stop = {
            "the", "a", "an", "is", "are", "if", "then", "and", "or",
            "in", "of", "to", "for", "on", "at", "by", "this", "that",
            "must", "should", "when", "will", "can", "cannot",
        }
        words = re.findall(r"[a-z]+", text.lower())
        sig = [w for w in words if w not in stop][:5]
        return "_".join(sig) if sig else "rule"

    # ------------------------------------------------------------------
    # Constraint extraction
    # ------------------------------------------------------------------

    def extract_constraints(self, source: str) -> list:
        """
        Extract JavaScript constraints from constants, throws, and timeouts.

        Strategies:
        1. ``const UPPER_CASE = value`` → limit/timeout constraint
        2. ``throw new XxxError("...")`` with descriptive message → invariant
        3. ``setTimeout(fn, ms)`` → timeout constraint

        Args:
            source: JavaScript / TypeScript source code text.

        Returns:
            List of :class:`ConstraintDict` instances.
        """
        constraints = []
        seen_names: set = set()

        # 1. Uppercase constants
        for match in _JS_CONST_RE.finditer(source):
            raw_name = match.group("name")
            value = match.group("value").strip().rstrip(";,")
            line_no = source[:match.start()].count("\n") + 1

            name = _to_snake_case(raw_name)
            if name in seen_names:
                continue
            seen_names.add(name)

            upper = raw_name.upper()
            if any(k in upper for k in ("TIMEOUT", "TTL", "EXPIR", "WAIT", "DELAY", "INTERVAL")):
                ctype = "timeout"
            elif any(k in upper for k in ("MAX", "MIN", "LIMIT", "SIZE", "LENGTH",
                                          "COUNT", "CAPACITY", "THRESHOLD", "RATE")):
                ctype = "limit"
            else:
                continue  # Skip non-meaningful constants

            constraints.append(ConstraintDict(
                name=name,
                description=f"Constant {raw_name} defines a {ctype}",
                type=ctype,
                value=str(value),
                confidence=0.75,
                source_line=line_no,
            ))

        # 2. throw new XxxError("message")
        for match in _JS_THROW_RE.finditer(source):
            exc = match.group("exc")
            msg = match.group("msg") or match.group("tmsg") or ""
            if not msg:
                continue

            line_no = source[:match.start()].count("\n") + 1
            name = _to_snake_case(f"validation_{exc}_{msg[:20]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=_truncate_description(msg),
                type="invariant",
                value=f"throw {exc}: {msg[:100]}",
                confidence=0.7,
                source_line=line_no,
            ))

        # 3. setTimeout / setInterval
        for match in _JS_TIMEOUT_RE.finditer(source):
            ms = int(match.group("ms"))
            seconds = ms / 1000
            display = f"{ms}ms" if seconds < 1 else f"{int(seconds)}s"
            name = f"timeout_{display.replace('.', '_')}"
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=f"Timeout or interval of {display} found in source",
                type="timeout",
                value=display,
                confidence=0.65,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        return constraints
