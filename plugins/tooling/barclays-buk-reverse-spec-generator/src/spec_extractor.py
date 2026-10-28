"""
spec_extractor.py - Core BDD spec extraction framework.

Provides a base extractor class and concrete extraction methods that parse
source code files into structured spec dictionaries matching the .spec format.

Architecture:
    BaseExtractor (abstract base)
        |- extract_entities()    -> list[EntityDict]
        |- extract_behaviors()   -> list[BehaviorDict]
        |- extract_rules()       -> list[RuleDict]
        |- extract_constraints() -> list[ConstraintDict]
        |- build_spec()          -> SpecDict
        |- integrate()           -> SpecDict (merge multiple results)

Confidence scoring:
    1.0  - Explicitly documented (docstring / JavaDoc / JSDoc)
    0.8  - Clearly visible signature (type hints, annotations)
    0.6  - Inferable from naming and structure
    0.4  - Weak signal (single keyword, no context)
    0.2  - Speculative (fallback heuristic)

Only items with confidence >= CONFIDENCE_THRESHOLD are included in the
final spec by default.  This can be overridden on construction.
"""

from __future__ import annotations

import re
import abc
import textwrap
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD: float = 0.5
"""Default minimum confidence for an extraction to be included in a spec."""


# ---------------------------------------------------------------------------
# Typed data structures
# ---------------------------------------------------------------------------

@dataclass
class PropertyDict:
    """Represents a single entity property."""

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Optional[str] = None
    enum: Optional[list] = None
    confidence: float = 1.0

    def to_spec_dict(self) -> dict:
        """Convert to a spec-format property dict (drops confidence)."""
        d: dict = {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description or f"Property {self.name}",
        }
        if self.default is not None:
            d["default"] = self.default
        if self.enum:
            d["enum"] = self.enum
        return d


@dataclass
class EntityDict:
    """Represents a data structure / class extracted from source code."""

    name: str
    description: str = ""
    properties: list = field(default_factory=list)  # list[PropertyDict]
    confidence: float = 1.0
    source_line: Optional[int] = None

    def to_spec_dict(self) -> dict:
        """Convert to a spec-format entity dict."""
        props = [
            p.to_spec_dict() if isinstance(p, PropertyDict) else p
            for p in self.properties
            if not isinstance(p, PropertyDict) or p.confidence >= CONFIDENCE_THRESHOLD
        ]
        return {
            "name": self.name,
            "description": self.description or f"Data entity {self.name}",
            "properties": props or [
                {"name": "id", "type": "string", "required": True,
                 "description": f"Unique identifier for {self.name}"}
            ],
        }


@dataclass
class BehaviorDict:
    """Represents a function / method extracted as a BDD behavior."""

    name: str
    description: str = ""
    given: list = field(default_factory=list)   # list[str]
    when: list = field(default_factory=list)    # list[str]
    then: list = field(default_factory=list)    # list[str]
    examples: list = field(default_factory=list)  # list[dict]
    confidence: float = 1.0
    source_line: Optional[int] = None

    def to_spec_dict(self) -> dict:
        """Convert to a spec-format behavior dict."""
        d: dict = {
            "name": self.name,
            "description": self.description or f"Behavior {self.name}",
            "given": self.given or ["system is operational"],
            "when": self.when or [f"{self.name} is invoked"],
            "then": self.then or ["operation completes successfully"],
        }
        if self.examples:
            d["examples"] = self.examples
        return d


@dataclass
class RuleDict:
    """Represents a business rule extracted from conditional logic."""

    name: str
    description: str = ""
    condition: str = ""
    action: str = ""
    confidence: float = 1.0
    source_line: Optional[int] = None

    def to_spec_dict(self) -> dict:
        """Convert to a spec-format rule dict."""
        return {
            "name": self.name,
            "description": self.description or f"Business rule {self.name}",
            "condition": self.condition or "when condition is met",
            "action": self.action or "then action is performed",
        }


@dataclass
class ConstraintDict:
    """Represents a constraint extracted from assertions, annotations, or comments."""

    name: str
    description: str = ""
    type: str = "invariant"   # limit | invariant | dependency | timeout
    value: str = ""
    confidence: float = 1.0
    source_line: Optional[int] = None

    def to_spec_dict(self) -> dict:
        """Convert to a spec-format constraint dict."""
        return {
            "name": self.name,
            "description": self.description or f"Constraint {self.name}",
            "type": self.type,
            "value": self.value or "see source code for details",
        }


