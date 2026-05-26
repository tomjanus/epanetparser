"""Command-line interface for parsing, validating, and converting EPANET network models.

This module provides a comprehensive CLI tool for working with EPANET water distribution
network models. It supports parsing and validation of models in WNTR JSON format,
bidirectional conversion between EPANET INP and WNTR JSON formats, and provides
detailed error and warning reporting with customizable output formats.

The validation framework is built on top of WNTR (Water Network Tool for Resilience)
and provides extensive error and warning reporting for all network components including
nodes (junctions, reservoirs, tanks), links (pipes, pumps, valves), patterns, curves,
sources, and controls.

Subcommands
-----------
validate : Validate EPANET models
    Parse and validate EPANET network models in INP or WNTR JSON format with
    support for custom validation rulesets. Provides detailed error and warning
    reports with configurable output formats (pretty console, JSON, terse).
    
convert : Convert between formats
    Bidirectional conversion between EPANET INP (text) and WNTR JSON formats.
    Supports custom output paths and configurable JSON indentation.
    
info : Display parser information
    Show parser version information and list available validation rulesets.

Key Features
------------
- Supports both EPANET INP and WNTR JSON input formats
- Customizable validation rulesets for different use cases
- Rich console output with colors and emoji (optional)
- JSON output for programmatic processing
- Bidirectional format conversion (INP ↔ JSON)
- Comprehensive error and warning reporting
- SHA-256 digest generation for file verification
- EPANET version targeting for INP output

Usage Examples
--------------
Validate a network model:
    $ epanetparser validate -f network.json
    $ epanetparser validate -f network.inp --use-ruleset milp
    $ epanetparser validate -f network.json --json-output --no-digest

Convert between formats:
    $ epanetparser convert network.inp output.json
    $ epanetparser convert network.json output.inp
    $ epanetparser convert network.inp --indent 4

Display information:
    $ epanetparser info
    $ epanetparser info --list-rulesets
    $ epanetparser --version

Notes
-----
This tool is an adaptation of pywrparser, a toolkit for parsing and validating
Pywr models written by Paul Slavin (https://github.com/pmslavin/pywrparser).

See Also
--------
WNTR: Water Network Tool for Resilience
    https://github.com/USEPA/WNTR
EPANET: EPA's Water Distribution System Modeling Software
    https://www.epa.gov/water-research/epanet
"""
import argparse
import os
import sys
from pathlib import Path
from typing import List
from rich_argparse import RichHelpFormatter
from rich import print as rprint

from epanetparser import rules, __version__
from epanetparser.display import (
    console,
    results_as_json,
    write_results
)
from epanetparser.epanet_types.network import WNTREPANETNetwork
from epanetparser.lib.converter import WNTRINPJSONConverter
from epanetparser.utils import sha256digest

RichHelpFormatter.usage_markup = True


