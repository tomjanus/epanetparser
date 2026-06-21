""" """
from .base import WNTREPANETType


class WNTREPANETSource(WNTREPANETType):
    """ Class representing the sources component of an EPANET network. """

    def __init__(self, data) -> None:
        self.data = data.get("sources", [])

    @property
    def type(self) -> str:
        return "sources"