@dataclass
class ExtractionResult:
    """Aggregated result from a single-file extraction pass."""

    entities: list = field(default_factory=list)       # list[EntityDict]
    behaviors: list = field(default_factory=list)      # list[BehaviorDict]
    rules: list = field(default_factory=list)          # list[RuleDict]
    constraints: list = field(default_factory=list)    # list[ConstraintDict]
    language: str = "unknown"
    source_file: str = ""
    warnings: list = field(default_factory=list)       # list[str]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _to_snake_case(name: str) -> str:
    """
    Convert a CamelCase / PascalCase / mixedCase name to snake_case.

    Also strips leading/trailing underscores and collapses consecutive
    underscores to a single one.

    Args:
        name: Raw identifier string.

    Returns:
        Lowercased snake_case identifier safe for use in spec files.
    """
    # Insert underscore before transitions from lowercase → uppercase
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Insert underscore before transitions uppercase sequence → uppercase+lowercase
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = s.lower()
    # Replace any non-alphanumeric-underscore with underscore
    s = re.sub(r"[^a-z0-9_]", "_", s)
    # Collapse consecutive underscores
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    # Must start with letter or underscore
    if s and s[0].isdigit():
        s = "_" + s
    return s or "unknown"


def _to_pascal_case(name: str) -> str:
    """
    Convert a snake_case / mixedCase name to PascalCase.

    If the input is already PascalCase (starts with uppercase and has no
    underscores/dashes), it is returned as-is.  This preserves class names
    like ``OrderService`` instead of converting them to ``Orderservice``.

    Args:
        name: Raw identifier string.

    Returns:
        PascalCase string suitable for entity names.
    """
    # If already PascalCase (no separators, starts uppercase), preserve it
    if name and name[0].isupper() and not re.search(r"[_\s-]", name):
        return name
    parts = re.split(r"[_\s-]+", name)
    return "".join(p.capitalize() for p in parts if p) or "Unknown"


def _truncate_description(text: str, max_len: int = 200) -> str:
    """
    Truncate a description to fit within spec limits (10–500 chars).

    Preserves whole words where possible.

    Args:
        text: Raw description text.
        max_len: Maximum allowed length (capped at 500).

    Returns:
        Cleaned, truncated description string.
    """
    max_len = min(max_len, 500)
    text = " ".join(text.split())   # Normalise whitespace
    if len(text) <= max_len:
        return text
    # Truncate to last word boundary
    truncated = text[:max_len - 3]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        truncated = truncated[:last_space]
    return truncated + "..."


def _clean_identifier(raw: str) -> str:
    """
    Strip non-identifier characters and ensure result is a valid snake_case name.

    Args:
        raw: Raw extracted name string.

    Returns:
        Valid snake_case identifier or 'unknown'.
    """
    # Remove language-specific noise characters
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned.lower() or "unknown"


def _normalize_type(raw: str) -> str:
    """
    Map a language-specific type annotation to a canonical spec type.

    Supported canonical types: string, number, boolean, null, array, object.

    Args:
        raw: Raw type string from source code (e.g. 'int', 'String', 'bool').

    Returns:
        Canonical spec type string.
    """
    mapping: dict[str, str] = {
        # Integer-like types
        "int": "number", "integer": "number", "long": "number",
        "short": "number", "byte": "number", "float": "number",
        "double": "number", "decimal": "number", "bigdecimal": "number",
        "biginteger": "number", "number": "number", "num": "number",
        "uint": "number", "uint32": "number", "uint64": "number",
        "int32": "number", "int64": "number",
        # String-like
        "str": "string", "string": "string", "varchar": "string",
        "text": "string", "char": "string", "character": "string",
        "uuid": "string", "uri": "string", "url": "string",
        "date": "string", "datetime": "string", "timestamp": "string",
        # Boolean
        "bool": "boolean", "boolean": "boolean",
        # Null / optional
        "none": "null", "null": "null", "void": "null", "unit": "null",
        "optional": "null",
        # Collections
        "list": "array", "array": "array", "set": "array", "tuple": "array",
        "sequence": "array", "collection": "array", "iterable": "array",
        "vector": "array", "queue": "array", "stack": "array",
        # Objects / maps
        "dict": "object", "map": "object", "hashmap": "object",
        "object": "object", "any": "object", "unknown": "object",
    }
    normalised = raw.strip().lower().rstrip("?")  # Strip Kotlin-style nullability
    # Handle generic wrappers: List<T> → array, Map<K,V> → object
    if re.match(r"(list|array|set|collection|iterable|sequence)\s*[<\[]", normalised):
        return "array"
    if re.match(r"(map|dict|hashmap|linkedhashmap|sortedmap)\s*[<\[]", normalised):
        return "object"
    if re.match(r"optional\s*[<\[]", normalised):
        return "null"
    return mapping.get(normalised, "string")


