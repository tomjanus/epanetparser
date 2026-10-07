"""Display and formatting utilities for EPANET parser results.

This module renders validation results for the terminal and for machine
consumption. It knows about two kinds of result, because they answer different
questions:

* *structural problems*, raised by the parser when a document cannot be turned
  into a model at all, which arrive as
  :class:`~epanetparser.core.epanettypes.exceptions.WNTREPANETParserException`;
* *validation issues*, produced by the validation engine when a model is
  well-formed but not correct, which arrive as
  :class:`~epanetparser.core.validation.results.ValidationIssue`.

Both are grouped by the component they concern, so a long report reads as a
list of components rather than a list of failures.

Functions
---------
write_results
    Render a result report on the console with Rich.
results_as_dict
    Build a structured dictionary from a result report.
results_as_json
    Serialise a result report as JSON.
coalesce_errors_and_warnings
    Merge error and warning mappings into one.
count_errors_warnings
    Count the errors and warnings in a result report.

Examples
--------
>>> from epanetparser.core.display import write_results
>>> report = network.validate()
>>> write_results("Net1.json", report.grouped_by_component())
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
import datetime
import io
import json
import os

from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

from epanetparser.core.validation import Severity, ValidationIssue
from epanetparser.core.utils import sha256digest

#: The console every result is rendered to.
console = Console()

WARN_EMOJI = ":yellow_circle:"
RULE_EMOJI = ":red_circle:"

#: Group key used for findings that are not about a single component.
NETWORK_KEY = "network"

#: Rich markup used for each severity when emoji are suppressed.
_SEVERITY_LABEL = {
    Severity.ERROR: "[FAILURE]",
    Severity.WARNING: "[WARNING]",
    Severity.INFO: "[INFO]",
}

_SEVERITY_COLOUR = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
}


def _severity_of(item: Any) -> Severity:
    """Classify a result item by severity.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.

    Returns
    -------
    Severity
        The item's severity. Objects that are neither a
        :class:`ValidationIssue` nor a :class:`Warning` are errors, which is
        how structural parser problems are rendered.
    """
    if isinstance(item, ValidationIssue):
        return item.severity
    return Severity.WARNING if isinstance(item, Warning) else Severity.ERROR


def _describe(item: Any) -> Tuple[str, str]:
    """Return the rule or code name and message of a result item.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.

    Returns
    -------
    Tuple[str, str]
        The item's name, which is its stable issue code for a
        :class:`ValidationIssue` and its rule or warning name otherwise, and
        its message.
    """
    if isinstance(item, ValidationIssue):
        return item.code, item.message
    name = getattr(item, "rule", None) or getattr(item, "warning", None) or ""
    message = getattr(item, "exc", None)
    return name, str(message if message is not None else item)


def _target_of(item: Any, component: str) -> str:
    """Return the component label to print for a result item.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.
    component : str
        The group the item was collected under.

    Returns
    -------
    str
        The component's name when it has one, otherwise the group key, so
        that network-level findings are still attributed somewhere.
    """
    if isinstance(item, ValidationIssue):
        return item.component_name or component
    return getattr(item, "component", None) or component


def _value_text(item: Any) -> str:
    """Return the indented detail line for a result item, if it has one."""
    if isinstance(item, ValidationIssue):
        detail = Text()
        detail.append(f"{item.rule_id}")
        if item.ruleset_key:
            detail.append(f"  [{item.ruleset_key}]")
        detail.append(f"  {item.attribute or '-'}")
        for key, value in sorted(item.context.items()):
            detail.append(f"\n{key}: {value}", style="dim")
        return Padding(Text("  ") + detail, (0, 6))
    valuetext = getattr(item, "valuetext", None)
    return Padding(str(valuetext), (0, 12)) if valuetext else Padding("", (0, 0))


"""Display and formatting utilities for EPANET parser results.

This module renders validation results for the terminal and for machine
consumption. It knows about two kinds of result, because they answer different
questions:

* *structural problems*, raised by the parser when a document cannot be turned
  into a model at all, which arrive as
  :class:`~epanetparser.core.epanettypes.exceptions.WNTREPANETParserException`;
* *validation issues*, produced by the validation engine when a model is
  well-formed but not correct, which arrive as
  :class:`~epanetparser.core.validation.results.ValidationIssue`.

Both are grouped by the component they concern, so a long report reads as a
list of components rather than a list of failures.

Functions
---------
write_results
    Render a result report on the console with Rich.
results_as_dict
    Build a structured dictionary from a result report.
