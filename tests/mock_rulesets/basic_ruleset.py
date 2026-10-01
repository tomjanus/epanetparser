"""A rule set with metadata but no rules, marked as the core ruleset.

Two things are being tested at once here, and both are easier to test together
than apart.

The rule set is *empty*. A rule set is discovered from its metadata, not from
whether it declares rules, so one with an empty body is still a valid rule set
and can still be selected. That case is worth testing precisely because there is
nothing in it to inspect: an implementation that inferred rule sets from their
contents rather than from their metadata would not find this one.

The rule set is *core*, because it sets ``__is_core__ = True``. Discovery treats
core and custom rule sets identically and lets this attribute tell them apart,
so a mock package that exercised only custom rule sets would not test the
distinction at all.

Examples
--------
>>> from epanetparser.core.validation import RuleSetRegistry
>>> registry = RuleSetRegistry(packages=["tests.mock_rulesets"])
>>> registry.get("basic").rule_count
0
>>> registry.get("basic").is_core
True
"""

#: Stable key of this ruleset.
__key__ = "basic"

#: Human-readable name.
__ruleset_name__ = "Basic Test Ruleset"

#: Version of this ruleset.
__version__ = "1.0.0"

#: Marks this ruleset as the core ruleset, so it may be selected as the one
#: core rule set of a validation run.
__is_core__ = True

#: Summary of what this ruleset checks.
__description__ = "A rule set with metadata and no rules."
