"""EPANET network representation and statistics.

This module provides classes for representing and analyzing EPANET water
distribution networks using the WNTR (Water Network Tool for Resilience) parser.

Classes
-------
WNTRNetworkStatistics
    Computes detailed statistics about network components.
WNTREPANETNetwork
    Main network representation with nodes, links, and other components.

Examples
--------
Load a network from an .inp file::

    network, errors, warnings = WNTREPANETNetwork.from_file("network.inp")
    if network:
        print(network.report())

Load from JSON::

    network, errors, warnings = WNTREPANETNetwork.from_json(json_string)
"""
from __future__ import annotations
import pathlib
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import logging
import json
import wntr
from epanetparser.core.parsers.wntrjsonparser import WNTRJSONParser
from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException       

log = logging.getLogger(__name__)


class WNTRNetworkStatistics:
    """Compute ds.
    
    This class provides methods to analyze network components by type,
    generating detailed counts and breakdowns of nodes, links, curves,
    patterns, sources, and controls.
    
    Parameters
    ----------
    network : WNTREPANETNetwork
        The network instance to analyze.
    
    Attributes
    ----------
    component_typefield_map : Dict[str, str|None]
        Maps component names to their type field names.
    network : WNTREPANETNetwork
        The network being analyzed.
    
    Examples
    --------
    >>> stats = WNTRNetworkStatistics(network)
    >>> report = stats.report()
    >>> print(report['nodes'])
    10
    """
    component_typefield_map: Dict[str, str|None] = {
        "nodes": "node_type",
        "links": "link_type",
        "sources" : None,
        "curves" : "curve_type",
        "patterns": None,
        "controls": "type"}

    def __init__(self, network: WNTREPANETNetwork):
        """Initialize statistics analyzer.
        
        Parameters
        ----------
        network : WNTREPANETNetwork
            The network to analyze.
        """
        self.network = network

    def get_component_types(self, component_name: str) -> List[str]:
        """Get unique component types for a given component category.
        
        Parameters
        ----------
        component_name : str
            Name of component category (e.g., 'nodes', 'links').
        
        Returns
        -------
        List[str]
            List of unique component types found.
        
        Examples
        --------
        >>> stats.get_component_types('nodes')
        ['Junction', 'Reservoir', 'Tank']
        """
        component_types: List[str] = []
        type_field: str | None = self.component_typefield_map[component_name]
        store = getattr(self.network, component_name)
        if type_field is None:
            return []
        for component in store:
            if component[type_field] not in component_types:
                component_types.append(component[type_field])
        return component_types

    def get_number_of_components(self, component_name: str, component_type: str|None = None) -> int:
        """Count components, optionally filtered by type.
        
        Parameters
        ----------
        component_name : str
            Name of component category (e.g., 'nodes', 'links').
        component_type : str, optional
            Specific type to filter by (e.g., 'Pipe', 'Junction').
        
        Returns
        -------
        int
            Number of matching components.
        
        Examples
        --------
        >>> stats.get_number_of_components('nodes')
        10
        >>> stats.get_number_of_components('nodes', 'Junction')
        7
        """
        # BUG FIX: Changed from self to self.network
        store = getattr(self.network, component_name)
        if component_type is not None:
            count = len(
                [item for item in store if 
                 item[self.component_typefield_map[component_name]] == component_type])
        else:
            count = len(store)
        return count

    def report(self) -> Dict[str, int]:
        """Generate detailed component statistics report.
        
        Returns
        -------
        Dict[str, int]
            Dictionary with component counts, including breakdowns by type.
            Keys include base component names (e.g., 'nodes') and typed
            components (e.g., 'nodes type Junction').
        
        Examples
        --------
        >>> report = stats.report()
        >>> print(report)
        {'nodes': 10, 'nodes type Junction': 7, 'nodes type Tank': 2, ...}
        """
        report: Dict[str, int] = {}
        components = self.component_typefield_map.keys()
        for component in components:
            component_types = self.get_component_types(component)
            if (count := self.get_number_of_components(component)) > 0:
                report[component] = count
            if len(component_types) > 0:
                for component_type in component_types:
                    key_name = component + " type " + component_type
                    report[key_name] = self.get_number_of_components(component, component_type)
        return report


