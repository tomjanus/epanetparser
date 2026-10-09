Validation Categories Reference
===============================

Every validation rule in epanetparser is assigned a **category** that classifies
the type of check it performs. Categories appear in JSON/TOON output, console
reports (with ``--verbose``), and the ``epanetparser-plugins show`` command.

This reference documents all eight categories, their associated EPANET error
codes (where applicable), and example rules from the ``epanet_core`` ruleset.

Category Overview
-----------------

.. list-table::
   :header-rows: 1
   :widths: 15 15 25 45

   * - Category
     - EPANET Codes
     - Severity
     - Description
   * - :ref:`Topology <cat-topology>`
     - 219, 220, 222, 223, 224, 233, 234
     - ERROR / WARNING
     - Network structure: connectivity, loops, valve placement, dead ends
   * - :ref:`Parameter <cat-parameter>`
     - 202, 208, 209, 211, 213, 225, 227
     - ERROR / WARNING
     - Component field values: ranges, required fields, numeric validity
   * - :ref:`Curve <cat-curve>`
     - 227, 230
     - ERROR / WARNING
     - Curve well-formedness: points, types, semantics, monotonicity
   * - :ref:`Control <cat-control>`
     - 207, 221
     - ERROR
     - Control logic: rule clauses, simple/rule controls, circular refs
   * - :ref:`Network <cat-network>`
     - 203, 204, 205, 206, 212, 216
     - ERROR
     - Cross-component references: names, curves, patterns, pumps
   * - :ref:`Option <cat-option>`
     - 200, 201, 210, 214, 215, 217, 218, 226, 228, 229, 231, 232
     - ERROR / WARNING
     - Simulation options: time, hydraulic, quality, energy, reactions
   * - :ref:`Energy <cat-energy>`
     - 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246
     - ERROR / WARNING
     - Energy/pumping: efficiency curves, prices, patterns, global settings
   * - :ref:`Engineering <cat-engineering>`
     - (judgment)
     - WARNING
     - Heuristics: valve authority, tank turnover, demand patterns, duplicates

.. _cat-topology:

Topology
--------

**EPANET error codes**: 219, 220, 222, 223, 224, 233, 234

Checks the physical structure and connectivity of the network. These are
structural constraints that EPANET itself enforces.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Rule Code
     - Severity
     - Description
   * - ``E_VALVE_TANK_CONNECTION``
     - ERROR
     - Valves cannot connect to Tank or Reservoir nodes (EPANET 219)
   * - ``E_VALVE_VALVE_CONNECTION``
     - ERROR
     - Valves cannot connect directly to other valves (EPANET 220)
   * - ``E_SELF_LOOP_LINK``
     - ERROR
     - A link must not connect a node to itself (EPANET 222)
   * - ``E_NETWORK_HAS_TANK_OR_RESERVOIR``
     - ERROR
     - Network must have at least one tank or reservoir (EPANET 224)
   * - ``E_UNCONNECTED_NODE``
     - ERROR
     - All demand nodes must be hydraulically connected (EPANET 233/234)
   * - ``E_PARALLEL_LINKS``
     - ERROR
     - Multiple links connecting the same node pair (duplicate detection)
   * - ``W_DEAD_END_JUNCTION``
     - WARNING
     - Junctions with degree=1 and no demand/emitter are suspicious
   * - ``E_VALVE_ONLY_CONNECTION``
     - ERROR
     - Junctions connected only via valves cannot be pressure-driven
   * - ``W_DUPLICATE_COORDINATES``
     - WARNING
     - Multiple nodes with identical coordinates
   * - ``W_NODE_COORDINATES_MISSING``
     - WARNING
     - Nodes without coordinates cannot be displayed on a map

.. _cat-parameter:

Parameter
---------

**EPANET error codes**: 202, 208, 209, 211, 213, 225, 227

