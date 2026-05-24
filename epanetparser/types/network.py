import io
import logging

from collections import Counter, defaultdict
from functools import partialmethod

from pywrparser.parsers import PywrJSONParser

from pywrparser.types import (
    PywrParameter,
    PywrRecorder
)
from pywrparser.types.exceptions import PywrParserException

from pywrparser.utils import (
    canonical_name,
    parse_reference_key,
)

log = logging.getLogger(__name__)


class PywrNetwork():
    """
    An abstract representation of a Pywr network.
    """

    def __init__(self, parser):
        self.metadata = parser.metadata
        self.timestepper = parser.timestepper
        self.scenarios = parser.scenarios
        self.scenario_combinations = parser.scenario_combinations
        self.tables = parser.tables
        self.nodes = parser.nodes
        self.edges = parser.edges
        self.parameters = parser.parameters
        self.recorders = parser.recorders

    @classmethod
    def from_file(cls, filename, raise_on_parser_error=False,
                  raise_on_parser_warning=False, ignore_warnings=False,
                  allow_duplicate_edges=True, ruleset=None):
        """
        Returns either the valid PywrNetwork contained in the file denoted
        by the `filename` argument, or corresponding errors encountered during
        parsing.

        Args:
            filename (str): The filename of a file containing a JSON definition
                of a Pywr network.
            raise_on_parser_error (bool): Specifies whether parsing errors should
                be raised immediately as exceptions or collected in the `errors` return
                value.
            raise_on_parser_warning (bool): Specifies whether warnings encountered
                during parsing should be raised immediately as exceptions or collected
                in the `warnings` return value.
            allow_duplicate_edges (bool): Specifies whether duplicate edges are
                considered as errors or are permitted in a valid networks.
            ruleset (str): The `key` of a valid ruleset. This ruleset will then be
                applied during parsing.

        Returns:
            network, errors, warnings (:class:`Tuple[PywrNetwork, Dict, Dict]`):
                in which either one of `network` or `errors` is not None. `warnings` may
                be present in either case.

        """
        try:
            if isinstance(filename, io.StringIO):
                json_src = filename.read()
            else:
                with open(filename, 'r') as fp:
                    json_src = fp.read()
        except OSError as err:
            err_txt = f"Unable to read input file: {err}"
            log.error(err_txt)
            exc = PywrParserException(err_txt)
            if raise_on_parser_error:
                raise exc from None
            else:
                return None, {"network": [exc]}, None

        try:
            parser = PywrJSONParser(json_src, ruleset)
        except PywrParserException as exc:
            if raise_on_parser_error:
                raise exc from None
            else:
                return None, {"network": [exc]}, None

        parser.parse(raise_on_error=raise_on_parser_error,
                     raise_on_warning=raise_on_parser_warning,
                     ignore_warnings=ignore_warnings,
                     allow_duplicate_edges=allow_duplicate_edges)
        ret_warnings = parser.warnings if parser.has_warnings else None
        if parser.has_errors:
            return None, parser.errors, ret_warnings

        return cls(parser), None, parser.warnings

    @classmethod
    def from_json(cls, json_src, raise_on_parser_error=False,
                  raise_on_parser_warning=False, ignore_warnings=False,
                  allow_duplicate_edges=True, ruleset=None):
        """
        Returns either the valid PywrNetwork represented by the JSON encoded string
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
            allow_duplicate_edges (bool): Specifies whether duplicate edges are
                considered as errors or are permitted in a valid networks.
            ruleset (str): The `key` of a valid ruleset. This ruleset will then be
                applied during parsing.

        Returns:
            network, errors, warnings (:class:`Tuple[PywrNetwork, Dict, Dict]`):
                in which either one of `network` or `errors` is not None. `warnings` may
                be present in either case.

        """
        parser = PywrJSONParser(json_src, ruleset=ruleset)
        parser.parse(raise_on_error=raise_on_parser_error,
                     raise_on_warning=raise_on_parser_warning,
                     ignore_warnings=ignore_warnings,
                     allow_duplicate_edges=allow_duplicate_edges)
        ret_warnings = parser.warnings if parser.has_warnings else None
        if parser.has_errors:
            return None, parser.errors, ret_warnings

        return cls(parser), None, parser.warnings


    def as_dict(self):
        """
        Returns:
            network (dict): A dict representation of the :class:`PywrNetwork`
                instance.
        """
        network = {
            "metadata": self.metadata.as_dict(),
            "timestepper": self.timestepper.as_dict(),
            "nodes": [node.as_dict() for node in self.nodes.values()],
            "edges": [edge.as_dict() for edge in self.edges]
        }
        if len(self.parameters) > 0:
            network["parameters"] = {n: p.as_dict() for n, p in self.parameters.items()}

        if len(self.recorders) > 0:
            network["recorders"] = {n: r.as_dict() for n, r in self.recorders.items()}

        if len(self.scenarios) > 0:
            network["scenarios"] = [s.as_dict() for s in self.scenarios]

        if len(self.scenario_combinations) > 0:
            network["scenario_combinations"] = [s.as_dict() for s in self.scenario_combinations]

        if len(self.tables) > 0:
            network["tables"] = {n: t.as_dict() for n, t in self.tables.items()}

        return network


    def as_json(self):
        """
        Returns:
            network (str): A JSON encoded representation of the :class:`PywrNetwork`
                instance.
        """
        import json
        return json.dumps(self.as_dict(), indent=2)


    def validate(self):
        """
          Currently unused.
          Additional network-level semantic validation, e.g..
           - Unconnected nodes
           - Unused parameters
        """
        pass


    def promote_inline_parameters(self):
        """
          Promotes inline parameter definitions to instances of
          :class:`PywrParameter`.

          Any values of attrs in a node which can be interpreted as
          an inline (i.e. dict) parameter definition are instantiated
          as parameters and the attr value replaced with the instance.
        """
        exclude = ("name", "type")
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if isinstance(value, dict):
                    type_key = value.get("type")
                    if not type_key or "recorder" in type_key.lower():
                        continue
                    param_name = value.get("name")
                    if not param_name or param_name in self.parameters:
                        param_name = canonical_name(node.name, attr)
                    log.debug(f"Creating inline param: {param_name}")
                    if param_name in self.parameters:
                        # Node inline param has same name as global param
                        raise ValueError("inline dups global param")
                    param = PywrParameter(param_name, value)
                    node.data[attr] = param

    def promote_inline_recorders(self):
        """
          Promotes inline recorder definitions to instances of
          :class:`PywrRecorder`.

          Any values of attrs in a node which can be interpreted as
          an inline (i.e. dict) recorder definition are instantiated
          as recorders and the attr value replaced with the instance.
        """
        exclude = ("name", "type")
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if isinstance(value, dict):
                    type_key = value.get("type")
                    if not type_key or "parameter" in type_key.lower():
                        continue
                    rec_name = value.get("name")
                    if not rec_name or rec_name in self.recorders:
                        rec_name = canonical_name(node.name, attr)
                    log.debug(f"Creating inline recorder: {rec_name}")
                    if rec_name in self.recorders:
                        # Node inline recorder has same name as global recorder
                        raise ValueError("inline dups global recorder")
                    recorder = PywrRecorder(rec_name, value)
                    node.data[attr] = recorder

    def attach_reference_parameters(self):
        """
          Promotes strings which reference parameters to instances of
          :class:`PywrParameter`.

          Any values of attrs in a node which resolve to a global parameter
          are replaced with the instance of that parameter.
        """
        exclude = ("name", "type")
        attached_parameters = []
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if attr.lower() in exclude:
                    """
                    A param could exist with the same name as a node,
                    leading to node["name"] = param
                    """
                    continue
                if isinstance(value, str):
                    param = self.parameters.get(value)
                    if not param:
                        continue
                    log.debug(f"Attaching global param ref: {value}")
                    node.data[attr] = param
                    attached_parameters.append(value)

        for attached_parameter in attached_parameters:
            self.parameters.pop(attached_parameter, None)

    def attach_reference_recorders(self):
        """
          Promotes strings which reference recorders to instances of
          :class:`PywrRecorder`.

          Any values of attrs in a node which resolve to a global recorder
          are replaced with the instance of that recorder.
        """
        exclude = ("name", "type")
        attached_recorders = []
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if attr.lower() in exclude:
                    """
                    A recorder could exist with the same name as a node,
                    leading to node["name"] = recorder
                    """
                    continue
                if isinstance(value, str):
                    recorder = self.recorders.get(value)
                    if not recorder:
                        continue
                    log.debug(f"Attaching global recorder ref: {value}")
                    node.data[attr] = recorder
                    attached_recorders.append(value)

        for attached_recorder in attached_recorders:
            del(self.recorders[attached_recorder])


    def __add_component_references(self, component=None):
        """
            Where a parameter or recorder name is in the format "__nodename__:attrname"
            it is interpreted as representing the attr "attrname" on node "nodename".
            In this case, a reference to the global parameter or recorder is added to
            the node where this is not already present.

            This method should be invoked only through the partialmethod descriptors
            defined below.
        """

        component_map = {
            "parameter": self.parameters,
            "recorder" : self.recorders
        }

        # Prevent use without partial filled
        if not component:
            return

        # Prevent unorthodox use
        if component not in component_map:
            return

        store = component_map[component]

        for comp_name in store:
            try:
                node_name, attr = parse_reference_key(comp_name)
            except ValueError:
                # comp_name not in std format
                log.debug(f"Not in std format: {comp_name}")
                continue

            if node_name not in self.nodes:
                # node implied by comp_name does not exist
                log.debug(f"No such node: {comp_name} -> {node_name}")
                continue

            node = self.nodes[node_name]

            if attr in node.attrs:
                # node exists but already has implied attr
                log.debug(f"Node {node.name} already has attr: {attr}")
                continue

            # node exists, does not have attr, so create as param_name str
            log.debug(f"add_{component}_references {node.name}:{attr} -> {comp_name}")
            node.data[attr] = comp_name

    add_parameter_references = partialmethod(
            __add_component_references,
            component="parameter"
    )
    """
        Where a parameter name is in the format "__nodename__:attrname"
        it is interpreted as representing the attr "attrname" on node "nodename".
        In this case, a reference to the global parameter is added to
        the node where this is not already present.

        Partial application of the internal :func:`__add_component_references`
        function.
    """

    add_recorder_references = partialmethod(
            __add_component_references,
            component="recorder"
    )
    """
        Where a recorder name is in the format "__nodename__:attrname"
        it is interpreted as representing the attr "attrname" on node "nodename".
        In this case, a reference to the global recorder is added to
        the node where this is not already present.

        Partial application of the internal :func:`__add_component_references`
        function.
    """

    def detach_parameters(self):
        """
        Removes any parameter instances from nodes and replaces these by
        a string referencing the name of the parameter.
        """
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if isinstance(value, PywrParameter):
                    if value.name in self.parameters:
                        if value is not self.parameters[value.name]:
                            # Attr param name duplicates global param name
                            raise ValueError("Attr param name duplicates global param name")
                    else:
                        self.parameters[value.name] = value
                        node.data[attr] = value.name


    def detach_recorders(self):
        """
        Removes any recorder instances from nodes and replaces these by
        a string referencing the name of the recorder.
        """
        for node in self.nodes.values():
            for attr, value in node.data.items():
                if isinstance(value, PywrRecorder):
                    if value.name in self.recorders:
                        # Attr recorder name duplicates global recorder name
                        raise ValueError("Attr recorder name duplicates global recorder name")
                    self.recorders[value.name] = value
                    node.data[attr] = value.name


    def report(self):
        """
        Returns:
            report (dict): Contains a key for each network component whose
              associated value is the number of instances of that component
              type.
        """
        report = {
            "nodes": len(self.nodes),
            "edges": len(self.edges)
        }

        components = ("parameters", "recorders", "tables", "scenarios")

        for component in components:
            store = getattr(self, component)
            if (count := len(store)) > 0:
                report[component] = count

        return report


    def verbose_report(self,):
        report = self.report()

        rep_lines = {"Title": self.title}
        if self.description:
            rep_lines["Description"] = self.description
        for component, count in report.items():
            rep_lines[component.capitalize()] = count

        return rep_lines


    @property
    def title(self):
        return self.metadata.data["title"]


    @property
    def description(self):
        return self.metadata.data.get("description")


    @property
    def duplicate_edges(self):
        """
            Return a dict of "duplicate" edges, that is edges of length `n`
            comprised of the same `n` nodes in the same order which are
            defined more than once.
            This is permitted by Pywr but may indicate a malformed network
            in some enviroments.
        """
        edge_count = Counter((n1, n2) for (n1, n2) in self.edges)
        return {edge: count for edge, count in edge_count.items() if count > 1}


    def url_references(self):
        """
            Return a dict of urls references by parameters, each mapping to
            a list of the parameters containing that reference.
        """
        url_map = defaultdict(list)
        for p in (param for param in self.parameters.values() if "url" in param.data):
            url_map[p.data["url"]].append(p)

        for t in (table for table in self.tables.values() if "url" in table.data):
            url_map[t.data["url"]].append(t)

        for r in (recorder for recorder in self.recorders.values() if "url" in recorder.data):
            url_map[r.data["url"]].append(r)

        return url_map
