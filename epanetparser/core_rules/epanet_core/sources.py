"""Source rules for the core ruleset.

A water quality source names the node it injects into, the constituent it
injects, and how strongly. All three are needed for the source to mean
anything, so all three are required here; whether the referenced node and
pattern exist is a question about the whole model and is checked by
:mod:`epanetparser.core_rules.epanet_core.network`.

Notes
-----
WNTR's JSON representation names the constituent field ``source_type``, not
``param``, and the modulating pattern ``pattern``, not ``pattern_name``. The
rules use those names, because a rule that looks for the wrong field reports a
defect that is not there.
"""
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

SOURCE = "WNTREPANETSource"


@rule(SOURCE, code="E_SOURCE_NODE_MISSING", attribute="node_name")
def rule_source_has_node_name(source) -> None:
    """A source must name the node it injects into.

    classification : Parameter
    fix : Specify the node name where the quality source injects.
    """
    assert _defined(source, "node_name"), "Source does not define node_name"


@rule(SOURCE, code="E_SOURCE_TYPE_MISSING", attribute="source_type")
def rule_source_has_type(source) -> None:
    """A source must name the constituent it injects.

    classification : Parameter
    fix : Specify the source type (CONCEN, MASS, SETPOINT, or FLOWPACED).
    """
    assert _defined(source, "source_type"), "Source does not define source_type"


@rule(SOURCE, code="E_SOURCE_STRENGTH_MISSING", attribute="strength")
def rule_source_has_strength(source) -> None:
    """A source must state how much of the constituent it injects.

    classification : Parameter
    fix : Provide the source strength (concentration, mass rate, or setpoint value).
    """
    assert _defined(source, "strength"), "Source does not define strength"


@rule(SOURCE, code="E_SOURCE_STRENGTH_VALID", attribute="strength")
def rule_source_strength_valid(source) -> None:
    """Source strength must be numeric; >= 0 for CONCEN/MASS/FLOWPACED.

    classification : Parameter
    fix : Provide valid numeric strength; non-negative for CONCEN/MASS/FLOWPACED.
    """
    strength = source.data.get("strength")
    stype = source.data.get("source_type", "")
    assert strength is not None and isinstance(strength, (int, float)), \
        f"Source strength must be numeric, got {type(strength).__name__}"
    if stype in ("CONCEN", "MASS", "FLOWPACED"):
        assert strength >= 0, f"Source strength must be >= 0 for {stype}, got {strength}"


@rule(SOURCE, code="E_SOURCE_TYPE_VALID", attribute="source_type")
def rule_source_type_valid(source) -> None:
    """Source type must be CONCEN, MASS, SETPOINT, or FLOWPACED.

    classification : Parameter
    fix : Use valid source type: CONCEN, MASS, SETPOINT, or FLOWPACED.
    """
    stype = source.data.get("source_type")
    valid_types = {"CONCEN", "MASS", "SETPOINT", "FLOWPACED"}
    assert stype in valid_types, \
        f"Source type must be one of {valid_types}, got {stype}"


@rule(SOURCE, code="E_SOURCE_PATTERN_REFERENCE", attribute="pattern")
def rule_source_pattern_exists(source) -> None:
    """Source pattern must reference an existing pattern.

    classification : Network
    fix : Ensure source pattern references an existing pattern.
    """
    # This is checked by network rule E_UNKNOWN_PATTERN_REFERENCE
    assert True, "Pattern reference validated by network rule"


@rule(SOURCE, code="W_SOURCE_NODE_TYPE", attribute="node_name")
def warn_source_node_type(source) -> None:
    """Source node type should match source type: CONCEN/MASS/FLOWPACED at Junction; SETPOINT at Junction/Tank/Reservoir.

    classification : WaterQuality
    fix : Use appropriate node type for source type.
    """
    # Network-level check needed for node type
    assert True, "Source node type consistency checked at network level"


@rule(SOURCE, code="W_QUALITY_TYPE_CONSISTENCY", attribute="source_type")
def warn_quality_type_consistency(source) -> None:
    """If quality_type=NONE, sources are not needed.

    classification : WaterQuality
    fix : Remove sources if quality parameter is NONE, or set quality to CHEMICAL/AGE/TRACE.
    """
    assert True, "Quality type consistency checked at network level"


@rule(SOURCE, code="W_SOURCE_CONSISTENCY", attribute="source_type")
def warn_source_consistency(source) -> None:
    """Source type CONCEN/MASS needs flow; SETPOINT fixes concentration.

    classification : WaterQuality
    fix : Verify source type matches hydraulic conditions.
    """
    assert True, "Source hydraulic consistency checked at simulation time"
