"""A second custom rule set, for testing that several can be selected at once.

Selecting several custom rule sets is the case that distinguishes a registry
from a single active rule set: a model may have to satisfy the core ruleset and
two application rulesets at once, and their findings must all be reported
without either shadowing the other.

The rules here are deliberately different from those in
:mod:`tests.mock_rulesets.advanced_ruleset` so that a report can be attributed
to the rule set that produced it.

Examples
--------
>>> from epanetparser.core.validation import RuleSetRegistry
>>> registry = RuleSetRegistry(packages=["tests.mock_rulesets"])
>>> sorted(
...     ruleset.key
...     for ruleset in registry.resolve(
...         __import__("epanetparser.core.validation", fromlist=["ValidationContext"])
...         .ValidationContext(core="basic", custom=["advanced", "extra"])
...     )
... )
['advanced', 'basic', 'extra']
"""
from epanetparser.core.validation import RuleViolation, rule

#: Stable key of this ruleset.
__key__ = "extra"

#: Human-readable name.
__ruleset_name__ = "Extra Test Ruleset"

#: Version of this ruleset.
__version__ = "0.3.0"

#: Summary of what this ruleset checks.
__description__ = "A second custom ruleset, for testing multiple selection."

#: Options this ruleset insists on, so that it can be told apart from others.
REQUIRED_OPTION_GROUPS = ("time", "hydraulic", "energy")


@rule("WNTREPANETOptions", code="E_EXTRA_OPTIONS_GROUPS")
def rule_option_groups_present(options) -> None:
    """Every option group this ruleset relies on must be defined."""
    absent = [group for group in REQUIRED_OPTION_GROUPS if group not in options.data]
    assert not absent, f"Options define no {', '.join(absent)} group"


@rule("WNTREPANETCurve", code="W_EXTRA_SINGLE_POINT_CURVE")
def warn_single_point_curve(curve) -> None:
    """A curve with a single point is legal but carries no shape information."""
    points = curve.data.get("points") or []
    assert len(points) != 1, (
        f"Curve '{curve.name}' has a single point, so it defines no curve"
    )


@rule("WNTREPANETNode", code="E_EXTRA_NAME_RESERVED")
def rule_name_not_reserved(node) -> None:
    """A node name must not collide with a name this ruleset reserves."""
    reserved = ("network", "none")
    if node.name in reserved:
        raise RuleViolation(f"Node name '{node.name}' is reserved", reserved=reserved)
