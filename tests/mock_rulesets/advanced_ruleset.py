"""Advanced mock ruleset with custom type overrides."""

from epanetparser.core.epanettypes.node import WNTREPANETNode
from epanetparser.core.epanettypes.link import WNTREPANETLink


__key__ = "advanced"
__ruleset_name__ = "Advanced Test Ruleset"
__version__ = "2.1.0"
__description__ = "An advanced ruleset with custom type definitions"


class CustomNode(WNTREPANETNode):
    """Custom node type with additional validation."""
    pass


class CustomLink(WNTREPANETLink):
    """Custom link type with additional validation."""
    pass
