"""Network-level rules for the core ruleset.

These are the checks a component rule cannot make. A component rule sees one
component and cannot know whether the thing it names exists, and it cannot see
a second component with the same name. Those are questions about the model as a
whole, so they are answered here, where the whole model and its name index are
available as ``network.index``.

Three families of rule live here:

* **Uniqueness.** Component names identify components, so they must be unique
  within their collection. Duplicate names used to be detected while parsing,
  which made parsing and validation inseparable; they are checked here instead.
* **Reference resolution.** Names that point at other components must resolve:
  a link must connect nodes that exist, a pump must reference a curve that
  exists, a node's demand pattern must be a pattern in the model, and so on.
* **Vaguely-non-empty models.** A model with no nodes, or with nodes but no
  links, carries no hydraulics and is not a model of anything.

A note on curve types
---------------------
Reference rules check that a referenced curve *exists*, not that it has a
particular ``curve_type``. WNTR's JSON representation labels every pump curve
``HEAD`` rather than ``PUMP``, and a tank volume curve ``HEAD`` rather than
``VOLUME``, so demanding a specific type would reject valid models. Whether a
curve is semantically the right one is a simulation concern rather than a
structural one, and is out of scope for static validation.
"""
from typing import Any, List, Sequence, Tuple

from epanetparser.core.validation import RuleViolation, network_rule

#: Component collections whose names must be unique.
UNIQUE_NAME_COLLECTIONS = ("nodes", "links", "curves", "patterns")

#: Link fields that name a node, with the endpoint each one names.
LINK_ENDPOINT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("start_node_name", "start"),
    ("end_node_name", "end"),
)

#: Link fields that hold the name of a curve.
LINK_CURVE_FIELDS: Tuple[str, ...] = (
    "pump_curve_name",
    "efficiency_curve_name",
    "headloss_curve_name",
)

#: Node fields that hold the name of a curve.
NODE_CURVE_FIELDS: Tuple[str, ...] = ("vol_curve_name",)

#: Node fields that hold the name of a pattern.
NODE_PATTERN_FIELDS: Tuple[str, ...] = (
    "demand_pattern",
    "head_pattern_name",
)


def _name_of(component: Any) -> str:
    """Return the name of a component, or a placeholder if it has none."""
    return component.data.get("name") or f"<unnamed {type(component).__name__}>"


def _dangling(
    components: Sequence[Any],
    fields: Sequence[str],
    collection: str,
    index: Any,
) -> List[str]:
    """Describe every reference in ``fields`` that does not resolve.

    Parameters
    ----------
    components : Sequence[Any]
        Components whose references are checked.
    fields : Sequence[str]
        Component data fields that hold a reference.
    collection : str
        Collection the references are resolved against.
    index : NetworkIndex
        The index to resolve against.

    Returns
    -------
    List[str]
        One ``"<component> <field> <target>"`` description per dangling
        reference, sorted. Empty when every reference resolves.
    """
    targets = index.collection(collection)
    dangling: List[str] = []
    for component in components or ():
        name = _name_of(component)
        for field in fields:
            referenced = component.data.get(field)
            if referenced and referenced not in targets:
                dangling.append(f"{name} {field} <{referenced}>")
    return sorted(dangling)


@network_rule(code="E_NETWORK_INDEX_UNAVAILABLE")
def rule_network_index_available(network) -> None:
    """A network must expose the index that network rules resolve names with.

    Notes
    -----
    The engine builds and caches the index before running any network rule, so
    a failure here means the object is not shaped like a network at all.
    Reporting it is more useful than an ``AttributeError`` raised by whichever
    rule happened to run first.
    """
    assert getattr(network, "index", None) is not None, \
        "Network does not provide a component index"


@network_rule(code="E_DUPLICATE_COMPONENT_NAME", attribute="name")
def rule_component_names_unique(network) -> None:
    """Component names must be unique within their collection."""
    index = network.index
    duplicates: List[str] = []
    for collection in UNIQUE_NAME_COLLECTIONS:
        duplicates.extend(
            f"{collection} <{name}>" for name in index.duplicates(collection)
        )
    assert not duplicates, f"Duplicate component names: {', '.join(sorted(duplicates))}"


@network_rule(code="E_NETWORK_HAS_NODES", attribute="nodes")
def rule_network_has_nodes(network) -> None:
    """A network must contain at least one named node."""
    assert len(network.index.nodes) > 0, "Network defines no named nodes"


@network_rule(code="E_NETWORK_HAS_LINKS", attribute="links")
def rule_network_has_links(network) -> None:
    """A network must contain at least one named link.

    Notes
    -----
    A network with nodes but no links carries no hydraulics, so it is not a
    model of anything and cannot be simulated.
    """
    assert len(network.index.links) > 0, "Network defines no named links"


@network_rule(code="E_UNKNOWN_NODE_REFERENCE", attribute="start_node_name")
def rule_link_endpoints_exist(network) -> None:
    """A link must connect nodes that exist."""
    index = network.index
    dangling: List[str] = []
    nodes = index.collection("nodes")
    for link in network.links:
        name = _name_of(link)
        for field, endpoint in LINK_ENDPOINT_FIELDS:
            node_name = link.data.get(field)
            if node_name and node_name not in nodes:
                dangling.append(f"{name} {endpoint} node {field} <{node_name}>")
    assert not dangling, (
        f"Links reference undefined nodes: {', '.join(sorted(dangling))}"
    )


@network_rule(code="E_UNKNOWN_CURVE_REFERENCE", attribute="pump_curve_name")
def rule_link_curves_exist(network) -> None:
    """A curve referenced by a link must exist."""
    dangling = _dangling(network.links, LINK_CURVE_FIELDS, "curves", network.index)
    assert not dangling, (
        f"Links reference undefined curves: {', '.join(dangling)}"
    )


@network_rule(code="E_UNKNOWN_CURVE_REFERENCE", attribute="vol_curve_name")
def rule_node_curves_exist(network) -> None:
    """A curve referenced by a node must exist."""
    dangling = _dangling(network.nodes, NODE_CURVE_FIELDS, "curves", network.index)
    assert not dangling, (
        f"Nodes reference undefined curves: {', '.join(dangling)}"
    )


@network_rule(code="E_UNKNOWN_PATTERN_REFERENCE", attribute="demand_pattern")
def rule_node_patterns_exist(network) -> None:
    """A pattern referenced by a node must exist."""
    dangling = _dangling(network.nodes, NODE_PATTERN_FIELDS, "patterns", network.index)
    assert not dangling, (
        f"Nodes reference undefined patterns: {', '.join(dangling)}"
    )


@network_rule(code="E_UNKNOWN_COMPONENT_REFERENCE", attribute="node_name")
def rule_source_references_exist(network) -> None:
    """The node and pattern a source names must exist.

    Notes
    -----
    Sources are rare and a dangling source reference is easy to overlook in a
    long report, so this rule raises a :class:`RuleViolation` that lists every
    dangling reference in the issue context.
    """
    index = network.index
    sources = getattr(network, "sources", ()) or ()
    dangling = _dangling(sources, ("node_name",), "nodes", index) + _dangling(
        sources, ("pattern",), "patterns", index
    )
    if dangling:
        raise RuleViolation(
            f"Sources reference undefined components: {', '.join(sorted(dangling))}",
            dangling=sorted(dangling),
        )
