""" """
from typing import Tuple
from .base import WNTREPANETType

class WNTREPANETLink(WNTREPANETType):
    """ """
    link_types: Tuple[str, ...] = ("Pipe", "Pump", "Valve")

    def __init__(self, data) -> None:
        self.data = data

    @property
    def type(self) -> str:
        return self.data.get("link_type")

    @property
    def name(self) -> str:
        return self.data.get("name")
    
    def rule_link_has_valid_type(self) -> None:
        """Verify that the link type is one of the supported types."""
        assert self.type in self.link_types, \
            f"Unsupported link type {self.type}"