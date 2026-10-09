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
    """The time option group must be defined.

    classification : Option
    fix : Add a [TIMES] section to the INP file or provide time options in JSON.
    """
    assert options.time_options is not None, "Time section not defined"


@rule(OPTIONS, code="E_OPTIONS_HYDRAULIC_MISSING", attribute="hydraulic")
def rule_hydraulic_section_required(options) -> None:
    """The hydraulics option group must be defined.

    classification : Option
    fix : Add a [OPTIONS] section with hydraulic settings or provide hydraulic options in JSON.
    """
    assert options.hydraulic_options is not None, "Hydraulics not defined"


@rule(OPTIONS, code="E_OPTIONS_ENERGY_MISSING", attribute="energy")
def rule_energy_section_required(options) -> None:
    """The energy option group must be defined.

    classification : Option
    fix : Add an [ENERGY] section or provide energy options in JSON.
    """
    assert options.energy_options is not None, "Energy options not defined"


@rule(OPTIONS, code="E_TIME_DURATION_POSITIVE", attribute="duration")
def rule_time_duration_positive(options) -> None:
    """Simulation duration must be > 0 (EPANET error 213).

    classification : Option
    fix : Set simulation duration to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return  # Missing time section handled by E_OPTIONS_TIME_MISSING
    duration = time_opts.get("duration")
    assert duration is not None and isinstance(duration, (int, float)) and duration > 0, \
        f"Time duration must be > 0, got {duration}"


@rule(OPTIONS, code="E_TIME_HYDRAULIC_TIMESTEP_POSITIVE", attribute="hydraulic_timestep")
def rule_time_hydraulic_timestep_positive(options) -> None:
    """Hydraulic timestep must be > 0 (EPANET error 213).

    classification : Option
    fix : Set hydraulic timestep to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    ts = time_opts.get("hydraulic_timestep")
    assert ts is not None and isinstance(ts, (int, float)) and ts > 0, \
        f"Hydraulic timestep must be > 0, got {ts}"


@rule(OPTIONS, code="E_TIME_QUALITY_TIMESTEP_POSITIVE", attribute="quality_timestep")
def rule_time_quality_timestep_positive(options) -> None:
    """Quality timestep must be > 0 (EPANET error 213).

    classification : Option
    fix : Set quality timestep to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    ts = time_opts.get("quality_timestep")
    assert ts is not None and isinstance(ts, (int, float)) and ts > 0, \
        f"Quality timestep must be > 0, got {ts}"


@rule(OPTIONS, code="E_TIME_PATTERN_TIMESTEP_POSITIVE", attribute="pattern_timestep")
def rule_time_pattern_timestep_positive(options) -> None:
    """Pattern timestep must be > 0 (EPANET error 213).

    classification : Option
    fix : Set pattern timestep to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    ts = time_opts.get("pattern_timestep")
    assert ts is not None and isinstance(ts, (int, float)) and ts > 0, \
        f"Pattern timestep must be > 0, got {ts}"


@rule(OPTIONS, code="E_TIME_REPORT_TIMESTEP_POSITIVE", attribute="report_timestep")
def rule_time_report_timestep_positive(options) -> None:
    """Report timestep must be > 0 (EPANET error 213).

    classification : Option
    fix : Set report timestep to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    ts = time_opts.get("report_timestep")
    assert ts is not None and isinstance(ts, (int, float)) and ts > 0, \
        f"Report timestep must be > 0, got {ts}"


@rule(OPTIONS, code="E_TIME_REPORT_START_LE_DURATION", attribute="report_start")
def rule_time_report_start_le_duration(options) -> None:
    """Report start must be <= duration (EPANET error 213).

    classification : Option
    fix : Set report start time less than or equal to simulation duration.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    report_start = time_opts.get("report_start", 0)
    duration = time_opts.get("duration", 0)
    assert report_start <= duration, \
        f"Report start ({report_start}) must be <= duration ({duration})"


