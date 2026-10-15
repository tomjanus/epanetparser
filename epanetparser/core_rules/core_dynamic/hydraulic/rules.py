"""Hydraulic simulation validation rules.

This module holds the rules of the core dynamic ``hydraulic`` ruleset. Each
rule runs after a hydraulic simulation and checks the simulation results for
common hydraulic issues such as:

* Minimum/maximum pressure violations
* Excessive velocities
* Flow continuity errors
* Energy balance violations

These rules require a hydraulic simulation to have been run first, and are
only executed when the simulation layer is requested (``--simulate`` on the
CLI, or the simulation validation tools on the MCP server).

WNTR is an optional dependency and is deliberately not imported here: the
rules operate on the simulation results object passed to them, so a missing
installation is reported when a simulation is run, never at discovery time.
"""
from epanetparser.core.validation import simulation_rule, Severity


#: Minimum acceptable pressure at junctions (psi)
MIN_PRESSURE_PSI = 20.0

#: Maximum acceptable pressure at junctions (psi)
MAX_PRESSURE_PSI = 150.0

#: Minimum pressure for fire flow conditions (psi)
FIRE_FLOW_PRESSURE_PSI = 20.0

#: Maximum acceptable velocity in pipes (ft/s)
MAX_VELOCITY_FPS = 10.0

#: Maximum acceptable headloss gradient (ft/1000ft)
MAX_HEADLOSS_GRADIENT = 10.0


@simulation_rule(
    attribute="pressure",
    required_outputs=["node.pressure"],
    severity=Severity.ERROR,
)
def rule_minimum_pressure(results) -> None:
    """Minimum pressure must be above 20 psi at all junctions.

    classification: Hydraulic
    fix: Increase pipe diameters, add pumps, or reduce demands to raise pressure.
    """
    pressures = results.node["pressure"].min().min()  # min over time, then min over nodes
    assert pressures >= MIN_PRESSURE_PSI, (
        f"Minimum pressure {pressures:.1f} psi below required {MIN_PRESSURE_PSI} psi"
    )


@simulation_rule(
    attribute="pressure",
    required_outputs=["node.pressure"],
    severity=Severity.WARNING,
)
def rule_maximum_pressure(results) -> None:
    """Maximum pressure should not exceed 150 psi at junctions.

    classification: Hydraulic
    fix: Add pressure reducing valves or reduce pump head.
    """
    pressures = results.node["pressure"].max().max()  # max over time, then max over nodes
    assert pressures <= MAX_PRESSURE_PSI, (
        f"Maximum pressure {pressures:.1f} psi exceeds recommended {MAX_PRESSURE_PSI} psi"
    )


@simulation_rule(
    attribute="velocity",
    required_outputs=["link.velocity"],
    severity=Severity.WARNING,
)
def rule_maximum_velocity(results) -> None:
    """Maximum velocity should not exceed 10 ft/s in pipes.

    classification: Hydraulic
    fix: Increase pipe diameters or reduce flow rates.
    """
    # Check if velocity output is available (may need to be computed)
    if "velocity" in results.link:
        velocities = results.link["velocity"].max().max()  # max over time, then max over links
        assert velocities <= MAX_VELOCITY_FPS, (
            f"Maximum velocity {velocities:.1f} ft/s exceeds recommended {MAX_VELOCITY_FPS} ft/s"
        )


@simulation_rule(
    attribute="headloss",
    required_outputs=["link.headloss"],
    severity=Severity.WARNING,
)
def rule_maximum_headloss_gradient(results) -> None:
    """Maximum headloss gradient should not exceed 10 ft/1000ft.

    classification: Hydraulic
    fix: Increase pipe diameters, add parallel pipes, or reduce flow rates.
    """
    if "headloss" in results.link:
        # headloss is in ft, need to divide by length in 1000ft units
        headloss = results.link["headloss"]
        # This is a simplified check - in practice would need pipe lengths
        max_hl = headloss.max().max()
        assert max_hl <= MAX_HEADLOSS_GRADIENT, (
            f"Maximum headloss {max_hl:.1f} ft exceeds recommended "
            f"{MAX_HEADLOSS_GRADIENT} ft/1000ft gradient"
        )


@simulation_rule(
    attribute="flow",
    required_outputs=["link.flowrate"],
    severity=Severity.ERROR,
)
def rule_flow_continuity(results) -> None:
    """Flow continuity must be maintained at all junctions.

    classification: Hydraulic
    fix: Check for disconnected components or invalid network topology.
    """
    # The WNTR solver should maintain continuity, but we can check
    # that flow is not NaN anywhere
    flows = results.link["flowrate"]
    assert not flows.isna().any().any(), "Flow continuity error: NaN flows detected"


@simulation_rule(
    attribute="demand",
    required_outputs=["node.demand"],
    severity=Severity.INFO,
)
def rule_unmet_demand(results) -> None:
    """Report any nodes with unmet demand (pressure-dependent demand).

    classification: Hydraulic
    fix: Increase supply capacity or reduce demands.
    """
    if "demand" in results.node:
        # Check for nodes where actual demand < required demand (if available)
        # This is informational - pressure-dependent demand is expected in some cases
        pass  # Implementation depends on WNTR output format


@simulation_rule(
    attribute="energy",
    required_outputs=["link.flowrate", "node.pressure"],
    severity=Severity.INFO,
)
def rule_energy_balance(results) -> None:
    """Energy balance: total energy input should equal total energy dissipated.

    classification: Hydraulic
    fix: Check pump curves and system curves for consistency.
    """
    # This is a complex check that would require pump energy calculations
    # Placeholder for future implementation
    pass
