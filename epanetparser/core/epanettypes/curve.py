"""Curve components: pump, head, efficiency and volume curves.

A curve is a named list of ``(x, y)`` points describing the behaviour of a
pump, a head-loss curve or a tank volume relation.

Validation rules for curves live in
:mod:`epanetparser.core_rules.epanet_core.curves`.
"""
from typing import Any, Dict, List, Tuple

from .base import WNTREPANETType


class WNTREPANETCurve(WNTREPANETType):
    """A named curve.

    Attributes
    ----------
    curve_types : Tuple[str, ...]
        Curve types EPANET defines: ``HEAD``, ``PUMP``, ``EFFICIENCY``,
        ``VOLUME`` and ``HEADLOSS``.
    component_kind : str
        ``"curves"``.

    Notes
    -----
    WNTR's JSON representation labels every pump curve ``HEAD`` rather than
    ``PUMP``, so a curve type is a coarse hint, not a guarantee. Reference
    rules therefore check that a referenced curve *exists* rather than that it
    has a particular type; see
    :mod:`epanetparser.core_rules.epanet_core.network_rules`.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.curve import WNTREPANETCurve
    >>> curve = WNTREPANETCurve({"name": "1", "curve_type": "HEAD", "points": [[0.0, 10.0]]})
    >>> curve.type
    'HEAD'
    >>> curve.points
    [[0.0, 10.0]]
    """

    curve_types: Tuple[str, ...] = (
        "HEAD",
        "PUMP",
        "EFFICIENCY",
        "VOLUME",
        "HEADLOSS",
    )
    component_kind: str = "curves"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the curve's fields, normalising a non-string name.

        Parameters
        ----------
        data : Dict[str, Any]
            Curve fields, including ``name`` and ``points``.
        """
        name = data.get("name")
        if name is not None and not isinstance(name, str):
            data["name"] = str(name)
        super().__init__(data)

    @property
    def type(self) -> str:
        """Curve type, for example ``"HEAD"``."""
        return self.data.get("curve_type")

    @property
    def name(self) -> str:
        """Curve name."""
        return self.data.get("name")

    @property
    def points(self) -> List[Any]:
        """Curve points as ``(x, y)`` pairs, or an empty list if unset."""
        points = self.data.get("points")
        if points is None:
            return []
        return [tuple(point) for point in points]
