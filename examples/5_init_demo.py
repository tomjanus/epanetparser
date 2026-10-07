"""Demonstration of parsing and initializing EPANET network models.

This demo shows how to:
- Parse a network from JSON (WNTR format)
- Parse a network from .inp file (via WNTR conversion)
- Create a network programmatically
- Inspect network components (nodes, links, curves, patterns, etc.)
- Access component data and metadata
"""
import sys
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.epanettypes import (
    WNTREPANETNode,
    WNTREPANETLink,
    WNTREPANETCurve,
    WNTREPANETPattern,
    WNTREPANETOptions,
    WNTREPANETSource,
    WNTREPANETControl,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
# pylint: disable-next=wrong-import-order, wrong-import-position
from common import render_section


def main():
    console = Console()
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]Network Initialization & Parsing Demo[/bold yellow]\n"
            "[dim]Parsing from JSON/.inp and creating networks programmatically[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    project_root = Path(__file__).resolve().parent.parent

    render_section(
        console,
        1,
        "Parse from JSON (WNTR Format)",
        "WNTREPANETNetwork.from_file() loads a JSON file exported from WNTR. "
        "Returns a tuple: (network, parser_errors, parser_warnings).",
    )
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    network, parse_errors, parse_warnings = WNTREPANETNetwork.from_file(str(valid_path))

    console.print(f"   [green]✓[/green] Network loaded: {network.name}")
    console.print(f"   [bold]Parser errors:[/bold] {len(parse_errors) if parse_errors else 0}")
    console.print(f"   [bold]Parser warnings:[/bold] {len(parse_warnings) if parse_warnings else 0}")

    render_section(
        console,
        2,
        "Network Overview",
        "Basic network statistics and metadata.",
    )
    console.print(f"   [bold]Name:[/bold] {network.name}")
    console.print(f"   [bold]Version:[/bold] {network.version}")
    console.print(f"   [bold]Comment:[/bold] {network.comment}")
    # References are in network_info
    if network.network_info:
        console.print(f"   [bold]References:[/bold] {network.network_info.references}")
    console.print(f"\n   [bold]Component counts:[/bold]")
    console.print(f"     Nodes: {len(network.nodes)}")
    console.print(f"     Links: {len(network.links)}")
    console.print(f"     Curves: {len(network.curves)}")
    console.print(f"     Patterns: {len(network.patterns)}")
    console.print(f"     Controls: {len(network.controls)}")
    console.print(f"     Sources: {len(network.sources)}")

    render_section(
        console,
        3,
        "Parse from .inp File",
        "WNTR can convert .inp to JSON internally. from_file() handles both.",
    )
    inp_path = project_root / "tests" / "data" / "valid_network.inp"
    if inp_path.exists():
        network_inp, _, _ = WNTREPANETNetwork.from_file(str(inp_path))
        console.print(f"   [green]✓[/green] .inp file loaded: {network_inp.name}")
        console.print(f"     Nodes: {len(network_inp.nodes)}, Links: {len(network_inp.links)}")
    else:
        console.print(f"   [yellow].inp test file not found at {inp_path}[/yellow]")

    render_section(
        console,
        4,
        "Inspecting Nodes",
        "Access node collections and individual node data.",
    )
    console.print(f"   [bold]Total nodes:[/bold] {len(network.nodes)}")
    console.print(f"   [bold]Node types:[/bold]")
    type_counts = {}
    for node in network.nodes:
        ntype = node.type  # Use .type property
        type_counts[ntype] = type_counts.get(ntype, 0) + 1
    for ntype, count in sorted(type_counts.items()):
        console.print(f"     {ntype}: {count}")

    # Show first few nodes of each type
    console.print("\n   [bold]Sample nodes:[/bold]")
    shown = set()
    for node in network.nodes:
        if node.type not in shown and len(shown) < 3:
            shown.add(node.type)
            console.print(f"\n     [cyan]{node.name}[/cyan] ({node.type})")
            console.print(f"       [dim]data keys: {list(node.data.keys())}[/dim]")
            # Show key attributes
            for attr in ['elevation', 'base_head', 'init_level', 'diameter', 'min_level', 'max_level', 'min_volume', 'vol_curve_name', 'emitter_coefficient', 'x', 'y']:
                val = getattr(node, attr, None)
                if val is not None:
                    console.print(f"       {attr}: {val}")

    render_section(
        console,
        5,
        "Inspecting Links",
        "Access link collections and individual link data.",
    )
    console.print(f"   [bold]Total links:[/bold] {len(network.links)}")
    console.print(f"   [bold]Link types:[/bold]")
    type_counts = {}
    for link in network.links:
        ltype = link.type  # Use .type property
        type_counts[ltype] = type_counts.get(ltype, 0) + 1
    for ltype, count in sorted(type_counts.items()):
        console.print(f"     {ltype}: {count}")

    # Show first few links of each type
    console.print("\n   [bold]Sample links:[/bold]")
    shown = set()
    for link in network.links:
        if link.type not in shown and len(shown) < 3:
            shown.add(link.type)
            console.print(f"\n     [cyan]{link.name}[/cyan] ({link.type})")
            console.print(f"       [dim]data keys: {list(link.data.keys())}[/dim]")
            for attr in ['length', 'diameter', 'roughness', 'minor_loss', 'status', 'pump_curve_name', 'valve_type', 'setting', 'check_valve']:
                val = getattr(link, attr, None)
                if val is not None:
                    console.print(f"       {attr}: {val}")

    render_section(
        console,
        6,
        "Inspecting Curves",
        "Curve data with points.",
    )
    console.print(f"   [bold]Total curves:[/bold] {len(network.curves)}")
    for curve in network.curves:
        console.print(f"\n     [cyan]{curve.name}[/cyan] ({curve.type})")
        console.print(f"       Points: {len(curve.points)}")
        for i, (x, y) in enumerate(curve.points[:5]):
            console.print(f"       [{i}] x={x}, y={y}")
        if len(curve.points) > 5:
            console.print(f"       ... and {len(curve.points) - 5} more points")

    render_section(
        console,
        7,
        "Inspecting Patterns",
        "Pattern data with multipliers.",
    )
    console.print(f"   [bold]Total patterns:[/bold] {len(network.patterns)}")
    for pattern in network.patterns:
        console.print(f"\n     [cyan]{pattern.name}[/cyan]")
        console.print(f"       Multipliers: {len(pattern.multipliers)}")
        for i, mult in enumerate(pattern.multipliers[:10]):
            console.print(f"       [{i}] {mult}")
        if len(pattern.multipliers) > 10:
            console.print(f"       ... and {len(pattern.multipliers) - 10} more")

    render_section(
        console,
        8,
        "Inspecting Options",
        "Options are grouped by category (time, hydraulic, report, etc.).",
    )
    opts = network.options
    console.print(f"   [bold]Options object:[/bold] {type(opts).__name__}")
    console.print(f"   [bold]Available option groups:[/bold]")
    for group in ['time_options', 'hydraulic_options', 'report_options', 'quality_options',
                  'reaction_options', 'energy_options', 'graphics_options', 'user_options']:
        val = getattr(opts, group, None)
        if val:
            console.print(f"     {group}: {len(val)} keys")
            # Show a few keys
            for k, v in list(val.items())[:3]:
                console.print(f"       {k}: {v}")
            if len(val) > 3:
                console.print(f"       ... and {len(val) - 3} more")

    render_section(
        console,
        9,
        "Inspecting Controls",
        "Control statements with conditions and actions.",
    )
    console.print(f"   [bold]Total controls:[/bold] {len(network.controls)}")
    for control in network.controls:
        console.print(f"\n     [cyan]Control[/cyan] ({control.type})")
        console.print(f"       Condition: {control.condition}")
        console.print(f"       Actions: {control.then_actions}")

    render_section(
        console,
        10,
        "Inspecting Sources",
        "Water quality sources.",
    )
    console.print(f"   [bold]Total sources:[/bold] {len(network.sources)}")
    for source in network.sources:
        console.print(f"\n     [cyan]{source.name}[/cyan]")
        console.print(f"       Type: {source.source_type}")
        console.print(f"       Node: {source.node_name}")
        console.print(f"       Strength: {source.strength}")
        console.print(f"       Pattern: {source.pattern_name}")

    render_section(
        console,
        11,
        "Creating a Network Programmatically",
        "Build a minimal network from JSON using from_json().",
    )
    # Create a simple network JSON
    minimal_json = {
        "version": "wntr-1.4.0",
        "name": "SimpleNetwork",
        "options": {
            "time": {"duration": 86400, "hydraulic_timestep": 3600},
            "hydraulic": {"headloss": "H-W"},
            "report": {"status": "FULL"},
        },
        "nodes": [
            {"name": "J1", "node_type": "Junction", "elevation": 10.0, "base_demand": 0.01},
            {"name": "J2", "node_type": "Junction", "elevation": 15.0, "base_demand": 0.02},
            {"name": "R1", "node_type": "Reservoir", "base_head": 50.0},
        ],
        "links": [
            {
                "name": "P1",
                "link_type": "Pipe",
                "start_node_name": "R1",
                "end_node_name": "J1",
                "length": 100.0,
                "diameter": 0.3,
                "roughness": 130.0,
            },
            {
                "name": "P2",
                "link_type": "Pipe",
                "start_node_name": "J1",
                "end_node_name": "J2",
                "length": 200.0,
                "diameter": 0.2,
                "roughness": 130.0,
            },
        ],
        "curves": [],
        "patterns": [],
        "controls": [],
        "sources": [],
    }

    import json
    network_new, _, _ = WNTREPANETNetwork.from_json(json.dumps(minimal_json))

    console.print(f"   [green]✓[/green] Created network: {network_new.name}")
    console.print(f"     Nodes: {len(network_new.nodes)}")
    console.print(f"     Links: {len(network_new.links)}")
    console.print(f"     Curves: {len(network_new.curves)}")
    console.print(f"     Patterns: {len(network_new.patterns)}")
    console.print(f"     Options: {type(network_new.options).__name__}")

    # Validate the new network
    from epanetparser.core.validation import validate
    report = validate(network_new)
    console.print(f"\n   [bold]Validation:[/bold] Valid={report.is_valid}, Errors={len(report.errors)}, Warnings={len(report.warnings)}")

    render_section(
        console,
        12,
        "Accessing Component Data via .data and .attrs",
        "Each component has .data (raw dict) and .attrs (typed accessors).",
    )
    sample_node = network.nodes[0]
    console.print(f"   [bold]Sample node:[/bold] {sample_node.name}")
    console.print(f"   [bold].data (raw dict):[/bold]")
    syntax = Syntax(str({k: v for k, v in list(sample_node.data.items())[:10]}), "python", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="node.data", border_style="dim"))
    console.print(f"   [bold].attrs (typed properties):[/bold]")
    for attr in ['name', 'type', 'elevation', 'base_demand', 'emitter_coefficient', 'x', 'y']:
        val = getattr(sample_node, attr, None)
        if val is not None:
            console.print(f"     {attr}: {val} ({type(val).__name__})")

    console.print()
    rprint("[bold green]✓ Network initialization demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()