#!/usr/bin/env python3
"""iOS Call Graph Analyzer — builds call graph for Swift/ObjC using AST-based analysis.

Extracts entities (classes, structs, enums, protocols, methods, properties) and builds
a usage graph showing which entities reference which others.

ENHANCED: Now uses AST-based reference scanning instead of pure regex to improve
accuracy. Type annotations, protocol conformances, inheritance chains are properly
detected instead of relying on string counts.
"""

import re
import json
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

try:
    from .ast_reference_scanner import build_ios_ast_graph, SWIFT_LANGUAGE
    from .objc_syntax import swift_base_names
except ImportError:
    from ast_reference_scanner import build_ios_ast_graph, SWIFT_LANGUAGE
    from objc_syntax import swift_base_names

try:
    from .arbiter_meta import require_stamp, stamp, write_json
except ImportError:
    from arbiter_meta import require_stamp, stamp, write_json

try:
    from .ios_framework_rules import FRAMEWORK_PROTOCOLS, TEST_BASE_CLASSES, is_test_path
except ImportError:
    from ios_framework_rules import FRAMEWORK_PROTOCOLS, TEST_BASE_CLASSES, is_test_path

if SWIFT_LANGUAGE is not None:
    from tree_sitter import Parser


# Swift entity patterns
SWIFT_CLASS_PATTERN = re.compile(
    r'^\s*(?:public|open|internal|fileprivate|private)?\s*'
    r'(?:final\s+)?'
    r'(class|struct|enum|protocol|actor)\s+'
    r'(?!func\b|var\b|let\b|subscript\b)'
    r'([A-Za-z_]\w*)'
    r'(?:\s*<[^>]+>)?'  # generics
    r'(?:\s*:\s*([^{]+))?',  # inheritance/conformances
    re.MULTILINE
)

SWIFT_FUNC_PATTERN = re.compile(
    r'^\s*(?:@\w+\s+)*'
    r'(?:public|open|internal|fileprivate|private)?\s*'
    r'(?:static\s+|class\s+)?'
    r'(?:override\s+)?'
    r'func\s+([A-Za-z_]\w*)\s*\(',
    re.MULTILINE
)

SWIFT_PROPERTY_PATTERN = re.compile(
    r'^\s*(?:@\w+\s+)*'
    r'(?:public|open|internal|fileprivate|private)?\s*'
    r'(?:static\s+|class\s+)?'
    r'(?:lazy\s+)?'
    r'(?:var|let)\s+([A-Za-z_]\w*)',
    re.MULTILINE
)

SWIFT_ANNOTATION_PATTERN = re.compile(r'@(\w+)')

# ObjC entity patterns
OBJC_INTERFACE_PATTERN = re.compile(
    r'@interface\s+(\w+)\s*(?::\s*(\w+))?(?:\s*<([^>]+)>)?'
)
OBJC_IMPL_PATTERN = re.compile(r'@implementation\s+(\w+)')
OBJC_METHOD_PATTERN = re.compile(r'^[-+]\s*\([^)]+\)\s*(\w+)', re.MULTILINE)

# Access level detection
ACCESS_PATTERN = re.compile(r'^\s*(public|open|internal|fileprivate|private)')

# Test file detection
TEST_PATH_PATTERNS = ["Tests/", "Test/", "UITests/", "Specs/", "XCTests/"]

EXCLUDE_PATTERNS = [
    "Pods/", "Carthage/", ".build/", "DerivedData/",
    "node_modules/", ".arbiter/", ".git/",
    ".framework/", ".xcframework/",  # vendored binary SDKs: headers only, not repo code
]