Validates individual component field values: required fields present, numeric
types, value ranges, and logical constraints (e.g., tank level ordering).

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_NODE_NAME_MISSING``
     - ERROR
     - A node must have a name
   * - ``E_NODE_ELEVATION_MISSING``
     - ERROR
     - Junctions must have elevation (EPANET 209)
   * - ``E_RESERVOIR_BASE_HEAD_MISSING``
     - ERROR
     - Reservoirs must have base_head (EPANET 209)
   * - ``E_TANK_DIAMETER_MISSING``
     - ERROR
     - Tanks must have diameter (EPANET 225)
   * - ``E_TANK_LEVEL_ORDERING``
     - ERROR
     - Tank levels must satisfy min ≤ init ≤ max (EPANET 225)
   * - ``E_TANK_LEVELS_NON_NEGATIVE``
     - ERROR
     - Tank min_level, init_level, max_level ≥ 0 (EPANET 225)
   * - ``E_TANK_DIAMETER_POSITIVE``
     - ERROR
     - Tank diameter must be > 0 (EPANET 225)
   * - ``E_TANK_MIN_VOLUME_NON_NEGATIVE``
     - ERROR
     - Tank min_vol ≥ 0 (EPANET 225)
   * - ``E_JUNCTION_DEMAND_NON_NEGATIVE``
     - ERROR
     - Junction base demand ≥ 0 (EPANET 209)
   * - ``E_JUNCTION_EMITTER_NON_NEGATIVE``
     - ERROR
     - Junction emitter coefficient ≥ 0 (EPANET 209)
   * - ``E_LINK_LENGTH_POSITIVE``
     - ERROR
     - Pipe length must be > 0 (EPANET 209)
   * - ``E_LINK_DIAMETER_POSITIVE``
     - ERROR
     - Pipe diameter must be > 0 (EPANET 209)
   * - ``E_LINK_ROUGHNESS_NON_NEGATIVE``
     - ERROR
     - Pipe roughness ≥ 0 (EPANET 209)
   * - ``E_PUMP_POWER_NON_NEGATIVE``
     - ERROR
     - Pump power ≥ 0 (EPANET 209)
   * - ``E_VALVE_SETTING_NON_NEGATIVE``
     - ERROR
     - Valve setting ≥ 0 (EPANET 209)
   * - ``W_TANK_MAX_LEVEL_EXCEEDS_DIAMETER``
     - WARNING
     - Tank max_level should not exceed diameter for cylindrical tanks
   * - ``W_ZERO_DEMAND_JUNCTION``
     - WARNING
     - Junction with zero demand and no emitter may be unnecessary

.. _cat-curve:

Curve
-----

**EPANET error codes**: 227, 230

Validates curve well-formedness: minimum points, sorted x-values, no duplicate
x-values, and semantic correctness for pump/efficiency/headloss/volume curves.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_CURVE_NAME_MISSING``
     - ERROR
     - A curve must have a name
   * - ``E_CURVE_TYPE_UNSUPPORTED``
     - ERROR
     - Curve type must be HEAD, PUMP, EFFICIENCY, or VOLUME
   * - ``E_CURVE_POINTS_MISSING``
     - ERROR
     - A curve must have at least one point
   * - ``E_CURVE_POINTS_MIN_COUNT``
     - ERROR
     - A curve must have at least 2 points for interpolation
   * - ``E_CURVE_POINTS_SORTED``
     - ERROR
     - Curve x-values must be strictly increasing
   * - ``E_CURVE_DUPLICATE_X``
     - ERROR
     - Curve x-values must be unique (no duplicate x)
   * - ``E_PUMP_CURVE_HEAD_NON_NEGATIVE``
     - ERROR
     - Pump curve y-values (head) must be ≥ 0
   * - ``E_EFFICIENCY_CURVE_RANGE``
     - ERROR
     - Efficiency curve y-values must be in [0, 100]
   * - ``E_HEADLOSS_CURVE_NON_NEGATIVE``
     - ERROR
     - Headloss curve y-values must be ≥ 0
   * - ``E_VOLUME_CURVE_MONOTONIC``
     - ERROR
     - Volume curve y-values must be strictly increasing

