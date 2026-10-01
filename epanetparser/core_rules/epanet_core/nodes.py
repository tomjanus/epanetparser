"""Node rules for the core ruleset.

These rules check the fields EPANET requires of each kind of node. Rules that
apply to only one kind carry ``@match``, so a junction is not asked for a tank
diameter.

A rule whose name begins with ``warn_`` reports at ``Severity.WARNING`` unless
it says otherwise, so a missing coordinate is a finding but not a failure.
"""
from epanetparser.core.decorators import match
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

NODE = "WNTREPANETNode"

#: Concrete node types EPANET defines.
NODE_TYPES = ("Junction", "Reservoir", "Tank")


@rule(NODE, code="E_NODE_NAME_MISSING", attribute="name")
def rule_node_has_name(node) -> None:
    """A node must have a name."""
    assert _defined(node, "name"), "Missing node must have a name"


@rule(NODE, code="W_NODE_TYPE_MISSING", attribute="node_type")
def warn_node_has_type(node) -> None:
    """A node should declare which kind of node it is."""
    assert _defined(node, "node_type"), "Node does not define type"


@rule(NODE, code="E_NODE_TYPE_UNSUPPORTED", attribute="node_type")
def rule_node_has_valid_type(node) -> None:
    """A node must be a junction, a reservoir or a tank."""
    assert node.type in NODE_TYPES, f"Unsupported node type {node.type}"


@rule(NODE, code="E_NODE_ELEVATION_MISSING", attribute="elevation")
@match("Junction")
def rule_junction_has_elevation(node) -> None:
    """A junction must have an elevation."""
    assert _defined(node, "elevation"), "Junction does not define elevation"


@rule(NODE, code="E_RESERVOIR_BASE_HEAD_MISSING", attribute="base_head")
@match("Reservoir")
def rule_reservoir_base_head(node) -> None:
    """A reservoir must have a base head."""
    assert _defined(node, "base_head"), "Reservoir does not define base_head"


@rule(NODE, code="E_TANK_DIAMETER_MISSING", attribute="diameter")
@match("Tank")
def rule_tank_has_diameter(node) -> None:
    """A tank must have a diameter."""
    assert _defined(node, "diameter"), "Tank does not define a diameter"


@rule(NODE, code="E_TANK_ELEVATION_MISSING", attribute="elevation")
@match("Tank")
def rule_tank_has_elevation(node) -> None:
    """A tank must have an elevation."""
    assert _defined(node, "elevation"), "Tank does not define elevation"


@rule(NODE, code="E_TANK_INIT_LEVEL_MISSING", attribute="init_level")
@match("Tank")
def rule_tank_has_init_level(node) -> None:
    """A tank must have an initial level."""
    assert _defined(node, "init_level"), "Tank does not define initial level"


@rule(NODE, code="E_TANK_MAX_LEVEL_MISSING", attribute="max_level")
@match("Tank")
def rule_tank_has_max_level(node) -> None:
    """A tank must have a maximum level."""
    assert _defined(node, "max_level"), "Tank does not define maximum level"


@rule(NODE, code="E_TANK_MIN_LEVEL_MISSING", attribute="min_level")
@match("Tank")
def rule_tank_has_min_level(node) -> None:
    """A tank must have a minimum level."""
    assert _defined(node, "min_level"), "Tank does not define minimum level"


@rule(NODE, code="E_TANK_MIN_VOLUME_MISSING", attribute="min_vol")
@match("Tank")
def rule_tank_has_min_volume(node) -> None:
    """A tank must have a minimum volume."""
    assert _defined(node, "min_vol"), "Tank does not define minimum volume"


@rule(NODE, code="W_NODE_COORDINATES_MISSING", attribute="coordinates")
def warn_node_missing_coord(node) -> None:
    """A node should have coordinates, otherwise it cannot be displayed."""
    assert node.coordinates, "Missing coordinates, node will not be displayed"
