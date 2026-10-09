"""MILP ruleset: constraints imposed by an example optimal pump scheduling tool.

This ruleset encodes the restrictions of one particular application: a Mixed
Integer Linear Programming formulation of pump scheduling, developed at De
Montfort University, Leicester. The formulation handles a deliberately narrow
class of network, so models outside that class are rejected here even though
they are valid EPANET models.

The distinction matters for the architecture. These constraints are *not* part
of "is this a well-formed EPANET model"; they are part of "will this model work
with our solver". That is why they live in a custom ruleset that a caller opts
into, rather than in the core ruleset that every model is checked against.

Select it alongside the core ruleset:

.. code-block:: python

    from epanetparser.core.validation import validate

    report = validate(network, ["epanet_core", "milp"])

Assumptions
-----------
The rules below encode the formulation's stated simplifications, not
properties of EPANET:

* a 24 hour schedule on a 1 hour timestep and a 2 hour pattern timestep, so
  12 pattern multipliers;
* demand-driven analysis with a fixed, unit-constrained demand model;
* no valves, no check valves, no tank overflow or volume curves, no emitters,
  and no controls, because the optimisation takes direct control of pump
  states.

Ruleset Metadata
----------------
__key__ : str
    Unique identifier for this ruleset ('milp').
__ruleset_name__ : str
    Human-readable name of the ruleset.
__version__ : str
    Semantic version of this ruleset.
__description__ : str
    Detailed description of the ruleset's purpose and constraints.
__is_core__ : bool
    Absent, so this ruleset is classified as custom rather than core.
"""
from epanetparser.core.validation import match, Severity, rule

#: Schedule horizon of the formulation, in hours.
TIME_HORIZON = 24

#: Simulation timestep required by the formulation, in hours.
TIME_STEP = 1

#: Pattern timestep required by the formulation, in hours. The formulation
#: schedules pumps on a 24 hour day, and a two hour pattern resolution is what
#: its 12 decision periods assume.
PATTERN_TIMESTEP = 2

#: Pattern multipliers implied by the horizon and the pattern timestep.
MULTIPLIER_LENGTH = TIME_HORIZON // PATTERN_TIMESTEP

#: Head loss formulations the formulation implements. C-M is not supported.
HEADLOSS_MODELS = ("D-W", "H-W")

#: Demand model the formulation implements: demand-driven, fixed demands.
DEMAND_MODEL = "DDA"

#: Flow units the formulation simulates in.
SIMULATED_FLOW_UNITS = "LPS"

NODE = "WNTREPANETNode"
LINK = "WNTREPANETLink"
PATTERN = "WNTREPANETPattern"
CONTROL = "WNTREPANETControl"
OPTIONS = "WNTREPANETOptions"

#: Stable key of this ruleset, used in a ValidationContext.
__key__ = "milp"

#: Human-readable name.
__ruleset_name__ = "Mixed Integer Linear Programming ruleset"

#: Version of this ruleset.
__version__ = "0.2.0"

#: Summary of what this ruleset checks.
__description__ = (
    "Constraints imposed by an example MILP optimal pump scheduling tool: a "
    "24 hour horizon on a 1 hour timestep and a 2 hour pattern timestep, "
    "demand-driven analysis in LPS with unit viscosity and specific gravity, "
    "no pressure unit overrides, no energy demand charge, and no use of "
    "valves, check valves, tank volume curves, tank overflow, emitters or "
    "controls."
)


@rule(PATTERN, code="E_MILP_PATTERN_LENGTH", attribute="multipliers")
def rule_pattern_length(pattern) -> None:
    """A pattern must hold one multiplier per scheduling period.

    Notes
    -----
    The expected count follows from the formulation's fixed schedule
    resolution, not from the model: see :data:`MULTIPLIER_LENGTH`. Whether the
    model agrees on that resolution is checked separately by
    :func:`rule_pattern_timestep`.

    classification : Parameter
    fix : Ensure the pattern has exactly 12 multipliers for a 24-hour horizon with 2-hour pattern timestep.
    """
    multipliers = pattern.data.get("multipliers") or []
    assert len(multipliers) == MULTIPLIER_LENGTH, (
        f"Pattern '{pattern.name}' has {len(multipliers)} multipliers, "
        f"expected {MULTIPLIER_LENGTH} for a {TIME_HORIZON} hour horizon on a "
        f"{PATTERN_TIMESTEP} hour pattern timestep"
    )


