"""
patterns/generic.py - Language-agnostic source code pattern extraction.

Provides a fallback extractor that applies heuristic regex patterns to any
text-based source file.  It is intentionally conservative: it only claims
high confidence when clear structural markers are present.

Patterns covered:
  - Class / struct / interface definitions (entities)
  - Function / method / procedure definitions (behaviors)
  - Single-line and block comments (constraints / rules)
  - Type annotations in comment form (e.g. ``@type``, ``@param``)
  - Logic keywords (if / else if / elif / switch / case) → rules
  - Numeric literals in constant context → limit constraints
  - Timeout hints from comments

This module intentionally avoids AST parsing; all matching is via ``re``.
"""

from __future__ import annotations

import re
import sys
import os

# Make sure the parent src directory is importable regardless of cwd
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
# Compiled patterns shared across methods
# ---------------------------------------------------------------------------

# Class-like definitions (class / struct / interface / record / type + name)
_CLASS_DEF_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|abstract|final|static|sealed|data|open|inner|"
    r"value|record)\s+)*"
    r"(?:class|struct|interface|record|type|enum)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:[^{;]*)?",
    re.MULTILINE,
)

# Function / method / procedure definitions (very broad)
_FUNC_DEF_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|abstract|override|async|"
    r"def|fun|func|function|sub|procedure)\s+)+"
    r"(?:(?:[A-Za-z_<>\[\]?]+)\s+)?"   # optional return type
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)",
    re.MULTILINE,
)

# Also capture simple `def name(...)` (Python/Ruby/Swift without modifiers)
_SIMPLE_DEF_RE = re.compile(
    r"^\s*(?:def|fun|func|function)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
    r"(?P<params>[^)]*)\)",
    re.MULTILINE,
)

# Block comment opening /** ... */
_BLOCK_COMMENT_START_RE = re.compile(r"/\*\*?")
_BLOCK_COMMENT_END_RE = re.compile(r"\*/")

# Single-line comment (// or # style)
_SINGLE_COMMENT_RE = re.compile(r"^\s*(?://|#)\s*(?P<text>.+)$", re.MULTILINE)

# @param / @returns / @throws tag inside doc-comments
_DOC_PARAM_RE = re.compile(r"@param(?:eter)?\s+(?:\{[^}]+\}\s*)?(?P<name>\w+)\s*(?P<desc>[^\n@]*)")
_DOC_RETURN_RE = re.compile(r"@(?:return|returns)\s+(?:\{[^}]+\}\s*)?(?P<desc>[^\n@]+)")
_DOC_THROWS_RE = re.compile(r"@(?:throws?|exception)\s+(?P<type>\w+)\s*(?P<desc>[^\n@]*)")

# Type annotation in comment: @type {TypeName} varName  OR  varName: TypeName
_COMMENT_TYPE_RE = re.compile(r"@type\s+\{?(?P<type>[A-Za-z_<>\[\]?]+)\}?\s+(?P<name>\w+)")

# Logic keywords that suggest a rule
_LOGIC_KEYWORD_RE = re.compile(
    r"^\s*(?:if|else\s+if|elif|else|switch|case|when|unless|guard)\b",
    re.MULTILINE,
)

# Timeout-like values: 30s, 5000ms, 1m, 24h
_TIMEOUT_RE = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|s|sec|seconds?|m|min|minutes?|h|hours?|d|days?)\b",
    re.IGNORECASE,
)

# Numeric limits in constant/config context: MAX_xxx = 1000, MIN_xxx = 0
_LIMIT_CONST_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Z0-9_]*(?:MAX|MIN|LIMIT|SIZE|LENGTH|COUNT)[A-Z0-9_]*|"
    r"(?:MAX|MIN|LIMIT|SIZE|LENGTH|COUNT)[A-Z0-9_]+)\s*[=:]\s*(?P<value>\d+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Comment extraction utility
# ---------------------------------------------------------------------------

