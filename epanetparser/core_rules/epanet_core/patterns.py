"""Pattern rules for the core ruleset.

The core ruleset only requires that a pattern is named and carries a list of
multipliers. How many multipliers a pattern should have depends on the
simulation horizon and timestep, and any fixed count is an assumption of a
particular application rather than of EPANET, so length constraints belong in
a custom ruleset.
"""
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

PATTERN = "WNTREPANETPattern"


@rule(PATTERN, code="E_PATTERN_NAME_MISSING", attribute="name")
def rule_pattern_has_name(pattern) -> None:
    """A pattern must have a name."""
    assert _defined(pattern, "name"), "Missing pattern name"


@rule(PATTERN, code="E_PATTERN_MULTIPLIERS_MISSING", attribute="multipliers")
def rule_pattern_has_multipliers(pattern) -> None:
    """A pattern must define a non-empty list of multipliers."""
    multipliers = pattern.data.get("multipliers")
    assert isinstance(multipliers, list) and len(multipliers) > 0, \
        "Pattern must have a non-empty list of multipliers"


@rule(PATTERN, code="E_PATTERN_MULTIPLIER_NOT_NUMERIC", attribute="multipliers")
def rule_pattern_multipliers_numeric(pattern) -> None:
    """Pattern multipliers must be numeric."""
    multipliers = pattern.data.get("multipliers") or []
    assert all(
        isinstance(multiplier, (int, float)) for multiplier in multipliers
    ), "Pattern multipliers must be numeric values"
