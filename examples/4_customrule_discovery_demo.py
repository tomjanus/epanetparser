"""Demonstration of custom ruleset discovery and how it differs from core rulesets.

This demo shows how to:
- Discover and list custom rulesets
- Inspect the MILP custom ruleset details
- Understand how custom rulesets add constraints on top of core rules
- Compare core vs custom ruleset rules
"""
import sys
from pathlib import Path
from collections import defaultdict
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from epanetparser.core.validation import (
    list_rulesets,
    discover_ruleset_modules,
    RuleSetRegistry,
    validate,
)
from epanetparser.core.epanettypes.network import WNTREPANETNetwork

sys.path.insert(0, str(Path(__file__).resolve().parent))
# pylint: disable-next=wrong-import-order, wrong-import-position
from common import render_section


def main():
    console = Console()
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]Custom Ruleset Discovery Demo[/bold yellow]\n"
            "[dim]Discovering custom rulesets and understanding their role[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    render_section(
        console,
        1,
        "Listing All Rulesets (Core + Custom)",
        "list_rulesets() returns both core and custom rulesets.",
    )
    rulesets = list_rulesets()

    table = Table(title="All Discovered Rulesets", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Kind", style="green")
    table.add_column("Name", style="white")
    table.add_column("Version", style="magenta")
    table.add_column("Total Rules", justify="right", style="cyan")
    table.add_column("Comp. Rules", justify="right", style="blue")
    table.add_column("Net. Rules", justify="right", style="blue")

    for rs in rulesets:
        kind = "[bold green]core[/bold green]" if rs["is_core"] else "[bold yellow]custom[/bold yellow]"
        table.add_row(
            rs["key"],
            kind,
            rs["name"],
            rs["version"],
            str(rs["rule_count"]),
            str(len(rs["component_rules"])),
            str(len(rs["network_rules"])),
        )
    console.print(table)

    render_section(
        console,
        2,
        "Custom Ruleset Details (MILP)",
        "Inspect the MILP custom ruleset which encodes constraints for "
        "a Mixed Integer Linear Programming pump scheduling tool.",
    )
    registry = RuleSetRegistry()
    milp_rs = registry.get("milp")
    console.print(f"   [green]✓[/green] Custom ruleset: {milp_rs.name} v{milp_rs.version}")
    console.print(f"   [bold]Key:[/bold] {milp_rs.key}")
    console.print(f"   [bold]Module:[/bold] {milp_rs.module_path}")
    console.print(f"   [bold]Is core:[/bold] {milp_rs.is_core}")
    console.print(f"   [bold]Description:[/bold] {milp_rs.description}")
    console.print(f"   [bold]Component rules:[/bold] {len(milp_rs.component_rules)}")
    console.print(f"   [bold]Network rules:[/bold] {len(milp_rs.network_rules)}")

    render_section(
        console,
        3,
        "MILP Rules by Component Type",
        "All MILP rules are component-level (no network rules). "
        "They encode application-specific constraints.",
    )
    by_type = defaultdict(list)
    for spec in milp_rs.component_rules:
        by_type[spec.component_type or "network"].append(spec)

    for comp_type in sorted(by_type.keys()):
        console.print(f"\n   [bold cyan]{comp_type}[/bold cyan] ({len(by_type[comp_type])} rules)")
        for spec in sorted(by_type[comp_type], key=lambda s: s.rule_id):
            severity_style = "red" if spec.severity.name == "ERROR" else "yellow"
            console.print(
                f"     [{severity_style}]{spec.severity.name}[/{severity_style}] "
                f"{spec.rule_id} ({spec.code})"
            )
            if spec.attribute:
                console.print(f"        [dim]Attribute: {spec.attribute}[/dim]")
            if spec.description:
                console.print(f"        [dim]{spec.description[:100]}[/dim]")

    render_section(
        console,
        4,
        "Core vs Custom: Key Differences",
        "Core rules check if a model is a well-formed EPANET model. "
        "Custom rules check if a model works with a specific application.",
    )
    console.print("   [bold]Core Ruleset (epanet_core):[/bold]")
    console.print("     • Simulator-agnostic")
    console.print("     • Required component fields (names, types, elevations, etc.)")
    console.print("     • Valid component types (Junction, Reservoir, Tank, Pipe, Pump, Valve)")
    console.print("     • Well-formed curves and patterns")
    console.print("     • Unique component names")
    console.print("     • Resolvable cross-component references")
    console.print("     • Required option groups (time, hydraulic, energy)")

    console.print("\n   [bold]Custom Ruleset (milp):[/bold]")
    console.print("     • Application-specific constraints")
    console.print("     • 24-hour schedule on 1-hour timestep")
    console.print("     • 2-hour pattern timestep (12 multipliers per pattern)")
    console.print("     • Demand-driven analysis (DDA) with fixed demands")
    console.print("     • Head loss: D-W or H-W only (not C-M)")
    console.print("     • No valves, check valves, tank volume curves, overflows")
    console.print("     • No emitters, no controls")
    console.print("     • Viscosity = 1.0, Specific gravity = 1.0")
    console.print("     • No pressure unit overrides, no demand charge")
    console.print("     • Simulated in LPS (warns if INP file uses different units)")

    render_section(
        console,
        5,
        "Validation: Core Only vs Core + MILP",
        "The same valid EPANET model passes core but fails MILP "
        "because MILP adds application-specific constraints.",
    )

    # Load valid network
    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    network = WNTREPANETNetwork.from_file(str(valid_path))[0]

    # Core only
    report_core = network.validate()
    console.print(f"\n   [bold]Core only:[/bold]")
    console.print(f"     Valid: {report_core.is_valid}")
    console.print(f"     Errors: {len(report_core.errors)}, Warnings: {len(report_core.warnings)}")

    # Core + MILP
    report_milp = network.validate(["epanet_core", "milp"])
    console.print(f"\n   [bold]Core + MILP:[/bold]")
    console.print(f"     Valid: {report_milp.is_valid}")
    console.print(f"     Errors: {len(report_milp.errors)}, Warnings: {len(report_milp.warnings)}")

    # Show MILP-specific issues
    milp_issues = [i for i in report_milp if i.ruleset_key == "milp"]
    console.print(f"\n   [bold]MILP-specific issues ({len(milp_issues)}):[/bold]")
    for issue in milp_issues[:10]:
        console.print(f"     [{issue.severity}] {issue.component_name}: {issue.code}")
    if len(milp_issues) > 10:
        console.print(f"     ... and {len(milp_issues) - 10} more")

    render_section(
        console,
        6,
        "Discovering Custom Ruleset Modules Directly",
        "Lower-level discovery for custom rules packages.",
    )
    modules = discover_ruleset_modules(["epanetparser.custom_rules"])
    console.print(f"   [green]✓[/green] Discovered custom modules: {list(modules.keys())}")
    for key, module in modules.items():
        console.print(f"   [bold]{key}[/bold] -> {module.__name__}")
        console.print(f"      Name: {module.__ruleset_name__}")
        console.print(f"      Version: {module.__version__}")
        console.print(f"      Is core: {getattr(module, '__is_core__', False)}")
        if hasattr(module, '__description__'):
            console.print(f"      Description: {module.__description__[:100]}")

    render_section(
        console,
        7,
        "How Custom Rulesets Are Structured",
        "A custom ruleset is a plain Python module that declares metadata "
        "and defines rules with @rule decorators. No inheritance, no patching.",
    )
    console.print("   [bold]Required module attributes:[/bold]")
    console.print("     __key__ = 'milp'                    # Stable identifier")
    console.print("     __ruleset_name__ = 'MILP ruleset'   # Human-readable name")
    console.print("     __version__ = '0.2.0'               # Semantic version")
    console.print("     __description__ = '...'              # What it checks")
    console.print("     (no __is_core__ attribute)           # Absence = custom")
    console.print("\n   [bold]Rules are defined with @rule decorator:[/bold]")
    console.print("     @rule(\"WNTREPANETPattern\", code=\"E_MILP_PATTERN_LENGTH\", attribute=\"multipliers\")")
    console.print("     def rule_pattern_length(pattern): ...")
    console.print("\n   [bold]Warnings use severity=Severity.WARNING:[/bold]")
    console.print("     @rule(OPTIONS, code=\"W_MILP_INPFILE_UNITS\", severity=Severity.WARNING, ...)")
    console.print("     def warn_inpfile_units(options): ...")

    console.print()
    rprint("[bold green]✓ Custom ruleset discovery demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()