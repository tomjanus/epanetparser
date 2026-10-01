"""Control rules for the core ruleset.

WNTR distinguishes simple controls from rule-based controls by the ``type``
field. A control with an unrecognised kind is one this parser cannot interpret,
so the kind itself is checked. A control also needs a condition to act on.
"""
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

CONTROL = "WNTREPANETControl"

#: Control kinds WNTR's JSON representation distinguishes.
CONTROL_TYPES = ("simple", "rule")


@rule(CONTROL, code="E_CONTROL_TYPE_MISSING", attribute="type")
def rule_control_has_type(control) -> None:
    """A control must declare whether it is a simple or a rule-based control."""
    assert _defined(control, "type"), "Control does not define type"


@rule(CONTROL, code="E_CONTROL_TYPE_UNSUPPORTED", attribute="type")
def rule_control_has_valid_type(control) -> None:
    """A control must be a simple or a rule-based control."""
    assert control.type in CONTROL_TYPES, f"Unsupported control type {control.type}"


@rule(CONTROL, code="E_CONTROL_CONDITION_MISSING", attribute="condition")
def rule_control_has_condition(control) -> None:
    """A control must state the condition that triggers it."""
    assert control.data.get("condition"), "Control does not define a condition"
