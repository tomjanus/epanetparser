"""Pandera schemas for simulation validation outputs.

This module defines Pandera schemas for validating the structure and content
of WNTR simulation results. These schemas can be used to validate that the
simulation produced the expected outputs with the correct types and ranges.

The schemas are used by the simulation validation rules to check that
required outputs are available before running the rules.
"""
from __future__ import annotations

try:
    import pandera as pa
    from pandera import Column, DataFrameSchema, Check
    PANDERA_AVAILABLE = True
except ImportError:
    PANDERA_AVAILABLE = False
    pa = None
    Column = None
    DataFrameSchema = None
    Check = None


# Schema for node results (pressure, demand, head, quality)
NODE_RESULTS_SCHEMA = None
LINK_RESULTS_SCHEMA = None
SIMULATION_RESULTS_SCHEMA = None

if PANDERA_AVAILABLE:
    # Node results: indexed by node name, columns for each timestep
    NODE_RESULTS_SCHEMA = DataFrameSchema(
        {
            "pressure": Column(
                float,
                Check.greater_than_or_equal_to(0),
                nullable=True,
                coerce=True,
                description="Nodal pressure (psi)",
            ),
            "demand": Column(
                float,
                Check.greater_than_or_equal_to(0),
                nullable=True,
                coerce=True,
                description="Actual demand (gpm or lps)",
            ),
            "head": Column(
                float,
                nullable=True,
                coerce=True,
                description="Hydraulic head (ft or m)",
            ),
            "quality": Column(
                float,
                Check.greater_than_or_equal_to(0),
                nullable=True,
                coerce=True,
                description="Water quality concentration",
            ),
        },
        index=pa.Index(str, description="Node name"),
        strict=False,
        coerce=True,
        description="Node simulation results (nodes x timesteps)",
    )

    # Link results: indexed by link name, columns for each timestep
    LINK_RESULTS_SCHEMA = DataFrameSchema(
        {
            "flowrate": Column(
                float,
                nullable=True,
                coerce=True,
                description="Link flow rate (gpm or lps)",
            ),
            "velocity": Column(
                float,
                Check.greater_than_or_equal_to(0),
                nullable=True,
                coerce=True,
                description="Link velocity (ft/s or m/s)",
            ),
            "headloss": Column(
                float,
                Check.greater_than_or_equal_to(0),
                nullable=True,
                coerce=True,
                description="Link headloss (ft or m)",
            ),
            "status": Column(
                str,
                Check.isin(["Open", "Closed", "CV", "Active"]),
                nullable=True,
                coerce=True,
                description="Link status",
            ),
            "setting": Column(
                float,
                nullable=True,
                coerce=True,
                description="Link setting (for pumps/valves)",
            ),
        },
        index=pa.Index(str, description="Link name"),
        strict=False,
        coerce=True,
        description="Link simulation results (links x timesteps)",
    )

    # Top-level simulation results schema
    SIMULATION_RESULTS_SCHEMA = DataFrameSchema(
        {
            "node": Column(
                object,
                nullable=False,
                coerce=False,
                description="Node results DataFrame",
            ),
            "link": Column(
                object,
                nullable=False,
                coerce=False,
                description="Link results DataFrame",
            ),
        },
        strict=False,
        coerce=False,
        description="Complete simulation results object",
    )


def validate_node_results(node_results) -> bool:
    """Validate node results against the Pandera schema.

    Parameters
    ----------
    node_results : pd.DataFrame
        Node results from WNTR simulation (nodes x timesteps).

    Returns
    -------
    bool
        True if validation passes, False otherwise.
    """
    if not PANDERA_AVAILABLE or NODE_RESULTS_SCHEMA is None:
        return True  # Skip validation if pandera not available

    try:
        NODE_RESULTS_SCHEMA.validate(node_results, lazy=True)
        return True
    except pa.errors.SchemaErrors:
        return False


def validate_link_results(link_results) -> bool:
    """Validate link results against the Pandera schema.

    Parameters
    ----------
    link_results : pd.DataFrame
        Link results from WNTR simulation (links x timesteps).

    Returns
    -------
    bool
        True if validation passes, False otherwise.
    """
    if not PANDERA_AVAILABLE or LINK_RESULTS_SCHEMA is None:
        return True

    try:
        LINK_RESULTS_SCHEMA.validate(link_results, lazy=True)
        return True
    except pa.errors.SchemaErrors:
        return False


def get_required_outputs_for_rule(rule_name: str) -> list[str]:
    """Get the required simulation outputs for a given rule.

    Parameters
    ----------
    rule_name : str
        Name of the simulation rule.

    Returns
    -------
    list[str]
        List of required output names (e.g., ["node.pressure", "link.flowrate"]).
    """
    rule_requirements = {
        "rule_minimum_pressure": ["node.pressure"],
        "rule_maximum_pressure": ["node.pressure"],
        "rule_maximum_velocity": ["link.velocity"],
        "rule_maximum_headloss_gradient": ["link.headloss"],
        "rule_flow_continuity": ["link.flowrate"],
        "rule_unmet_demand": ["node.demand"],
        "rule_energy_balance": ["node.pressure", "link.flowrate"],
    }
    return rule_requirements.get(rule_name, [])


def check_outputs_available(simulation_results, required_outputs: list[str]) -> bool:
    """Check if all required outputs are available in simulation results.

    Parameters
    ----------
    simulation_results : object
        WNTR simulation results object.
    required_outputs : list[str]
        List of required output names (e.g., ["node.pressure", "link.flowrate"]).

    Returns
    -------
    bool
        True if all required outputs are available, False otherwise.
    """
    if not hasattr(simulation_results, "node") or not hasattr(simulation_results, "link"):
        return False

    available = set()
    if hasattr(simulation_results.node, "columns"):
        available.update(f"node.{col}" for col in simulation_results.node.columns)
    if hasattr(simulation_results.link, "columns"):
        available.update(f"link.{col}" for col in simulation_results.link.columns)

    return all(req in available for req in required_outputs)