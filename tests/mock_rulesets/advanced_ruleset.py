"""A rule set exercising every kind of rule, for testing discovery and execution.

The rules here are ordinary functions that ``assert``. Nothing subclasses or
patches a component class, which is the point: this rule set must be able to add
validation to existing component classes without touching them.

It declares one rule of each kind worth testing:

* a rule that always passes, so a passing result is distinguishable from an
  empty one;
* a rule that always fails, so a failing result is distinguishable from a rule
  that was never run;
* a rule that carries structured context through
  :class:`~epanetparser.core.validation.RuleViolation`;
* a rule restricted to one component type with ``@match``;
* a network rule, which sees the whole model and its index.

Examples
--------
>>> from epanetparser.core.validation import RuleSetRegistry
>>> registry = RuleSetRegistry(packages=["tests.mock_rulesets"])
>>> registry.get("advanced").rule_count
5
"""
from epanetparser.core.validation import match, RuleViolation, network_rule, rule

#: Stable key of this ruleset.
__key__ = "advanced"

#: Human-readable name.
__ruleset_name__ = "Advanced Test Ruleset"

#: Version of this ruleset.
__version__ = "2.1.0"

#: Summary of what this ruleset checks.
__description__ = "A rule set covering every kind of rule the engine supports."

#: Name a node must carry for the custom ruleset to accept it.
REQUIRED_NODE_NAME = "J1"

#: Name of the pattern the network rule requires to exist.
REQUIRED_PATTERN_NAME = "1"


@rule("WNTREPANETNode", code="E_ADVANCED_NODE_NAME")
def rule_node_name_is_j1(node) -> None:
    """A node's name must be 'J1', which almost no real model satisfies."""
    assert node.name == REQUIRED_NODE_NAME, (
        f"Node '{node.name}' is not named '{REQUIRED_NODE_NAME}'"
    )


@rule("WNTREPANETLink", code="E_ADVANCED_NO_LINKS", attribute="name")
def rule_no_links(link) -> None:
    """No link may exist, so any model with a link fails this ruleset."""
    raise RuleViolation("Links are not permitted", link=link.name)


@rule("WNTREPANETPattern", code="E_ADVANCED_PATTERN_MULTIPLIERS")
def rule_pattern_multipliers_are_even(pattern) -> None:
    """A pattern must hold an even number of multipliers."""
    count = len(pattern.data.get("multipliers") or [])
    assert count % 2 == 0, f"Pattern '{pattern.name}' has an odd multiplier count {count}"


@rule("WNTREPANETNode", code="W_ADVANCED_TANK_ELEVATION", attribute="elevation")
@match("Tank")
def warn_tank_elevation_low(node) -> None:
    """A tank should sit above ground, which is a modelling convention."""
    elevation = node.data.get("elevation")
    assert elevation is None or elevation >= 0, (
        f"Tank '{node.name}' has a negative elevation {elevation}"
    )


@network_rule(code="E_ADVANCED_MISSING_PATTERN", attribute="patterns")
def rule_pattern_present(network) -> None:
    """The network must define the pattern this ruleset depends on."""
    assert REQUIRED_PATTERN_NAME in network.index.patterns, (
        f"Network defines no pattern named '{REQUIRED_PATTERN_NAME}'"
    )
