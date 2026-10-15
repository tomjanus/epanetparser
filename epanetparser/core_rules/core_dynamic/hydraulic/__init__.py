"""Hydraulic simulation validation ruleset (core, dynamic layer).

This ruleset contains validation rules that run after a hydraulic simulation
and check the simulation results for common hydraulic issues such as:

* Minimum/maximum pressure violations
* Excessive velocities
* Flow continuity errors
* Energy balance violations

These rules require a hydraulic simulation to have been run first, and are
only executed when the simulation layer is requested (``--simulate`` on the
CLI, or the simulation validation tools on the MCP server).

Select it alongside the core static rule set:

.. code-block:: python

    from epanetparser.core.validation import validate

    report = validate(network, ["epanet_core", "hydraulic"])
    # Then run simulation validation
    results = network.to_wntr().run_sim()
    validator = Validator.from_context(["epanet_core", "hydraulic"])
    report = validator.validate_simulation(results, report)

The ruleset is a core rule set of the dynamic layer: it sets
``__is_core__ = True`` and ``__layer__ = "dynamic"``. It cannot occupy the
static core slot (which must resolve to exactly one rule set that is core
*and* static); it is selected as a custom rule set alongside the static core
rule set instead. WNTR is an optional dependency, so the rules are written
without importing it: a missing installation is reported when a simulation
is run, never at discovery time.

Ruleset Metadata
----------------
__key__ : str
    Unique identifier for this ruleset ('hydraulic').
__ruleset_name__ : str
    Human-readable name of the ruleset.
__version__ : str
    Semantic version of this ruleset.
__description__ : str
    Detailed description of the ruleset's purpose and constraints.
__is_core__ : bool
    True, so this ruleset is classified as core rather than custom.
__layer__ : str
    'dynamic', the validation layer this ruleset belongs to.
"""
from epanetparser.core_rules.core_dynamic.hydraulic.rules import (
    FIRE_FLOW_PRESSURE_PSI,
    MAX_HEADLOSS_GRADIENT,
    MAX_PRESSURE_PSI,
    MAX_VELOCITY_FPS,
    MIN_PRESSURE_PSI,
    rule_energy_balance,
    rule_flow_continuity,
    rule_maximum_headloss_gradient,
    rule_maximum_pressure,
    rule_maximum_velocity,
    rule_minimum_pressure,
    rule_unmet_demand,
)
from epanetparser.core_rules.core_dynamic.hydraulic.schemas import (
    LINK_RESULTS_SCHEMA,
    NODE_RESULTS_SCHEMA,
    SIMULATION_RESULTS_SCHEMA,
    check_outputs_available,
    get_required_outputs_for_rule,
    schemas_available,
    validate_link_results,
    validate_node_results,
)

#: Re-exported rule functions, constants and schema helpers, so callers can
#: reach the whole ruleset through the package.
__all__ = [
    "FIRE_FLOW_PRESSURE_PSI",
    "LINK_RESULTS_SCHEMA",
    "MAX_HEADLOSS_GRADIENT",
    "MAX_PRESSURE_PSI",
    "MAX_VELOCITY_FPS",
    "MIN_PRESSURE_PSI",
    "NODE_RESULTS_SCHEMA",
    "SIMULATION_RESULTS_SCHEMA",
    "check_outputs_available",
    "get_required_outputs_for_rule",
    "rule_energy_balance",
    "rule_flow_continuity",
    "rule_maximum_headloss_gradient",
    "rule_maximum_pressure",
    "rule_maximum_velocity",
    "rule_minimum_pressure",
    "rule_unmet_demand",
    "schemas_available",
    "validate_link_results",
    "validate_node_results",
]

#: Stable key of this ruleset, used in a ValidationContext.
__key__ = "hydraulic"

#: Human-readable name.
__ruleset_name__ = "Hydraulic Simulation Validation"

#: Version of this ruleset.
__version__ = "1.0.0"

#: Summary of what this ruleset checks.
__description__ = (
    "Validation rules for hydraulic simulation results including pressure, "
    "velocity, headloss, flow continuity, and energy balance checks."
)

#: Marks this ruleset as a core rule set.
__is_core__ = True

#: The validation layer this ruleset belongs to: rules here run against
#: simulation results, so the layer is dynamic rather than static.
__layer__ = "dynamic"