results_as_json
    Serialise a result report as JSON.
coalesce_errors_and_warnings
    Merge error and warning mappings into one.
count_errors_warnings
    Count the errors and warnings in a result report.

Examples
--------
>>> from epanetparser.core.display import write_results
>>> report = network.validate()
>>> write_results("Net1.json", report.grouped_by_component())
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
import datetime
import io
import json
import os

from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from epanetparser.core.validation import Severity, ValidationIssue
from epanetparser.core.utils import sha256digest

#: The console every result is rendered to.
console = Console()

WARN_EMOJI = ":yellow_circle:"
RULE_EMOJI = ":red_circle:"

#: Group key used for findings that are not about a single component.
NETWORK_KEY = "network"

#: Rich markup used for each severity when emoji are suppressed.
_SEVERITY_LABEL = {
    Severity.ERROR: "[FAILURE]",
    Severity.WARNING: "[WARNING]",
    Severity.INFO: "[INFO]",
}

_SEVERITY_COLOUR = {
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
}


def _severity_of(item: Any) -> Severity:
    """Classify a result item by severity.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.

    Returns
    -------
    Severity
        The item's severity. Objects that are neither a
        :class:`ValidationIssue` nor a :class:`Warning` are errors, which is
        how structural parser problems are rendered.
    """
    if isinstance(item, ValidationIssue):
        return item.severity
    return Severity.WARNING if isinstance(item, Warning) else Severity.ERROR


def _describe(item: Any) -> Tuple[str, str]:
    """Return the rule or code name and message of a result item.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.

    Returns
    -------
    Tuple[str, str]
        The item's name, which is its stable issue code for a
        :class:`ValidationIssue` and its rule or warning name otherwise, and
        its message.
    """
    if isinstance(item, ValidationIssue):
        return item.code, item.message
    name = getattr(item, "rule", None) or getattr(item, "warning", None) or ""
    message = getattr(item, "exc", None)
    return name, str(message if message is not None else item)


def _target_of(item: Any, component: str) -> str:
    """Return the component label to print for a result item.

    Parameters
    ----------
    item : Any
        A :class:`ValidationIssue` or a legacy warning or error object.
    component : str
        The group the item was collected under.

    Returns
    -------
    str
        The component's name when it has one, otherwise the group key, so
        that network-level findings are still attributed somewhere.
    """
    if isinstance(item, ValidationIssue):
        return item.component_name or component
    return getattr(item, "component", None) or component


def _value_text(item: Any) -> str:
    """Return the indented detail line for a result item, if it has one."""
    if isinstance(item, ValidationIssue):
        detail = Text()
        detail.append(f"{item.rule_id}")
        if item.ruleset_key:
            detail.append(f"  [{item.ruleset_key}]")
        detail.append(f"  {item.attribute or '-'}")
        for key, value in sorted(item.context.items()):
            detail.append(f"\n{key}: {value}", style="dim")
        return Padding(Text("  ") + detail, (0, 6))
    valuetext = getattr(item, "valuetext", None)
    return Padding(str(valuetext), (0, 12)) if valuetext else Padding("", (0, 0))


def write_results(
    filename: str,
    errors: Optional[Dict[str, Sequence[Any]]] = None,
    warnings: Optional[Dict[str, Sequence[Any]]] = None,
    use_emoji: bool = True,
    results: Optional[Any] = None,
) -> None:
    """Render a result report on the console.

    Parameters
    ----------
    filename : str
        Name of the model the results are for, shown in the header.
    errors : Dict[str, Sequence[Any]]
        Findings keyed by component, as produced by
        :meth:`~epanetparser.core.validation.results.ValidationReport.grouped_by_component`.
        Both validation issues and structural parser exceptions are accepted.
    warnings : Optional[Dict[str, Sequence[Any]]]
        Additional warnings keyed by component, for callers that keep warnings
        and errors apart. Ignored when ``results`` is given.
    use_emoji : bool
        If True, mark findings with a coloured circle. If False, use a text
        label such as ``[FAILURE]``.
    results : Optional[Any]
        A :class:`~epanetparser.core.validation.results.ValidationReport` to
        render. When given, ``errors`` and ``warnings`` are ignored and the
        report is grouped by component internally.

    Notes
    -----
    Findings are printed grouped by component, with network-level findings
    first, because a reference that points at nothing only makes sense once
    the reader knows which network it is about.

    Examples
    --------
    >>> write_results("Net1.json", results=network.validate())
    """
    if results is not None:
        errors = results.grouped_by_component()
        warnings = None
    error_total, warning_total = count_errors_warnings(errors, warnings)
    merged = coalesce_errors_and_warnings(errors, warnings)
    err_plural = "" if error_total == 1 else "s"
    warn_plural = "" if warning_total == 1 else "s"

    console.print("")
    console.print(Align(Panel(_acknowledgement()), align="center"))
    console.print("")
    console.print(
        Align(
            Panel(
                f"[bold green]Parser results for '{filename}':"
                f" [bold red]{error_total} error{err_plural}[/bold red],"
                f" [bold yellow]{warning_total} warning{warn_plural}",
                style="blue",
            ),
            align="center",
        )
    )

    network_findings = merged.pop(NETWORK_KEY, [])
    if network_findings:
        console.print(Rule(f"[bold]{NETWORK_KEY.capitalize()}", style="blue"))
        console.print()
    for finding in network_findings:
        console.print(_finding_line(finding, NETWORK_KEY, use_emoji))
        _print_finding_details(finding, use_emoji)
    console.print()

    for component, findings in merged.items():
        console.print(Rule(f"[bold]{component.capitalize()}", style="blue"))
        console.print()
        for finding in findings:
            console.print(_finding_line(finding, component, use_emoji))
            _print_finding_details(finding, use_emoji)
        console.print()
    console.print(Rule(style="blue"))


