"""Network metadata rules for the core ruleset.

The metadata component records what WNTR knew about a model when it read it.
A missing name is an error because a report that cannot name its subject is
not usable; a missing version is a warning, because the model may still be
perfectly simulable without it.
"""
from epanetparser.core.validation import rule

NETWORK_INFO = "WNTREPANETNetworkInfo"


@rule(NETWORK_INFO, code="E_NETWORK_NAME_MISSING", attribute="name")
def rule_network_has_name(network_info) -> None:
    """A model must have a name, otherwise it cannot be identified in a report.

    classification : Parameter
    fix : Provide a name for the network model.
    """
    assert network_info.name, "Network missing a name"


@rule(NETWORK_INFO, code="W_NETWORK_VERSION_MISSING", attribute="version")
def warn_network_has_version(network_info) -> None:
    """A model should record the version of the tool that wrote it.

    classification : Parameter
    fix : Add version metadata to the network model for traceability.
    """
    assert network_info.version, "Network missing a version"
