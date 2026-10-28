# Language-specific pattern extractors
"""
Pattern extractors for different programming languages.

Available extractors:
    GenericExtractor   - Language-agnostic heuristic extraction (fallback)
    PythonExtractor    - Python-specific extraction (classes, type hints, docstrings)
    JavaExtractor      - Java-specific extraction (JavaDoc, annotations, guards)
    JavaScriptExtractor - JavaScript/TypeScript extraction (JSDoc, interfaces, arrows)

Use :func:`spec_extractor.get_extractor` to obtain the correct extractor for a
given language name, or import the extractor classes directly.
"""

from .generic import GenericExtractor
from .python import PythonExtractor
from .java import JavaExtractor
from .javascript import JavaScriptExtractor

__all__ = [
    "GenericExtractor",
    "PythonExtractor",
    "JavaExtractor",
    "JavaScriptExtractor",
]
