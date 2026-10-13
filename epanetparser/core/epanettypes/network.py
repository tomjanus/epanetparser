"""The EPANET network: a container of components with a name index.

A network holds the model's component collections and the metadata that
describes them. It knows nothing about validity: constructing one succeeds
whatever the components contain. What a model means is a separate question,
answered by :meth:`WNTREPANETNetwork.validate`.

Loading
-------
:meth:`WNTREPANETNetwork.from_file` and :meth:`WNTREPANETNetwork.from_json`
read a model from an ``.inp`` or WNTR ``.json`` file. ``.inp`` files are
converted using the standalone INP parser in ``core.io``.

Validation
----------
:meth:`WNTREPANETNetwork.validate` runs the rules of the selected rulesets
against every component and then against the network as a whole. It returns a
:class:`~epanetparser.core.validation.results.ValidationReport` and never
raises for a rule failure.

Examples
--------
Load and validate a model::

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    network, errors, warnings = WNTREPANETNetwork.from_file("Net1.inp")
    report = network.validate()
    if not report.is_valid:
        for issue in report.errors:
            print(issue.code, issue.component_name, issue.message)

See Also
--------
epanetparser.core.parsers.wntrjsonparser : Builds the model; validates nothing.
epanetparser.core.validation : Rule execution and structured results.
"""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Dict, List, Optional, Sequence, Tuple
from collections import OrderedDict

from epanetparser.core.parsers.wntrjsonparser import WNTRJSONParser
from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException
from epanetparser.core.validation import (
    NetworkIndex,
    ValidationReport,
    Validator,
)
from epanetparser.core.io.network.model import (
    NodeRegistry,
    LinkRegistry,
    PatternRegistry,
    CurveRegistry,
    SourceRegistry,
)
from epanetparser.core.io import InpParseError, read_inp_to_dict
from epanetparser.core.io.epanet.io import InpFile
from epanetparser.core.io.network.io import from_dict

log = logging.getLogger(__name__)


class ComponentList(list):
    """A list that also provides a .values() method for compatibility with registry-based code."""
    
    def values(self):
        """Return self for compatibility with registry-based code."""
        return self