def _acknowledgement() -> str:
    """Return the banner shown above every report."""
    return (
        "This is [bold blue]epanetparser[/bold blue] - a parser and validator "
        "for [bold]EPANET[/bold] network models, working with the JSON "
        "representation specified by [bold green]WNTR[/bold green] - "
        "[italic]`A Python package designed to simulate and analyze "
        "resilience of water distribution networks.`[/italic]"
    )


def _finding_line(finding: Any, component: str, use_emoji: bool) -> Padding:
    """Render one finding as a padded console line."""
    severity = _severity_of(finding)
    name, message = _describe(finding)
    if use_emoji:
        prefix = RULE_EMOJI if severity is Severity.ERROR else WARN_EMOJI
    else:
        prefix = _SEVERITY_LABEL[severity]
    return Padding(
        f"{prefix}  {_target_of(finding, component)} "
        f"[bold blue]'{name}'[/bold blue] ->"
        f" [white italic]{message}[/white italic]",
        (0, 2),
    )


def _print_finding_details(finding: Any, use_emoji: bool) -> None:
    """Print detailed information for a finding (rule_id, ruleset, attribute, context)."""
    if not isinstance(finding, ValidationIssue):
        return
    
    details = []
    details.append(f"  Rule: {finding.rule_id}")
    if finding.ruleset_key:
        details.append(f"  Ruleset: {finding.ruleset_key}")
    if finding.attribute:
        details.append(f"  Attribute: {finding.attribute}")
    
    # Print failing_fields if present in context
    if "failing_fields" in finding.context:
        fields = finding.context["failing_fields"]
        if fields:
            details.append(f"  Failing fields: {', '.join(fields)}")
    
    # Print component_data excerpt if available (for network elements)
    if finding.component_data and finding.component_type != "network":
        # Show a summary of component data
        data_summary = []
        for k, v in finding.component_data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                data_summary.append(f"{k}={v!r}")
            elif isinstance(v, list) and len(v) < 10:
                data_summary.append(f"{k}={v!r}")
        if data_summary:
            details.append(f"  Component data: {', '.join(data_summary[:5])}")
            if len(data_summary) > 5:
                details.append(f"    ... and {len(data_summary) - 5} more fields")
    
    # Print other context items (excluding failing_fields which we already printed)
    for key, value in sorted(finding.context.items()):
        if key != "failing_fields":
            details.append(f"  {key}: {value}")
    
    if details:
        for detail in details:
            console.print(f"    [dim]{detail}[/dim]")


def coalesce_errors_and_warnings(
    errors: Optional[Dict[str, Sequence[Any]]],
    warnings: Optional[Dict[str, Sequence[Any]]],
) -> Dict[str, List[Any]]:
    """Merge error and warning mappings into one mapping.

    Parameters
    ----------
    errors : Optional[Dict[str, Sequence[Any]]]
        Findings keyed by component.
    warnings : Optional[Dict[str, Sequence[Any]]]
        Further findings keyed by component.

    Returns
    -------
    Dict[str, List[Any]]
        A new mapping with both sets of findings concatenated per component.
        Neither input is modified.
    """
    merged: Dict[str, List[Any]] = {
        component: list(findings) for component, findings in (errors or {}).items()
    }
    for component, findings in (warnings or {}).items():
        merged[component] = merged.get(component, []) + list(findings)
    return merged


