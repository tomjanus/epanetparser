"""Generate the README validation images for the three validation layers.

This is a development / documentation tool, not part of the installed
package. It requires **Pillow** (and ``rich``, which is a runtime
dependency) and a handful of monospace / emoji system fonts. It runs the real
``epanetparser`` CLI for one representative model per validation layer,
captures stdout and stderr verbatim together with the process exit status, and
renders each capture as a terminal-style PNG. It also emits an SVG of the same
recorded text using Rich and a Pillow-drawn overview schematic.

The three layers are:

* **structural** -- while an input document is read (``InpParseError``);
* **static** -- simulator-agnostic rules over the parsed
  ``WNTREPANETNetwork`` (``epanet_core`` plus any custom rule sets);
* **simulation** -- post-simulation rules over hydraulic results
  (``@simulation_rule`` and the Pandera schemas).

Run it from the repository root::

    python docs/tools/make_readme_images.py

Use ``--check`` to run the captures and report the asset state without writing
anything. The generator is deterministic: the subprocess is run with a fixed
console width and the Rich console log handler is raised to ``CRITICAL`` so the
wall-clock timestamps that the logger prints never reach the captured output.
The full capture is kept, but each image renders at most ``--max-lines`` output
lines followed by an explicit truncation marker, so the images stay readable.
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

# Repository root: docs/tools/make_readme_images.py -> parents[2].
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "assets"

# Terminal palette.
WINDOW_BG = "#1b1f23"
BODY_BG = "#1b1f23"
TITLE_BG = "#2d333b"
TITLE_FG = "#e6edf3"
BODY_FG = "#d4d4d4"
DIM_FG = "#8b949e"
BORDER = "#30363d"

FONT_SIZE = 15
TITLE_BAR_H = 30
PADDING = 16

_MONO_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
)
_MONO_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
)
_EMOJI_CANDIDATES = (
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
)


def _first_existing(candidates: Sequence[str]) -> Optional[str]:
    """Return the first path in ``candidates`` that exists on disk."""
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _load_mono(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a monospace font, falling back to Pillow's default bitmap font."""
    candidates = _MONO_BOLD_CANDIDATES if bold else _MONO_CANDIDATES
    path = _first_existing(candidates)
    if path is None:
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def _load_emoji() -> Optional[ImageFont.FreeTypeFont]:
    """Load the colour-emoji font, which only exists at its native size."""
    path = _first_existing(_EMOJI_CANDIDATES)
    if path is None:
        return None
    try:
        # NotoColorEmoji is a fixed-size bitmap font; it refuses other sizes.
        return ImageFont.truetype(path, 109)
    except OSError:
        return None


def _is_emoji(char: str) -> bool:
    """Return True for the pictographic characters used in the reports."""
    code = ord(char)
    return 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Capture:
    """One CLI invocation to capture and render."""

    key: str
    title: str
    command: Sequence[str]
    max_lines: Optional[int] = None
    extra_env: Dict[str, str] = field(default_factory=dict)


@dataclass
class Captured:
    """The result of running a capture."""

    capture: Capture
    output: str
    exit_code: int

    @property
    def lines(self) -> List[str]:
        return self.output.splitlines()


def run_command(command: Sequence[str], extra_env: Optional[Dict[str, str]] = None) -> Tuple[str, int]:
    """Run an ``epanetparser`` CLI command and capture stdout and stderr.

    The command is executed with the repository root on ``PYTHONPATH`` so the
    worktree code is exercised even when an editable install points elsewhere.
    A fixed console width and a raised console log level keep the output
    deterministic (the Rich logger otherwise prints a wall-clock timestamp).
    """
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(REPO_ROOT) + (os.pathsep + existing if existing else "")
    env["COLUMNS"] = "80"
    env["DISABLE_PANDERA_IMPORT_WARNING"] = "True"
    env["EPANETPARSER_CONSOLE_LEVEL"] = "CRITICAL"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, "-m", "epanetparser.core.parse", *command],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr, proc.returncode


def capture(spec: Capture) -> Captured:
    """Run ``spec`` and return the captured output and exit status."""
    output, code = run_command(spec.command, spec.extra_env)
    return Captured(capture=spec, output=output, exit_code=code)


def _with_truncation(lines: List[str], max_lines: Optional[int]) -> List[str]:
    """Return at most ``max_lines`` lines, followed by an explicit marker."""
    if max_lines is None or len(lines) <= max_lines:
        return list(lines)
    marker = f"... {len(lines) - max_lines} more lines (run the command to see all)"
    return lines[:max_lines] + [marker]


def _body_lines(captured: Captured) -> List[str]:
    """Build the text recorded in both the PNG and the SVG."""
    header = "$ epanetparser " + " ".join(captured.capture.command)
    body = _with_truncation(captured.lines, captured.capture.max_lines)
    footer = f"[exit status: {captured.exit_code}]"
    return [header, *body, "", footer]


