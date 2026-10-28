"""
patterns/python.py - Python-specific BDD spec extraction.

Extracts spec components from Python source code using Python-aware regex
patterns rather than AST parsing (keeping stdlib-only dependency).

Supported Python constructs:
    Entities:
        - ``class Foo:`` definitions → EntityDict
        - Dataclass fields (``field: Type = default``) → PropertyDict
        - ``__init__`` parameter lists → PropertyDict

    Behaviors:
        - ``def foo(...)`` / ``async def foo(...)`` → BehaviorDict
        - Google-style and NumPy-style docstrings parsed for
          Args / Returns / Raises sections
        - ``@property`` methods treated as computed properties (entity)
        - ``@abstractmethod`` marked with higher confidence

    Rules:
        - ``if``/``elif``/``else`` blocks preceded by an explanatory comment
        - Guard clauses (``if not ...: raise``)
        - Inline ``# RULE:`` / ``# BUSINESS RULE:`` annotations

    Constraints:
        - ``assert expr, "message"`` statements
        - ``raise ValueError("...")`` with descriptive message
        - Class-level ``MAX_*`` / ``MIN_*`` / ``TIMEOUT_*`` constants
        - ``@dataclass`` validator patterns

Confidence tiers (Python-specific):
    1.0 - Full docstring with Args/Returns/Raises sections
    0.9 - Partial docstring (summary only)
    0.8 - Type hints present (no docstring)
    0.7 - Decorator present (@abstractmethod, @property)
    0.6 - Plain def with no annotation
    0.5 - Inferred from naming alone
"""

from __future__ import annotations

import re
import sys
import os
import textwrap

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
# Python-specific compiled patterns
# ---------------------------------------------------------------------------

# Class definition (with optional bases and decorators above)
_PY_CLASS_RE = re.compile(
    r"^(?P<indent>\s*)class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*\((?P<bases>[^)]*)\))?\s*:",
    re.MULTILINE,
)

# Function / method definition (including async)
_PY_DEF_RE = re.compile(
    r"^(?P<indent>\s*)(?P<decorators>(?:@\S+\s*\n)*)"
    r"(?P<async>async\s+)?def\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)"
    r"(?:\s*->\s*(?P<return_type>[^:]+))?\s*:",
    re.MULTILINE,
)

# Decorator (for look-behind extraction)
_PY_DECORATOR_RE = re.compile(r"^\s*@(?P<dec>[A-Za-z_][\w.]*(?:\([^)]*\))?)", re.MULTILINE)

# Triple-quoted docstring (any quote style)
_PY_DOCSTRING_RE = re.compile(
    r'(?P<indent>\s*)(?:"""(?P<dq>.*?)"""|\'\'\'(?P<sq>.*?)\'\'\')',
    re.DOTALL,
)

# Dataclass field annotation: field_name: Type [= default]
_PY_FIELD_ANNOTATION_RE = re.compile(
    r"^(?P<indent>\s+)(?P<name>[a-z_][A-Za-z0-9_]*)\s*:\s*"
    r"(?P<type>[A-Za-z_][\w\[\], |]*)"
    r"(?:\s*=\s*(?P<default>[^\n#]+))?",
    re.MULTILINE,
)

# Assert statement: assert expr [, "message"]
_PY_ASSERT_RE = re.compile(
    r"^\s*assert\s+(?P<expr>[^,\n]+)"
    r"(?:,\s*(?P<msg>[\"'][^\"']+[\"']|f[\"'][^\"']+[\"']))?",
    re.MULTILINE,
)

# raise ValueError("...") / raise TypeError("...") patterns
_PY_RAISE_RE = re.compile(
    r"^\s*raise\s+(?P<exc>[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Warning)?)\s*"
    r"\(\s*(?:f?[\"'](?P<msg>[^\"']{10,})[\"'])?\s*\)",
    re.MULTILINE,
)

