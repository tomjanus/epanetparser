"""Supporting libraries for the EPANET parser.

Converting between EPANET's native INP format and WNTR's JSON representation is
done by :class:`~epanetparser.core.lib.converter.WNTRINPJSONConverter`, which
delegates to WNTR rather than implementing an INP grammar of its own.

The JSON encoders that used to live here were removed: every component and the
network itself already provide ``as_dict`` and ``as_json``, so a second set of
encoders duplicated them without adding capability. Use
:meth:`epanetparser.core.epanettypes.base.WNTREPANETType.as_json` and
:meth:`epanetparser.core.epanettypes.network.WNTREPANETNetwork.as_json`.
"""
from epanetparser.core.lib.converter import WNTRINPJSONConverter

__all__ = ["WNTRINPJSONConverter"]