def _extract_leading_comment(source: str, line_index: int, lines: list) -> str:
    """
    Extract the closest preceding comment for the code at ``line_index``.

    Looks back through blank lines to find a single-line or block comment
    that documents the following definition.

    Args:
        source: Full source text (unused; kept for API symmetry).
        line_index: 0-based index of the definition line in ``lines``.
        lines: All source lines.

    Returns:
        Cleaned comment text, or empty string if none found.
    """
    comment_lines = []
    i = line_index - 1

    # Skip blank lines immediately above the definition
    while i >= 0 and not lines[i].strip():
        i -= 1

    if i < 0:
        return ""

    # Collect block comment /** ... */
    if lines[i].strip().endswith("*/"):
        end = i
        while i >= 0 and "/*" not in lines[i]:
            comment_lines.insert(0, lines[i])
            i -= 1
        if i >= 0:
            comment_lines.insert(0, lines[i])
        # Strip leading *, /**,  */
        cleaned = []
        for cl in comment_lines:
            stripped = re.sub(r"^\s*\*+/?", "", cl).strip()
            if stripped and not stripped.startswith("@"):
                cleaned.append(stripped)
        return " ".join(cleaned)

    # Collect consecutive single-line comments
    while i >= 0 and re.match(r"^\s*(?://|#)", lines[i]):
        comment_lines.insert(0, re.sub(r"^\s*(?://|#)\s*", "", lines[i]).strip())
        i -= 1

    return " ".join(comment_lines)


def _extract_block_comments(source: str) -> list:
    """
    Extract all block comments (``/* ... */``) from source.

    Args:
        source: Raw source text.

    Returns:
        List of raw comment content strings (stripped of ``/*`` delimiters).
    """
    comments = []
    pos = 0
    while True:
        start = source.find("/*", pos)
        if start == -1:
            break
        end = source.find("*/", start + 2)
        if end == -1:
            break
        raw = source[start + 2:end]
        # Clean leading asterisks
        cleaned = re.sub(r"^\s*\*+\s?", "", raw, flags=re.MULTILINE)
        comments.append(cleaned.strip())
        pos = end + 2
    return comments


# ---------------------------------------------------------------------------
# Parameter parsing
# ---------------------------------------------------------------------------

