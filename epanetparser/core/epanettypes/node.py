"""Node components: junctions, reservoirs and tanks.

Each concrete node type is a separate class that inherits from WNTREPANETType.
This allows WNTR element classes (Junction, Reservoir, Tank) to inherit from
these classes and gain the validation interface.

Validation rules for nodes live in
:mod:`epanetparser.core_rules.core_static.epanet_core.nodes`, not here.
"""
from typing import Any, Dict, KeysView, Optional, Tuple
import copy

from .base import WNTREPANETType


class WNTREPANETNode(WNTREPANETType):
    """Base class for all node types (junction, reservoir, tank).

    This class exists for backward compatibility. New code should use
    the concrete subclasses: WNTREPANETJunction, WNTREPANETReservoir, WNTREPANETTank.

    Attributes
    ----------
    node_types : Tuple[str, ...]
        The concrete node types EPANET defines.
    component_kind : str
        ``"nodes"``.
    """

    node_types: Tuple[str, ...] = ("Junction", "Reservoir", "Tank")
    component_kind: str = "nodes"

    def __init__(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Store the node's fields, normalising a non-string name.

        Parameters
        ----------
        data : Dict[str, Any], optional
            Node fields, including ``name`` and ``node_type``.
        **kwargs
            Additional fields passed as keyword arguments (for WNTR element compatibility).
        """
        if data is None:
            data = {}
        data.update(kwargs)
        name = data.get("name")
        if name is not None and not isinstance(name, str):
            data["name"] = str(name)
        super().__init__(data)

    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        """Node coordinates as an ``(x, y)`` pair, or None if unset."""
        coordinates = self.data.get("coordinates")
        if coordinates is None:
            return None
        return tuple(coordinates)

    @property
    def type(self) -> str:
        """Concrete node type, for example ``"Junction"``."""
        return self.data.get("node_type")

    @property
    def name(self) -> str:
        """Node name."""
        return self.data.get("name")

    @property
    def emitter_coefficient(self) -> Optional[float]:
        """Emitter coefficient, or None if the node has no emitter."""
        return self.data.get("emitter_coefficient")

    @property
    def attrs(self) -> KeysView:
        """View of the node's field names."""
        return self.data.keys()

    def as_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the node's fields.

        Returns
        -------
        Dict[str, Any]
            Copy of ``data``, with any nested component also converted.

        Notes
        -----
        Nodes are leaves of the model, so the copy only guards against a
        caller mutating nested lists such as ``coordinates``.
        """
        return copy.deepcopy(self.data)


class WNTREPANETJunction(WNTREPANETNode):
    """A junction node.

    Junctions are points where water is consumed or where links connect.
    They require an elevation and optionally have a base demand and emitter.
    """

    component_kind: str = "nodes"

    @property
    def type(self) -> str:
        return "Junction"

    @property
    def elevation(self) -> Optional[float]:
        return self.data.get("elevation")

    @property
    def base_demand(self) -> Optional[float]:
        return self.data.get("base_demand")

    @property
    def demand_pattern_name(self) -> Optional[str]:
        return self.data.get("pattern_name")

    @property
    def demand_category(self) -> Optional[str]:
        return self.data.get("demand_category")


class WNTREPANETReservoir(WNTREPANETNode):
    """A reservoir node.

    Reservoirs are infinite water sources at a fixed hydraulic head.
    They require a base_head and optionally have a head pattern.
    """

    component_kind: str = "nodes"

    @property
    def type(self) -> str:
        return "Reservoir"

    @property
    def elevation(self) -> Optional[float]:
        return self.data.get("elevation")

    @property
    def base_head(self) -> Optional[float]:
        return self.data.get("base_head")

    @property
    def head_pattern_name(self) -> Optional[str]:
        return self.data.get("head_pattern_name")


class WNTREPANETTank(WNTREPANETNode):
    """A tank node.

    Tanks are water storage nodes with variable water level.
    They require elevation, diameter, and level parameters.
    """

    component_kind: str = "nodes"

    @property
    def type(self) -> str:
        return "Tank"

    @property
    def elevation(self) -> Optional[float]:
        return self.data.get("elevation")

    @property
    def diameter(self) -> Optional[float]:
        return self.data.get("diameter")

    @property
    def init_level(self) -> Optional[float]:
        return self.data.get("init_level")

    @property
    def min_level(self) -> Optional[float]:
        return self.data.get("min_level")

    @property
    def max_level(self) -> Optional[float]:
        return self.data.get("max_level")

    @property
    def min_vol(self) -> Optional[float]:
        return self.data.get("min_vol")

    @property
    def vol_curve_name(self) -> Optional[str]:
        return self.data.get("vol_curve_name")

    @property
    def overflow(self) -> Optional[bool]:
        return self.data.get("overflow")