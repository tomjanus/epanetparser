""" Tests for EPANET parser. """
from epanetparser.core import __version__, _registry
from epanetparser.core.registry import ValidatorRegistry


def test_version() -> None:
    """ Check that the version is correct. """
    assert __version__ == '0.1.0'


def test_global_registry() -> None:
    """ Check that the global registry of rules and warnings is initialized correctly. """
    assert isinstance(_registry, ValidatorRegistry)
