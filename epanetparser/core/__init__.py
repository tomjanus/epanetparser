"""Core of the EPANET parser: parsing, the model, and static validation.

This module is a re-export shim. It exists so that the most-used names can be
reached without knowing which submodule they live in, and it deliberately
contains no logic of its own.

The pipeline, and where each stage lives:

.. code-block:: text

    EPANET input
        |
        v
    WNTRJSONParser                epanetparser.core.parsers.wntrjsonparser
        |                          parsing only; no validation
        v
    WNTREPANETNetwork             epanetparser.core.epanettypes.network
        |
        v
    validate()                    epanetparser.core.validation
        |                          simulator-agnostic static checks
        v
    Simulator

What is re-exported
-------------------
Parsing
    :func:`~epanetparser.core.parsers.wntrjsonparser.WNTRJSONParser`
Model
    :class:`~epanetparser.core.epanettypes.network.WNTREPANETNetwork` and the
    component classes
Validation
    :func:`~epanetparser.core.validation.validate`,
    :class:`~epanetparser.core.validation.ValidationContext`,
    :class:`~epanetparser.core.validation.ValidationReport`,
    :class:`~epanetparser.core.validation.Severity` and the rule decorators
Setup
    :func:`~epanetparser.core.init.initialize`
Command line
    :func:`~epanetparser.core.parse.run`

Notes
-----
``__version__`` is the single source of truth for the package version, read
from the installed distribution metadata so that it cannot drift from
``pyproject.toml``.

Examples
--------
>>> from epanetparser.core import WNTREPANETNetwork, validate
>>> network, errors, warnings = WNTREPANETNetwork.from_file("Net1.inp")
>>> report = validate(network)
>>> report.is_valid
True
"""
from importlib.metadata import PackageNotFoundError, version as _distribution_version
from typing import List

try:
    __version__ = _distribution_version("epanetparser")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.1.0"

from epanetparser.core.decorators import described, match
from epanetparser.core.display import (
    console,
    count_errors_warnings,
    results_as_dict,
    results_as_json,
    write_results,
)
from epanetparser.core.epanettypes import (
    WNTREPANETControl,
    WNTREPANETCurve,
    WNTREPANETLink,
    WNTREPANETNetworkInfo,
    WNTREPANETNode,
    WNTREPANETOptions,
    WNTREPANETPattern,
    WNTREPANETSource,
)
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETParserException,
)
from epanetparser.core.epanettypes.network import (
    WNTRNetworkStatistics,
    WNTREPANETNetwork,
)
from epanetparser.core.init import initialize, is_initialized
from epanetparser.core.parsers.wntrjsonparser import WNTRJSONParser
from epanetparser.core.validation import (
    NetworkIndex,
    RuleSet,
    RuleSetRegistry,
    RuleSetSelectionError,
    Severity,
    ValidationContext,
    ValidationIssue,
    ValidationReport,
    Validator,
    network_rule,
    rule,
    validate,
)

__all__: List[str] = [
    "NetworkIndex",
    "RuleSet",
    "RuleSetRegistry",
    "RuleSetSelectionError",
    "Severity",
    "WNTRJSONParser",
    "WNTRNetworkStatistics",
    "WNTREPANETControl",
    "WNTREPANETCurve",
    "WNTREPANETLink",
    "WNTREPANETNetwork",
    "WNTREPANETNetworkInfo",
    "WNTREPANETNode",
    "WNTREPANETOptions",
    "WNTREPANETParserException",
    "WNTREPANETPattern",
    "WNTREPANETSource",
    "ValidationContext",
    "ValidationIssue",
    "ValidationReport",
    "Validator",
    "__version__",
    "console",
    "count_errors_warnings",
    "described",
    "initialize",
    "is_initialized",
    "match",
    "network_rule",
    "results_as_dict",
    "results_as_json",
    "rule",
    "validate",
    "write_results",
]