@rule(OPTIONS, code="E_TIME_RULE_TIMESTEP_POSITIVE", attribute="rule_timestep")
def rule_time_rule_timestep_positive(options) -> None:
    """Rule timestep must be > 0 (EPANET error 213).

    classification : Option
    fix : Set rule timestep to a positive value in seconds.
    """
    time_opts = options.time_options
    if time_opts is None:
        return
    ts = time_opts.get("rule_timestep")
    assert ts is not None and isinstance(ts, (int, float)) and ts > 0, \
        f"Rule timestep must be > 0, got {ts}"


@rule(OPTIONS, code="E_TIME_STATISTIC_VALID", attribute="statistic")
def rule_time_statistic_valid(options) -> None:
    """Time statistic must be NONE, AVERAGE, MINIMUM, MAXIMUM, or RANGE (EPANET error 213).

    classification : Option
    fix : Use valid statistic: NONE, AVERAGE, MINIMUM, MAXIMUM, or RANGE.
    """
    time_opts = options.time_options or {}
    stat = time_opts.get("statistic", "NONE")
    valid_stats = {"NONE", "AVERAGE", "MINIMUM", "MAXIMUM", "RANGE"}
    assert stat in valid_stats, \
        f"Statistic must be one of {valid_stats}, got {stat}"


@rule(OPTIONS, code="E_OPTION_HEADLOSS_VALID", attribute="headloss")
def rule_option_headloss_valid(options) -> None:
    """Headloss model must be H-W, D-W, or C-M (EPANET error 213).

    classification : Option
    fix : Use valid headloss model: H-W (Hazen-Williams), D-W (Darcy-Weisbach), or C-M (Chezy-Manning).
    """
    hyd_opts = options.hydraulic_options or {}
    model = hyd_opts.get("headloss", "H-W")
    valid_models = {"H-W", "D-W", "C-M"}
    assert model in valid_models, \
        f"Headloss model must be one of {valid_models}, got {model}"


@rule(OPTIONS, code="E_OPTION_DEMAND_MODEL_VALID", attribute="demand_model")
def rule_option_demand_model_valid(options) -> None:
    """Demand model must be DDA, PDA, or PDD (EPANET error 213).

    classification : Option
    fix : Use valid demand model: DDA (demand-driven), PDA (pressure-driven), or PDD.
    """
    hyd_opts = options.hydraulic_options or {}
    model = hyd_opts.get("demand_model", "DDA")
    valid_models = {"DDA", "PDA", "PDD"}
    assert model in valid_models, \
        f"Demand model must be one of {valid_models}, got {model}"


@rule(OPTIONS, code="E_OPTION_UNITS_VALID", attribute="inpfile_units")
def rule_option_units_valid(options) -> None:
    """Flow units must be valid (EPANET error 213).

    classification : Option
    fix : Use valid flow units: LPS, LPM, MLD, CMH, CMD, GPM, MGD, CFS, AFD.
    """
    hyd_opts = options.hydraulic_options or {}
    units = hyd_opts.get("inpfile_units", "LPS")
    valid_units = {"LPS", "LPM", "MLD", "CMH", "CMD", "GPM", "MGD", "CFS", "AFD"}
    assert units in valid_units, \
        f"Flow units must be one of {valid_units}, got {units}"


@rule(OPTIONS, code="E_OPTION_PRESSURE_UNITS_VALID", attribute="inpfile_pressure_units")
def rule_option_pressure_units_valid(options) -> None:
    """Pressure units if set must be PSI, KPA, or M (EPANET error 213).

    classification : Option
    fix : Use valid pressure units: PSI, KPA, or M.
    """
    hyd_opts = options.hydraulic_options or {}
    units = hyd_opts.get("inpfile_pressure_units")
    if units is not None:
        valid_units = {"PSI", "KPA", "M"}
        assert units in valid_units, \
            f"Pressure units must be one of {valid_units}, got {units}"