def _parse_generic_params(param_str: str) -> list:
    """
    Parse a raw parameter list string into a list of PropertyDict objects.

    Handles simple ``name``, ``type name``, ``name: type``, and
    ``name = default`` patterns.  Returns an empty list for empty input.

    Args:
        param_str: Raw parameter string between parentheses.

    Returns:
        List of :class:`PropertyDict` instances with inferred type/name.
    """
    if not param_str.strip():
        return []

    props = []
    # Split on commas not inside <>, (), []
    parts = _split_params(param_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        name = "param"
        ptype = "string"
        default = None

        # Strip default value
        if "=" in part:
            part, default_raw = part.split("=", 1)
            default = default_raw.strip()
            part = part.strip()

        # Pattern: name: Type  (TypeScript / Kotlin / Swift)
        if re.match(r"^\w+\s*:\s*\w", part):
            chunks = part.split(":", 1)
            name = _clean_identifier(chunks[0])
            ptype = _normalize_type(chunks[1].strip())

        # Pattern: Type name  (Java / C#)
        elif re.match(r"^[A-Za-z_<\[]\S*\s+\w", part):
            chunks = part.rsplit(None, 1)
            ptype = _normalize_type(chunks[0])
            name = _clean_identifier(chunks[-1]) if len(chunks) > 1 else "param"

        # Plain name only
        elif re.match(r"^\w+$", part):
            name = _clean_identifier(part)

        props.append(PropertyDict(
            name=name,
            type=ptype,
            required=(default is None),
            description=f"Parameter {name}",
            default=default,
            confidence=0.6,
        ))

    return props


def _split_params(param_str: str) -> list:
    """
    Split a parameter list on top-level commas only (ignores generics/tuples).

    Args:
        param_str: Raw parameter string.

    Returns:
        List of parameter sub-strings.
    """
    parts = []
    depth = 0
    buf = []
    for ch in param_str:
        if ch in ("<", "(", "[", "{"):
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
# Generic extractor implementation
# ---------------------------------------------------------------------------

class GenericExtractor(BaseExtractor):
    """
    Language-agnostic extractor that uses broad heuristic regex patterns.

    This extractor acts as a fallback when no language-specific extractor
    is available.  It trades precision for coverage.

    Confidence scores:
        - Entity with leading doc-comment: 0.8
        - Entity without comment: 0.6
        - Behavior with leading doc-comment: 0.8
        - Behavior without comment: 0.6
        - Rule from logic keyword + adjacent comment: 0.5
        - Constraint from named constant: 0.7
        - Constraint from timeout comment: 0.6

    Args:
        confidence_threshold: Minimum confidence to include an item.
        module_name: Override module name.
        max_behaviors: Maximum number of behaviors to extract per file.
            Prevents enormous specs from large utility files.
        max_rules: Maximum number of rules to extract per file.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        module_name: str = None,
        max_behaviors: int = 30,
        max_rules: int = 20,
    ) -> None:
        super().__init__(confidence_threshold, module_name)
        self.max_behaviors = max_behaviors
        self.max_rules = max_rules

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def extract_entities(self, source: str) -> list:
        """
        Extract class / struct / interface definitions as entities.

        Each matching definition becomes an :class:`EntityDict`.  Fields are
        derived from constructor/init parameter lists or attribute assignments
        visible in the class body (best-effort).

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`EntityDict` instances.
        """
        entities = []
        lines = source.split("\n")
        seen_names: set = set()

        for match in _CLASS_DEF_RE.finditer(source):
            raw_name = match.group("name")
            # Skip obvious non-domain names
            if raw_name.lower() in ("test", "tests", "spec", "mock", "stub", "fake", "helper"):
                continue
            # Deduplicate
            pascal = _to_pascal_case(raw_name)
            if pascal in seen_names:
                continue
            seen_names.add(pascal)

            line_index = source[:match.start()].count("\n")
            comment = _extract_leading_comment(source, line_index, lines)
            desc = _truncate_description(comment) if comment else ""

            confidence = 0.8 if comment else 0.6
            entity = EntityDict(
                name=pascal,
                description=desc or f"Data entity representing {raw_name}",
                properties=self._extract_class_properties(source, match.start()),
                confidence=confidence,
                source_line=line_index + 1,
            )
            entities.append(entity)

        return entities

    def _extract_class_properties(self, source: str, class_start: int) -> list:
        """
        Best-effort extraction of properties from a class body.

        Looks for field declarations, constructor parameters, or attribute
        assignments inside the class block that starts at ``class_start``.

        Args:
            source: Full source text.
            class_start: Character offset of the class definition keyword.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        # Find the class body (between braces or indented block)
        body_start = source.find("{", class_start)
        if body_start == -1:
            # Python-style: look at next indented block
            return self._extract_indented_fields(source, class_start)

        # Find matching closing brace
        depth = 0
        pos = body_start
        while pos < len(source):
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
                if depth == 0:
                    break
            pos += 1

        body = source[body_start:pos + 1]
        return self._extract_brace_fields(body)

    def _extract_brace_fields(self, body: str) -> list:
        """
        Extract field declarations from a brace-delimited class body.

        Matches patterns like:
            private String email;
            readonly id: number;
            int count = 0;

        Args:
            body: Class body text including braces.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        # Patterns: [modifiers] Type name [= default];
        field_re = re.compile(
            r"^\s*(?:(?:private|protected|public|final|static|readonly|"
            r"lateinit|override|var|val|let|const)\s+)*"
            r"(?P<type>[A-Za-z_<>\[\]?]+)\s+"
            r"(?P<name>[a-z_][A-Za-z0-9_]*)\s*"
            r"(?:=\s*(?P<default>[^;{\n]+))?\s*[;,\n]",
            re.MULTILINE,
        )
        props = []
        seen: set = set()
        for m in field_re.finditer(body):
            fname = m.group("name")
            if fname in seen or fname in ("this", "self", "super"):
                continue
            seen.add(fname)
            ftype = _normalize_type(m.group("type"))
            default = m.group("default")
            props.append(PropertyDict(
                name=fname,
                type=ftype,
                required=(default is None),
                description=f"Field {fname}",
                default=default.strip() if default else None,
                confidence=0.7,
            ))
        return props[:20]  # Cap to prevent enormous property lists

    def _extract_indented_fields(self, source: str, class_start: int) -> list:
        """
        Extract field definitions from an indented block (Python-style).

        Looks for ``self.x =`` and ``x: Type`` patterns.

        Args:
            source: Full source text.
            class_start: Character offset of the class definition.

        Returns:
            List of :class:`PropertyDict` instances.
        """
        # Find the line after the class definition
        rest = source[class_start:]
        lines = rest.split("\n")[1:30]  # Look at next 30 lines only

        props = []
        seen: set = set()

        for line in lines:
            # self.name = ...  (Python instance attribute)
            m = re.match(r"^\s+self\.(?P<name>[a-z_]\w*)\s*=", line)
            if m:
                name = m.group("name")
                if name not in seen:
                    seen.add(name)
                    props.append(PropertyDict(
                        name=name,
                        type="string",
                        required=True,
                        description=f"Attribute {name}",
                        confidence=0.65,
                    ))
                continue

            # name: Type  (Python type annotation)
            m = re.match(r"^\s+(?P<name>[a-z_]\w*)\s*:\s*(?P<type>[A-Za-z_\[\]]+)", line)
            if m:
                name = m.group("name")
                if name not in seen:
                    seen.add(name)
                    props.append(PropertyDict(
                        name=name,
                        type=_normalize_type(m.group("type")),
                        required=True,
                        description=f"Attribute {name}",
                        confidence=0.7,
                    ))

        return props[:20]

    # ------------------------------------------------------------------
    # Behavior extraction
    # ------------------------------------------------------------------

    def extract_behaviors(self, source: str) -> list:
        """
        Extract function / method definitions as BDD behaviors.

        Skips constructors, private helpers (prefixed with ``_``), and very
        short methods that are likely getters/setters.

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`BehaviorDict` instances (up to ``max_behaviors``).
        """
        behaviors = []
        lines = source.split("\n")
        seen_names: set = set()

        combined_re = re.compile(
            r"^\s*(?:(?:public|private|protected|static|final|abstract|"
            r"override|async|def|fun|func|function|sub)\s+)*"
            r"(?:(?:[A-Za-z_<>\[\]?]+)\s+)?"
            r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
            r"(?P<params>[^)]*)\)",
            re.MULTILINE,
        )

        for match in combined_re.finditer(source):
            if len(behaviors) >= self.max_behaviors:
                break

            raw_name = match.group("name")
            # Skip constructors / common boilerplate
            if raw_name[0].isupper():
                continue
            # Skip private helpers (convention: _name or __name)
            if raw_name.startswith("__") and raw_name.endswith("__"):
                continue
            # Skip very generic non-informative names
            if raw_name in ("main", "init", "setup", "teardown", "get", "set"):
                continue

            snake_name = _to_snake_case(raw_name)
            if snake_name in seen_names:
                continue
            seen_names.add(snake_name)

            line_index = source[:match.start()].count("\n")
            comment = _extract_leading_comment(source, line_index, lines)

            # Build given/when/then from comment and signature
            given, when, then_ = self._build_gwt_from_comment(
                comment, raw_name, match.group("params")
            )
            desc = _truncate_description(comment) if comment else f"Performs {raw_name} operation"

            confidence = 0.8 if comment else 0.55

            behaviors.append(BehaviorDict(
                name=snake_name,
                description=desc,
                given=given,
                when=when,
                then=then_,
                confidence=confidence,
                source_line=line_index + 1,
            ))

        return behaviors

    def _build_gwt_from_comment(
        self,
        comment: str,
        func_name: str,
        param_str: str,
    ) -> tuple:
        """
        Derive Given / When / Then lists from a comment and function signature.

        The heuristic is:
        - ``given``: Describe parameters or state from comment
        - ``when``:  The function call itself
        - ``then``:  Success/return state from comment

        Args:
            comment: Leading comment text (may be empty).
            func_name: Raw function name.
            param_str: Raw parameter list string.

        Returns:
            Tuple of (given_list, when_list, then_list).
        """
        params = _parse_generic_params(param_str)
        snake = _to_snake_case(func_name)
        human = re.sub(r"_", " ", snake)

        given = []
        when = [f"{human} is called"]
        then = [f"{human} completes successfully"]

        if params:
            param_names = ", ".join(p.name for p in params[:3])
            given.append(f"valid {param_names} provided")

        if comment:
            # Extract @param descriptions from docstring-style comments
            for m in _DOC_PARAM_RE.finditer(comment):
                desc = m.group("desc").strip()
                name = m.group("name")
                if desc:
                    given.append(f"{name} is provided: {desc[:80]}")
            # Extract @return description
            m = _DOC_RETURN_RE.search(comment)
            if m:
                then = [_truncate_description(m.group("desc").strip(), 80)]
            # Extract @throws / @exception
            for m in _DOC_THROWS_RE.finditer(comment):
                exc_type = m.group("type")
                then.append(f"raises {exc_type} on error")

        if not given:
            given = ["system is in valid state"]

        return given[:5], when[:3], then[:5]

    # ------------------------------------------------------------------
    # Rule extraction
    # ------------------------------------------------------------------

    def extract_rules(self, source: str) -> list:
        """
        Extract business rules from conditional logic and inline comments.

        A rule is identified when:
        - A logic keyword (if/else/switch/case/when) is preceded by an
          explanatory comment, or
        - A comment contains rule-like language ("must", "should", "cannot",
          "only", "requires", "ensures", "validates").

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`RuleDict` instances (up to ``max_rules``).
        """
        rules = []
        lines = source.split("\n")
        seen_names: set = set()

        # Rule keyword: comment before logic
        for i, line in enumerate(lines):
            if len(rules) >= self.max_rules:
                break

            # Check for logic keyword
            if not _LOGIC_KEYWORD_RE.match(line):
                continue

            # Look back for an explanatory comment
            comment = _extract_leading_comment(source, i, lines)
            if not comment:
                continue

            # Must look like a rule statement
            rule_indicators = re.compile(
                r"\b(must|should|cannot|only|require[sd]?|ensure[sd]?|"
                r"valid|check|enforce|guard|restrict|allow|deny|prevent|reject)\b",
                re.IGNORECASE,
            )
            if not rule_indicators.search(comment):
                continue

            condition_text = line.strip()
            # Extract the condition expression
            cond_match = re.match(
                r"^\s*(?:if|else\s+if|elif|when|guard)\s*\(?(?P<expr>[^{:]+)",
                condition_text,
            )
            condition = (
                f"when {cond_match.group('expr').strip()}"
                if cond_match
                else "when condition is met"
            )

            # Derive action from the comment
            action = _truncate_description(comment, 100)
            if not action.lower().startswith(("then", "apply", "return", "reject", "deny")):
                action = f"then {action}"

            name = self._derive_rule_name(comment, i)
            if name in seen_names:
                continue
            seen_names.add(name)

            rules.append(RuleDict(
                name=name,
                description=_truncate_description(comment),
                condition=condition,
                action=action,
                confidence=0.5,
                source_line=i + 1,
            ))

        # Fallback: strong rule language in comments (no logic keyword required)
        strong_rule_re = re.compile(
            r"^\s*(?://|#|/\*+)\s*(?P<text>(?:RULE|BUSINESS RULE|CONSTRAINT|POLICY)"
            r"[:\s].+)$",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in strong_rule_re.finditer(source):
            if len(rules) >= self.max_rules:
                break
            text = match.group("text").strip()
            name = self._derive_rule_name(text, 0)
            if name in seen_names:
                continue
            seen_names.add(name)
            rules.append(RuleDict(
                name=name,
                description=_truncate_description(text),
                condition="when rule condition is evaluated",
                action=f"then {_truncate_description(text, 80)}",
                confidence=0.6,
            ))

        return rules

    def _derive_rule_name(self, text: str, line_number: int) -> str:
        """
        Derive a snake_case rule name from comment text.

        Extracts the first 4–6 meaningful words and converts to snake_case.

        Args:
            text: Comment or description text.
            line_number: Source line number (used as suffix for uniqueness).

        Returns:
            snake_case rule name.
        """
        # Strip punctuation
        words = re.findall(r"[a-z]+", text.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "if", "then", "and", "or",
            "in", "of", "to", "for", "on", "at", "by", "this", "that",
        }
        sig_words = [w for w in words if w not in stop_words][:5]
        if sig_words:
            return "_".join(sig_words)
        return f"rule_line_{line_number}"

    # ------------------------------------------------------------------
    # Constraint extraction
    # ------------------------------------------------------------------

    def extract_constraints(self, source: str) -> list:
        """
        Extract constraints from constant declarations, timeout hints, and
        annotated comments.

        Three constraint categories are detected:
        1. ``limit``   - numeric constants with MAX/MIN/LIMIT/SIZE in name
        2. ``timeout`` - time-unit patterns (30s, 5000ms, 1m, etc.)
        3. ``invariant`` - comments with @invariant or "must always be"

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`ConstraintDict` instances.
        """
        constraints = []
        seen_names: set = set()

        # 1. Named numeric limits
        for match in _LIMIT_CONST_RE.finditer(source):
            raw_name = match.group("name")
            value = match.group("value")
            name = _to_snake_case(raw_name)
            if name in seen_names:
                continue
            seen_names.add(name)

            # Determine sub-type from name
            upper = raw_name.upper()
            ctype = "limit"
            if "TIMEOUT" in upper or "EXPIRE" in upper:
                ctype = "timeout"

            constraints.append(ConstraintDict(
                name=name,
                description=f"Numeric limit defined as {raw_name} = {value}",
                type=ctype,
                value=value,
                confidence=0.7,
            ))

        # 2. Timeout values from comments and code
        lines_scanned: set = set()
        for match in _TIMEOUT_RE.finditer(source):
            line_no = source[:match.start()].count("\n")
            if line_no in lines_scanned:
                continue
            lines_scanned.add(line_no)

            raw_val = match.group("value")
            unit = match.group("unit").lower()
            # Normalise to seconds for consistency
            multipliers = {
                "ms": 0.001, "s": 1, "sec": 1, "second": 1, "seconds": 1,
                "m": 60, "min": 60, "minute": 60, "minutes": 60,
                "h": 3600, "hour": 3600, "hours": 3600,
                "d": 86400, "day": 86400, "days": 86400,
            }
            mult = multipliers.get(unit, 1)
            seconds = float(raw_val) * mult
            display = f"{raw_val}{unit}"

            name = f"timeout_{int(seconds)}s"
            if name in seen_names:
                name = f"timeout_{int(seconds)}s_line{line_no}"
            if name in seen_names:
                continue
            seen_names.add(name)

            constraints.append(ConstraintDict(
                name=name,
                description=f"Timeout constraint of {display} found in source",
                type="timeout",
                value=display,
                confidence=0.6,
            ))

        # 3. Invariant / dependency comments
        invariant_re = re.compile(
            r"^\s*(?://|#|/\*+)\s*"
            r"(?P<text>(?:@invariant|@precondition|@postcondition|must always|"
            r"requires|depends on|dependency)[^\n]*)",
            re.MULTILINE | re.IGNORECASE,
        )
        for match in invariant_re.finditer(source):
            text = match.group("text").strip()
            # Strip the tag itself
            text = re.sub(
                r"^@(?:invariant|precondition|postcondition)\s*:?\s*",
                "", text, flags=re.IGNORECASE,
            )
            if not text or len(text) < 5:
                continue

            name = self._derive_rule_name(text, 0)
            name = f"invariant_{name}" if not name.startswith("invariant") else name
            if name in seen_names:
                continue
            seen_names.add(name)

            ctype = "dependency" if re.search(
                r"\b(requires|depends|dependency)\b", text, re.IGNORECASE
            ) else "invariant"

            constraints.append(ConstraintDict(
                name=name,
                description=_truncate_description(text),
                type=ctype,
                value=_truncate_description(text, 80),
                confidence=0.6,
            ))

        return constraints
