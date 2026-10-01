"""Parsers for EPANET network models.

:class:`~epanetparser.core.parsers.wntrjsonparser.WNTRJSONParser` reads a WNTR
JSON document and builds a model. It performs no validation: a model that EPANET
could not simulate still parses successfully here, so that the same document
can be checked against whichever rule sets a caller selects.

``.inp`` files are not parsed directly. WNTR converts them to its own JSON
representation first, which
:meth:`~epanetparser.core.epanettypes.network.WNTREPANETNetwork.from_file` does
when it is given an ``.inp`` path.
"""
from epanetparser.core.parsers.wntrjsonparser import WNTRJSONParser

__all__ = ["WNTRJSONParser"]
