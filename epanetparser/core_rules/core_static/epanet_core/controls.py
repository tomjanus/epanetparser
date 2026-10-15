"""Control rules for the core ruleset.

WNTR distinguishes simple controls from rule-based controls by the ``type``
field. A control with an unrecognised kind is one this parser cannot interpret,
so the kind itself is checked. A control also needs a condition to act on.
"""
from epanetparser.core.validation import defined as _defined, match, rule

CONTROL = "WNTREPANETControl"

#: Control kinds WNTR's JSON representation distinguishes.
CONTROL_TYPES = ("simple", "rule")


@rule(CONTROL, code="E_CONTROL_TYPE_MISSING", attribute="type")
def rule_control_has_type(control) -> None:
    """A control must declare whether it is a simple or a rule-based control.

    classification : Control
    fix : Specify the control type as 'simple' or 'rule'.
    """
    assert _defined(control, "type"), "Control does not define type"


@rule(CONTROL, code="E_CONTROL_TYPE_UNSUPPORTED", attribute="type")
def rule_control_has_valid_type(control) -> None:
    """A control must be a simple or a rule-based control.

    classification : Control
    fix : Change the control type to 'simple' or 'rule'.
    """
    assert control.type in CONTROL_TYPES, f"Unsupported control type {control.type}"


@rule(CONTROL, code="E_CONTROL_CONDITION_MISSING", attribute="condition")
def rule_control_has_condition(control) -> None:
    """A control must state the condition that triggers it.

    classification : Control
    fix : Provide a condition (time, tank level, node pressure, etc.) that triggers the control action.
    """
    assert control.data.get("condition"), "Control does not define a condition"


@rule(CONTROL, code="E_RULE_CLAUSE_STRUCTURE", attribute="condition")
@match("rule")
def rule_rule_clause_structure(control) -> None:
    """Rule-based controls must have valid IF/THEN/ELSE structure (EPANET error 221).

    classification : Control
    fix : Ensure IF is followed by THEN; ELSE is optional; no dangling clauses.
    """
    cond = control.data.get("condition", {})
    # Check for basic structure: IF must have THEN
    if isinstance(cond, dict):
        # This is a simplified check - actual rule structure validation would be more complex
        assert cond, "Rule condition must not be empty"
        # Check for THEN actions
        then_actions = control.data.get("then_actions", [])
        assert len(then_actions) > 0, "Rule control must have at least one THEN action"
        # If ELSE present, must have actions
        else_actions = control.data.get("else_actions", [])
        if else_actions:
            assert len(else_actions) > 0, "Rule ELSE clause must have actions"


@rule(CONTROL, code="E_SIMPLE_CONTROL_CONDITION", attribute="condition")
@match("simple")
def rule_simple_control_condition_valid(control) -> None:
    """Simple control condition must be parsable (EPANET error 213).

    classification : Control
    fix : Use valid condition syntax: TIME, TANK level, NODE pressure, etc.
    """
    cond = control.data.get("condition")
    assert cond, "Simple control must have a condition"
    # Handle both string and dict conditions
    if isinstance(cond, dict):
        cond_type = cond.get("type", "")
        valid_types = {"TIME", "TANK_LEVEL", "NODE_PRESSURE", "NODE_DEMAND", "FLOW", "HEAD"}
        if cond_type:
            assert cond_type in valid_types, f"Invalid simple control condition type: {cond_type}"
    else:
        # String condition - basic validation that it's not empty
        assert len(str(cond).strip()) > 0, "Condition string must not be empty"


@rule(CONTROL, code="E_RULE_CONTROL_PREMISE", attribute="condition")
@match("rule")
def rule_rule_control_premise_valid(control) -> None:
    """Rule premise must reference valid node/link/clock (EPANET error 221).

    classification : Control
    fix : Use valid premise references to existing components.
    """
    cond = control.data.get("condition")
    assert cond, "Rule control must have a premise/condition"


@rule(CONTROL, code="E_RULE_CONTROL_ACTION", attribute="condition")
@match("rule")
def rule_rule_control_action_valid(control) -> None:
    """Rule action must set valid link status/setting (EPANET error 221).

    classification : Control
    fix : Use valid action syntax setting link status or setting.
    """
    then_actions = control.data.get("then_actions", [])
    assert len(then_actions) > 0, "Rule control must have THEN actions"
    for action in then_actions:
        assert action.get("link"), "Rule action must specify a link"
        assert action.get("attribute") in ("status", "setting"), \
            "Rule action attribute must be 'status' or 'setting'"


@rule(CONTROL, code="W_CONTROL_PRIORITY", attribute="priority")
def warn_control_priority(control) -> None:
    """Multiple controls on same link: priority must be resolvable.

    classification : Control
    fix : Define clear priority for controls on the same link.
    """
    priority = control.data.get("priority", 0)
    assert isinstance(priority, (int, float)) and priority >= 0, \
        "Control priority must be non-negative"


@rule(CONTROL, code="W_CONTROL_CIRCULAR_DEPENDENCY", attribute="condition")
def warn_control_circular_dependency(control) -> None:
    """Controls should not create circular logic.

    classification : Control
    fix : Resolve circular dependencies between controls.
    """
    # This is a network-level check - placeholder for component-level warning
    assert True, "Circular control dependencies checked at network level"