# ---------------------------------------------------------------------------
# Base extractor
# ---------------------------------------------------------------------------

class BaseExtractor(abc.ABC):
    """
    Abstract base class for language-specific source code extractors.

    Subclasses must implement the four core extraction methods.  The
    :meth:`build_spec` and :meth:`integrate` helpers are provided by this
    base class and do not need to be overridden.

    Args:
        confidence_threshold: Minimum confidence score (0.0–1.0) required for
            an extracted item to be included in the final spec.  Defaults to
            :data:`CONFIDENCE_THRESHOLD`.
        module_name: Optional module name override.  If not supplied the
            extractor will attempt to derive one from the source file name.
    """

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        module_name: Optional[str] = None,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.module_name = module_name

    # ------------------------------------------------------------------
    # Abstract extraction methods (must be implemented by subclasses)
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def extract_entities(self, source: str) -> list:
        """
        Extract data entities (classes, structs, data models) from source code.

        Each returned :class:`EntityDict` should represent a single cohesive
        data structure with its fields as :class:`PropertyDict` items.

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`EntityDict` instances.
        """

    @abc.abstractmethod
    def extract_behaviors(self, source: str) -> list:
        """
        Extract observable behaviors (functions, methods, endpoints) from source.

        Each :class:`BehaviorDict` should capture the pre/post conditions
        visible from the function signature, docstring, or annotations.

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`BehaviorDict` instances.
        """

    @abc.abstractmethod
    def extract_rules(self, source: str) -> list:
        """
        Extract business rules from conditional logic, guard clauses, and
        inline comments that describe decision logic.

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`RuleDict` instances.
        """

    @abc.abstractmethod
    def extract_constraints(self, source: str) -> list:
        """
        Extract constraints from assertions, annotations, magic numbers,
        and architectural comments.

        Args:
            source: Raw source code text.

        Returns:
            List of :class:`ConstraintDict` instances.
        """

    # ------------------------------------------------------------------
    # Provided helpers (call from subclasses or external code)
    # ------------------------------------------------------------------

    def extract_all(self, source: str, source_file: str = "") -> ExtractionResult:
        """
        Run all four extraction methods and aggregate into an :class:`ExtractionResult`.

        Each method is called independently so that a failure in one does not
        prevent the others from running.

        Args:
            source: Raw source code text.
            source_file: Optional path to the source file (for error messages).

        Returns:
            :class:`ExtractionResult` containing all extracted items and any
            warnings encountered during extraction.
        """
        result = ExtractionResult(source_file=source_file)
        result.language = self._language_name()

        for attr, method in (
            ("entities", self.extract_entities),
            ("behaviors", self.extract_behaviors),
            ("rules", self.extract_rules),
            ("constraints", self.extract_constraints),
        ):
            try:
                items = method(source)
                setattr(result, attr, items or [])
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(
                    f"extract_{attr} raised {type(exc).__name__}: {exc}"
                )

        return result

    def build_spec(
        self,
        source: str,
        source_file: str = "",
        description: str = "",
    ) -> dict:
        """
        Build a complete spec dictionary from a single source file.

        Runs all extractors, applies the confidence threshold filter, and
        assembles a spec dict that is ready for :func:`spec_serializer.dump_yaml`.

        Args:
            source: Raw source code text.
            source_file: Optional source file name used to derive the module name.
            description: Optional description for the module.  Falls back to a
                generated description when not supplied.

        Returns:
            Complete spec dict with ``version``, ``module``, ``description``,
            and any non-empty sections (entities, behaviors, rules, constraints).
        """
        result = self.extract_all(source, source_file)
        return self._assemble_spec(result, source_file, description)

    def integrate(self, results: list, source_file: str = "", description: str = "") -> dict:
        """
        Merge multiple :class:`ExtractionResult` objects into a single spec dict.

        Entities, behaviors, rules, and constraints are deduplicated by name;
        the highest-confidence version of each name wins.

        Args:
            results: List of :class:`ExtractionResult` objects to merge.
            source_file: Source file name used to derive the module name.
            description: Description override for the merged spec.

        Returns:
            Merged spec dict.
        """
        merged = ExtractionResult(source_file=source_file)

        for result in results:
            for attr in ("entities", "behaviors", "rules", "constraints"):
                existing = {item.name: item for item in getattr(merged, attr)}
                for item in getattr(result, attr):
                    existing_item = existing.get(item.name)
                    if existing_item is None or item.confidence > existing_item.confidence:
                        existing[item.name] = item
                setattr(merged, attr, list(existing.values()))

            merged.warnings.extend(result.warnings)

        return self._assemble_spec(merged, source_file, description)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _language_name(self) -> str:
        """Return a human-readable language name for this extractor."""
        return type(self).__name__.replace("Extractor", "").lower() or "unknown"

    def _derive_module_name(self, source_file: str) -> str:
        """
        Derive a snake_case module name from a source file path.

        Args:
            source_file: File path string (may be empty).

        Returns:
            Valid snake_case module name.
        """
        if self.module_name:
            return self.module_name
        if not source_file:
            return "extracted_module"
        # Take the base filename without extension
        import os
        base = os.path.basename(source_file)
        stem = re.sub(r"\.[^.]+$", "", base)  # Remove extension
        return _to_snake_case(stem) or "extracted_module"

    def _filter_by_confidence(self, items: list) -> list:
        """
        Filter a list of extraction dataclasses by :attr:`confidence_threshold`.

        Args:
            items: List of dataclass instances with a ``confidence`` attribute.

        Returns:
            Filtered list containing only items meeting the threshold.
        """
        return [item for item in items if item.confidence >= self.confidence_threshold]

    def _assemble_spec(
        self,
        result: ExtractionResult,
        source_file: str,
        description: str,
    ) -> dict:
        """
        Convert an :class:`ExtractionResult` into a spec-format dictionary.

        Applies confidence filtering, converts dataclasses to plain dicts,
        and fills in mandatory root-level fields.

        Args:
            result: Extraction result to assemble.
            source_file: Source file path (used to derive module name).
            description: Optional description override.

        Returns:
            Spec-format dictionary.
        """
        module = self._derive_module_name(source_file)

        entities = [
            e.to_spec_dict()
            for e in self._filter_by_confidence(result.entities)
        ]
        behaviors = [
            b.to_spec_dict()
            for b in self._filter_by_confidence(result.behaviors)
        ]
        rules = [
            r.to_spec_dict()
            for r in self._filter_by_confidence(result.rules)
        ]
        constraints = [
            c.to_spec_dict()
            for c in self._filter_by_confidence(result.constraints)
        ]

        desc = description or (
            f"Extracted specification for {module} "
            f"({result.language} source)"
        )
        desc = _truncate_description(desc)
        if len(desc) < 10:
            desc = f"Behavioral specification for the {module} module"

        spec: dict = {
            "version": "1.0",
            "module": module,
            "description": desc,
        }

        if entities:
            spec["entities"] = entities
        if behaviors:
            spec["behaviors"] = behaviors
        if rules:
            spec["rules"] = rules
        if constraints:
            spec["constraints"] = constraints

        # Spec must have at least one section; add a placeholder if empty
        if not any(key in spec for key in ("entities", "behaviors", "rules", "constraints")):
            spec["behaviors"] = [
                {
                    "name": "module_operation",
                    "description": f"Primary operation of the {module} module",
                    "given": ["module is initialised"],
                    "when": ["operation is requested"],
                    "then": ["operation completes without error"],
                }
            ]

        return spec

    def _ensure_description(self, text: str, fallback: str) -> str:
        """
        Return a valid description string (10–500 chars).

        Args:
            text: Candidate description (may be empty).
            fallback: Fallback string if text is too short.

        Returns:
            Non-empty description of at least 10 characters.
        """
        cleaned = " ".join(text.split()) if text else ""
        if len(cleaned) < 10:
            cleaned = fallback
        return _truncate_description(cleaned)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def get_extractor(language: str, **kwargs) -> BaseExtractor:
    """
    Return the appropriate extractor for the given language.

    Lazily imports language-specific modules to keep the base extractor
    free of hard dependencies.

    Args:
        language: Language name (case-insensitive).  Supported values:
            ``python``, ``java``, ``javascript``, ``js``, ``generic``.
        **kwargs: Additional keyword arguments forwarded to the extractor
            constructor (e.g. ``confidence_threshold``, ``module_name``).

    Returns:
        Instantiated :class:`BaseExtractor` subclass.

    Raises:
        ValueError: If the language is not supported.
    """
    lang = language.lower().strip()
    try:
        if lang in ("python", "py"):
            from patterns.python import PythonExtractor
            return PythonExtractor(**kwargs)
        elif lang in ("java",):
            from patterns.java import JavaExtractor
            return JavaExtractor(**kwargs)
        elif lang in ("javascript", "js", "typescript", "ts"):
            from patterns.javascript import JavaScriptExtractor
            return JavaScriptExtractor(**kwargs)
        else:
            from patterns.generic import GenericExtractor
            return GenericExtractor(**kwargs)
    except ImportError:
        # Fallback: try relative import (when used as a package)
        try:
            if lang in ("python", "py"):
                from src.patterns.python import PythonExtractor
                return PythonExtractor(**kwargs)
            elif lang in ("java",):
                from src.patterns.java import JavaExtractor
                return JavaExtractor(**kwargs)
            elif lang in ("javascript", "js", "typescript", "ts"):
                from src.patterns.javascript import JavaScriptExtractor
                return JavaScriptExtractor(**kwargs)
            else:
                from src.patterns.generic import GenericExtractor
                return GenericExtractor(**kwargs)
        except ImportError as exc:
            raise ValueError(
                f"Could not import extractor for language '{language}': {exc}"
            ) from exc


