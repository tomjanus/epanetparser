"""Pattern components: time-varying multipliers.

A pattern is a named, periodic list of multipliers. EPANET has no fixed
pattern length: the number of multipliers follows from the simulation
duration and the pattern timestep. Constraints on pattern length therefore
belong to a custom ruleset that knows the application's scheduling
assumptions, not to the core ruleset.

Validation rules for patterns live in
:mod:`epanetparser.core_rules.epanet_core.patterns`.
"""
from typing import Any, Dict, List

from .base import WNTREPANETType


class WNTREPANETPattern(WNTREPANETType):
    """A named time pattern.

    Attributes
    ----------
    component_kind : str
        ``"patterns"``.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.pattern import WNTREPANETPattern
    >>> pattern = WNTREPANETPattern({"name": "1", "multipliers": [1.0, 1.2, 0.8]})
    >>> pattern.name
    '1'
    >>> len(pattern.multipliers)
    3
    """

    component_kind: str = "patterns"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the pattern's fields, normalising a non-string name.

        Parameters
        ----------
        data : Dict[str, Any]
            Pattern fields, including ``name`` and ``multipliers``.
        """
        name = data.get("name")
        if name is not None and not isinstance(name, str):
            data["name"] = str(name)
        super().__init__(data)

    @property
    def name(self) -> str:
        """Pattern name."""
        return self.data.get("name")

    @property
    def multipliers(self) -> List[Any]:
        """Pattern multipliers, or an empty list if unset."""
        multipliers = self.data.get("multipliers")
        if multipliers is None:
            return []
        return list(multipliers)

    @property
    def type(self) -> str:
        """Component type identifier, always ``"pattern"``."""
        return "pattern"
