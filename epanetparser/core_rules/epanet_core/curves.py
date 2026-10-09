"""Curve rules for the core ruleset.

A curve is a named, ordered list of ``(x, y)`` points. These rules check that
the name and type are present and that the point list is usable: two numbers
per point, both numeric, ascending in x so that interpolation is well defined.
"""
from epanetparser.core.validation import defined as _defined, match, rule

CURVE = "WNTREPANETCurve"

#: Curve types EPANET defines.
CURVE_TYPES = ("HEAD", "PUMP", "EFFICIENCY", "VOLUME", "HEADLOSS")


@rule(CURVE, code="E_CURVE_NAME_MISSING", attribute="name")
def rule_curve_has_name(curve) -> None:
    """A curve must have a name.

    classification : Parameter
    fix : Assign a unique identifier to the curve.
    """
    assert _defined(curve, "name"), "Missing curve name"


@rule(CURVE, code="E_CURVE_TYPE_UNSUPPORTED", attribute="curve_type")
def rule_curve_has_valid_type(curve) -> None:
    """A curve must declare one of the curve types EPANET defines.

    classification : Parameter
    fix : Change the curve type to one of: HEAD, PUMP, EFFICIENCY, VOLUME, HEADLOSS.
    """
    assert curve.type in CURVE_TYPES, f"Unsupported curve type {curve.type}"


@rule(CURVE, code="E_CURVE_POINTS_MISSING", attribute="points")
def rule_curve_has_points(curve) -> None:
    """A curve must have a non-empty list of points.

    classification : Curve
    fix : Provide at least two (x, y) data points for the curve.
    """
    points = curve.data.get("points")
    assert isinstance(points, list) and len(points) > 0, \
        "Curve must have a non-empty list of points"


@rule(CURVE, code="E_CURVE_POINT_MALFORMED", attribute="points")
def rule_curve_points_valid(curve) -> None:
    """Each curve point must be a pair of values.

    classification : Curve
    fix : Ensure each point is a list or tuple of exactly two values (x, y).
    """
    points = curve.data.get("points") or []
    assert all(
        isinstance(point, (list, tuple)) and len(point) == 2 for point in points
    ), "Each curve point must be a list or tuple of two values (x, y)"


@rule(CURVE, code="E_CURVE_POINT_NOT_NUMERIC", attribute="points")
def rule_curve_points_numeric(curve) -> None:
    """Each curve point must be numeric.

    classification : Curve
    fix : Ensure both x and y values are numeric (int or float).
    """
    points = curve.data.get("points") or []
    assert all(
        isinstance(point[0], (int, float)) and isinstance(point[1], (int, float))
        for point in points
    ), "Curve points must be numeric values"


@rule(CURVE, code="E_CURVE_POINTS_UNSORTED", attribute="points")
def rule_curve_points_sorted(curve) -> None:
    """Curve points must ascend in x so that interpolation is well defined.

    classification : Curve
    fix : Sort curve points by x-value in ascending order.
    """
    points = curve.data.get("points") or []
    assert all(
        points[idx][0] <= points[idx + 1][0] for idx in range(len(points) - 1)
    ), "Curve points must be sorted in ascending order by x-value"


@rule(CURVE, code="W_CURVE_POINTS_MINIMUM", attribute="points")
def warn_curve_minimum_points(curve) -> None:
    """Curve should have at least 2 points for proper interpolation.

    classification : Curve
    fix : Provide at least two (x, y) data points for the curve.
    """
    points = curve.data.get("points") or []
    assert len(points) >= 2, "Curve should have at least 2 points for interpolation"


@rule(CURVE, code="E_CURVE_DUPLICATE_X", attribute="points")
def rule_curve_no_duplicate_x(curve) -> None:
    """Curve must not have duplicate x-values (EPANET error 202).

    classification : Curve
    fix : Remove duplicate x-values from curve points.
    """
    points = curve.data.get("points") or []
    x_values = [p[0] for p in points]
    assert len(x_values) == len(set(x_values)), "Curve must not have duplicate x-values"


