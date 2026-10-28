"""
implementer.py — generate code stubs for spec-led behaviors.

Only acts on divergences where:
    source_of_truth == "spec"
AND
    divergence_status in ("missing_impl", "diverged")

These are behaviors that the spec says must exist but the code does not
implement (or implements incorrectly). The stubs are NOT production code —
they are scaffolding to progress the verification loop: make tests compile,
make the intent explicit, let the developer fill in the logic.

Supported target languages: java, python, javascript (basic stubs)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from .divergence_classifier import Divergence, MISSING_IMPL, DIVERGED

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_stubs(
    spec: dict,
    divergences: List[Divergence],
    language: str,
    target_dir,
) -> List[str]:
    """
    Generate code stubs for spec-led divergences.

    Parameters
    ----------
    spec        : parsed spec dict
    divergences : list of Divergence objects from divergence_classifier
    language    : "java" | "python" | "javascript"
    target_dir  : directory to write stub files into

    Returns
    -------
    List of file paths written.
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Filter to only spec-led, actionable divergences
    candidates = [
        d for d in divergences
        if d.source_of_truth == "spec"
        and d.divergence_type in (MISSING_IMPL, DIVERGED)
        and d.item_type == "behaviors"
    ]

    if not candidates:
        return []

    lang = language.lower().strip()
    if lang == "java":
        return _write_java_stubs(spec, candidates, target_dir)
    elif lang == "python":
        return _write_python_stubs(spec, candidates, target_dir)
    elif lang in ("javascript", "typescript", "js", "ts"):
        return _write_js_stubs(spec, candidates, target_dir)
    else:
        return _write_generic_stubs(spec, candidates, target_dir)


# ---------------------------------------------------------------------------
# Java stub generation
# ---------------------------------------------------------------------------


def _write_java_stubs(spec: dict, divergences: List[Divergence], target_dir: Path) -> List[str]:
    """Generate a single Java stub class containing all missing/diverged behaviors."""
    module = spec.get("module", "unknown_module")
    class_name = _to_pascal_case(module) + "Stubs"
    file_path = target_dir / f"{class_name}.java"

    lines: list = [
        "// AUTO-GENERATED STUBS — fill in implementation",
        f"// Source: {spec.get('module', '')} spec",
        "// Run /converge after implementing to verify alignment",
        "",
        "package com.barclays.api.stub;",
        "",
        "import org.springframework.http.ResponseEntity;",
        "import org.springframework.web.bind.annotation.*;",
        "",
        "/**",
        f" * Stubs generated from spec: {spec.get('module', '')}",
        f" * Description: {spec.get('description', '')}",
        " *",
        " * These are scaffolding stubs. Each method throws UnsupportedOperationException",
        " * until a real implementation is provided.",
        " */",
        "@RestController",
        f"public class {class_name} {{",
        "",
    ]

    behaviors_by_name = {b.get("name"): b for b in spec.get("behaviors", [])}

    for div in divergences:
        behavior = behaviors_by_name.get(div.item_name)
        if behavior is None:
            continue
        lines.extend(_behavior_to_java_method(behavior, div.divergence_type))
        lines.append("")

    lines.append("}")

    _write_file(file_path, lines)
    return [str(file_path)]


def _behavior_to_java_method(behavior: dict, divergence_type: str) -> List[str]:
    """Render a single Java stub method from a behavior spec entry."""
    name = behavior.get("name", "unknown")
    description = behavior.get("description", "")
    given = behavior.get("given", [])
    when_list = behavior.get("when", [])
    then_list = behavior.get("then", [])

    http_method = _infer_http_method(when_list)
    method_name = _to_camel_case(name)
    path = "/" + name.replace("_", "-")

    lines: list = []
    lines.append(f"    /**")
    lines.append(f"     * {description}")
    if given:
        lines.append(f"     *")
        lines.append(f"     * Given:")
        for g in given:
            lines.append(f"     *   - {g}")
    if when_list:
        lines.append(f"     *")
        lines.append(f"     * When:")
        for w in when_list:
            lines.append(f"     *   - {w}")
    if then_list:
        lines.append(f"     *")
        lines.append(f"     * Then:")
        for t in then_list:
            lines.append(f"     *   - {t}")
    lines.append(f"     *")
    lines.append(f"     * NOTE: stub — divergence_type={divergence_type}")
    lines.append(f"     */")

    if http_method == "GET":
        lines.append(f'    @GetMapping("{path}")')
    elif http_method == "POST":
        lines.append(f'    @PostMapping("{path}")')
    elif http_method == "PUT":
        lines.append(f'    @PutMapping("{path}")')
    elif http_method == "DELETE":
        lines.append(f'    @DeleteMapping("{path}")')
    else:
        lines.append(f'    @RequestMapping(value = "{path}", method = RequestMethod.POST)')

    lines.append(f"    public ResponseEntity<?> {method_name}() {{")
    lines.append(f'        throw new UnsupportedOperationException("Stub: {name} not implemented");')
    lines.append(f"    }}")

    return lines


# ---------------------------------------------------------------------------
# Python stub generation
# ---------------------------------------------------------------------------


def _write_python_stubs(spec: dict, divergences: List[Divergence], target_dir: Path) -> List[str]:
    """Generate a Python stub module containing all missing/diverged behaviors."""
    module = spec.get("module", "unknown_module")
    file_path = target_dir / f"{module}_stubs.py"

    lines: list = [
        '"""',
        f"AUTO-GENERATED STUBS for {module}",
        f"Description: {spec.get('description', '')}",
        "",
        "Fill in the implementation for each function.",
        'Run /converge after implementing to verify alignment.',
        '"""',
        "",
        "from typing import Any, Optional",
        "",
        "",
    ]

    behaviors_by_name = {b.get("name"): b for b in spec.get("behaviors", [])}

    for div in divergences:
        behavior = behaviors_by_name.get(div.item_name)
        if behavior is None:
            continue
        lines.extend(_behavior_to_python_function(behavior, div.divergence_type))
        lines.append("")
        lines.append("")

    _write_file(file_path, lines)
    return [str(file_path)]


