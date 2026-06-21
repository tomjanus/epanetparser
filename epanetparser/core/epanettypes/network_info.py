""" """
from .base import WNTREPANETType

class WNTREPANETNetworkInfo(WNTREPANETType):
    """ Class representing the network information component of an EPANET network. 
    
    NOTE: 
    -----
    The network_info component is not a standard EPANET component but is included in 
    the WNTR JSON format to capture metadata about the network.
    This class provides properties to access common metadata fields such as name, 
    comment, version, and references, and includes validation rules to ensure that 
    required metadata is present.
    """
    def __init__(self, data) -> None:
        _network_info_keys = ["name", "comment", "version", "references"]
        self.data = {k: data[k] for k in _network_info_keys if k in data}

    @property
    def name(self) -> str:
        """ Get the name of the network, if available. """
        return self.data.get("name", "")
    
    @property
    def comment(self) -> str:
        """ Get the comment associated with the network, if available. """
        return self.data.get("comment", "")
    
    @property
    def version(self) -> str:
        """ Get the version of the network, if available. """
        return self.data.get("version", "")
    
    @property
    def references(self) -> list:
        """ Get any references associated with the network, if available. """
        return self.data.get("references", [])
    
    @property
    def type(self) -> str:
        """ Return the component type identifier for this class. """
        return "network_info"

    # Validation rules and warnings for the network_info component

    def rule_network_has_name(self) -> None:
        """ Ensure that the network has a name. """
        assert self.name, "Network missing a name"

    # TODO: This warning does not show up if a rule shows up
    def warn_network_has_version(self) -> None:
        """ Warn if the network is missing a version. """
        assert self.version, "Network missing a version"