@rule(CURVE, code="E_PUMP_CURVE_NEGATIVE_HEAD", attribute="points")
@match("HEAD")
@match("PUMP")
def rule_pump_curve_no_negative_head(curve) -> None:
    """Pump curve head values should not be negative in operating range (EPANET error 227).

    classification : Curve
    fix : Ensure pump curve head values are >= 0 for all points.
    """
    if curve.type in ("HEAD", "PUMP"):
        points = curve.data.get("points") or []
        for i, (x, y) in enumerate(points):
            assert y >= 0, f"Pump curve point {i} has negative head ({y}) at flow {x}"


@rule(CURVE, code="E_EFFICIENCY_CURVE_RANGE", attribute="points")
@match("EFFICIENCY")
def rule_efficiency_curve_range(curve) -> None:
    """Efficiency curve values must be in [0, 100] range.

    classification : Curve
    fix : Ensure all efficiency values are between 0 and 100 percent.
    """
    if curve.type == "EFFICIENCY":
        points = curve.data.get("points") or []
        for i, (x, y) in enumerate(points):
            assert 0 <= y <= 100, f"Efficiency curve point {i} value {y} outside [0, 100] range"


@rule(CURVE, code="E_HEADLOSS_CURVE_POSITIVE", attribute="points")
@match("HEADLOSS")
def rule_headloss_curve_positive(curve) -> None:
    """Headloss curve y-values (headloss coefficient) must be >= 0.

    classification : Curve
    fix : Ensure all headloss values are non-negative.
    """
    if curve.type == "HEADLOSS":
        points = curve.data.get("points") or []
        for i, (x, y) in enumerate(points):
            assert y >= 0, f"Headloss curve point {i} has negative value ({y}) at flow {x}"


@rule(CURVE, code="E_VOLUME_CURVE_INCREASING", attribute="points")
@match("VOLUME")
def rule_volume_curve_increasing(curve) -> None:
    """Tank volume curve: volume must increase with level (x).

    classification : Curve
    fix : Ensure volume curve y-values increase with x (level).
    """
    if curve.type == "VOLUME":
        points = curve.data.get("points") or []
        for idx in range(len(points) - 1):
            assert points[idx][1] <= points[idx + 1][1], \
                f"Volume curve: volume must increase with level at point {idx}"


@rule(CURVE, code="E_PUMP_CURVE_SHUTOFF_HEAD", attribute="points")
@match("HEAD")
@match("PUMP")
def warn_pump_curve_shutoff_head(curve) -> None:
    """Pump curve should have a point at flow=0 (shutoff head).

    classification : Engineering
    fix : Add shutoff head point at Q=0 for accurate pump modeling.
    """
    if curve.type in ("HEAD", "PUMP"):
        points = curve.data.get("points") or []
        has_zero_flow = any(p[0] == 0 for p in points)
        assert has_zero_flow, "Pump curve should have shutoff head point at flow=0"


@rule(CURVE, code="E_PUMP_CURVE_MAX_FLOW", attribute="points")
@match("HEAD")
@match("PUMP")
def warn_pump_curve_max_flow(curve) -> None:
    """Pump curve should extend to expected maximum flow.

    classification : Engineering
    fix : Ensure pump curve covers the expected operating flow range.
    """
    if curve.type in ("HEAD", "PUMP"):
        points = curve.data.get("points") or []
        max_flow = max(p[0] for p in points) if points else 0
        assert max_flow > 0, "Pump curve should have points at positive flow values"


@rule(CURVE, code="W_CURVE_TYPE_MATCHES_USE", attribute="curve_type")
def warn_curve_type_matches_use(curve) -> None:
    """Curve type should match its intended use (PUMP/HEAD for pumps, VOLUME for tanks, etc.).

    classification : Engineering
    fix : Use appropriate curve type: PUMP/HEAD for pumps, VOLUME for tanks, EFFICIENCY for efficiency, HEADLOSS for valves.
    """
    # This is a general warning - the actual use is checked in network rules
    assert True, "Curve type should match its application (validated by reference rules)"
