"""Demonstration of ValidationContext for explicit validation control.

This demo shows how to:
- Create ValidationContext with explicit core and custom rulesets
- Use context.registry for ruleset introspection
- Build custom registries for specialized validation
- Use from_any() for flexible context creation
- Validate components and networks with explicit context
"""
import sys
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from epanetparser.core.validation import (
    validate,
    ValidationContext,
    RuleSetRegistry,
    Severity,
    list_rulesets,
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
            "[bold yellow]ValidationContext Demo[/bold yellow]\n"
            "[dim]Explicit control over validation ruleset selection[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    invalid_path = project_root / "tests" / "data" / "invalid_network.json"

    network, _, _ = WNTREPANETNetwork.from_file(str(valid_path))
    invalid_network, _, _ = WNTREPANETNetwork.from_file(str(invalid_path))

    render_section(
        console,
        1,
        "Default ValidationContext (Core Only)",
        "ValidationContext() with no arguments uses the default core ruleset.",
    )
    context = ValidationContext()
    console.print(f"   [bold]Core keys:[/bold] {context.core_keys}")
    console.print(f"   [bold]Custom keys:[/bold] {context.custom}")
    console.print(f"   [bold]All ruleset keys:[/bold] {context.ruleset_keys}")

    report = validate(network, context)
    console.print(f"\n   [bold]Valid network result:[/bold] Valid={report.is_valid}, Issues={len(report)}")

    render_section(
        console,
        2,
        "Explicit Core + Custom Rulesets",
        "Specify exactly which rulesets to use.",
    )
    context = ValidationContext(core="epanet_core", custom=["milp"])
    console.print(f"   [bold]Core keys:[/bold] {context.core_keys}")
    console.print(f"   [bold]Custom keys:[/bold] {context.custom}")
    console.print(f"   [bold]All ruleset keys:[/bold] {context.ruleset_keys}")

    report = validate(invalid_network, context)
    console.print(f"\n   [bold]Invalid network result:[/bold] Valid={report.is_valid}, Issues={len(report)}")
    console.print(f"   Errors: {len(report.errors)}, Warnings: {len(report.warnings)}")

    # Show breakdown by ruleset
    from collections import defaultdict
    by_ruleset = defaultdict(int)
    for issue in report:
        by_ruleset[issue.ruleset_key] += 1
    console.print(f"   [bold]By ruleset:[/bold] {dict(by_ruleset)}")

    render_section(
        console,
        3,
        "Using Registry from Context",
        "Access the ruleset registry through context.registry.",
    )
    context = ValidationContext(core="epanet_core", custom=["milp"])
    registry = context.registry

    console.print(f"   [bold]Available core rulesets:[/bold] {registry.core_keys()}")
    console.print(f"   [bold]Available custom rulesets:[/bold] {registry.custom_keys()}")
    console.print(f"   [bold]All ruleset keys:[/bold] {registry.keys()}")

    # Get detailed info about a ruleset
    core_rs = registry.get("epanet_core")
    console.print(f"\n   [bold]Core ruleset details:[/bold]")
    console.print(f"     Name: {core_rs.name} v{core_rs.version}")
    console.print(f"     Module: {core_rs.module_path}")
    console.print(f"     Component rules: {len(core_rs.component_rules)}")
    console.print(f"     Network rules: {len(core_rs.network_rules)}")

    milp_rs = registry.get("milp")
    console.print(f"\n   [bold]MILP ruleset details:[/bold]")
    console.print(f"     Name: {milp_rs.name} v{milp_rs.version}")
    console.print(f"     Module: {milp_rs.module_path}")
    console.print(f"     Component rules: {len(milp_rs.component_rules)}")
    console.print(f"     Network rules: {len(milp_rs.network_rules)}")

    render_section(
        console,
        4,
        "Listing Rules in a Ruleset",
        "Inspect individual rules within a ruleset.",
    )
    for rs_key in ["epanet_core", "milp"]:
        rs = registry.get(rs_key)
        console.print(f"\n   [bold]{rs_key} ({'core' if rs.is_core else 'custom'})[/bold]")

        # Component rules by type
        by_type = defaultdict(list)
        for spec in rs.component_rules:
            by_type[spec.component_type or "any"].append(spec)

        for comp_type in sorted(by_type.keys()):
            console.print(f"     [cyan]{comp_type}[/cyan] ({len(by_type[comp_type])} rules)")
            for spec in by_type[comp_type][:3]:
                sev_style = "red" if spec.severity.name == "ERROR" else "yellow"
                console.print(f"       [{sev_style}]{spec.severity.name}[/{sev_style}] {spec.rule_id} ({spec.code})")
            if len(by_type[comp_type]) > 3:
                console.print(f"       ... and {len(by_type[comp_type]) - 3} more")

        # Network rules
        if rs.network_rules:
            console.print(f"     [cyan]network[/cyan] ({len(rs.network_rules)} rules)")
            for spec in rs.network_rules[:3]:
                sev_style = "red" if spec.severity.name == "ERROR" else "yellow"
                console.print(f"       [{sev_style}]{spec.severity.name}[/{sev_style}] {spec.rule_id} ({spec.code})")

    render_section(
        console,
        5,
        "ValidationContext.from_any() for Flexible Input",
        "Create context from various input formats.",
    )
    # From list
    ctx1 = ValidationContext.from_any(["epanet_core", "milp"])
    console.print(f"   From list: core={ctx1.core_keys}, custom={ctx1.custom}")

    # From dict
    ctx2 = ValidationContext.from_any({"core": "epanet_core", "custom": ["milp"]})
    console.print(f"   From dict: core={ctx2.core_keys}, custom={ctx2.custom}")

    # From another context
    ctx3 = ValidationContext.from_any(ctx1)
    console.print(f"   From context: core={ctx3.core_keys}, custom={ctx3.custom}")

    # From string (core only)
    ctx4 = ValidationContext.from_any("epanet_core")
    console.print(f"   From string: core={ctx4.core_keys}, custom={ctx4.custom}")

    # Default (no args)
    ctx5 = ValidationContext.from_any()
    console.print(f"   Default: core={ctx5.core_keys}, custom={ctx5.custom}")

    render_section(
        console,
        6,
        "Building Custom Registry for Specialized Validation",
        "Create a registry with specific rulesets for a use case.",
    )
    # Start with default registry to get core
    base_registry = RuleSetRegistry()
    base_registry.discover()

    # Build a custom registry with only what we need
    custom_registry = RuleSetRegistry(
        rulesets=[
            base_registry.get("epanet_core"),
            base_registry.get("milp"),
        ]
    )

    console.print(f"   [bold]Custom registry contents:[/bold]")
    for rs in custom_registry.all():
        console.print(f"     {rs.key} ({'core' if rs.is_core else 'custom'}): {rs.name}")

    # Use with context
    context = ValidationContext(core="epanet_core", custom=["milp"])
    context.registry = custom_registry

    report = validate(network, context)
    console.print(f"\n   [bold]Validation with custom registry:[/bold]")
    console.print(f"     Valid={report.is_valid}, Issues={len(report)}")

    render_section(
        console,
        7,
        "Validating Individual Components",
        "Validate a single component with a context.",
    )
    # Get a sample node and link
    sample_node = network.nodes[0]
    sample_link = network.links[0]

    context = ValidationContext(core="epanet_core", custom=["milp"])

    # Validate node
    node_report = validate(sample_node, context)
    console.print(f"   [bold]Node {sample_node.name} ({sample_node.type}):[/bold]")
    console.print(f"     Valid={node_report.is_valid}, Issues={len(node_report)}")

    # Validate link
    link_report = validate(sample_link, context)
    console.print(f"   [bold]Link {sample_link.name} ({sample_link.type}):[/bold]")
    console.print(f"     Valid={link_report.is_valid}, Issues={len(link_report)}")

    # Validate network
    net_report = validate(network, context)
    console.print(f"   [bold]Full network:[/bold]")
    console.print(f"     Valid={net_report.is_valid}, Issues={len(net_report)}")

    render_section(
        console,
        8,
        "Error Handling: Invalid Ruleset Selection",
        "ValidationContext and Registry raise clear errors for invalid selections.",
    )
    console.print("   [bold]Examples of errors:[/bold]")

    # No core ruleset
    try:
        ctx = ValidationContext(custom=["milp"])
        ctx.registry = custom_registry
        validate(network, ctx)
    except Exception as e:
        console.print(f"   [red]No core:[/red] {type(e).__name__}: {e}")

    # Unknown ruleset
    try:
        ctx = ValidationContext(core="unknown_ruleset")
        ctx.registry = base_registry
        validate(network, ctx)
    except Exception as e:
        console.print(f"   [red]Unknown ruleset:[/red] {type(e).__name__}: {e}")

    # Core as custom
    try:
        ctx = ValidationContext(core="epanet_core", custom=["epanet_core"])
        ctx.registry = base_registry
        validate(network, ctx)
    except Exception as e:
        console.print(f"   [red]Core as custom:[/red] {type(e).__name__}: {e}")

    render_section(
        console,
        9,
        "Ruleset Registry as_dict() for Serialization",
        "Get structured data about all rulesets for APIs or config.",
    )
    registry = RuleSetRegistry()
    registry.discover()

    for rs in registry.all():
        data = rs.as_dict()
        console.print(f"\n   [bold]{rs.key}[/bold]:")
        console.print(f"     Name: {data['name']} v{data['version']}")
        console.print(f"     Is core: {data['is_core']}")
        console.print(f"     Rules: {data['rule_count']} total")
        console.print(f"     Component rules: {len(data['component_rules'])}")
        console.print(f"     Network rules: {len(data['network_rules'])}")

    # Full list as dict (useful for JSON APIs)
    all_rulesets = list_rulesets()
    console.print(f"\n   [bold]All rulesets (from list_rulesets()):[/bold]")
    for rs in all_rulesets:
        console.print(f"     {rs['key']} ({'core' if rs['is_core'] else 'custom'}): {rs['name']}")

    console.print()
    rprint("[bold green]✓ ValidationContext demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()