def configure_args(args: List[str]) -> argparse.Namespace:
    """Configure and parse command-line arguments for the EPANET validator.
    
    Sets up an argument parser with three subcommands:
    - validate: Validate an EPANET model with ruleset support
    - convert: Convert between INP and JSON formats
    - info: Display parser information and available rulesets
    
    Args:
        args: List of command-line arguments to parse (typically sys.argv[1:]).
    
    Returns:
        Parsed command-line arguments as an argparse.Namespace object.
    
    Notes:
        If no arguments are provided, prints help message and exits.
    """
    parser = argparse.ArgumentParser(
        prog="epanetparser",
        epilog="The tool is an adaptation of the toolkit for parsing and validating Pywr models written by Paul Slavin, https://github.com/pmslavin/pywrparser, https://pmslavin.github.io/pywrparser\n",
        description="Parser and validator for water distribution network (WDN) models in EPANET format.",
        formatter_class=RichHelpFormatter
    )
    
    # Top-level options
    parser.add_argument("--version",
        action="store_true",
        default=False,
        help="Display the version of %(prog)s"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="available commands",
        metavar=""
    )
    
    # ========== VALIDATE SUBCOMMAND ==========
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an EPANET model and display results",
        formatter_class=RichHelpFormatter
    )
    validate_parser.add_argument("-f", "--filename",
        metavar="<filename>",
        help="File containing an EPANET model in INP or WNTR JSON format",
        type=str,
        required=True
    )
    
    # Validation options for validate command
    validation = validate_parser.add_argument_group("validation options")
    validation.add_argument("--use-ruleset",
        metavar="<ruleset>",
        type=str,
        default=None,
        help="Apply the specified ruleset during parsing"
    )
    validation.add_argument("--raise-on-warning",
        action="store_true",
        default=False,
        help="Raise failures of parsing warnings as exceptions. Implies --raise-on-error"
    )
    validation.add_argument("--raise-on-error",
        action="store_true",
        default=False,
        help="Raise failures of parsing rules as exceptions"
    )
    validation.add_argument("--ignore-warnings",
        action="store_true",
        default=False,
        help="Do not display parsing report if only warnings are present"
    )

    # Display options for validate command
    display = validate_parser.add_argument_group("display options")
    display.add_argument("--json-output",
        action="store_true",
        default=False,
        help="Display parsing report in JSON format for machine reading"
    )
    display.add_argument("--pretty-output",
        action="store_true",
        default=True,
        help="Display parsing report on the console with colour (default)"
    )
    display.add_argument("--no-emoji",
        action="store_true",
        default=False,
        help="Omit emoji in console parsing reports"
    )
    display.add_argument("--no-colour",
        action="store_true",
        default=False,
        help="Omit colour output in console parsing reports. Implies --no-emoji"
    )
    display.add_argument("--terse-report",
        action="store_true",
        default=False,
        help="Display only a terse report for valid networks"
    )
    display.add_argument("--no-digest",
        action="store_true",
        default=False,
        help="Omit sha256 digest in JSON and dict parsing reports"
    )
    
    # ========== CONVERT SUBCOMMAND ==========
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert between EPANET INP and WNTR JSON formats",
        formatter_class=RichHelpFormatter
    )
    convert_parser.add_argument(
        "input_file",
        help="Input file (.inp or .json)"
    )
    convert_parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Optional output filename (default: same name with swapped extension)"
    )
    convert_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces for JSON indentation (default: 2)"
    )
    convert_parser.add_argument(
        "--epanet-version",
        type=float,
        default=2.2,
        help="Version of EPANET to target for INP output (default: 2.2)"
    )
    
    # ========== INFO SUBCOMMAND ==========
    info_parser = subparsers.add_parser(
        "info",
        help="Display information about the EPANET parser",
        formatter_class=RichHelpFormatter
    )
    info_parser.add_argument("-l", "--list-rulesets",
        action="store_true",
        default=False,
        help="Display a list of all available rulesets"
    )

    if len(args) == 0:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args(args)


def handle_validate(args: argparse.Namespace) -> None:
    """Handle the 'validate' command for validating an EPANET model.
    
    Executes the validation workflow for a specified EPANET model file, including
    parsing, applying rulesets, and displaying results based on provided arguments.
    
    Args:
        args: Parsed command-line arguments specific to the 'validate' command.
    
    Raises:
        SystemExit: Exits with code 1 for invalid ruleset.
    """
    filename = args.filename
    raise_error = args.raise_on_error
    raise_warning = args.raise_on_warning
    useemoji = not args.no_emoji if not args.no_colour else False
    include_digest = not args.no_digest
    ruleset = args.use_ruleset

    # Validate ruleset if specified
    if ruleset:
        rulesets = rules.get_rulesets()
        if ruleset not in rulesets:
            rprint(f"No ruleset with key: {ruleset}", file=sys.stderr)
            sys.exit(1)

    # Set console color mode
    if args.no_colour:
        console.no_color = True

    # Parse the network
    network, errors, warnings = WNTREPANETNetwork.from_file(
        filename, 
        raise_on_parser_error=raise_error,
        raise_on_parser_warning=raise_warning,
        ignore_warnings=args.ignore_warnings,
        ruleset=ruleset
    )

    # Display errors and warnings if present
    if errors or warnings:
        if not errors and args.ignore_warnings:
            # Do nothing - warnings are ignored and no errors present
            pass
        elif args.json_output:
            console.print(results_as_json(filename, errors, warnings, include_digest=include_digest))
        else:
            write_results(filename, errors, warnings, use_emoji=useemoji)

    # Display network report if validation succeeded
    if network:
        if args.terse_report:
            report = network.report()
            console.print(report)
        else:
            report = network.verbose_report()
            file_txt = f"[green]File:[/green] [bold blue]{os.path.basename(filename)}[/bold blue]"
            console.print(file_txt)
            if include_digest:
                digest_txt = f"[green]sha256:[/green] [blue]{sha256digest(filename)}[/blue]"
                console.print(digest_txt)

            for prefix, txt in report.items():
                console.print(f"[green]{prefix}:[/green] [blue]{txt}[/blue]")
    

