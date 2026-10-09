"""Node rules for the core ruleset.

These rules check the fields EPANET requires of each kind of node. Rules that
apply to only one kind carry ``@match``, so a junction is not asked for a tank
diameter.

A rule whose name begins with ``warn_`` reports at ``Severity.WARNING`` unless
it says otherwise, so a missing coordinate is a finding but not a failure.
"""
from epanetparser.core.validation import match, defined as _defined, rule

NODE = "WNTREPANETNode"

#: Concrete node types EPANET defines.
NODE_TYPES = ("Junction", "Reservoir", "Tank")


@rule(NODE, code="E_NODE_NAME_MISSING", attribute="name")
def rule_node_has_name(node) -> None:
    """A node must have a name.

    classification : Parameter
    fix : Assign a unique identifier to the node.
    """
    assert _defined(node, "name"), "Missing node must have a name"


@rule(NODE, code="W_NODE_TYPE_MISSING", attribute="node_type")
def warn_node_has_type(node) -> None:
    """A node should declare which kind of node it is.

    classification : Parameter
    fix : Specify the node type as Junction, Reservoir, or Tank.
    """
    assert _defined(node, "node_type"), "Node does not define type"


@rule(NODE, code="E_NODE_TYPE_UNSUPPORTED", attribute="node_type")
def rule_node_has_valid_type(node) -> None:
    """A node must be a junction, a reservoir or a tank.

    classification : Parameter
    fix : Change the node type to one of: Junction, Reservoir, Tank.
    """
    assert node.type in NODE_TYPES, f"Unsupported node type {node.type}"


@rule(NODE, code="E_NODE_ELEVATION_MISSING", attribute="elevation")
@match("Junction")
def rule_junction_has_elevation(node) -> None:
    """A junction must have an elevation.

    classification : Parameter
    fix : Provide the junction elevation in meters.
    """
    assert _defined(node, "elevation"), "Junction does not define elevation"


@rule(NODE, code="E_RESERVOIR_BASE_HEAD_MISSING", attribute="base_head")
@match("Reservoir")
def rule_reservoir_base_head(node) -> None:
    """A reservoir must have a base head.

    classification : Parameter
    fix : Provide the reservoir base head (hydraulic head) in meters.
    """
    assert _defined(node, "base_head"), "Reservoir does not define base_head"


@rule(NODE, code="E_TANK_DIAMETER_MISSING", attribute="diameter")
@match("Tank")
def rule_tank_has_diameter(node) -> None:
    """A tank must have a diameter.

    classification : Parameter
    fix : Provide the tank diameter in meters (must be positive).
    """
    assert _defined(node, "diameter"), "Tank does not define a diameter"


@rule(NODE, code="E_TANK_ELEVATION_MISSING", attribute="elevation")
@match("Tank")
def rule_tank_has_elevation(node) -> None:
    """A tank must have an elevation.

    classification : Parameter
    fix : Provide the tank bottom elevation in meters.
    """
    assert _defined(node, "elevation"), "Tank does not define elevation"


@rule(NODE, code="E_TANK_INIT_LEVEL_MISSING", attribute="init_level")
@match("Tank")
def rule_tank_has_init_level(node) -> None:
    """A tank must have an initial level.

    classification : Parameter
    fix : Provide the initial water level in the tank (meters above bottom).
    """
    assert _defined(node, "init_level"), "Tank does not define initial level"


@rule(NODE, code="E_TANK_MAX_LEVEL_MISSING", attribute="max_level")
@match("Tank")
def rule_tank_has_max_level(node) -> None:
    """A tank must have a maximum level.

    classification : Parameter
    fix : Provide the maximum water level in the tank (meters above bottom).
    """
    assert _defined(node, "max_level"), "Tank does not define maximum level"


@rule(NODE, code="E_TANK_MIN_LEVEL_MISSING", attribute="min_level")
@match("Tank")
def rule_tank_has_min_level(node) -> None:
    """A tank must have a minimum level.

    classification : Parameter
    fix : Provide the minimum water level in the tank (meters above bottom).
    """
    assert _defined(node, "min_level"), "Tank does not define minimum level"


@rule(NODE, code="E_TANK_MIN_VOLUME_MISSING", attribute="min_vol")
@match("Tank")
def rule_tank_has_min_volume(node) -> None:
    """A tank must have a minimum volume.

    classification : Parameter
    fix : Provide the minimum volume of the tank in cubic meters.
    """
    assert _defined(node, "min_vol"), "Tank does not define minimum volume"


@rule(NODE, code="W_NODE_COORDINATES_MISSING", attribute="coordinates")
def warn_node_missing_coord(node) -> None:
    """A node should have coordinates, otherwise it cannot be displayed.

    classification : Topology
    fix : Assign X,Y coordinates to the node for map display.
    """
    assert node.coordinates, "Missing coordinates, node will not be displayed"


@rule(NODE, code="E_JUNCTION_ELEVATION_INVALID", attribute="elevation")
@match("Junction")
def rule_junction_elevation_numeric(node) -> None:
    """Junction elevation must be numeric (EPANET error 209).

    classification : Parameter
    fix : Provide a valid numeric elevation value for the junction.
    """
    elev = node.data.get("elevation")
    assert elev is not None and isinstance(elev, (int, float)), \
        f"Junction elevation must be numeric, got {type(elev).__name__}"