class WNTREPANETNetwork:
    """EPANET water distribution network representation.
    
    An abstract representation of an EPANET network pre-parsed by the 
    USEPA WNTR (Water Network Tool for Resilience) package.
    
    This class provides methods to load, validate, and analyze EPANET
    networks from .inp or .json files.
    
    Parameters
    ----------
    parser : WNTRJSONParser
        A parser instance containing the parsed network data.
    
    Attributes
    ----------
    network_info : NetworkInfo
        Basic network metadata (name, comment, version).
    options : Options
        Network simulation options and settings.
    curves : List
        Performance curves (pump curves, efficiency curves, etc.).
    patterns : List
        Time-based demand/source patterns.
    nodes : List
        Network nodes (junctions, tanks, reservoirs).
    links : List
        Network links (pipes, pumps, valves).
    sources : List
        Water quality sources.
    controls : List
        Simple and rule-based controls.
    
    Examples
    --------
    Load from a file::
    
        network, errors, warnings = WNTREPANETNetwork.from_file("Net1.inp")
        if network:
            print(f"Network: {network.name}")
            print(network.report())
    
    Access network components::
    
        for node in network.nodes:
            print(node.name, node.node_type)
    
    See Also
    --------
    WNTRJSONParser : Parser for WNTR JSON format
    WNTRNetworkStatistics : Detailed network statistics
    
    References
    ----------
    .. [1] https://github.com/USEPA/WNTR
    """

    def __init__(self, parser: WNTRJSONParser):
        """Initialize network from parser.
        
        Parameters
        ----------
        parser : WNTRJSONParser
            Parser containing the network data.
        """
        self.network_info = parser.network_info
        self.options = parser.options
        self.curves = parser.curves
        self.patterns = parser.patterns
        self.nodes = parser.nodes
        self.links = parser.links
        self.sources = parser.sources
        self.controls = parser.controls

    @classmethod
    def from_file(
            cls,
            filename: str | pathlib.Path,
            raise_on_parser_error=False,
            raise_on_parser_warning=False,
            ignore_warnings=False,
            ruleset=None) -> Tuple[WNTREPANETNetwork, None, defaultdict]:
        """Load network from .inp or .json file.
        
        Reads an EPANET network from a file. Supports both .inp (EPANET input)
        and .json (WNTR JSON) formats. The .inp files are automatically converted
        to JSON using WNTR before parsing.
        
        Parameters
        ----------
        filename : str or pathlib.Path
            Path to the network file (.inp or .json).
        raise_on_parser_error : bool, default=False
            If True, raise exceptions on parsing errors. If False, return
            errors in the errors dictionary.
        raise_on_parser_warning : bool, default=False
            If True, raise exceptions on warnings. If False, collect warnings
            in the warnings dictionary.
        ignore_warnings : bool, default=False
            If True, skip warning checks entirely.
        ruleset : str, optional
            Key of a validation ruleset to apply during parsing.
        
        Returns
        -------
        network : WNTREPANETNetwork or None
            The parsed network, or None if errors occurred.
        errors : dict or None
            Dictionary of parsing errors, or None if no errors.
        warnings : defaultdict or None
            Dictionary of warnings, or None if no warnings.
        
        Raises
        ------
        WNTREPANETParserException
            If raise_on_parser_error=True and parsing fails.
        
        Examples
        --------
        Load a network with error handling::
        
            network, errors, warnings = WNTREPANETNetwork.from_file(
                "network.inp",
                raise_on_parser_error=False
            )
            
            if errors:
                print("Errors:", errors)
            elif network:
                print(f"Loaded: {network.name}")
                if warnings:
                    print("Warnings:", warnings)
        
        Load with strict validation::
        
            try:
                network, _, _ = WNTREPANETNetwork.from_file(
                    "network.inp",
                    raise_on_parser_error=True,
                    raise_on_parser_warning=True
                )
            except WNTREPANETParserException as e:
                print(f"Validation failed: {e}")
        """
        filename = pathlib.Path(filename)
        file_extension = filename.suffix
        try:
            if file_extension.lower() == ".inp":
                # Convert the inp file to its json representation using WNTR
                network = wntr.network.WaterNetworkModel(filename.as_posix())
                json_src = json.dumps(wntr.network.to_dict(network))
            else:
                with open(filename, 'r', encoding='utf-8') as fp:
                    json_src = fp.read()
        except (FileNotFoundError, OSError) as err:
            err_txt = f"Unable to read input file: {err}"
            #log.error(err_txt)
            exc = WNTREPANETParserException(err_txt)
            if raise_on_parser_error:
                raise exc from None
            return None, {"network": [exc]}, None
        try:
            parser = WNTRJSONParser(json_src, ruleset)
        except WNTREPANETParserException as exc:
            if raise_on_parser_error:
                raise exc from None
            return None, {"network": [exc]}, None

        parser.parse(raise_on_error=raise_on_parser_error,
                     raise_on_warning=raise_on_parser_warning,
                     ignore_warnings=ignore_warnings)
        ret_warnings = parser.warnings if parser.has_warnings else None
        if parser.has_errors:
            return None, parser.errors, ret_warnings
            return cls(parser), None, parser.warnings

    @classmethod
    def from_json(cls, json_src, raise_on_parser_error=False,
                  raise_on_parser_warning=False, ignore_warnings=False,
                  ruleset=None) -> Tuple[WNTREPANETNetwork, None, defaultdict]:
        """Load network from JSON string.
        
        Parse an EPANET network from a JSON-encoded string in WNTR format.
        
        Parameters
        ----------
        json_src : str
            JSON-encoded string representing the network.
        raise_on_parser_error : bool, default=False
            If True, raise exceptions on parsing errors.
        raise_on_parser_warning : bool, default=False
            If True, raise exceptions on warnings.
        ignore_warnings : bool, default=False
            If True, skip warning checks.
        ruleset : str, optional
            Key of a validation ruleset to apply.
        
        Returns
        -------
        network : WNTREPANETNetwork or None
            The parsed network, or None if errors occurred.
        errors : dict or None
            Dictionary of parsing errors, or None if no errors.
        warnings : defaultdict or None
            Dictionary of warnings, or None if no warnings.
        
        Examples
        --------
        >>> import json
        >>> json_str = json.dumps(network_dict)
        >>> network, errors, warnings = WNTREPANETNetwork.from_json(json_str)
        """
        parser = WNTRJSONParser(json_src, ruleset=ruleset)
        parser.parse(raise_on_error=raise_on_parser_error,
                     raise_on_warning=raise_on_parser_warning,
                     ignore_warnings=ignore_warnings)
        ret_warnings = parser.warnings if parser.has_warnings else None
        if parser.has_errors:
            return None, parser.errors, ret_warnings
        return cls(parser), None, parser.warnings


    def as_dict(self) -> Dict[str, Any]:
        """Convert network to dictionary representation.
        
        Returns
        -------
        dict
            Dictionary containing all network components and metadata.
            Includes network_info, options, curves, patterns, nodes,
            links, sources, and controls.
        
        Examples
        --------
        >>> network_dict = network.as_dict()
        >>> print(network_dict.keys())
        dict_keys(['name', 'options', 'nodes', 'links', ...])
        """
        network = self.network_info.as_dict()
        network["options"] = self.options.as_dict()
        if len(self.curves) > 0:
            network["curves"] = [curve.as_dict() for curve in self.curves]
        network["patterns"] = [pattern.as_dict() for pattern in self.patterns]
        network["nodes"] = [node.as_dict() for node in self.nodes]
        network["links"] = [link.as_dict() for link in self.links]
        network["sources"] = [source.as_dict() for source in self.sources]
        network["controls"] = [control.as_dict() for control in self.controls]
        return network


    def as_json(self) -> str:
        """Return a JSON encoded representation of the WNTREPANETNetwork.
        
        Returns:
            str: A JSON encoded representation of the :class:`WNTREPANETNetwork`
                instance with 2-space indentation.
        """
        return json.dumps(self.as_dict(), indent=2)


    def validate(self) -> None | NotImplemented:
        """Perform network-level semantic validation.
        
        Currently unused placeholder for future validation features.
        Potential validations include:
        - Unconnected nodes
        - Unused parameters
        - Network topology checks
        
        Returns
        -------
        None or NotImplemented
            Currently returns NotImplemented.
        """
        return NotImplemented


    def report(self) -> Dict[str, int]:
        """Generate summary report of network components.
        
        Provides basic counts of major network components.
        
        Returns
        -------
        dict
            Dictionary with component counts. Keys include 'nodes', 'links',
            and optionally 'curves', 'patterns', 'sources', 'controls'
            (only if count > 0).
        
        Examples
        --------
        >>> report = network.report()
        >>> print(f"Nodes: {report['nodes']}, Links: {report['links']}")
        Nodes: 11, Links: 13
        
        See Also
        --------
        verbose_report : More detailed report with formatted output
        """
        report = {
            "nodes": len(self.nodes),
            "links": len(self.links)
        }
        components = ("curves", "patterns", "sources", "controls")
        for component in components:
            store = getattr(self, component)
            if (count := len(store)) > 0:
                report[component] = count
        return report


    def verbose_report(self) -> Dict[str, int]:
        """Generate verbose report with capitalized component names.
        
        Returns
        -------
        dict
            Dictionary with component counts, keys capitalized.
        
        Examples
        --------
        >>> report = network.verbose_report()
        >>> print(report)
        {'Nodes': 11, 'Links': 13, 'Patterns': 2}
        """
        report = self.report()
        rep_lines = {}
        for component, count in report.items():
            rep_lines[component.capitalize()] = count
        return rep_lines


    @property
    def name(self) -> str:
        """Network name.
        
        Returns
        -------
        str
            The network name from network_info.
        """
        if hasattr(self.network_info, 'name'):
            return self.network_info.name
        return self.network_info.get('name', 'Unnamed Network')


    @property
    def comment(self) -> str:
        """Network description/comment.
        
        Returns
        -------
        str
            The network comment from network_info.
        """
        if hasattr(self.network_info, 'comment'):
            return self.network_info.comment
        return self.network_info.get('comment', '')
    

    @property
    def version(self) -> str:
        """Network version.
        
        Returns
        -------
        str
            The network version from network_info.
        """
        if hasattr(self.network_info, 'version'):
            return self.network_info.version
        return self.network_info.get('version', '')
    
    