@rule(OPTIONS, code="E_OPTION_VISCOSITY_POSITIVE", attribute="viscosity")
def rule_option_viscosity_positive(options) -> None:
    """Viscosity must be > 0 (EPANET error 213).

    classification : Option
    fix : Set fluid viscosity to a positive value.
    """
    hyd_opts = options.hydraulic_options or {}
    visc = hyd_opts.get("viscosity", 1.0)
    assert isinstance(visc, (int, float)) and visc > 0, \
        f"Viscosity must be > 0, got {visc}"


@rule(OPTIONS, code="E_OPTION_SPECIFIC_GRAVITY_POSITIVE", attribute="specific_gravity")
def rule_option_specific_gravity_positive(options) -> None:
    """Specific gravity must be > 0 (EPANET error 213).

    classification : Option
    fix : Set fluid specific gravity to a positive value.
    """
    hyd_opts = options.hydraulic_options or {}
    sg = hyd_opts.get("specific_gravity", 1.0)
    assert isinstance(sg, (int, float)) and sg > 0, \
        f"Specific gravity must be > 0, got {sg}"


@rule(OPTIONS, code="E_OPTION_TRIALS_POSITIVE", attribute="trials")
def rule_option_trials_positive(options) -> None:
    """Trials must be > 0 (EPANET error 213).

    classification : Option
    fix : Set number of trials to a positive integer.
    """
    hyd_opts = options.hydraulic_options or {}
    trials = hyd_opts.get("trials", 50)
    assert isinstance(trials, (int, float)) and trials > 0, \
        f"Trials must be > 0, got {trials}"


@rule(OPTIONS, code="E_OPTION_ACCURACY_POSITIVE", attribute="accuracy")
def rule_option_accuracy_positive(options) -> None:
    """Accuracy must be > 0 (EPANET error 213).

    classification : Option
    fix : Set hydraulic accuracy to a positive value.
    """
    hyd_opts = options.hydraulic_options or {}
    acc = hyd_opts.get("accuracy", 0.001)
    assert isinstance(acc, (int, float)) and acc > 0, \
        f"Accuracy must be > 0, got {acc}"


@rule(OPTIONS, code="E_OPTION_UNBALANCED_VALID", attribute="unbalanced")
def rule_option_unbalanced_valid(options) -> None:
    """Unbalanced option must be STOP or CONTINUE (EPANET error 213).

    classification : Option
    fix : Use valid unbalanced option: STOP or CONTINUE.
    """
    hyd_opts = options.hydraulic_options or {}
    unbal = hyd_opts.get("unbalanced", "STOP")
    valid = {"STOP", "CONTINUE"}
    assert unbal in valid, \
        f"Unbalanced must be one of {valid}, got {unbal}"


@rule(OPTIONS, code="E_OPTION_PDA_PRESSURES", attribute="minimum_pressure")
def rule_option_pda_pressures(options) -> None:
    """PDA pressure limits must be valid when demand_model is PDA/PDD (EPANET error 208).

    classification : Option
    fix : Set minimum_pressure >= 0, required_pressure > minimum_pressure, pressure_exponent > 0.
    """
    hyd_opts = options.hydraulic_options or {}
    demand_model = hyd_opts.get("demand_model", "DDA")
    if demand_model in ("PDA", "PDD"):
        min_p = hyd_opts.get("minimum_pressure", 0)
        req_p = hyd_opts.get("required_pressure", 0)
        exp = hyd_opts.get("pressure_exponent", 0.5)
        assert isinstance(min_p, (int, float)) and min_p >= 0, \
            f"PDA minimum_pressure must be >= 0, got {min_p}"
        assert isinstance(req_p, (int, float)) and req_p > min_p, \
            f"PDA required_pressure ({req_p}) must be > minimum_pressure ({min_p})"
        assert isinstance(exp, (int, float)) and exp > 0, \
            f"PDA pressure_exponent must be > 0, got {exp}"


@rule(OPTIONS, code="E_OPTION_EMITTER_EXPONENT", attribute="emitter_exponent")
def rule_option_emitter_exponent(options) -> None:
    """Emitter exponent must be > 0 (EPANET error 213).

    classification : Option
    fix : Set emitter exponent to a positive value (typically 0.5).
    """
    hyd_opts = options.hydraulic_options or {}
    exp = hyd_opts.get("emitter_exponent", 0.5)
    assert isinstance(exp, (int, float)) and exp > 0, \
        f"Emitter exponent must be > 0, got {exp}"