def count_errors_warnings(
    errors: Optional[Dict[str, Sequence[Any]]],
    warnings: Optional[Dict[str, Sequence[Any]]],
) -> Tuple[int, int]:
    """Count the errors and warnings in a result report.

    Parameters
    ----------
    errors : Optional[Dict[str, Sequence[Any]]]
        Findings keyed by component.
    warnings : Optional[Dict[str, Sequence[Any]]]
        Further findings keyed by component.

    Returns
    -------
    Tuple[int, int]
        The number of errors and the number of warnings, counted from the
        severity of each finding rather than from which mapping it arrived in.
    """
    error_total = 0
    warning_total = 0
    for findings in (errors or {}).values():
        for finding in findings:
            if _severity_of(finding) is Severity.WARNING:
                warning_total += 1
            else:
                error_total += 1
    for findings in (warnings or {}).values():
        for finding in findings:
            if _severity_of(finding) is Severity.WARNING:
                warning_total += 1
            else:
                error_total += 1
    return error_total, warning_total


def results_as_dict(
    filename: str,
    errors: Optional[Dict[str, Sequence[Any]]] = None,
    warnings: Optional[Dict[str, Sequence[Any]]] = None,
    include_digest: bool = True,
    context: Any = None,
) -> dict:
    """Build a structured dictionary from a result report.

    Parameters
    ----------
    filename : str
        Path to the model the results are for, or a file-like object for
        standard input.
    errors : Optional[Dict[str, Sequence[Any]]]
        Findings keyed by component.
    warnings : Optional[Dict[str, Sequence[Any]]]
        Further findings keyed by component.
    include_digest : bool
        If True, include the SHA-256 digest of the model file.
    context : Any
        Rule set selection the results were produced with. Recorded under
        ``rulesets`` so that a stored report says which rules produced it.

    Returns
    -------
    dict
        Mapping with a ``results`` section holding the file name, creation
        time, selected rule sets and finding counts, plus ``errors`` and
        ``warnings`` sections holding the findings themselves.
    """
    from epanetparser.core.validation import ValidationContext

    error_total, warning_total = count_errors_warnings(errors, warnings)
    from_stdin = isinstance(filename, io.StringIO)
    if from_stdin:
        filename = "stdin"
    fbasename = os.path.basename(filename)
    resolved = ValidationContext.from_any(context)
    result: Dict[str, Any] = {
        "results": {
            "file": {"name": fbasename},
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rulesets": list(resolved.ruleset_keys),
            "errors": error_total,
            "warnings": warning_total,
        }
    }
    if include_digest and not from_stdin:
        result["results"]["file"]["sha256"] = sha256digest(filename)
    if errors:
        result["errors"] = {
            component: [_as_dict(finding) for finding in findings]
            for component, findings in errors.items()
        }
    if warnings:
        result["warnings"] = {
            component: [_as_dict(finding) for finding in findings]
            for component, findings in warnings.items()
        }
    return result


def _as_dict(finding: Any) -> Dict[str, Any]:
    """Serialise one finding, whatever kind it is."""
    if isinstance(finding, ValidationIssue):
        return finding.as_dict()
    if hasattr(finding, "as_dict"):
        return finding.as_dict()
    return {"message": str(finding)}


def results_as_json(
    filename: str,
    errors: Optional[Dict[str, Sequence[Any]]] = None,
    warnings: Optional[Dict[str, Sequence[Any]]] = None,
    include_digest: bool = True,
    indent: int = 2,
    context: Any = None,
) -> str:
    """Serialise a result report as JSON.

    Parameters
    ----------
    filename : str
        Path to the model the results are for, or a file-like object for
        standard input.
    errors : Optional[Dict[str, Sequence[Any]]]
        Findings keyed by component.
    warnings : Optional[Dict[str, Sequence[Any]]]
        Further findings keyed by component.
    include_digest : bool
        If True, include the SHA-256 digest of the model file.
    indent : int
        Number of spaces to indent by. Pass 0 for compact output.
    context : Any
        Rule set selection the results were produced with.

    Returns
    -------
    str
        JSON text of :func:`results_as_dict`.
    """
    return json.dumps(
        results_as_dict(
            filename,
            errors,
            warnings,
            include_digest=include_digest,
            context=context,
        ),
        indent=indent or None,
    )

