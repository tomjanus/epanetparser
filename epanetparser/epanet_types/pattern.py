""" """
from .base import WNTREPANETType

MULTIPLIER_LENGTH = 12 # Derive from options
# duration / pattern_timestep

# TODO: Allow validator to have access to all data not just the section
#       such that we can use other section data for validation

class WNTREPANETPattern(WNTREPANETType):
    """ """
    def __init__(self, data) -> None:
        name = data.get("name")
        if not isinstance(name, str):
            if not name:
                # Unnamed pattern - will fail validation
                pass
            else:
                # Other non-str name, cast to str
                data["name"] = str(name)
        self.data = data

    @property
    def name(self) -> str:
        return self.data.get("name")
    
    @property
    def type(self) -> str:
        return "pattern"
    
    """ Validation rules """
    def rule_pattern_has_name(self) -> None:
        assert self.name is not None, "Missing pattern name"

    def rule_pattern_length(self) -> None:
        assert len(self.data.get("multipliers")) == MULTIPLIER_LENGTH