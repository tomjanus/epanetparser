"""Node components: junctions, reservoirs and tanks.

A node is the point where water is injected, consumed or stored. The three
concrete types differ only in which fields EPANET requires of them, so this
module exposes one class and the concrete type is read from the
``node_type`` field.

Validation rules for nodes live in
:mod:`epanetparser.core_rules.epanet_core.nodes`, not here.
"""
from typing import Any, Dict, KeysView, Optional, Tuple
import copy

from .base import WNTREPANETType


class WNTREPANETNode(WNTREPANETType):
    """A junction, reservoir or tank.

    Attributes
    ----------
    node_types : Tuple[str, ...]
        The concrete node types EPANET defines.
    component_kind : str
        ``"nodes"``.

    Notes
    -----
    A node name that is a non-string scalar is coerced to ``str`` on
    construction, because JSON producers occasionally emit numeric node
    names. A missing or empty name is left alone: reporting it is the job of
    a validation rule, not of parsing.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.node import WNTREPANETNode
    >>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction", "elevation": 10.0})
    >>> node.type
    'Junction'
    >>> node.name
    'J1'
    >>> node.validate().is_valid
    True
    """

    node_types: Tuple[str, ...] = ("Junction", "Reservoir", "Tank")
    component_kind: str = "nodes"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the node's fields, normalising a non-string name.

        Parameters
        ----------
        data : Dict[str, Any]
            Node fields, including ``name`` and ``node_type``.
        """
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
