"""Link rules for the core ruleset.

A link is a pipe, a pump or a valve. Whether the link's endpoints exist, and
whether the curves a link names exist, is a question about the whole model and
is therefore checked by the network rules in
:mod:`epanetparser.core_rules.epanet_core.network`.
"""
from epanetparser.core.decorators import match
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

LINK = "WNTREPANETLink"

#: Concrete link types EPANET defines.
LINK_TYPES = ("Pipe", "Pump", "Valve")


@rule(LINK, code="E_LINK_NAME_MISSING", attribute="name")
def rule_link_has_name(link) -> None:
    """A link must have a name."""
    assert _defined(link, "name"), "Missing link must have a name"


@rule(LINK, code="E_LINK_TYPE_UNSUPPORTED", attribute="link_type")
def rule_link_has_valid_type(link) -> None:
    """A link must be a pipe, a pump or a valve."""
    assert link.type in LINK_TYPES, f"Unsupported link type {link.type}"


@rule(LINK, code="E_PUMP_UNDEFINED", attribute="pump_curve_name")
@match("Pump")
def rule_pump_has_curve_or_power(link) -> None:
    """A pump must be defined by a head curve or by a power rating.

    EPANET describes a pump's flow-head relation in one of two ways: by
    reference to a pump curve, or by a constant power value. A pump with
    neither has no flow-head relation at all, so it cannot be simulated.

    Notes
    -----
    ``POWER`` appears in WNTR's JSON as ``power``, and it is populated for
    every pump, including curve-defined ones, where it is derived. What
    distinguishes a curve-defined pump from a power-defined one is therefore the
    presence of ``pump_curve_name``, and only the absence of both is a defect.
    """
    has_curve = bool(link.data.get("pump_curve_name"))
    has_power = link.data.get("power") not in (None, 0)
    assert has_curve or has_power, (
        "Pump is defined by neither a pump curve nor a power rating"
    )
