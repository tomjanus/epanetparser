"""Advanced mock ruleset with custom type overrides."""

from epanetparser.core.epanettypes.node import WNTREPANETNode
from epanetparser.core.epanettypes.link import WNTREPANETLink
from epanetparser.core.decorators import match, described
__key__ = "advanced"
__ruleset_name__ = "Advanced Test Ruleset"
__version__ = "2.1.0"
__description__ = "An advanced ruleset with custom type definitions"
__required_rules__ = None
__conflicting_rules__ = None


class CustomNode(WNTREPANETNode):
    """Custom node type with additional validation."""
    
    @match("Tank")
    def rule_no_tank_overflow(self) -> None:
        """Validate that tank overflow is not enabled."""
        if "overflow" in self.data:
            assert self.data["overflow"] == False, "Overflows on tanks not supported"

    @described
    def rule_no_emitters(self) -> None:
        """Validate that node does not have active emitters."""
        assert self.emitter_coefficient in (None, 0), "Emitters with nonzero coefficients not supported"


class CustomLink(WNTREPANETLink):
    """Custom link type with additional validation."""
    
    @described
    @match("Valve")
    def rule_no_valves_allowed(self) -> None:
        """Validate that no valve-type links exist in the network."""
        assert False, "Valve links not supported"
