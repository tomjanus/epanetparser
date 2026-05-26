""" """
from __future__ import annotations
import pathlib
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import logging
import json
import wntr
from epanetparser.parsers.wntrjsonparser import WNTRJSONParser
from epanetparser.epanet_types.exceptions import WNTREPANETParserException


log = logging.getLogger(__name__)


class WNTRNetworkStatistics:
    """ """
    component_typefield_map: Dict[str, str|None] = {
        "nodes": "node_type",
        "links": "link_type",
        "sources" : None,
        "curves" : "curve_type",
        "patterns": None,
        "controls": "type"}

    def __init__(self, network: WNTREPANETNetwork):
        self.network = network

    def get_component_types(self, component_name: str) -> List[str]:
        """ """
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
        store = getattr(self, component_name)
        if component_type is not None:
            count = len(
                [item for item in store if 
                 item[self.component_typefield_map[component_name]] == component_type])
        else:
            count = len(store)
        return count

    def report(self) -> Dict[str, int]:
        """
        Returns:
            report (dict): Contains a key for each network component whose
              associated value is the number of instances of that component
              type.
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
    """
    An abstract representation of a EPANET network preparsed by USEPA WNTR Package
    https://github.com/USEPA/WNTR
    .
    """

    def __init__(self, parser: WNTRJSONParser):
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
        """
        Returns either the valid WNTR EPANET network contained in the JSON txt file denoted
        by the `filename` argument, or corresponding errors encountered during
        parsing.

        Args:
            filename (str | pathlib.Path): The filename of a file containing a JSON definition
                of a EPANET network.
            raise_on_parser_error (bool): Specifies whether parsing errors should
                be raised immediately as exceptions or collected in the `errors` return
                value.
            raise_on_parser_warning (bool): Specifies whether warnings encountered
                during parsing should be raised immediately as exceptions or collected
                in the `warnings` return value.
            ruleset (str): The `key` of a valid ruleset. This ruleset will then be
                applied during parsing.

        Returns:
            network, errors, warnings (:class:`Tuple[WNTREPANETNetwork, Dict, Dict]`):
                in which either one of `network` or `errors` is not None. `warnings` may
                be present in either case.

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
        """
        Returns either the valid WNTR EPANET represented by the JSON encoded string
        contained in the `json_src` argument, or corresponding errors encountered
        during parsing.

        Args:
            json_src (str): A string containing a JSON encoded representation of
                a Pywr network.
            raise_on_parser_error (bool): Specifies whether parsing errors should
                be raised immediately as exceptions or collected in the `errors` return
                value.
            raise_on_parser_warning (bool): Specifies whether warnings encountered
                during parsing should be raised immediately as exceptions or collected
                in the `warnings` return value.
            ruleset (str): The `key` of a valid ruleset. This ruleset will then be
                applied during parsing.

        Returns:
            network, errors, warnings (:class:`Tuple[WNTRNetwork, Dict, Dict]`):
                in which either one of `network` or `errors` is not None. `warnings` may
                be present in either case.

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
        """
        Returns:
            network (dict): A dict representation of the :class:`WNTREPANETNetwork`
                instance.
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
        """
          Currently unused.
          Additional network-level semantic validation, e.g..
           - Unconnected nodes
           - Unused parameters
        """
        return NotImplemented


    def report(self) -> Dict[str, int]:
        """Generate a summary report of network components.
        
        Returns:
            dict: Contains a key for each network component whose
                associated value is the number of instances of that component
                type.
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
        report = self.report()
        rep_lines = {}
        for component, count in report.items():
            rep_lines[component.capitalize()] = count
        return rep_lines


    @property
    def name(self) -> str:
        return self.network_info.name


    @property
    def comment(self) -> str:
        return self.network_info.comment
    

    @property
    def version(self) -> str:
        return self.network_info.version
