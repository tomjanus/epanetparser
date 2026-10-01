"""Command-line tool for inspecting the available validation rulesets.

Validation rules are no longer registered as plugins on component classes;
they live in rule sets, found by the same mechanism for core and custom rule
sets alike. This command is the console entry point for looking at what has
been found: which rule sets exist, what is in them, and what a given rule set
requires of a model.

Subcommands
-----------
list
    List the discovered rule sets, marking which is the core ruleset.
show
    List the rules of one rule set, or of a component type within it.
refresh
    Discard cached rule sets and scan again.

Examples
--------
$ epanetparser-plugins list
$ epanetparser-plugins show --ruleset milp
$ epanetparser-plugins show --component WNTREPANETNode --ruleset epanet_core
"""
import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from epanetparser.core.validation import (
    RuleSetRegistry,
    RuleSetSelectionError,
    clear_caches,
)

console = Console()


def list_rulesets(registry: RuleSetRegistry) -> None:
    """Print the discovered rule sets as a table.

    Parameters
    ----------
    registry : RuleSetRegistry
        Registry to read from. Discovery happens on first use.
    """
    rulesets = registry.all()
    if not rulesets:
        console.print("[yellow]No rule sets were discovered.[/yellow]")
        return
    table = Table(title="Validation rule sets", header_style="bold magenta")
    table.add_column("Key", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Version", style="green")
    table.add_column("Component rules", justify="right")
    table.add_column("Network rules", justify="right")
    for ruleset in rulesets:
        table.add_row(
            ruleset.key,
            "core" if ruleset.is_core else "custom",
            ruleset.name,
            ruleset.version,
            str(len(ruleset.component_rules)),
            str(len(ruleset.network_rules)),
        )
    console.print(table)
    console.print(f"\n[dim]{registry.describe()}[/dim]")


def show_ruleset(ruleset_key: str, component: str = None) -> None:
    """Print the rules of one rule set, optionally filtered by component.

    Parameters
    ----------
    ruleset_key : str
        Key of the rule set to show.
    component : Optional[str]
        Show only the rules for this component class, for example
        ``"WNTREPANETNode"``.

    Notes
    -----
    Rules are printed one per line rather than in a table. A rule's code, name,
    target and description together are wider than a terminal, so a table would
    truncate the very fields being looked up.

    Raises
    ------
    SystemExit
        If the rule set has not been discovered.
    """
    registry = RuleSetRegistry()
    try:
        ruleset = registry.get(ruleset_key)
    except RuleSetSelectionError as err:
        console.print(f"[red]{err}[/red]", file=sys.stderr)
        raise SystemExit(1) from None
    kind = "core" if ruleset.is_core else "custom"
    console.print(
        Panel(
            f"[bold]{ruleset.name}[/bold] v{ruleset.version}\n"
            f"[dim]{ruleset.module_path}[/dim]\n\n{ruleset.description}",
            title=f"[bold]{kind} rule set: {ruleset.key}[/bold]",
            border_style="green" if ruleset.is_core else "blue",
        )
    )
    component_rules = [
        spec
        for spec in ruleset.component_rules
        if component is None or spec.component_type == component
    ]
    network_rules = ruleset.network_rules if component is None else []
    for title, specs in (
        ("Component rules", component_rules),
        ("Network rules", network_rules),
    ):
        if not specs:
            continue
        console.print(f"\n[bold]{title} ({len(specs)})[/bold]")
        for spec in specs:
            target = spec.component_type or "network"
            console.print(
                f"  [green]{spec.code}[/green]  [yellow]{spec.rule_id}[/yellow]"
                f"  [dim]({target}, {spec.severity})[/dim]"
            )
            if spec.attribute:
                console.print(f"      [magenta]attribute[/magenta] {spec.attribute}")
            if spec.description:
                console.print(f"      [dim italic]{spec.description}[/dim italic]")


def main() -> None:
    """Configure the command line, then dispatch to a subcommand."""
    parser = argparse.ArgumentParser(
        prog="epanetparser-plugins",
        description="Inspect the validation rule sets available to epanetparser.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="")
    subparsers.add_parser("list", help="List the discovered rule sets")

    show_parser = subparsers.add_parser(
        "show", help="Show the rules of a rule set"
    )
    show_parser.add_argument(
        "--ruleset", required=True, help="Key of the rule set to show"
    )
    show_parser.add_argument(
        "--component",
        default=None,
        help="Show only rules for this component class, e.g. WNTREPANETNode",
    )

    subparsers.add_parser(
        "refresh", help="Discard cached rule sets and scan again"
    )

    args = parser.parse_args(sys.argv[1:])
    if args.command == "list":
        list_rulesets(RuleSetRegistry())
    elif args.command == "show":
        show_ruleset(args.ruleset, args.component)
    elif args.command == "refresh":
        clear_caches()
        list_rulesets(RuleSetRegistry())
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