def detect_language(source: str, filename: str = "") -> str:
    """
    Heuristically detect the programming language of a source file.

    Detection order:
    1. File extension (most reliable)
    2. Shebang line
    3. Keyword fingerprinting

    Args:
        source: Raw source code text.
        filename: Optional filename (used for extension detection).

    Returns:
        Detected language name (``python``, ``java``, ``javascript``, or
        ``generic`` when detection fails).
    """
    import os

    if filename:
        ext = os.path.splitext(filename)[1].lower()
        _ext_map = {
            ".py": "python",
            ".java": "java",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript",
        }
        if ext in _ext_map:
            return _ext_map[ext]

    # Shebang detection
    first_line = source.split("\n", 1)[0]
    if "python" in first_line:
        return "python"
    if "node" in first_line or "deno" in first_line:
        return "javascript"

    # Keyword fingerprinting
    java_score = sum([
        bool(re.search(r"\bpublic\s+class\b", source)),
        bool(re.search(r"\bimport\s+java\.", source)),
        bool(re.search(r"\bSystem\.out\.", source)),
        bool(re.search(r"@Override\b", source)),
        bool(re.search(r"\bvoid\s+\w+\s*\(", source)),
    ])
    python_score = sum([
        bool(re.search(r"\bdef\s+\w+\s*\(", source)),
        bool(re.search(r"\bimport\s+\w+\b", source)),
        bool(re.search(r'"""', source)),
        bool(re.search(r"\bself\b", source)),
        bool(re.search(r":\s*$", source, re.MULTILINE)),
    ])
    js_score = sum([
        bool(re.search(r"\bconst\s+\w+\s*=", source)),
        bool(re.search(r"\bfunction\s+\w+\s*\(", source)),
        bool(re.search(r"\)(?:\s*:\s*\w+)?\s*=>", source)),   # arrow fn (with or without braces)
        bool(re.search(r"\brequire\s*\(", source)),
        bool(re.search(r"\bconsole\.log\b", source)),
        bool(re.search(r"\b(?:let|const|var)\s+\w+\s*=\s*(?:async\s+)?\(", source)),
        bool(re.search(r"\binterface\s+[A-Z]\w+\s*\{", source)),   # TS interface
    ])

    scores = {"java": java_score, "python": python_score, "javascript": js_score}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] >= 2 else "generic"
