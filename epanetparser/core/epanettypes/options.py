"""Network options component.

The options component wraps the ``[OPTIONS]``, ``[TIMES]``, ``[REPORT]``,
``[QUALITY]``, ``[REACTIONS]``, ``[ENERGY]`` and ``[GRAPHICS]`` blocks of an
EPANET model, which WNTR's JSON representation groups under the ``options``
key.

The accessors below return whole sub-blocks, not individual settings. Rules
read the settings they care about from those blocks, which keeps the class
independent of any particular EPANET version's option set.

Validation rules for options live in
:mod:`epanetparser.core_rules.epanet_core.options`; constraints imposed by a
particular solver, such as a fixed simulation horizon, belong in a custom
ruleset.
"""
from typing import Any, Dict, KeysView, Optional

from .base import WNTREPANETType


class WNTREPANETOptions(WNTREPANETType):
    """The simulation options of an EPANET model.

    Attributes
    ----------
    component_kind : str
        ``"options"``.

    Notes
    -----
    This component is always present: the parser requires the ``options`` key
    in the source document. A missing sub-block is reported by a validation
    rule rather than raising here, so a partially specified model can still be
    parsed and reported on as a whole.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.options import WNTREPANETOptions
    >>> options = WNTREPANETOptions({"time": {"duration": 86400}})
    >>> options.time_options["duration"]
    86400
    >>> options.hydraulic_options is None
    True
    """

    component_kind: str = "options"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the options.

        Parameters
        ----------
        data : Dict[str, Any]
            Mapping of option group name to that group's settings.
        """
        super().__init__(data)

    @property
    def time_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the time group, or None if the group is absent."""
        return self.data.get("time")

    @property
    def hydraulic_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the hydraulics group, or None if the group is absent."""
        return self.data.get("hydraulic")

    @property
    def report_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the report group, or None if the group is absent."""
        return self.data.get("report")

    @property
    def quality_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the quality group, or None if the group is absent."""
        return self.data.get("quality")

    @property
    def reaction_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the reactions group, or None if the group is absent."""
        return self.data.get("reaction")

    @property
    def energy_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the energy group, or None if the group is absent."""
        return self.data.get("energy")

    @property
    def graphics_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the graphics group, or None if the group is absent."""
        return self.data.get("graphics")

    @property
    def user_options(self) -> Optional[Dict[str, Any]]:
        """Settings of the ``[USER]`` group, or None if the group is absent.

        Notes
        -----
        WNTR emits a ``user`` group that ``WNTREPANETOptions`` does not model
        as a first-class concept. It is exposed here for completeness and is
        otherwise unvalidated; see
        ``docs/TODO_MODEL_LAYER_DUPLICATION.md``.
        """
        return self.data.get("user")

    @property
    def attrs(self) -> KeysView:
        """View of the option group names."""
        return self.data.keys()

    @property
    def type(self) -> str:
        """Component type identifier, always ``"WNTR_Network_Options"``."""
        return "WNTR_Network_Options"
