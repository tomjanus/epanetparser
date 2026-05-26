"""WNTR JSON format parser for EPANET network models.

This module provides a parser for EPANET network models encoded in WNTR's JSON format.
It validates the network structure against configurable rulesets and collects errors and
warnings during the parsing process.

The parser handles all major EPANET components including:
- Network metadata (name, version, comments)
- Options (simulation parameters)
- Curves (pump/valve curves)
- Patterns (demand/control patterns)
- Nodes (junctions, tanks, reservoirs)
- Links (pipes, pumps, valves)
- Sources (water quality sources)
- Controls (simple and rule-based controls)

Key Features:
- Flexible error handling (raise immediately or collect)
- Warning collection for non-critical issues
- Duplicate component detection
- Ruleset-based validation
"""
from typing import Optional, Any, Dict, List, Tuple
import json
from collections import defaultdict
from functools import partial

from epanetparser import rules
from epanetparser.epanet_types import (
    WNTREPANETNetworkInfo,
    WNTREPANETOptions,
    WNTREPANETCurve,
    WNTREPANETPattern,
    WNTREPANETNode,
    WNTREPANETLink,
    WNTREPANETSource,
    WNTREPANETControl
)
from epanetparser.epanet_types.exceptions import (
    WNTREPANETParserException,
    WNTREPANETNetworkValidationError
)
from epanetparser.utils import raiseorpush

# Constants for handling duplicate keys in JSON
DUP_KEY_BASE = "__WNTREPANETParser_Duplicate_Key_{pattern}__"
DUP_KEY_FLAG = DUP_KEY_BASE.format(pattern="{idx:03d}")
DUP_KEY_RE = r"{base}".format(base=DUP_KEY_BASE.format(pattern="[0-9]{3}"))


