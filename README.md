# grid-gen

A CLI tool for generating printable grid and line paper as SVG or PDF files, designed for book binding workflows.

## Features

- **Grid types**: square grid, hexagonal grid, lined writing paper, isometric grid
- **Page layouts**: full page, half (2 panels for folding), quarter (4 panels for folding)
- **Orientation**: portrait or landscape
- **Output formats**: SVG and PDF
- **Configurable**: grid spacing, line width, line color, margins

## Installation

```bash
# With uv
uv pip install .

# With PDF support
uv pip install ".[pdf]"

# Or run directly without installing
uv run grid-gen --help
```

PDF output requires the `cairosvg` library and the `cairo` system library. On macOS with Homebrew: `brew install cairo`. With conda: `conda install cairo`.

## Usage

```bash
# Square grid, default settings
grid-gen -o graph.svg

# 7mm lined writing paper in light blue
grid-gen --type lined --size 7 --color "#9999cc" -o lined.pdf

# Hexagonal grid, 8mm hexes
grid-gen --type hex --size 8 -o hex.svg

# Isometric grid
grid-gen --type iso --size 5 -o iso.svg

# Landscape orientation
grid-gen --type grid --orientation landscape -o landscape.svg

# Half-page layout (fold in half for a 5.5x8.5" book)
grid-gen --type grid --layout half -o half.svg

# Quarter-page layout (fold twice for a ~4.25x5.5" book)
grid-gen --type lined --layout quarter --orientation landscape -o quarter.pdf
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--type` | `grid` | `grid`, `hex`, `lined`, or `iso` |
| `--size` | `5` | Grid spacing in mm |
| `--line-width` | `0.3` | Line width in mm |
| `--color` | `#cccccc` | Line color (CSS color or hex value) |
| `--orientation` | `portrait` | `portrait` or `landscape` |
| `--layout` | `full` | `full`, `half`, or `quarter` |
| `--margin` | `10` | Margin around each panel in mm |
| `-o` | `output.svg` | Output path (use `.pdf` for PDF) |

## Page Size

US Letter (8.5 x 11 inches). Panels for half/quarter layouts include dashed fold lines.

## License

MIT

## AI Disclosure

Claude Opus 4.6 was used to create the code and README.md files within this repository.
