#!/usr/bin/env python3
"""Generate printable grid/line paper SVGs for book binding.

Supports square grids, hexagonal grids, lined writing paper, and isometric grids.
Pages can fill the whole sheet or be split into panels for folding/cutting.
"""

import argparse
import ctypes.util
import math
import os
import subprocess
import sys
import svg


# US Letter in mm
PAGE_W_MM = 215.9
PAGE_H_MM = 279.4

MM_PER_PT = 25.4 / 72


def mm(val: float) -> float:
    """Convert mm to SVG user units (points at 72dpi)."""
    return val / MM_PER_PT


def draw_grid(w: float, h: float, size: float, line_width: float, color: str) -> list:
    """Draw a square grid pattern within w x h area (all values in mm)."""
    elements = []
    step = mm(size)
    sw = mm(line_width)
    pw, ph = mm(w), mm(h)

    # Vertical lines
    x = 0.0
    while x <= pw + 0.01:
        elements.append(
            svg.Line(x1=x, y1=0, x2=x, y2=ph, stroke=color, stroke_width=sw)
        )
        x += step

    # Horizontal lines
    y = 0.0
    while y <= ph + 0.01:
        elements.append(
            svg.Line(x1=0, y1=y, x2=pw, y2=y, stroke=color, stroke_width=sw)
        )
        y += step

    return elements


def draw_dots(w: float, h: float, size: float, line_width: float, color: str) -> list:
    """Draw a dot grid pattern within w x h area (all values in mm).

    Dots are placed at every grid intersection. The line_width parameter
    controls the dot diameter.
    """
    elements = []
    step = mm(size)
    r = mm(line_width) / 2  # line_width as dot diameter, so radius is half
    pw, ph = mm(w), mm(h)

    x = 0.0
    while x <= pw + 0.01:
        y = 0.0
        while y <= ph + 0.01:
            elements.append(svg.Circle(cx=x, cy=y, r=r, fill=color))
            y += step
        x += step

    return elements


def draw_lined(w: float, h: float, size: float, line_width: float, color: str) -> list:
    """Draw horizontal ruled lines within w x h area (all values in mm)."""
    elements = []
    step = mm(size)
    sw = mm(line_width)
    pw, ph = mm(w), mm(h)

    y = step  # start one line-height down
    while y <= ph + 0.01:
        elements.append(
            svg.Line(x1=0, y1=y, x2=pw, y2=y, stroke=color, stroke_width=sw)
        )
        y += step

    return elements


def draw_hex(w: float, h: float, size: float, line_width: float, color: str) -> list:
    """Draw a flat-top hexagonal grid within w x h area (all values in mm).

    Size controls the hex side length.
    """
    s = mm(size)
    sw = mm(line_width)
    pw, ph = mm(w), mm(h)

    # Flat-top hex geometry
    hex_w = s * 2  # width of one hex
    hex_h = s * math.sqrt(3)  # height of one hex
    col_step = hex_w * 0.75
    row_step = hex_h

    path_data = []
    col = 0
    cx = 0.0
    while cx - s <= pw:
        row_offset = hex_h / 2 if col % 2 else 0.0
        cy = row_offset
        while cy - hex_h / 2 <= ph:
            # 6 vertices of flat-top hex centered at (cx, cy)
            pts = []
            for i in range(6):
                angle = math.radians(60 * i)
                px = cx + s * math.cos(angle)
                py = cy + s * math.sin(angle)
                pts.append((px, py))
            path_data.append(svg.M(pts[0][0], pts[0][1]))
            for px, py in pts[1:]:
                path_data.append(svg.L(px, py))
            path_data.append(svg.Z())
            cy += row_step
        cx += col_step
        col += 1

    return [svg.Path(d=path_data, stroke=color, stroke_width=sw, fill="none")]


