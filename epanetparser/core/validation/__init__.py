"""Explicit, registry-driven static validation for EPANET models.

In `epanetparser`, a model is first parsed from an input file, then validated 
by one or more rulesets the caller selects:

.. code-block:: text

    EPANET input -> Parser -> EPANET model -> Static validation -> Simulator

Parsing builds the model structure in a json-like format. Validation is
simulator-agnostic, like a compiler's static checks: it knows what a
well-formed EPANET model looks like, not what a particular solver can do with
it. Constraints that belong to one application, such as an MILP pump
scheduling formulation, live in custom rulesets and are opted into explicitly.

Rules are plain functions that ``assert``. They live in modules discovered by
one shared mechanism, which is used for the single core ruleset and for any
number of custom rulesets alike:

.. code-block:: python

    from epanetparser.core.validation import ValidationContext, validate

    report = validate(network)                          # core ruleset only
    report = validate(network, ["epanet_core", "milp"])  # core plus custom

    if not report.is_valid:
        for issue in report.errors:
            print(issue.code, issue.component_name, issue.message)

A ruleset is an ordinary module declaring ``__key__``, ``__ruleset_name__`` and
``__version__``. A core ruleset also sets ``__is_core__ = True``. There is no
inheritance from component classes and no monkey-patching of them: adding
validation never requires touching the model.

Examples
--------
Component-level validation:

>>> from epanetparser.core.epanettypes import WNTREPANETNode
>>> from epanetparser.core.validation import validate
>>> junction = WNTREPANETNode({"name": "J1", "node_type": "Junction", "elevation": 10.0})
>>> report = validate(junction)
>>> report.is_valid
True

Network-level validation, including cross-component references:

>>> report = validate(network)
>>> [issue.code for issue in report.errors if issue.component_type == "network"]
[]

See Also
--------
epanetparser.core.parsers.wntrjsonparser : Parses a model; performs no validation.
epanetparser.core_rules : The core ruleset.
epanetparser.custom_rules : Custom rulesets.
"""
from epanetparser.core.validation.discovery import (
    ENTRY_POINT_GROUP,
    REQUIRED_METADATA,
    default_packages,
    discover_ruleset_modules,
)
from epanetparser.core.validation.engine import (
    COMPONENT_COLLECTIONS,
    NAME_INDEXED_COLLECTIONS,
    NetworkIndex,
    ValidationContext,
    Validator,
    clear_caches,
    get_validator,
    validate,
)
from epanetparser.core.validation.registry import (
    DEFAULT_CORE_KEY,
    RuleSet,
    RuleSetRegistry,
    RuleSetSelectionError,
    list_rulesets,
)
from epanetparser.core.validation.results import Severity, ValidationIssue, ValidationReport
from epanetparser.core.validation.rules import (
    RuleExecutionError,
    RuleSpec,
    RuleViolation,
    collect_rules,
    defined,
    network_rule,
    rule,
)
from epanetparser.core.validation.decorators import (
    DescribedCallable,
    described,
    extract_quick_description,
    match,
)
from epanetparser.core.validation.introspection import (
    FileInfo,
    MethodInfo,
    discover_classes,
    discover_methods_in_class,
    get_rule_methods,
    get_warning_methods,
)

__all__ = [
    "COMPONENT_COLLECTIONS",
    "DEFAULT_CORE_KEY",
    "ENTRY_POINT_GROUP",
    "REQUIRED_METADATA",
    "NAME_INDEXED_COLLECTIONS",
    "NetworkIndex",
    "RuleExecutionError",
    "RuleSet",
    "RuleSetRegistry",
    "RuleSetSelectionError",
    "RuleSpec",
    "RuleViolation",
    "Severity",
    "ValidationContext",
    "ValidationIssue",
    "ValidationReport",
    "Validator",
    "clear_caches",
    "collect_rules",
    "default_packages",
    "defined",
    "discover_classes",
    "discover_methods_in_class",
    "discover_ruleset_modules",
    "extract_quick_description",
    "FileInfo",
    "get_rule_methods",
    "get_validator",
    "get_warning_methods",
    "list_rulesets",
    "match",
    "network_rule",
    "rule",
    "validate",
    "described",
    "MethodInfo",
    "DescribedCallable",
]
