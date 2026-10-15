"""MCP validation tools over stdio, in JSON and TOON.

Starts the bundled MCP server as a subprocess, calls the three validation
tools (``validate_network``, ``validate_static``, ``validate_simulation``)
in both output formats, and displays truncated samples of each so the two
formats can be compared side by side. Needs the optional ``agentic`` extra
for the client; ``validate_simulation`` additionally needs the
``simulation`` extra. Missing extras print a skip note, not a traceback.
"""
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import render_section

NETWORK = PROJECT_ROOT / "tests" / "data" / "invalid_network.json"
SIM_NETWORK = PROJECT_ROOT / "tests" / "data" / "simulation_failing_network.inp"

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

import importlib.util

#: Simulation validation runs through WNTR, an optional extra. Detect it by
#: spec so the demo skips cleanly when the extra is absent.
WNTR_AVAILABLE = importlib.util.find_spec("wntr") is not None


async def call_tool(tool: str, arguments: dict) -> str:
    """Call one MCP tool on a fresh stdio server and return its text."""
    import os

    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(PROJECT_ROOT) + (
        os.pathsep + existing if existing else ""
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "epanetparser.core.mcp_server"],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            return result.content[0].text


#: Lines of JSON output shown before truncating: enough for the envelope,
#: the counts, and the first issue.
MAX_JSON_LINES = 24

#: TOON issue rows shown before truncating, after the header block.
MAX_TOON_ROWS = 6


async def show_formats(
    console: Console, tool: str, arguments: dict, number: int
) -> None:
    """Call a tool in both formats and display truncated samples of each."""
    import json as jsonlib

    json_text = await call_tool(tool, {**arguments})
    toon_text = await call_tool(tool, {**arguments, "output_format": "toon"})
    payload = jsonlib.loads(json_text)
    issue_count = len(payload["issues"])

    # Self-check: both formats describe the same report.
    assert f"issues[{issue_count}]" in toon_text
    for issue in payload["issues"]:
        assert issue["code"] in toon_text, issue["code"]
        assert issue["validation_layer"] in toon_text

    saving = (len(json_text) - len(toon_text)) / len(json_text) * 100
    render_section(
        console,
        number,
        tool,
        f"JSON and TOON both report {issue_count} issues.",
    )

    summary = Table(show_header=True, header_style="bold")
    summary.add_column("Format")
    summary.add_column("Issues", justify="right")
    summary.add_column("Chars", justify="right")
    summary.add_row("JSON", str(issue_count), f"{len(json_text):,}")
    summary.add_row(
        "TOON", str(issue_count), f"{len(toon_text):,} ({saving:.0f}% smaller)"
    )
    console.print(summary)

    json_lines = json_text.splitlines()
    json_sample = "\n".join(json_lines[:MAX_JSON_LINES])
    if len(json_lines) > MAX_JSON_LINES:
        json_sample += f"\n... [truncated; {issue_count} issues in total]"
    console.print(
        Panel(
            Syntax(json_sample, "json", theme="monokai", word_wrap=True),
            title=f"JSON sample (first {min(MAX_JSON_LINES, len(json_lines))} "
            f"of {len(json_lines)} lines)",
            border_style="blue",
            expand=False,
        )
    )

    toon_lines = toon_text.splitlines()
    header_end = next(
        index for index, line in enumerate(toon_lines)
        if line.startswith("issues[")
    ) + 1
    shown_rows = min(MAX_TOON_ROWS, issue_count)
    toon_sample = "\n".join(toon_lines[:header_end + shown_rows])
    if issue_count > shown_rows:
        toon_sample += (
            f"\n... [{issue_count - shown_rows} more issues omitted]"
        )
    # Plain Text, not a markup-parsed string: TOON rows contain brackets
    # such as issues[88] that Rich would otherwise read as style tags.
    console.print(
        Panel(
            Text(toon_sample),
            title=f"TOON sample ({shown_rows} of {issue_count} issue rows)",
            border_style="green",
            expand=False,
        )
    )


async def amain() -> None:
    console = Console()
    if not MCP_AVAILABLE:
        console.print("skipped — install epanetparser[agentic] for this demo")
        return

    await show_formats(
        console, "validate_network", {"file_path": str(NETWORK)}, 1
    )
    await show_formats(
        console, "validate_static", {"file_path": str(NETWORK)}, 2
    )

    if not WNTR_AVAILABLE:
        console.print("validate_simulation skipped — "
                      "install epanetparser[simulation] for this step")
    else:
        await show_formats(
            console,
            "validate_simulation",
            {"file_path": str(SIM_NETWORK)},
            3,
        )


def main() -> None:
    asyncio.run(amain())
    print("05_mcp_server_outputs completed")


if __name__ == "__main__":
    main()