.. _cat-control:

Control
-------

**EPANET error codes**: 207, 221

Validates control logic: rule control clause structure, simple control syntax,
and circular dependency detection.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_CONTROL_RULE_CLAUSE_STRUCTURE``
     - ERROR
     - Rule control IF/THEN/ELSE clauses must be well-formed
   * - ``E_CONTROL_SIMPLE_SYNTAX``
     - ERROR
     - Simple control must have valid link/status/setting
   * - ``E_CONTROL_RULE_CIRCULAR``
     - ERROR
     - Rule controls must not have circular dependencies
   * - ``E_CONTROL_LINK_EXISTS``
     - ERROR
     - Control must reference an existing link
   * - ``E_CONTROL_NODE_EXISTS``
     - ERROR
     - Control condition must reference an existing node
   * - ``W_CONTROL_UNUSED``
     - WARNING
     - Control references a link not in the network

.. _cat-network:

Network
-------

**EPANET error codes**: 203, 204, 205, 206, 212, 216

Cross-component reference resolution: ensuring every name used in one component
exists in the appropriate collection.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_UNKNOWN_NODE_REFERENCE``
     - ERROR
     - Link endpoints must reference existing nodes (EPANET 203)
   * - ``E_UNKNOWN_CURVE_REFERENCE``
     - ERROR
     - Pump/efficiency/headloss/volume curves must exist (EPANET 204)
   * - ``E_UNKNOWN_PATTERN_REFERENCE``
     - ERROR
     - Demand/head patterns must exist (EPANET 205)
   * - ``E_UNKNOWN_COMPONENT_REFERENCE``
     - ERROR
     - Source node/pattern must exist (EPANET 206)
   * - ``E_UNKNOWN_LINK_REFERENCE``
     - ERROR
     - Control link must exist (EPANET 212)
   * - ``E_UNKNOWN_TRACE_NODE``
     - ERROR
     - Quality trace_node must reference existing node (EPANET 216)
   * - ``E_UNKNOWN_PUMP_REFERENCE``
     - ERROR
     - Energy section pump references must exist
   * - ``E_DUPLICATE_COMPONENT_NAME``
     - ERROR
     - Component names unique within collection
   * - ``E_NETWORK_HAS_NODES``
     - ERROR
     - Network must have at least one node
   * - ``E_NETWORK_HAS_LINKS``
     - ERROR
     - Network must have at least one link
   * - ``E_NETWORK_NAME_MISSING``
     - ERROR
     - Network must have a name (from [TITLE])

.. _cat-option:

Option
------

**EPANET error codes**: 200, 201, 210, 214, 215, 217, 218, 226, 228, 229, 231, 232

