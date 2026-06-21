""" """
from .base import WNTREPANETType

class WNTREPANETControl(WNTREPANETType):
    """ """
    def __init__(self, data) -> None:
        self.data = data

    @property
    def type(self) -> str:
        return self.data.get("type")

    