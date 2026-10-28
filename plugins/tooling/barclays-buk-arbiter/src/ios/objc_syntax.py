#!/usr/bin/env python3
"""Objective-C syntax analysis with tree-sitter (tree-sitter-objc grammar).

Provides, for .h/.m/.mm files:
- declarations: classes (interface, class extension, implementation — merged across
  files), protocols, and methods with full selectors (`countFor:inSection:`) and
  line ranges
- references: message sends, @selector(...), dot-syntax property access, and
  class/protocol mentions (excluding @class/@protocol forward declarations,
  #imports and a class's references to itself)
- a framework selector index built from SDK and Pods headers, so methods the
  framework calls (`viewDidLoad`, `tableView:cellForRowAtIndexPath:`) are not
  mistaken for dead code

Common Foundation macros (NS_ASSUME_NONNULL_BEGIN, NS_SWIFT_NAME(...), ...) are
blanked with same-length whitespace before parsing, so byte offsets and line
numbers stay exact.

Install: pip install tree-sitter tree-sitter-objc
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

try:
    import tree_sitter_objc
    from tree_sitter import Language, Parser
    OBJC_LANGUAGE = Language(tree_sitter_objc.language())
except ImportError:
    OBJC_LANGUAGE = None

# Macros that confuse the grammar; replaced by whitespace of the same length
_MACRO_PATTERN = re.compile(
    rb"\b(?:NS_ASSUME_NONNULL_BEGIN|NS_ASSUME_NONNULL_END|NS_DESIGNATED_INITIALIZER"
    rb"|NS_REQUIRES_SUPER|NS_UNAVAILABLE|NS_REFINED_FOR_SWIFT|NS_SWIFT_UI_ACTOR"
    rb"|NS_REQUIRES_NIL_TERMINATION|NS_RETURNS_RETAINED|NS_RETURNS_NOT_RETAINED"
    rb"|NS_FORMAT_ARGUMENT\s*\(\s*\d+\s*\)|IB_DESIGNABLE|IBInspectable|UI_APPEARANCE_SELECTOR"
    rb"|(?:NS_SWIFT_NAME|NS_SWIFT_UNAVAILABLE|API_AVAILABLE|API_UNAVAILABLE|API_DEPRECATED"
    rb"|API_DEPRECATED_WITH_REPLACEMENT|NS_AVAILABLE_IOS|NS_AVAILABLE|NS_DEPRECATED_IOS"
    rb"|NS_DEPRECATED|NS_EXTENSION_UNAVAILABLE_IOS|NS_FORMAT_FUNCTION|__attribute__"
    rb"|DEPRECATED_MSG_ATTRIBUTE|NS_SWIFT_ASYNC_NAME|NS_SWIFT_ASYNC)\s*"
    rb"\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)|DEPRECATED_ATTRIBUTE)"
    # Project/framework-prefixed attribute macros: BWK_EXTERN, UIKIT_EXTERN, FOUNDATION_EXPORT,
    # NS_EXTENSIBLE_STRING_ENUM, BWK_ONLY_AVAILABLE_IN_TEST, ...
    rb"|\b[A-Z][A-Z0-9]*_(?:EXTERN|EXPORT|INLINE|NOESCAPE|STRING_ENUM|EXTENSIBLE_STRING_ENUM"
    rb"|TYPED_ENUM|TYPED_EXTENSIBLE_ENUM|ONLY_AVAILABLE_IN_TEST|UNAVAILABLE_IN_\w+)\b"
)
# typedef NS_ENUM(NSInteger, Name) → enum Name (padded)
_ENUM_PATTERN = re.compile(
    rb"(?:\btypedef\s+)?\b(?:NS_ENUM|NS_OPTIONS|NS_CLOSED_ENUM|NS_ERROR_ENUM|NS_TYPED_ENUM)\s*\(\s*[\w ]+?\s*,\s*(\w+)\s*\)")
_SWIFT_NAME_PATTERN = re.compile(rb"NS_SWIFT_NAME\s*\(\s*(?:\w+\.)?(\w+)")

TYPE_DECLARATIONS = ("class_interface", "class_implementation", "protocol_declaration")
METHOD_NODES = ("method_declaration", "method_definition")
SWIFT_PREPOSITIONS = re.compile(r"(?<=[a-z0-9])(?:With|For|From|To|In|At|By|Using|Of|On|Into|As|And)(?=[A-Z])")


def _blank(match: "re.Match[bytes]") -> bytes:
    return re.sub(rb"[^\n]", b" ", match.group(0))


def prepare_source(source: bytes) -> bytes:
    """Blank macros the grammar can't parse, keeping byte offsets identical."""
    source = _MACRO_PATTERN.sub(_blank, source)

    def enum(match):
        text = b"enum " + match.group(1)
        return text + b" " * (len(match.group(0)) - len(text))

    return _ENUM_PATTERN.sub(enum, source)


