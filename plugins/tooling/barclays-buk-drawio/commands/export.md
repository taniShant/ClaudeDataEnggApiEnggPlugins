---
description: "Export .drawio files to PNG or JPG format using a Playwright headless browser with a self-contained Canvas renderer."
user-invocable: true
argument-hint: "<input-file.drawio> [png|jpg] [output-file]"
---

You are the main Claude Code agent.

When the user runs `/barclays-buk-drawio:export`, they want to export a draw.io diagram to an image format.

## Argument Parsing

The user provides arguments as a single string after `/barclays-buk-drawio:export`.
Parse them positionally:

| Position | Meaning | Required | Default |
|----------|---------|----------|---------|
| 1 | Path to `.drawio` file | **yes** | — |
| 2 | Output format: `png` or `jpg` | no | `png` |
| 3 | Output file path | no | `<input_stem>.<format>` in same directory as input |

### Examples of raw argument strings

| User types | input_file | format | output |
|---|---|---|---|
| `my_diagram.drawio` | `my_diagram.drawio` | `png` | `my_diagram.png` |
| `my_diagram.drawio jpg` | `my_diagram.drawio` | `jpg` | `my_diagram.jpg` |
| `my_diagram.drawio png out/result.png` | `my_diagram.drawio` | `png` | `out/result.png` |

## Example Output

```
Exported: ./architecture.png
```

## Execution

1. **Parse** the user's argument string into the three values above.
2. **Build and run** the command:

```bash
python3 ../scripts/export_drawio.py <input_file> --format <format> --output <output_file>
```

Replace `<input_file>`, `<format>`, and `<output_file>` with the resolved values.
If the user did not supply an output file, omit `--output` and let the script
use its default.

3. **Report** the result to the user (the script prints the output path on
   success, or an error message on failure).

## Prerequisites

On the first run the script **automatically** creates a virtual environment at
`../scripts/.export-venv`, installs `playwright`, and downloads the Chromium
browser binary. No manual setup is required.

## Error Handling

- **File not found** — relay the error; ask the user to check the path.
- **Venv creation failure** — relay the error; the user may need to check their
  Python installation or network connectivity.
- **Export timeout / render error** — relay the error message from the script.
- **CDN unreachable** — if the diagrams.net viewer JS cannot be loaded, suggest
  the user open the `.drawio` file in app.diagrams.net and export manually.

## Fallback Behavior

If the export script is not found at `../scripts/export_drawio.py`, inform the user that the drawio plugin's export script is missing. Suggest they reinstall the plugin.
