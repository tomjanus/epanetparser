"""Network metadata component.

The network information component carries the descriptive fields WNTR records
alongside a model: its name, comment, version and references. It is not an
EPANET section; it is metadata about the file, and EPANET itself neither
requires nor reads it.

Validation rules for network metadata live in
:mod:`epanetparser.core_rules.epanet_core.network_info`.
"""
from typing import Any, Dict, List

from .base import WNTREPANETType

#: Metadata fields retained by this component, in reporting order.
NETWORK_INFO_KEYS = ("name", "comment", "version", "references")


class WNTREPANETNetworkInfo(WNTREPANETType):
    """Descriptive metadata about an EPANET model.

    Attributes
    ----------
    component_kind : str
        ``"network_info"``.

    Notes
    -----
    Only the fields in :data:`NETWORK_INFO_KEYS` are retained; anything else in
    the source document is dropped, so the component does not accumulate
    arbitrary keys from a particular producer.

    Examples
    --------
    >>> from epanetparser.core.epanettypes.network_info import WNTREPANETNetworkInfo
    >>> info = WNTREPANETNetworkInfo({"name": "Net1", "version": "wntr-1.4.0", "extra": 1})
    >>> info.name
    'Net1'
    >>> sorted(info.data)
    ['name', 'version']
    """

    component_kind: str = "network_info"

    def __init__(self, data: Dict[str, Any]) -> None:
        """Store the recognised metadata fields.

        Parameters
        ----------
        data : Dict[str, Any]
            Source metadata. Unrecognised keys are discarded.
        """
        super().__init__(
            {key: data[key] for key in NETWORK_INFO_KEYS if key in data}
        )

    @property
    def name(self) -> str:
        """Name of the model, or an empty string if absent."""
        return self.data.get("name", "")

    @property
    def comment(self) -> str:
        """Comment describing the model, or an empty string if absent."""
        return self.data.get("comment", "")

    @property
    def version(self) -> str:
        """Version of the tool that wrote the model, or an empty string."""
        return self.data.get("version", "")

    @property
    def references(self) -> List[Any]:
        """References recorded with the model, or an empty list."""
        return self.data.get("references", [])

    @property
    def type(self) -> str:
        """Component type identifier, always ``"network_info"``."""
        return "network_info"
