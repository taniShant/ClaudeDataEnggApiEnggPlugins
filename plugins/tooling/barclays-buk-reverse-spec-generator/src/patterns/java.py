"""
patterns/java.py - Java-specific BDD spec extraction.

Extracts spec components from Java source code using Java-aware regex patterns.

Supported Java constructs:
    Entities:
        - ``class Foo {`` / ``record Foo(...)`` / ``interface Foo {`` definitions
        - Field declarations with access modifiers and type annotations
        - JavaDoc ``@param`` / ``@return`` for field description enrichment
        - Record component lists

    Behaviors:
        - Public / protected / package-private method signatures
        - Full JavaDoc comment parsing (@param, @return, @throws)
        - ``@Override``, ``@Deprecated``, ``@Bean``, ``@RequestMapping`` decorators
        - Constructor patterns (when the class appears to be a service)
        - Spring MVC / JAX-RS endpoint annotations

    Rules:
        - Conditional logic (if/else) with JavaDoc-quality comment above
        - ``@Validate`` / ``@NotNull`` / ``@Size`` Bean Validation annotations
        - Guard patterns: ``if (cond) { throw new XxxException(...); }``

    Constraints:
        - ``assert expr : "message"`` → invariant
        - ``throw new XxxException("message")`` → validation invariant
        - Numeric magic-number constants (``public static final int MAX_...``)
        - ``@Min`` / ``@Max`` / ``@Size`` Bean Validation annotations → limit
        - ``@Timeout`` annotations → timeout

Confidence tiers (Java-specific):
    1.0 - Full JavaDoc with @param/@return/@throws
    0.9 - Partial JavaDoc (summary only)
    0.85 - Strong annotations (@Override, @NotNull, @Valid, @Bean)
    0.8  - Public method with type hints, no doc
    0.7  - Protected/package method
    0.6  - Private method with doc
    0.5  - Inferred from naming
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
# Java-specific compiled patterns
# ---------------------------------------------------------------------------

# Class / interface / record / enum definition
_JAVA_CLASS_RE = re.compile(
    r"(?P<mods>(?:(?:public|protected|private|abstract|final|static|sealed|"
    r"non-sealed)\s+)*)"
    r"(?P<kind>class|interface|record|enum)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*<[^>]*>)?"            # generic type params
    r"(?:\s+extends\s+[A-Za-z_][\w.<>, ]*)?"
    r"(?:\s+implements\s+[A-Za-z_][\w.<>, ]*)?"
    r"\s*(?:\((?P<record_params>[^)]*)\))?"   # record components
    r"\s*\{",
    re.MULTILINE,
)

# Field declaration: [modifiers] Type name [= default];
_JAVA_FIELD_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:private|protected|public|static|final|volatile|"
    r"transient|readonly)\s+)*)"
    r"(?P<type>[A-Za-z_][\w<>\[\], ]*)\s+"
    r"(?P<name>[a-z_][A-Za-z0-9_]*)"
    r"(?:\s*=\s*(?P<default>[^;{]+))?\s*;",
    re.MULTILINE,
)

# Method / constructor signature
_JAVA_METHOD_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|protected|private|static|final|abstract|"
    r"synchronized|native|default|override|@Override|@Deprecated)\s+)*)"
    r"(?P<return_type>[A-Za-z_][\w<>\[\], ]*)\s+"
    r"(?P<name>[a-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)"
    r"(?:\s*throws\s+(?P<throws>[A-Za-z_][\w, ]*))?"
    r"\s*\{",
    re.MULTILINE,
)

# Constructor: same as method but name starts with uppercase
_JAVA_CTOR_RE = re.compile(
    r"^\s*(?P<mods>(?:public|protected|private)\s+)"
    r"(?P<name>[A-Z][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)"
    r"(?:\s*throws\s+(?P<throws>[A-Za-z_][\w, ]*))?"
    r"\s*\{",
    re.MULTILINE,
)

# JavaDoc block: /** ... */
_JAVADOC_RE = re.compile(r"/\*\*\s*(?P<content>.*?)\*/", re.DOTALL)

# JavaDoc tags
_JAVADOC_PARAM_RE = re.compile(r"@param\s+(?P<name>\w+)\s+(?P<desc>[^\n@]+)")
_JAVADOC_RETURN_RE = re.compile(r"@return\s+(?P<desc>[^\n@]+)")
_JAVADOC_THROWS_RE = re.compile(r"@throws?\s+(?P<type>\w+)\s+(?P<desc>[^\n@]+)")
_JAVADOC_SEE_RE = re.compile(r"@see\s+(?P<ref>[^\n@]+)")

# Bean Validation / Jakarta constraints
_JAVA_ANNOTATION_RE = re.compile(
    r"@(?P<ann>[A-Za-z_][A-Za-z0-9_]*)(?:\s*\((?P<args>[^)]*)\))?",
    re.MULTILINE,
)
_JAVA_CONSTRAINT_ANNS = {
    "NotNull", "NotEmpty", "NotBlank", "Size", "Min", "Max",
    "DecimalMin", "DecimalMax", "Pattern", "Email", "Positive",
    "PositiveOrZero", "Negative", "NegativeOrZero", "Future",
    "Past", "PastOrPresent", "FutureOrPresent", "Digits",
    "AssertTrue", "AssertFalse",
}

# throw new XxxException("message")
_JAVA_THROW_RE = re.compile(
    r"throw\s+new\s+(?P<exc>[A-Za-z_][A-Za-z0-9_]*(?:Exception|Error|Fault)?)\s*"
    r"\(\s*(?:\"(?P<msg>[^\"]{5,})\")?",
)

# assert statement: assert expr : "message"
_JAVA_ASSERT_RE = re.compile(
    r"^\s*assert\s+(?P<expr>[^;:\n]+)"
    r"(?:\s*:\s*(?P<msg>[\"'][^\"']+[\"']))?\s*;",
    re.MULTILINE,
)

# public static final (int|long|String) NAME = value;
_JAVA_CONST_RE = re.compile(
    r"^\s*(?:public|protected)?\s*static\s+final\s+"
    r"(?P<type>int|long|double|float|String|Integer|Long)\s+"
    r"(?P<name>[A-Z][A-Z0-9_]{2,})\s*=\s*(?P<value>[^\s;]+)\s*;",
    re.MULTILINE,
)

# Guard pattern: if (...) { throw ... }
_JAVA_GUARD_RE = re.compile(
    r"if\s*\((?P<cond>[^)]+)\)\s*\{?\s*\n?\s*throw\s+new\s+(?P<exc>\w+)",
    re.MULTILINE,
)

# Spring/JAX-RS endpoint annotations
_JAVA_ENDPOINT_RE = re.compile(
    r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|"
    r"PatchMapping|Path|GET|POST|PUT|DELETE|PATCH)\s*"
    r'(?:\(\s*(?:value\s*=\s*)?["\']?(?P<path>[^"\'),]+)["\']?\s*\))?',
    re.MULTILINE,
)

# if/else conditional for rule extraction
_JAVA_IF_RE = re.compile(r"^\s*(?:if|else\s+if)\s*\((?P<expr>[^)]+)\)", re.MULTILINE)


# ---------------------------------------------------------------------------
# JavaDoc parser
# ---------------------------------------------------------------------------

class _JavaDoc:
    """
    Minimal parser for JavaDoc comment blocks.

    Attributes:
        summary:  First sentence/paragraph of the JavaDoc.
        params:   Dict mapping param name → description.
        returns:  Return description string.
        throws:   Dict mapping exception name → description.
        see:      List of ``@see`` references.
        deprecated: Deprecation message if present.
    """

    def __init__(self, raw: str) -> None:
        self.summary: str = ""
        self.params: dict = {}
        self.returns: str = ""
        self.throws: dict = {}
        self.see: list = []
        self.deprecated: str = ""
        self._parse(raw)

    def _parse(self, text: str) -> None:
        """Parse raw JavaDoc text into structured fields."""
        # Strip leading * from each line
        lines = []
        for line in text.split("\n"):
            stripped = re.sub(r"^\s*\*+\s?", "", line).strip()
            lines.append(stripped)

        # Summary: all lines before the first @tag
        summary_parts = []
        i = 0
        while i < len(lines) and not lines[i].startswith("@"):
            if lines[i]:
                summary_parts.append(lines[i])
            i += 1
        self.summary = " ".join(summary_parts)

        # Parse @param tags
        for m in _JAVADOC_PARAM_RE.finditer(text):
            self.params[m.group("name")] = m.group("desc").strip()

        # Parse @return
        m = _JAVADOC_RETURN_RE.search(text)
        if m:
            self.returns = m.group("desc").strip()

        # Parse @throws
        for m in _JAVADOC_THROWS_RE.finditer(text):
            self.throws[m.group("type")] = m.group("desc").strip()

        # @see
        for m in _JAVADOC_SEE_RE.finditer(text):
            self.see.append(m.group("ref").strip())

        # @deprecated
        dep_match = re.search(r"@deprecated\s*(?P<msg>[^\n@]*)", text, re.IGNORECASE)
        if dep_match:
            self.deprecated = dep_match.group("msg").strip()


def _extract_javadoc_before(source: str, offset: int) -> _JavaDoc | None:
    """
    Find and parse the JavaDoc comment immediately preceding the given offset.

    Args:
        source: Full Java source text.
        offset: Character offset of the construct to find JavaDoc for.

    Returns:
        :class:`_JavaDoc` instance or None if no JavaDoc found.
    """
    pre = source[:offset]
    # Find the last /** ... */ block
    last_start = pre.rfind("/**")
    if last_start == -1:
        return None

    last_end = pre.find("*/", last_start)
    if last_end == -1:
        return None

    # Ensure there is no other class/method definition between the comment end
    # and the current offset (i.e., the comment belongs to this construct)
    between = pre[last_end + 2:].strip()
    # Allow only annotations, access modifiers, and blank lines in between
    if re.search(r"(?:class|interface|record|enum|void|\bpublic\b|\bprivate\b)\s+\w", between):
        return None

    raw = source[last_start + 3:last_end]
    doc = _JavaDoc(raw)
    if not (doc.summary or doc.params or doc.returns):
        return None
    return doc


# ---------------------------------------------------------------------------
# Java type normalisation
# ---------------------------------------------------------------------------

def _parse_java_type(raw: str) -> str:
    """
    Convert a Java type annotation string to a canonical spec type.

    Handles generics, arrays, and wrapper types.

    Args:
        raw: Raw Java type string (e.g. ``List<String>``, ``int[]``, ``Boolean``).

    Returns:
        Canonical spec type string.
    """
    s = raw.strip()

    # Boxed types
    boxed = {
        "Integer": "number", "Long": "number", "Double": "number",
        "Float": "number", "Short": "number", "Byte": "number",
        "BigDecimal": "number", "BigInteger": "number",
        "Boolean": "boolean",
        "String": "string", "UUID": "string", "URI": "string", "URL": "string",
        "Date": "string", "LocalDate": "string", "LocalDateTime": "string",
        "ZonedDateTime": "string", "Instant": "string",
        "Object": "object",
        "Void": "null", "void": "null",
    }
    if s in boxed:
        return boxed[s]

    # Array types
    if s.endswith("[]") or s.endswith("..."):
        return "array"

    # Generic List/Collection types
    if re.match(r"(?:List|ArrayList|LinkedList|Set|HashSet|TreeSet|"
                r"Collection|Iterable|Deque|Queue|Stack)<", s):
        return "array"

    # Generic Map types
    if re.match(r"(?:Map|HashMap|LinkedHashMap|TreeMap|Hashtable|"
                r"ConcurrentHashMap)<", s):
        return "object"

    # Optional<T>
    if re.match(r"Optional<", s):
        return "null"  # Nullable return

    return _normalize_type(s)


# ---------------------------------------------------------------------------
# Parameter list parser
# ---------------------------------------------------------------------------

def _parse_java_params(param_str: str, doc: _JavaDoc | None = None) -> list:
    """
    Parse a Java method parameter list into :class:`PropertyDict` objects.

    Handles:
        - Annotated parameters: ``@NotNull String name``
        - Generic: ``List<String> items``
        - Varargs: ``String... values``
        - Final: ``final int count``

    Args:
        param_str: Raw parameter string between parentheses.
        doc: Parsed JavaDoc for description enrichment.

    Returns:
        List of :class:`PropertyDict` instances.
    """
    if not param_str.strip():
        return []

    # Split on commas not inside angle brackets
    parts = _split_java_params(param_str)
    props = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Strip annotations: @NotNull @Valid ...
        part = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", part).strip()
        # Strip 'final'
        part = re.sub(r"^final\s+", "", part).strip()

        if not part:
            continue

        # Varargs: Type... name
        is_vararg = "..." in part
        part_clean = part.replace("...", "[]")

        # Split on last whitespace: type name
        tokens = part_clean.rsplit(None, 1)
        if len(tokens) == 2:
            type_raw, name_raw = tokens
        elif len(tokens) == 1:
            # Might be just a type (anonymous param in interface)
            type_raw = tokens[0]
            name_raw = "param"
        else:
            continue

        name = _clean_identifier(name_raw)
        ptype = _parse_java_type(type_raw.strip())

        desc = ""
        if doc and name in doc.params:
            desc = _truncate_description(doc.params[name], 100)

        props.append(PropertyDict(
            name=name,
            type="array" if is_vararg else ptype,
            required=True,
            description=desc or f"Parameter {name}",
            confidence=0.85 if doc else 0.75,
        ))

    return props


def _split_java_params(param_str: str) -> list:
    """
    Split a Java parameter string on top-level commas.

    Respects nesting inside ``<>`` and ``()``.

    Args:
        param_str: Raw parameter string.

    Returns:
        List of parameter sub-strings.
    """
    parts = []
    buf = []
    depth = 0
    for ch in param_str:
        if ch in ("<", "(", "["):
            depth += 1
            buf.append(ch)
        elif ch in (">", ")", "]"):
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
# Java extractor
# ---------------------------------------------------------------------------

class JavaExtractor(BaseExtractor):
    """
    Java-specific spec extractor.

    Understands Java 8–21 constructs including:
    - ``class``/``interface``/``record``/``enum`` → entities
    - Public/protected methods → behaviors
    - JavaDoc comments
    - Bean Validation annotations (@NotNull, @Size, etc.)
    - Spring annotations (@Service, @Repository, @RequestMapping, etc.)
    - Guard clause patterns

    Args:
        confidence_threshold: Minimum confidence to include an item.
        module_name: Override module name.
        include_private: If True, include private methods (default: False).
        max_behaviors: Maximum number of behaviors per file.
        max_rules: Maximum number of rules per file.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        module_name: str = None,
        include_private: bool = False,
        max_behaviors: int = 40,
        max_rules: int = 20,
    ) -> None:
        super().__init__(confidence_threshold, module_name)
        self.include_private = include_private
        self.max_behaviors = max_behaviors
        self.max_rules = max_rules

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def extract_entities(self, source: str) -> list:
        """
        Extract Java class / record / interface definitions as entities.

        Processing rules:
        - ``class`` → entity with fields as properties
        - ``record`` → entity with record components as properties
        - ``interface`` → entity with abstract method signatures
        - Skips classes with Test/Mock/Stub/Fake in the name
        - Fields from inner classes are excluded

        Args:
            source: Java source code text.

        Returns:
            List of :class:`EntityDict` instances.
        """
        entities = []
        seen_names: set = set()

        for match in _JAVA_CLASS_RE.finditer(source):
            raw_name = match.group("name")
            kind = match.group("kind")

            # Skip test/mock classes
            lower_name = raw_name.lower()
            if any(
                lower_name.endswith(s) or lower_name.startswith(s)
                for s in ("test", "mock", "stub", "fake", "spy", "helper", "util")
            ):
                continue

            # Skip annotations-only interfaces
            if kind == "interface" and "Annotation" in raw_name:
                continue

            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            # Extract JavaDoc
            doc = _extract_javadoc_before(source, match.start())
            summary = doc.summary if doc else ""

            desc = _truncate_description(summary) if summary else (
                f"Java {kind} {raw_name}"
            )
            confidence = 1.0 if doc else 0.75

            # Properties
            if kind == "record" and match.group("record_params"):
                props = self._extract_record_components(match.group("record_params"), doc)
            else:
                props = self._extract_class_fields(source, match.end())

            entities.append(EntityDict(
                name=pascal,
                description=desc,
                properties=props,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        return entities

    def _extract_record_components(self, params_str: str, doc: _JavaDoc | None) -> list:
        """
        Extract record component list as PropertyDict objects.

        Args:
            params_str: Raw record component string.
            doc: JavaDoc for description enrichment.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        return _parse_java_params(params_str, doc)

    def _extract_class_fields(self, source: str, class_body_start: int) -> list:
        """
        Extract field declarations from a Java class body.

        Looks for standard field patterns inside the class brace block.

        Args:
            source: Full source text.
            class_body_start: Character offset of the opening ``{``.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        # Find the class body (up to matching closing brace)
        body = self._extract_brace_block(source, class_body_start - 1)
        if not body:
            return []

        props = []
        seen: set = set()

        for match in _JAVA_FIELD_RE.finditer(body):
            mods = match.group("mods") or ""
            name = match.group("name")
            raw_type = match.group("type")
            default = match.group("default")

            # Skip static fields (class-level constants already captured as constraints)
            if "static" in mods:
                continue

            if name in seen:
                continue
            seen.add(name)

            ptype = _parse_java_type(raw_type.strip())
            required = "final" in mods and default is None
            visibility = (
                "public" if "public" in mods
                else "protected" if "protected" in mods
                else "private"
            )

            # High confidence for properly declared fields
            confidence = 0.8 if visibility in ("public", "protected") else 0.7

            props.append(PropertyDict(
                name=name,
                type=ptype,
                required=required,
                description=f"Field {name} ({visibility})",
                default=default.strip() if default else None,
                confidence=confidence,
            ))

        return props[:20]

    def _extract_brace_block(self, source: str, opening_brace_hint: int) -> str:
        """
        Extract text between matching braces starting near ``opening_brace_hint``.

        Args:
            source: Full source text.
            opening_brace_hint: Character offset to search for ``{`` from.

        Returns:
            Content between the matching braces (inclusive), or empty string.
        """
        start = source.find("{", opening_brace_hint)
        if start == -1:
            return ""
        depth = 0
        pos = start
        while pos < min(len(source), start + 10000):  # Cap scan size
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
        Extract Java method signatures as BDD behaviors.

        Includes:
        - Public and protected methods
        - Private methods only when ``include_private=True``
        - Constructors for service/manager classes
        - Spring endpoint methods get URL path in ``when``

        Excludes:
        - ``equals``, ``hashCode``, ``toString``, ``clone`` (boilerplate)
        - Getter/setter methods (``getX`` / ``setX`` / ``isX``)
        - Test methods

        Args:
            source: Java source code text.

        Returns:
            List of :class:`BehaviorDict` instances.
        """
        behaviors = []
        seen_names: set = set()

        boilerplate = {"equals", "hashCode", "toString", "clone",
                       "compareTo", "finalize", "wait", "notify", "notifyAll"}

        for match in _JAVA_METHOD_RE.finditer(source):
            if len(behaviors) >= self.max_behaviors:
                break

            raw_name = match.group("name")
            mods = match.group("mods") or ""
            return_type_raw = match.group("return_type") or ""
            params_str = match.group("params") or ""
            throws_raw = match.group("throws") or ""

            # Filter by visibility
            if "private" in mods and not self.include_private:
                continue

            # Skip boilerplate and accessors
            if raw_name in boilerplate:
                continue
            if re.match(r"(?:get|set|is)[A-Z]", raw_name):
                continue

            # Skip test methods
            if raw_name.startswith("test") or raw_name.startswith("should"):
                continue

            snake_name = _to_snake_case(raw_name)
            if snake_name in seen_names:
                continue
            seen_names.add(snake_name)

            # JavaDoc
            doc = _extract_javadoc_before(source, match.start())

            # Parameters
            params = _parse_java_params(params_str, doc)

            # Return type
            return_type = _parse_java_type(return_type_raw.strip())

            # Check for endpoint annotation
            endpoint_path = self._find_endpoint_annotation(source, match.start())

            # Description
            if doc and doc.summary:
                desc = _truncate_description(doc.summary)
                confidence = 1.0
            elif "public" in mods:
                desc = f"Executes {raw_name}"
                confidence = 0.8
            else:
                desc = f"Performs {raw_name}"
                confidence = 0.7

            # Boost confidence for annotated methods
            anns = self._get_annotations_before(source, match.start())
            if any(a in anns for a in ("Override", "Bean", "Service", "Transactional")):
                confidence = min(1.0, confidence + 0.1)

            if doc and doc.deprecated:
                confidence = max(0.3, confidence - 0.2)

            # Build GWT
            given, when, then_ = self._build_java_gwt(
                raw_name, params, doc, return_type,
                endpoint_path, throws_raw, mods,
            )

            behaviors.append(BehaviorDict(
                name=snake_name,
                description=desc,
                given=given,
                when=when,
                then=then_,
                confidence=confidence,
                source_line=source[:match.start()].count("\n") + 1,
            ))

        return behaviors

    def _find_endpoint_annotation(self, source: str, method_start: int) -> str:
        """
        Look for a Spring/JAX-RS mapping annotation before a method.

        Args:
            source: Full source text.
            method_start: Character offset of the method.

        Returns:
            Path string from the annotation, or empty string.
        """
        pre = source[max(0, method_start - 300):method_start]
        m = _JAVA_ENDPOINT_RE.search(pre)
        if m:
            return m.group("path") or ""
        return ""

    def _get_annotations_before(self, source: str, method_start: int) -> list:
        """
        Collect annotation names in the 300 characters before a method.

        Args:
            source: Full source text.
            method_start: Character offset of the method.

        Returns:
            List of annotation name strings.
        """
        pre = source[max(0, method_start - 300):method_start]
        return [m.group("ann") for m in _JAVA_ANNOTATION_RE.finditer(pre)]

    def _build_java_gwt(
        self,
        method_name: str,
        params: list,
        doc: _JavaDoc | None,
        return_type: str,
        endpoint_path: str,
        throws_raw: str,
        mods: str,
    ) -> tuple:
        """
        Build Given / When / Then lists for a Java method.

        Args:
            method_name: Raw method name.
            params: Parsed parameter list.
            doc: Parsed JavaDoc (may be None).
            return_type: Canonical return type string.
            endpoint_path: Optional HTTP path from endpoint annotation.
            throws_raw: Raw throws clause string.
            mods: Raw modifiers string.

        Returns:
            Tuple of (given_list, when_list, then_list).
        """
        snake = _to_snake_case(method_name)
        human = re.sub(r"_", " ", snake)

        given: list = []
        when: list = []
        then_: list = []

        # Given: parameter preconditions
        for p in params[:4]:
            hint = doc.params.get(p.name, "") if doc else ""
            if hint:
                given.append(f"{p.name} is valid: {hint[:80]}")
            else:
                given.append(f"{p.name} is provided")

        if not given:
            if "static" in mods:
                given = ["required inputs are available"]
            else:
                given = ["object is properly initialised"]

        # When
        if endpoint_path:
            # Detect HTTP method from caller context
            http_verb = "call to"
            if re.match(r"post|create|add|insert|register", method_name, re.IGNORECASE):
                http_verb = "POST"
            elif re.match(r"get|fetch|find|retrieve|load|read", method_name, re.IGNORECASE):
                http_verb = "GET"
            elif re.match(r"put|update|replace|set", method_name, re.IGNORECASE):
                http_verb = "PUT"
            elif re.match(r"delete|remove|destroy", method_name, re.IGNORECASE):
                http_verb = "DELETE"
            when = [f"{http_verb} {endpoint_path} is received", f"{human} is invoked"]
        else:
            when = [f"{human} is called"]

        # Then
        if doc and doc.returns:
            then_.append(_truncate_description(doc.returns, 100))
        elif return_type and return_type != "null":
            then_.append(f"{return_type} result is returned")
        else:
            then_.append(f"{human} completes without error")

        if doc and doc.throws:
            for exc, exc_desc in list(doc.throws.items())[:2]:
                then_.append(
                    f"throws {exc}: {exc_desc[:60]}" if exc_desc else f"throws {exc} on error"
                )

        if throws_raw:
            for exc in throws_raw.split(","):
                exc = exc.strip()
                if exc and f"throws {exc}" not in " ".join(then_):
                    then_.append(f"may throw {exc}")
                    break

        return given[:5], when[:2], then_[:5]

    # ------------------------------------------------------------------
    # Rule extraction
    # ------------------------------------------------------------------

    def extract_rules(self, source: str) -> list:
        """
        Extract Java business rules from conditionals and validation annotations.

        Strategies:
        1. ``if (cond)`` with rule-language JavaDoc/comment above
        2. Guard patterns: ``if (cond) { throw new XxxException(...); }``
        3. Bean Validation annotations on class fields/methods

        Args:
            source: Java source code text.

        Returns:
            List of :class:`RuleDict` instances.
        """
        rules = []
        seen_names: set = set()
        lines = source.split("\n")

        rule_re = re.compile(
            r"\b(must|should|cannot|require[sd]?|ensure[sd]?|valid|enforce|"
            r"guard|restrict|allow|deny|prevent|reject|check|assert|verify)\b",
            re.IGNORECASE,
        )

        # Strategy 1: if/else with rule-language comment above
        for i, line in enumerate(lines):
            if len(rules) >= self.max_rules:
                break

            if not re.match(r"^\s*(?:if|else\s+if)\s*\(", line):
                continue

            comment = self._get_preceding_comment(source, lines, i)
            if not comment or not rule_re.search(comment):
                continue

            cond_match = re.match(r"^\s*(?:if|else\s+if)\s*\((?P<expr>[^)]+)\)", line)
            condition = (
                f"when {cond_match.group('expr').strip()}" if cond_match
                else "when condition is met"
            )

            name = self._derive_java_rule_name(comment)
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
        for match in _JAVA_GUARD_RE.finditer(source):
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
                description=f"Guard clause validates: {cond[:100]}",
                condition=f"when {cond[:100]}",
                action=f"then throw {exc}",
                confidence=0.7,
                source_line=line_no,
            ))

        # Strategy 3: Bean Validation annotations
        ann_rule_re = re.compile(
            r"@(?P<ann>NotNull|NotEmpty|NotBlank|Size|Min|Max|Pattern|Email|"
            r"Positive|Negative|AssertTrue|AssertFalse)\s*"
            r"(?:\((?P<args>[^)]*)\))?\s*\n"
            r"(?:.*\n){0,2}"   # Allow annotations to stack
            r"\s*(?:private|protected|public)?\s*\w+\s+(?P<field>\w+)",
            re.MULTILINE,
        )
        for match in ann_rule_re.finditer(source):
            if len(rules) >= self.max_rules:
                break

            ann = match.group("ann")
            args = match.group("args") or ""
            field = match.group("field")
            line_no = source[:match.start()].count("\n") + 1

            name = _to_snake_case(f"{ann}_{field}")
            if name in seen_names:
                continue
            seen_names.add(name)

            desc, condition, action = self._ann_to_rule(ann, args, field)

            rules.append(RuleDict(
                name=name,
                description=desc,
                condition=condition,
                action=action,
                confidence=0.8,
                source_line=line_no,
            ))

        return rules

    @staticmethod
    def _ann_to_rule(ann: str, args: str, field: str) -> tuple:
        """
        Convert a Bean Validation annotation to a rule triple.

        Args:
            ann: Annotation name (e.g. ``NotNull``, ``Size``).
            args: Annotation arguments string.
            field: Field name the annotation is applied to.

        Returns:
            Tuple of (description, condition, action).
        """
        templates = {
            "NotNull": (
                f"Field {field} must not be null",
                f"when {field} is provided",
                f"then {field} must not be null",
            ),
            "NotEmpty": (
                f"Field {field} must not be empty",
                f"when {field} value is being set",
                f"then {field} must not be an empty string",
            ),
            "NotBlank": (
                f"Field {field} must not be blank",
                f"when {field} value is being set",
                f"then {field} must contain at least one non-whitespace character",
            ),
            "Size": (
                f"Field {field} has size constraints: {args}",
                f"when {field} value is being validated",
                f"then {field} size must satisfy {args}",
            ),
            "Min": (
                f"Field {field} minimum value constraint",
                f"when {field} is being set",
                f"then {field} must be >= {args}",
            ),
            "Max": (
                f"Field {field} maximum value constraint",
                f"when {field} is being set",
                f"then {field} must be <= {args}",
            ),
            "Pattern": (
                f"Field {field} must match pattern {args}",
                f"when {field} is being validated",
                f"then {field} must match regex {args}",
            ),
            "Email": (
                f"Field {field} must be a valid email address",
                f"when {field} is provided",
                f"then {field} must conform to email format",
            ),
            "Positive": (
                f"Field {field} must be a positive number",
                f"when {field} is being set",
                f"then {field} must be > 0",
            ),
            "Negative": (
                f"Field {field} must be a negative number",
                f"when {field} is being set",
                f"then {field} must be < 0",
            ),
        }
        default = (
            f"Validation {ann} on {field}: {args}",
            f"when {field} is validated",
            f"then {field} must satisfy {ann} constraint",
        )
        return templates.get(ann, default)

    def _get_preceding_comment(self, source: str, lines: list, line_index: int) -> str:
        """
        Extract the nearest JavaDoc or single-line comment above a line.

        Args:
            source: Full source text.
            lines: All source lines.
            line_index: 0-based target line index.

        Returns:
            Combined comment text, or empty string.
        """
        # Check for JavaDoc above
        line_offset = sum(len(l) + 1 for l in lines[:line_index])
        doc = _extract_javadoc_before(source, line_offset)
        if doc and doc.summary:
            return doc.summary

        # Fall back to single-line comments
        parts = []
        i = line_index - 1
        while i >= 0 and not lines[i].strip():
            i -= 1
        while i >= 0 and re.match(r"^\s*//", lines[i]):
            parts.insert(0, re.sub(r"^\s*//+\s*", "", lines[i]).strip())
            i -= 1
        return " ".join(parts)

    def _derive_java_rule_name(self, text: str) -> str:
        """
        Derive a snake_case rule name from a comment or annotation description.

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
        Extract Java constraints from constants, assertions, and Bean Validation.

        Strategies:
        1. ``public static final TYPE NAME = value;`` → limit/timeout
        2. ``assert expr : "message";`` → invariant
        3. ``throw new XxxException("message")`` → invariant
        4. ``@Size(min=x, max=y)`` / ``@Min`` / ``@Max`` → limit constraints

        Args:
            source: Java source code text.

        Returns:
            List of :class:`ConstraintDict` instances.
        """
        constraints = []
        seen_names: set = set()

        # 1. Static final constants
        for match in _JAVA_CONST_RE.finditer(source):
            raw_name = match.group("name")
            value = match.group("value").strip()
            line_no = source[:match.start()].count("\n") + 1

            name = _to_snake_case(raw_name)
            if name in seen_names:
                continue
            seen_names.add(name)

            upper = raw_name.upper()
            if any(k in upper for k in ("TIMEOUT", "TTL", "EXPIR", "WAIT", "DELAY")):
                ctype = "timeout"
            elif any(k in upper for k in ("MAX", "MIN", "LIMIT", "SIZE", "LENGTH",
                                          "COUNT", "CAPACITY", "THRESHOLD")):
                ctype = "limit"
            else:
                continue  # Skip non-meaningful constants

            constraints.append(ConstraintDict(
                name=name,
                description=f"Constant {raw_name} = {value} defines a {ctype}",
                type=ctype,
                value=str(value),
                confidence=0.8,
                source_line=line_no,
            ))

        # 2. Assert statements
        for match in _JAVA_ASSERT_RE.finditer(source):
            expr = match.group("expr").strip()
            msg_raw = match.group("msg") or ""
            msg = msg_raw.strip("\"'")

            if not msg and len(expr) < 10:
                continue

            line_no = source[:match.start()].count("\n") + 1
            name = _to_snake_case(f"assert_{expr[:25]}")
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=_truncate_description(msg or f"Assertion: {expr[:100]}"),
                type="invariant",
                value=f"assert {expr[:100]}",
                confidence=0.75,
                source_line=line_no,
            ))

        # 3. throw new XxxException("message") — validation pattern
        for match in _JAVA_THROW_RE.finditer(source):
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
                value=f"throws {exc}: {msg[:100]}",
                confidence=0.7,
                source_line=line_no,
            ))

        # 4. @Size(min=x, max=y) and @Min/@Max annotations
        size_ann_re = re.compile(
            r"@Size\s*\(\s*(?:min\s*=\s*(?P<min>\d+))?\s*,?\s*"
            r"(?:max\s*=\s*(?P<max>\d+))?\s*\)",
            re.MULTILINE,
        )
        for match in size_ann_re.finditer(source):
            min_val = match.group("min") or "0"
            max_val = match.group("max") or "unlimited"
            line_no = source[:match.start()].count("\n") + 1

            name = f"size_constraint_min{min_val}_max{max_val}"
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=f"Size constraint: min={min_val}, max={max_val}",
                type="limit",
                value=f"min={min_val}, max={max_val}",
                confidence=0.85,
                source_line=line_no,
            ))

        return constraints