def parse(source: bytes):
    return Parser(OBJC_LANGUAGE).parse(prepare_source(source))


def walk(node) -> Iterable[Any]:
    cursor = node.walk()
    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if cursor.goto_first_child():
                continue
        if cursor.goto_next_sibling():
            visited_children = False
        elif cursor.goto_parent():
            visited_children = True
        else:
            return


def _text(node) -> str:
    return node.text.decode(errors="replace") if node is not None else ""


def method_selector(node) -> str:
    """Selector of a method_declaration/method_definition, e.g. 'countFor:inSection:'."""
    keywords = [_text(c) for c in node.named_children if c.type == "identifier"]
    has_params = any(c.type == "method_parameter" for c in node.named_children)
    if not keywords:
        return ""
    return "".join(f"{k}:" for k in keywords) if has_params else keywords[0]


def message_selector(node) -> str:
    """Selector of a message_expression, e.g. [obj countFor:@"a" inSection:1]."""
    keywords = [_text(c) for i, c in enumerate(node.children)
                if node.field_name_for_child(i) == "method"]
    has_colon = any(c.type == ":" for c in node.children)
    if not keywords:
        return ""
    return "".join(f"{k}:" for k in keywords) if has_colon else keywords[0]


def swift_base_names(selector: str, swift_name: Optional[str] = None) -> Set[str]:
    """Names Swift code may use to call an ObjC selector (over-approximate on purpose).

    loadWithItem:completion: → {loadWithItem, load}; setThing: → {thing, setThing};
    countFor:inSection: + NS_SWIFT_NAME(count(for:section:)) → {countFor, count}
    """
    first = selector.split(":")[0]
    names = {first}
    split = SWIFT_PREPOSITIONS.split(first, maxsplit=1)[0]
    if split:
        names.add(split)
    if first.startswith("set") and len(first) > 3 and first[3].isupper() and selector.count(":") == 1:
        names.add(first[3].lower() + first[4:])  # property setter
    if swift_name:
        names.add(swift_name)
    return {n for n in names if n and n != "init"}


def _line_range(node, source: bytes) -> Dict[str, Any]:
    """Line extent of a declaration; same contract as the Swift extractor."""
    start, end = node.start_byte, node.end_byte
    line_start = source.rfind(b"\n", 0, start) + 1
    line_end = source.find(b"\n", end)
    line_end = len(source) if line_end == -1 else line_end
    before = source[line_start:start].strip()
    after = source[end:line_end].strip()
    owns_lines = not before and (not after or after.startswith(b"//"))

    start_line = node.start_point[0] + 1
    prev = node.prev_sibling
    while (prev is not None and prev.type == "comment"
           and prev.end_point[0] + 1 == start_line - 1
           and not source[source.rfind(b"\n", 0, prev.start_byte) + 1:prev.start_byte].strip()):
        start_line = prev.start_point[0] + 1
        prev = prev.prev_sibling
    return {"startLine": start_line, "endLine": node.end_point[0] + 1, "ownsLines": owns_lines}


def _owner(node) -> Optional[Any]:
    cur = node.parent
    while cur is not None and cur.type not in TYPE_DECLARATIONS:
        cur = cur.parent
    return cur


def _owner_name(decl) -> str:
    return _text(next((c for c in decl.named_children if c.type == "identifier"), None))


