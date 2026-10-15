"""Link components: pipes, pumps and valves.

Each concrete link type is a separate class that inherits from WNTREPANETType.
This allows WNTR element classes (Pipe, Pump, Valve) to inherit from
these classes and gain the validation interface.

Validation rules for links live in
:mod:`epanetparser.core_rules.core_static.epanet_core.links` and, for cross-component
references, in :mod:`epanetparser.core_rules.core_static.epanet_core.network_rules`.
"""
from typing import Any, Dict, Optional, Tuple

from .base import WNTREPANETType


class WNTREPANETLink(WNTREPANETType):
    """Base class for all link types (pipe, pump, valve).

    This class exists for backward compatibility. New code should use
    the concrete subclasses: WNTREPANETPipe, WNTREPANETPump, WNTREPANETValve.

    Attributes
    ----------
    link_types : Tuple[str, ...]
        The concrete link types EPANET defines.
    component_kind : str
        ``"links"``.
    """

    link_types: Tuple[str, ...] = ("Pipe", "Pump", "Valve")
    component_kind: str = "links"

    def __init__(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Store the link's fields.

        Parameters
        ----------
        data : Dict[str, Any], optional
            Link fields, including ``name`` and ``link_type``.
        **kwargs
            Additional fields passed as keyword arguments (for WNTR element compatibility).
        """
        if data is None:
            data = {}
        data.update(kwargs)
        super().__init__(data)

    @property
    def type(self) -> str:
        """Concrete link type, for example ``"Pipe"``."""
        return self.data.get("link_type")

    @property
    def name(self) -> str:
        """Link name."""
        return self.data.get("name")

    @property
    def start_node_name(self) -> Optional[str]:
        return self.data.get("start_node_name")

    @property
    def end_node_name(self) -> Optional[str]:
        return self.data.get("end_node_name")


class WNTREPANETPipe(WNTREPANETLink):
    """A pipe link.

    Pipes convey water between two nodes. They have length, diameter,
    roughness, and optional check valve.
    """

    component_kind: str = "links"

    @property
    def type(self) -> str:
        return "Pipe"

    @property
    def length(self) -> Optional[float]:
        return self.data.get("length")

    @property
    def diameter(self) -> Optional[float]:
        return self.data.get("diameter")

    @property
    def roughness(self) -> Optional[float]:
        return self.data.get("roughness")

    @property
    def minor_loss(self) -> Optional[float]:
        return self.data.get("minor_loss")

    @property
    def initial_status(self) -> Optional[str]:
        return self.data.get("initial_status")

    @property
    def check_valve(self) -> Optional[bool]:
        return self.data.get("check_valve")


class WNTREPANETPump(WNTREPANETLink):
    """A pump link.

    Pumps add energy to the system. They can be power-based or head-based.
    """

    component_kind: str = "links"

    @property
    def type(self) -> str:
        return "Pump"

    @property
    def pump_type(self) -> Optional[str]:
        return self.data.get("pump_type")

    @property
    def power(self) -> Optional[float]:
        return self.data.get("power")

    @property
    def pump_curve_name(self) -> Optional[str]:
        return self.data.get("pump_curve_name")

    @property
    def speed(self) -> Optional[float]:
        return self.data.get("base_speed")

    @property
    def speed_pattern_name(self) -> Optional[str]:
        return self.data.get("speed_pattern_name")

    @property
    def initial_status(self) -> Optional[str]:
        return self.data.get("initial_status")

    @property
    def efficiency_curve_name(self) -> Optional[str]:
        return self.data.get("efficiency_curve_name")


class WNTREPANETValve(WNTREPANETLink):
    """A valve link.

    Valves control flow or pressure. Types include PRV, PSV, PBV, FCV, TCV, GPV.
    """

    component_kind: str = "links"

    @property
    def type(self) -> str:
        return "Valve"

    @property
    def valve_type(self) -> Optional[str]:
        return self.data.get("valve_type")

    @property
    def diameter(self) -> Optional[float]:
        return self.data.get("diameter")

    @property
    def minor_loss(self) -> Optional[float]:
        return self.data.get("minor_loss")

    @property
    def initial_setting(self) -> Optional[float]:
        return self.data.get("initial_setting")

    @property
    def initial_status(self) -> Optional[str]:
        return self.data.get("initial_status")

    @property
    def headloss_curve_name(self) -> Optional[str]:
        return self.data.get("headloss_curve_name")