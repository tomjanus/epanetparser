"""Demonstration of the validation workflow.

This demo shows how to:
- Validate a network with the core ruleset only
- Validate with core + custom rulesets (MILP)
- Inspect validation reports (errors, warnings, info)
- Group issues by severity, component, ruleset
- Export validation results to JSON
- Use the ValidationReport query methods
"""
import sys
import json
from pathlib import Path
from collections import defaultdict
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from epanetparser.core.validation import (
    validate,
    Severity,
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
            "[bold yellow]Validation Workflow Demo[/bold yellow]\n"
            "[dim]Validating networks, inspecting reports, exporting results[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    invalid_path = project_root / "tests" / "data" / "invalid_network.json"

    render_section(
        console,
        1,
        "Load Test Networks",
        "Load both valid and invalid networks for demonstration.",
    )
    valid_network, _, _ = WNTREPANETNetwork.from_file(str(valid_path))
    invalid_network, _, _ = WNTREPANETNetwork.from_file(str(invalid_path))

    console.print(f"   [green]✓[/green] Valid network: {valid_network.name} ({len(valid_network.nodes)} nodes, {len(valid_network.links)} links)")
    console.print(f"   [green]✓[/green] Invalid network: {invalid_network.name} ({len(invalid_network.nodes)} nodes, {len(invalid_network.links)} links)")

    render_section(
        console,
        2,
        "Validate with Core Ruleset Only (Default)",
        "The default validate() call uses only the core ruleset.",
    )
    report_valid = validate(valid_network)
    console.print(f"   [bold]Valid network:[/bold]")
    console.print(f"     is_valid: {report_valid.is_valid}")
    console.print(f"     Total issues: {len(report_valid)}")
    console.print(f"     Errors: {len(report_valid.errors)}")
    console.print(f"     Warnings: {len(report_valid.warnings)}")
    console.print(f"     Info: {len(report_valid.info)}")

    report_invalid_core = validate(invalid_network)
    console.print(f"\n   [bold]Invalid network (core only):[/bold]")
    console.print(f"     is_valid: {report_invalid_core.is_valid}")
    console.print(f"     Total issues: {len(report_invalid_core)}")
    console.print(f"     Errors: {len(report_invalid_core.errors)}")
    console.print(f"     Warnings: {len(report_invalid_core.warnings)}")
    console.print(f"     Info: {len(report_invalid_core.info)}")

    render_section(
        console,
        3,
        "Validate with Core + MILP Custom Ruleset",
        "Add the MILP ruleset to check application-specific constraints.",
    )
    report_invalid_milp = validate(invalid_network, ["epanet_core", "milp"])
    console.print(f"   [bold]Invalid network (core + MILP):[/bold]")
    console.print(f"     is_valid: {report_invalid_milp.is_valid}")
    console.print(f"     Total issues: {len(report_invalid_milp)}")
    console.print(f"     Errors: {len(report_invalid_milp.errors)}")
    console.print(f"     Warnings: {len(report_invalid_milp.warnings)}")
    console.print(f"     Info: {len(report_invalid_milp.info)}")

    # Show ruleset breakdown
    console.print(f"\n   [bold]Issues by ruleset:[/bold]")
    by_ruleset = defaultdict(int)
    for issue in report_invalid_milp:
        by_ruleset[issue.ruleset_key] += 1
    for rs, count in sorted(by_ruleset.items()):
        console.print(f"     {rs}: {count} issues")

    render_section(
        console,
        4,
        "Inspecting Issues - By Severity",
        "Use report.by_severity() to filter issues by severity level.",
    )
    for severity in Severity:
        issues = report_invalid_milp.by_severity(severity)
        if issues:
            console.print(f"\n   [bold]{severity.name}[/bold] ({len(issues)} issues):")
            for issue in issues[:5]:
                comp = issue.component_name or issue.component_type or "network"
                console.print(f"     [{issue.severity}] {comp}: {issue.code} - {issue.message[:80]}")
            if len(issues) > 5:
                console.print(f"     ... and {len(issues) - 5} more")

    render_section(
        console,
        5,
        "Inspecting Issues - By Component",
        "Use report.grouped_by_component() to group issues by component.",
    )
    grouped = report_invalid_milp.grouped_by_component()
    console.print(f"   [bold]Components with issues:[/bold] {len(grouped)}")
    for component, issues in sorted(grouped.items()):
        console.print(f"\n   [cyan]{component}[/cyan] ({len(issues)} issues)")
        for issue in issues[:3]:
            console.print(f"     [{issue.severity}] {issue.code}: {issue.message[:80]}")
        if len(issues) > 3:
            console.print(f"     ... and {len(issues) - 3} more")

    render_section(
        console,
        6,
        "Inspecting Issues - By Ruleset",
        "Filter issues by which ruleset they came from.",
    )
    for rs_key in ["epanet_core", "milp"]:
        issues = [i for i in report_invalid_milp if i.ruleset_key == rs_key]
        if issues:
            console.print(f"\n   [bold]{rs_key}[/bold] ({len(issues)} issues):")
            for issue in issues[:5]:
                comp = issue.component_name or issue.component_type or "network"
                console.print(f"     [{issue.severity}] {comp}: {issue.code}")
            if len(issues) > 5:
                console.print(f"     ... and {len(issues) - 5} more")

    render_section(
        console,
        7,
        "Inspecting Issues - By Code",
        "Use report.by_code() to find specific issue codes.",
    )
    # Find all duplicate name issues
    dup_issues = report_invalid_milp.by_code("E_DUPLICATE_COMPONENT_NAME")
    if dup_issues:
        console.print(f"   [bold]E_DUPLICATE_COMPONENT_NAME[/bold] ({len(dup_issues)} issues):")
        for issue in dup_issues:
            console.print(f"     [{issue.severity}] {issue.component_name}: {issue.message[:80]}")

    # Find all missing curve reference issues
    curve_issues = report_invalid_milp.by_code("E_UNKNOWN_CURVE_REFERENCE")
    if curve_issues:
        console.print(f"\n   [bold]E_UNKNOWN_CURVE_REFERENCE[/bold] ({len(curve_issues)} issues):")
        for issue in curve_issues[:3]:
            console.print(f"     [{issue.severity}] {issue.component_name}: {issue.message[:80]}")

    render_section(
        console,
        8,
        "Accessing Component Data in Issues",
        "Each ValidationIssue includes the full component_data dict.",
    )
    for issue in report_invalid_milp:
        if issue.component_data:
            console.print(f"\n   [bold]Issue: {issue.code}[/bold] ({issue.component_name or issue.component_type})")
            console.print(f"     Component type: {issue.component_type}")
            console.print(f"     Ruleset: {issue.ruleset_key}")
            console.print(f"     Severity: {issue.severity}")
            console.print(f"     Data keys: {list(issue.component_data.keys())}")
            # Show a few key fields
            for key in ["name", "type", "diameter", "elevation", "pump_curve_name", "link_type", "node_type"]:
                if key in issue.component_data:
                    console.print(f"       {key}: {issue.component_data[key]}")
            break  # Just show first one with data

    render_section(
        console,
        9,
        "Export Results as JSON",
        "Use report.as_dict() for programmatic processing or storage.",
    )
    json_output = report_invalid_milp.as_dict()
    console.print(f"   [bold]JSON structure keys:[/bold] {list(json_output.keys())}")
    console.print(f"   is_valid: {json_output['is_valid']}")
    console.print(f"   counts: {json_output['counts']}")

    # Pretty print first 2 issues
    sample = {
        "is_valid": json_output["is_valid"],
        "counts": json_output["counts"],
        "issues": json_output["issues"][:2]
    }
    syntax = Syntax(json.dumps(sample, indent=2), "json", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="ValidationReport JSON (first 2 issues)", border_style="green"))

    render_section(
        console,
        10,
        "Valid Network with Core + MILP",
        "A valid EPANET model may still fail custom ruleset constraints.",
    )
    report_valid_milp = validate(valid_network, ["epanet_core", "milp"])
    console.print(f"   [bold]Valid network + MILP:[/bold]")
    console.print(f"     is_valid: {report_valid_milp.is_valid}")
    console.print(f"     Total issues: {len(report_valid_milp)}")
    console.print(f"     Errors: {len(report_valid_milp.errors)}")
    console.print(f"     Warnings: {len(report_valid_milp.warnings)}")

    milp_issues = [i for i in report_valid_milp if i.ruleset_key == "milp"]
    console.print(f"     MILP-specific issues: {len(milp_issues)}")
    for issue in milp_issues[:5]:
        console.print(f"       [{issue.severity}] {issue.component_name}: {issue.code}")
    if len(milp_issues) > 5:
        console.print(f"       ... and {len(milp_issues) - 5} more")

    render_section(
        console,
        11,
        "Using ValidationContext for Explicit Control",
        "ValidationContext allows explicit ruleset selection and registry access.",
    )
    context = ValidationContext(core="epanet_core", custom=["milp"])
    report = validate(invalid_network, context)
    console.print(f"   [bold]Context rulesets:[/bold] {context.ruleset_keys}")
    console.print(f"   [bold]Validation result:[/bold] Valid={report.is_valid}, Issues={len(report)}")

    # Access registry from context
    registry = context.registry
    console.print(f"\n   [bold]Available core rulesets:[/bold] {registry.core_keys()}")
    console.print(f"   [bold]Available custom rulesets:[/bold] {registry.custom_keys()}")

    core_rs = registry.get("epanet_core")
    console.print(f"\n   [bold]Core ruleset details:[/bold]")
    console.print(f"     Name: {core_rs.name} v{core_rs.version}")
    console.print(f"     Component rules: {len(core_rs.component_rules)}")
    console.print(f"     Network rules: {len(core_rs.network_rules)}")

    console.print()
    rprint("[bold green]✓ Validation workflow demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()