# ---------------------------------------------------------------------------
# PNG rendering
# ---------------------------------------------------------------------------
def _line_pixels(line: str, font: ImageFont.FreeTypeFont, emoji_cell: int) -> float:
    """Return the rendered pixel width of ``line``."""
    width = 0.0
    for char in line:
        width += emoji_cell if _is_emoji(char) else font.getlength(char)
    return width


def render_png(lines: Sequence[str], title: str, out_path: Path) -> None:
    """Render ``lines`` as a terminal-style PNG with a title bar."""
    font = _load_mono(FONT_SIZE)
    title_font = _load_mono(FONT_SIZE - 1, bold=True)
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + 2
    cell_w = font.getlength("M")

    body_lines = list(lines)
    content_lines = body_lines or [""]
    max_cols = max(len(line) for line in content_lines)
    width_px = int(max(_line_pixels(line, font, 2 * cell_w) for line in content_lines))
    body_w = max(width_px, 520) + PADDING * 2
    body_h = line_h * len(content_lines) + PADDING * 2
    total_h = TITLE_BAR_H + body_h

    image = Image.new("RGB", (body_w, total_h), WINDOW_BG)
    draw = ImageDraw.Draw(image)
    # Title bar with rounded top corners.
    radius = 8
    draw.rounded_rectangle(
        (0, 0, body_w, TITLE_BAR_H + radius), radius=radius, fill=TITLE_BG
    )
    draw.rectangle((0, TITLE_BAR_H, body_w, TITLE_BAR_H + radius), fill=TITLE_BG)
    # Traffic-light dots.
    for index, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        cx = 14 + index * 16
        draw.ellipse((cx - 5, TITLE_BAR_H // 2 - 5, cx + 5, TITLE_BAR_H // 2 + 5), fill=colour)
    draw.text((14 + 3 * 16 + 6, 7), title, font=title_font, fill=TITLE_FG)
    draw.line((0, TITLE_BAR_H, body_w, TITLE_BAR_H), fill=BORDER)

    emoji_font = _load_emoji()
    emoji_cache: Dict[str, Image.Image] = {}
    emoji_px = line_h - 2

    y = TITLE_BAR_H + PADDING
    for line in content_lines:
        colour = DIM_FG if line.startswith("...") and "more lines" in line else BODY_FG
        x = PADDING
        run = ""
        for char in line:
            if _is_emoji(char):
                if run:
                    draw.text((x, y), run, font=font, fill=colour)
                    x += font.getlength(run)
                    run = ""
                if emoji_font is not None:
                    tile = emoji_cache.get(char)
                    if tile is None:
                        tile = _emoji_tile(char, emoji_font, emoji_px)
                        emoji_cache[char] = tile
                    if tile is not None:
                        image.paste(tile, (int(x), y), tile)
                x += 2 * cell_w
            else:
                run += char
        if run:
            draw.text((x, y), run, font=font, fill=colour)
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "PNG", optimize=True)


def _emoji_tile(char: str, emoji_font: ImageFont.FreeTypeFont, size: int) -> Optional[Image.Image]:
    """Render a colour emoji into an ``size``-pixel RGBA tile."""
    try:
        canvas = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        ImageDraw.Draw(canvas).text((0, 0), char, font=emoji_font, embedded_color=True)
    except Exception:
        return None
    bbox = canvas.getbbox()
    if bbox is None:
        return None
    return canvas.crop(bbox).resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------
def render_svg(lines: Sequence[str], title: str, out_path: Path) -> None:
    """Record ``lines`` with Rich and write the corresponding SVG."""
    from rich.console import Console

    width = max((len(line) for line in lines), default=80)
    console = Console(
        record=True,
        file=io.StringIO(),
        width=max(width + 1, 80),
        force_terminal=False,
        color_system=None,
        emoji=False,
        highlight=False,
    )
    for line in lines:
        console.print(line, markup=False, emoji=False, highlight=False)
    svg = console.export_svg(title=title)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------------------
# Overview schematic
# ---------------------------------------------------------------------------
def render_overview(out_path: Path) -> None:
    """Draw the three-layer validation overview schematic as a PNG."""
    title_font = _load_mono(20, bold=True)
    box_font = _load_mono(15, bold=True)
    text_font = _load_mono(12)
    subtitle_font = _load_mono(11)

    canvas_w, canvas_h = 1720, 470
    image = Image.new("RGB", (canvas_w, canvas_h), "#ffffff")
    draw = ImageDraw.Draw(image)

    draw.text((40, 28), "epanetparser: three validation layers", font=title_font, fill="#1f2328")

    boxes = [
        {
            "title": "EPANET input",
            "sub": ".inp  |  WNTR .json",
            "fill": "#eef2f6",
            "border": "#8b949e",
            "tag": "",
        },
        {
            "title": "Parser",
            "sub": "structural layer\nInpParseError",
            "fill": "#fff1e6",
            "border": "#d97706",
            "tag": "Layer 1",
        },
        {
            "title": "WNTREPANETNetwork",
            "sub": "static layer\nepanet_core + custom",
            "fill": "#eaf3ff",
            "border": "#2563eb",
            "tag": "Layer 2",
        },
        {
            "title": "Simulator",
            "sub": "simulation layer\n@simulation_rule + Pandera",
            "fill": "#efe9ff",
            "border": "#7c3aed",
            "tag": "Layer 3",
        },
        {
            "title": "ValidationReport",
            "sub": "one layered report\nvalidation_layer = ...",
            "fill": "#e8f7ee",
            "border": "#15803d",
            "tag": "Unified",
        },
    ]

    box_w, box_h = 288, 188
    gap = 42
    top = 150
    left = 40
    arrow_y = top + box_h // 2

    for index, box in enumerate(boxes):
        x0 = left + index * (box_w + gap)
        x1 = x0 + box_w
        y0 = top
        y1 = y0 + box_h
        draw.rounded_rectangle(
            (x0, y0, x1, y1), radius=14, fill=box["fill"], outline=box["border"], width=2
        )
        if box["tag"]:
            tag_w = int(text_font.getlength(box["tag"])) + 20
            draw.rounded_rectangle(
                (x0 + 14, y0 + 12, x0 + 14 + tag_w, y0 + 34),
                radius=8,
                fill=box["border"],
            )
            draw.text((x0 + 24, y0 + 16), box["tag"], font=subtitle_font, fill="#ffffff")
        draw.text((x0 + 16, y0 + 52), box["title"], font=box_font, fill="#1f2328")
        sub_y = y0 + 82
        for line in box["sub"].split("\n"):
            draw.text((x0 + 16, sub_y), line, font=text_font, fill="#57606a")
            sub_y += 18
        if index < len(boxes) - 1:
            ax0 = x1 + 6
            ax1 = x1 + gap - 6
            draw.line((ax0, arrow_y, ax1, arrow_y), fill="#57606a", width=2)
            draw.polygon(
                [(ax1, arrow_y - 6), (ax1 + 9, arrow_y), (ax1, arrow_y + 6)],
                fill="#57606a",
            )

    note = (
        "Every issue keeps a validation_layer tag and its layer's metadata; all "
        "three layers converge into a single ValidationReport."
    )
    draw.text((40, 386), note, font=text_font, fill="#57606a")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, "PNG", optimize=True)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