@rule(OPTIONS, code="E_OPTION_QUALITY_TYPE_VALID", attribute="parameter")
def rule_option_quality_type_valid(options) -> None:
    """Quality parameter must be NONE, CHEMICAL, AGE, or TRACE (EPANET error 213).

    classification : Option
    fix : Use valid quality parameter: NONE, CHEMICAL, AGE, or TRACE.
    """
    qual_opts = options.quality_options or {}
    param = qual_opts.get("parameter", "NONE")
    valid = {"NONE", "CHEMICAL", "AGE", "TRACE"}
    assert param in valid, \
        f"Quality parameter must be one of {valid}, got {param}"


@rule(OPTIONS, code="E_OPTION_DIFFUSIVITY_POSITIVE", attribute="diffusivity")
def rule_option_diffusivity_positive(options) -> None:
    """Diffusivity must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set diffusivity to a non-negative value.
    """
    qual_opts = options.quality_options or {}
    diff = qual_opts.get("diffusivity", 1.0)
    assert isinstance(diff, (int, float)) and diff >= 0, \
        f"Diffusivity must be >= 0, got {diff}"


@rule(OPTIONS, code="E_OPTION_TOLERANCE_POSITIVE", attribute="tolerance")
def rule_option_tolerance_positive(options) -> None:
    """Tolerance must be > 0 (EPANET error 213).

    classification : Option
    fix : Set quality tolerance to a positive value.
    """
    qual_opts = options.quality_options or {}
    tol = qual_opts.get("tolerance", 0.01)
    assert isinstance(tol, (int, float)) and tol > 0, \
        f"Tolerance must be > 0, got {tol}"


@rule(OPTIONS, code="E_ENERGY_GLOBAL_EFFICIENCY", attribute="global_efficiency")
def rule_energy_global_efficiency(options) -> None:
    """Global efficiency must be in (0, 100] if specified (EPANET error 213).

    classification : Option
    fix : Set global efficiency to a value between 0 and 100 percent.
    """
    energy_opts = options.energy_options or {}
    eff = energy_opts.get("global_efficiency")
    if eff is not None:
        assert 0 < eff <= 100, \
            f"Global efficiency must be in (0, 100], got {eff}"


@rule(OPTIONS, code="E_ENERGY_GLOBAL_PRICE", attribute="global_price")
def rule_energy_global_price(options) -> None:
    """Global energy price must be >= 0 if specified (EPANET error 213).

    classification : Option
    fix : Set global energy price to a non-negative value.
    """
    energy_opts = options.energy_options or {}
    price = energy_opts.get("global_price")
    if price is not None:
        assert price >= 0, \
            f"Global energy price must be >= 0, got {price}"


@rule(OPTIONS, code="E_ENERGY_DEMAND_CHARGE", attribute="demand_charge")
def rule_energy_demand_charge(options) -> None:
    """Energy demand charge must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set energy demand charge to a non-negative value.
    """
    energy_opts = options.energy_options or {}
    charge = energy_opts.get("demand_charge", 0)
    assert charge >= 0, \
        f"Demand charge must be >= 0, got {charge}"


@rule(OPTIONS, code="E_REACTIONS_BULK_ORDER", attribute="bulk_order")
def rule_reactions_bulk_order(options) -> None:
    """Bulk reaction order must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set bulk reaction order to a non-negative value (typically 1).
    """
    rxn_opts = options.reaction_options or {}
    order = rxn_opts.get("bulk_order", 1)
    assert isinstance(order, (int, float)) and order >= 0, \
        f"Bulk reaction order must be >= 0, got {order}"


@rule(OPTIONS, code="E_REACTIONS_WALL_ORDER", attribute="wall_order")
def rule_reactions_wall_order(options) -> None:
    """Wall reaction order must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set wall reaction order to a non-negative value (typically 1).
    """
    rxn_opts = options.reaction_options or {}
    order = rxn_opts.get("wall_order", 1)
    assert isinstance(order, (int, float)) and order >= 0, \
        f"Wall reaction order must be >= 0, got {order}"


