"""Demonstration of converting between .inp and JSON formats.

This demo shows how to:
- Convert .inp file to JSON using the CLI
- Convert JSON to .inp using the CLI
- Use the converter API programmatically
- Validate round-trip conversion
- Handle conversion errors
"""
import sys
import json
import tempfile
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from epanetparser.core.epanettypes.network import WNTREPANETNetwork

sys.path.insert(0, str(Path(__file__).resolve().parent))
# pylint: disable-next=wrong-import-order, wrong-import-position
from common import render_section


def main():
    console = Console()
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]Format Conversion Demo[/bold yellow]\n"
            "[dim]Converting between .inp and JSON formats[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    project_root = Path(__file__).resolve().parent.parent
    inp_path = project_root / "tests" / "data" / "valid_network.inp"
    json_path = project_root / "tests" / "data" / "valid_network.json"

    render_section(
        console,
        1,
        "Check Source Files",
        "Verify the test files exist.",
    )
    console.print(f"   [bold].inp file:[/bold] {inp_path}")
    console.print(f"     Exists: {inp_path.exists()}")
    console.print(f"   [bold].json file:[/bold] {json_path}")
    console.print(f"     Exists: {json_path.exists()}")

    render_section(
        console,
        2,
        "Load Network from .inp File",
        "WNTREPANETNetwork.from_file() automatically uses WNTR to convert .inp to JSON.",
    )
    network_inp, parse_errors, parse_warnings = WNTREPANETNetwork.from_file(str(inp_path))
    console.print(f"   [green]✓[/green] Loaded from .inp: {network_inp.name}")
    console.print(f"   Parser errors: {len(parse_errors) if parse_errors else 0}")
    console.print(f"   Parser warnings: {len(parse_warnings) if parse_warnings else 0}")
    console.print(f"   Nodes: {len(network_inp.nodes)}, Links: {len(network_inp.links)}")

    render_section(
        console,
        3,
        "Load Network from JSON File",
        "Direct JSON loading (faster, no conversion needed).",
    )
    network_json, parse_errors, parse_warnings = WNTREPANETNetwork.from_file(str(json_path))
    console.print(f"   [green]✓[/green] Loaded from JSON: {network_json.name}")
    console.print(f"   Parser errors: {len(parse_errors) if parse_errors else 0}")
    console.print(f"   Parser warnings: {len(parse_warnings) if parse_warnings else 0}")
    console.print(f"   Nodes: {len(network_json.nodes)}, Links: {len(network_json.links)}")

    render_section(
        console,
        4,
        "Compare Networks",
        "Verify both loading methods produce equivalent networks.",
    )
    console.print(f"   [bold]Names match:[/bold] {network_inp.name == network_json.name}")
    console.print(f"   [bold]Node count match:[/bold] {len(network_inp.nodes) == len(network_json.nodes)}")
    console.print(f"   [bold]Link count match:[/bold] {len(network_inp.links) == len(network_json.links)}")
    console.print(f"   [bold]Curve count match:[/bold] {len(network_inp.curves) == len(network_json.curves)}")
    console.print(f"   [bold]Pattern count match:[/bold] {len(network_inp.patterns) == len(network_json.patterns)}")

    render_section(
        console,
        5,
        "Export Network to JSON (as_json)",
        "Use network.as_json() to get JSON string representation.",
    )
    json_str = network_json.as_json(indent=2)
    console.print(f"   [green]✓[/green] Generated JSON ({len(json_str)} chars)")
    # Show first 500 chars
    preview = json_str[:500] + "..." if len(json_str) > 500 else json_str
    syntax = Syntax(preview, "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="JSON Preview", border_style="green"))

    render_section(
        console,
        6,
        "Export Network to JSON File",
        "Save JSON to file using as_json() and Path.write_text().",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        output_json = Path(tmpdir) / "network_output.json"
        json_str = network_json.as_json(indent=2)
        output_json.write_text(json_str)
        console.print(f"   [green]✓[/green] Saved to: {output_json}")
        console.print(f"   File size: {output_json.stat().st_size} bytes")

        # Verify by loading back
        network_reload, _, _ = WNTREPANETNetwork.from_file(str(output_json))
        console.print(f"   [bold]Reloaded:[/bold] {network_reload.name}")
        console.print(f"   Nodes: {len(network_reload.nodes)}, Links: {len(network_reload.links)}")

    render_section(
        console,
        7,
        "Export Network to Dictionary (as_dict)",
        "Use network.as_dict() for programmatic access without JSON serialization.",
    )
    net_dict = network_json.as_dict()
    console.print(f"   [bold]Top-level keys:[/bold] {list(net_dict.keys())}")
    console.print(f"   Nodes: {len(net_dict.get('nodes', []))}")
    console.print(f"   Links: {len(net_dict.get('links', []))}")
    console.print(f"   Curves: {len(net_dict.get('curves', []))}")
    console.print(f"   Patterns: {len(net_dict.get('patterns', []))}")

    render_section(
        console,
        8,
        "CLI Conversion: JSON to .inp",
        "Use the epanetparser CLI to convert JSON to .inp format.",
    )
    import subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        output_inp = Path(tmpdir) / "network_output.inp"
        result = subprocess.run([
            sys.executable, "-m", "epanetparser.core.parse", "convert",
            str(json_path),
            str(output_inp)
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            console.print(f"   [green]✓[/green] CLI conversion successful")
            console.print(f"   Output: {output_inp}")
            console.print(f"   File size: {output_inp.stat().st_size} bytes")
            console.print(f"   Stdout: {result.stdout.strip()}")
        else:
            console.print(f"   [red]CLI conversion failed:[/red]")
            console.print(f"     Return code: {result.returncode}")
            console.print(f"     Stderr: {result.stderr.strip()}")

    render_section(
        console,
        9,
        "CLI Conversion: .inp to JSON",
        "Use the epanetparser CLI to convert .inp to JSON format.",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        output_json2 = Path(tmpdir) / "network_output2.json"
        result = subprocess.run([
            sys.executable, "-m", "epanetparser.core.parse", "convert",
            str(inp_path),
            str(output_json2)
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            console.print(f"   [green]✓[/green] CLI conversion successful")
            console.print(f"   Output: {output_json2}")
            console.print(f"   File size: {output_json2.stat().st_size} bytes")
            console.print(f"   Stdout: {result.stdout.strip()}")
        else:
            console.print(f"   [red]CLI conversion failed:[/red]")
            console.print(f"     Return code: {result.returncode}")
            console.print(f"     Stderr: {result.stderr.strip()}")

    render_section(
        console,
        10,
        "Round-trip Conversion Test",
        "Convert .inp -> JSON -> .inp and verify equivalence.",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: .inp -> JSON
        step1_json = Path(tmpdir) / "step1.json"
        result1 = subprocess.run([
            sys.executable, "-m", "epanetparser.core.parse", "convert",
            str(inp_path),
            str(step1_json)
        ], capture_output=True, text=True, cwd=project_root)
        
        if result1.returncode != 0:
            console.print(f"   [red]Step 1 failed:[/red] {result1.stderr.strip()}")
        else:
            # Step 2: JSON -> .inp
            step2_inp = Path(tmpdir) / "step2.inp"
            result2 = subprocess.run([
                sys.executable, "-m", "epanetparser.core.parse", "convert",
                str(step1_json),
                str(step2_inp)
            ], capture_output=True, text=True, cwd=project_root)
            
            if result2.returncode != 0:
                console.print(f"   [red]Step 2 failed:[/red] {result2.stderr.strip()}")
            else:
                # Step 3: Load both and compare
                net_original, _, _ = WNTREPANETNetwork.from_file(str(inp_path))
                net_roundtrip, _, _ = WNTREPANETNetwork.from_file(str(step2_inp))
                
                console.print(f"   [green]✓[/green] Round-trip conversion successful")
                console.print(f"   Original: {len(net_original.nodes)} nodes, {len(net_original.links)} links")
                console.print(f"   Round-trip: {len(net_roundtrip.nodes)} nodes, {len(net_roundtrip.links)} links")
                
                # Compare key attributes
                matches = [
                    ("Name", net_original.name == net_roundtrip.name),
                    ("Nodes", len(net_original.nodes) == len(net_roundtrip.nodes)),
                    ("Links", len(net_original.links) == len(net_roundtrip.links)),
                    ("Curves", len(net_original.curves) == len(net_roundtrip.curves)),
                    ("Patterns", len(net_original.patterns) == len(net_roundtrip.patterns)),
                ]
                for label, match in matches:
                    status = "[green]✓[/green]" if match else "[red]✗[/red]"
                    console.print(f"     {status} {label} match: {match}")

    render_section(
        console,
        11,
        "Error Handling: Unsupported Format",
        "CLI reports errors for unsupported file extensions.",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_output = Path(tmpdir) / "network.txt"
        result = subprocess.run([
            sys.executable, "-m", "epanetparser.core.parse", "convert",
            str(json_path),
            str(bad_output)
        ], capture_output=True, text=True, cwd=project_root)
        
        console.print(f"   Return code: {result.returncode}")
        console.print(f"   Stderr: {result.stderr.strip()}")

    render_section(
        console,
        12,
        "Programmatic Conversion using WNTR",
        "Direct WNTR usage for advanced conversion control.",
    )
    console.print("   [dim]Note: This requires WNTR to be installed separately.[/dim]")
    console.print("   [bold]Example WNTR code:[/bold]")
    wntr_code = '''import wntr

# Load .inp file
wn = wntr.network.WaterNetworkModel('network.inp')

# Save as JSON (WNTR format)
wntr.epanet.io.InpFile().write(wn, 'network.json')

# Or use epanetparser's built-in conversion
from epanetparser.core.epanettypes.network import WNTREPANETNetwork
network = WNTREPANETNetwork.from_file('network.inp')[0]
network.as_json(path='network.json')'''
    syntax = Syntax(wntr_code, "python", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="WNTR Conversion Example", border_style="blue"))

    console.print()
    rprint("[bold green]✓ Format conversion demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()