def draw_iso(w: float, h: float, size: float, line_width: float, color: str) -> list:
    """Draw an isometric grid within w x h area (all values in mm).

    Three families of parallel lines at 0, 60, and -60 degrees.
    Size controls the spacing between parallel lines (measured perpendicular).
    """
    sw = mm(line_width)
    pw, ph = mm(w), mm(h)
    spacing = mm(size)

    elements = []

    # Horizontal lines
    y = 0.0
    while y <= ph + 0.01:
        elements.append(
            svg.Line(x1=0, y1=y, x2=pw, y2=y, stroke=color, stroke_width=sw)
        )
        y += spacing

    # Lines at +60 degrees (rising to upper-right)
    # perpendicular spacing → along-x offset = spacing / sin(60)
    dx = spacing / math.sin(math.radians(60))
    dy_per_dx = math.tan(math.radians(60))

    # Lines going from bottom-left area to upper-right
    start = -ph / dy_per_dx
    x = start
    while x <= pw:
        x1, y1 = x, ph
        x2, y2 = x + ph / dy_per_dx, 0.0
        elements.append(
            svg.Line(x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=sw)
        )
        x += dx

    # Lines at -60 degrees (falling to lower-right)
    x = start
    while x <= pw:
        x1, y1 = x, 0.0
        x2, y2 = x + ph / dy_per_dx, ph
        elements.append(
            svg.Line(x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=sw)
        )
        x += dx

    return elements


DRAW_FNS = {
    "grid": draw_grid,
    "dots": draw_dots,
    "hex": draw_hex,
    "lined": draw_lined,
    "iso": draw_iso,
}


def make_panel(
    draw_fn,
    panel_w_mm: float,
    panel_h_mm: float,
    offset_x: float,
    offset_y: float,
    margin_mm: float,
    size: float,
    line_width: float,
    color: str,
    clip_id: str,
) -> list:
    """Create a clipped, translated panel of grid pattern.

    offset_x, offset_y are in points. panel_w/h and margin are in mm.
    """
    inner_w = panel_w_mm - 2 * margin_mm
    inner_h = panel_h_mm - 2 * margin_mm
    margin_pt = mm(margin_mm)

    pattern_elements = draw_fn(inner_w, inner_h, size, line_width, color)

    clip = svg.ClipPath(
        id=clip_id,
        elements=[svg.Rect(x=0, y=0, width=mm(inner_w), height=mm(inner_h))],
    )

    group = svg.G(
        transform=[svg.Translate(offset_x + margin_pt, offset_y + margin_pt)],
        elements=[
            svg.Defs(elements=[clip]),
            svg.G(clip_path=f"url(#{clip_id})", elements=pattern_elements),
        ],
    )
    return [group]


def make_page(args) -> svg.SVG:
    """Assemble the full SVG page with the chosen layout."""
    if args.orientation == "landscape":
        page_w_mm, page_h_mm = PAGE_H_MM, PAGE_W_MM
    else:
        page_w_mm, page_h_mm = PAGE_W_MM, PAGE_H_MM

    page_w = mm(page_w_mm)
    page_h = mm(page_h_mm)
    draw_fn = DRAW_FNS[args.type]

    elements = []
    # White background
    elements.append(svg.Rect(x=0, y=0, width=page_w, height=page_h, fill="white"))

    fold_lines = []
    fold_color = "#999999"
    fold_width = mm(0.2)
    fold_dash = f"{mm(2)},{mm(2)}"

    if args.layout == "full":
        elements.extend(
            make_panel(
                draw_fn,
                page_w_mm,
                page_h_mm,
                0,
                0,
                args.margin,
                args.size,
                args.line_width,
                args.color,
                "clip-0",
            )
        )

    elif args.layout == "half":
        half_w = page_w_mm / 2
        for i in range(2):
            ox = mm(half_w) * i
            elements.extend(
                make_panel(
                    draw_fn,
                    half_w,
                    page_h_mm,
                    ox,
                    0,
                    args.margin,
                    args.size,
                    args.line_width,
                    args.color,
                    f"clip-{i}",
                )
            )
        # Vertical fold line at center
        cx = page_w / 2
        fold_lines.append(
            svg.Line(
                x1=cx,
                y1=0,
                x2=cx,
                y2=page_h,
                stroke=fold_color,
                stroke_width=fold_width,
                stroke_dasharray=fold_dash,
            )
        )

    elif args.layout == "quarter":
        half_w = page_w_mm / 2
        half_h = page_h_mm / 2
        for i, (col, row) in enumerate([(0, 0), (1, 0), (0, 1), (1, 1)]):
            ox = mm(half_w) * col
            oy = mm(half_h) * row
            elements.extend(
                make_panel(
                    draw_fn,
                    half_w,
                    half_h,
                    ox,
                    oy,
                    args.margin,
                    args.size,
                    args.line_width,
                    args.color,
                    f"clip-{i}",
                )
            )
        #        # Vertical fold line
        #        cx = page_w / 2
        #        fold_lines.append(
        #            svg.Line(
        #                x1=cx, y1=0, x2=cx, y2=page_h,
        #                stroke=fold_color, stroke_width=fold_width,
        #                stroke_dasharray=fold_dash,
        #            )
        #        )
        #        # Horizontal fold line
        #        cy = page_h / 2
        #        fold_lines.append(
        #            svg.Line(
        #                x1=0, y1=cy, x2=page_w, y2=cy,
        #                stroke=fold_color, stroke_width=fold_width,
        #                stroke_dasharray=fold_dash,
        #            )
        #        )

    elements.extend(fold_lines)

    return svg.SVG(
        width=page_w,
        height=page_h,
        viewBox=svg.ViewBoxSpec(0, 0, page_w, page_h),
        elements=elements,
    )


