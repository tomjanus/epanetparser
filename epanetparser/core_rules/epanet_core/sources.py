"""Source rules for the core ruleset.

A water quality source names the node it injects into, the constituent it
injects, and how strongly. All three are needed for the source to mean
anything, so all three are required here; whether the referenced node and
pattern exist is a question about the whole model and is checked by
:mod:`epanetparser.core_rules.epanet_core.network`.

Notes
-----
WNTR's JSON representation names the constituent field ``source_type``, not
``param``, and the modulating pattern ``pattern``, not ``pattern_name``. The
rules use those names, because a rule that looks for the wrong field reports a
defect that is not there.
"""
from epanetparser.core.validation import defined as _defined
from epanetparser.core.validation import rule

SOURCE = "WNTREPANETSource"


@rule(SOURCE, code="E_SOURCE_NODE_MISSING", attribute="node_name")
def rule_source_has_node_name(source) -> None:
    """A source must name the node it injects into."""
    assert _defined(source, "node_name"), "Source does not define node_name"


@rule(SOURCE, code="E_SOURCE_TYPE_MISSING", attribute="source_type")
def rule_source_has_type(source) -> None:
    """A source must name the constituent it injects."""
    assert _defined(source, "source_type"), "Source does not define source_type"


@rule(SOURCE, code="E_SOURCE_STRENGTH_MISSING", attribute="strength")
def rule_source_has_strength(source) -> None:
    """A source must state how much of the constituent it injects."""
    assert _defined(source, "strength"), "Source does not define strength"
