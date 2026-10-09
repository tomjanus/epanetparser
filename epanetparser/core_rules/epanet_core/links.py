"""Link rules for the core ruleset.

A link is a pipe, a pump or a valve. Whether the link's endpoints exist, and
whether the curves a link names exist, is a question about the whole model and
is therefore checked by the network rules in
:mod:`epanetparser.core_rules.epanet_core.network`.
"""
from epanetparser.core.validation import match, defined as _defined, rule

LINK = "WNTREPANETLink"

#: Concrete link types EPANET defines.
LINK_TYPES = ("Pipe", "Pump", "Valve")


@rule(LINK, code="E_LINK_NAME_MISSING", attribute="name")
def rule_link_has_name(link) -> None:
    """A link must have a name.

    classification : Parameter
    fix : Assign a unique identifier to the link.
    """
    assert _defined(link, "name"), "Missing link must have a name"


@rule(LINK, code="E_LINK_TYPE_UNSUPPORTED", attribute="link_type")
def rule_link_has_valid_type(link) -> None:
    """A link must be a pipe, a pump or a valve.

    classification : Parameter
    fix : Change the link type to one of: Pipe, Pump, Valve.
    """
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

    classification : Curve
    fix : Provide either a pump curve name or a power rating for the pump.
    """
    has_curve = bool(link.data.get("pump_curve_name"))
    has_power = link.data.get("power") not in (None, 0)
    assert has_curve or has_power, (
        "Pump is defined by neither a pump curve nor a power rating"
    )


@rule(LINK, code="E_PIPE_LENGTH_POSITIVE", attribute="length")
@match("Pipe")
def rule_pipe_length_positive(link) -> None:
    """Pipe length must be > 0 (EPANET error 211).

    classification : Parameter
    fix : Set pipe length to a positive value.
    """
    length = link.data.get("length")
    assert length is not None and isinstance(length, (int, float)) and length > 0, \
        f"Pipe length must be > 0, got {length}"


@rule(LINK, code="E_PIPE_DIAMETER_POSITIVE", attribute="diameter")
@match("Pipe")
def rule_pipe_diameter_positive(link) -> None:
    """Pipe diameter must be > 0 (EPANET error 211).

    classification : Parameter
    fix : Set pipe diameter to a positive value.
    """
    diam = link.data.get("diameter")
    assert diam is not None and isinstance(diam, (int, float)) and diam > 0, \
        f"Pipe diameter must be > 0, got {diam}"


@rule(LINK, code="E_PIPE_ROUGHNESS_POSITIVE", attribute="roughness")
@match("Pipe")
def rule_pipe_roughness_positive(link) -> None:
    """Pipe roughness must be > 0 (EPANET error 211).

    classification : Parameter
    fix : Set pipe roughness to a positive value.
    """
    rough = link.data.get("roughness")
    assert rough is not None and isinstance(rough, (int, float)) and rough > 0, \
        f"Pipe roughness must be > 0, got {rough}"


@rule(LINK, code="E_PIPE_MINOR_LOSS_NON_NEGATIVE", attribute="minor_loss")
@match("Pipe")
def rule_pipe_minor_loss_non_negative(link) -> None:
    """Pipe minor loss coefficient must be >= 0 (EPANET error 211).

    classification : Parameter
    fix : Set pipe minor loss coefficient to a non-negative value.
    """
    mloss = link.data.get("minor_loss")
    if mloss is not None:
        assert isinstance(mloss, (int, float)) and mloss >= 0, \
            f"Pipe minor loss must be >= 0, got {mloss}"


@rule(LINK, code="E_PIPE_INIT_STATUS_VALID", attribute="initial_status")
@match("Pipe")
def rule_pipe_initial_status_valid(link) -> None:
    """Pipe initial_status must be OPEN or CLOSED (EPANET error 211).

    classification : Parameter
    fix : Set initial_status to OPEN or CLOSED.
    """
    status = link.data.get("initial_status")
    if status is not None:
        assert status.upper() in ("OPEN", "CLOSED"), \
            f"Pipe initial_status must be OPEN or CLOSED, got {status}"


@rule(LINK, code="E_PIPE_BULK_COEFF_NON_NEGATIVE", attribute="bulk_coeff")
@match("Pipe")
def rule_pipe_bulk_coeff_non_negative(link) -> None:
    """Pipe bulk reaction coefficient must be >= 0 if present (EPANET error 211).

    classification : Parameter
    fix : Set bulk reaction coefficient to a non-negative value, or omit if not used.
    """
    coeff = link.data.get("bulk_coeff")
    if coeff is not None:
        assert isinstance(coeff, (int, float)) and coeff >= 0, \
            f"Pipe bulk_coeff must be >= 0, got {coeff}"


@rule(LINK, code="E_PIPE_WALL_COEFF_NON_NEGATIVE", attribute="wall_coeff")
@match("Pipe")
def rule_pipe_wall_coeff_non_negative(link) -> None:
    """Pipe wall reaction coefficient must be >= 0 if present (EPANET error 211).

    classification : Parameter
    fix : Set wall reaction coefficient to a non-negative value, or omit if not used.
    """
    coeff = link.data.get("wall_coeff")
    if coeff is not None:
        assert isinstance(coeff, (int, float)) and coeff >= 0, \
            f"Pipe wall_coeff must be >= 0, got {coeff}"


@rule(LINK, code="E_PUMP_POWER_POSITIVE", attribute="power")
@match("Pump")
def rule_pump_power_positive(link) -> None:
    """Pump power must be > 0 if power-defined (EPANET error 211).

    classification : Parameter
    fix : Set pump power to a positive value.
    """
    power = link.data.get("power")
    has_curve = bool(link.data.get("pump_curve_name"))
    if not has_curve and power is not None:
        assert isinstance(power, (int, float)) and power > 0, \
            f"Power-defined pump must have power > 0, got {power}"


@rule(LINK, code="E_PUMP_SPEED_NON_NEGATIVE", attribute="speed")
@match("Pump")
def rule_pump_speed_non_negative(link) -> None:
    """Pump speed must be >= 0 (EPANET error 211).

    classification : Parameter
    fix : Set pump speed to a non-negative value.
    """
    speed = link.data.get("speed")
    if speed is not None:
        assert isinstance(speed, (int, float)) and speed >= 0, \
            f"Pump speed must be >= 0, got {speed}"


@rule(LINK, code="E_PUMP_INIT_STATUS_VALID", attribute="initial_status")
@match("Pump")
def rule_pump_initial_status_valid(link) -> None:
    """Pump initial_status must be OPEN or CLOSED (EPANET error 211).

    classification : Parameter
    fix : Set initial_status to OPEN or CLOSED.
    """
    status = link.data.get("initial_status")
    if status is not None:
        assert status.upper() in ("OPEN", "CLOSED"), \
            f"Pump initial_status must be OPEN or CLOSED, got {status}"


@rule(LINK, code="E_VALVE_DIAMETER_POSITIVE", attribute="diameter")
@match("Valve")
def rule_valve_diameter_positive(link) -> None:
    """Valve diameter must be > 0 (EPANET error 211).

    classification : Parameter
    fix : Set valve diameter to a positive value.
    """
    diam = link.data.get("diameter")
    assert diam is not None and isinstance(diam, (int, float)) and diam > 0, \
        f"Valve diameter must be > 0, got {diam}"


@rule(LINK, code="E_VALVE_SETTING_NON_NEGATIVE", attribute="setting")
@match("Valve")
def rule_valve_setting_non_negative(link) -> None:
    """Valve setting must be >= 0 (EPANET error 211).

    classification : Parameter
    fix : Set valve setting to a non-negative value.
    """
    setting = link.data.get("setting")
    if setting is not None:
        assert isinstance(setting, (int, float)) and setting >= 0, \
            f"Valve setting must be >= 0, got {setting}"


@rule(LINK, code="E_VALVE_INIT_STATUS_VALID", attribute="initial_status")
@match("Valve")
def rule_valve_initial_status_valid(link) -> None:
    """Valve initial_status must be OPEN, CLOSED, or ACTIVE (EPANET error 211).

    classification : Parameter
    fix : Set initial_status to OPEN, CLOSED, or ACTIVE.
    """
    status = link.data.get("initial_status")
    if status is not None:
        assert status.upper() in ("OPEN", "CLOSED", "ACTIVE"), \
            f"Valve initial_status must be OPEN, CLOSED, or ACTIVE, got {status}"


@rule(LINK, code="E_VALVE_TYPE_VALID", attribute="valve_type")
@match("Valve")
def rule_valve_type_valid(link) -> None:
    """Valve type must be one of PRV, PSV, PBV, FCV, TCV, GPV (EPANET error 211).

    classification : Parameter
    fix : Use a valid valve type: PRV, PSV, PBV, FCV, TCV, or GPV.
    """
    vtype = link.data.get("valve_type")
    valid_types = {"PRV", "PSV", "PBV", "FCV", "TCV", "GPV"}
    assert vtype in valid_types, \
        f"Valve type must be one of {valid_types}, got {vtype}"


@rule(LINK, code="E_CONTROL_CV_GPV", attribute="check_valve")
@match("Pipe")
def rule_no_control_on_cv_gpv(link) -> None:
    """Cannot control a check valve (CV) or GPV link (EPANET error 207).

    classification : Control
    fix : Remove control from check valve pipes or GPV valves.
    """
    check_valve = link.data.get("check_valve", False)
    # Note: GPV check would need valve type check, done in network rule
    assert not check_valve, "Cannot control a pipe with check valve (CV)"


@rule(LINK, code="W_PIPE_ROUGHNESS_UNREALISTIC", attribute="roughness")
@match("Pipe")
def warn_pipe_roughness_unrealistic(link) -> None:
    """Pipe roughness should be within typical material ranges (EPANET error 211).

    classification : Engineering
    fix : Verify roughness matches pipe material and age; typical range 0.001-100 mm.
    """
    rough = link.data.get("roughness")
    if rough is not None and isinstance(rough, (int, float)):
        # Warn if outside typical range (H-W: ~50-150, D-W: ~0.01-1 mm)
        # We don't know headloss model here, so warn on extremes
        assert not (rough < 0.001 or rough > 500), \
            f"Pipe roughness {rough} outside typical range (0.001-500); verify material/age"


@rule(LINK, code="W_PIPE_VELOCITY_HIGH", attribute="diameter")
@match("Pipe")
def warn_pipe_velocity_high(link) -> None:
    """High velocity pipes may indicate undersizing.

    classification : Engineering
    fix : Consider larger diameter if velocity exceeds 3 m/s at design flow.
    """
    # Static check: very small diameter relative to typical flows
    diam = link.data.get("diameter")
    length = link.data.get("length")
    if (diam is not None and length is not None and
        isinstance(diam, (int, float)) and isinstance(length, (int, float))):
        # Heuristic: diameter < 50mm for long pipes suggests potential high velocity
        assert not (diam < 0.05 and length > 100), \
            f"Small diameter ({diam}m) for long pipe ({length}m) may cause high velocity"


@rule(LINK, code="W_PIPE_VELOCITY_LOW", attribute="diameter")
@match("Pipe")
def warn_pipe_velocity_low(link) -> None:
    """Low velocity pipes may indicate oversizing.

    classification : Engineering
    fix : Consider smaller diameter if velocity is below 0.3 m/s at design flow.
    """
    diam = link.data.get("diameter")
    length = link.data.get("length")
    if (diam is not None and length is not None and
        isinstance(diam, (int, float)) and isinstance(length, (int, float))):
        # Heuristic: very large diameter for short pipes
        assert not (diam > 1.0 and length < 50), \
            f"Large diameter ({diam}m) for short pipe ({length}m) may cause low velocity"
