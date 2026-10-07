"""Demonstration of core ruleset discovery and rule introspection.

This demo shows how to:
- Discover and list the core ruleset
- Inspect its metadata and rules
- Use introspection to find rule_* and warn_* methods on component classes
"""
import sys
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from epanetparser.core.validation import (
    list_rulesets,
    discover_ruleset_modules,
    RuleSetRegistry,
    get_rule_methods,
    get_warning_methods,
)
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
            "[bold yellow]Core Ruleset Discovery & Introspection Demo[/bold yellow]\n"
            "[dim]Discovering the core ruleset, its rules, and component validation methods[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    render_section(
        console,
        1,
        "Listing All Discovered Rulesets",
        "Use list_rulesets() to get structured information about all rulesets.",
    )
    rulesets = list_rulesets()
    console.print(f"   [green]✓[/green] Found {len(rulesets)} ruleset(s)")

    table = Table(title="Discovered Rulesets", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="yellow")
    table.add_column("Kind", style="green")
    table.add_column("Name", style="white")
    table.add_column("Version", style="magenta")
    table.add_column("Description", style="dim")
    table.add_column("Rules", justify="right", style="cyan")
    table.add_column("Comp. Rules", justify="right", style="blue")
    table.add_column("Net. Rules", justify="right", style="blue")

    for rs in rulesets:
        kind = "core" if rs["is_core"] else "custom"
        table.add_row(
            rs["key"],
            kind,
            rs["name"],
            rs["version"],
            rs["description"][:60] + "..." if len(rs["description"]) > 60 else rs["description"],
            str(rs["rule_count"]),
            str(len(rs["component_rules"])),
            str(len(rs["network_rules"])),
        )
    console.print(table)

    render_section(
        console,
        2,
        "Core Ruleset Details via Registry",
        "Use RuleSetRegistry for richer access to a specific ruleset.",
    )
    registry = RuleSetRegistry()
    core_rs = registry.get("epanet_core")
    console.print(f"   [green]✓[/green] Core ruleset: {core_rs.name} v{core_rs.version}")
    console.print(f"   [bold]Key:[/bold] {core_rs.key}")
    console.print(f"   [bold]Module:[/bold] {core_rs.module_path}")
    console.print(f"   [bold]Component rules:[/bold] {len(core_rs.component_rules)}")
    console.print(f"   [bold]Network rules:[/bold] {len(core_rs.network_rules)}")

    render_section(
        console,
        3,
        "Core Rules by Component Type",
        "Show component-level rules grouped by the component type they apply to.",
    )
    from collections import defaultdict
    by_type = defaultdict(list)
    for spec in core_rs.component_rules:
        by_type[spec.component_type or "network"].append(spec)

    for comp_type in sorted(by_type.keys()):
        console.print(f"\n   [bold cyan]{comp_type}[/bold cyan] ({len(by_type[comp_type])} rules)")
        for spec in sorted(by_type[comp_type], key=lambda s: s.rule_id):
            severity_style = "red" if spec.severity.name == "ERROR" else "yellow"
            console.print(
                f"     [{severity_style}]{spec.severity.name}[/{severity_style}] "
                f"{spec.rule_id} ({spec.code})"
            )
            if spec.description:
                console.print(f"        [dim]{spec.description[:80]}[/dim]")

    render_section(
        console,
        4,
        "Core Network Rules",
        "Show network-level rules (cross-component validation).",
    )
    for spec in sorted(core_rs.network_rules, key=lambda s: s.rule_id):
        severity_style = "red" if spec.severity.name == "ERROR" else "yellow"
        console.print(
            f"   [{severity_style}]{spec.severity.name}[/{severity_style}] "
            f"{spec.rule_id} ({spec.code})"
        )
        if spec.description:
            console.print(f"      [dim]{spec.description[:80]}[/dim]")

    render_section(
        console,
        5,
        "Introspection: Rule Methods on Component Classes",
        "Note: epanetparser uses decorator-based rules in separate modules (not "
        "method-based rules on classes). get_rule_methods() and "
        "get_warning_methods() return 0 for the current architecture. "
        "They are kept for inspecting classes that might use the method-based style.",
    )

    component_classes = [
        ("WNTREPANETNode", WNTREPANETNode),
        ("WNTREPANETLink", WNTREPANETLink),
        ("WNTREPANETCurve", WNTREPANETCurve),
        ("WNTREPANETPattern", WNTREPANETPattern),
        ("WNTREPANETOptions", WNTREPANETOptions),
        ("WNTREPANETSource", WNTREPANETSource),
        ("WNTREPANETControl", WNTREPANETControl),
    ]

    for name, cls in component_classes:
        rule_methods = get_rule_methods(cls)
        warn_methods = get_warning_methods(cls)
        console.print(f"\n   [bold]{name}[/bold]")
        console.print(f"      [green]Rule methods:[/green] {len(rule_methods)}")
        console.print(f"      [yellow]Warning methods:[/yellow] {len(warn_methods)}")
        if rule_methods:
            for method_name, info in sorted(rule_methods.items()):
                console.print(f"        • {method_name}{info.signature}")
                if info.description:
                    console.print(f"          [dim]{info.description[:80]}[/dim]")
        if warn_methods:
            for method_name, info in sorted(warn_methods.items()):
                console.print(f"        • {method_name}{info.signature}")
                if info.description:
                    console.print(f"          [dim]{info.description[:80]}[/dim]")

    render_section(
        console,
        6,
        "Using discover_ruleset_modules() Directly",
        "Lower-level discovery that returns the raw rule set modules.",
    )
    modules = discover_ruleset_modules(["epanetparser.core_rules"])
    console.print(f"   [green]✓[/green] Discovered modules: {list(modules.keys())}")
    for key, module in modules.items():
        console.print(f"   [bold]{key}[/bold] -> {module.__name__}")
        console.print(f"      Name: {module.__ruleset_name__}")
        console.print(f"      Version: {module.__version__}")
        console.print(f"      Is core: {getattr(module, '__is_core__', False)}")
        if hasattr(module, '__description__'):
            console.print(f"      Description: {module.__description__[:80]}")

    console.print()
    rprint("[bold green]✓ Core ruleset discovery demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()