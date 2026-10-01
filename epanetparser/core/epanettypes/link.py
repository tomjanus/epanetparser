"""Link components: pipes, pumps and valves.

A link carries water between two nodes. As with nodes, the concrete type is
read from the ``link_type`` field rather than being a separate class.

Validation rules for links live in
:mod:`epanetparser.core_rules.epanet_core.links` and, for cross-component
references, in :mod:`epanetparser.core_rules.epanet_core.network_rules`.
"""
from typing import Any, Dict, Tuple

from .base import WNTREPANETType


class WNTREPANETLink(WNTREPANETType):
    """A pipe, pump or valve.

    Attributes
    ----------
    link_types : Tuple[str, ...]
        The concrete link types EPANET defines.
    component_kind : str
        ``"links"``.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.link import WNTREPANETLink
    >>> link = WNTREPANETLink({"name": "P1", "link_type": "Pipe", "start_node_name": "J1"})
    >>> link.type
    'Pipe'
    >>> link.name
    'P1'
    """

    link_types: Tuple[str, ...] = ("Pipe", "Pump", "Valve")
    component_kind: str = "links"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the link's fields.

        Parameters
        ----------
        data : Dict[str, Any]
            Link fields, including ``name`` and ``link_type``.
        """
        super().__init__(data)

    @property
    def type(self) -> str:
        """Concrete link type, for example ``"Pipe"``."""
        return self.data.get("link_type")

    @property
    def name(self) -> str:
        """Link name."""
        return self.data.get("name")