@rule(NODE, code="E_MILP_TANK_VOLUME_CURVE", attribute="vol_curve_name")
@match("Tank")
def rule_no_tank_curve(node) -> None:
    """A tank must not use a volume curve.

    Notes
    -----
    The formulation models tanks as cylinders of constant cross-section, so a
    volume curve would contradict its storage model.

    classification : Curve
    fix : Remove the volume curve reference from the tank definition.
    """
    assert node.data.get("vol_curve_name") is None, \
        "Volume curves for tanks not supported"


@rule(NODE, code="E_MILP_TANK_OVERFLOW", attribute="overflow")
@match("Tank")
def rule_no_tank_overflow(node) -> None:
    """A tank must not overflow.

    classification : Parameter
    fix : Set the tank overflow attribute to false or remove it.
    """
    assert node.data.get("overflow") in (None, False), \
        "Overflows on tanks not supported"


@rule(NODE, code="E_MILP_EMITTER", attribute="emitter_coefficient")
def rule_no_emitters(node) -> None:
    """A node must not have an emitter.

    Notes
    -----
    An emitter is an unbounded demand, which the linear formulation has no
    term for.

    classification : Parameter
    fix : Set the emitter coefficient to zero or remove the emitter definition.
    """
    assert node.emitter_coefficient in (None, 0), \
        "Emitters with nonzero coefficients not supported"


@rule(LINK, code="E_MILP_CHECK_VALVE", attribute="check_valve")
def rule_check_valves(link) -> None:
    """A link must not have a check valve.

    Notes
    -----
    The formulation takes pump states as decision variables and cannot also
    represent a state constraint arising from flow direction.

    classification : Parameter
    fix : Remove the check valve setting from the pipe definition.
    """
    assert link.data.get("check_valve") in (False, None), \
        "Check valves not supported"


@rule(LINK, code="E_MILP_VALVE", attribute="link_type")
@match("Valve")
def rule_no_valves_allowed(link) -> None:
    """A model must not contain valves.

    classification : Topology
    fix : Remove all valve links from the network model.
    """
    assert False, "Valve links not supported"


@rule(CONTROL, code="E_MILP_CONTROL", attribute="type")
def rule_no_controls_allowed(control) -> None:
    """A model must not contain controls.

    Notes
    -----
    The formulation decides pump states itself, so a control that changes them
    would contradict its own decisions.

    classification : Control
    fix : Remove all control definitions from the network model.
    """
    assert False, "Controls not supported"


@rule(OPTIONS, code="E_MILP_TIME_HORIZON", attribute="duration")
def rule_simulation_time_horizon(options) -> None:
    """The simulation must cover at least the full schedule horizon.

    classification : Option
    fix : Set the simulation duration to at least 86400 seconds (24 hours).
    """
    time_options = options.time_options or {}
    duration = time_options.get("duration")
    required = TIME_HORIZON * 3600
    assert duration is not None and duration >= required, (
        f"Simulation time horizon {duration} seconds shorter than schedule "
        f"time horizon {required} seconds"
    )


@rule(OPTIONS, code="E_MILP_TIMESTEP", attribute="hydraulic_timestep")
def rule_hydraulic_timestep(options) -> None:
    """The hydraulic timestep must equal the schedule timestep.

    classification : Option
    fix : Set the hydraulic timestep to 3600 seconds (1 hour).
    """
    time_options = options.time_options or {}
    timestep = time_options.get("hydraulic_timestep")
    required = TIME_STEP * 3600
    assert timestep == required, (
        f"Simulation timestep {timestep} seconds not equal to MILOPS "
        f"timestep {required} seconds"
    )


@rule(OPTIONS, code="E_MILP_PATTERN_TIMESTEP", attribute="pattern_timestep")
def rule_pattern_timestep(options) -> None:
    """The pattern timestep must equal the schedule's pattern resolution.

    Notes
    -----
    This is what makes :func:`rule_pattern_length` meaningful: the number of
    multipliers a pattern needs follows from the pattern timestep, so the two
    settings have to agree before a pattern length can be judged.

    classification : Option
    fix : Set the pattern timestep to 7200 seconds (2 hours).
    """
    time_options = options.time_options or {}
    timestep = time_options.get("pattern_timestep")
    required = PATTERN_TIMESTEP * 3600
    assert timestep == required, (
        f"Pattern timestep {timestep} seconds not equal to MILOPS pattern "
        f"timestep {required} seconds"
    )