@rule(NODE, code="E_RESERVOIR_BASE_HEAD_INVALID", attribute="base_head")
@match("Reservoir")
def rule_reservoir_base_head_numeric(node) -> None:
    """Reservoir base_head must be numeric (EPANET error 209).

    classification : Parameter
    fix : Provide a valid numeric base head value for the reservoir.
    """
    head = node.data.get("base_head")
    assert head is not None and isinstance(head, (int, float)), \
        f"Reservoir base_head must be numeric, got {type(head).__name__}"


@rule(NODE, code="E_TANK_ELEVATION_INVALID", attribute="elevation")
@match("Tank")
def rule_tank_elevation_numeric(node) -> None:
    """Tank elevation must be numeric (EPANET error 209).

    classification : Parameter
    fix : Provide a valid numeric elevation value for the tank bottom.
    """
    elev = node.data.get("elevation")
    assert elev is not None and isinstance(elev, (int, float)), \
        f"Tank elevation must be numeric, got {type(elev).__name__}"


@rule(NODE, code="E_JUNCTION_DEMAND_NON_NEGATIVE", attribute="base_demand")
@match("Junction")
def rule_junction_demand_non_negative(node) -> None:
    """Junction base demand must be >= 0 (EPANET error 209).

    classification : Parameter
    fix : Set base demand to a non-negative value.
    """
    demand = node.data.get("base_demand", 0)
    assert isinstance(demand, (int, float)) and demand >= 0, \
        f"Junction base demand must be >= 0, got {demand}"


@rule(NODE, code="E_JUNCTION_EMITTER_NON_NEGATIVE", attribute="emitter_coefficient")
@match("Junction")
def rule_junction_emitter_non_negative(node) -> None:
    """Junction emitter coefficient must be >= 0 if present (EPANET error 209).

    classification : Parameter
    fix : Set emitter coefficient to a non-negative value, or omit if no emitter.
    """
    emitter = node.data.get("emitter_coefficient")
    if emitter is not None:
        assert isinstance(emitter, (int, float)) and emitter >= 0, \
            f"Junction emitter coefficient must be >= 0, got {emitter}"


@rule(NODE, code="E_TANK_LEVEL_ORDERING", attribute="init_level")
@match("Tank")
def rule_tank_level_ordering(node) -> None:
    """Tank levels must satisfy: min_level <= init_level <= max_level (EPANET error 225).

    classification : Parameter
    fix : Ensure min_level <= init_level <= max_level for the tank.
    """
    min_level = node.data.get("min_level")
    init_level = node.data.get("init_level")
    max_level = node.data.get("max_level")
    assert min_level is not None and init_level is not None and max_level is not None, \
        "Tank min_level, init_level, max_level must all be defined"
    assert min_level <= init_level <= max_level, \
        f"Tank levels must satisfy min_level ({min_level}) <= init_level ({init_level}) <= max_level ({max_level})"


@rule(NODE, code="E_TANK_LEVELS_NON_NEGATIVE", attribute="min_level")
@match("Tank")
def rule_tank_levels_non_negative(node) -> None:
    """Tank min_level, init_level, max_level must be >= 0 (EPANET error 225).

    classification : Parameter
    fix : Set all tank levels (min, init, max) to non-negative values.
    """
    for field in ("min_level", "init_level", "max_level"):
        val = node.data.get(field)
        assert val is not None and isinstance(val, (int, float)) and val >= 0, \
            f"Tank {field} must be >= 0, got {val}"


@rule(NODE, code="E_TANK_DIAMETER_POSITIVE", attribute="diameter")
@match("Tank")
def rule_tank_diameter_positive(node) -> None:
    """Tank diameter must be > 0 (EPANET error 225).

    classification : Parameter
    fix : Set tank diameter to a positive value.
    """
    diam = node.data.get("diameter")
    assert diam is not None and isinstance(diam, (int, float)) and diam > 0, \
        f"Tank diameter must be > 0, got {diam}"


@rule(NODE, code="E_TANK_MIN_VOLUME_NON_NEGATIVE", attribute="min_vol")
@match("Tank")
def rule_tank_min_volume_non_negative(node) -> None:
    """Tank min_vol must be >= 0 (EPANET error 225).

    classification : Parameter
    fix : Set tank min_vol to a non-negative value.
    """
    min_vol = node.data.get("min_vol", 0)
    assert isinstance(min_vol, (int, float)) and min_vol >= 0, \
        f"Tank min_vol must be >= 0, got {min_vol}"


@rule(NODE, code="W_TANK_MAX_LEVEL_EXCEEDS_DIAMETER", attribute="max_level")
@match("Tank")
def warn_tank_max_level_exceeds_diameter(node) -> None:
    """Tank max_level should not exceed diameter for cylindrical tanks.

    classification : Parameter
    fix : Verify tank geometry; for cylindrical tanks max_level should be <= diameter.
    """
    max_level = node.data.get("max_level")
    diameter = node.data.get("diameter")
    if max_level is not None and diameter is not None:
        assert max_level <= diameter * 1.1, \
            f"Tank max_level ({max_level}) exceeds diameter ({diameter}); verify geometry"


@rule(NODE, code="W_ZERO_DEMAND_JUNCTION", attribute="base_demand")
@match("Junction")
def warn_zero_demand_junction(node) -> None:
    """Junction with zero base demand and no emitter may be unnecessary.

    classification : Engineering
    fix : Verify junction purpose; add demand/emitter or remove if not needed.
    """
    demand = node.data.get("base_demand", 0) or 0
    emitter = node.data.get("emitter_coefficient", 0) or 0
    assert demand > 0 or emitter > 0, \
        "Junction has zero demand and no emitter; verify it serves a purpose"
