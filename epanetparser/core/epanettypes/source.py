"""Water quality source components.

A source injects a constituent, such as chlorine, into a node. Sources are
uncommon: most models have none.

Validation rules for sources live in
:mod:`epanetparser.core_rules.epanet_core.sources`. The reference a source
makes to its node and to its pattern is resolved by
:mod:`epanetparser.core_rules.epanet_core.network_rules`, because a component
rule cannot see the rest of the model.
"""
from typing import Any, Dict, Optional

from .base import WNTREPANETType


class WNTREPANETSource(WNTREPANETType):
    """A water quality source.

    Attributes
    ----------
    component_kind : str
        ``"sources"``.

    Notes
    -----
    The parser constructs one instance per source dictionary. An earlier
    version read ``data.get("sources", [])`` and therefore discarded the
    source it was given; the field dictionary is now stored intact, which is
    what makes the source rules meaningful. See
    ``docs/TODO_MODEL_LAYER_DUPLICATION.md``.

    Field names follow WNTR's JSON representation: ``node_name``,
    ``source_type``, ``strength`` and ``pattern``.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.source import WNTREPANETSource
    >>> source = WNTREPANETSource(
    ...     {"name": "INP1", "node_name": "J1", "source_type": "Chlorine",
    ...      "strength": 0.001, "pattern": "1"}
    ... )
    >>> source.node_name
    'J1'
    >>> source.source_type
    'Chlorine'
    >>> source.type
    'source'
    """

    component_kind: str = "sources"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the source's fields.

        Parameters
        ----------
        data : Dict[str, Any]
            Source fields. WNTR names them ``node_name``, ``source_type``,
            ``strength`` and ``pattern``.
        """
        super().__init__(data)

    @property
    def type(self) -> str:
        """Component type identifier, always ``"source"``."""
        return "source"

    @property
    def node_name(self) -> str:
        """Name of the node the constituent is injected into."""
        return self.data.get("node_name")

    @property
    def source_type(self) -> str:
        """Name of the injected constituent, for example ``"Chlorine"``."""
        return self.data.get("source_type")

    @property
    def strength(self) -> Optional[float]:
        """Concentration injected at the node."""
        return self.data.get("strength")

    @property
    def pattern(self) -> str:
        """Name of the pattern modulating the source strength, if any."""
        return self.data.get("pattern")