Validates simulation options across all categories: time, hydraulic, quality,
energy, and reaction options.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_TIME_OPTIONS_PRESENT``
     - ERROR
     - Time options section must be present
   * - ``E_DURATION_POSITIVE``
     - ERROR
     - Duration must be > 0
   * - ``E_HYDRAULIC_TIMESTEP_POSITIVE``
     - ERROR
     - Hydraulic timestep must be > 0
   * - ``E_QUALITY_TIMESTEP_POSITIVE``
     - ERROR
     - Quality timestep must be > 0
   * - ``E_PATTERN_TIMESTEP_POSITIVE``
     - ERROR
     - Pattern timestep must be > 0
   * - ``E_PATTERN_TIMESTEP_DIVIDES_HYDRAULIC``
     - ERROR
     - Pattern timestep must divide hydraulic timestep
   * - ``E_REPORT_TIMESTEP_POSITIVE``
     - ERROR
     - Report timestep must be > 0
   * - ``E_START_CLOCKTIME_VALID``
     - ERROR
     - Start clocktime must be valid HH:MM format
   * - ``E_HYDRAULIC_OPTIONS_PRESENT``
     - ERROR
     - Hydraulic options section must be present
   * - ``E_HEADLOSS_FORMULA_VALID``
     - ERROR
     - Headloss formula must be H-W, D-W, or C-M
   * - ``E_DEMAND_MODEL_VALID``
     - ERROR
     - Demand model must be DD or PDA
   * - ``E_MINIMUM_PRESSURE_NON_NEGATIVE``
     - ERROR
     - Minimum pressure (PDA) must be ≥ 0
   * - ``E_REQUIRED_PRESSURE_POSITIVE``
     - ERROR
     - Required pressure (PDA) must be > 0
   * - ``E_PRESSURE_EXPONENT_VALID``
     - ERROR
     - Pressure exponent (PDA) must be in [0, 1]
   * - ``E_QUALITY_OPTIONS_PRESENT``
     - ERROR
     - Quality options section must be present
   * - ``E_QUALITY_TYPE_VALID``
     - ERROR
     - Quality type must be NONE, CHEMICAL, AGE, or TRACE
   * - ``E_TRACE_NODE_EXISTS``
     - ERROR
     - Trace node must exist when quality type is TRACE
   * - ``E_REACTION_OPTIONS_PRESENT``
     - ERROR
     - Reaction options section must be present
   * - ``E_BULK_ORDER_VALID``
     - ERROR
     - Bulk reaction order must be ≥ 0
   * - ``E_WALL_ORDER_VALID``
     - ERROR
     - Wall reaction order must be ≥ 0
   * - ``E_TANK_ORDER_VALID``
     - ERROR
     - Tank reaction order must be ≥ 0
   * - ``E_GLOBAL_BULK_COEFF_VALID``
     - ERROR
     - Global bulk coefficient must be valid
   * - ``E_GLOBAL_WALL_COEFF_VALID``
     - ERROR
     - Global wall coefficient must be valid
   * - ``E_LIMITING_CONCENTRATION_NON_NEGATIVE``
     - ERROR
     - Limiting concentration must be ≥ 0

.. _cat-energy:

Energy
------

**EPANET error codes**: 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246

Validates energy and pumping options: efficiency curves, pump efficiency ranges,
global efficiency, price patterns, and pump-specific settings.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``E_ENERGY_OPTIONS_PRESENT``
     - ERROR
     - Energy options section must be present if pumps exist
   * - ``E_PUMP_EFFICIENCY_CURVE``
     - ERROR
     - Pump efficiency curve must be EFFICIENCY type
   * - ``E_PUMP_EFFICIENCY_RANGE``
     - ERROR
     - Pump efficiency curve values must be in [0, 100]
   * - ``E_GLOBAL_EFFICIENCY``
     - ERROR
     - Global efficiency (when no curve) must be in (0, 100]
   * - ``E_ENERGY_PRICE_PATTERN``
     - ERROR
     - Energy price pattern must reference existing pattern
   * - ``E_ENERGY_GLOBAL_PATTERN``
     - ERROR
     - Global energy pattern must exist
   * - ``E_ENERGY_PUMP_PRICE_PATTERN``
     - ERROR
     - Per-pump price patterns must exist
   * - ``E_ENERGY_PUMP_PATTERN``
     - ERROR
     - Per-pump energy patterns must exist
   * - ``E_ENERGY_PUMP_EFFICIENCY``
     - ERROR
     - Per-pump efficiency curves must be EFFICIENCY type
   * - ``W_PUMP_NO_EFFICIENCY``
     - WARNING
     - Pump has no efficiency curve and no global efficiency
   * - ``W_TANK_TURNOVER_LOW``
     - WARNING
     - Tank volume / avg daily demand > 7 days (low turnover)
   * - ``W_TANK_TURNOVER_HIGH``
     - WARNING
     - Tank volume / avg daily demand < 0.5 days (high turnover)
   * - ``W_VALVE_AUTHORITY_LOW``
     - WARNING
     - PRV/PSV authority < 0.25 indicates poor control

.. _cat-engineering:

Engineering
-----------

**EPANET error codes**: (judgment-based, not in EPANET spec)

Heuristic warnings based on engineering best practices. These do not correspond
to EPANET error codes but flag configurations that are legal yet questionable.

