#!/usr/bin/env python3
"""Export .drawio files to PNG or JPG using Playwright.

Renders draw.io XML with a self-contained Canvas renderer (no external JS
dependencies).  On first run the script creates a Python venv and installs
playwright + Chromium.  Subsequent runs reuse the existing venv.
"""

import json
import os
import subprocess
import sys
import venv
import xml.etree.ElementTree as ET
from pathlib import Path

# ── locations ─────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
VENV_DIR = SCRIPT_DIR / ".export-venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"


# ── bootstrap: Python venv ────────────────────────────────────────────
def _running_inside_venv() -> bool:
    return Path(sys.executable).resolve() == VENV_PYTHON.resolve()


def _ensure_venv() -> None:
    if VENV_PYTHON.exists():
        return

    print("First run — setting up Python virtual environment …")
    venv.create(VENV_DIR, with_pip=True)

    pip = VENV_DIR / "bin" / "pip"
    print("  Installing playwright …")
    subprocess.check_call(
        [str(pip), "install", "--quiet", "playwright"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    playwright_bin = VENV_DIR / "bin" / "playwright"
    print("  Installing Chromium browser (one-time download) …")
    subprocess.check_call(
        [str(playwright_bin), "install", "chromium"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print("  Setup complete.\n")


def _reexec_in_venv() -> None:
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__] + sys.argv[1:])


# ── export logic (runs inside the venv) ──────────────────────────────
import argparse
import base64
import tempfile


def parse_drawio_to_json(drawio_xml: str) -> dict:
    """Parse draw.io XML into a JSON-serialisable dict of cells."""
    root = ET.fromstring(drawio_xml)
    diagram = root.find(".//diagram")
    if diagram is None:
        raise ValueError("No <diagram> element found in draw.io file")

    model = diagram.find(".//mxGraphModel")
    if model is None:
        raise ValueError("No <mxGraphModel> element found")

    # Extract mxGraphModel attributes
    model_attrs = dict(model.attrib)

    graph_root = model.find("root")
    if graph_root is None:
        raise ValueError("No <root> element found")

    cells = []
    for cell in graph_root.findall("mxCell"):
        c = dict(cell.attrib)
        geo = cell.find("mxGeometry")
        if geo is not None:
            g = dict(geo.attrib)
            # Parse Array children (waypoints)
            array_el = geo.find("Array")
            if array_el is not None:
                points = []
                for pt in array_el.findall("mxPoint"):
                    points.append(dict(pt.attrib))
                g["points"] = points
            # Parse source/target point children
            for pt_child in geo.findall("mxPoint"):
                pt_as = pt_child.get("as", "")
                if pt_as == "sourcePoint":
                    g["sourcePoint"] = dict(pt_child.attrib)
                elif pt_as == "targetPoint":
                    g["targetPoint"] = dict(pt_child.attrib)
            c["geometry"] = g
        cells.append(c)

    return {"modelAttrs": model_attrs, "cells": cells}


# ---------------------------------------------------------------------------
# Self-contained Canvas renderer (inline JS).
#
# Handles: rectangle (rounded), ellipse, rhombus (diamond), document,
#          parallelogram, text labels, connectors with arrowheads,
#          swimlane containers.
# Styling: fillColor, strokeColor, strokeWidth, dashed, fontSize, fontStyle.
# ---------------------------------------------------------------------------
RENDERER_JS = r"""
// ── helpers ──────────────────────────────────────────────────────────
function parseStyle(styleStr) {
    var map = {};
    if (!styleStr) return map;
    var pairs = styleStr.split(';');
    for (var i = 0; i < pairs.length; i++) {
        var p = pairs[i].trim();
        if (!p) continue;
        var eq = p.indexOf('=');
        if (eq > 0) {
            map[p.substring(0, eq)] = p.substring(eq + 1);
        } else {
            // Shape identifier (e.g. "ellipse", "rhombus", "swimlane")
            map['_shape'] = p;
        }
    }
    return map;
}

function setStroke(ctx, s) {
    ctx.strokeStyle = s.strokeColor || '#1e1e1e';
    ctx.lineWidth = parseFloat(s.strokeWidth) || 1;
    if (s.dashed === '1') {
        var pat = (s.dashPattern || '5 5').split(' ').map(Number);
        ctx.setLineDash(pat);
    } else {
        ctx.setLineDash([]);
    }
}

function htmlToText(html) {
    if (!html) return '';
    return html
        .replace(/<br\s*\/?>/gi, '\n')
        .replace(/<[^>]+>/g, '')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .trim();
}

// ── shape renderers ─────────────────────────────────────────────────
function renderRect(ctx, x, y, w, h, s) {
    var r = (s.rounded === '1') ? Math.min(8, w / 4, h / 4) : 0;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    if (s.fillColor && s.fillColor !== 'none') {
        ctx.fillStyle = s.fillColor;
        ctx.fill();
    }
    setStroke(ctx, s);
    ctx.stroke();
}

function renderEllipse(ctx, x, y, w, h, s) {
    ctx.beginPath();
    ctx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
    if (s.fillColor && s.fillColor !== 'none') {
        ctx.fillStyle = s.fillColor;
        ctx.fill();
    }
    setStroke(ctx, s);
    ctx.stroke();
}

function renderDiamond(ctx, x, y, w, h, s) {
    var cx = x + w / 2, cy = y + h / 2;
    ctx.beginPath();
    ctx.moveTo(cx, y);
    ctx.lineTo(x + w, cy);
    ctx.lineTo(cx, y + h);
    ctx.lineTo(x, cy);
    ctx.closePath();
    if (s.fillColor && s.fillColor !== 'none') {
        ctx.fillStyle = s.fillColor;
        ctx.fill();
    }
    setStroke(ctx, s);
    ctx.stroke();
}

function renderDocument(ctx, x, y, w, h, s) {
    var waveH = h * 0.15;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + h - waveH);
    ctx.quadraticCurveTo(x + w * 0.75, y + h - waveH * 2, x + w / 2, y + h - waveH);
    ctx.quadraticCurveTo(x + w * 0.25, y + h, x, y + h - waveH);
    ctx.closePath();
    if (s.fillColor && s.fillColor !== 'none') {
        ctx.fillStyle = s.fillColor;
        ctx.fill();
    }
    setStroke(ctx, s);
    ctx.stroke();
}

function renderSwimlane(ctx, x, y, w, h, s, label) {
    var startSize = parseFloat(s.startSize) || 20;
    // Header
    ctx.beginPath();
    ctx.rect(x, y, w, startSize);
    if (s.fillColor && s.fillColor !== 'none') {
        ctx.fillStyle = s.fillColor;
        ctx.fill();
    }
    setStroke(ctx, s);
    ctx.stroke();
    // Body
    ctx.beginPath();
    ctx.rect(x, y + startSize, w, h - startSize);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    setStroke(ctx, s);
    ctx.stroke();
    // Label in header
    if (label) {
        var fs = parseFloat(s.fontSize) || 12;
        var bold = (s.fontStyle === '1') ? 'bold ' : '';
        ctx.font = bold + fs + 'px sans-serif';
        ctx.fillStyle = s.fontColor || '#000000';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, x + w / 2, y + startSize / 2);
    }
}

function renderLabel(ctx, x, y, w, h, s, label) {
    if (!label) return;
    var lines = label.split('\n');
    var fs = parseFloat(s.fontSize) || 12;
    var bold = (s.fontStyle === '1') ? 'bold ' : '';
    var fontFamily = s.fontFamily || 'sans-serif';
    ctx.font = bold + fs + 'px ' + fontFamily;
    ctx.fillStyle = s.fontColor || '#000000';

    var align = s.align || 'center';
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';

    var lineH = fs * 1.3;
    var totalH = lines.length * lineH;
    var startY = y + (h - totalH) / 2 + lineH / 2;
    var tx = (align === 'left') ? x + 4 : (align === 'right') ? x + w - 4 : x + w / 2;

    for (var i = 0; i < lines.length; i++) {
        ctx.fillText(lines[i], tx, startY + i * lineH);
    }
}

function drawArrowhead(ctx, tipX, tipY, fromX, fromY, lineWidth) {
    var dx = tipX - fromX;
    var dy = tipY - fromY;
    var angle = Math.atan2(dy, dx);
    var headLen = 10 + (lineWidth || 1) * 1.5;
    var headAngle = Math.PI / 7;
    ctx.beginPath();
    ctx.moveTo(tipX - headLen * Math.cos(angle - headAngle),
               tipY - headLen * Math.sin(angle - headAngle));
    ctx.lineTo(tipX, tipY);
    ctx.lineTo(tipX - headLen * Math.cos(angle + headAngle),
               tipY - headLen * Math.sin(angle + headAngle));
    ctx.closePath();
    ctx.fill();
}

function renderEdge(ctx, cell, cellsById, s) {
    var pts = [];

    // Source point
    var srcCell = cellsById[cell.source];
    var tgtCell = cellsById[cell.target];
    var geo = cell.geometry || {};

    if (srcCell && tgtCell) {
        var srcGeo = srcCell.geometry || {};
        var tgtGeo = tgtCell.geometry || {};
        var sx = parseFloat(srcGeo.x) || 0;
        var sy = parseFloat(srcGeo.y) || 0;
        var sw = parseFloat(srcGeo.width) || 0;
        var sh = parseFloat(srcGeo.height) || 0;
        var tx = parseFloat(tgtGeo.x) || 0;
        var ty = parseFloat(tgtGeo.y) || 0;
        var tw = parseFloat(tgtGeo.width) || 0;
        var th = parseFloat(tgtGeo.height) || 0;

        // Add parent offsets
        if (srcCell.parent && srcCell.parent !== '0' && srcCell.parent !== '1') {
            var sp = cellsById[srcCell.parent];
            if (sp && sp.geometry) { sx += parseFloat(sp.geometry.x) || 0; sy += parseFloat(sp.geometry.y) || 0; }
        }
        if (tgtCell.parent && tgtCell.parent !== '0' && tgtCell.parent !== '1') {
            var tp = cellsById[tgtCell.parent];
            if (tp && tp.geometry) { tx += parseFloat(tp.geometry.x) || 0; ty += parseFloat(tp.geometry.y) || 0; }
        }

        // Use exit/entry points from style if available
        var exitX = (s.exitX !== undefined) ? parseFloat(s.exitX) : 0.5;
        var exitY = (s.exitY !== undefined) ? parseFloat(s.exitY) : 1;
        var entryX = (s.entryX !== undefined) ? parseFloat(s.entryX) : 0.5;
        var entryY = (s.entryY !== undefined) ? parseFloat(s.entryY) : 0;

        var startX = sx + sw * exitX;
        var startY = sy + sh * exitY;
        var endX = tx + tw * entryX;
        var endY = ty + th * entryY;

        pts.push([startX, startY]);

        // Add waypoints from geometry
        if (geo.points) {
            for (var i = 0; i < geo.points.length; i++) {
                var wp = geo.points[i];
                pts.push([parseFloat(wp.x) || 0, parseFloat(wp.y) || 0]);
            }
        }

        pts.push([endX, endY]);
    } else if (geo.sourcePoint && geo.targetPoint) {
        // Standalone edge (e.g. legend arrows)
        pts.push([parseFloat(geo.sourcePoint.x) || 0, parseFloat(geo.sourcePoint.y) || 0]);
        if (geo.points) {
            for (var i = 0; i < geo.points.length; i++) {
                pts.push([parseFloat(geo.points[i].x) || 0, parseFloat(geo.points[i].y) || 0]);
            }
        }
        pts.push([parseFloat(geo.targetPoint.x) || 0, parseFloat(geo.targetPoint.y) || 0]);
    }

    if (pts.length < 2) return;

    setStroke(ctx, s);
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);

    // Orthogonal routing
    if (s.edgeStyle === 'orthogonalEdgeStyle' && pts.length === 2) {
        var mx = (pts[0][0] + pts[1][0]) / 2;
        ctx.lineTo(mx, pts[0][1]);
        ctx.lineTo(mx, pts[1][1]);
        ctx.lineTo(pts[1][0], pts[1][1]);
    } else {
        for (var i = 1; i < pts.length; i++) {
            ctx.lineTo(pts[i][0], pts[i][1]);
        }
    }
    ctx.stroke();

    // Arrowheads
    var lw = parseFloat(s.strokeWidth) || 1;
    ctx.fillStyle = s.strokeColor || '#1e1e1e';

    if (s.endArrow && s.endArrow !== 'none') {
        var last = pts[pts.length - 1];
        var prev = pts[pts.length - 2];
        drawArrowhead(ctx, last[0], last[1], prev[0], prev[1], lw);
    }
    if (s.startArrow && s.startArrow !== 'none') {
        var first = pts[0];
        var second = pts[1];
        drawArrowhead(ctx, first[0], first[1], second[0], second[1], lw);
    }

    // Edge label
    if (cell.value) {
        var label = cell.value.replace(/<[^>]+>/g, '').replace(/&[^;]+;/g, ' ').trim();
        if (label) {
            var midIdx = Math.floor(pts.length / 2);
            var mx2, my2;
            if (pts.length % 2 === 0) {
                mx2 = (pts[midIdx - 1][0] + pts[midIdx][0]) / 2;
                my2 = (pts[midIdx - 1][1] + pts[midIdx][1]) / 2;
            } else {
                mx2 = pts[midIdx][0];
                my2 = pts[midIdx][1];
            }
            var efs = parseFloat(s.fontSize) || 10;
            ctx.font = efs + 'px sans-serif';
            var tw2 = ctx.measureText(label).width;
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(mx2 - tw2 / 2 - 3, my2 - efs / 2 - 2, tw2 + 6, efs + 4);
            ctx.fillStyle = s.fontColor || '#000000';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(label, mx2, my2);
        }
    }
}

// ── main render ─────────────────────────────────────────────────────
function renderScene(canvas, data) {
    var cells = data.cells;
    var cellsById = {};
    for (var i = 0; i < cells.length; i++) {
        cellsById[cells[i].id] = cells[i];
    }

    // Separate vertices and edges
    var vertices = [];
    var edges = [];
    for (var i = 0; i < cells.length; i++) {
        var c = cells[i];
        if (c.edge === '1') edges.push(c);
        else if (c.vertex === '1' || (c.geometry && c.geometry.width)) vertices.push(c);
    }

    // Compute bounding box
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

    for (var i = 0; i < vertices.length; i++) {
        var v = vertices[i];
        var g = v.geometry;
        if (!g) continue;
        var vx = parseFloat(g.x) || 0;
        var vy = parseFloat(g.y) || 0;
        var vw = parseFloat(g.width) || 0;
        var vh = parseFloat(g.height) || 0;
        // Add parent offset
        if (v.parent && v.parent !== '0' && v.parent !== '1') {
            var par = cellsById[v.parent];
            if (par && par.geometry) {
                vx += parseFloat(par.geometry.x) || 0;
                vy += parseFloat(par.geometry.y) || 0;
            }
        }
        minX = Math.min(minX, vx);
        minY = Math.min(minY, vy);
        maxX = Math.max(maxX, vx + vw);
        maxY = Math.max(maxY, vy + vh);
    }

    // Include edge waypoints and standalone points
    for (var i = 0; i < edges.length; i++) {
        var eg = edges[i].geometry;
        if (!eg) continue;
        if (eg.points) {
            for (var j = 0; j < eg.points.length; j++) {
                var px = parseFloat(eg.points[j].x) || 0;
                var py = parseFloat(eg.points[j].y) || 0;
                minX = Math.min(minX, px); minY = Math.min(minY, py);
                maxX = Math.max(maxX, px); maxY = Math.max(maxY, py);
            }
        }
        if (eg.sourcePoint) {
            minX = Math.min(minX, parseFloat(eg.sourcePoint.x) || 0);
            minY = Math.min(minY, parseFloat(eg.sourcePoint.y) || 0);
            maxX = Math.max(maxX, parseFloat(eg.sourcePoint.x) || 0);
            maxY = Math.max(maxY, parseFloat(eg.sourcePoint.y) || 0);
        }
        if (eg.targetPoint) {
            minX = Math.min(minX, parseFloat(eg.targetPoint.x) || 0);
            minY = Math.min(minY, parseFloat(eg.targetPoint.y) || 0);
            maxX = Math.max(maxX, parseFloat(eg.targetPoint.x) || 0);
            maxY = Math.max(maxY, parseFloat(eg.targetPoint.y) || 0);
        }
    }

    if (minX === Infinity) { minX = 0; minY = 0; maxX = 400; maxY = 300; }

    var padding = 50;
    var sceneW = maxX - minX + padding * 2;
    var sceneH = maxY - minY + padding * 2;
    var offsetX = -minX + padding;
    var offsetY = -minY + padding;

    canvas.width = Math.ceil(sceneW);
    canvas.height = Math.ceil(sceneH);

    var ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(offsetX, offsetY);

    // Render vertices first (back to front by document order)
    for (var i = 0; i < vertices.length; i++) {
        var v = vertices[i];
        var g = v.geometry;
        if (!g) continue;
        var s = parseStyle(v.style);
        var vx = parseFloat(g.x) || 0;
        var vy = parseFloat(g.y) || 0;
        var vw = parseFloat(g.width) || 0;
        var vh = parseFloat(g.height) || 0;

        // Add parent offset for absolute positioning
        if (v.parent && v.parent !== '0' && v.parent !== '1') {
            var par = cellsById[v.parent];
            if (par && par.geometry) {
                vx += parseFloat(par.geometry.x) || 0;
                vy += parseFloat(par.geometry.y) || 0;
            }
        }

        ctx.save();

        var shape = s._shape || '';
        if (shape === 'swimlane') {
            renderSwimlane(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        } else if (shape === 'ellipse') {
            renderEllipse(ctx, vx, vy, vw, vh, s);
            renderLabel(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        } else if (shape === 'rhombus') {
            renderDiamond(ctx, vx, vy, vw, vh, s);
            renderLabel(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        } else if (s.shape === 'document') {
            renderDocument(ctx, vx, vy, vw, vh, s);
            renderLabel(ctx, vx, vy, vw, vh * 0.85, s, htmlToText(v.value));
        } else if (s.shape === 'parallelogram') {
            // Render as skewed rect
            ctx.beginPath();
            var offset = vw * 0.15;
            ctx.moveTo(vx + offset, vy);
            ctx.lineTo(vx + vw, vy);
            ctx.lineTo(vx + vw - offset, vy + vh);
            ctx.lineTo(vx, vy + vh);
            ctx.closePath();
            if (s.fillColor && s.fillColor !== 'none') { ctx.fillStyle = s.fillColor; ctx.fill(); }
            setStroke(ctx, s); ctx.stroke();
            renderLabel(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        } else if (shape === 'text' || s._shape === 'text' ||
                   (!s.fillColor && !s.strokeColor && !s.rounded && !shape && v.value)) {
            // Pure text element
            renderLabel(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        } else {
            // Default: rectangle (possibly rounded)
            renderRect(ctx, vx, vy, vw, vh, s);
            renderLabel(ctx, vx, vy, vw, vh, s, htmlToText(v.value));
        }

        ctx.restore();
    }

    // Render edges on top
    for (var i = 0; i < edges.length; i++) {
        ctx.save();
        var s = parseStyle(edges[i].style);
        renderEdge(ctx, edges[i], cellsById, s);
        ctx.restore();
    }

    ctx.restore();
}
"""


def create_export_html(scene_json: str, mime_type: str) -> str:
    """Build self-contained HTML that renders the parsed draw.io data to a
    canvas and writes the base-64 result into a DOM node for Playwright."""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<canvas id="canvas"></canvas>
<div id="result"></div>
<div id="done"></div>
<div id="error"></div>
<script>
{RENDERER_JS}

try {{
    var data = {scene_json};
    var canvas = document.getElementById('canvas');
    renderScene(canvas, data);

    canvas.toBlob(function(blob) {{
        var reader = new FileReader();
        reader.onload = function() {{
            var base64 = reader.result.split(',')[1];
            document.getElementById('result').textContent = base64;
            document.getElementById('done').textContent = 'EXPORT_DONE';
        }};
        reader.readAsDataURL(blob);
    }}, '{mime_type}', 0.92);
}} catch (err) {{
    document.getElementById('error').textContent = 'EXPORT_ERROR: ' + err.message;
}}
</script>
</body>
</html>"""


def resolve_output_path(input_path: Path, fmt: str, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg).resolve()

    stem = input_path.stem  # "architecture" from "architecture.drawio"
    return input_path.parent / f"{stem}.{fmt}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export draw.io files to PNG or JPG",
    )
    parser.add_argument("input_file", help="Path to .drawio file")
    parser.add_argument(
        "--format",
        "-f",
        choices=["png", "jpg"],
        default="png",
        help="Output format (default: png)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: <input_name>.<format>)",
    )
    args = parser.parse_args()

    # --- validate input ------------------------------------------------
    input_path = Path(args.input_file).resolve()
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if input_path.suffix != ".drawio":
        print("Error: Input must be a .drawio file", file=sys.stderr)
        sys.exit(1)

    # --- resolve output path & mime type -------------------------------
    fmt = args.format
    output_path = resolve_output_path(input_path, fmt, args.output)
    mime_type = "image/png" if fmt == "png" else "image/jpeg"

    # --- read & parse draw.io XML --------------------------------------
    with open(input_path, "r", encoding="utf-8") as f:
        drawio_xml = f.read()

    scene_data = parse_drawio_to_json(drawio_xml)
    scene_json = json.dumps(scene_data)

    # --- launch headless browser & export ------------------------------
    from playwright.sync_api import sync_playwright

    html_content = create_export_html(scene_json, mime_type)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(html_content)
                tmp_path = tmp.name

            page.goto(f"file://{tmp_path}")

            page.wait_for_function(
                """() =>
                    document.getElementById('done').textContent === 'EXPORT_DONE'
                    || document.getElementById('error').textContent.startsWith('EXPORT_ERROR')
                """,
                timeout=30_000,
            )

            error_text = page.locator("#error").text_content()
            if error_text and error_text.startswith("EXPORT_ERROR"):
                print(f"Export failed: {error_text}", file=sys.stderr)
                sys.exit(1)

            b64_data = page.locator("#result").text_content()
            if not b64_data:
                print("Error: No image data produced", file=sys.stderr)
                sys.exit(1)

            image_bytes = base64.b64decode(b64_data)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as out:
                out.write(image_bytes)

            print(f"Exported: {output_path}")

        finally:
            if tmp_path:
                os.unlink(tmp_path)
            browser.close()


if __name__ == "__main__":
    if not _running_inside_venv():
        _ensure_venv()
        _reexec_in_venv()

    main()
