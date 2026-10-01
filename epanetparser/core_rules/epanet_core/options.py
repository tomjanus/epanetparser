"""Options rules for the core ruleset.

EPANET cannot simulate a model that does not say when to simulate it, how to
compute hydraulics, or how to account for pump energy, so the time,
hydraulics and energy option groups are required.

What the settings *inside* those groups must be is not a core concern: a fixed
horizon, a fixed timestep or a particular demand model are assumptions of an
application and belong in a custom ruleset.
"""
from epanetparser.core.validation import rule

OPTIONS = "WNTREPANETOptions"

#: Option groups a model must define to be simulable.
REQUIRED_OPTION_GROUPS = ("time", "hydraulic", "energy")


@rule(OPTIONS, code="E_OPTIONS_TIME_MISSING", attribute="time")
def rule_time_section_required(options) -> None:
    """The time option group must be defined."""
    assert options.time_options is not None, "Time section not defined"


@rule(OPTIONS, code="E_OPTIONS_HYDRAULIC_MISSING", attribute="hydraulic")
def rule_hydraulic_section_required(options) -> None:
    """The hydraulics option group must be defined."""
    assert options.hydraulic_options is not None, "Hydraulics not defined"


@rule(OPTIONS, code="E_OPTIONS_ENERGY_MISSING", attribute="energy")
def rule_energy_section_required(options) -> None:
    """The energy option group must be defined."""
    assert options.energy_options is not None, "Energy options not defined"
