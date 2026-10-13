"""Three-Layer Validation Demo for epanetparser.

This example demonstrates the three validation layers in order:
1. Structural layer - parser errors surfaced as ValidationIssue with validation_layer="structural"
2. Static layer - core_rules.epanet_core validation rules
3. Simulation layer - hydraulic simulation validation rules (requires WNTR)

See examples/common.py for rendering helpers and examples/6_validation_demo.py for style.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rprint

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import (
    validate,
    ValidationContext,
    ValidationReport,
    Severity,
)
from epanetparser.core.validation.engine import Validator


def render_section(console: Console, number: int, title: str, description: str):
    """Render a section header like other demos."""
    console.print()
    console.rule(f"[bold cyan]{number}. {title}[/bold cyan]")
    if description:
        console.print(f"[dim]{description}[/dim]")


def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]EPANETPARSER THREE-LAYER VALIDATION DEMO[/bold blue]\n"
        "[dim]Demonstrating structural, static, and simulation validation layers",
        border_style="blue",
    ))
    
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "tests" / "data"
    
    # 1. STRUCTURAL LAYER
    render_section(
        console,
        1,
        "Structural Layer (Parser Errors)",
        "Load malformed INP to see parser errors as ValidationIssue with validation_layer='structural'.",
    )
    
    malformed_path = data_dir / "malformed_network.inp"
    console.print(f"   [bold]Loading:[/bold] {malformed_path.relative_to(project_root)}")
    
    # Load with raise_on_parser_error=False to get errors as returned values
    network, errors, warnings = WNTREPANETNetwork.from_file(str(malformed_path), raise_on_parser_error=False)
    console.print(f"   [green]✓[/green] Parsed with raise_on_parser_error=False")
    console.print(f"   [bold]Network returned:[/bold] {network}")
    console.print(f"   [bold]Errors returned:[/bold]")
    if errors:
        for key, err_list in errors.items():
            for err in err_list:
                console.print(f"     - {type(err).__name__}: {err}")
                console.print(f"       error_code: {getattr(err, 'error_code', 'N/A')}")
                console.print(f"       line_number: {getattr(err, 'line_number', 'N/A')}")
                console.print(f"       section: {getattr(err, 'section', 'N/A')}")
                # Show to_validation_issue
                issue = err.to_validation_issue()
                console.print(f"       [cyan]→ to_validation_issue():[/cyan] validation_layer={issue.validation_layer}, code={issue.code}")
                console.print(f"       context: {issue.context}")
    
    # Also show in a ValidationReport
    console.print(f"\n   [bold]As ValidationReport with structural issues:[/bold]")
    report_struct = ValidationReport()
    if errors:
        for _, err_list in errors.items():
            for err in err_list:
                report_struct.add(err.to_validation_issue())
    console.print(f"     is_valid: {report_struct.is_valid}")
    console.print(f"     issues: {len(report_struct)}")
    console.print(f"     validation_layer values: {[i.validation_layer for i in report_struct]}")
    
    # Show JSON snippet
    json_snippet = json.dumps(report_struct.as_dict(), indent=2)
    syntax = Syntax(json_snippet, "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="Structural Issues as JSON", border_style="blue", expand=False))

    # 2. STATIC LAYER
    render_section(
        console,
        2,
        "Static Layer (Core Validation Rules)",
        "Load an invalid network and run validate() to see ERROR and WARNING findings from epanet_core rules.",
    )
    
    invalid_json = data_dir / "invalid_network.json"
    console.print(f"   [bold]Loading:[/bold] {invalid_json.relative_to(project_root)}")
    
    net_static, _, _ = WNTREPANETNetwork.from_file(str(invalid_json))
    console.print(f"   [green]✓[/green] Loaded network: {net_static.name}")
    console.print(f"     Nodes: {len(net_static.nodes)}, Links: {len(net_static.links)}")
    
    # Validate with core ruleset (and optionally milp for more issues)
    ctx = ValidationContext(core="epanet_core")  # default is fine; be explicit
    report_static = validate(net_static, ctx)
    console.print(f"\n   [bold]Validation results (epanet_core):[/bold]")
    console.print(f"     is_valid: {report_static.is_valid}")
    console.print(f"     Total issues: {len(report_static)}")
    console.print(f"     Errors: {len(report_static.errors)}")
    console.print(f"     Warnings: {len(report_static.warnings)}")
    console.print(f"     Info: {len(report_static.info)}")
    
    # Group by severity
    console.print(f"\n   [bold]ERROR + WARNING findings grouped by severity:[/bold]")
    for severity in [Severity.ERROR, Severity.WARNING]:
        issues = report_static.by_severity(severity)
        if issues:
            console.print(f"\n   [bold]{severity.name}[/bold] ({len(issues)} issues):")
            for issue in issues[:10]:
                comp = issue.component_name or issue.component_type or "network"
                console.print(f"     [{issue.severity}] {comp}: {issue.code} - {issue.message[:90]}")
            if len(issues) > 10:
                console.print(f"     ... and {len(issues) - 10} more")
    
    # Group by ruleset
    console.print(f"\n   [bold]Issues by ruleset:[/bold]")
    by_ruleset = defaultdict(int)
    for issue in report_static:
        by_ruleset[issue.ruleset_key] += 1
    for rs, count in sorted(by_ruleset.items()):
        console.print(f"     {rs}: {count} issues")

    # 3. SIMULATION LAYER
    render_section(
        console,
        3,
        "Simulation Layer (Hydraulic Rules)",
        "Run hydraulic simulation and apply hydraulic ruleset; requires WNTR with [simulation] extra.",
    )
    
    sim_failing_path = data_dir / "simulation_failing_network.inp"
    console.print(f"   [bold]Loading:[/bold] {sim_failing_path.relative_to(project_root)}")
    
    net_sim, _, _ = WNTREPANETNetwork.from_file(str(sim_failing_path))
    console.print(f"   [green]✓[/green] Loaded network for simulation")
    
    try:
        import wntr  # noqa: F401
        WNTR_AVAILABLE = True
    except ImportError:
        WNTR_AVAILABLE = False
    
    if not WNTR_AVAILABLE:
        console.print("   [yellow]skipped — install epanetparser[simulation][/yellow]")
    else:
        try:
            wn = net_sim.to_wntr()
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()
            console.print(f"   [green]✓[/green] Hydraulic simulation completed")
            
            report_sim = ValidationReport()
            ctx_sim = ValidationContext(custom=("hydraulic",))
            validator = Validator.from_context(ctx_sim)
            report_sim = validator.validate_simulation(results, report_sim)
            console.print(f"\n   [bold]Simulation validation results (hydraulic):[/bold]")
            console.print(f"     is_valid: {report_sim.is_valid}")
            console.print(f"     Total issues: {len(report_sim)}")
            for issue in report_sim:
                console.print(f"       [{issue.severity}] {issue.code}: {issue.message}")
                console.print(f"       validation_layer: {issue.validation_layer}")
                if issue.simulation_metadata:
                    console.print(f"       simulation_metadata: {issue.simulation_metadata}")
        except Exception as e:
            console.print(f"   [red]Error during simulation validation:[/red] {e}")
            raise
    
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ Three-layer validation demo completed successfully![/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
