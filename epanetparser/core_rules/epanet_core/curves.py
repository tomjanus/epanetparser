"""Curve rules for the core ruleset.

A curve is a named, ordered list of ``(x, y)`` points. These rules check that
the name and type are present and that the point list is usable: two numbers
per point, both numeric, ascending in x so that interpolation is well defined.
"""
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

CURVE = "WNTREPANETCurve"

#: Curve types EPANET defines.
CURVE_TYPES = ("HEAD", "PUMP", "EFFICIENCY", "VOLUME", "HEADLOSS")


@rule(CURVE, code="E_CURVE_NAME_MISSING", attribute="name")
def rule_curve_has_name(curve) -> None:
    """A curve must have a name."""
    assert _defined(curve, "name"), "Missing curve name"


@rule(CURVE, code="E_CURVE_TYPE_UNSUPPORTED", attribute="curve_type")
def rule_curve_has_valid_type(curve) -> None:
    """A curve must declare one of the curve types EPANET defines."""
    assert curve.type in CURVE_TYPES, f"Unsupported curve type {curve.type}"


@rule(CURVE, code="E_CURVE_POINTS_MISSING", attribute="points")
def rule_curve_has_points(curve) -> None:
    """A curve must have a non-empty list of points."""
    points = curve.data.get("points")
    assert isinstance(points, list) and len(points) > 0, \
        "Curve must have a non-empty list of points"


@rule(CURVE, code="E_CURVE_POINT_MALFORMED", attribute="points")
def rule_curve_points_valid(curve) -> None:
    """Each curve point must be a pair of values."""
    points = curve.data.get("points") or []
    assert all(
        isinstance(point, (list, tuple)) and len(point) == 2 for point in points
    ), "Each curve point must be a list or tuple of two values (x, y)"


@rule(CURVE, code="E_CURVE_POINT_NOT_NUMERIC", attribute="points")
def rule_curve_points_numeric(curve) -> None:
    """Each curve point must be numeric."""
    points = curve.data.get("points") or []
    assert all(
        isinstance(point[0], (int, float)) and isinstance(point[1], (int, float))
        for point in points
    ), "Curve points must be numeric values"


@rule(CURVE, code="E_CURVE_POINTS_UNSORTED", attribute="points")
def rule_curve_points_sorted(curve) -> None:
    """Curve points must ascend in x so that interpolation is well defined."""
    points = curve.data.get("points") or []
    assert all(
        points[idx][0] <= points[idx + 1][0] for idx in range(len(points) - 1)
    ), "Curve points must be sorted in ascending order by x-value"
