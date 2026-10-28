# torch plugin

Claude Code plugin that provides the `/torch:on` skill for task-driven capability discovery.

## Requirements

- Python 3.10+
- Claude Code 2.1.110+ (older versions require manual dependency installation)

## Installing

### Via BUK marketplace (recommended)

Install the plugin from the BUK CIO marketplace:

```sh
/plugin install barclays-buk-torch@barclays-cio-buk
```

### Via DG repo checkout

If running from a local clone of this repository:

```sh
claude plugins marketplace add git@app.gitlab.barcapint.com:barclays/claude/marketplace/cio/buk.git \
  --sparse .claude-plugin plugins

claude plugins install torch@torch
```

> **HTTPS alternative** (if SSH is not available):
> ```sh
> claude plugins marketplace add https://app.gitlab.barcapint.com/barclays/claude/marketplace/cio/buk.git \
>   --sparse .claude-plugin plugins
> ```

### Post-install setup

After installing, run setup.py to wire hooks, create the runtime venv, and copy files to a stable location:

```sh
# macOS / Linux
python3 setup.py

# Windows
python setup.py
```

This wires 4 hooks into `~/.claude/settings.json`, copies runtime files to `~/.claude/hooks/torch/`, and creates an isolated venv at `~/.claude/torch/venv/`.

**Restart Claude Code after setup completes.**

Preview changes without writing anything:

```sh
python3 setup.py --dry-run
```

### Verify installation

```sh
python3 setup.py --verify
```

Runs a 14-point health check including hook wiring, venv health, runtime file integrity, daemon status, and a smoke test.

## Getting updates

When new capabilities are published to the catalogue, pull the latest:

```sh
/marketplace sync barclays-cio-buk
```

Then re-run setup.py to update the runtime copy:

```sh
python3 setup.py
```

Restart Claude Code after updating.

## Uninstalling

To fully remove Torch (hooks, runtime copy, venv, and data):

```sh
python3 setup.py --uninstall
```

To also remove the managed cue from `~/.claude/CLAUDE.md`:

```sh
python3 setup.py --uninstall --cue
```

> Note: `claude plugins uninstall torch` only removes the plugin source files. It does **not** clean up hooks in `settings.json`, the runtime copy at `~/.claude/hooks/torch/`, or the venv. Always use `setup.py --uninstall` for a complete removal.

## Structure

```
torch/
├── .claude-plugin/
│   └── plugin.json                    # Plugin manifest (v0.3.2)
├── setup.py                           # Unified installer (install/verify/uninstall)
├── bin/
│   ├── router.py                      # IDF-weighted BM25 scorer
│   └── router-daemon.py               # Persistent Unix socket daemon
├── hooks/
│   ├── on-prompt-submit.py            # UserPromptSubmit + SubagentStart hook
│   ├── on-tool-use.py                 # PostToolUse attribution hook
│   └── on-stop.py                     # Stop hook — terminates daemon on session end
└── skills/
    └── on/
        ├── SKILL.md                   # Torch skill (≤6 KiB)
        └── catalog/
            ├── provenance.json        # Source revision + digests
            ├── cards/<id>.md          # Capability routing cards — do not edit
            ├── details/<id>.md        # Per-capability detail cards — do not edit
            └── landscape/
                ├── model-map.md       # Graph navigation layer — do not edit
                ├── graph-data.json    # Capability graph — do not edit
                ├── graph-provenance.json  # Graph build provenance — do not edit
                └── routing-index.json # BM25 routing index (push channel) — do not edit
```

All files under `catalog/` are generated. The platform team rebuilds and pushes them to `main`
when capability sources change. Engineers pull updates via `/marketplace sync barclays-cio-buk`.

## Invocation modes

| Mode | SKILL.md | Cue in CLAUDE.md | Behaviour |
|---|---|---|---|
| Assisted | `disable-model-invocation: false` | Present | Model invokes torch skill autonomously during task planning |
| Manual | `disable-model-invocation: true` | Absent | User invokes `/torch:on` explicitly |

Current mode: **assisted** (`graph-mode: enabled`).