if __name__ == "__main__":
    # Demonstration and testing of network loading functionality.
    #
    # This demo shows how to:
    # - Load networks from different file formats (.inp and .json)
    # - Handle parsing errors and warnings
    # - Display network statistics
    # - Access network components
    #
    # Usage:
    #   Run with default example networks:
    #     python network.py
    #
    #   Test a specific network file:
    #     python network.py /path/to/your/network.inp
    #
    #   Test multiple files:
    #     python network.py network1.inp network2.json network3.inp
    
    import sys
    import os
    
    def print_separator(char='=', length=70):
        """Print a visual separator line."""
        print(char * length)
    
    def print_network_info(network: WNTREPANETNetwork):
        """Display detailed information about a network.
        
        Parameters
        ----------
        network : WNTREPANETNetwork
            The network to display.
        """
        print_separator()
        print(f"NETWORK: {network.name}")
        print_separator()
        print(f"Version: {network.version}")
        if network.comment:
            print(f"Comment: {network.comment}")
        print()
        
        # Basic report
        print("BASIC REPORT:")
        print("-" * 40)
        report = network.report()
        for component, count in sorted(report.items()):
            print(f"  {component.ljust(20)}: {count}")
        print()
        
        # Verbose report
        print("VERBOSE REPORT:")
        print("-" * 40)
        verbose = network.verbose_report()
        for component, count in sorted(verbose.items()):
            print(f"  {component.ljust(20)}: {count}")
        print()
        
        # Component details
        if network.nodes:
            print(f"SAMPLE NODES (showing first 3 of {len(network.nodes)}):")
            print("-" * 40)
            for i, node in enumerate(network.nodes[:3]):
                node_dict = node.as_dict() if hasattr(node, 'as_dict') else node
                node_name = node_dict.get('name', f'Node_{i}')
                node_type = node_dict.get('node_type', 'Unknown')
                print(f"  {node_name} ({node_type})")
        print()
        
        if network.links:
            print(f"SAMPLE LINKS (showing first 3 of {len(network.links)}):")
            print("-" * 40)
            for i, link in enumerate(network.links[:3]):
                link_dict = link.as_dict() if hasattr(link, 'as_dict') else link
                link_name = link_dict.get('name', f'Link_{i}')
                link_type = link_dict.get('link_type', 'Unknown')
                print(f"  {link_name} ({link_type})")
        print()
    
    def test_network_file(filepath: str):
        """Test loading a network file and display results.
        
        Parameters
        ----------
        filepath : str
            Path to the network file.
        """
        print_separator('=')
        print(f"TESTING: {filepath}")
        print_separator('=')
        if not os.path.exists(filepath):
            print(f"❌ ERROR: File not found: {filepath}")
            print()
            return
        print(f"📂 Loading network from: {filepath}")
        print(f"   File size: {os.path.getsize(filepath)} bytes")
        print()
        try:
            network, errors, warnings = WNTREPANETNetwork.from_file(
                filepath,
                raise_on_parser_error=False,
                raise_on_parser_warning=False,
                ignore_warnings=False
            )
            
            if errors:
                print("❌ PARSING ERRORS:")
                print("-" * 40)
                for error_type, error_list in errors.items():
                    print(f"  {error_type}:")
                    for error in error_list:
                        print(f"    - {error}")
                print()
                return
            
            if warnings:
                print("⚠️  WARNINGS:")
                print("-" * 40)
                for warn_type, warn_list in warnings.items():
                    print(f"  {warn_type}:")
                    for warning in warn_list[:5]:  # Show first 5 warnings
                        print(f"    - {warning}")
                    if len(warn_list) > 5:
                        print(f"    ... and {len(warn_list) - 5} more")
                print()
            
            if network:
                print("✅ Network loaded successfully!")
                print()
                print_network_info(network)
                
                # Test JSON export
                print("JSON EXPORT TEST:")
                print("-" * 40)
                try:
                    json_str = network.as_json()
                    print(f"  JSON length: {len(json_str)} characters")
                    print(f"  JSON preview: {json_str[:100]}...")
                    print("  ✅ JSON export successful")
                except Exception as e:
                    print(f"  ❌ JSON export failed: {e}")
                print()
        
        except Exception as e:
            print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Main demo execution
    print_separator('=')
    print("EPANET NETWORK LOADER - DEMONSTRATION")
    print_separator('=')
    print()
    
    # Determine which files to test
    if len(sys.argv) > 1:
        # User provided file paths
        test_files = sys.argv[1:]
        print(f"Testing {len(test_files)} user-specified file(s):")
        for f in test_files:
            print(f"  - {f}")
        print()
    else:
        # Use example networks from the package
        print("No files specified. Using built-in example networks.")
        print("Usage: python network.py <path_to_network1> <path_to_network2> ...")
        print()
        
        # Get the package directory
        package_dir = pathlib.Path(__file__).parent.parent
        networks_dir = package_dir / "networks"
        
        test_files = []
        
        # Try to find example networks
        if (networks_dir / "test").exists():
            test_valid = networks_dir / "test" / "test_valid_network.inp"
            if test_valid.exists():
                test_files.append(str(test_valid))
        
        if (networks_dir / "core").exists():
            for net_file in ["Net1.inp", "Net2.inp", "Net3.inp"]:
                net_path = networks_dir / "core" / net_file
                if net_path.exists():
                    test_files.append(str(net_path))
                    break  # Just use one core network for demo
        
        if not test_files:
            print("⚠️  No example networks found in package.")
            print("Please specify a network file path as an argument.")
            print()
            print("Example:")
            print("  python network.py /path/to/network.inp")
            sys.exit(0)
        
        print(f"Found {len(test_files)} example network(s):")
        for f in test_files:
            print(f"  - {f}")
        print()
    
    # Test each file
    for i, filepath in enumerate(test_files):
        test_network_file(filepath)
        
        if i < len(test_files) - 1:
            print()
            print()
    
    print_separator('=')
    print("DEMO COMPLETE")
    print_separator('=')

