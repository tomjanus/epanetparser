"""Control components.

A control changes the state of a link when a condition on the network is met.
WNTR's JSON representation records controls as a ``type`` (``"simple"`` or
``"rule"``) plus the condition and the resulting actions, both kept as text
because the EPANET control language is not a data structure this parser
re-interprets.

Validation rules for controls live in
:mod:`epanetparser.core_rules.epanet_core.controls`.
"""
from typing import Any, Dict, List

from .base import WNTREPANETType


class WNTREPANETControl(WNTREPANETType):
    """A simple or rule-based control.

    Attributes
    ----------
    control_types : Tuple[str, ...]
        Control kinds WNTR distinguishes.
    component_kind : str
        ``"controls"``.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.control import WNTREPANETControl
    >>> control = WNTREPANETControl({"type": "simple", "condition": "TIME > 8"})
    >>> control.type
    'simple'
    """

    control_types = ("simple", "rule")
    component_kind: str = "controls"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the control's fields.

        Parameters
        ----------
        data : Dict[str, Any]
            Control fields, including ``type`` and ``condition``.
        """
        super().__init__(data)

    @property
    def type(self) -> str:
        """Control kind, for example ``"simple"``."""
        return self.data.get("type")

    @property
    def condition(self) -> str:
        """Control condition as written in the model."""
        return self.data.get("condition")

    @property
    def then_actions(self) -> List[Any]:
        """Actions taken when the condition holds, or an empty list."""
        actions = self.data.get("then_actions")
        if actions is None:
            return []
        return list(actions)