def handle_convert(args: argparse.Namespace) -> None:
    """Handle the 'convert' command for converting between INP and JSON formats.
    
    Executes the conversion workflow for a specified input file, determining the
    conversion direction based on file extensions and writing the output to a
    specified or default location.
    
    Args:
        args: Parsed command-line arguments specific to the 'convert' command.
    
    Raises:
        SystemExit: Exits with code 1 for invalid file extensions or conversion errors.
    """
    input_path = Path(args.input_file)
    output_path = args.output_file
    # Validate input file exists
    if not input_path.exists():
        rprint(f"[red]Error:[/red] Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    # Determine conversion direction
    input_ext = input_path.suffix.lower()
    
    if input_ext == ".inp":
        # INP to JSON
        if output_path is None:
            output_path: Path = WNTRINPJSONConverter.replace_file_suffix(input_path, ".json")
        output_path = Path(output_path)
        generated_file = WNTRINPJSONConverter.inp_to_json(
            inp_path=input_path,
            json_path=output_path,
            indent=args.indent)       
        console.print(f"[green]✓[/green] Converted INP to JSON: [blue]{generated_file}[/blue]")
        
    elif input_ext == ".json":
        # JSON to INP
        if output_path is None:
            output_path: Path = WNTRINPJSONConverter.replace_file_suffix(input_path, ".inp")
        output_path = Path(output_path)
        generated_file = WNTRINPJSONConverter.json_to_inp(
            json_path=input_path,
            inp_path=output_path,
            version=args.epanet_version)  # Default to EPANET 2.2 for conversion
        console.print(f"[green]✓[/green] Converted JSON to INP: [blue]{generated_file}[/blue]")
    else:
        rprint(f"[red]Error:[/red] Unsupported file extension '{input_ext}'. Use .inp or .json", file=sys.stderr)
        sys.exit(1)


def handle_info(args: argparse.Namespace) -> None:
    """Handle the 'info' command for displaying parser information.
    
    Executes the information display workflow, including listing available rulesets
    if requested.
    
    Args:
        args: Parsed command-line arguments specific to the 'info' command.
    """
    if args.list_rulesets:
        console.print(rules.describe_rulesets(), end="")
    else:
        # Display general parser information
        console.print(f"[bold]EPANET Parser[/bold] version {__version__}")
        console.print("\nA tool for parsing and validating EPANET network models.")
        console.print("\nUse 'epanetparser info --list-rulesets' to see available validation rulesets.")
        console.print("Use 'epanetparser validate --help' for validation options.")
        console.print("Use 'epanetparser convert --help' for conversion options.")
    

def handle_args(args: argparse.Namespace) -> None:
    """Process parsed command-line arguments and dispatch to appropriate handler.
    
    This function serves as the main dispatcher, routing to the appropriate
    handler based on the subcommand specified in the arguments.
    
    Args:
        args: Parsed command-line arguments from configure_args().
    
    Raises:
        SystemExit: Exits with code 0 for version display.
    """
    # Handle top-level --version flag
    if args.version:
        rprint(__version__)
        sys.exit(0)
    
    # Dispatch to appropriate handler based on subcommand
    if args.command == "validate":
        handle_validate(args)
    elif args.command == "convert":
        handle_convert(args)
    elif args.command == "info":
        handle_info(args)
    else:
        # This shouldn't happen if argparse is configured correctly
        rprint(f"[red]Error:[/red] No command specified. Use --help for usage information.", file=sys.stderr)
        sys.exit(1)


def run() -> None:
    """Main entry point for the EPANET validator CLI.
    
    Parses command-line arguments and executes the validation workflow.
    Called when the module is run as a script.
    """
    args = configure_args(sys.argv[1:])
    handle_args(args)


if __name__ == "__main__":
    run()