class ObjCProject:
    """Parses all ObjC files once; collects declarations and references."""

    def __init__(self, files: List[Path], repo_path: Path,
                 is_test_path: Callable[[str], bool] = lambda rel: False,
                 test_base_classes: Iterable[str] = ("XCTestCase",)):
        self.repo_path = repo_path
        self.is_test_path = is_test_path
        self.test_base_classes = set(test_base_classes)
        self.trees: List[Tuple[str, bytes, Any]] = []
        self.files_with_parse_errors: List[str] = []
        for f in files:
            try:
                source = f.read_bytes()
            except (IOError, OSError):
                continue
            rel = str(f.relative_to(repo_path))
            tree = parse(source)
            if tree.root_node.has_error:
                self.files_with_parse_errors.append(rel)
            self.trees.append((rel, source, tree))

        self.classes: Dict[str, Dict[str, Any]] = {}
        self.protocols: Dict[str, Dict[str, Any]] = {}
        self.methods: Dict[str, Dict[str, Any]] = {}  # fqn → entity
        self._collect_declarations()

    # ------------------------------------------------------------------ declarations

    def _is_test(self, rel: str) -> bool:
        return self.is_test_path(rel)

    def _collect_declarations(self) -> None:
        for rel, source, tree in self.trees:
            is_header = rel.endswith(".h")
            for node in walk(tree.root_node):
                if node.type in ("class_interface", "class_implementation"):
                    self._add_class_part(node, rel, source, is_header)
                elif node.type == "protocol_declaration":
                    self._add_protocol(node, rel, source)
                elif node.type in METHOD_NODES:
                    self._add_method(node, rel, source, is_header)

    def _add_class_part(self, node, rel: str, source: bytes, is_header: bool) -> None:
        name = _owner_name(node)
        if not name:
            return
        category = node.child_by_field_name("category")
        superclass = node.child_by_field_name("superclass")
        protocols = [_text(t) for t in walk(node)
                     if t.type == "type_identifier" and t.parent.type == "type_name"
                     and t.parent.parent is not None and t.parent.parent.type == "parameterized_arguments"
                     and t.parent.parent.parent == node]
        protocols += [_text(c) for r in node.named_children if r.type == "protocol_reference_list"
                      for c in r.named_children if c.type == "identifier"]
        kind = ("category" if category is not None and _text(category)
                else "extension" if node.type == "class_interface" and b"(" in node.text.split(b"\n")[0]
                else "interface" if node.type == "class_interface" else "implementation")

        entity = self.classes.setdefault(name, {
            "name": name, "fullyQualifiedName": name, "type": "class", "language": "objc",
            "file": rel, "line": node.start_point[0] + 1, "declarations": [],
            "inheritsFrom": None, "protocolConformances": [], "annotations": [],
            "accessLevel": "private", "isTestCode": self._is_test(rel), "isOverride": False,
            "isObjCExposed": False, "isExtensionMember": False, "isOwnClass": False,
        })
        entity["declarations"].append({"file": rel, "kind": kind, **_line_range(node, source)})
        if kind in ("interface", "implementation"):
            entity["isOwnClass"] = True  # categories alone extend someone else's class
        if kind == "implementation":
            entity["file"], entity["line"] = rel, node.start_point[0] + 1
        if superclass is not None:
            entity["inheritsFrom"] = _text(superclass)
        for p in protocols:
            if p not in entity["protocolConformances"]:
                entity["protocolConformances"].append(p)
        if is_header and kind in ("interface", "category"):
            entity["accessLevel"] = "public"

    def _add_protocol(self, node, rel: str, source: bytes) -> None:
        name = _owner_name(node)
        if not name:
            return
        entity = self.protocols.setdefault(name, {
            "name": name, "fullyQualifiedName": name, "type": "protocol", "language": "objc",
            "file": rel, "line": node.start_point[0] + 1, "declarations": [],
            "inheritsFrom": None, "protocolConformances": [], "annotations": [],
            "accessLevel": "public" if rel.endswith(".h") else "private",
            "isTestCode": self._is_test(rel), "isOverride": False,
            "isObjCExposed": False, "isExtensionMember": False,
        })
        entity["declarations"].append({"file": rel, "kind": "protocol", **_line_range(node, source)})

    def _add_method(self, node, rel: str, source: bytes, is_header: bool) -> None:
        owner = _owner(node)
        selector = method_selector(node)
        if owner is None or not selector:
            return
        owner_name = _owner_name(owner)
        is_class_method = node.text.lstrip().startswith(b"+")
        fqn = f"{'+' if is_class_method else '-'}[{owner_name} {selector}]"
        method_type = next((c for c in node.named_children if c.type == "method_type"), None)
        swift_name = _SWIFT_NAME_PATTERN.search(source[node.start_byte:node.end_byte + 200].split(b";")[0])
        category = owner.child_by_field_name("category")

        entity = self.methods.setdefault(fqn, {
            "name": selector, "fullyQualifiedName": fqn, "type": "method", "language": "objc",
            "file": rel, "line": node.start_point[0] + 1, "declarations": [],
            "owner": owner_name, "category": _text(category) or None,
            "isClassMethod": is_class_method,
            "inheritsFrom": None, "protocolConformances": [], "annotations": [],
            "accessLevel": "private", "isTestCode": self._is_test(rel), "isOverride": False,
            "isObjCExposed": False, "isExtensionMember": category is not None,
            "isProtocolRequirement": owner.type == "protocol_declaration",
            "swiftName": None,
        })
        entity["declarations"].append({
            "file": rel, "kind": "definition" if node.type == "method_definition" else "declaration",
            **_line_range(node, source)})
        if node.type == "method_definition":
            entity["file"], entity["line"] = rel, node.start_point[0] + 1
        if is_header and owner.type != "class_implementation":
            entity["accessLevel"] = "public"
        if method_type is not None and b"IBAction" in method_type.text and "@IBAction" not in entity["annotations"]:
            entity["annotations"].append("@IBAction")
        if swift_name:
            entity["swiftName"] = swift_name.group(1).decode()

    # ------------------------------------------------------------------ references

    def references(self, type_names: Set[str]) -> Tuple[List[Dict[str, Any]], Dict[str, int], Set[str]]:
        """Type references (to any of type_names), selector usage counts, and
        classes whose methods are invoked through runtime-built selectors.

        Selector counts are by selector only (any receiver), which errs on the side
        of keeping code. Calls from inside a method to its own selector don't count.
        A method body that calls NSSelectorFromString(<non-literal>) marks every
        class it names as a dynamic dispatch target — e.g.
        `NSSelectorFromString(className)` sent to BMBViewControllerTrackingHelper.
        """
        type_refs: List[Dict[str, Any]] = []
        selector_counts: Dict[str, int] = defaultdict(int)
        dynamic_classes: Set[str] = set()

        for rel, source, tree in self.trees:
            for node in walk(tree.root_node):
                t = node.type
                if t == "message_expression":
                    sel = message_selector(node)
                    if sel and not self._inside_own_method(node, sel):
                        selector_counts[sel] += 1
                elif t == "call_expression" and self._is_runtime_selector(node):
                    body = self._enclosing_body(node)
                    dynamic_classes |= {
                        _text(n) for n in walk(body)
                        if n.type in ("identifier", "type_identifier") and _text(n) in type_names
                    }
                elif t == "selector_expression":
                    sel = re.sub(r"\s+", "", _text(node))
                    sel = sel[len("@selector("):-1] if sel.startswith("@selector(") else sel
                    if sel:
                        selector_counts[sel] += 1
                elif t == "field_identifier" and node.parent.type == "field_expression":
                    prop = _text(node)
                    selector_counts[prop] += 1
                    selector_counts[f"set{prop[:1].upper()}{prop[1:]}:"] += 1
                elif t in ("identifier", "type_identifier"):
                    name = _text(node)
                    if name in type_names and self._is_type_reference(node, name):
                        owner = _owner(node)
                        type_refs.append({
                            "source_entity": _owner_name(owner) if owner is not None else "(file-scope)",
                            "source_file": rel,
                            "target_entity": name,
                            "target_file": None,
                            "reference_type": self._reference_kind(node),
                            "line": node.start_point[0] + 1,
                            "confidence": 1.0,
                        })
        return type_refs, dict(selector_counts), dynamic_classes

    @staticmethod
    def _is_runtime_selector(node) -> bool:
        """NSSelectorFromString(x) / NSClassFromString(x) with a non-literal argument."""
        func = node.child_by_field_name("function")
        if func is None or _text(func) not in ("NSSelectorFromString", "NSClassFromString"):
            return False
        args = node.child_by_field_name("arguments")
        first = args.named_children[0] if args is not None and args.named_children else None
        return first is not None and first.type != "string_literal"

    @staticmethod
    def _enclosing_body(node):
        cur = node.parent
        while cur is not None and cur.type not in ("method_definition", "function_definition"):
            cur = cur.parent
        return cur if cur is not None else node.parent

    @staticmethod
    def _is_type_reference(node, name: str) -> bool:
        parent = node.parent
        if parent.type in ("class_declaration", "protocol_forward_declaration", "preproc_include"):
            return False
        if parent.type in TYPE_DECLARATIONS:
            # The declared name itself, or the category name
            if _owner_name(parent) == name and parent.named_children[0] == node:
                return False
            if parent.child_by_field_name("category") == node:
                return False
        if parent.type == "message_expression":
            # Method keywords aren't type references; the receiver may be a class
            idx = next(i for i, c in enumerate(parent.children) if c == node)
            if parent.field_name_for_child(idx) == "method":
                return False
        owner = _owner(node)
        if owner is not None and _owner_name(owner) == name and parent != owner:
            return False  # self-reference inside its own @interface/@implementation
        return True

    @staticmethod
    def _reference_kind(node) -> str:
        parent = node.parent
        if parent.type in ("class_interface", "class_implementation") and \
                parent.child_by_field_name("superclass") == node:
            return "inheritance"
        if parent.type in ("protocol_reference_list",) or (
                parent.type == "type_name" and parent.parent is not None
                and parent.parent.type == "parameterized_arguments"):
            return "protocol_conformance"
        if parent.type == "message_expression":
            return "class_message"
        return "type_annotation"

    @staticmethod
    def _inside_own_method(node, selector: str) -> bool:
        cur = node.parent
        while cur is not None:
            if cur.type == "method_definition":
                return method_selector(cur) == selector
            cur = cur.parent
        return False

    # ------------------------------------------------------------------ outputs

    def entities(self) -> List[Dict[str, Any]]:
        # Test classes (XCTestCase subclasses) and their methods are run by the test runner
        test_classes = {n for n, c in self.classes.items()
                        if c.get("inheritsFrom") in self.test_base_classes}
        for name in test_classes:
            self.classes[name]["isTestCode"] = True
        for m in self.methods.values():
            if m.get("owner") in test_classes:
                m["isTestCode"] = True
        own_classes = [{k: v for k, v in c.items() if k != "isOwnClass"}
                       for c in self.classes.values() if c.get("isOwnClass", True)]
        return own_classes + list(self.protocols.values()) + list(self.methods.values())


