"""Command-line interface for parsing, validating, and converting EPANET models.

This module provides a comprehensive CLI tool for working with EPANET water distribution
network models. It supports parsing and validation of models in WNTR JSON format,
bidirectional conversion between EPANET INP and WNTR JSON formats, and provides
detailed error and warning reporting with customizable output formats.

Parsing and validation are separate steps. Parsing builds a model and reports
only structural problems, such as a document that is not valid JSON or that
omits a required section. Validation then applies one core ruleset, plus any
custom rulesets the user selects, and reports what it finds as a structured
report. A model can be valid, invalid, or unvalidated, and the command line
distinguishes those cases.

Static validation is simulator-agnostic: the core ruleset checks that a model
is a well-formed EPANET model, not that any particular tool can simulate it.
Constraints belonging to one application, such as an MILP pump scheduling
formulation, live in custom rulesets and are opted into with ``--ruleset``.

Subcommands
-----------
download-extra : Download extra network files
    Download files from GitHub release using the 'networks' preset. Provides options
    for showing progress and controlling console output.

validate : Validate EPANET models
    Parse and validate EPANET network models in INP or WNTR JSON format with
    support for custom rulesets. Provides detailed error and warning
    reports with configurable output formats (pretty console, JSON, terse).

convert : Convert between formats
    Bidirectional conversion between EPANET INP (text) and WNTR JSON formats.
    Supports custom output paths and configurable JSON indentation.

download : Download network files
    Download network files from Google Drive using presets (e.g., 'networks') or
    manually specify a folder URL and output directory. Presets provide
    quick access to commonly used resources like benchmark networks.

info : Display parser information
    Show parser version information and list available rulesets.

Key Features
------------
- Supports both EPANET INP and WNTR JSON input formats
- Simulator-agnostic core ruleset, plus any number of custom rulesets
- Structured validation results: stable issue codes, severities and context
- Rich console output with colors and emoji (optional)
- JSON output for programmatic processing
- Bidirectional format conversion (INP ↔ JSON)
- SHA-256 digest generation for file verification
- EPANET version targeting for INP output

Exit Status
-----------
0
    The model parsed and validated with no errors, or the command produced the
    output that was asked for.
1
    Bad usage: an unknown ruleset, or an unreadable input file with
    ``--raise-on-error``.
2
    The model parsed but is invalid, or has warnings and ``--raise-on-warning``
    was given.

Usage Examples
--------------
Validate a network model:
    $ epanetparser validate -f network.json
    $ epanetparser validate -f network.inp --ruleset milp
    $ epanetparser validate -f network.inp --ruleset milp --ruleset project
    $ epanetparser validate -f network.json --json-output --no-digest
    $ epanetparser validate -f network.json --list-rulesets

Convert between formats:
    $ epanetparser convert network.inp output.json
    $ epanetparser convert network.json output.inp
    $ epanetparser convert network.inp --indent 4

Download files:
    $ epanetparser download networks
    $ epanetparser download "https://drive.google.com/.../folder_id" ./my_data
    $ epanetparser download networks --mode files --quiet

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
import json
import os
import sys
from pathlib import Path
from typing import List
from rich_argparse import RichHelpFormatter
from rich import print as rprint

from epanetparser.core import __version__, console
from epanetparser.core.display import results_as_json, write_results
from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.lib.converter import WNTRINPJSONConverter
from epanetparser.core.utils import sha256digest
from epanetparser.core.download import download_networks
from epanetparser.core.environment import PackageResolver
from epanetparser.core.validation import (
    RuleSetRegistry,
    RuleSetSelectionError,
    ValidationContext,
    ValidationReport,
)

RichHelpFormatter.usage_markup = True


def configure_args(args: List[str]) -> argparse.Namespace:
    """Configure and parse command-line arguments for the EPANET validator.
    
    Sets up an argument parser with four subcommands:
    - validate: Validate an EPANET model with ruleset support
    - convert: Convert between INP and JSON formats
    - download: Download files from Google Drive (presets or manual)
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
        description="Parser and validator of EPANET water distribution network models.",
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
    
    # ========== DOWNLOAD SUBCOMMAND ==========
    download_parser = subparsers.add_parser(
        "download-extra",
        help="Download additional networks from GitHub release for testing and benchmarking",
        formatter_class=RichHelpFormatter
    )
    
    download_parser.add_argument("--progress",
        action="store_true",
        default=True,
        help="Show progress when downloading files."
    ) 

    download_parser.add_argument("--quiet",
        action="store_true",
        default=False,
        help="Display parsing report on the console with colour (default)"
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
    validation.add_argument("--ruleset",
        metavar="<ruleset>",
        action="append",
        default=None,
        dest="rulesets",
        help=(
            "Add a custom ruleset to the core ruleset. May be given more than "
            "once to apply several, e.g. --ruleset milp --ruleset project"
        )
    )
    validation.add_argument("--list-rulesets",
        action="store_true",
        default=False,
        help="List the available rulesets and exit"
    )
    validation.add_argument("--raise-on-warning",
        action="store_true",
        default=False,
        help="Treat warnings as failures, so the exit status is non-zero"
    )
    validation.add_argument("--ignore-warnings",
        action="store_true",
        default=False,
        help="Omit warnings from the report"
    )
    validation.add_argument("--raise-on-error",
        action="store_true",
        default=False,
        help=(
            "Raise a structural parsing problem as an exception instead of "
            "reporting it"
        )
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
        help="Convert between EPANET's native INP format and WNTR JSON format",
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


def handle_download(args: argparse.Namespace) -> None:
    """Handle the 'download-extra' command for downloading files from GitHub relase.
    """
    resolver = PackageResolver()
    info = resolver.resolve()
    rprint(info)
    distribution_root = info.distribution_root
    root_folder = distribution_root if distribution_root else info.project_root
    download_folder = root_folder / "epanetparser" / "networks" / "extra"
    download_networks(
        output_dir = download_folder,
        progress_bar=args.progress,
        quiet=args.quiet)


def handle_validate(args: argparse.Namespace) -> None:
    """Handle the 'validate' command for validating an EPANET model.

    Parses the model, validates it against the selected rulesets, and displays
    the results. Parsing problems and validation findings are reported
    separately, because they answer different questions: whether the document
    could be read at all, and whether the model it describes is correct.

    Args:
        args: Parsed command-line arguments for the 'validate' command.

    Raises:
        SystemExit: Exits with code 1 for an unknown ruleset, and with code 2
            when the model is invalid and --raise-on-error was not given.
    """
    filename = args.filename
    raise_error = args.raise_on_error
    raise_warning = args.raise_on_warning
    useemoji = not args.no_emoji if not args.no_colour else False
    include_digest = not args.no_digest
    context = _build_context(args.rulesets)

    if args.list_rulesets:
        rprint(RuleSetRegistry().describe())
        return

    if args.no_colour:
        console.no_color = True

    # Parse the model. Nothing is validated here: a document that cannot be
    # parsed is reported as a structural problem and nothing more.
    network, errors, warnings = WNTREPANETNetwork.from_file(
        filename,
        raise_on_parser_error=raise_error,
    )

    if network is None:
        # Nothing was validated, so the command must not claim the model is
        # fine. Exiting 1 rather than 2: 2 would mean the model was parsed and
        # found invalid, and this is not that.
        if not args.json_output:
            write_results(filename, errors or {}, warnings, use_emoji=useemoji)
        else:
            _print_json(
                results_as_json(
                    filename, errors, warnings, include_digest=include_digest
                )
            )
        sys.exit(1)

    try:
        report = network.validate(context)
    except RuleSetSelectionError as exc:
        rprint(f"[red]Error:[/red] {exc}", file=sys.stderr)
        sys.exit(1)

    if args.ignore_warnings:
        report = ValidationReport(
            [issue for issue in report if not issue.is_warning]
        )

    if args.json_output:
        # Machine-readable output means exactly one JSON document on stdout, so
        # the human-readable component counts are not printed alongside it.
        _print_json(json.dumps(report.as_dict(), indent=2))
    else:
        if len(report):
            write_results(filename, use_emoji=useemoji, results=report)
        _print_report(network, filename, args, include_digest)

    if not report.is_valid and not raise_error:
        sys.exit(2)
    if report.warnings and raise_warning:
        sys.exit(2)


def _build_context(rulesets) -> ValidationContext:
    """Build a validation context from the requested custom rulesets.

    Args:
        rulesets: Custom rule set keys from the command line, or None.

    Returns:
        ValidationContext: The core ruleset plus the requested custom ones.

    Raises:
        SystemExit: Exits with code 1 if a key is not a discovered ruleset.
    """
    context = ValidationContext(custom=tuple(rulesets or ()))
    registry = context.registry
    available = registry.keys()
    for key in context.custom:
        if key not in available:
            rprint(
                f"[red]Error:[/red] No ruleset with key '{key}'. "
                f"Available: {', '.join(available) or '<none>'}",
                file=sys.stderr,
            )
            sys.exit(1)
    return context


def _print_json(payload: str) -> None:
    """Write a JSON document to stdout without reformatting it.

    Args:
        payload: The serialised document.

    Notes:
        Prints through the standard library rather than the Rich console.
        Rich wraps output to the terminal width, which inserts real newlines
        into the text and turns the document into invalid JSON.
    """
    print(payload)


def _print_report(
    network: WNTREPANETNetwork,
    filename: str,
    args: argparse.Namespace,
    include_digest: bool,
) -> None:
    """Print the component counts of a successfully parsed model.

    Args:
        network: The parsed model.
        filename: Path the model was read from.
        args: Parsed command-line arguments.
        include_digest: If True, print the model's SHA-256 digest.
    """
    if args.terse_report:
        console.print(network.report())
        return
    report = network.verbose_report()
    console.print(f"[green]File:[/green] [bold blue]{os.path.basename(filename)}[/bold blue]")
    if include_digest:
        console.print(f"[green]sha256:[/green] [blue]{sha256digest(filename)}[/blue]")
    for prefix, count in report.items():
        console.print(f"[green]{prefix}:[/green] [blue]{count}[/blue]")
    

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

    Args:
        args: Parsed command-line arguments for the 'info' command.
    """
    if args.list_rulesets:
        console.print(RuleSetRegistry().describe())
        return
    console.print(f"[bold]EPANET Parser[/bold] version {__version__}")
    console.print("\nA tool for parsing and validating EPANET network models.")
    console.print(
        "\nParsing builds a model; validation is a separate, explicit step "
        "that returns a structured report."
    )
    console.print(
        "\nUse 'epanetparser info --list-rulesets' to see available rulesets."
    )
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
    elif args.command == "download-extra":
        handle_download(args)
    else:
        # This shouldn't happen if argparse is configured correctly
        rprint(
            "[red]Error:[/red] No command specified. "
            "Use --help for usage information.",
            file=sys.stderr,
        )
        sys.exit(1)


def run() -> None:
    """Main entry point for the EPANET validator CLI.
    
    Parses command-line arguments and executes the validation workflow.
    Called when the module is run as a script.
    """
    # Ensure library is initialized (config, autodiscovery, etc.)
    from epanetparser.core.init import initialize
    initialize()
    
    args = configure_args(sys.argv[1:])
    handle_args(args)


if __name__ == "__main__":
    run()