def _behavior_to_python_function(behavior: dict, divergence_type: str) -> List[str]:
    """Render a single Python stub function from a behavior spec entry."""
    name = behavior.get("name", "unknown")
    description = behavior.get("description", "")
    given = behavior.get("given", [])
    when_list = behavior.get("when", [])
    then_list = behavior.get("then", [])
    examples = behavior.get("examples", [])

    lines: list = []
    lines.append(f"def {name}(*args: Any, **kwargs: Any) -> Any:")
    lines.append(f'    """')
    lines.append(f"    {description}")
    if given:
        lines.append(f"")
        lines.append(f"    Given:")
        for g in given:
            lines.append(f"        - {g}")
    if when_list:
        lines.append(f"")
        lines.append(f"    When:")
        for w in when_list:
            lines.append(f"        - {w}")
    if then_list:
        lines.append(f"")
        lines.append(f"    Then:")
        for t in then_list:
            lines.append(f"        - {t}")
    if examples:
        lines.append(f"")
        lines.append(f"    Examples:")
        for ex in examples[:3]:
            inp = ex.get("input", "")
            out = ex.get("output", "")
            lines.append(f"        Input:  {inp}")
            lines.append(f"        Output: {out}")
    lines.append(f"")
    lines.append(f"    Note: stub — divergence_type={divergence_type}")
    lines.append(f'    """')
    lines.append(f'    raise NotImplementedError("{name} is not implemented")')
    return lines


# ---------------------------------------------------------------------------
# JavaScript stub generation
# ---------------------------------------------------------------------------


def _write_js_stubs(spec: dict, divergences: List[Divergence], target_dir: Path) -> List[str]:
    """Generate a JavaScript/TypeScript stub module."""
    module = spec.get("module", "unknown_module")
    file_path = target_dir / f"{module}.stubs.js"

    lines: list = [
        "// AUTO-GENERATED STUBS — fill in implementation",
        f"// Source: {spec.get('module', '')} spec",
        "// Run /converge after implementing to verify alignment",
        "",
    ]

    behaviors_by_name = {b.get("name"): b for b in spec.get("behaviors", [])}

    for div in divergences:
        behavior = behaviors_by_name.get(div.item_name)
        if behavior is None:
            continue
        lines.extend(_behavior_to_js_function(behavior, div.divergence_type))
        lines.append("")

    lines.append("module.exports = {")
    for div in divergences:
        lines.append(f"  {_to_camel_case(div.item_name)},")
    lines.append("};")

    _write_file(file_path, lines)
    return [str(file_path)]


def _behavior_to_js_function(behavior: dict, divergence_type: str) -> List[str]:
    name = behavior.get("name", "unknown")
    description = behavior.get("description", "")
    given = behavior.get("given", [])
    then_list = behavior.get("then", [])
    camel = _to_camel_case(name)

    lines: list = []
    lines.append(f"/**")
    lines.append(f" * {description}")
    if given:
        lines.append(f" *")
        given_str = "; ".join(given)
        lines.append(f" * Given: {given_str}")
    if then_list:
        lines.append(f" *")
        then_str = "; ".join(then_list)
        lines.append(f" * Then: {then_str}")
    lines.append(f" * @stub divergence_type={divergence_type}")
    lines.append(f" */")
    lines.append(f"async function {camel}(...args) {{")
    lines.append(f'  throw new Error("Stub: {name} not implemented");')
    lines.append(f"}}")
    return lines


# ---------------------------------------------------------------------------
# Generic stub generation (fallback)
# ---------------------------------------------------------------------------


def _write_generic_stubs(spec: dict, divergences: List[Divergence], target_dir: Path) -> List[str]:
    """Write a plain-text stub manifest for unknown languages."""
    module = spec.get("module", "unknown_module")
    file_path = target_dir / f"{module}.stubs.txt"

    lines: list = [
        f"STUB MANIFEST: {module}",
        f"Description: {spec.get('description', '')}",
        "",
        "The following behaviors are spec-led but have no implementation:",
        "",
    ]

    behaviors_by_name = {b.get("name"): b for b in spec.get("behaviors", [])}
    for div in divergences:
        behavior = behaviors_by_name.get(div.item_name)
        if not behavior:
            continue
        lines.append(f"  [{div.divergence_type.upper()}] {div.item_name}")
        desc = behavior.get("description", "")
        if desc:
            lines.append(f"    {desc}")
        given = behavior.get("given", [])
        if given:
            lines.append(f"    Given: {'; '.join(given)}")
        then_list = behavior.get("then", [])
        if then_list:
            lines.append(f"    Then:  {'; '.join(then_list)}")
        lines.append("")

    _write_file(file_path, lines)
    return [str(file_path)]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _infer_http_method(when_list: list) -> str:
    """Infer HTTP method from 'when' clause text."""
    text = " ".join(when_list).upper()
    for method in ("DELETE", "PUT", "PATCH", "POST", "GET"):
        if method in text:
            return method
    return "POST"


def _to_pascal_case(s: str) -> str:
    return "".join(word.capitalize() for word in re.split(r"[_\-\s]+", s) if word)


def _to_camel_case(s: str) -> str:
    parts = [w for w in re.split(r"[_\-\s]+", s) if w]
    if not parts:
        return s
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _write_file(path: Path, lines: list) -> None:
    """Write lines to path with LF line endings."""
    content = "\n".join(lines) + "\n"
    path.write_text(content, encoding="utf-8")
