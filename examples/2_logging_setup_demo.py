"""Demonstration of Rich logging setup and configuration-driven initialization.

This demo mirrors the visual style of ``config_demo.py`` and shows how to:
- load the ``logging`` section from the central config,
- instantiate ``LoggingConfig`` from that dictionary,
- configure console and rotating-file logging,
- inspect resulting file log output.
"""
import sys
import os
import tempfile
from pathlib import Path
import yaml
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from epanetparser.core.config import ConfigLoader
from epanetparser.core.logger_setup import (
    ENV_PREFIX,
    LoggingConfig,
    configure_logging,
    get_logger,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
# pylint: disable-next=wrong-import-order, wrong-import-position
from common import render_section


def main():
    console = Console()
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]Logging setup demo[/bold yellow]\n"
            "[dim]Loading logging settings from config and applying Rich logging[/dim]",
            border_style="bright_blue",
        )
    )
    console.print()

    manager = ConfigLoader()
    config = manager.load()
    logging_section = config.get("logging", {})

    render_section(
        console,
        3,
        "Preview Logging Configuration",
        "Show a compact YAML preview of the logging section.",
    )
    yaml_output = yaml.dump(logging_section, default_flow_style=False, sort_keys=False)
    yaml_lines = yaml_output.split("\n")[:20]
    yaml_preview = "\n".join(yaml_lines)
    syntax = Syntax(yaml_preview, "yaml", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="logging section", border_style="green"))

    render_section(
        console,
        4,
        "Instantiating LoggingConfig",
        "Create a LoggingConfig instance from the logging config dictionary.",
    )
    logging_config = LoggingConfig.from_dict(logging_section, ignore_unknown=True)
    console.print("   [green]✓[/green] Created LoggingConfig from config section")
    console.print(f"   [bold]Configured level:[/bold] {logging_config.level}")
    console.print(f"   [bold]Configured show_path:[/bold] {logging_config.show_path}")

    render_section(
        console,
        5,
        "Applying Runtime Overrides",
        "Set a temporary environment override and direct output to a temp log file.",
    )
    original_console_level = os.environ.get(f"{ENV_PREFIX}_CONSOLE_LEVEL")
    os.environ[f"{ENV_PREFIX}_CONSOLE_LEVEL"] = "DEBUG"
    console.print(
        f"   [bold]Runtime env override:[/bold] {ENV_PREFIX}_CONSOLE_LEVEL=DEBUG"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        demo_log_path = Path(tmpdir) / "demo_output.log"
        logging_config.logfile = demo_log_path
        logging_config.tracebacks_show_locals = True

        render_section(
            console,
            6,
            "Configuring and Emitting Logs",
            "Configure logging and emit debug, info, warning, and exception records.",
        )
        configure_logging(logging_config)
        log = get_logger("demo_module")

        log.debug("Debug message emitted due to console level override.")
        log.info("Informational log entry from logging demo.")
        log.warning("Warning log entry for demonstration purposes.")

        try:
            _ = 5 / 0
        except ZeroDivisionError:
            log.exception("Captured exception as part of demo output")

        console.print("   [green]✓[/green] Log messages emitted successfully")
        console.print(f"   [bold]Log file path:[/bold] {demo_log_path}")

        render_section(
            console,
            7,
            "Inspecting File Output",
            "Read and display the rotating file handler output in a panel.",
        )
        if demo_log_path.exists():
            file_output = demo_log_path.read_text(encoding="utf-8")
            log_syntax = Syntax(file_output, "text", theme="monokai", line_numbers=False)
            console.print(Panel(log_syntax, title="demo_output.log", border_style="magenta"))
        else:
            console.print("   [yellow]No log file was created[/yellow]")

    if original_console_level is None:
        del os.environ[f"{ENV_PREFIX}_CONSOLE_LEVEL"]
    else:
        os.environ[f"{ENV_PREFIX}_CONSOLE_LEVEL"] = original_console_level

    console.print()
    rprint("[bold green]✓ Logging setup demo completed successfully![/bold green]")


if __name__ == "__main__":
    main()