Example rules (``epanet_core``):

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Severity
     - Description
   * - ``W_DEMAND_PATTERN_FLAT``
     - WARNING
     - Demand pattern all 1.0 (no diurnal variation)
   * - ``W_NO_DEMAND_PATTERN``
     - WARNING
     - Junction has demand but no pattern assigned
   * - ``W_MULTIPLE_SOURCES_SAME_NODE``
     - WARNING
     - Multiple quality sources at same node
   * - ``W_RESERVOIR_NO_PATTERN``
     - WARNING
     - Reservoir has no head pattern (constant head)
   * - ``W_ZERO_DEMAND_JUNCTION``
     - WARNING
     - Junction with zero demand and no emitter may be unnecessary
   * - ``W_TANK_MAX_LEVEL_EXCEEDS_DIAMETER``
     - WARNING
     - Tank max_level should not exceed diameter
   * - ``W_DEAD_END_JUNCTION``
     - WARNING
     - Dead-end junctions with no demand/emitter
   * - ``W_DUPLICATE_COORDINATES``
     - WARNING
     - Multiple nodes with identical coordinates
   * - ``W_NODE_COORDINATES_MISSING``
     - WARNING
     - Nodes without coordinates cannot be displayed

MILP Custom Ruleset Categories
------------------------------

The ``milp`` custom ruleset adds application-specific constraints:

.. list-table::
   :header-rows: 1
   :widths: 35 10 55

   * - Rule Code
     - Category
     - Description
   * - ``E_MILP_TIMESTEP``
     - Option
     - Hydraulic timestep must match MILP timestep (3600s)
   * - ``E_MILP_DURATION``
     - Option
     - Duration must be multiple of MILP timestep
   * - ``E_MILP_PATTERN_LENGTH``
     - Option
     - Pattern length must be 24 hours
   * - ``E_MILP_INPFILE_UNITS``
     - Parameter
     - Units must be LPS (not GPM)
   * - ``E_MILP_HEADLOSS_FORMULA``
     - Option
     - Headloss must be Hazen-Williams
   * - ``E_MILP_DEMAND_MODEL``
     - Option
     - Demand model must be DD (not PDA)
   * - ``E_MILP_QUALITY_TYPE``
     - Option
     - Quality must be NONE
   * - ``E_MILP_REACTIONS``
     - Option
     - Reactions must be disabled
   * - ``E_MILP_VALVE``
     - Topology
     - Valve links not supported
   * - ``E_MILP_CHECK_VALVE``
     - Control
     - Check valves not supported
   * - ``E_MILP_GPV``
     - Control
     - General purpose valves not supported
   * - ``E_MILP_EMITTER``
     - Parameter
     - Emitters not supported
   * - ``E_MILP_CONTROL``
     - Control
     - Controls not supported
   * - ``E_MILP_SOURCE``
     - Network
     - Sources not supported
   * - ``E_MILP_CURVE_TYPE``
     - Curve
     - Only HEAD pump curves supported
   * - ``W_MILP_*``
     - Engineering
     - Various MILP-specific warnings

Using Categories in Custom Rules
--------------------------------

When writing custom rules, include the ``classification`` field in the docstring:

.. code-block:: python

    from epanetparser.core.validation import rule

    @rule("WNTREPANETLink", code="E_MY_CUSTOM_RULE", attribute="length")
    def rule_my_custom_check(link) -> None:
        """Pipe length must not exceed 1000m for this application.

        classification : Parameter
        fix : Reduce pipe length or split into shorter segments.
        """
        length = link.data.get("length", 0)
        assert length <= 1000, f"Pipe length {length}m exceeds 1000m limit"

The category must be one of the eight standard categories listed above. This
ensures consistent reporting and enables filtering by category in downstream
tooling.

See Also
--------

- :doc:`rules` — How to write rules and rule sets
- :doc:`usage` — CLI options for filtering and displaying categories
- :doc:`library` — Python API for accessing issue categories