class WNTRJSONParser:
    """Parser for EPANET network models in WNTR JSON format.
    
    This parser validates and processes EPANET network models encoded in WNTR's
    JSON format. It applies validation rules from the specified ruleset and
    collects errors and warnings encountered during parsing.
    
    Attributes:
        errors: Dictionary mapping component types to lists of validation errors.
        warnings: Dictionary mapping component types to lists of validation warnings.
        src: Parsed JSON source dictionary.
        network_info: Parsed network metadata (WNTREPANETNetworkInfo object).
        options: Parsed simulation options (WNTREPANETOptions object).
        curves: List of parsed curve objects.
        patterns: List of parsed pattern objects.
        nodes: List of parsed node objects.
        links: List of parsed link objects.
        sources: List of parsed source objects.
        controls: List of parsed control objects.
    """
    
    def __init__(self, json_src: str, ruleset: Optional[str] = None) -> None:
        """Initialize the parser with JSON source and optional ruleset.

        Args:
            json_src: JSON-encoded string representation of an EPANET network
                     in WNTR format.
            ruleset: Optional key of a ruleset to apply during validation.
        
        Raises:
            WNTREPANETParserException: If the JSON is invalid or malformed.
        """

        self.errors: Dict[str, List] = defaultdict(list)
        self.warnings: Dict[str, List] = defaultdict(list)

        if ruleset:
            self.set_parser_ruleset(ruleset)

        try:
            self.src: Dict[str, Any] = json.loads(
                json_src, object_pairs_hook=self.__class__.enforce_unique)
        except json.decoder.JSONDecodeError as err:
            raise WNTREPANETParserException(f"Invalid JSON document: {str(err)}") from None

        # Containers for storing WNTR Type objects that pass validation
        self.network_info: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
        self.curves: List[Any] = []
        self.patterns: List[Any] = []
        self.nodes: List[Any] = []
        self.links: List[Any] = []
        self.sources: List[Any] = []
        self.controls: List[Any] = []


    @staticmethod
    def enforce_unique(ordered_pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """Enforce unique keys in JSON by flagging duplicates.
        
        This method is used as an object_pairs_hook during JSON parsing to detect
        and handle duplicate keys. Duplicate keys are renamed with a special marker
        to prevent silent data loss.
        
        Args:
            ordered_pairs: List of (key, value) tuples from JSON parsing.
        
        Returns:
            Dictionary with unique keys, duplicates flagged with special prefix.
        """
        d: Dict[str, Any] = {}
        sep = ':'
        idx = 1
        for k, v in ordered_pairs:
            if k in d:
                key = DUP_KEY_FLAG.format(idx=idx) + sep + k
                d[key] = v
                idx += 1
            else:
                d[k] = v
        return d

    def set_parser_ruleset(self, ruleset: str) -> None:
        """Apply a specific ruleset to the parser.
        
        Dynamically loads and applies the specified ruleset, updating the
        component type classes to use ruleset-specific implementations.
        
        Args:
            ruleset: The key identifier of the ruleset to apply.
        
        Raises:
            WNTREPANETParserException: If the specified ruleset key is not found.
        """
        rulesets = rules.get_rulesets()
        if ruleset not in rulesets:
            raise WNTREPANETParserException(f"No ruleset with key: {ruleset}")

        import importlib
        import epanetparser.epanet_types
        rules.set_active_ruleset(ruleset)
        importlib.reload(epanetparser.epanet_types)
        from epanetparser.epanet_types import (
            WNTREPANETNetworkInfo,
            WNTREPANETOptions,
            WNTREPANETCurve,
            WNTREPANETPattern,
            WNTREPANETNode,
            WNTREPANETLink,
            WNTREPANETSource,
            WNTREPANETControl,
        )
        globals()["WNTREPANETNetworkInfo"] = WNTREPANETNetworkInfo
        globals()["WNTREPANETOptions"] = WNTREPANETOptions
        globals()["WNTREPANETCurve"] = WNTREPANETCurve
        globals()["WNTREPANETPattern"] = WNTREPANETPattern
        globals()["WNTREPANETNode"] = WNTREPANETNode
        globals()["WNTREPANETLink"] = WNTREPANETLink
        globals()["WNTREPANETSource"] = WNTREPANETSource
        globals()["WNTREPANETControl"] = WNTREPANETControl


    def parse(
        self,
        raise_on_error: bool = False,
        raise_on_warning: bool = False,
        ignore_warnings: bool = False
    ) -> None:
        """Parse the WNTR JSON network definition.
        
        Parses all components of the EPANET network model and validates them
        against the active ruleset. Errors and warnings are collected in the
        parser's errors and warnings attributes.
        
        The parsing process handles the following components in order:
        1. Network metadata (name, version, comments)
        2. Simulation options
        3. Curves
        4. Patterns
        5. Nodes (junctions, tanks, reservoirs)
        6. Links (pipes, pumps, valves)
        7. Sources
        8. Controls
        
        Args:
            raise_on_error: If True, raise validation errors immediately as exceptions
                          rather than collecting them.
            raise_on_warning: If True, raise warnings immediately as exceptions
                            rather than collecting them.
            ignore_warnings: If True, suppress all warning processing.
        """
        seen_nodes: set = set()
        seen_links: set = set()

        # Create partial function with fixed arguments for the context manager
        component_exc_capture = partial(
            raiseorpush,
            raise_error=raise_on_error,
            raise_warning=raise_on_warning,
            ignore_warnings=ignore_warnings,
            dest=self
        )

        # 1. Parse network information (metadata)
        network_dict = {
            key: value for key, value in self.src.items()
            if key in ("version", "comment", "name")
        }
        with component_exc_capture("network_info") as cc:
            network_info = WNTREPANETNetworkInfo(network_dict)
            cc.capture_warnings(network_info)
            self.network_info = network_info

        # 2. Parse network options
        options_dict = self.src["options"]
        with component_exc_capture("options") as cc:
            options = WNTREPANETOptions(options_dict)
            cc.capture_warnings(options)
            self.options = options

        # 3. Parse curves data
        for curve_dict in self.src.get("curves", []):
            with component_exc_capture("curves") as cc:
                wntr_curve = WNTREPANETCurve(curve_dict)
                cc.capture_warnings(wntr_curve)
                self.curves.append(wntr_curve)

        # 4. Parse patterns data
        for pattern_dict in self.src.get("patterns", []):
            with component_exc_capture("patterns") as cc:
                wntr_pattern = WNTREPANETPattern(pattern_dict)
                cc.capture_warnings(wntr_pattern)
                self.patterns.append(wntr_pattern)

        # 5. Parse nodes
        for node_dict in self.src["nodes"]:
            with component_exc_capture("nodes") as cc:
                node = WNTREPANETNode(node_dict)
                cc.capture_warnings(node)
                if node.name in seen_nodes:
                    self.errors["network"].append(
                        WNTREPANETNetworkValidationError(f"Duplicate node name <{node.name}>")
                    )
                else:
                    self.nodes.append(node)
                    seen_nodes.add(node.name)

        # 6. Parse links
        for link_dict in self.src["links"]:
            with component_exc_capture("links") as cc:
                link = WNTREPANETLink(link_dict)
                cc.capture_warnings(link)
                if link.name in seen_links:
                    self.errors["network"].append(
                        WNTREPANETNetworkValidationError(f"Duplicate link name <{link.name}>")
                    )
                else:
                    self.links.append(link)
                    seen_links.add(link.name)

        # 7. Parse sources
        for source_dict in self.src.get("sources", []):
            with component_exc_capture("sources") as cc:
                wntr_source = WNTREPANETSource(source_dict)
                cc.capture_warnings(wntr_source)
                self.sources.append(wntr_source)

        # 8. Parse controls
        for control_dict in self.src.get("controls", []):
            with component_exc_capture("controls") as cc:
                wntr_control = WNTREPANETControl(control_dict)
                cc.capture_warnings(wntr_control)
                self.controls.append(wntr_control) 


    @property
    def has_errors(self) -> bool:
        """Check if any validation errors were encountered.

        Returns:
            True if parsing errors are present, False otherwise.
        """
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any validation warnings were generated.

        Returns:
            True if parsing warnings are present, False otherwise.
        """
        return len(self.warnings) > 0
