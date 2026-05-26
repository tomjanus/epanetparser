""" """
from .base import WNTREPANETType

class WNTREPANETNetworkInfo(WNTREPANETType):
    """ """
    def __init__(self, data):
        self.data = data

    @property
    def name(self) -> str:
        return self.data.get("name")
    
    @property
    def comment(self) -> str:
        return self.data.get("comment")
    
    @property
    def version(self) -> str:
        return self.data.get("version")
    
    @property
    def type(self) -> str:
        return "network_info"

    def rule_network_has_name(self) -> None:
        assert self.name is not None, "Network missing a name"

    # TODO: This warning does not show up if a rule shows up
    def warn_network_has_version(self) -> None:
        assert self.version is not None, "Network missing a version"