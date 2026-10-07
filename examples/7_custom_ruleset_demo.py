"""Demonstration of creating a custom ruleset from scratch.

This demo shows how to:
- Define a custom ruleset module with required metadata
- Write validation rules using @rule decorator
- Use @match to restrict rules to specific component types
- Use @network_rule for cross-component validation
- Use Severity.WARNING for non-fatal checks
- Use RuleViolation for structured error data
- Register and use the custom ruleset with validate()
"""
import sys
from pathlib import Path
from types import ModuleType
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from epanetparser.core.validation import (
    validate,
    Severity,
    rule,
    match,
    network_rule,
    RuleViolation,
    collect_rules,
    RuleSetRegistry,
    ValidationContext,
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
            "[bold yellow]Creating a Custom Ruleset Demo[/bold yellow]\n"
            "[dim]Building a custom ruleset from scratch[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    render_section(
        console,
        1,
        "Custom Ruleset Structure",
        "A custom ruleset is a plain Python module with required metadata "
        "and rule functions decorated with @rule.",
    )

    console.print("   [bold]Required module attributes:[/bold]")
    console.print("     __key__ = 'my_ruleset'              # Unique identifier")
    console.print("     __ruleset_name__ = 'My Ruleset'     # Human-readable name")
    console.print("     __version__ = '1.0.0'               # Semantic version")
    console.print("     __description__ = '...'              # What it checks")
    console.print("     # No __is_core__ = True              # Absence makes it custom")
    console.print()
    console.print("   [bold]Rule decorators:[/bold]")
    console.print("     @rule(\"WNTREPANETNode\", code=\"E_MY_RULE\", attribute=\"field\")")
    console.print("     @match(\"Junction\")  # Optional: restrict to component subtype")
    console.print("     def rule_my_check(node): ...")
    console.print()
    console.print("     @rule(\"WNTREPANETLink\", severity=Severity.WARNING)")
    console.print("     def warn_my_warning(link): ...")
    console.print()
    console.print("     @network_rule(code=\"E_NETWORK_CHECK\")")
    console.print("     def rule_network_check(network): ...  # Receives whole network")

    render_section(
        console,
        2,
        "Defining a Custom Ruleset Module",
        "Create a module with rules for a hypothetical 'SimpleDesign' ruleset "
        "that enforces basic design constraints.",
    )

    # Create the custom ruleset module
    simple_design = ModuleType("simple_design_rules")
    simple_design.__key__ = "simple_design"
    simple_design.__ruleset_name__ = "Simple Design Rules"
    simple_design.__version__ = "1.0.0"
    simple_design.__description__ = "Basic design constraints: min pipe diameter, max velocity, reservoir head range"

    # Define rules
    NODE = "WNTREPANETNode"
    LINK = "WNTREPANETLink"
    OPTIONS = "WNTREPANETOptions"

    @rule(NODE, code="E_SD_RESERVOIR_HEAD", attribute="base_head")
    @match("Reservoir")
    def rule_reservoir_head_range(node):
        """Reservoir base head should be between 10m and 100m."""
        head = node.data.get("base_head")
        assert head is not None, "Reservoir must have base_head"
        assert 10 <= head <= 100, f"Reservoir head {head}m outside range [10, 100]"

    @rule(LINK, code="E_SD_PIPE_DIAMETER", attribute="diameter")
    @match("Pipe")
    def rule_min_pipe_diameter(link):
        """Pipes must have diameter >= 50mm."""
        dia = link.data.get("diameter")
        assert dia is not None, "Pipe must have diameter"
        assert dia >= 0.05, f"Pipe diameter {dia}m < 0.05m minimum"

    @rule(LINK, code="W_SD_PIPE_VELOCITY", attribute="diameter", severity=Severity.WARNING)
    @match("Pipe")
    def warn_pipe_velocity(link):
        """Warn if pipe velocity might exceed 2 m/s (rough check)."""
        # This is a simplified check - real velocity needs flow calculation
        dia = link.data.get("diameter")
        if dia and dia < 0.1:
            # Small pipes more likely to have high velocity
            raise AssertionError(
                f"Pipe {link.name} diameter {dia}m may exceed 2 m/s velocity"
            )

    @rule(OPTIONS, code="E_SD_TIMESTEP", attribute="hydraulic_timestep")
    def rule_design_timestep(options):
        """Design analysis should use hourly or longer timestep."""
        time_opts = options.time_options or {}
        timestep = time_opts.get("hydraulic_timestep")
        assert timestep is not None, "Missing hydraulic_timestep"
        assert timestep >= 3600, f"Timestep {timestep}s < 3600s (1 hour) for design"

    @network_rule(code="E_SD_CONNECTED")
    def rule_network_connected(network):
        """Network should have at least one reservoir or tank."""
        has_source = any(n.type in ("Reservoir", "Tank") for n in network.nodes)
        assert has_source, "Network must have at least one Reservoir or Tank"

    # Attach rules to module
    simple_design.rule_reservoir_head_range = rule_reservoir_head_range
    simple_design.rule_min_pipe_diameter = rule_min_pipe_diameter
    simple_design.warn_pipe_velocity = warn_pipe_velocity
    simple_design.rule_design_timestep = rule_design_timestep
    simple_design.rule_network_connected = rule_network_connected

    # Set __module__ on each function so collect_rules recognizes them
    for func in [rule_reservoir_head_range, rule_min_pipe_diameter, 
                 warn_pipe_velocity, rule_design_timestep, rule_network_connected]:
        func.__module__ = simple_design.__name__

    # Show the module structure
    console.print("   [green]✓[/green] Created module: simple_design_rules")
    console.print(f"     __key__: {simple_design.__key__}")
    console.print(f"     __ruleset_name__: {simple_design.__ruleset_name__}")
    console.print(f"     __version__: {simple_design.__version__}")
    console.print(f"     __description__: {simple_design.__description__}")

    render_section(
        console,
        3,
        "Collecting Rules from the Module",
        "Use collect_rules() to extract rules from a module.",
    )
    comp_rules, net_rules = collect_rules(simple_design)
    console.print(f"   [green]✓[/green] Collected {len(comp_rules)} component rules, {len(net_rules)} network rules")

    table = Table(title="Collected Rules", show_header=True, header_style="bold cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Rule ID", style="white")
    table.add_column("Code", style="green")
    table.add_column("Severity", style="red")
    table.add_column("Component", style="blue")
    table.add_column("Attribute", style="magenta")

    for spec in comp_rules:
        table.add_row(
            "Component",
            spec.rule_id,
            spec.code,
            spec.severity.name,
            spec.component_type or "any",
            spec.attribute or "-"
        )
    for spec in net_rules:
        table.add_row(
            "Network",
            spec.rule_id,
            spec.code,
            spec.severity.name,
            "network",
            spec.attribute or "-"
        )
    console.print(table)

    render_section(
        console,
        4,
        "Using the Custom Ruleset with ValidationContext",
        "Create a ValidationContext with the custom module and validate. "
        "The custom ruleset must be registered in the registry first.",
    )

    # Load a test network
    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    network, _, _ = WNTREPANETNetwork.from_file(str(valid_path))

    # First, build the RuleSet from the module and register it
    from epanetparser.core.validation.registry import RuleSet, RuleSetRegistry
    custom_rs = RuleSet.from_module(simple_design)
    console.print(f"   [green]✓[/green] Built RuleSet: {custom_rs}")

    # Create registry with BOTH core and custom rulesets
    # Discover core rulesets first
    base_registry = RuleSetRegistry()
    base_registry.discover()
    core_rs = base_registry.get("epanet_core")
    
    # Now create a new registry with both
    registry = RuleSetRegistry(rulesets=[core_rs, custom_rs])
    console.print(f"   [bold]Registry contents:[/bold]")
    for rs in registry.all():
        console.print(f"     {rs.key} ({'core' if rs.is_core else 'custom'}): {rs.name}")

    # Create context with core + custom (using the registered key)
    context = ValidationContext(core="epanet_core", custom=["simple_design"])
    context.registry = registry  # Use our custom registry
    report = validate(network, context)

    console.print(f"\n   [bold]Validation result:[/bold] Valid={report.is_valid}")
    console.print(f"   Total issues: {len(report)} (Errors: {len(report.errors)}, Warnings: {len(report.warnings)})")

    # Show custom ruleset issues
    custom_issues = [i for i in report if i.ruleset_key == "simple_design"]
    console.print(f"\n   [bold]Simple Design ruleset issues ({len(custom_issues)}):[/bold]")
    for issue in custom_issues:
        comp = issue.component_name or issue.component_type or "network"
        console.print(f"     [{issue.severity}] {comp}: {issue.code} - {issue.message[:80]}")

    render_section(
        console,
        5,
        "Testing RuleViolation for Structured Data",
        "RuleViolation allows including failing_fields and extra context data.",
    )

    # Create a module with RuleViolation
    structured_module = ModuleType("structured_rules")

    @rule("WNTREPANETLink", code="E_STRUCTURED_PUMP", attribute="pump_curve_name")
    def rule_pump_curve(link):
        """Pump must reference a valid curve."""
        curve_name = link.data.get("pump_curve_name")
        if curve_name:
            # Simulate checking if curve exists
            raise RuleViolation(
                f"Pump '{link.name}' references curve '{curve_name}' which does not exist",
                failing_fields=["pump_curve_name"],
                component_data=link.data,
                curve=curve_name,
                pump=link.name
            )

    rule_pump_curve.__module__ = structured_module.__name__
    structured_module.rule_pump_curve = rule_pump_curve

    # Collect and inspect
    comp_rules2, _ = collect_rules(structured_module)
    spec = comp_rules2[0]
    console.print(f"   Rule: {spec.rule_id}")
    console.print(f"   Code: {spec.code}")
    console.print(f"   Severity: {spec.severity}")

    # Test the rule on a pump
    pump_link = None
    for link in network.links:
        if link.type == "Pump":
            pump_link = link
            break

    if pump_link:
        console.print(f"\n   Testing on pump: {pump_link.name}")
        try:
            spec.func(pump_link)  # Use .func not .rule_func
            console.print("   [green]✓ Rule passed[/green]")
        except RuleViolation as rv:
            console.print(f"   [red]RuleViolation raised:[/red]")
            console.print(f"     Message: {str(rv)}")
            console.print(f"     Failing fields: {rv.failing_fields}")
            console.print(f"     Extra data: {rv.context}")

    render_section(
        console,
        6,
        "Alternative: Registering in Global Registry",
        "You can also add to the default registry for use without explicit context.registry.",
    )

    # The registry we created in section 4 already has the ruleset
    # Show how to use it directly
    console.print("   [bold]Registry from previous section:[/bold]")
    for rs in registry.all():
        console.print(f"     {rs.key} ({'core' if rs.is_core else 'custom'}): {rs.name}")

    # Validate using the registry directly
    report2 = validate(network, context)
    console.print(f"\n   Validation with registry: Valid={report2.is_valid}, Issues={len(report2)}")

    render_section(
        console,
        7,
        "Best Practices for Custom Rulesets",
        "Guidelines for writing maintainable custom rulesets.",
    )
    console.print("   [bold]1. Use descriptive rule IDs and codes[/bold]")
    console.print("     - Code is part of public API (downstream tooling matches on it)")
    console.print("     - Omit code to auto-generate from function name")
    console.print()
    console.print("   [bold]2. Use @match for component-specific rules[/bold]")
    console.print("     - @match(\"Junction\") restricts to junctions only")
    console.print("     - @match(\"Tank\") restricts to tanks only")
    console.print()
    console.print("   [bold]3. Use @network_rule for cross-component checks[/bold]")
    console.print("     - Receives the full network object")
    console.print("     - Can access network.index for name resolution")
    console.print()
    console.print("   [bold]4. Use Severity.WARNING for advisory checks[/bold]")
    console.print("     - Only ERROR severity makes a report invalid")
    console.print("     - Name functions warn_* to auto-assign WARNING severity")
    console.print()
    console.print("   [bold]5. Use defined(component, field) for required fields[/bold]")
    console.print("     - Requires field to have a value, not just be present")
    console.print()
    console.print("   [bold]6. Keep rules focused and single-purpose[/bold]")
    console.print("     - One assertion per rule when possible")
    console.print("     - Clear, actionable error messages")
    console.print()
    console.print("   [bold]7. Place core rules in epanet_core/, custom in custom_rules/[/bold]")
    console.print("     - Core = simulator-agnostic EPANET validity")
    console.print("     - Custom = application-specific constraints")

    console.print()
    rprint("[bold green]✓ Custom ruleset creation demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()