# ---------------------------------------------------------------------- framework selectors

_HEADER_METHOD = re.compile(rb"^[ \t]*[-+][ \t]*\(", re.MULTILINE)
_KEYWORD = re.compile(rb"([A-Za-z_]\w*)\s*:")


def _selector_from_header_text(text: bytes) -> Optional[str]:
    """Selector from a header method declaration `- (T)foo:(A)a bar:(B)b ...;`."""
    # Strip parenthesised types (nested for block types)
    prev = None
    while prev != text:
        prev, text = text, re.sub(rb"\([^()]*\)", b"", text)
    text = text.lstrip(b"-+ \t")
    keywords = _KEYWORD.findall(text)
    if keywords:
        return "".join(k.decode() + ":" for k in keywords)
    m = re.match(rb"\s*([A-Za-z_]\w*)", text)
    return m.group(1).decode() if m else None


def selectors_in_headers(headers: Iterable[Path]) -> Set[str]:
    selectors: Set[str] = set()
    for h in headers:
        try:
            content = _MACRO_PATTERN.sub(_blank, h.read_bytes())
        except (IOError, OSError):
            continue
        for m in _HEADER_METHOD.finditer(content):
            end = content.find(b";", m.start())
            if end == -1 or end - m.start() > 2000:
                continue
            sel = _selector_from_header_text(content[m.start():end])
            if sel:
                selectors.add(sel)
    return selectors


