"""Display and formatting utilities for EPANET parser results.

This module provides functions to display parsing results from EPANET network models
in various formats (console output with Rich, JSON, dict). It handles both errors
and warnings from the validation process and formats them for user consumption.
"""
from typing import Tuple
import datetime
import io
import json
import os
from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from epanetparser import rules
from epanetparser.utils import sha256digest

# Instantiate the console upon loading the file
console = Console()

WARN_EMOJI = ":yellow_circle:"
RULE_EMOJI = ":red_circle:"


def write_results(filename: str, errors: dict, warnings: dict, use_emoji: bool = True) -> None:
    """Display parsing results to the console with Rich formatting.
    
    Prints a formatted report of errors and warnings from parsing an EPANET network model.
    The output includes an acknowledgment panel, summary statistics, and detailed error/warning
    messages organized by component type.
    
    Args:
        filename: Path to the parsed EPANET model file.
        errors: Dictionary mapping component types to lists of error objects.
        warnings: Dictionary mapping component types to lists of warning objects.
        use_emoji: If True, use emoji symbols for errors and warnings; otherwise use text labels.
    """
    error_total, warning_total = count_errors_warnings(errors, warnings)
    all_errors_warnings = coalesce_errors_and_warnings(errors, warnings)
    err_plural = "" if error_total == 1 else "s"
    warn_plural = "" if warning_total == 1 else "s"
    console.print("")
    acknowledgment = Align(Panel(
        "This is [bold blue]epanetparser[/bold blue] - a parser for [bold]EPANET[/bold] network models based on [bold green]pywrparser[/bold green]: [italic]`A parser for Pywr json network definitions`[/italic] by Paul Slavin."
        " It works with JSON representations of EPANET models adhering to the JSON format specified by [bold]WNTR[/bold]"
        " - [italic]`A Python package designed to simulate and analyze resilience of water distribution networks.[/italic]`"), align="center")
    console.print(acknowledgment)
    console.print("")
    header = Align(Panel(f"[bold green]Parser results for '{filename}':"
    f" [bold red]{error_total} error{err_plural}[/bold red],"
    f" [bold yellow]{warning_total} warning{warn_plural}", style="blue"), align="center")
    console.print(header)

    net_all = all_errors_warnings.pop("network", [])

    if net_all:
        console.rule("[bold green]Network", style="blue")
        console.print()
    for eow in net_all:
        if isinstance(eow, Warning):
            prefix = WARN_EMOJI if use_emoji else "[WARNING]"
            row = "warning"
        else:
            row = "rule"
            prefix = RULE_EMOJI if use_emoji else "[FAILURE]"

        line = Padding(f"{prefix}  Network {row} -> [white italic]{eow}[/white italic]", (0, 2))
        console.print(line)
    console.print()

    for component, eows in all_errors_warnings.items():
        console.rule(f"[bold green]{component.capitalize()}", style="blue")
        console.print()

        for eow in eows:
            if isinstance(eow, Warning):
                prefix = WARN_EMOJI if use_emoji else eow.desc_text
                row = eow.warning
            else:
                row = eow.rule
                prefix = RULE_EMOJI if use_emoji else eow.desc_text

            eow_line = Padding(
            f"{prefix}  {eow.component} [bold blue]'{row}'[/bold blue] ->"
            f" [white italic]{eow.exc}[/white italic]",
            (0, 2))
            value_line = Padding(f"{eow.valuetext}", (0, 12))
            console.print(eow_line)
            console.print(value_line)

        console.print()
    console.rule(style="blue")


def coalesce_errors_and_warnings(errors: dict, warnings: dict) -> dict:
    """Merge errors and warnings dictionaries into a single dictionary.
    
    Combines error and warning dictionaries by component type. If both errors and warnings
    exist for the same component, they are concatenated into a single list.
    
    Args:
        errors: Dictionary mapping component types to lists of error objects.
        warnings: Dictionary mapping component types to lists of warning objects.
    
    Returns:
        Dictionary mapping component types to combined lists of errors and warnings.
    """
    all_errors_warnings = (errors or {}).copy()
    for component, warns in (warnings or {}).items():
        all_errors_warnings[component] = all_errors_warnings.get(component, []) + warns
    return all_errors_warnings


def count_errors_warnings(errors: dict, warnings: dict) -> Tuple[int, int]:
    """Count the total number of errors and warnings.
    
    Args:
        errors: Dictionary mapping component types to lists of error objects.
        warnings: Dictionary mapping component types to lists of warning objects.
    
    Returns:
        Tuple containing (error_count, warning_count).
    """
    error_total = sum(len(errs) for errs in errors.values()) if errors else 0
    warning_total = sum(len(warns) for warns in warnings.values()) if warnings else 0
    return error_total, warning_total


def results_as_dict(
        filename: str,
        errors: dict,
        warnings: dict, 
        include_digest: bool = True) -> dict:
    """Convert parsing results to a structured dictionary.
    
    Creates a dictionary representation of parsing results including metadata,
    error/warning counts, and detailed error/warning information.
    
    Args:
        filename: Path to the parsed EPANET model file (or StringIO object).
        errors: Dictionary mapping component types to lists of error objects.
        warnings: Dictionary mapping component types to lists of warning objects.
        include_digest: If True, include SHA256 hash of the file in the output.
    
    Returns:
        Dictionary containing structured parsing results with metadata and errors/warnings.
    """
    error_total, warning_total = count_errors_warnings(errors, warnings)
    if isinstance(filename, io.StringIO):
        filename = "stdin"
    fbasename = os.path.basename(filename)
    ruleset = rules.get_ruleset_module(rules.ACTIVE_RULESET_KEY)
    ruleset_name = ruleset.__ruleset_name__ if ruleset else "Default"
    ret = {
        "parse_results": {
            "file": {"name": fbasename},
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ruleset": ruleset_name,
            "errors": error_total,
            "warnings": warning_total
        }
    }
    if include_digest:
        fdigest = sha256digest(filename)
        ret["parse_results"]["file"]["sha256"] = fdigest
    if errors:
        ret["errors"] = {
            component: [err.as_dict() for err in errs]
            for component, errs in errors.items()
        }
    if warnings:
        ret["warnings"] = {
            component: [warn.as_dict() for warn in warns]
            for component, warns in warnings.items()
        }
    return ret


def results_as_json(
        filename: str,
        errors: dict,
        warnings: dict,
        include_digest: bool = True,
        indent: int = 0
    ) -> str:
    """Convert parsing results to a JSON string.
    
    Wrapper around results_as_dict that serializes the output to JSON format.
    
    Args:
        filename: Path to the parsed EPANET model file (or StringIO object).
        errors: Dictionary mapping component types to lists of error objects.
        warnings: Dictionary mapping component types to lists of warning objects.
        include_digest: If True, include SHA256 hash of the file in the output.
        indent: Number of spaces for JSON indentation (0 for compact output).
    
    Returns:
        JSON string representation of the parsing results.
    """
    return json.dumps(
        results_as_dict(filename, errors, warnings, include_digest), 
        indent=indent
    )