class WNTREPANETNetwork:
    """An EPANET water distribution network.

    Parameters
    ----------
    parser : WNTRJSONParser, optional
        Parser that has already produced the model's components.

    Attributes
    ----------
    network_info : WNTREPANETNetworkInfo
        Model metadata: name, comment, version, references.
    options : WNTREPANETOptions
        Simulation options.
    curves : CurveRegistry
        Curves, in document order.
    patterns : PatternRegistry
        Patterns, in document order.
    nodes : NodeRegistry
        Nodes, in document order.
    links : LinkRegistry
        Links, in document order.
    sources : SourceRegistry
        Water quality sources, in document order.
    controls : OrderedDict
        Controls, in document order.
    index : NetworkIndex
        Name-to-component index, built on first use. Network rules resolve
        references through it.

    Notes
    -----
    The component collections use registries (ordered dicts) that maintain
    document order and allow name-based lookup. They are not keyed by name
    in a way that would hide duplicates; duplicates are tracked separately
    by NetworkIndex.

    Examples
    --------
    >>> network = WNTREPANETNetwork(parser)   # doctest: +SKIP
    >>> network.report()                     # doctest: +SKIP
    {'nodes': 11, 'links': 13, 'patterns': 2}
    >>> network.validate().is_valid          # doctest: +SKIP
    True
    """

    #: Component collections, in the order they are reported and validated.
    COMPONENT_COLLECTIONS: Tuple[str, ...] = (
        "curves",
        "patterns",
        "nodes",
        "links",
        "sources",
        "controls",
    )

    def __init__(self, parser: Optional[WNTRJSONParser] = None) -> None:
        """Initialize the network, optionally loading from a parser.

        Parameters
        ----------
        parser : WNTRJSONParser, optional
            Parser whose :meth:`~WNTRJSONParser.parse` has already run.
        """
        # Initialize registries (internal names)
        self._node_registry = NodeRegistry(self)
        self._link_registry = LinkRegistry(self)
        self._pattern_registry = PatternRegistry(self)
        self._curve_registry = CurveRegistry(self)
        self._source_registry = SourceRegistry(self)
        self._controls = OrderedDict()

        # Maintain lists for order and mutation compatibility
        self._nodes_list = ComponentList()
        self._links_list = ComponentList()
        self._curves_list = ComponentList()
        self._patterns_list = ComponentList()
        self._sources_list = ComponentList()
        self._controls_list = ComponentList()

        # Set attributes needed for registry compatibility with WNTR
        # These use WNTR's naming convention
        self.network_info = None
        self.options = None
        self._options = parser.options if parser else None
        self._pattern_reg = self._pattern_registry
        self._curve_reg = self._curve_registry
        self._node_reg = self._node_registry
        self._link_reg = self._link_registry
        self._controls = self._controls
        self._sources = self._source_registry
        self.index: Optional[NetworkIndex] = None

        # Finalize registries (sets up model reference)
        self._node_registry._finalize_(self)
        self._link_registry._finalize_(self)
        self._pattern_registry._finalize_(self)
        self._curve_registry._finalize_(self)
        self._source_registry._finalize_(self)

        if parser:
            self._load_from_parser(parser)

    def _load_from_parser(self, parser: WNTRJSONParser) -> None:
        """Load components from a parser into the registries and lists."""
        self.network_info = parser.network_info
        self.options = parser.options
        self._options = parser.options
        
        # Load curves
        for curve in parser.curves:
            self._curve_registry[curve.name] = curve
            self._curves_list.append(curve)
        
        # Load patterns
        for pattern in parser.patterns:
            self._pattern_registry[pattern.name] = pattern
            self._patterns_list.append(pattern)
        
        # Load nodes
        for node in parser.nodes:
            if node.name is not None:
                self._node_registry[node.name] = node
            self._nodes_list.append(node)
        
        # Load links
        for link in parser.links:
            if link.name is not None:
                self._link_registry[link.name] = link
            self._links_list.append(link)
        
        # Load sources
        for source in parser.sources:
            if source.name is not None:
                self._source_registry[source.name] = source
            self._sources_list.append(source)
        
        # Load controls
        for control in parser.controls:
            if control.name is not None:
                self._controls[control.name] = control
            self._controls_list.append(control)

    # Properties for backward compatibility and validation engine
    @property
    def curves(self):
        return self._curves_list

    @property
    def patterns(self):
        return self._patterns_list

    @property
    def nodes(self):
        return self._nodes_list

    @property
    def links(self):
        return self._links_list

    @property
    def sources(self):
        return self._sources_list

    @property
    def controls(self):
        return self._controls_list

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    @classmethod
    def from_file(
        cls,
        filename: str | pathlib.Path,
        raise_on_parser_error: bool = False,
        raise_on_parser_warning: bool = False,
        ignore_warnings: bool = False,
    ) -> Tuple[Optional["WNTREPANETNetwork"], Optional[Dict], Optional[Dict]]:
        """Load a network from an ``.inp`` or WNTR ``.json`` file.

        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the model. ``.inp`` files are converted using core.io.
        raise_on_parser_error : bool
            If True, raise a structural parsing problem instead of returning
            it. Rule failures are not involved: nothing is validated here.
        raise_on_parser_warning : bool
            Accepted for compatibility. The parser produces no warnings.
        ignore_warnings : bool
            Accepted for compatibility. The parser produces no warnings.

        Returns
        -------
        network : WNTREPANETNetwork or None
            The parsed model, or None if the document could not be parsed.
        errors : dict or None
            Structural problems, grouped by collection, or None if there were
            none.
        warnings : dict or None
            Always None. The parser produces no warnings; non-fatal findings
            come from :meth:`validate`.

        Raises
        ------
        WNTREPANETParserException
            If the file cannot be read or parsed and ``raise_on_parser_error`` is True.
        InpParseError
            If an INP file cannot be parsed and ``raise_on_parser_error`` is True.
        """
        path = pathlib.Path(filename)
        try:
            if path.suffix.lower() == ".inp":
                # Parse INP using standalone parser
                try:
                    wn_dict = read_inp_to_dict(path.as_posix())
                except InpParseError as err:
                    if raise_on_parser_error:
                        raise
                    return None, {"network": [err]}, None
                network = cls.from_dict(wn_dict)
                return network, None, None
            elif path.suffix.lower() == ".json":
                json_src = path.read_text(encoding="utf-8")
                return cls.from_json(
                    json_src,
                    raise_on_parser_error=raise_on_parser_error,
                    raise_on_parser_warning=raise_on_parser_warning,
                    ignore_warnings=ignore_warnings,
                )
            else:
                raise ValueError(
                    f"Unsupported file extension '{path.suffix}'. Use .inp or .json"
                )
        except (FileNotFoundError, OSError, ValueError) as err:
            message = f"Unable to read input file: {err}"
            if raise_on_parser_error:
                raise WNTREPANETParserException(message) from None
            return None, {"network": [WNTREPANETParserException(message)]}, None

    @classmethod
    def from_dict(cls, wn_dict: Dict[str, Any]) -> "WNTREPANETNetwork":
        """Create a network from a WNTR dictionary."""
        network = cls()
        
        # Load metadata
        from epanetparser.core.epanettypes import (
            WNTREPANETNetworkInfo, 
            WNTREPANETOptions,
            WNTREPANETCurve,
            WNTREPANETPattern,
            WNTREPANETJunction,
            WNTREPANETReservoir,
            WNTREPANETTank,
            WNTREPANETPipe,
            WNTREPANETPump,
            WNTREPANETValve,
            WNTREPANETSource,
            WNTREPANETControl,
        )
        metadata_keys = ("version", "comment", "name", "references")
        network.network_info = WNTREPANETNetworkInfo(
            {key: wn_dict[key] for key in metadata_keys if key in wn_dict}
        )
        network.options = WNTREPANETOptions(wn_dict.get("options", {}))
        network._options = network.options
        
        # Load curves
        for curve in wn_dict.get("curves", []):
            curve_obj = WNTREPANETCurve(curve)
            network._curve_registry[curve["name"]] = curve_obj
            network._curves_list.append(curve_obj)
        
        # Load patterns
        for pattern in wn_dict.get("patterns", []):
            pattern_obj = WNTREPANETPattern(pattern)
            network._pattern_registry[pattern["name"]] = pattern_obj
            network._patterns_list.append(pattern_obj)
        
        # Load nodes
        for node in wn_dict.get("nodes", []):
            node_type = node.get("node_type", "Junction")
            if node_type == "Junction":
                node_obj = WNTREPANETJunction(node)
            elif node_type == "Reservoir":
                node_obj = WNTREPANETReservoir(node)
            elif node_type == "Tank":
                node_obj = WNTREPANETTank(node)
            else:
                node_obj = WNTREPANETNode(node)
            network._node_registry[node["name"]] = node_obj
            network._nodes_list.append(node_obj)
        
        # Load links
        for link in wn_dict.get("links", []):
            link_type = link.get("link_type", "Pipe")
            if link_type == "Pipe":
                link_obj = WNTREPANETPipe(link)
            elif link_type == "Pump":
                link_obj = WNTREPANETPump(link)
            elif link_type == "Valve":
                link_obj = WNTREPANETValve(link)
            else:
                link_obj = WNTREPANETLink(link)
            network._link_registry[link["name"]] = link_obj
            network._links_list.append(link_obj)
        
        # Load sources
        for source in wn_dict.get("sources", []):
            source_obj = WNTREPANETSource(source)
            network._source_registry[source["name"]] = source_obj
            network._sources_list.append(source_obj)
        
        # Load controls
        for i, control in enumerate(wn_dict.get("controls", [])):
            control_name = control.get("name", f"control_{i}")
            control_obj = WNTREPANETControl(control)
            network._controls[control_name] = control_obj
            network._controls_list.append(control_obj)
        
        return network

    @classmethod
    def from_json(
        cls,
        json_src: str,
        raise_on_parser_error: bool = False,
        raise_on_parser_warning: bool = False,
        ignore_warnings: bool = False,
    ) -> Tuple[Optional["WNTREPANETNetwork"], Optional[Dict], Optional[Dict]]:
        """Load a network from a WNTR JSON string.

        Parameters
        ----------
        json_src : str
            JSON-encoded text of an EPANET model in WNTR's format.
        raise_on_parser_error : bool
            If True, raise a structural parsing problem instead of returning
            it.
        raise_on_parser_warning : bool
            Accepted for compatibility. The parser produces no warnings.
        ignore_warnings : bool
            Accepted for compatibility. The parser produces no warnings.

        Returns
        -------
        network : WNTREPANETNetwork or None
            The parsed model, or None if the document could not be parsed.
        errors : dict or None
            Structural problems, grouped by collection, or None if there were
            none.
        warnings : dict or None
            Always None.
        """
        try:
            parser = WNTRJSONParser(json_src)
        except WNTREPANETParserException as exc:
            if raise_on_parser_error:
                raise exc from None
            return None, {"network": [exc]}, None
        parser.parse(
            raise_on_error=raise_on_parser_error,
            raise_on_warning=raise_on_parser_warning,
            ignore_warnings=ignore_warnings,
        )
        warnings = dict(parser.warnings) if parser.has_warnings else None
        if parser.has_errors:
            return None, dict(parser.errors), warnings
        return cls(parser), None, warnings

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def build_index(self) -> NetworkIndex:
        """Return the network's name index, building and caching it if needed.

        Returns
        -------
        NetworkIndex
            Name-to-component index of this network.
        """
        if self.index is None:
            self.index = NetworkIndex(self)
        return self.index

    def invalidate_index(self) -> None:
        """Discard the cached name index so the next use rebuilds it."""
        self.index = None

    def validate(self, context: Any = None) -> ValidationReport:
        """Validate the whole model.

        Parameters
        ----------
        context : Any
            Rule set selection. Anything
            :meth:`~epanetparser.core.validation.engine.ValidationContext.from_any`
            accepts. Defaults to the core ruleset alone; pass a custom ruleset
            to apply application-specific constraints as well.

        Returns
        -------
        ValidationReport
            Component issues in component order, followed by network issues.
            Check :attr:`~epanetparser.core.validation.results.ValidationReport.is_valid`.

        Notes
        -----
        This method contains no rule logic; it delegates to the engine, which
        selects rules by class name. Custom rulesets therefore apply to this
        class without it knowing they exist.

        Raises
        ------
        RuleSetSelectionError
            If ``context`` names a rule set that has not been discovered, or
            does not select exactly one core rule set.
        RuleExecutionError
            If a selected rule raises an exception other than
            ``AssertionError``, which indicates a defect in the rule.
        """
        return Validator.from_context(context, registry=_context_registry(context)).validate(
            self, index=self.build_index()
        )

    # ------------------------------------------------------------------
    # Reporting and serialisation
    # ------------------------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        """Return the model as a dictionary in WNTR's JSON shape.

        Returns
        -------
        Dict[str, Any]
            Metadata, options and every component collection. Empty
            collections are omitted except for ``patterns``, so that a
            round trip preserves the distinction WNTR makes.
        """
        network = self.network_info.as_dict()
        network["options"] = self.options.as_dict()
        
        # Curves
        if self._curve_reg:
            network["curves"] = [item.as_dict() for item in self._curve_reg.values()]
        
        # Patterns (always include, even if empty)
        network["patterns"] = [item.as_dict() for item in self._pattern_reg.values()]
        
        # Nodes
        if self._node_reg:
            network["nodes"] = [item.as_dict() for item in self._node_reg.values()]
        
        # Links
        if self._link_reg:
            network["links"] = [item.as_dict() for item in self._link_reg.values()]
        
        # Sources
        if self._source_registry:
            network["sources"] = [item.as_dict() for item in self._source_registry.values()]
        
        # Controls
        if self._controls:
            network["controls"] = [item.as_dict() for item in self._controls.values()]
        
        return network

    def as_json(self, indent: Optional[int] = 2) -> str:
        """Return the model as a JSON string in WNTR's JSON shape.

        Parameters
        ----------
        indent : Optional[int]
            Number of spaces to indent by. Pass None for compact output.

        Returns
        -------
        str
            JSON text of :meth:`as_dict`.
        """
        return json.dumps(self.as_dict(), indent=indent)

    def report(self) -> Dict[str, int]:
        """Return the number of components in each collection.

        Returns
        -------
        Dict[str, int]
            Component counts. ``nodes`` and ``links`` are always present; the
            remaining collections appear only when non-empty.
        """
        report = {
            "nodes": len(self._node_reg),
            "links": len(self._link_reg),
        }
        for collection in self.COMPONENT_COLLECTIONS:
            if collection in report:
                continue
            count = len(getattr(self, collection))
            if count:
                report[collection] = count
        return report

    def verbose_report(self) -> Dict[str, int]:
        """Return :meth:`report` with capitalised collection names.

        Returns
        -------
        Dict[str, int]
            Component counts keyed by capitalised collection name.
        """
        return {key.capitalize(): count for key, count in self.report().items()}

    def component(self, collection: str, name: str) -> Optional[Any]:
        """Return a component by collection and name.

        Parameters
        ----------
        collection : str
            Collection to look in, for example ``"nodes"``.
        name : str
            Name of the component.

        Returns
        -------
        Any or None
            The component, or None if the collection has no component with
            that name. Duplicate names resolve to the first, which is why
            validation reports duplicates separately.
        """
        return self.build_index().collection(collection).get(name)

    @property
    def name(self) -> str:
        """Network name, or ``"Unnamed Network"`` if it has none."""
        return self.network_info.name or "Unnamed Network"
    
    @name.setter
    def name(self, value: str) -> None:
        """Set the network name."""
        if self.network_info is not None:
            self.network_info.data["name"] = value

    @property
    def comment(self) -> str:
        """Network comment, or an empty string if it has none."""
        return self.network_info.comment or ""

    @property
    def version(self) -> str:
        """Version of the tool that wrote the model, or an empty string."""
        return self.network_info.version or ""

    def to_wntr(self):
        """Return a WaterNetworkModel for WNTR simulation.
        
        Returns
        -------
        WaterNetworkModel
            A WNTR WaterNetworkModel that can be simulated.
        """
        wn = from_dict(self.as_dict())
        # Set _inpfile so the model can be written to INP for simulation
        wn._inpfile = InpFile()
        return wn


def _context_registry(context: Any) -> Optional[Any]:
    """Return the registry a context should resolve against, if it names one."""
    from epanetparser.core.validation import ValidationContext

    if isinstance(context, ValidationContext):
        return context.registry
    return None


class WNTRNetworkStatistics:
    """Counts components in a network, grouped by concrete type.

    Parameters
    ----------
    network : WNTREPANETNetwork
        Network to summarise.

    Notes
    -----
    Unlike :meth:`WNTREPANETNetwork.report`, which counts whole collections,
    this reports the breakdown by concrete type, for example ``Junction`` and
    ``Tank`` within ``nodes``. It reads the components as dictionaries, so it
    works on parser output but not on a model that stores components as
    objects. See ``docs/TODO_MODEL_LAYER_DUPLICATION.md``.

    Examples
    --------
    >>> stats = WNTRNetworkStatistics(network)   # doctest: +SKIP
    >>> stats.report()                          # doctest: +SKIP
    {'nodes': 11, 'nodes type Junction': 9, 'nodes type Tank': 1, ...}
    """

    #: Collection name to the data field holding its concrete type, or None
    #: when the collection is not further subdivided.
    component_typefield_map: Dict[str, Optional[str]] = {
        "nodes": "node_type",
        "links": "link_type",
        "sources": None,
        "curves": "curve_type",
        "patterns": None,
        "controls": "type",
    }

    def __init__(self, network: WNTREPANETNetwork) -> None:
        """Store the network to summarise."""
        self.network = network

    def get_component_types(self, component_name: str) -> List[str]:
        """Return the concrete types present in a collection.

        Parameters
        ----------
        component_name : str
            Collection name, for example ``"nodes"``.

        Returns
        -------
        List[str]
            Concrete types, in the order first encountered. Empty for a
            collection that is not subdivided.
        """
        type_field = self.component_typefield_map.get(component_name)
        store = self._records(component_name)
        if type_field is None:
            return []
        component_types: List[str] = []
        for component in store:
            value = component.get(type_field)
            if value is not None and value not in component_types:
                component_types.append(value)
        return component_types

    def get_number_of_components(
        self,
        component_name: str,
        component_type: Optional[str] = None,
    ) -> int:
        """Count components in a collection, optionally of one concrete type.

        Parameters
        ----------
        component_name : str
            Collection name, for example ``"nodes"``.
        component_type : Optional[str]
            Concrete type to count, for example ``"Junction"``. All components
            in the collection are counted when omitted.

        Returns
        -------
        int
            Number of matching components.
        """
        store = self._records(component_name)
        if component_type is None:
            return len(store)
        type_field = self.component_typefield_map.get(component_name)
        if type_field is None:
            return 0
        return sum(1 for item in store if item.get(type_field) == component_type)

    def report(self) -> Dict[str, int]:
        """Return component counts, with a per-concrete-type breakdown.

        Returns
        -------
        Dict[str, int]
            Counts keyed by collection name, plus one ``"<collection> type
            <type>"`` entry per concrete type present.
        """
        report: Dict[str, int] = {}
        for collection in self.component_typefield_map:
            component_types = self.get_component_types(collection)
            count = self.get_number_of_components(collection)
            if count:
                report[collection] = count
            for component_type in component_types:
                report[f"{collection} type {component_type}"] = (
                    self.get_number_of_components(collection, component_type)
                )
        return report

    def _records(self, component_name: str) -> Sequence[Dict[str, Any]]:
        """Return a collection's components as dictionaries.

        Parameters
        ----------
        component_name : str
            Collection name.

        Returns
        -------
        Sequence[Dict[str, Any]]
            The components' data dictionaries, or an empty sequence for an
            unknown collection.
        """
        store = getattr(self.network, component_name, None)
        if store is None:
            return []
        records: List[Dict[str, Any]] = []
        for component in store:
            data = component.get if isinstance(component, dict) else None
            if data is None:
                data = getattr(component, "data", None)
            if isinstance(data, dict):
                records.append(data)
        return records