def dependency_dirs(repo_path: Path) -> List[Path]:
    """Pods/ and Carthage/ directories at the top level or up to two levels down
    (workspaces with submodules may have their own)."""
    found = []
    for pattern in ("Pods", "Carthage", "*/Pods", "*/Carthage", "*/*/Pods", "*/*/Carthage"):
        found += [p for p in repo_path.glob(pattern) if p.is_dir() and "/.git/" not in str(p)]
    return found


def sdk_path() -> str:
    try:
        return subprocess.run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"],
                              capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception:
        return ""


def framework_selectors(repo_path: Path, cache_dir: Optional[Path] = None) -> Set[str]:
    """Selectors declared by the iOS SDK, Pods/Carthage and vendored .framework headers.

    A repo method with one of these selectors is (almost always) an override or a
    protocol method the framework calls. The SDK index is cached per SDK path.
    """
    selectors: Set[str] = set()
    cache_dir = cache_dir or Path.home() / ".cache" / "arbiter"
    sdk = sdk_path()
    if sdk:
        cache = cache_dir / f"sdk_selectors_{re.sub(r'[^A-Za-z0-9.]', '_', Path(sdk).name)}.json"
        if cache.exists():
            selectors |= set(json.loads(cache.read_text()))
        else:
            sdk_selectors = selectors_in_headers(Path(sdk, "System/Library/Frameworks").rglob("*.h"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(sorted(sdk_selectors)))
            selectors |= sdk_selectors

    for deps in dependency_dirs(repo_path):
        selectors |= selectors_in_headers(deps.rglob("*.h"))

    # Vendored binary frameworks checked into the repo (e.g. Frameworks/Foo.framework)
    vendored = [
        f for f in repo_path.rglob("*.h")
        if (".framework/" in str(f) or ".xcframework/" in str(f))
        and "/Pods/" not in str(f) and "/.git/" not in str(f)
    ]
    selectors |= selectors_in_headers(vendored)
    return selectors
