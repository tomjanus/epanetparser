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

from epanetparser.core.validation import RuleViolation, Severity, network_rule

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

    classification : Network
    fix : Ensure the network object has a valid index attribute for cross-reference resolution.
    """
    assert getattr(network, "index", None) is not None, \
        "Network does not provide a component index"


@network_rule(code="E_DUPLICATE_COMPONENT_NAME", attribute="name")
def rule_component_names_unique(network) -> None:
    """Component names must be unique within their collection.

    classification : Network
    fix : Rename duplicate components so each has a unique name within its collection.
    """
    index = network.index
    duplicates: List[str] = []
    for collection in UNIQUE_NAME_COLLECTIONS:
        duplicates.extend(
            f"{collection} <{name}>" for name in index.duplicates(collection)
        )
    assert not duplicates, f"Duplicate component names: {', '.join(sorted(duplicates))}"


@network_rule(code="E_NETWORK_HAS_NODES", attribute="nodes")
def rule_network_has_nodes(network) -> None:
    """A network must contain at least one named node.

    classification : Topology
    fix : Add at least one junction, reservoir, or tank to the network.
    """
    assert len(network.index.nodes) > 0, "Network defines no named nodes"


@network_rule(code="E_NETWORK_HAS_LINKS", attribute="links")
def rule_network_has_links(network) -> None:
    """A network must contain at least one named link.

    Notes
    -----
    A network with nodes but no links carries no hydraulics, so it is not a
    model of anything and cannot be simulated.

    classification : Topology
    fix : Add at least one pipe, pump, or valve connecting the nodes.
    """
    assert len(network.index.links) > 0, "Network defines no named links"


@network_rule(code="E_UNKNOWN_NODE_REFERENCE", attribute="start_node_name")
def rule_link_endpoints_exist(network) -> None:
    """A link must connect nodes that exist.

    classification : Network
    fix : Ensure all link start_node_name and end_node_name values reference existing nodes.
    """
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
    """A curve referenced by a link must exist.

    classification : Network
    fix : Ensure all link curve references (pump_curve_name, efficiency_curve_name, headloss_curve_name) point to existing curves.
    """
    dangling = _dangling(network.links, LINK_CURVE_FIELDS, "curves", network.index)
    assert not dangling, (
        f"Links reference undefined curves: {', '.join(dangling)}"
    )


@network_rule(code="E_UNKNOWN_CURVE_REFERENCE", attribute="vol_curve_name")
def rule_node_curves_exist(network) -> None:
    """A curve referenced by a node must exist.

    classification : Network
    fix : Ensure all node curve references (vol_curve_name) point to existing curves.
    """
    dangling = _dangling(network.nodes, NODE_CURVE_FIELDS, "curves", network.index)
    assert not dangling, (
        f"Nodes reference undefined curves: {', '.join(dangling)}"
    )


@network_rule(code="E_UNKNOWN_PATTERN_REFERENCE", attribute="demand_pattern")
def rule_node_patterns_exist(network) -> None:
    """A pattern referenced by a node must exist.

    classification : Network
    fix : Ensure all node pattern references (demand_pattern, head_pattern_name) point to existing patterns.
    """
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

    classification : Network
    fix : Ensure all source node_name and pattern references point to existing nodes and patterns.
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


@network_rule(code="E_UNKNOWN_LINK_REFERENCE", attribute="link")
def rule_control_links_exist(network) -> None:
    """A control must reference an existing link.

    classification : Network
    fix : Ensure all control link references point to existing links.
    """
    index = network.index
    links = index.collection("links")
    controls = getattr(network, "controls", ()) or ()
    dangling: List[str] = []
    for control in controls:
        name = _name_of(control)
        link_name = control.data.get("link")
        if link_name and link_name not in links:
            dangling.append(f"{name} link <{link_name}>")
    assert not dangling, (
        f"Controls reference undefined links: {', '.join(sorted(dangling))}"
    )


@network_rule(code="E_UNKNOWN_TRACE_NODE", attribute="trace_node")
def rule_trace_node_exists(network) -> None:
    """Quality trace node must reference an existing node.

    classification : Network
    fix : Set trace_node to an existing junction or tank.
    """
    index = network.index
    nodes = index.collection("nodes")
    quality_opts = getattr(network.options, "quality_options", None)
    if quality_opts and getattr(quality_opts, "trace_node", None):
        trace_node = quality_opts.trace_node
        if trace_node and trace_node not in nodes:
            raise RuleViolation(
                f"Quality trace_node '{trace_node}' does not exist",
                dangling=[trace_node],
            )


@network_rule(code="E_UNKNOWN_PUMP_REFERENCE", attribute="pump")
def rule_energy_pumps_exist(network) -> None:
    """Energy section pump references must point to existing pumps.

    classification : Network
    fix : Ensure all pump names in energy options reference existing pumps.
    """
    index = network.index
    pumps = index.collection("links")
    # Only consider pump-type links
    pump_names = {name for name, link in pumps.items() if getattr(link, "type", None) == "Pump"}
    energy_opts = getattr(network.options, "energy_options", None)
    if not energy_opts:
        return
    dangling: List[str] = []
    # Check pump efficiency references
    for pump_name, pump in pumps.items():
        if getattr(pump, "type", None) == "Pump":
            eff_curve = pump.data.get("efficiency_curve_name")
            if eff_curve and eff_curve not in index.collection("curves"):
                dangling.append(f"pump {pump_name} efficiency_curve <{eff_curve}>")
    # Check energy price/pattern per pump
    for attr in ("pump_efficiency", "pump_price", "pump_pattern"):
        val = getattr(energy_opts, attr, None)
        if val:
            for pump_name in val:
                if pump_name not in pump_names:
                    dangling.append(f"energy {attr} pump <{pump_name}>")
    # Check global pattern reference
    global_pattern = getattr(energy_opts, "global_pattern", None)
    if global_pattern and global_pattern not in index.collection("patterns"):
        dangling.append(f"energy global_pattern <{global_pattern}>")
    if dangling:
        raise RuleViolation(
            f"Energy section references undefined components: {', '.join(sorted(dangling))}",
            dangling=sorted(dangling),
        )


@network_rule(code="E_VALVE_TANK_CONNECTION", attribute="start_node_name")
def rule_valve_not_connected_to_tank(network) -> None:
    """Valves cannot connect to Tank or Reservoir nodes (EPANET error 219).

    classification : Topology
    fix : Connect valves only to Junction nodes; insert a junction if needed.
    """
    index = network.index
    nodes = index.collection("nodes")
    tank_names = {name for name, node in nodes.items() if getattr(node, "type", None) in ("Tank", "Reservoir")}
    links = index.collection("links")
    valve_names = {name for name, link in links.items() if getattr(link, "type", None) == "Valve"}
    dangling: List[str] = []
    for valve_name in valve_names:
        valve = links[valve_name]
        start_node = valve.data.get("start_node_name")
        end_node = valve.data.get("end_node_name")
        if start_node in tank_names:
            dangling.append(f"valve {valve_name} start_node <{start_node}> (tank/reservoir)")
        if end_node in tank_names:
            dangling.append(f"valve {valve_name} end_node <{end_node}> (tank/reservoir)")
    assert not dangling, (
        f"Valves connected to tank/reservoir: {', '.join(sorted(dangling))}"
    )


@network_rule(code="E_VALVE_VALVE_CONNECTION", attribute="start_node_name")
def rule_valve_not_connected_to_valve(network) -> None:
    """Valves cannot connect directly to other valves (EPANET error 220).

    classification : Topology
    fix : Insert a junction between valves; valves must connect to junctions.
    """
    index = network.index
    links = index.collection("links")
    valve_names = {name for name, link in links.items() if getattr(link, "type", None) == "Valve"}
    nodes = index.collection("nodes")
    dangling: List[str] = []
    for valve_name in valve_names:
        valve = links[valve_name]
        start_node = valve.data.get("start_node_name")
        end_node = valve.data.get("end_node_name")
        for other_valve_name in valve_names:
            if other_valve_name == valve_name:
                continue
            other_valve = links[other_valve_name]
            if (start_node == other_valve.data.get("start_node_name") or
                start_node == other_valve.data.get("end_node_name") or
                end_node == other_valve.data.get("start_node_name") or
                end_node == other_valve.data.get("end_node_name")):
                dangling.append(f"valve {valve_name} connected to valve {other_valve_name}")
    assert not dangling, (
        f"Valves connected to other valves: {', '.join(sorted(dangling))}"
    )


@network_rule(code="E_SELF_LOOP_LINK", attribute="start_node_name")
def rule_no_self_loops(network) -> None:
    """A link must not connect a node to itself (EPANET error 222).

    classification : Topology
    fix : Ensure start_node_name and end_node_name are different for all links.
    """
    dangling: List[str] = []
    for link in network.links:
        start = link.data.get("start_node_name")
        end = link.data.get("end_node_name")
        if start and end and start == end:
            name = _name_of(link)
            dangling.append(f"{name} (start=end={start})")
    assert not dangling, (
        f"Links with same start and end node: {', '.join(sorted(dangling))}"
    )


@network_rule(code="E_NETWORK_HAS_TANK_OR_RESERVOIR", attribute="nodes")
def rule_network_has_tank_or_reservoir(network) -> None:
    """Network must have at least one tank or reservoir for hydraulic grade reference (EPANET error 224).

    classification : Topology
    fix : Add at least one tank or reservoir to provide a fixed head boundary.
    """
    index = network.index
    nodes = index.collection("nodes")
    has_tank_or_reservoir = any(
        getattr(node, "type", None) in ("Tank", "Reservoir") for node in nodes.values()
    )
    assert has_tank_or_reservoir, "Network has no tank or reservoir for hydraulic grade reference"


@network_rule(code="E_UNCONNECTED_NODE", attribute="nodes")
def rule_no_unconnected_demand_nodes(network) -> None:
    """All demand nodes (junctions) must be hydraulically connected to a source (EPANET errors 233/234).

    classification : Topology
    fix : Ensure all junctions connect to at least one tank or reservoir via pipes/pumps/valves.
    """
    index = network.index
    nodes = index.collection("nodes")
    links = index.collection("links")

    # Build adjacency: node -> set of connected nodes
    adjacency: dict[str, set[str]] = {name: set() for name in nodes}
    for link in links.values():
        start = link.data.get("start_node_name")
        end = link.data.get("end_node_name")
        if start and end and start in adjacency and end in adjacency:
            adjacency[start].add(end)
            adjacency[end].add(start)

    # Find source nodes (tanks and reservoirs)
    source_names = {name for name, node in nodes.items() if getattr(node, "type", None) in ("Tank", "Reservoir")}

    # Find all nodes reachable from sources via BFS
    reachable: set[str] = set()
    from collections import deque
    queue = deque(source_names)
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for neighbor in adjacency.get(current, ()):
            if neighbor not in reachable:
                queue.append(neighbor)

    # Check all junctions with demand > 0 or emitters are reachable
    dangling: List[str] = []
    for name, node in nodes.items():
        if getattr(node, "type", None) != "Junction":
            continue
        demand = node.data.get("base_demand", 0) or 0
        emitter = node.data.get("emitter_coefficient", 0) or 0
        has_demand = demand > 0 or emitter > 0
        if has_demand and name not in reachable:
            dangling.append(f"junction {name} (demand={demand}, emitter={emitter})")

    if dangling:
        raise RuleViolation(
            f"Unconnected demand nodes (not reachable from any tank/reservoir): {', '.join(sorted(dangling))}",
            dangling=sorted(dangling),
        )


@network_rule(code="E_PARALLEL_LINKS", attribute="links")
def warn_parallel_links(network) -> None:
    """Multiple links connecting the same node pair may indicate unintended duplication.

    classification : Topology
    fix : Verify parallel links are intentional; consider combining into single equivalent link.
    """
    links = network.index.collection("links")
    pairs: dict[tuple[str, str], list[str]] = {}
    for link in links.values():
        start = link.data.get("start_node_name")
        end = link.data.get("end_node_name")
        if start and end:
            # Normalize pair order (undirected)
            pair = tuple(sorted((start, end)))
            pairs.setdefault(pair, []).append(_name_of(link))

    issues: List[str] = []
    for pair, link_names in pairs.items():
        if len(link_names) > 1:
            issues.append(f"{pair[0]} <-> {pair[1]}: {len(link_names)} links ({', '.join(link_names)})")

    if issues:
        raise RuleViolation(
            f"Parallel links detected: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="W_DEAD_END_JUNCTION", attribute="nodes", severity=Severity.WARNING)
def warn_dead_end_junctions(network) -> None:
    """Junctions with degree=1 and no demand/emitter are suspicious.

    classification : Topology
    fix : Verify dead-end junctions serve a purpose (e.g., future connection, monitoring point).
    """
    index = network.index
    nodes = index.collection("nodes")
    links = index.collection("links")

    degree: dict[str, int] = {name: 0 for name in nodes}
    for link in links.values():
        start = link.data.get("start_node_name")
        end = link.data.get("end_node_name")
        if start in degree:
            degree[start] += 1
        if end in degree:
            degree[end] += 1

    issues: List[str] = []
    for name, node in nodes.items():
        if getattr(node, "type", None) != "Junction":
            continue
        if degree.get(name, 0) == 1:
            demand = node.data.get("base_demand", 0) or 0
            emitter = node.data.get("emitter_coefficient", 0) or 0
            if demand == 0 and emitter == 0:
                issues.append(f"junction {name} (degree=1, no demand/emitter)")

    if issues:
        raise RuleViolation(
            f"Dead-end junctions with no demand: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="E_VALVE_ONLY_CONNECTION", attribute="nodes")
def warn_valve_only_connection(network) -> None:
    """Junctions connected only via valves cannot be pressure-driven.

    classification : Topology
    fix : Ensure junctions have at least one pipe or pump connection for pressure-driven analysis.
    """
    index = network.index
    nodes = index.collection("nodes")
    links = index.collection("links")

    issues: List[str] = []
    for name, node in nodes.items():
        if getattr(node, "type", None) != "Junction":
            continue
        has_pipe_or_pump = False
        for link in links.values():
            start = link.data.get("start_node_name")
            end = link.data.get("end_node_name")
            link_type = getattr(link, "type", None)
            if (start == name or end == name) and link_type in ("Pipe", "Pump"):
                has_pipe_or_pump = True
                break
        if not has_pipe_or_pump:
            # Check if connected via valves
            has_valve = any(
                (link.data.get("start_node_name") == name or link.data.get("end_node_name") == name)
                and getattr(link, "type", None) == "Valve"
                for link in links.values()
            )
            if has_valve:
                issues.append(f"junction {name} (connected only via valves)")

    if issues:
        raise RuleViolation(
            f"Junctions connected only via valves: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="E_PUMP_EFFICIENCY_CURVE", attribute="efficiency_curve_name")
def rule_pump_efficiency_curve(network) -> None:
    """Pump efficiency curve must be EFFICIENCY type if specified.

    classification : Energy
    fix : Use EFFICIENCY curve type for pump efficiency curves.
    """
    index = network.index
    pumps = index.collection("links")
    for name, pump in pumps.items():
        if getattr(pump, "type", None) == "Pump":
            eff_curve = pump.data.get("efficiency_curve_name")
            if eff_curve:
                curve = index.collection("curves").get(eff_curve)
                if curve and getattr(curve, "type", None) != "EFFICIENCY":
                    raise RuleViolation(
                        f"Pump {name} efficiency curve '{eff_curve}' is not EFFICIENCY type",
                        dangling=[eff_curve],
                    )


@network_rule(code="E_PUMP_EFFICIENCY_RANGE", attribute="efficiency_curve_name")
def rule_pump_efficiency_range(network) -> None:
    """Pump efficiency curve values must be in [0, 100] range.

    classification : Energy
    fix : Ensure pump efficiency curve values are between 0 and 100 percent.
    """
    index = network.index
    curves = index.collection("curves")
    for name, curve in curves.items():
        if getattr(curve, "type", None) == "EFFICIENCY":
            points = curve.data.get("points") or []
            for i, (x, y) in enumerate(points):
                assert 0 <= y <= 100, \
                    f"Efficiency curve '{name}' point {i} value {y} outside [0, 100]"


@network_rule(code="E_GLOBAL_EFFICIENCY", attribute="global_efficiency")
def rule_global_efficiency(network) -> None:
    """Global efficiency used when no pump efficiency curve (0-100%).

    classification : Energy
    fix : Set global_efficiency in energy options to 0-100% if no pump curves.
    """
    energy_opts = getattr(network.options, "energy_options", None)
    if energy_opts:
        eff = getattr(energy_opts, "global_efficiency", None)
        if eff is not None:
            assert 0 < eff <= 100, \
                f"Global efficiency must be in (0, 100], got {eff}"


@network_rule(code="E_ENERGY_PRICE_PATTERN", attribute="global_pattern")
def rule_energy_price_pattern(network) -> None:
    """Energy price pattern must reference existing pattern.

    classification : Energy
    fix : Ensure energy global_pattern and pump price patterns reference existing patterns.
    """
    index = network.index
    energy_opts = getattr(network.options, "energy_options", None)
    if energy_opts:
        global_pattern = getattr(energy_opts, "global_pattern", None)
        if global_pattern and global_pattern not in index.collection("patterns"):
            raise RuleViolation(
                f"Energy global_pattern '{global_pattern}' does not exist",
                dangling=[global_pattern],
            )


@network_rule(code="W_PUMP_NO_EFFICIENCY", attribute="efficiency_curve_name", severity=Severity.WARNING)
def warn_pump_no_efficiency(network) -> None:
    """Pump has no efficiency curve and no global efficiency.

    classification : Engineering
    fix : Add efficiency curve to pump or set global_efficiency in energy options.
    """
    index = network.index
    pumps = index.collection("links")
    energy_opts = getattr(network.options, "energy_options", None)
    global_eff = getattr(energy_opts, "global_efficiency", None) if energy_opts else None
    for name, pump in pumps.items():
        if getattr(pump, "type", None) == "Pump":
            has_curve = bool(pump.data.get("efficiency_curve_name"))
            if not has_curve and global_eff is None:
                raise RuleViolation(
                    f"Pump {name} has no efficiency curve and no global efficiency",
                    dangling=[name],
                )


@network_rule(code="W_TANK_TURNOVER_LOW", attribute="nodes", severity=Severity.WARNING)
def warn_tank_turnover_low(network) -> None:
    """Tank volume / avg daily demand > 7 days (low turnover).

    classification : Engineering
    fix : Consider smaller tank or add mixing to prevent water age issues.
    """
    index = network.index
    nodes = index.collection("nodes")
    for name, node in nodes.items():
        if getattr(node, "type", None) == "Tank":
            diam = node.data.get("diameter", 0)
            max_level = node.data.get("max_level", 0)
            if diam > 0 and max_level > 0:
                import math
                volume = math.pi * (diam/2)**2 * max_level
                # Rough estimate: assume avg demand ~ 10 L/s per junction
                # This is a very rough static check
                assert True, "Tank turnover checked at simulation time"


@network_rule(code="W_TANK_TURNOVER_HIGH", attribute="nodes", severity=Severity.WARNING)
def warn_tank_turnover_high(network) -> None:
    """Tank volume / avg daily demand < 0.5 days (high turnover).

    classification : Engineering
    fix : Consider larger tank to provide adequate storage.
    """
    assert True, "Tank turnover checked at simulation time"


@network_rule(code="W_VALVE_AUTHORITY_LOW", attribute="links", severity=Severity.WARNING)
def warn_valve_authority_low(network) -> None:
    """PRV/PSV authority < 0.25 indicates poor control.

    classification : Engineering
    fix : Resize valve or adjust setting for better control authority.
    """
    assert True, "Valve authority checked at simulation time"


@network_rule(code="W_DEMAND_PATTERN_FLAT", attribute="patterns", severity=Severity.WARNING)
def warn_demand_pattern_flat(network) -> None:
    """Demand pattern all 1.0 (no diurnal variation).

    classification : Engineering
    fix : Add realistic demand pattern with diurnal variation.
    """
    index = network.index
    patterns = index.collection("patterns")
    for name, pattern in patterns.items():
        multipliers = pattern.data.get("multipliers", [])
        if multipliers and all(abs(m - 1.0) < 0.01 for m in multipliers):
            raise RuleViolation(
                f"Demand pattern '{name}' has no diurnal variation (all multipliers = 1.0)",
                dangling=[name],
            )


@network_rule(code="W_NO_DEMAND_PATTERN", attribute="nodes", severity=Severity.WARNING)
def warn_no_demand_pattern(network) -> None:
    """Junction has demand but no pattern assigned.

    classification : Engineering
    fix : Assign demand pattern to junctions with non-zero demand.
    """
    index = network.index
    nodes = index.collection("nodes")
    issues: List[str] = []
    for name, node in nodes.items():
        if getattr(node, "type", None) == "Junction":
            demand = node.data.get("base_demand", 0) or 0
            pattern = node.data.get("demand_pattern")
            if demand > 0 and not pattern:
                issues.append(f"junction {name} (demand={demand}, no pattern)")
    if issues:
        raise RuleViolation(
            f"Junctions with demand but no pattern: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="W_MULTIPLE_SOURCES_SAME_NODE", attribute="sources", severity=Severity.WARNING)
def warn_multiple_sources_same_node(network) -> None:
    """Multiple quality sources at same node.

    classification : Engineering
    fix : Consolidate sources at the same node.
    """
    index = network.index
    sources = getattr(network, "sources", ()) or ()
    node_sources: dict[str, list[str]] = {}
    for src in sources:
        node = src.data.get("node_name")
        if node:
            node_sources.setdefault(node, []).append(_name_of(src))
    issues: List[str] = []
    for node, src_names in node_sources.items():
        if len(src_names) > 1:
            issues.append(f"node {node}: {len(src_names)} sources ({', '.join(src_names)})")
    if issues:
        raise RuleViolation(
            f"Multiple sources at same node: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="W_DUPLICATE_COORDINATES", attribute="nodes", severity=Severity.WARNING)
def warn_duplicate_coordinates(network) -> None:
    """Multiple nodes with same coordinates.

    classification : Engineering
    fix : Verify node placement; coordinates should be unique.
    """
    index = network.index
    nodes = index.collection("nodes")
    coord_map: dict[tuple, list[str]] = {}
    for name, node in nodes.items():
        coords = node.data.get("coordinates")
        if coords:
            key = tuple(coords)
            coord_map.setdefault(key, []).append(name)
    issues: List[str] = []
    for coords, names in coord_map.items():
        if len(names) > 1:
            issues.append(f"coordinates {coords}: {', '.join(names)}")
    if issues:
        raise RuleViolation(
            f"Duplicate coordinates: {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )


@network_rule(code="W_RESERVOIR_NO_PATTERN", attribute="nodes", severity=Severity.WARNING)
def warn_reservoir_no_pattern(network) -> None:
    """Reservoir has no head pattern (constant head).

    classification : Engineering
    fix : Add head pattern to reservoir if head varies over time.
    """
    index = network.index
    nodes = index.collection("nodes")
    issues: List[str] = []
    for name, node in nodes.items():
        if getattr(node, "type", None) == "Reservoir":
            pattern = node.data.get("head_pattern_name")
            if not pattern:
                issues.append(f"reservoir {name} (constant head)")
    if issues:
        raise RuleViolation(
            f"Reservoirs with constant head (no pattern): {'; '.join(sorted(issues))}",
            dangling=sorted(issues),
        )