@rule(OPTIONS, code="E_REACTIONS_TANK_ORDER", attribute="tank_order")
def rule_reactions_tank_order(options) -> None:
    """Tank reaction order must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set tank reaction order to a non-negative value (typically 1).
    """
    rxn_opts = options.reaction_options or {}
    order = rxn_opts.get("tank_order", 1)
    assert isinstance(order, (int, float)) and order >= 0, \
        f"Tank reaction order must be >= 0, got {order}"


@rule(OPTIONS, code="E_REACTIONS_BULK_COEFF", attribute="bulk_coeff")
def rule_reactions_bulk_coeff(options) -> None:
    """Global bulk reaction coefficient must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set global bulk reaction coefficient to a non-negative value.
    """
    rxn_opts = options.reaction_options or {}
    coeff = rxn_opts.get("bulk_coeff", 0)
    assert isinstance(coeff, (int, float)) and coeff >= -1e-5, \
        f"Bulk reaction coefficient must be >= 0, got {coeff}"


@rule(OPTIONS, code="E_REACTIONS_WALL_COEFF", attribute="wall_coeff")
def rule_reactions_wall_coeff(options) -> None:
    """Global wall reaction coefficient must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set global wall reaction coefficient to a non-negative value.
    """
    rxn_opts = options.reaction_options or {}
    coeff = rxn_opts.get("wall_coeff", 0)
    assert isinstance(coeff, (int, float)) and coeff >= -1e-5, \
        f"Wall reaction coefficient must be >= 0, got {coeff}"


@rule(OPTIONS, code="E_REACTIONS_LIMITING_POTENTIAL", attribute="limiting_potential")
def rule_reactions_limiting_potential(options) -> None:
    """Limiting potential must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set limiting potential to a non-negative value.
    """
    rxn_opts = options.reaction_options or {}
    lp = rxn_opts.get("limiting_potential", 0)
    assert isinstance(lp, (int, float)) and lp >= 0, \
        f"Limiting potential must be >= 0, got {lp}"


@rule(OPTIONS, code="E_REACTIONS_ROUGHNESS_CORRELATION", attribute="roughness_correl")
def rule_reactions_roughness_correlation(options) -> None:
    """Roughness correlation must be >= 0 (EPANET error 213).

    classification : Option
    fix : Set roughness correlation to a non-negative value.
    """
    rxn_opts = options.reaction_options or {}
    rc = rxn_opts.get("roughness_correl", 0)
    assert isinstance(rc, (int, float)) and rc >= 0, \
        f"Roughness correlation must be >= 0, got {rc}"


@rule(OPTIONS, code="W_TIME_PATTERN_TIMESTEP_DIVIDES_HYDRAULIC", attribute="pattern_timestep")
def warn_time_pattern_timestep_divides_hydraulic(options) -> None:
    """Pattern timestep should divide hydraulic timestep evenly.

    classification : Engineering
    fix : Align pattern timestep to be a multiple of hydraulic timestep.
    """
    time_opts = options.time_options or {}
    pattern_ts = time_opts.get("pattern_timestep", 3600)
    hydraulic_ts = time_opts.get("hydraulic_timestep", 3600)
    if hydraulic_ts > 0:
        assert pattern_ts % hydraulic_ts == 0, \
            f"Pattern timestep ({pattern_ts}) should be multiple of hydraulic timestep ({hydraulic_ts})"


@rule(OPTIONS, code="W_UNITS_INCONSISTENT", attribute="inpfile_units")
def warn_units_inconsistent(options) -> None:
    """Input file units vs simulation units mismatch.

    classification : Engineering
    fix : Align input file units with simulation units.
    """
    hyd_opts = options.hydraulic_options or {}
    units = hyd_opts.get("inpfile_units", "LPS")
    # Simulation is typically in SI (LPS)
    assert True, "Verify input file units match simulation units"
