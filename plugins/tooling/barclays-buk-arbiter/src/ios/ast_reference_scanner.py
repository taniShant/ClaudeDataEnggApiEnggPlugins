#!/usr/bin/env python3
"""AST-based reference scanner for Swift/ObjC.

Swift is parsed with tree-sitter (tree-sitter-swift grammar). Objective-C still
uses regex patterns. If the Swift grammar is not installed, the scanner falls
back to the legacy regex scanner and reports parser="regex" in stats.

Key improvements over grep-based counting:
- References come from syntax nodes, so comments and string literals never count
- Declarations are collected across all files before references are resolved,
  so cross-file references are detected
- References are attributed to the enclosing type; self-references are ignored
- Each reference is classified (inheritance, protocol conformance, type annotation,
  generic argument, constructor call, identifier, extension)

Install: pip install tree-sitter tree-sitter-swift
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import tree_sitter_swift
    from tree_sitter import Language, Parser, Query, QueryCursor
    SWIFT_LANGUAGE = Language(tree_sitter_swift.language())
except ImportError:
    SWIFT_LANGUAGE = None

try:
    from .objc_syntax import (OBJC_LANGUAGE, ObjCProject, dependency_dirs, framework_selectors,
                              sdk_path, swift_base_names)
except ImportError:
    from objc_syntax import (OBJC_LANGUAGE, ObjCProject, dependency_dirs, framework_selectors,
                             sdk_path, swift_base_names)

try:
    from .ios_framework_rules import TEST_BASE_CLASSES, is_test_path
except ImportError:
    from ios_framework_rules import TEST_BASE_CLASSES, is_test_path

@dataclass
class Reference:
    """Represents a reference from one entity to another."""
    source_entity: str  # Who references
    source_file: str
    target_entity: str  # What is referenced
    target_file: Optional[str]  # May be unknown
    reference_type: str  # "type_annotation", "inheritance", "protocol_conformance", "method_call", etc.
    line: int
    confidence: float  # 0.0-1.0: how certain is this reference

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SwiftRegexScanner:
    """Legacy regex-based Swift scanner, used only when tree-sitter-swift is unavailable."""

    # Swift semantic reference types we track
    REFERENCE_TYPES = {
        "identifier": 0.8,  # e.g., `let x = MyClass()` or `MyClass()` in function
        "type_annotation": 1.0,  # e.g., `var x: MyClass` or `func f() -> MyClass`
        "inheritance": 1.0,  # e.g., `class Foo: MyClass`
        "protocol_conformance": 1.0,  # e.g., `class Foo: MyProtocol`
        "generic_argument": 0.9,  # e.g., `Array<MyClass>`
        "extension_type": 1.0,  # e.g., `extension MyClass { ... }`
    }

    def __init__(self, swift_files: List[Path]):
        self.swift_files = swift_files
        self.references: List[Reference] = []
        self.entities: Dict[str, Dict[str, Any]] = {}

    def scan(self) -> Tuple[List[Reference], Dict[str, Dict[str, Any]]]:
        """Scan all Swift files and return references + entities."""
        print(f"📍 Scanning {len(self.swift_files)} Swift files for AST references...")

        for file_path in self.swift_files:
            self._scan_file(file_path)

        print(f"   Found {len(self.references)} references")
        print(f"   Found {len(self.entities)} entities")
        return self.references, self.entities

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single Swift file with regex patterns."""
        try:
            content = file_path.read_text()
        except (IOError, OSError):
            return

        entities = self._extract_entities_from_source(content, str(file_path))
        self.entities.update(entities)

        refs = self._extract_references_from_source(content, str(file_path), entities)
        self.references.extend(refs)

    def _extract_entities_from_source(self, content: str, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Extract entity definitions from source code using patterns."""
        entities = {}

        # Swift class/struct/enum/protocol patterns
        import re

        # Classes
        class_pattern = re.compile(
            r'^\s*(?:public|open|internal|fileprivate|private)?\s*'
            r'(?:final\s+)?'
            r'class\s+([A-Za-z_]\w*)'
            r'(?:\s*:\s*([^{]+))?',
            re.MULTILINE
        )
        for match in class_pattern.finditer(content):
            name = match.group(1)
            inheritance = match.group(2)
            entities[name] = {
                "name": name,
                "type": "class",
                "file": file_path,
                "inheritance": [p.strip() for p in inheritance.split(",")] if inheritance else [],
            }

        # Structs
        struct_pattern = re.compile(
            r'^\s*(?:public|open|internal|fileprivate|private)?\s*'
            r'struct\s+([A-Za-z_]\w*)'
            r'(?:\s*:\s*([^{]+))?',
            re.MULTILINE
        )
        for match in struct_pattern.finditer(content):
            name = match.group(1)
            inheritance = match.group(2)
            entities[name] = {
                "name": name,
                "type": "struct",
                "file": file_path,
                "protocols": [p.strip() for p in inheritance.split(",")] if inheritance else [],
            }

        # Protocols
        protocol_pattern = re.compile(
            r'^\s*(?:public|open|internal|fileprivate|private)?\s*'
            r'protocol\s+([A-Za-z_]\w*)',
            re.MULTILINE
        )
        for match in protocol_pattern.finditer(content):
            name = match.group(1)
            entities[name] = {
                "name": name,
                "type": "protocol",
                "file": file_path,
            }

        return entities

    def _extract_references_from_source(
        self, content: str, file_path: str, entities: Dict[str, Dict[str, Any]]
    ) -> List[Reference]:
        """Extract references from source using enhanced pattern matching."""
        references = []
        lines = content.split("\n")
        import re

        entity_names = set(entities.keys())

        # Type annotation patterns
        # var x: SomeClass, func f() -> SomeClass, parameter: SomeClass, etc.
        type_annotation_pattern = re.compile(r':\s*([A-Za-z_]\w*)(?:\s*[=,\)])')
        for line_num, line in enumerate(lines, 1):
            for match in type_annotation_pattern.finditer(line):
                type_name = match.group(1)
                if type_name in entity_names and type_name not in ("self", "Self", "var", "let"):
                    references.append(Reference(
                        source_entity="(line-scope)",
                        source_file=file_path,
                        target_entity=type_name,
                        target_file=None,
                        reference_type="type_annotation",
                        line=line_num,
                        confidence=1.0,
                    ))

        # Inheritance/protocol conformance
        # class Foo: Bar, Baz { }
        inheritance_pattern = re.compile(r'(?:class|struct|enum)\s+(\w+)\s*:\s*([^{]+)\{')
        for line_num, line in enumerate(lines, 1):
            for match in inheritance_pattern.finditer(line):
                source = match.group(1)
                conformances_str = match.group(2)
                for conf in conformances_str.split(","):
                    conf_name = conf.strip().split("<")[0].strip()  # Handle generics
                    if conf_name in entity_names:
                        references.append(Reference(
                            source_entity=source,
                            source_file=file_path,
                            target_entity=conf_name,
                            target_file=None,
                            reference_type="inheritance" if len(conformances_str.split(",")) == 1 else "protocol_conformance",
                            line=line_num,
                            confidence=1.0,
                        ))

        # Extension of type
        # extension SomeClass { }
        extension_pattern = re.compile(r'extension\s+([A-Za-z_]\w*)\s*(?::\s*([^{]+))?\{')
        for line_num, line in enumerate(lines, 1):
            for match in extension_pattern.finditer(line):
                extended_type = match.group(1)
                if extended_type in entity_names:
                    references.append(Reference(
                        source_entity="(extension)",
                        source_file=file_path,
                        target_entity=extended_type,
                        target_file=None,
                        reference_type="extension_type",
                        line=line_num,
                        confidence=1.0,
                    ))

        return references


class SwiftASTScanner:
    """Scans Swift files for references using tree-sitter syntax trees.

    Two passes: declarations are collected from every file first, then each file's
    identifier nodes are resolved against the full set of declared type names.
    """

    REFERENCE_TYPES = {
        "inheritance": 1.0,  # class Foo: MyClass
        "protocol_conformance": 1.0,  # class Foo: MyProtocol
        "type_annotation": 1.0,  # var x: MyClass, func f() -> MyClass
        "generic_argument": 0.9,  # Array<MyClass>, [MyClass]
        "constructor_call": 1.0,  # MyClass()
        "identifier": 0.8,  # MyClass.shared, MyEnum.case
        "extension_type": 0.3,  # extension MyClass { } — not evidence of use on its own
    }

    TYPE_DECLARATIONS = ("class_declaration", "protocol_declaration", "typealias_declaration")
    FUNC_DECLARATIONS = ("function_declaration", "protocol_function_declaration")
    # simple_identifier parents that declare a name rather than reference one
    NON_REFERENCE_PARENTS = ("parameter", "value_argument_label", "pattern") + FUNC_DECLARATIONS

    def __init__(self, swift_files: List[Path], repo_path: Path):
        if SWIFT_LANGUAGE is None:
            raise ImportError("tree-sitter-swift not installed")
        self.swift_files = swift_files
        self.repo_path = repo_path
        self.parser = Parser(SWIFT_LANGUAGE)
        self.decl_query = Query(SWIFT_LANGUAGE, """
            (class_declaration) @decl
            (protocol_declaration) @decl
            (typealias_declaration) @decl
            (function_declaration) @func
            (protocol_function_declaration) @func
        """)
        self.ref_query = Query(SWIFT_LANGUAGE, "(type_identifier) @ref (simple_identifier) @ref")
        self.trees: List[Tuple[str, Any]] = []
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.references: List[Reference] = []
        self.files_with_parse_errors: List[str] = []
        # Method name → [(file, start_byte, end_byte, argument labels)] for each declaration
        self.method_decls: Dict[str, List[Tuple[str, int, int, Tuple[str, ...]]]] = defaultdict(list)
        self.protocol_requirements: Set[str] = set()
        self.member_reference_counts: Dict[str, int] = defaultdict(int)

    def parse(self) -> None:
        for file_path in self.swift_files:
            try:
                source = file_path.read_bytes()
            except (IOError, OSError):
                continue
            rel_path = str(file_path.relative_to(self.repo_path))
            tree = self.parser.parse(source)
            if tree.root_node.has_error:
                self.files_with_parse_errors.append(rel_path)
            self.trees.append((rel_path, tree))

    def collect_entities(self) -> Dict[str, Dict[str, Any]]:
        """Pass 1: collect type declarations (extensions are not entities) and method names."""
        for rel_path, tree in self.trees:
            for node in self._captures(self.decl_query, tree.root_node, "func"):
                name_node = node.child_by_field_name("name")
                if name_node is None or name_node.type != "simple_identifier":
                    continue  # operators
                name = name_node.text.decode(errors="replace")
                self.method_decls[name].append(
                    (rel_path, node.start_byte, node.end_byte, self._declared_labels(node)))
                if node.type == "protocol_function_declaration":
                    self.protocol_requirements.add(name)
            for node in self._captures(self.decl_query, tree.root_node, "decl"):
                kind = self._declaration_kind(node)
                if kind == "extension":
                    continue
                name_node = node.child_by_field_name("name")
                if name_node is None:
                    continue
                name = name_node.text.decode(errors="replace")
                self.entities[name] = {
                    "name": name,
                    "type": kind,
                    "file": rel_path,
                    "line": node.start_point[0] + 1,
                    "inheritance": [
                        c.text.decode(errors="replace")
                        for c in node.named_children if c.type == "inheritance_specifier"
                    ],
                }
        return self.entities

    def collect_references(self, known_names: Set[str], known_kinds: Dict[str, str],
                           extra_member_names: Set[str] = frozenset()) -> List[Reference]:
        """Pass 2: resolve identifier nodes against all known type and method names.

        Type references are recorded individually; method references are only
        counted (by name — overloads and same-named methods share a count, which
        errs on the side of keeping code). extra_member_names are counted too —
        the Swift names of Objective-C selectors (`load` for `loadWithItem:`).
        """
        for rel_path, tree in self.trees:
            for node in self._captures(self.ref_query, tree.root_node, "ref"):
                target = node.text.decode(errors="replace")
                if node.type == "simple_identifier" and (
                        target in self.method_decls or target in extra_member_names):
                    if self._is_method_reference(node, target, rel_path):
                        self.member_reference_counts[target] += 1
                if target not in known_names:
                    continue
                ref = self._classify(node, target, rel_path, known_kinds)
                if ref:
                    self.references.append(ref)
        return self.references

    def runtime_selector_classes(self, type_names: Set[str]) -> Set[str]:
        """Types named in a function that builds selectors from runtime strings.

        `NSSelectorFromString(name)` / `Selector(name)` / `NSClassFromString(name)`
        with a non-literal argument means any method of those types may be called.
        """
        found: Set[str] = set()
        query = Query(SWIFT_LANGUAGE, "(call_expression) @call")
        for _, tree in self.trees:
            for call in self._captures(query, tree.root_node, "call"):
                func = call.named_children[0] if call.named_children else None
                if func is None or func.text not in (b"NSSelectorFromString", b"Selector",
                                                     b"NSClassFromString"):
                    continue
                args = [n for n in self._walk(call) if n.type == "value_argument"]
                if not args or any(n.type in ("line_string_literal", "multi_line_string_literal")
                                   for n in args[0].named_children):
                    continue
                body = call
                while body.parent is not None and body.type not in self.FUNC_DECLARATIONS:
                    body = body.parent
                found |= {
                    n.text.decode(errors="replace") for n in self._walk(body)
                    if n.type in ("type_identifier", "simple_identifier")
                    and n.text.decode(errors="replace") in type_names
                }
        return found

    @staticmethod
    def _walk(node):
        stack = [node]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(n.children)

    def _is_method_reference(self, node, name: str, rel_path: str) -> bool:
        if node.parent.type in self.NON_REFERENCE_PARENTS:
            return False
        enclosing = [labels for f, start, end, labels in self.method_decls.get(name, [])
                     if f == rel_path and start <= node.start_byte < end]
        if not enclosing:
            return True
        # Inside a same-named method: only real recursion — same method called on
        # self with the same argument labels — doesn't count. A call on another
        # object (`stackView.removeButton(forId:)`) or to an overload
        # (`setup(point:)` from `setup(tabbar:)`) does.
        call = self._call_for(node)
        if call is None:
            return True
        return self._call_labels(call) not in enclosing

    @staticmethod
    def _call_for(node):
        """The call_expression `node` names, if it is called unqualified or on `self`."""
        parent = node.parent
        if parent.type == "call_expression":
            return parent
        if parent.type == "navigation_suffix":
            nav = parent.parent
            receiver = nav.named_children[0] if nav.named_children else None
            if receiver is None or receiver.text not in (b"self", b"Self"):
                return None
            return nav.parent if nav.parent is not None and nav.parent.type == "call_expression" else None
        return None

    @staticmethod
    def _call_labels(call) -> Optional[Tuple[str, ...]]:
        suffix = next((c for c in call.named_children if c.type == "call_suffix"), None)
        if suffix is None:
            return ()
        if any(c.type == "lambda_literal" for c in suffix.named_children):
            return None  # trailing closure: labels can't be compared reliably → count it
        args = next((c for c in suffix.named_children if c.type == "value_arguments"), None)
        labels = []
        for arg in (args.named_children if args is not None else []):
            if arg.type != "value_argument":
                continue
            label = next((c for c in arg.named_children if c.type == "value_argument_label"), None)
            labels.append(label.text.decode(errors="replace") if label is not None else "_")
        return tuple(labels)

    @staticmethod
    def _declared_labels(func) -> Tuple[str, ...]:
        """External argument labels of a declaration: `f(_ a: Int, at b: Int)` → ('_', 'at')."""
        labels = []
        for param in func.named_children:
            if param.type != "parameter":
                continue
            ident = next((c for c in param.named_children if c.type == "simple_identifier"), None)
            labels.append(ident.text.decode(errors="replace") if ident is not None else "_")
        return tuple(labels)

    def _classify(self, node, target: str, rel_path: str,
                  known_kinds: Dict[str, str]) -> Optional[Reference]:
        parent = node.parent
        # Declaration name itself, e.g. the `Foo` in `class Foo`
        if parent.type in self.TYPE_DECLARATIONS and parent.child_by_field_name("name") == node:
            return None

        ref_type = None
        enclosing = None
        cur = node
        while cur.parent is not None:
            p = cur.parent
            if p.type == "import_declaration":
                return None
            if p.type in self.TYPE_DECLARATIONS:
                if (ref_type is None and self._declaration_kind(p) == "extension"
                        and p.child_by_field_name("name") == cur):
                    return self._reference("(extension)", rel_path, target, "extension_type", node)
                enclosing = p
                break
            if ref_type is None:
                if p.type == "inheritance_specifier":
                    ref_type = ("protocol_conformance" if known_kinds.get(target) == "protocol"
                                else "inheritance")
                elif p.type in ("type_arguments", "array_type", "dictionary_type"):
                    ref_type = "generic_argument"
            cur = p

        if ref_type is None:
            if node.type == "type_identifier":
                ref_type = "type_annotation"
            elif parent.type == "call_expression" and parent.named_children[0] == node:
                ref_type = "constructor_call"
            else:
                ref_type = "identifier"

        source = self._enclosing_name(enclosing) if enclosing is not None else "(file-scope)"
        if source == target:
            return None  # self-reference doesn't keep a type alive
        return self._reference(source, rel_path, target, ref_type, node)

    def _reference(self, source: str, rel_path: str, target: str,
                   ref_type: str, node) -> Reference:
        return Reference(
            source_entity=source,
            source_file=rel_path,
            target_entity=target,
            target_file=self.entities.get(target, {}).get("file"),
            reference_type=ref_type,
            line=node.start_point[0] + 1,
            confidence=self.REFERENCE_TYPES[ref_type],
        )

    @staticmethod
    def _declaration_kind(node) -> str:
        if node.type == "typealias_declaration":
            return "typealias"
        kind = node.child_by_field_name("declaration_kind")
        return kind.text.decode() if kind is not None else node.type.replace("_declaration", "")

    @staticmethod
    def _enclosing_name(decl) -> str:
        name_node = decl.child_by_field_name("name")
        if name_node is None:
            return "(file-scope)"
        # Extension names are a user_type (possibly generic); keep the base type name
        if name_node.type == "user_type":
            ident = next((c for c in name_node.named_children if c.type == "type_identifier"), name_node)
            return ident.text.decode(errors="replace")
        return name_node.text.decode(errors="replace")

    @staticmethod
    def _captures(query, root, name: str) -> list:
        return QueryCursor(query).captures(root).get(name, [])


class ObjCASTScanner:
    """Scans Objective-C files for references."""

    def __init__(self, objc_files: List[Path]):
        self.objc_files = objc_files
        self.references: List[Reference] = []
        self.entities: Dict[str, Dict[str, Any]] = {}

    def scan(self) -> Tuple[List[Reference], Dict[str, Dict[str, Any]]]:
        """Scan all ObjC files and return references + entities."""
        print(f"📍 Scanning {len(self.objc_files)} Objective-C files for AST references...")

        for file_path in self.objc_files:
            self._scan_file(file_path)

        print(f"   Found {len(self.references)} references")
        print(f"   Found {len(self.entities)} entities")
        return self.references, self.entities

    def _scan_file(self, file_path: Path) -> None:
        """Parse a single Objective-C file."""
        try:
            content = file_path.read_text()
        except (IOError, OSError):
            return

        entities = self._extract_entities_from_source(content, str(file_path))
        self.entities.update(entities)

        refs = self._extract_references_from_source(content, str(file_path), entities)
        self.references.extend(refs)

    def _extract_entities_from_source(self, content: str, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Extract entity definitions from ObjC source."""
        entities = {}
        import re

        # @interface ClassName : SuperClass <Protocol1, Protocol2>
        interface_pattern = re.compile(
            r'@interface\s+(\w+)\s*(?::\s*(\w+))?(?:\s*<([^>]+)>)?'
        )
        for match in interface_pattern.finditer(content):
            name = match.group(1)
            superclass = match.group(2)
            protocols_str = match.group(3)
            entities[name] = {
                "name": name,
                "type": "interface",
                "file": file_path,
                "superclass": superclass,
                "protocols": [p.strip() for p in protocols_str.split(",")] if protocols_str else [],
            }

        return entities

    def _extract_references_from_source(
        self, content: str, file_path: str, entities: Dict[str, Dict[str, Any]]
    ) -> List[Reference]:
        """Extract references from ObjC source."""
        references = []
        lines = content.split("\n")
        import re

        entity_names = set(entities.keys())

        # @interface ClassName : SuperClass <- superclass reference
        interface_pattern = re.compile(r'@interface\s+(\w+)\s*:\s*(\w+)')
        for line_num, line in enumerate(lines, 1):
            for match in interface_pattern.finditer(line):
                superclass = match.group(2)
                if superclass in entity_names:
                    references.append(Reference(
                        source_entity=match.group(1),
                        source_file=file_path,
                        target_entity=superclass,
                        target_file=None,
                        reference_type="inheritance",
                        line=line_num,
                        confidence=1.0,
                    ))

        # @interface ClassName <Protocol1, Protocol2>
        protocol_pattern = re.compile(r'@interface\s+(\w+)\s*<([^>]+)>')
        for line_num, line in enumerate(lines, 1):
            for match in protocol_pattern.finditer(line):
                protocols_str = match.group(2)
                for proto in protocols_str.split(","):
                    proto_name = proto.strip()
                    if proto_name in entity_names:
                        references.append(Reference(
                            source_entity=match.group(1),
                            source_file=file_path,
                            target_entity=proto_name,
                            target_file=None,
                            reference_type="protocol_conformance",
                            line=line_num,
                            confidence=1.0,
                        ))

        return references


def swiftinterface_requirements(repo_path: Path, cache_dir: Optional[Path] = None) -> Set[str]:
    """Method names required by Swift protocols in SDK, Pods and vendored frameworks.

    Pure-Swift SDKs (e.g. BioCatch's `BCStateChangedEventListener.onStateChanged`)
    have no ObjC headers, so their protocols only appear in `.swiftinterface` files.
    One interface per module is parsed (architecture variants are duplicates).
    The SDK part is cached per SDK version.
    """
    if SWIFT_LANGUAGE is None:
        return set()
    query = Query(SWIFT_LANGUAGE, "(protocol_function_declaration) @req")

    def names_in(files: Iterable[Path]) -> Set[str]:
        per_module: Dict[Path, Path] = {}
        for f in files:
            current = per_module.get(f.parent)
            if current is None or (".private." in current.name and ".private." not in f.name):
                per_module[f.parent] = f
        names: Set[str] = set()
        parser = Parser(SWIFT_LANGUAGE)
        for f in per_module.values():
            try:
                tree = parser.parse(f.read_bytes())
            except (IOError, OSError):
                continue
            for node in QueryCursor(query).captures(tree.root_node).get("req", []):
                name = node.child_by_field_name("name")
                if name is not None and name.type == "simple_identifier":
                    names.add(name.text.decode(errors="replace"))
        return names

    requirements: Set[str] = set()
    sdk = sdk_path()
    if sdk:
        cache_dir = cache_dir or Path.home() / ".cache" / "arbiter"
        cache = cache_dir / f"sdk_swift_requirements_{Path(sdk).name}.json"
        if cache.exists():
            requirements |= set(json.loads(cache.read_text()))
        else:
            sdk_names = names_in(Path(sdk).glob("System/Library/Frameworks/*.framework/Modules/"
                                                "*.swiftmodule/*.swiftinterface"))
            sdk_names |= names_in(Path(sdk).glob("usr/lib/swift/*.swiftmodule/*.swiftinterface"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(sorted(sdk_names)))
            requirements |= sdk_names

    for deps in dependency_dirs(repo_path):
        requirements |= names_in(deps.rglob("*.swiftinterface"))
    vendored = [f for f in repo_path.rglob("*.swiftinterface")
                if (".framework/" in str(f) or ".xcframework/" in str(f))
                and "/Pods/" not in str(f) and "/.git/" not in str(f)]
    requirements |= names_in(vendored)
    return requirements


def build_ios_ast_graph(repo_path: str) -> Dict[str, Any]:
    """Build comprehensive AST-based reference graph for iOS project."""
    repo_path = Path(repo_path).resolve()

    swift_files = [f for f in repo_path.rglob("*.swift") if not _is_excluded(f)]
    objc_files = [f for f in repo_path.rglob("*.m") if not _is_excluded(f)]
    objc_files += [f for f in repo_path.rglob("*.mm") if not _is_excluded(f)]

    parser = "tree-sitter" if SWIFT_LANGUAGE is not None else "regex"
    print(f"\n🔍 Building AST-based reference graph (Swift parser: {parser})")
    print(f"   Swift files: {len(swift_files)}")
    print(f"   ObjC files: {len(objc_files)}")

    header_files = [f for f in repo_path.rglob("*.h") if not _is_excluded(f)]

    # Scan ObjC first so Swift references to ObjC types resolve
    objc_entity_list: List[Dict[str, Any]] = []
    objc_selector_counts: Dict[str, int] = {}
    objc_parse_errors: List[str] = []
    objc_parser = "tree-sitter" if OBJC_LANGUAGE is not None else "regex"
    if OBJC_LANGUAGE is not None:
        print(f"📍 Parsing {len(objc_files) + len(header_files)} Objective-C files with tree-sitter...")
        objc_project = ObjCProject(objc_files + header_files, repo_path,
                                   is_test_path, TEST_BASE_CLASSES)
        objc_entity_list = objc_project.entities()
        objc_parse_errors = objc_project.files_with_parse_errors
        objc_entities = {e["name"]: e for e in objc_entity_list if e["type"] in ("class", "protocol")}
        objc_refs = []
        print(f"   Found {len(objc_entity_list)} entities")
    else:
        objc_scanner = ObjCASTScanner(objc_files)
        objc_refs, objc_entities = objc_scanner.scan()

    # Selectors the SDK, Pods and vendored frameworks declare — overrides and protocol
    # methods with these are called by the framework, not by repo code
    fw_selectors = framework_selectors(repo_path)
    for e in objc_entity_list:
        if e["type"] == "method" and e["name"] in fw_selectors:
            e["implementsFrameworkSelector"] = True
            e["frameworkReason"] = f"Framework selector (SDK/Pods declare {e['name']})"
    framework_swift_names: Set[str] = set()
    for sel in fw_selectors:
        framework_swift_names |= swift_base_names(sel)
    framework_swift_names |= swiftinterface_requirements(repo_path)

    # Swift names that may call ObjC selectors: loadWithItem: → load, loadWithItem
    objc_swift_names: Set[str] = set()
    for e in objc_entity_list:
        if e["type"] == "method":
            objc_swift_names |= swift_base_names(e["name"], e.get("swiftName"))

    parse_errors: List[str] = []
    member_reference_counts: Dict[str, int] = {}
    protocol_requirements: List[str] = []
    if SWIFT_LANGUAGE is not None:
        print(f"📍 Parsing {len(swift_files)} Swift files with tree-sitter...")
        swift_scanner = SwiftASTScanner(swift_files, repo_path)
        swift_scanner.parse()
        swift_entities = swift_scanner.collect_entities()
        all_entities = {**swift_entities, **objc_entities}
        known_kinds = {name: e["type"] for name, e in all_entities.items()}
        swift_refs = swift_scanner.collect_references(set(all_entities), known_kinds,
                                                      objc_swift_names)
        parse_errors = swift_scanner.files_with_parse_errors
        member_reference_counts = dict(swift_scanner.member_reference_counts)
        protocol_requirements = sorted(swift_scanner.protocol_requirements)
        print(f"   Found {len(swift_refs)} references")
        print(f"   Found {len(swift_entities)} entities")
        if parse_errors:
            print(f"   ⚠ {len(parse_errors)} files had syntax errors (partial trees used)")
    else:
        print("   ⚠ tree-sitter-swift not installed — falling back to regex "
              "(pip install tree-sitter tree-sitter-swift)")
        swift_refs, swift_entities = SwiftRegexScanner(swift_files).scan()
        all_entities = {**swift_entities, **objc_entities}

    dynamic_classes: Set[str] = set()
    if OBJC_LANGUAGE is not None:
        type_refs, objc_selector_counts, dynamic_classes = objc_project.references(set(all_entities))
        objc_refs = [Reference(**r) for r in type_refs]
    if SWIFT_LANGUAGE is not None:
        dynamic_classes |= swift_scanner.runtime_selector_classes(set(all_entities))
    for e in objc_entity_list:
        if e["type"] == "method" and e.get("owner") in dynamic_classes:
            e["dynamicDispatchClass"] = e["owner"]

    all_references = swift_refs + objc_refs

    # Build reference index
    reference_index = defaultdict(list)
    for ref in all_references:
        reference_index[ref.target_entity].append(ref.to_dict())

    return {
        "entities": all_entities,
        "references": [r.to_dict() for r in all_references],
        "reference_index": dict(reference_index),
        "member_reference_counts": member_reference_counts,
        "protocol_requirements": protocol_requirements,
        "objc_entities": objc_entity_list,
        "framework_swift_names": sorted(framework_swift_names),
        "dynamic_dispatch_classes": sorted(dynamic_classes),
        "objc_selector_counts": objc_selector_counts,
        "stats": {
            "parser": parser,
            "total_entities": len(all_entities),
            "total_references": len(all_references),
            "swift_files": len(swift_files),
            "objc_files": len(objc_files),
            "swift_entities": len(swift_entities),
            "objc_entities": len(objc_entities),
            "swift_files_with_parse_errors": parse_errors,
            "objc_parser": objc_parser,
            "objc_header_files": len(header_files),
            "objc_files_with_parse_errors": objc_parse_errors,
        },
    }


EXCLUDE_PATTERNS = [
    "Pods/", "Carthage/", ".build/", "DerivedData/",
    "node_modules/", ".arbiter/", ".git/",
    ".framework/", ".xcframework/",  # vendored binary SDKs: headers only, not repo code
]

def _is_excluded(file_path: Path) -> bool:
    path_str = str(file_path)
    return any(pat in path_str for pat in EXCLUDE_PATTERNS)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ast_reference_scanner.py <repo_path> [output.json]")
        sys.exit(1)

    repo_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    result = build_ios_ast_graph(repo_path)

    print(f"\n📊 AST Analysis Results:")
    print(f"   Entities: {result['stats']['total_entities']}")
    print(f"   References: {result['stats']['total_references']}")

    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"   Output: {output_file}")
