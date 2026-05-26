""" """
from .base import WNTREPANETType


class WNTREPANETSource(WNTREPANETType):
    """ """

    def __init__(self, data) -> None:
        self.data = data

    @property
    def type(self) -> str:
        return "source"