@rule(OPTIONS, code="E_MILP_HEADLOSS_MODEL", attribute="headloss")
def rule_headloss_model(options) -> None:
    """The head loss formulation must be one the tool implements.

    classification : Option
    fix : Set the headloss model to either H-W (Hazen-Williams) or D-W (Darcy-Weisbach).
    """
    hydraulic_options = options.hydraulic_options or {}
    model = hydraulic_options.get("headloss")
    supported = ", ".join(HEADLOSS_MODELS)
    assert model in HEADLOSS_MODELS, \
        f"Improper headloss model {model}. Supported models {supported}"


@rule(OPTIONS, code="E_MILP_VISCOSITY", attribute="viscosity")
def rule_viscosity(options) -> None:
    """The fluid viscosity must be 1.0.

    classification : Option
    fix : Set the fluid viscosity to 1.0.
    """
    hydraulic_options = options.hydraulic_options or {}
    viscosity = hydraulic_options.get("viscosity")
    assert viscosity == 1, f"Viscosity is not 1.0: {viscosity}"


@rule(OPTIONS, code="E_MILP_SPECIFIC_GRAVITY", attribute="specific_gravity")
def rule_specific_gravity(options) -> None:
    """The fluid specific gravity must be 1.0.

    classification : Option
    fix : Set the fluid specific gravity to 1.0.
    """
    hydraulic_options = options.hydraulic_options or {}
    gravity = hydraulic_options.get("specific_gravity")
    assert gravity == 1, f"Specific gravity is not 1.0: {gravity}"


@rule(OPTIONS, code="E_MILP_DEMAND_MODEL", attribute="demand_model")
def rule_demand_model(options) -> None:
    """Demands must be fixed, not pressure driven.

    classification : Option
    fix : Set the demand model to DDA (demand-driven analysis).
    """
    hydraulic_options = options.hydraulic_options or {}
    model = hydraulic_options.get("demand_model")
    assert model == DEMAND_MODEL, \
        f"Demand model is not {DEMAND_MODEL} (fixed demand): {model}"


@rule(OPTIONS, code="E_MILP_PRESSURE_UNITS", attribute="inpfile_pressure_units")
def rule_pressure_units(options) -> None:
    """The model must not override pressure units.

    classification : Option
    fix : Remove the pressure units override from the hydraulic options.
    """
    hydraulic_options = options.hydraulic_options or {}
    units = hydraulic_options.get("inpfile_pressure_units")
    assert units is None, f"Unsupported pressure units: {units}"


@rule(OPTIONS, code="E_MILP_DEMAND_CHARGE", attribute="demand_charge")
def rule_zero_demand_charge(options) -> None:
    """The energy cost of demand must be zero.

    Notes
    -----
    The tool optimises pump operation only; a per-unit demand charge would add
    a term the formulation does not carry.

    classification : Option
    fix : Set the demand charge to zero in the energy options.
    """
    energy_options = options.energy_options or {}
    charge = energy_options.get("demand_charge")
    assert charge == 0, f"Nonzero demand charge: {charge}"


@rule(
    OPTIONS,
    code="W_MILP_INPFILE_UNITS",
    severity=Severity.WARNING,
    attribute="inpfile_units",
)
def warn_inpfile_units(options) -> None:
    """The input file's flow units should match the units being simulated.

    Notes
    -----
    The tool simulates in litres per second, so an input file written in other
    units is still usable, but its numbers will not match the simulation's.
    Reporting this as a warning rather than an error keeps such models
    simulable while making the unit mismatch visible.

    classification : Option
    fix : Convert the input file units to LPS (litres per second) or acknowledge the unit mismatch.
    """
    hydraulic_options = options.hydraulic_options or {}
    units = hydraulic_options.get("inpfile_units")
    assert units == SIMULATED_FLOW_UNITS, (
        f"Units not in {SIMULATED_FLOW_UNITS}. Units in INP file will be "
        f"different than simulated: {units}"
    )
