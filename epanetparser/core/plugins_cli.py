"""Command-line interface for plugin management."""
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from epanetparser.core import get_plugin_registry, load_plugins


def list_plugins(verbose: bool = False):
    """List all loaded plugins and their statistics.
    
    Parameters
    ----------
    verbose : bool
        If True, show detailed list of all rules and warnings.
    """
    console = Console()
    registry = get_plugin_registry()
    
    # Show loaded plugins
    loaded = registry.list_plugins()
    if loaded:
        console.print(f"\n[bold cyan]Loaded Plugins ({len(loaded)}):[/bold cyan]")
        for plugin_name in sorted(loaded):
            if plugin_name.startswith("builtin:"):
                console.print(f"  • {plugin_name} [dim](built-in)[/dim]")
            else:
                console.print(f"  • {plugin_name} [dim](external)[/dim]")
    else:
        console.print("\n[yellow]No external plugins loaded[/yellow]")
    
    # Show statistics
    stats = registry.get_statistics()
    if not stats:
        console.print("\n[yellow]No validations registered[/yellow]")
        console.print()
        return
    # If statistics are actually available, show them in a table
    console.print(f"\n[bold cyan]Validation Statistics:[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component Type", style="cyan")
    table.add_column("Rules", justify="right", style="green")
    table.add_column("Warnings", justify="right", style="yellow")
    
    total_rules = 0
    total_warnings = 0
    
    for component_type in sorted(stats.keys()):
        rules_count = stats[component_type]["rules"]
        warnings_count = stats[component_type]["warnings"]
        total_rules += rules_count
        total_warnings += warnings_count
        table.add_row(
            component_type,
            str(rules_count),
            str(warnings_count)
        )
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_rules}[/bold]",
        f"[bold]{total_warnings}[/bold]"
    )
    console.print(table)
    
    if not verbose:
        console.print()
        return
    # Show detailed list of all rules and warnings if verbose is True
    console.print(f"\n[bold cyan]Detailed Validation List:[/bold cyan]")
    for component_type in sorted(stats.keys()):
        rules = registry.get_rules(component_type)
        warnings = registry.get_warnings(component_type)
        if rules or warnings:
            console.print(f"\n[bold yellow]{component_type}:[/bold yellow]")
            if rules:
                console.print("  [green]Rules:[/green]")
                for rule_name in sorted(rules.keys()):
                    func = rules[rule_name]
                    doc = func.__doc__ or "No description"
                    console.print(f"    • {rule_name}: [dim]{doc.strip()}[/dim]")
            if warnings:
                console.print("  [yellow]Warnings:[/yellow]")
                for warn_name in sorted(warnings.keys()):
                    func = warnings[warn_name]
                    doc = func.__doc__ or "No description"
                    console.print(f"    • {warn_name}: [dim]{doc.strip()}[/dim]")
    console.print()


def show_component(component_type: str):
    """Show all validations for a specific component type.
    
    Parameters
    ----------
    component_type : str
        Name of the component type to show.
    """
    console = Console()
    registry = get_plugin_registry()
    
    rules = registry.get_rules(component_type)
    warnings = registry.get_warnings(component_type)
    
    if not rules and not warnings:
        console.print(f"\n[yellow]No validations found for {component_type}[/yellow]\n")
        return
    
    console.print(f"\n[bold cyan]Validations for {component_type}:[/bold cyan]\n")
    
    if rules:
        console.print("[bold green]Rules:[/bold green]")
        for rule_name in sorted(rules.keys()):
            func = rules[rule_name]
            doc = func.__doc__ or "No description"
            console.print(Panel(
                doc.strip(),
                title=f"[green]{rule_name}[/green]",
                border_style="green"
            ))
    
    if warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warn_name in sorted(warnings.keys()):
            func = warnings[warn_name]
            doc = func.__doc__ or "No description"
            console.print(Panel(
                doc.strip(),
                title=f"[yellow]{warn_name}[/yellow]",
                border_style="yellow"
            ))
    
    console.print()


def reload_plugins():
    """Reload all plugins."""
    console = Console()
    console.print("\n[cyan]Reloading plugins...[/cyan]")
    count = load_plugins()
    console.print(f"[green]✓ Loaded {count} plugin(s)[/green]\n")


def main():
    """Main CLI entry point."""

    parser = argparse.ArgumentParser(
        description="EPANET Parser Plugin Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  epanetparser-plugins list              # List all plugins and stats
  epanetparser-plugins list --verbose    # Show detailed validation list
  epanetparser-plugins show WNTREPANETLink  # Show validations for links
  epanetparser-plugins reload            # Reload external plugins
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    # List command
    list_parser = subparsers.add_parser("list", help="List all loaded plugins")
    list_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed list of all validations"
    )
    # Show command
    show_parser = subparsers.add_parser("show", help="Show validations for a component")
    show_parser.add_argument(
        "component",
        help="Component type name (e.g., WNTREPANETLink, WNTREPANETNode)"
    )
    # Reload command
    subparsers.add_parser("reload", help="Reload external plugins")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    if args.command == "list":
        list_plugins(verbose=args.verbose)
    elif args.command == "show":
        show_component(args.component)
    elif args.command == "reload":
        reload_plugins()


if __name__ == "__main__":
    main()
