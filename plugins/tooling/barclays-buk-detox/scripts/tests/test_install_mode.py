"""Install-mode guards: catch changes that work in the monorepo but break once the
plugin is installed from the marketplace (see README "Install-mode rules").

Static checks only — the isolated-install smoke test is documented in the README.
"""

import json
import re
import sys
from pathlib import Path
from unittest import TestCase, main

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.utils.resolve_skill import resolve_named

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN_JSON = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())
PLUGIN_NAME = PLUGIN_JSON["name"]
# Markdown that Claude Code loads at runtime (agents, commands, skills).
RUNTIME_MD = sorted(
    p for d in ("agents", "commands", "skills") for p in (PLUGIN_ROOT / d).rglob("*.md")
)


def _marketplace_entry():
    for parent in PLUGIN_ROOT.parents:
        mp = parent / ".claude-plugin" / "marketplace.json"
        if mp.is_file():
            for entry in json.loads(mp.read_text()).get("plugins", []):
                if (parent / entry.get("source", "")).resolve() == PLUGIN_ROOT:
                    return entry
    return None


def _hits(pattern, skip_line=lambda line: False):
    rx = re.compile(pattern)
    out = []
    for p in RUNTIME_MD:
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if rx.search(line) and not skip_line(line):
                out.append(f"{p.relative_to(PLUGIN_ROOT)}:{n}: {line.strip()[:120]}")
    return out


class TestInstallMode(TestCase):
    def test_subagent_types_use_plugin_namespace(self):
        # Agents register as "<plugin.json name>:<agent>".
        agents = {p.stem for p in (PLUGIN_ROOT / "agents").glob("*.md")}
        bad = []
        for p in RUNTIME_MD:
            for name in re.findall(r'subagent_type: "([^"]+)"', p.read_text()):
                prefix, _, agent = name.partition(":")
                if prefix != PLUGIN_NAME or agent not in agents:
                    bad.append(f"{p.relative_to(PLUGIN_ROOT)}: {name}")
        self.assertEqual(bad, [], f"subagent_type must be '{PLUGIN_NAME}:<existing agent>'")

    def test_orchestrator_handoffs_name_agent_and_model(self):
        # Every "Delegate to `detox-*-agent`" must give the registered name and pass --model through.
        text = (PLUGIN_ROOT / "agents" / "detox-orchestrator-agent.md").read_text()
        bad = [line.strip()[:120] for line in text.splitlines()
               if re.search(r"Delegate to `detox-[a-z-]+-agent`", line)
               and not ('subagent_type: "' in line and 'model: "{model}"' in line)]
        self.assertEqual(bad, [], "hand-offs need subagent_type and model: \"{model}\"")

    def test_plugin_root_not_read_from_environment(self):
        # ${CLAUDE_PLUGIN_ROOT} is substituted inline; it is NOT an env var at runtime.
        bad = _hits(r"os\.environ(\.get)?\W+CLAUDE_PLUGIN_ROOT|\$env:CLAUDE_PLUGIN_ROOT|%CLAUDE_PLUGIN_ROOT%"
                    r"|\$CLAUDE_PLUGIN_ROOT\b")
        self.assertEqual(bad, [], "use the literal ${CLAUDE_PLUGIN_ROOT} text, not an env var")

    def test_no_monorepo_paths(self):
        bad = _hits(r"plugins/tooling/", skip_line=lambda line: line.startswith("source:"))
        self.assertEqual(bad, [], "monorepo paths do not exist in an installed plugin")

    def test_plugin_skill_refs_are_registered(self):
        # Only top-level skills/<name>/SKILL.md register; nested ones must be loaded by path.
        top_level = {p.parent.name for p in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")}
        bad = [h for h in _hits(rf"^\s*-\s*{re.escape(PLUGIN_NAME)}:")
               if h.split(f"{PLUGIN_NAME}:", 1)[1].strip() not in top_level]
        bad += _hits(rf"{re.escape(PLUGIN_NAME)}:{re.escape(PLUGIN_NAME)}:")
        self.assertEqual(bad, [], "skill refs must name a registered top-level skill")

    def test_resolver_skill_refs_exist(self):
        refs = set()
        for p in RUNTIME_MD:
            refs.update(re.findall(r'\{"skill": "([a-z0-9-]+(?:/[a-z0-9-]+)?)"\}', p.read_text()))
        self.assertTrue(refs)
        self.assertEqual([r for r in sorted(refs) if not resolve_named(r)["path"]], [])

    def test_test_agent_loads_test_generation_skill(self):
        text = (PLUGIN_ROOT / "agents" / "detox-test-agent.md").read_text()
        self.assertIn('{"skill": "test-generation"}', text)
        self.assertIn("resolve_skill.py", text)

    def test_no_gnu_timeout_command(self):
        # GNU timeout/gtimeout are not on macOS (exit 127); use the Bash tool's timeout parameter.
        bad = _hits(r"(^|[`;&|(]\s*|\$\(\s*)g?timeout\s+\d")
        self.assertEqual(bad, [], "do not wrap commands in timeout/gtimeout")

    def test_scripts_use_verified_python(self):
        # python3 is often missing on Windows; run scripts with the {python} verified at startup.
        # The detection probe itself (python3 -c "import sys; print(sys.version_info[0])") is allowed.
        bad = _hits(r"\bpython3\s+(-c|[\"$])",
                    skip_line=lambda line: 'print(sys.version_info[0])' in line)
        self.assertEqual(bad, [], "invoke Detox scripts with {python}, not python3")

    def test_skill_names_match_folders(self):
        # Agent Skills spec: lowercase letters, digits and hyphens — no underscores.
        bad = []
        for skill in (PLUGIN_ROOT / "skills").rglob("SKILL.md"):
            m = re.search(r"^name:\s*(\S+)", skill.read_text(), re.M)
            if m and m.group(1) != skill.parent.name:
                bad.append(f"{skill.parent.name} -> name: {m.group(1)}")
        self.assertEqual(bad, [])

    def test_plugin_name_follows_convention(self):
        self.assertTrue(PLUGIN_NAME.startswith("barclays-buk-"), "CONTRIBUTING.md: barclays-buk-<name>")
        entry = _marketplace_entry()
        if entry is None:
            self.skipTest("marketplace.json not found (running outside the marketplace repo)")
        self.assertEqual(entry.get("name"), PLUGIN_NAME,
                         "plugin.json name must match the marketplace entry name")

    def test_marketplace_version_matches_plugin_json(self):
        entry = _marketplace_entry()
        if entry is None:
            self.skipTest("marketplace.json not found (running outside the marketplace repo)")
        self.assertEqual(entry.get("version"), PLUGIN_JSON["version"],
                         "bump the version in both plugin.json and marketplace.json")


if __name__ == "__main__":
    main()
