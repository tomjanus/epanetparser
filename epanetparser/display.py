""" """
from typing import Tuple, Dict, Any
import datetime
import io
import json
import os
from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel

# Instantiate the console upon loading the file
console = Console()

WARN_EMOJI = ":yellow_circle:"
RULE_EMOJI = ":red_circle:"


def write_results(filename: str, errors: dict, warnings: dict, use_emoji: bool = True) -> None:
    """ """
    error_total, warning_total = count_errors_warnings(errors, warnings)
    all = coalesce_errors_and_warnings(errors, warnings)
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

    net_all = all.pop("network", [])

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

    for component, eows in all.items():
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
    """ """
    warnings = warnings if warnings else {}
    all_errors_warnings = errors.copy() if errors else {}
    for component, warns in warnings.items():
        comp_errs = all_errors_warnings.get(component, [])
        all_errors_warnings[component] = comp_errs + warns
    return all_errors_warnings


def count_errors_warnings(errors: dict, warnings: dict) -> Tuple[int, int]:
    """ """
    error_total = 0
    warning_total = 0
    if errors:
        for component, errs in errors.items():
            error_total += len(errs)
    if warnings:
        for component, warns in warnings.items():
            warning_total += len(warns)
    return error_total, warning_total


def results_as_dict(filename: str, errors: dict, warnings: dict, include_digest: bool = True) -> dict:
    """ """
    error_total, warning_total = count_errors_warnings(errors, warnings)

    if isinstance(filename, io.StringIO):
        filename = "stdin"
    fbasename = os.path.basename(filename)
    from epanetparser import rules
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
        from epanetparser.utils import sha256digest
        fdigest = sha256digest(filename)
        ret["parse_results"]["file"]["sha256"] = fdigest
    if errors:
        component_errs = {}
        for component, errs in errors.items():
            component_errs[component] = [err.as_dict() for err in errs]
        ret["errors"] = component_errs
    if warnings:
        component_warns = {}
        for component, warns in warnings.items():
            component_warns[component] = [warn.as_dict() for warn in warns]
        ret["warnings"] = component_warns
    return ret


def results_as_json(
        filename: str,
        errors: dict,
        warnings: dict,
        include_digest: bool = True,
        indent: int = 0
    ) -> None:
    """ """
    return json.dumps(results_as_dict(filename, errors, warnings, include_digest), indent=indent)
