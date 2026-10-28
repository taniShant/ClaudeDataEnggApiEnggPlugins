#!/usr/bin/env python3
"""Resolve absolute paths to Detox's nested skill files.

Claude Code only registers skills at skills/<name>/SKILL.md, so Detox's nested
skills (remediation-cwe/*, analysis/*, ...) are never loaded as skills when the
plugin is installed from the marketplace. Agents Read them by path instead; this
script resolves that path from the plugin install directory (never the target repo).

Input (JSON stdin):
    {"cwe": "CWE-79"}                          # CWE remediation skill
    {"language": "java"}                       # language fix-pattern skill
    {"skill": "analysis/dependency-analyzer"}  # any nested skill by relative dir
    (keys may be combined; each requested key gets a result)

Output (JSON stdout):
    {"status": "success",
     "plugin_root": "/.../barclays-buk-detox/<version>",
     "cwe": {"path": "/.../skills/remediation-cwe/cwe-079-xss/SKILL.md", "fallback": false},
     "language": {"path": "/.../java-fix-patterns/SKILL.md"},
     "skill": {"path": "/.../analysis/dependency-analyzer/SKILL.md"}}
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.common import read_json_input, write_json_output
from scripts.core.errors import error_exit

# scripts/utils/resolve_skill.py → three parents up reaches the plugin root.
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
CWE_DIR = SKILLS_DIR / "remediation-cwe"
LANG_DIR = SKILLS_DIR / "language-patterns-individual"
FALLBACK_CWE = CWE_DIR / "cwe-generic-fallback" / "SKILL.md"

LANGUAGE_ALIASES = {
    "js": "javascript", "node": "javascript", "nodejs": "javascript",
    "ts": "typescript", "py": "python", "golang": "go",
    "c#": "csharp", "cs": "csharp", "dotnet": "csharp", "kotlin": "java",
}


def resolve_cwe(cwe: str) -> dict:
    m = re.search(r"(\d+)", str(cwe))
    if not m:
        error_exit(f"Invalid CWE id: {cwe!r}", "resolve_skill")
    number = int(m.group(1))
    # Folder names are inconsistently padded (cwe-079, cwe-95, cwe-1188): match numerically.
    for d in sorted(CWE_DIR.glob("cwe-*")):
        dm = re.match(r"cwe-(\d+)-", d.name)
        if dm and int(dm.group(1)) == number and (d / "SKILL.md").is_file():
            return {"path": str(d / "SKILL.md"), "fallback": False}
    return {"path": str(FALLBACK_CWE), "fallback": True}


def resolve_language(language: str) -> dict:
    lang = LANGUAGE_ALIASES.get(language.strip().lower(), language.strip().lower())
    p = LANG_DIR / f"{lang}-fix-patterns" / "SKILL.md"
    return {"path": str(p) if p.is_file() else None}


def resolve_named(skill: str) -> dict:
    p = (SKILLS_DIR / skill / "SKILL.md").resolve()
    # Reject traversal out of the plugin's skills directory.
    if SKILLS_DIR.resolve() not in p.parents or not p.is_file():
        return {"path": None}
    return {"path": str(p)}


def main() -> None:
    inp = read_json_input()
    if not SKILLS_DIR.is_dir():
        error_exit(f"Detox skills directory not found at {SKILLS_DIR} — plugin not installed correctly",
                   "resolve_skill")
    out: dict = {"status": "success", "plugin_root": str(SKILLS_DIR.parent)}
    if inp.get("cwe"):
        out["cwe"] = resolve_cwe(inp["cwe"])
    if inp.get("language"):
        out["language"] = resolve_language(inp["language"])
    if inp.get("skill"):
        out["skill"] = resolve_named(inp["skill"])
    if len(out) == 2:
        error_exit("Provide at least one of: cwe, language, skill", "resolve_skill")
    write_json_output(out)


if __name__ == "__main__":
    main()