def _ensure_cairo_lib() -> None:
    """Ensure the cairo shared library is discoverable by cairocffi.

    When running inside an isolated venv (e.g. created by uv), system
    libraries installed via Homebrew or conda may not be on the default
    search path. This probes common locations and updates DYLD_LIBRARY_PATH
    before cairocffi is imported.
    """
    # If ctypes can already find it, nothing to do
    if ctypes.util.find_library("cairo"):
        return

    search_dirs = []

    # Homebrew (macOS)
    try:
        prefix = subprocess.check_output(
            ["brew", "--prefix", "cairo"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        search_dirs.append(os.path.join(prefix, "lib"))
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Common Homebrew lib paths
    for d in ["/opt/homebrew/lib", "/usr/local/lib"]:
        if d not in search_dirs:
            search_dirs.append(d)

    # Conda
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        search_dirs.append(os.path.join(conda_prefix, "lib"))
    # Also check base miniconda/anaconda locations
    home = os.path.expanduser("~")
    for name in ["miniconda3", "miniforge3", "anaconda3"]:
        d = os.path.join(home, name, "lib")
        if d not in search_dirs:
            search_dirs.append(d)

    # Probe for the library
    lib_names = ["libcairo.2.dylib", "libcairo.dylib", "libcairo.so.2", "libcairo.so"]
    for d in search_dirs:
        for lib in lib_names:
            if os.path.isfile(os.path.join(d, lib)):
                existing = os.environ.get("DYLD_LIBRARY_PATH", "")
                if d not in existing:
                    os.environ["DYLD_LIBRARY_PATH"] = (
                        f"{d}:{existing}" if existing else d
                    )
                return

    raise OSError(
        "libcairo was not found in any standard location. "
        "Searched: " + ", ".join(search_dirs)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate printable grid/line paper SVGs for book binding.",
    )
    parser.add_argument(
        "--type",
        choices=["grid", "dots", "hex", "lined", "iso"],
        default="grid",
        help="Grid pattern type (default: grid)",
    )
    parser.add_argument(
        "--size",
        type=float,
        default=5.0,
        help="Grid spacing in mm (default: 5)",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=0.3,
        help="Line width in mm (default: 0.3)",
    )
    parser.add_argument(
        "--color",
        default="#cccccc",
        help="Line color as CSS color (default: #cccccc)",
    )
    parser.add_argument(
        "--orientation",
        choices=["portrait", "landscape"],
        default="portrait",
        help="Page orientation (default: portrait)",
    )
    parser.add_argument(
        "--layout",
        choices=["full", "half", "quarter"],
        default="full",
        help="Page layout: full page, half (2 panels), or quarter (4 panels) (default: full)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=10.0,
        help="Margin around each panel in mm (default: 10)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.svg",
        help="Output file path; use .pdf extension for PDF output (default: output.svg)",
    )
    args = parser.parse_args()

    # Normalize bare hex color values (e.g. "b3b3b3" -> "#b3b3b3")
    c = args.color
    if (
        not c.startswith("#")
        and all(ch in "0123456789abcdefABCDEF" for ch in c)
        and len(c) in (3, 6, 8)
    ):
        args.color = "#" + c

    page = make_page(args)
    svg_str = str(page)

    _, ext = os.path.splitext(args.output)
    if ext.lower() == ".pdf":
        try:
            _ensure_cairo_lib()
            import cairosvg
        except ImportError:
            print(
                "Error: PDF output requires cairosvg. Install it with: pip install cairosvg"
            )
            raise SystemExit(1)
        except OSError as e:
            print(f"Error: cairo system library not found. {e}")
            print("Install it with: brew install cairo")
            raise SystemExit(1)
        cairosvg.svg2pdf(bytestring=svg_str.encode("utf-8"), write_to=args.output)
    else:
        with open(args.output, "w") as f:
            f.write(svg_str)
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