# Constant assignment at module/class level: MAX_RETRIES = 3
_PY_CONST_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[A-Z][A-Z0-9_]{2,})\s*(?::\s*\w+\s*)?=\s*(?P<value>[^\n#]+)",
    re.MULTILINE,
)

# Guard clause: if not ...: raise ...
_PY_GUARD_RE = re.compile(
    r"^\s*if\s+(?:not\s+)?(?P<cond>[^:]+):\s*\n\s*raise\s+(?P<exc>\w+)",
    re.MULTILINE,
)

# if / elif patterns for rule extraction
_PY_IF_RE = re.compile(
    r"^\s*(?P<kw>if|elif)\s+(?P<expr>[^:]+):",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Docstring parser
# ---------------------------------------------------------------------------

class _PythonDocstring:
    """
    Minimal parser for Google-style and NumPy-style Python docstrings.

    Attributes:
        summary:  First paragraph of the docstring.
        args:     Dict mapping arg name → description.
        returns:  Return description string.
        raises:   Dict mapping exception name → description.
        notes:    Additional note text.
    """

    def __init__(self, raw: str) -> None:
        self.summary: str = ""
        self.args: dict = {}
        self.returns: str = ""
        self.raises: dict = {}
        self.notes: str = ""
        self._parse(textwrap.dedent(raw).strip())

    def _parse(self, text: str) -> None:
        """Parse a dedented docstring into structured sections."""
        lines = text.split("\n")

        # Summary: everything before the first blank line or section header
        summary_lines = []
        i = 0
        while i < len(lines) and lines[i].strip() and not self._is_section_header(lines[i]):
            summary_lines.append(lines[i].strip())
            i += 1
        self.summary = " ".join(summary_lines)

        # Parse sections
        current_section: str = ""
        section_lines: list = []

        while i < len(lines):
            line = lines[i]
            if self._is_section_header(line):
                # Flush previous section
                if current_section and section_lines:
                    self._flush_section(current_section, section_lines)
                current_section = line.strip().rstrip(":").lower()
                section_lines = []
            else:
                section_lines.append(line)
            i += 1

        if current_section and section_lines:
            self._flush_section(current_section, section_lines)

    @staticmethod
    def _is_section_header(line: str) -> bool:
        """Return True if line is a Google/NumPy section header."""
        stripped = line.strip()
        # Google style: "Args:", "Returns:", "Raises:", "Notes:", "Example:"
        if re.match(r"^(Args|Arguments|Returns|Return|Raises|Notes|Note|"
                    r"Example|Examples|Attributes|Parameters|Yields?)\s*:", stripped):
            return True
        # NumPy style: "Parameters\n----------"
        if re.match(r"^(Parameters|Returns?|Raises?|Notes?|Examples?)\s*$", stripped):
            return True
        return False

    def _flush_section(self, section: str, lines: list) -> None:
        """Process collected lines for a named section."""
        if section in ("args", "arguments", "parameters"):
            self.args = self._parse_args_section(lines)
        elif section in ("returns", "return", "yields", "yield"):
            self.returns = " ".join(
                l.strip() for l in lines if l.strip() and not l.strip().startswith("---")
            )
        elif section in ("raises", "raise"):
            self.raises = self._parse_raises_section(lines)
        elif section in ("notes", "note"):
            self.notes = " ".join(l.strip() for l in lines if l.strip())

    def _parse_args_section(self, lines: list) -> dict:
        """
        Parse Google-style Args section.

        Handles::
            param_name (Type): description...
            param_name: description...
        """
        args: dict = {}
        current_name: str = ""
        current_desc: list = []

        for line in lines:
            # Ignore NumPy separator lines
            if re.match(r"^\s*-+\s*$", line):
                continue
            # New arg entry: "    name (type): desc"  or  "    name: desc"
            m = re.match(
                r"^\s{2,4}(?P<name>\w+)\s*(?:\([^)]*\))?\s*:\s*(?P<desc>.*)", line
            )
            if m:
                if current_name:
                    args[current_name] = " ".join(current_desc).strip()
                current_name = m.group("name")
                current_desc = [m.group("desc").strip()]
            elif current_name and line.startswith("        "):
                # Continuation line
                current_desc.append(line.strip())

        if current_name:
            args[current_name] = " ".join(current_desc).strip()

        return args

    def _parse_raises_section(self, lines: list) -> dict:
        """Parse Google-style Raises section."""
        raises: dict = {}
        current_exc: str = ""
        current_desc: list = []

        for line in lines:
            if re.match(r"^\s*-+\s*$", line):
                continue
            m = re.match(r"^\s{2,4}(?P<exc>[A-Za-z_]\w*)\s*:\s*(?P<desc>.*)", line)
            if m:
                if current_exc:
                    raises[current_exc] = " ".join(current_desc).strip()
                current_exc = m.group("exc")
                current_desc = [m.group("desc").strip()]
            elif current_exc and line.startswith("        "):
                current_desc.append(line.strip())

        if current_exc:
            raises[current_exc] = " ".join(current_desc).strip()

        return raises


def _extract_py_docstring(source: str, def_start: int) -> tuple:
    """
    Extract the docstring immediately following a ``def`` or ``class`` statement.

    Args:
        source: Full source text.
        def_start: Character offset of the ``def``/``class`` keyword.

    Returns:
        Tuple of (raw_docstring_text, end_offset).  Returns ("", def_start)
        if no docstring is present.
    """
    # Find the colon ending the definition
    colon_pos = source.find(":", def_start)
    if colon_pos == -1:
        return "", def_start

    rest = source[colon_pos + 1:]
    # Skip whitespace/newline to the first non-empty token
    stripped = rest.lstrip(" \t\n\r")
    offset = colon_pos + 1 + (len(rest) - len(stripped))

    # Check for triple-quote opening
    for quote in ('"""', "'''"):
        if stripped.startswith(quote):
            end_quote = stripped.find(quote, len(quote))
            if end_quote != -1:
                raw = stripped[len(quote):end_quote]
                return raw, offset + end_quote + len(quote)
    return "", def_start


def _get_decorators_before(source: str, def_start: int) -> list:
    """
    Collect decorator names that appear immediately before a def/class.

    Args:
        source: Full source text.
        def_start: Character offset of the ``def``/``class`` keyword.

    Returns:
        List of decorator name strings (e.g. ["property", "abstractmethod"]).
    """
    # Look at the 5 lines before the definition
    pre = source[:def_start]
    lines = pre.split("\n")
    decorators = []
    for line in reversed(lines[-6:]):
        m = re.match(r"^\s*@(?P<dec>[A-Za-z_][\w.]*)", line)
        if m:
            decorators.insert(0, m.group("dec"))
        elif line.strip() and not line.strip().startswith("#"):
            break  # Hit non-decorator, non-comment line
    return decorators


# ---------------------------------------------------------------------------
# Python type-hint normalisation
# ---------------------------------------------------------------------------

def _parse_py_type(raw: str) -> str:
    """
    Convert a Python type hint string to a canonical spec type.

    Handles:
        - ``Optional[X]`` → canonical type of X
        - ``Union[X, None]`` → canonical type of X
        - ``List[X]`` / ``list[X]`` → array
        - ``Dict[K, V]`` / ``dict[K, V]`` → object
        - Plain names delegated to :func:`_normalize_type`

    Args:
        raw: Raw Python type annotation string.

    Returns:
        Canonical spec type string.
    """
    s = raw.strip()

    # Optional[X] → X
    m = re.match(r"Optional\[(.+)\]", s)
    if m:
        return _parse_py_type(m.group(1))

    # Union[X, None] or Union[X, Y] → first non-None type
    m = re.match(r"Union\[(.+)\]", s)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        non_none = [p for p in parts if p.lower() not in ("none", "nonetype")]
        return _parse_py_type(non_none[0]) if non_none else "null"

    # X | None  (Python 3.10+ union syntax)
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        non_none = [p for p in parts if p.lower() not in ("none", "nonetype")]
        return _parse_py_type(non_none[0]) if non_none else "null"

    # List-like generics
    if re.match(r"(?:List|list|Tuple|tuple|Set|set|Sequence|Iterable)\[", s):
        return "array"

    # Dict-like generics
    if re.match(r"(?:Dict|dict|Mapping|OrderedDict)\[", s):
        return "object"

    # Literal[...] → string
    if s.startswith("Literal["):
        return "string"

    return _normalize_type(s)


# ---------------------------------------------------------------------------
# Parameter list parser
# ---------------------------------------------------------------------------

def _parse_py_params(param_str: str, docstring: _PythonDocstring | None = None) -> list:
    """
    Parse a Python function parameter string into :class:`PropertyDict` objects.

    Handles:
        - Positional: ``name``
        - Annotated: ``name: Type``
        - Defaulted: ``name: Type = default``
        - ``*args`` / ``**kwargs``

    Skips ``self`` and ``cls``.

    Args:
        param_str: Raw parameter string between parentheses.
        docstring: Optional parsed docstring for enriching descriptions.

    Returns:
        List of :class:`PropertyDict` instances.
    """
    if not param_str.strip():
        return []

    props = []
    # Split on commas, respecting nested brackets
    parts = _split_py_params(param_str)

    for part in parts:
        part = part.strip()
        if not part or part in ("self", "cls", "*", "/"):
            continue
        if part.startswith("*") and not part.startswith("**"):
            # *args — variadic positional
            name = part.lstrip("*").split(":")[0].strip()
            props.append(PropertyDict(
                name=name or "args",
                type="array",
                required=False,
                description=f"Variadic positional arguments",
                confidence=0.7,
            ))
            continue
        if part.startswith("**"):
            # **kwargs — variadic keyword
            name = part.lstrip("*").split(":")[0].strip()
            props.append(PropertyDict(
                name=name or "kwargs",
                type="object",
                required=False,
                description="Variadic keyword arguments",
                confidence=0.7,
            ))
            continue

        name = "param"
        ptype = "string"
        default = None
        confidence = 0.7

        # Strip default
        if "=" in part:
            param_part, default_raw = part.split("=", 1)
            default = default_raw.strip()
            part = param_part.strip()

        # Type annotation: name: Type
        if ":" in part:
            name_part, type_part = part.split(":", 1)
            name = _clean_identifier(name_part.strip())
            ptype = _parse_py_type(type_part.strip())
            confidence = 0.85
        else:
            name = _clean_identifier(part)
            confidence = 0.65

        # Enrich description from docstring
        desc = ""
        if docstring and name in docstring.args:
            desc = _truncate_description(docstring.args[name], 100)
            confidence = min(1.0, confidence + 0.15)

        props.append(PropertyDict(
            name=name,
            type=ptype,
            required=(default is None),
            description=desc or f"Parameter {name}",
            default=default,
            confidence=confidence,
        ))

    return props


def _split_py_params(param_str: str) -> list:
    """
    Split a Python parameter string on top-level commas.

    Respects nesting inside ``[]``, ``()``, ``{}``, and ``<>``.

    Args:
        param_str: Raw parameter string.

    Returns:
        List of individual parameter sub-strings.
    """
    parts = []
    buf = []
    depth = 0
    for ch in param_str:
        if ch in ("[", "(", "{", "<"):
            depth += 1
            buf.append(ch)
        elif ch in ("]", ")", "}", ">"):
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
# Python extractor
# ---------------------------------------------------------------------------

class PythonExtractor(BaseExtractor):
    """
    Python-specific spec extractor.

    Understands Python syntax including:
    - ``class``/``dataclass`` definitions → entities
    - ``def``/``async def`` → behaviors
    - ``if``/``guard`` patterns → rules
    - ``assert``/``raise``/constant literals → constraints
    - Google-style and NumPy-style docstrings
    - Type hints (return types, parameters)
    - Decorators (``@property``, ``@abstractmethod``, etc.)

    Args:
        confidence_threshold: Minimum confidence to include an item.
        module_name: Override module name.
        skip_private: If True (default), skip methods whose names start with
            a single underscore.  Dunder methods are always skipped.
        max_behaviors: Maximum number of behaviors to extract per file.
        max_rules: Maximum number of rules to extract per file.
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
        Extract Python class definitions as spec entities.

        Processes:
        - Regular classes → EntityDict with properties from __init__ params
        - Dataclasses → EntityDict with field annotations as properties
        - NamedTuple subclasses → EntityDict with field annotations

        Skips:
        - Test/mock/base classes (low signal-to-noise)
        - Classes with no meaningful body

        Args:
            source: Python source code text.

        Returns:
            List of :class:`EntityDict` instances.
        """
        entities = []
        seen_names: set = set()

        for match in _PY_CLASS_RE.finditer(source):
            raw_name = match.group("name")
            bases = match.group("bases") or ""

            # Skip utility/test classes
            lower_name = raw_name.lower()
            if any(
                lower_name.startswith(s) or lower_name.endswith(s)
                for s in ("test", "mock", "stub", "fake", "fixture", "mixin",
                          "abstract", "base")
            ):
                continue

            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            # Detect decorators for this class
            decorators = _get_decorators_before(source, match.start())
            is_dataclass = "dataclass" in decorators

            # Extract docstring
            doc_raw, _ = _extract_py_docstring(source, match.start())
            doc = _PythonDocstring(doc_raw) if doc_raw else None
            summary = doc.summary if doc else ""

            desc = _truncate_description(summary) if summary else f"Data entity {raw_name}"

            # Determine confidence
            confidence = 0.9 if doc else 0.7
            if is_dataclass:
                confidence = 1.0

            # Extract properties
            if is_dataclass or "TypedDict" in bases or "NamedTuple" in bases:
                props = self._extract_dataclass_fields(source, match.end())
            else:
                props = self._extract_init_params(source, match.end())

            entities.append(EntityDict(
                name=pascal,
                description=desc,
                properties=props,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        return entities

    def _extract_dataclass_fields(self, source: str, class_end: int) -> list:
        """
        Extract field annotations from a dataclass or TypedDict body.

        Looks for patterns like ``field_name: Type [= default]`` at class
        indentation level (one level deeper than the class header).

        Args:
            source: Full source text.
            class_end: Character offset immediately after the ``:`` of the class line.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        # Get the class body: look ahead for indented lines
        rest = source[class_end:]
        lines = rest.split("\n")

        # Find first non-empty line to determine body indentation
        body_indent: int | None = None
        props = []
        seen: set = set()

        for line in lines[:60]:  # Look at max 60 lines ahead
            stripped = line.strip()
            if not stripped:
                continue
            indent = len(line) - len(line.lstrip())

            if body_indent is None:
                body_indent = indent
            elif indent < body_indent:
                # We've left the class body
                break
            elif indent != body_indent:
                # Nested content, skip
                continue

            # field: Type [= default]
            m = re.match(
                r"^(?P<name>[a-z_][A-Za-z0-9_]*)\s*:\s*"
                r"(?P<type>[A-Za-z_][\w\[\], |]*)"
                r"(?:\s*=\s*(?P<default>[^\n#]+))?",
                stripped,
            )
            if m:
                name = m.group("name")
                if name in seen or name in ("pass", "return"):
                    continue
                seen.add(name)
                default_raw = m.group("default")
                default = default_raw.strip().rstrip(",") if default_raw else None
                # field(default=...) → extract actual default
                if default and default.startswith("field("):
                    dflt_match = re.search(r"default(?:_factory)?\s*=\s*([^,)]+)", default)
                    default = dflt_match.group(1).strip() if dflt_match else None

                props.append(PropertyDict(
                    name=name,
                    type=_parse_py_type(m.group("type")),
                    required=(default is None),
                    description=f"Field {name}",
                    default=default,
                    confidence=0.9,
                ))

        return props[:20]

    def _extract_init_params(self, source: str, class_end: int) -> list:
        """
        Extract properties from a class's ``__init__`` method parameters.

        Searches within the first 100 lines of the class body for a
        ``def __init__(self, ...)`` definition.

        Args:
            source: Full source text.
            class_end: Character offset after the class header colon.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        rest = source[class_end:]
        # Find __init__
        init_match = re.search(
            r"def\s+__init__\s*\(\s*self\s*,?\s*(?P<params>[^)]*)\)",
            rest[:3000],  # Look within reasonable distance
        )
        if not init_match:
            # Try to find field-style annotations (non-dataclass)
            return self._extract_dataclass_fields(source, class_end)

        param_str = init_match.group("params")
        # Extract docstring of __init__
        doc_raw, _ = _extract_py_docstring(rest, init_match.start())
        doc = _PythonDocstring(doc_raw) if doc_raw else None

        return _parse_py_params(param_str, doc)

    # ------------------------------------------------------------------
    # Behavior extraction
    # ------------------------------------------------------------------

    def extract_behaviors(self, source: str) -> list:
        """
        Extract Python function and method definitions as behaviors.

        Processing rules:
        - Module-level functions and class methods are both included.
        - ``__init__``, ``__repr__``, ``__eq__`` (and all dunder methods)
          are skipped.
        - Private methods (``_name``) are skipped when ``skip_private=True``.
        - ``@property`` methods are treated as read behaviors with low
          confidence (they are more entity properties than behaviors).
        - ``async def`` methods are given a ``when`` clause that notes
          the async call.

        Args:
            source: Python source code text.

        Returns:
            List of :class:`BehaviorDict` instances.
        """
        behaviors = []
        seen_names: set = set()
        lines = source.split("\n")

        for match in _PY_DEF_RE.finditer(source):
            if len(behaviors) >= self.max_behaviors:
                break

            raw_name = match.group("name")

            # Skip dunder methods
            if raw_name.startswith("__") and raw_name.endswith("__"):
                continue

            # Skip private methods
            if self.skip_private and raw_name.startswith("_") and not raw_name.startswith("__"):
                continue

            # Skip test functions
            if raw_name.startswith("test_") or raw_name.endswith("_test"):
                continue

            snake_name = _to_snake_case(raw_name)
            if snake_name in seen_names:
                continue
            seen_names.add(snake_name)

            # Decorators
            decorators = _get_decorators_before(source, match.start())
            is_property = "property" in decorators or "cached_property" in decorators
            is_abstract = "abstractmethod" in decorators
            is_async = bool(match.group("async"))
            is_static = "staticmethod" in decorators
            is_class_method = "classmethod" in decorators

            # Return type hint
            return_type_raw = match.group("return_type") or ""
            return_type = _parse_py_type(return_type_raw.strip()) if return_type_raw else ""

            # Extract docstring
            doc_raw, _ = _extract_py_docstring(source, match.start())
            doc = _PythonDocstring(doc_raw) if doc_raw else None

            # Parameters
            param_str = match.group("params") or ""
            # Remove 'self' / 'cls' — they are already stripped in _parse_py_params
            params = _parse_py_params(param_str, doc)

            # Description
            if doc and doc.summary:
                desc = _truncate_description(doc.summary)
                confidence = 1.0
            elif return_type or params:
                desc = f"Executes {raw_name} operation"
                confidence = 0.8
            else:
                desc = f"Performs {raw_name}"
                confidence = 0.6 if not is_property else 0.5

            if is_abstract:
                confidence = min(1.0, confidence + 0.1)

            # Build GWT
            given, when, then_ = self._build_py_gwt(
                raw_name, params, doc, return_type, is_async,
                is_property, is_static, is_class_method,
            )

            # Examples from docstring
            examples = []
            if doc and doc.notes:
                m_ex = re.search(r">>>\s*(?P<call>[^\n]+)\n\s*(?P<result>[^\n]+)", doc.notes)
                if m_ex:
                    examples.append({
                        "input": m_ex.group("call").strip(),
                        "output": m_ex.group("result").strip(),
                    })

            line_no = source[:match.start()].count("\n") + 1

            behaviors.append(BehaviorDict(
                name=snake_name,
                description=desc,
                given=given,
                when=when,
                then=then_,
                examples=examples,
                confidence=confidence,
                source_line=line_no,
            ))

        return behaviors

    def _build_py_gwt(
        self,
        func_name: str,
        params: list,
        doc: _PythonDocstring | None,
        return_type: str,
        is_async: bool,
        is_property: bool,
        is_static: bool,
        is_class_method: bool,
    ) -> tuple:
        """
        Build Given/When/Then lists for a Python function.

        Args:
            func_name: Raw function name.
            params: Parsed parameter list.
            doc: Parsed docstring (may be None).
            return_type: Canonical return type string.
            is_async: Whether function is async.
            is_property: Whether function is a @property.
            is_static: Whether function is @staticmethod.
            is_class_method: Whether function is @classmethod.

        Returns:
            Tuple of (given_list, when_list, then_list).
        """
        snake = _to_snake_case(func_name)
        human = re.sub(r"_", " ", snake)

        given: list = []
        when: list = []
        then_: list = []

        # Given: parameter preconditions
        for p in params[:4]:
            if p.required:
                hint = doc.args.get(p.name, "") if doc else ""
                if hint:
                    given.append(f"{p.name} is provided: {hint[:80]}")
                else:
                    given.append(f"{p.name} is provided")
            else:
                given.append(f"{p.name} is optional, defaults to {p.default or 'unset'}")

        if not given:
            if is_static or is_class_method:
                given = [f"class is accessible"]
            else:
                given = ["object is in valid state"]

        # When
        async_qualifier = "asynchronously " if is_async else ""
        if is_property:
            when = [f"{human} property is {async_qualifier}accessed"]
        else:
            when = [f"{human} is {async_qualifier}called"]

        # Then: from @returns docstring, raise info, return type
        if doc and doc.returns:
            then_.append(_truncate_description(doc.returns, 100))
        elif return_type and return_type != "null":
            then_.append(f"{return_type} result is returned")
        else:
            then_.append(f"{human} completes successfully")

        if doc and doc.raises:
            for exc, exc_desc in list(doc.raises.items())[:2]:
                if exc_desc:
                    then_.append(f"raises {exc}: {exc_desc[:60]}")
                else:
                    then_.append(f"raises {exc} on invalid input")

        return given[:5], when[:2], then_[:5]

    # ------------------------------------------------------------------
    # Rule extraction
    # ------------------------------------------------------------------

    def extract_rules(self, source: str) -> list:
        """
        Extract Python business rules from conditional logic.

        Detection strategies:
        1. ``if``/``elif`` with a preceding explanatory comment that uses
           rule language (must/should/cannot/requires/ensures).
        2. Guard clauses: ``if not cond: raise ExceptionType``
        3. Inline ``# RULE:`` / ``# BUSINESS RULE:`` comments.

        Args:
            source: Python source code text.

        Returns:
            List of :class:`RuleDict` instances.
        """
        rules = []
        lines = source.split("\n")
        seen_names: set = set()

        # Strategy 1: if/elif with rule-language comment above
        rule_re = re.compile(
            r"\b(must|should|cannot|only if|require[sd]?|ensure[sd]?|"
            r"valid|enforce|guard|restrict|allow|deny|prevent|reject|check)\b",
            re.IGNORECASE,
        )

        for i, line in enumerate(lines):
            if len(rules) >= self.max_rules:
                break

            if not re.match(r"^\s*(?:if|elif)\s", line):
                continue

            # Look for rule-language comment above
            comment = self._get_preceding_comment(lines, i)
            if not comment or not rule_re.search(comment):
                continue

            cond_match = re.match(r"^\s*(?:if|elif)\s+(?P<expr>.+):", line)
            condition = (
                f"when {cond_match.group('expr').strip()}" if cond_match
                else "when condition is met"
            )

            name = self._derive_py_rule_name(comment)
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
        for match in _PY_GUARD_RE.finditer(source):
            if len(rules) >= self.max_rules:
                break

            cond = match.group("cond").strip()
            exc = match.group("exc")
            line_no = source[:match.start()].count("\n") + 1

            name = _to_snake_case(f"guard_{cond[:30]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            rules.append(RuleDict(
                name=name,
                description=f"Guard clause: validates that {cond}",
                condition=f"when {cond}",
                action=f"then raise {exc}",
                confidence=0.65,
                source_line=line_no,
            ))

        # Strategy 3: explicit RULE: comments
        rule_comment_re = re.compile(
            r"^\s*#\s*(?:RULE|BUSINESS RULE|POLICY)\s*:\s*(?P<text>.+)$",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in rule_comment_re.finditer(source):
            if len(rules) >= self.max_rules:
                break

            text = match.group("text").strip()
            name = self._derive_py_rule_name(text)
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
        Extract single-line Python comments (``# ...``) immediately above a line.

        Skips blank lines but stops at the first non-comment, non-blank line.

        Args:
            lines: All source lines as a list.
            line_index: 0-based index of the target line.

        Returns:
            Combined comment text, or empty string.
        """
        comment_parts = []
        i = line_index - 1
        while i >= 0 and not lines[i].strip():
            i -= 1
        while i >= 0 and re.match(r"^\s*#", lines[i]):
            comment_parts.insert(0, re.sub(r"^\s*#+\s*", "", lines[i]).strip())
            i -= 1
        return " ".join(comment_parts)

    def _derive_py_rule_name(self, text: str) -> str:
        """
        Derive a snake_case rule name from a comment or description.

        Args:
            text: Source text to derive name from.

        Returns:
            snake_case rule name string.
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
        Extract Python constraints from assertions, raises, and constants.

        Detection strategies:
        1. ``assert expr, "message"`` → invariant constraint
        2. ``raise ValueError("...")`` → invariant (validation rule)
        3. Module/class-level ``UPPER_CASE_CONST = value`` → limit/timeout
        4. ``# @invariant:`` comments

        Args:
            source: Python source code text.

        Returns:
            List of :class:`ConstraintDict` instances.
        """
        constraints = []
        seen_names: set = set()

        # 1. Assert statements
        for match in _PY_ASSERT_RE.finditer(source):
            expr = match.group("expr").strip()
            msg_raw = match.group("msg") or ""
            msg = msg_raw.strip("\"'f")

            # Only include asserts with a descriptive message or clear expression
            if not msg and len(expr) < 10:
                continue

            line_no = source[:match.start()].count("\n") + 1
            name = _to_snake_case(f"assert_{expr[:25]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            desc = msg or f"Assertion: {expr[:100]}"
            constraints.append(ConstraintDict(
                name=name,
                description=_truncate_description(desc),
                type="invariant",
                value=f"assert {expr[:100]}",
                confidence=0.75,
                source_line=line_no,
            ))

        # 2. raise ValueError / TypeError with descriptive message
        for match in _PY_RAISE_RE.finditer(source):
            exc = match.group("exc")
            msg = match.group("msg") or ""
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
                value=f"raise {exc}: {msg[:100]}",
                confidence=0.7,
                source_line=line_no,
            ))

        # 3. Upper-case constants (module or class level)
        for match in _PY_CONST_RE.finditer(source):
            raw_name = match.group("name")
            value = match.group("value").strip().rstrip(",")
            indent = match.group("indent")

            # Only at module/class level (indent of 0 or 4)
            if len(indent) > 8:
                continue

            name = _to_snake_case(raw_name)
            if name in seen_names:
                continue
            seen_names.add(name)

            # Determine constraint type
            upper = raw_name.upper()
            if any(k in upper for k in ("TIMEOUT", "TTL", "EXPIR", "WAIT")):
                ctype = "timeout"
            elif any(k in upper for k in ("MAX", "MIN", "LIMIT", "SIZE", "LENGTH", "COUNT")):
                ctype = "limit"
            else:
                continue  # Skip non-meaningful constants

            constraints.append(ConstraintDict(
                name=name,
                description=f"Constant {raw_name} defines a {ctype}",
                type=ctype,
                value=str(value),
                confidence=0.7,
            ))

        # 4. Invariant comments (@invariant / @precondition / @postcondition)
        inv_comment_re = re.compile(
            r"^\s*#\s*@(?:invariant|precondition|postcondition)\s*:?\s*(?P<text>.+)$",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in inv_comment_re.finditer(source):
            text = match.group("text").strip()
            if not text or len(text) < 5:
                continue

            name = _to_snake_case(f"invariant_{text[:30]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=_truncate_description(text),
                type="invariant",
                value=text[:150],
                confidence=0.8,
            ))

        return constraints