def build_ios_call_graph(repo_path: str, verbose: bool = False, use_ast: bool = True,
                         ast_graph: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build call graph for iOS project.

    Args:
        repo_path: Path to iOS project
        verbose: Print progress
        use_ast: Use tree-sitter for Swift entities and type references (default)
            vs. regex-only
        ast_graph: Pre-built result of build_ios_ast_graph, to avoid re-scanning

    Returns:
        Call graph with entities, usage, entry points, and cache hash
    """
    repo_path = Path(repo_path).resolve()
    entities = []
    usages = []

    # Scan Swift files
    swift_files = [f for f in repo_path.rglob("*.swift") if not _is_excluded(f)]
    for file_path in swift_files:
        file_entities = _extract_swift_entities(file_path, repo_path, use_ast)
        entities.extend(file_entities)

    if use_ast and ast_graph is None:
        ast_graph = build_ios_ast_graph(str(repo_path))

    # Scan ObjC files (tree-sitter entities come from the AST graph: they are merged
    # across .h/.m files, so they can't be extracted file by file)
    objc_files = [f for f in repo_path.rglob("*.m") if not _is_excluded(f)]
    objc_files += [f for f in repo_path.rglob("*.mm") if not _is_excluded(f)]
    if use_ast and ast_graph["stats"].get("objc_parser") == "tree-sitter":
        entities.extend(ast_graph["objc_entities"])
    else:
        for file_path in objc_files:
            file_entities = _extract_objc_entities(file_path, repo_path)
            entities.extend(file_entities)

    if use_ast and ast_graph["stats"]["parser"] == "tree-sitter":
        if verbose:
            print(f"   Using tree-sitter references for Swift types and methods...")
        usages = merge_ast_usages(entities, ast_graph, repo_path, objc_files)
    else:
        if use_ast and verbose:
            print(f"   tree-sitter unavailable — using grep-based usage counts")
        entity_names = {e["name"] for e in entities}
        usages = _build_usage_graph(entities, entity_names, repo_path, swift_files + objc_files)

    if verbose:
        print(f"   Entities found: {len(entities)}")
        print(f"   Usage references: {len(usages)}")

    # Identify entry points
    entry_points = _identify_ios_entry_points(entities)

    return {
        "entities": entities,
        "usages": usages,
        "entryPoints": entry_points,
        "stats": {
            "total_entities": len(entities),
            "swift_files_scanned": len(swift_files),
            "objc_files_scanned": len(objc_files),
            "usage_edges": len(usages),
            "entry_points": len(entry_points),
        },
        "cache_hash": _compute_cache_hash(repo_path),
    }


def _extract_swift_entities(file_path: Path, repo_path: Path,
                            use_ast: bool = True) -> List[Dict[str, Any]]:
    """Extract entities from a Swift file (tree-sitter when available, else regex)."""
    if use_ast and SWIFT_LANGUAGE is not None:
        return _extract_swift_entities_ast(file_path, repo_path)
    return _extract_swift_entities_regex(file_path, repo_path)


SWIFT_TYPE_DECLARATIONS = ("class_declaration", "protocol_declaration")
SWIFT_FUNC_DECLARATIONS = ("function_declaration", "protocol_function_declaration")


def _extract_swift_entities_ast(file_path: Path, repo_path: Path) -> List[Dict[str, Any]]:
    """Extract types and methods from a Swift file using the tree-sitter syntax tree.

    Unlike the regex extractor, this handles same-line attributes and modifiers
    (`@objc public final class`, `public static func`), multi-line declarations,
    and never matches inside comments or strings.
    """
    entities: List[Dict[str, Any]] = []
    try:
        source = file_path.read_bytes()
    except (IOError, OSError):
        return entities

    rel_path = str(file_path.relative_to(repo_path))
    is_test_file = is_test_path(rel_path)
    is_extension_file = "+" in file_path.stem  # e.g. UIView+LayoutAnchors.swift
    tree = Parser(SWIFT_LANGUAGE).parse(source)

    def visit(node, enclosing_kind: str, enclosing_annotations: List[str],
              enclosing_name: str, is_test: bool) -> None:
        for child in node.named_children:
            if child.type in SWIFT_TYPE_DECLARATIONS:
                kind = _ts_declaration_kind(child)
                annotations = _ts_annotations(child)
                name = _ts_enclosing_name(child)
                # Members of XCTestCase/QuickSpec subclasses are invoked by the test runner
                child_is_test = is_test or any(
                    c.text.decode(errors="replace").split("<")[0] in TEST_BASE_CLASSES
                    for c in child.named_children if c.type == "inheritance_specifier")
                if kind != "extension":
                    entity = _ts_type_entity(child, kind, annotations, rel_path,
                                             child_is_test, source)
                    entity["memberNames"] = _ts_member_names(child)
                    entities.append(entity)
                visit(child, kind, annotations, name, child_is_test)
            elif child.type in SWIFT_FUNC_DECLARATIONS:
                entity = _ts_method_entity(child, rel_path, is_test,
                                           enclosing_kind, enclosing_annotations,
                                           is_extension_file, source)
                if entity:
                    entity["owner"] = enclosing_name or None
                    entities.append(entity)
                # Local functions/types inside a function body are not tracked
            else:
                visit(child, enclosing_kind, enclosing_annotations, enclosing_name, is_test)

    visit(tree.root_node, "", [], "", is_test_file)
    return entities


SWIFT_KEYWORD_NAMES = {"self", "super", "nil", "true", "false", "some", "none"}


def _ts_member_names(type_node) -> List[str]:
    """Methods, properties and nested types declared directly in a type's body."""
    body = next((c for c in type_node.named_children if c.type.endswith("_body")), None)
    names: Set[str] = set()
    for member in (body.named_children if body is not None else []):
        if member.type in SWIFT_FUNC_DECLARATIONS or member.type in SWIFT_TYPE_DECLARATIONS:
            name = member.child_by_field_name("name")
            if name is not None and name.type in ("simple_identifier", "type_identifier"):
                names.add(name.text.decode(errors="replace"))
        elif member.type in ("property_declaration", "protocol_property_declaration"):
            for pattern in member.named_children:
                if pattern.type == "pattern":
                    ident = next((c for c in pattern.named_children if c.type == "simple_identifier"), None)
                    if ident is not None:
                        names.add(ident.text.decode(errors="replace"))
    return sorted(n for n in names if len(n) > 2 and n not in SWIFT_KEYWORD_NAMES)


def _ts_enclosing_name(node) -> str:
    """Type name of a declaration; for `extension Foo<T>: P` → 'Foo'."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return ""
    if name_node.type == "user_type":
        ident = next((c for c in name_node.named_children if c.type == "type_identifier"), name_node)
        return ident.text.decode(errors="replace")
    return name_node.text.decode(errors="replace")


def _ts_type_entity(node, kind: str, annotations: List[str],
                    rel_path: str, is_test: bool, source: bytes) -> Dict[str, Any]:
    name_node = node.child_by_field_name("name")
    inheritance = [
        c.text.decode(errors="replace")
        for c in node.named_children if c.type == "inheritance_specifier"
    ]
    # Same convention as the regex extractor: a class's first inherited type is its
    # superclass — unless it is a known framework protocol (`class Foo: UITableViewDataSource`)
    superclass = None
    if kind == "class" and inheritance and inheritance[0] not in FRAMEWORK_PROTOCOLS:
        superclass = inheritance[0]
    protocols = inheritance[1:] if superclass else inheritance
    return {
        "name": name_node.text.decode(errors="replace"),
        "fullyQualifiedName": name_node.text.decode(errors="replace"),
        "type": kind,
        "file": rel_path,
        "line": name_node.start_point[0] + 1,
        **_ts_line_range(node, source),
        "language": "swift",
        "accessLevel": _ts_access_level(node),
        "inheritsFrom": superclass,
        "protocolConformances": protocols,
        "annotations": annotations,
        "isTestCode": is_test,
        "isOverride": False,
        "isObjCExposed": "@objc" in annotations or "@objcMembers" in annotations,
        "isExtensionMember": False,
    }


def _ts_method_entity(node, rel_path: str, is_test: bool, enclosing_kind: str,
                      enclosing_annotations: List[str], is_extension_file: bool,
                      source: bytes) -> Dict[str, Any] | None:
    name_node = node.child_by_field_name("name")
    if name_node is None or name_node.type != "simple_identifier":
        return None  # operators, e.g. `static func ==`
    annotations = _ts_annotations(node)
    return {
        "name": name_node.text.decode(errors="replace"),
        "fullyQualifiedName": name_node.text.decode(errors="replace"),
        "type": "method",
        "file": rel_path,
        "line": name_node.start_point[0] + 1,
        **_ts_line_range(node, source),
        "language": "swift",
        "accessLevel": _ts_access_level(node),
        "inheritsFrom": None,
        "protocolConformances": [],
        "annotations": annotations,
        "isTestCode": is_test,
        "isOverride": "override" in _ts_modifier_words(node),
        "isObjCExposed": ("@objc" in annotations or "dynamic" in _ts_modifier_words(node)
                          or "@objcMembers" in enclosing_annotations),
        "isExtensionMember": enclosing_kind == "extension" or is_extension_file,
        "isProtocolRequirement": node.type == "protocol_function_declaration",
    }


def _ts_line_range(node, source: bytes) -> Dict[str, Any]:
    """Full line extent of a declaration, for removal.

    startLine includes attributes and directly preceding comments (doc comments).
    ownsLines is False when other code shares the first or last line, e.g.
    `protocol P { func f() }` — removing those lines would remove more than this entity.
    """
    start, end = node.start_byte, node.end_byte
    line_start = source.rfind(b"\n", 0, start) + 1
    line_end = source.find(b"\n", end)
    line_end = len(source) if line_end == -1 else line_end
    before = source[line_start:start].strip()
    after = source[end:line_end].strip()
    owns_lines = not before and (not after or after.startswith(b"//"))

    start_line = node.start_point[0] + 1
    prev = node.prev_sibling
    while (prev is not None and prev.type in ("comment", "multiline_comment")
           and prev.end_point[0] + 1 == start_line - 1
           and not source[source.rfind(b"\n", 0, prev.start_byte) + 1:prev.start_byte].strip()):
        start_line = prev.start_point[0] + 1
        prev = prev.prev_sibling

    return {"startLine": start_line, "endLine": node.end_point[0] + 1, "ownsLines": owns_lines}


def _ts_declaration_kind(node) -> str:
    kind = node.child_by_field_name("declaration_kind")
    return kind.text.decode() if kind is not None else node.type.replace("_declaration", "")


def _ts_modifiers(node):
    return next((c for c in node.named_children if c.type == "modifiers"), None)


def _ts_annotations(node) -> List[str]:
    """Attributes such as @objc, @objc(Name), @MainActor → '@objc', '@MainActor'."""
    modifiers = _ts_modifiers(node)
    if modifiers is None:
        return []
    annotations = []
    for c in modifiers.named_children:
        if c.type == "attribute":
            match = SWIFT_ANNOTATION_PATTERN.match(c.text.decode(errors="replace"))
            if match:
                annotations.append(f"@{match.group(1)}")
    return annotations


def _ts_modifier_words(node) -> Set[str]:
    modifiers = _ts_modifiers(node)
    if modifiers is None:
        return set()
    return {
        c.text.decode(errors="replace").split("(")[0]
        for c in modifiers.named_children if c.type != "attribute"
    }


def _ts_access_level(node) -> str:
    for word in ("open", "public", "internal", "fileprivate", "private"):
        if word in _ts_modifier_words(node):
            return word
    return "internal"


def _extract_swift_entities_regex(file_path: Path, repo_path: Path) -> List[Dict[str, Any]]:
    """Extract entities from a Swift file with regex patterns (legacy fallback)."""
    entities = []
    try:
        content = file_path.read_text(errors="replace")
    except (IOError, OSError):
        return entities

    rel_path = str(file_path.relative_to(repo_path))
    is_test = any(pat in rel_path for pat in TEST_PATH_PATTERNS)
    is_extension_file = "+" in file_path.stem  # e.g. UIView+LayoutAnchors.swift
    lines = content.split("\n")

    # Extract types (class, struct, enum, protocol, actor)
    for match in SWIFT_CLASS_PATTERN.finditer(content):
        entity_type = match.group(1)
        name = match.group(2)
        inheritance = match.group(3)
        line_num = content[:match.start()].count("\n") + 1

        # Parse inheritance
        superclass = None
        protocols = []
        if inheritance:
            parts = [p.strip() for p in inheritance.split(",")]
            for i, part in enumerate(parts):
                # First part could be superclass (for class types)
                if i == 0 and entity_type == "class" and part[0].isupper():
                    superclass = part
                else:
                    protocols.append(part)

        # Detect annotations in the 3 lines above
        annotations = []
        start_line = max(0, line_num - 4)
        context_lines = "\n".join(lines[start_line:line_num])
        for ann_match in SWIFT_ANNOTATION_PATTERN.finditer(context_lines):
            annotations.append(f"@{ann_match.group(1)}")

        # Detect access level
        access = "internal"
        acc_match = ACCESS_PATTERN.match(lines[line_num - 1] if line_num <= len(lines) else "")
        if acc_match:
            access = acc_match.group(1)

        entities.append({
            "name": name,
            "fullyQualifiedName": name,
            "type": entity_type,
            "file": rel_path,
            "line": line_num,
            "language": "swift",
            "accessLevel": access,
            "inheritsFrom": superclass,
            "protocolConformances": protocols,
            "annotations": annotations,
            "isTestCode": is_test,
            "isOverride": False,
            "isObjCExposed": "@objc" in annotations or "@objcMembers" in annotations,
            "isExtensionMember": is_extension_file,
        })

    # Extract functions/methods
    for match in SWIFT_FUNC_PATTERN.finditer(content):
        name = match.group(1)
        line_num = content[:match.start()].count("\n") + 1
        line_text = lines[line_num - 1] if line_num <= len(lines) else ""

        # Detect annotations
        annotations = []
        start_line = max(0, line_num - 3)
        context_lines = "\n".join(lines[start_line:line_num])
        for ann_match in SWIFT_ANNOTATION_PATTERN.finditer(context_lines):
            annotations.append(f"@{ann_match.group(1)}")

        is_override = "override" in line_text

        access = "internal"
        acc_match = ACCESS_PATTERN.match(line_text)
        if acc_match:
            access = acc_match.group(1)

        entities.append({
            "name": name,
            "fullyQualifiedName": name,
            "type": "method",
            "file": rel_path,
            "line": line_num,
            "language": "swift",
            "accessLevel": access,
            "inheritsFrom": None,
            "protocolConformances": [],
            "annotations": annotations,
            "isTestCode": is_test,
            "isOverride": is_override,
            "isObjCExposed": "@objc" in annotations,
            "isExtensionMember": is_extension_file,
        })

    return entities


def _extract_objc_entities(file_path: Path, repo_path: Path) -> List[Dict[str, Any]]:
    """Extract entities from an Objective-C file."""
    entities = []
    try:
        content = file_path.read_text(errors="replace")
    except (IOError, OSError):
        return entities

    rel_path = str(file_path.relative_to(repo_path))
    is_test = any(pat in rel_path for pat in TEST_PATH_PATTERNS)

    # Extract @interface declarations
    for match in OBJC_INTERFACE_PATTERN.finditer(content):
        name = match.group(1)
        superclass = match.group(2)
        protocols_str = match.group(3)
        line_num = content[:match.start()].count("\n") + 1

        protocols = []
        if protocols_str:
            protocols = [p.strip() for p in protocols_str.split(",")]

        entities.append({
            "name": name,
            "fullyQualifiedName": name,
            "type": "class",
            "file": rel_path,
            "line": line_num,
            "language": "objc",
            "accessLevel": "public",
            "inheritsFrom": superclass,
            "protocolConformances": protocols,
            "annotations": [],
            "isTestCode": is_test,
            "isOverride": False,
            "isObjCExposed": True,
        })

    # Extract methods
    for match in OBJC_METHOD_PATTERN.finditer(content):
        name = match.group(1)
        line_num = content[:match.start()].count("\n") + 1

        entities.append({
            "name": name,
            "fullyQualifiedName": name,
            "type": "method",
            "file": rel_path,
            "line": line_num,
            "language": "objc",
            "accessLevel": "public",
            "inheritsFrom": None,
            "protocolConformances": [],
            "annotations": [],
            "isTestCode": is_test,
            "isOverride": False,
            "isObjCExposed": True,
        })

    return entities


SWIFT_TYPE_KINDS = ("class", "struct", "enum", "protocol", "actor")
WORD_PATTERN = re.compile(r"[A-Za-z_]\w*")


def merge_ast_usages(entities: List[Dict], ast_graph: Dict[str, Any],
                     repo_path: Path, objc_files: List[Path]) -> List[Dict[str, Any]]:
    """Build usage counts from tree-sitter references plus word counts for ObjC.

    - Swift types: AST type references (comments, strings, self-references and
      extensions excluded) + mentions in ObjC files.
    - Swift methods: AST call sites by name (declarations, parameters, labels and
      calls from inside the method itself excluded) + mentions in ObjC files,
      including ObjC selector forms like `loadWithItem`. A method that implements
      a protocol requirement declared in this repo counts as used.
    - ObjC entities (tree-sitter): classes/protocols by AST type references from
      Swift and ObjC; methods by selector — message sends, @selector, dot syntax —
      plus Swift call sites under their imported names (`load` for `loadWithItem:`,
      NS_SWIFT_NAME). Methods implementing a repo protocol requirement count as used;
      `init…` methods count Swift constructor calls of their class.
    - ObjC entities (regex fallback): whole-word mentions across Swift and ObjC
      files minus their own declarations.
    """
    swift_types = {
        e["name"] for e in entities
        if e.get("language") == "swift" and e["type"] in SWIFT_TYPE_KINDS
    }
    swift_methods = {
        e["name"] for e in entities
        if e.get("language") == "swift" and e["type"] == "method"
    }
    member_counts = ast_graph.get("member_reference_counts", {})
    requirements = set(ast_graph.get("protocol_requirements", []))
    implemented = {
        e["name"] for e in entities
        if e.get("language") == "swift" and e["type"] == "method"
        and not e.get("isProtocolRequirement")
    }

    swift_files = [f for f in repo_path.rglob("*.swift") if not _is_excluded(f)]
    _flag_external_member_mentions(entities, swift_files + objc_files, repo_path)
    objc_words, objc_with_bases = _count_words(objc_files)
    all_words, all_with_bases = _count_words(swift_files)
    for word, n in objc_words.items():
        all_words[word] = all_words.get(word, 0) + n
    for word, n in objc_with_bases.items():
        all_with_bases[word] = all_with_bases.get(word, 0) + n

    counts: Dict[str, int] = {}
    for name in swift_types:
        counts[name] = objc_words.get(name, 0)
    for ref in ast_graph["references"]:
        target = ref["target_entity"]
        if target in swift_types and ref["reference_type"] != "extension_type":
            counts[target] += 1

    _flag_framework_and_dynamic_swift_methods(entities, ast_graph)

    # Swift methods implementing an ObjC protocol requirement (and vice versa below)
    objc_requirement_names: Set[str] = set()
    for e in entities:
        if e.get("language") == "objc" and e.get("isProtocolRequirement"):
            objc_requirement_names |= swift_base_names(e["name"], e.get("swiftName"))

    for name in swift_methods - swift_types:
        counts[name] = (member_counts.get(name, 0)
                        + objc_words.get(name, 0) + objc_with_bases.get(name, 0)
                        + (1 if name in requirements and name in implemented else 0)
                        + (1 if name in objc_requirement_names else 0))

    if ast_graph["stats"].get("objc_parser") == "tree-sitter":
        counts.update(_objc_ast_usages(entities, ast_graph, member_counts))
        return [{"fullyQualifiedName": n, "usageCount": c} for n, c in counts.items() if c > 0]

    objc_decls: Dict[str, int] = {}
    for e in entities:
        if e.get("language") == "objc":
            objc_decls[e["name"]] = objc_decls.get(e["name"], 0) + 1
    for name, decl_count in objc_decls.items():
        if name in counts:
            continue
        # `- (void)loadWithItem:` is called from Swift as `load(withItem:)`
        base = name.split("With")[0] if "With" in name[1:] else None
        mentions = all_words.get(name, 0) - decl_count + (all_words.get(base, 0) if base else 0)
        counts[name] = max(mentions, 0)

    return [{"fullyQualifiedName": n, "usageCount": c} for n, c in counts.items() if c > 0]


def _flag_external_member_mentions(entities: List[Dict], files: List[Path], repo_path: Path) -> None:
    """Mark Swift types whose members are mentioned in other files.

    Mirrors the executor's pre-removal member scan: such a type would be blocked at
    removal time, so it shouldn't be ranked SAFE. Name-based, so it errs on the side
    of keeping types whose members share common names.
    """
    wanted = {m for e in entities for m in e.get("memberNames", [])}
    if not wanted:
        return
    files_with: Dict[str, Set[str]] = {}
    for f in files:
        try:
            words = set(WORD_PATTERN.findall(f.read_text(errors="replace"))) & wanted
        except (IOError, OSError):
            continue
        rel = str(f.relative_to(repo_path))
        for w in words:
            files_with.setdefault(w, set()).add(rel)
    for e in entities:
        mentioned = [m for m in e.get("memberNames", []) if files_with.get(m, set()) - {e["file"]}]
        if mentioned:
            e["externalMemberCount"] = len(mentioned)
            e["externalMembers"] = mentioned[:5]


def _flag_framework_and_dynamic_swift_methods(entities: List[Dict], ast_graph: Dict[str, Any]) -> None:
    """Mark Swift methods the framework or the runtime calls (scored as KEEP).

    - `override` of a method no repo type declares → overrides an SDK/Pod method
    - non-private method whose name is the Swift name of an SDK/Pods selector →
      likely a framework protocol method (`tableView(_:cellForRowAt:)`)
    - method of a type invoked via NSSelectorFromString(<runtime string>)
    """
    framework_names = set(ast_graph.get("framework_swift_names", []))
    dynamic_classes = set(ast_graph.get("dynamic_dispatch_classes", []))
    repo_method_names = {
        e["name"] for e in entities if e["type"] == "method" and not e.get("isOverride")
    } | {e["name"].split(":")[0] for e in entities
         if e["type"] == "method" and e.get("language") == "objc"}

    for e in entities:
        if e.get("language") != "swift" or e["type"] != "method":
            continue
        if e.get("isOverride") and e["name"] not in repo_method_names:
            e["implementsFrameworkSelector"] = True
            e["frameworkReason"] = f"Overrides a framework method ({e['name']})"
        elif (e.get("accessLevel") not in ("private", "fileprivate")
              and e["name"] in framework_names):
            e["implementsFrameworkSelector"] = True
            e["frameworkReason"] = f"Name matches an SDK/Pods selector ({e['name']})"
        if e.get("owner") in dynamic_classes:
            e["dynamicDispatchClass"] = e["owner"]


def _objc_ast_usages(entities: List[Dict], ast_graph: Dict[str, Any],
                     member_counts: Dict[str, int]) -> Dict[str, int]:
    """Usage counts for tree-sitter ObjC entities, keyed by fullyQualifiedName."""
    objc = [e for e in entities if e.get("language") == "objc"]
    selector_counts = ast_graph.get("objc_selector_counts", {})

    type_refs: Dict[str, int] = {}
    constructor_refs: Dict[str, int] = {}
    for ref in ast_graph["references"]:
        if ref["reference_type"] == "extension_type":
            continue
        type_refs[ref["target_entity"]] = type_refs.get(ref["target_entity"], 0) + 1
        if ref["reference_type"] == "constructor_call":
            constructor_refs[ref["target_entity"]] = constructor_refs.get(ref["target_entity"], 0) + 1

    requirements = {e["name"] for e in objc if e["type"] == "method" and e.get("isProtocolRequirement")}
    swift_requirements = set(ast_graph.get("protocol_requirements", []))
    swift_implemented = {e["name"] for e in entities if e.get("language") == "swift"
                         and e["type"] == "method" and not e.get("isProtocolRequirement")}
    implemented = {e["name"] for e in objc if e["type"] == "method" and not e.get("isProtocolRequirement")}

    counts: Dict[str, int] = {}
    for e in objc:
        if e["type"] != "method":
            counts[e["fullyQualifiedName"]] = type_refs.get(e["name"], 0)
            continue
        selector = e["name"]
        count = selector_counts.get(selector, 0)
        count += sum(member_counts.get(n, 0) for n in swift_base_names(selector, e.get("swiftName")))
        if selector.startswith("init"):
            count += constructor_refs.get(e.get("owner"), 0)
        if selector in requirements and selector in implemented:
            count += 1  # protocol requirement ↔ implementation keep each other
        swift_names = swift_base_names(selector, e.get("swiftName"))
        if e.get("isProtocolRequirement") and swift_names & swift_implemented:
            count += 1  # ObjC protocol requirement implemented in Swift
        if not e.get("isProtocolRequirement") and swift_names & swift_requirements:
            count += 1  # ObjC method implementing a Swift @objc protocol requirement
        counts[e["fullyQualifiedName"]] = count
    return counts


def _count_words(files: List[Path]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Whole-word counts, plus counts of `fooWithBar` tokens keyed by their `foo` base."""
    words: Dict[str, int] = {}
    with_bases: Dict[str, int] = {}
    for file_path in files:
        try:
            content = file_path.read_text(errors="replace")
        except (IOError, OSError):
            continue
        for word in WORD_PATTERN.findall(content):
            words[word] = words.get(word, 0) + 1
            idx = word.find("With", 1)
            if idx > 0 and idx + 4 < len(word) and word[idx + 4].isupper():
                base = word[:idx]
                with_bases[base] = with_bases.get(base, 0) + 1
    return words, with_bases


def _build_usage_graph(entities: List[Dict], entity_names: Set[str],
                       repo_path: Path, source_files: List[Path]) -> List[Dict[str, Any]]:
    """Build usage references by grepping for entity name occurrences."""
    usages = []
    usage_counts: Dict[str, int] = {}

    # Only check types and longer method names to reduce false positives
    names_to_check = {
        e["name"] for e in entities
        if e["type"] in ("class", "struct", "enum", "protocol", "actor")
        or len(e["name"]) > 5
    }

    for file_path in source_files:
        try:
            content = file_path.read_text(errors="replace")
        except (IOError, OSError):
            continue

        rel_path = str(file_path.relative_to(repo_path))

        for name in names_to_check:
            # Skip if entity is defined in this file (self-reference)
            count = content.count(name)
            # Entity's own declaration counts as 1
            entity_in_file = any(
                e["name"] == name and e["file"] == rel_path for e in entities
            )
            effective_count = count - (1 if entity_in_file else 0)

            if effective_count > 0:
                usage_counts[name] = usage_counts.get(name, 0) + effective_count

    # Convert to usage list
    for name, count in usage_counts.items():
        usages.append({
            "fullyQualifiedName": name,
            "usageCount": count,
        })

    return usages


def _identify_ios_entry_points(entities: List[Dict]) -> List[Dict[str, Any]]:
    """Identify iOS entry points from entity metadata."""
    entry_points = []

    for entity in entities:
        annotations = entity.get("annotations", [])
        superclass = entity.get("inheritsFrom", "")
        protocols = entity.get("protocolConformances", [])

        is_entry = False
        reason = ""

        if "@main" in annotations or "@UIApplicationMain" in annotations:
            is_entry = True
            reason = "Application entry point"
        elif superclass in ("UIViewController", "UITableViewController", "UICollectionViewController"):
            is_entry = True
            reason = f"View controller ({superclass})"
        elif "App" in protocols:
            is_entry = True
            reason = "SwiftUI App protocol"
        elif "UIApplicationDelegate" in protocols:
            is_entry = True
            reason = "App delegate"

        if is_entry:
            entry_points.append({
                "name": entity["name"],
                "file": entity["file"],
                "reason": reason,
            })

    return entry_points


def _is_excluded(file_path: Path) -> bool:
    path_str = str(file_path)
    return any(pat in path_str for pat in EXCLUDE_PATTERNS)


def _compute_cache_hash(repo_path: Path) -> str:
    """Compute hash of source files for cache invalidation."""
    hasher = hashlib.sha256()
    for ext in ("*.swift", "*.m", "*.mm"):
        for f in sorted(repo_path.rglob(ext)):
            if not _is_excluded(f):
                try:
                    hasher.update(f.read_bytes())
                except (IOError, OSError):
                    pass
    return f"sha256:{hasher.hexdigest()[:16]}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ios_call_graph_analyzer.py <repo_path> [output.json]")
        sys.exit(1)

    repo_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print(f"🔍 Building iOS call graph: {repo_path}")
    results = build_ios_call_graph(repo_path, verbose=True)

    stats = results["stats"]
    print(f"   Entities: {stats['total_entities']}")
    print(f"   Swift files: {stats['swift_files_scanned']}")
    print(f"   ObjC files: {stats['objc_files_scanned']}")
    print(f"   Usage edges: {stats['usage_edges']}")
    print(f"   Entry points: {stats['entry_points']}")

    results["generatedBy"] = stamp(["ios_call_graph_analyzer.py", "ast_reference_scanner.py",
                                    "objc_syntax.py", "ios_framework_rules.py"])
    if output_file:
        write_json(output_file, results, compact=True)
        print(f"   Output: {output_file}")