CAPTURES: Tuple[Capture, ...] = (
    Capture(
        key="layer1_structural",
        title="Layer 1 - structural",
        command=("validate", "-f", "tests/data/malformed_network.inp", "--no-digest"),
    ),
    Capture(
        key="layer2_static",
        title="Layer 2 - static",
        command=(
            "validate",
            "-f",
            "tests/data/invalid_network.json",
            "--verbose",
            "--no-digest",
        ),
        max_lines=45,
    ),
    Capture(
        key="layer3_simulation",
        title="Layer 3 - simulation",
        command=(
            "validate",
            "-f",
            "tests/data/simulation_failing_network.inp",
            "--simulation-only",
            "--simulation-ruleset",
            "hydraulic",
            "--no-digest",
        ),
        max_lines=55,
    ),
)


def _captures() -> Dict[str, Captured]:
    return {spec.key: capture(spec) for spec in CAPTURES}


def _check(captured: Dict[str, Captured]) -> int:
    """Report the capture and asset state without writing anything."""
    problems = 0
    for spec in CAPTURES:
        item = captured[spec.key]
        print(f"{spec.key}: {len(item.lines)} lines, exit status {item.exit_code}")
        if spec.key.startswith("layer3") and "E_MINIMUM_PRESSURE" not in item.output:
            print(f"  WARNING: {spec.key} does not contain E_MINIMUM_PRESSURE")
            problems += 1
    expected = ["three_layer_overview.png"] + [
        f"{spec.key}{suffix}" for spec in CAPTURES for suffix in (".png", ".svg")
    ]
    for name in expected:
        path = ASSETS_DIR / name
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = "ok" if exists and size > 0 else "MISSING" if not exists else "EMPTY"
        if status != "ok":
            problems += 1
        print(f"  {name}: {status} ({size} bytes)")
    return 1 if problems else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run captures and report asset state without writing any files",
    )
    args = parser.parse_args(argv)

    captured = _captures()

    if args.check:
        return _check(captured)

    written: List[Path] = []
    for spec in CAPTURES:
        item = captured[spec.key]
        lines = _body_lines(item)
        png = ASSETS_DIR / f"{spec.key}.png"
        svg = ASSETS_DIR / f"{spec.key}.svg"
        render_png(lines, item.capture.title, png)
        render_svg(lines, item.capture.title, svg)
        written.extend((png, svg))

    overview = ASSETS_DIR / "three_layer_overview.png"
    render_overview(overview)
    written.append(overview)

    for path in written:
        print(f"wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
