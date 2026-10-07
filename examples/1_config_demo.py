"""Demonstration of the ConfigManager and Config classes for loading and managing
configuration data for epanetparser.
"""
import sys
from pathlib import Path
import yaml
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from epanetparser.core.config import ConfigLoader
sys.path.insert(0, str(Path(__file__).resolve().parent))
# pylint: disable-next=wrong-import-order, wrong-import-position
from common import render_section


def main():
    console = Console()
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]ConfigManager and Config demo[/bold yellow]\n"
            "[dim]Inspecting defaults, user overrides, and serialization[/dim]",
            border_style="bright_blue",
        )
    )

    manager = ConfigLoader()
    render_section(
        console,
        1,
        "Loading Configuration Manager",
        "Initialize the manager and inspect the default and user configuration paths.",
    )
    console.print(f"   [bold]Default config resource:[/bold] {manager.packaged_config_path}")
    console.print(f"   [bold]User config location:[/bold] {manager.config_path}")

    render_section(
        console,
        2,
        "Loading Configuration With User Overrides",
        "Load the merged configuration and confirm the number of available sections.",
    )
    config = manager.load()
    console.print(f"   [green]✓[/green] Configuration loaded successfully")
    console.print(f"   [bold]Total sections:[/bold] {len(config)}")

    render_section(
        console,
        3,
        "Example Configuration Access",
        "Preview the first few configuration sections in a compact YAML view.",
    )
    sample_config = dict(list(config.items())[:3])
    if sample_config:
        yaml_output = yaml.dump(sample_config, default_flow_style=False, sort_keys=False)
        yaml_output = config.to_yaml()  # Use the Config's to_yaml method for consistent formatting
        yaml_lines = yaml_output.split("\n")[:15]
        yaml_preview = "\n".join(yaml_lines)
        syntax = Syntax(yaml_preview, "yaml", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Configuration Sample", border_style="green"))
    else:
        console.print("   [dim]No configuration data available[/dim]")

    render_section(
        console,
        4,
        "Accessing Configuration Values",
        "Inspect a concrete configuration entry and its nested structure.",
    )
    config_keys = list(config.keys())
    if config_keys:
        first_key = config_keys[0]
        value = config[first_key]
        console.print(f"   [bold]Example:[/bold] config['{first_key}']")
        console.print(f"   [bold]Type:[/bold] {type(value).__name__}")
        if isinstance(value, dict):
            console.print(f"   [bold]Keys:[/bold] {list(value.keys())[:5]}")

    render_section(
        console,
        5,
        "Using get() With Defaults",
        "Demonstrate the safe lookup behavior for existing and missing keys.",
    )
    value = config.get("rule_set_discovery")
    console.print(f"   [green]✓[/green] config.get('rule_set_discovery') returned a value")
    missing = config.get("nonexistent_key", "default_value")
    console.print(f"   [bold]Missing key fallback:[/bold] {missing!r}")

    render_section(
        console,
        6,
        "Configuration Immutability",
        "Show that the top-level mapping is immutable while nested structures remain mutable.",
    )
    try:
        config["new_key"] = "value"  # pylint: disable=unsupported-assignment-operation
    except TypeError:
        console.print("   [yellow]✓ Attempting to add a key raised TypeError[/yellow]")
    console.print("   [dim](Nested structures remain mutable.)[/dim]")
    console.print()
    rprint("[bold green]✓ Config demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()
