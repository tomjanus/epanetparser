import json
import re
from collections import (
    defaultdict,
    Counter
)
from functools import partial

from pywrparser import rules
from pywrparser.types import (
    PywrTimestepper,
    PywrMetadata,
    PywrScenario,
    PywrScenarioCombination,
    PywrTable,
    PywrNode,
    PywrEdge,
    PywrParameter,
    PywrRecorder,
)
from pywrparser.types.exceptions import (
    PywrParserException,
    PywrNetworkValidationError
)
from pywrparser.utils import raiseorpush

DUP_KEY_BASE = "__PywrParser_Duplicate_Key_{pattern}__"
DUP_KEY_FLAG = DUP_KEY_BASE.format(pattern="{idx:03d}")
DUP_KEY_RE   = r"{base}".format(base=DUP_KEY_BASE.format(pattern="[0-9]{3}"))


class PywrJSONParser():
    def __init__(self, json_src, ruleset=None):
        """
        Creates an instance of a parser in which the specified `json_src` is
        validated against the specified `ruleset`.

        Args:
            json_src (str): A JSON encoded representation of a Pywr network
            ruleset (str): The key of a ruleset whose rules are to be applied
        """
        self.errors = defaultdict(list)
        self.warnings = defaultdict(list)

        if ruleset:
            self.set_parser_ruleset(ruleset)

        try:
            self.src = json.loads(json_src, object_pairs_hook=self.__class__.enforce_unique)
        except json.decoder.JSONDecodeError as err:
            raise PywrParserException(f"Invalid JSON document: {str(err)}")

        self.nodes = {}
        self.edges = []
        self.parameters = {}
        self.recorders = {}
        self.scenarios = []
        self.scenario_combinations = []
        self.tables = {}


    @staticmethod
    def enforce_unique(ordered_pairs):
        d = {}
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

    def set_parser_ruleset(self, ruleset):
        """
        Applies the specified `ruleset` to the parser.

        Args:
            ruleset (str): The key of a ruleset whose rules are to be applied
        """
        rulesets = rules.get_rulesets()
        if ruleset not in rulesets:
            raise PywrParserException(f"No ruleset with key: {ruleset}")

        import importlib
        import pywrparser.types
        rules.set_active_ruleset(ruleset)
        importlib.reload(pywrparser.types)
        from pywrparser.types import (
            PywrTimestepper,
            PywrMetadata,
            PywrScenario,
            PywrTable,
            PywrNode,
            PywrEdge,
            PywrParameter,
            PywrRecorder,
        )
        globals()["PywrTimestepper"] = PywrTimestepper
        globals()["PywrMetadata"] = PywrMetadata
        globals()["PywrScenario"] = PywrScenario
        globals()["PywrTable"] = PywrTable
        globals()["PywrNode"] = PywrNode
        globals()["PywrEdge"] = PywrEdge
        globals()["PywrParameter"] = PywrParameter
        globals()["PywrRecorder"] = PywrRecorder



    def parse(self, raise_on_error=False, raise_on_warning=False,
              ignore_warnings=False, allow_duplicate_edges=True):
        """
        Parse the Pywr model definition that was passed to the parser on instantiation.
        Following this action, the :py:attr:`parser.errors` and :py:attr:`parser.warnings`
        attributes are defined.

        Args:
            raise_on_parser_error (bool): Specifies whether parsing errors should
                be raised immediately as exceptions or collected in the `errors` return
                value.
            raise_on_parser_warning (bool): Specifies whether warnings encountered
                during parsing should be raised immediately as exceptions or collected
                in the `warnings` return value.
            allow_duplicate_edges (bool): Specifies whether duplicate edges are
                considered as errors or are permitted in a valid networks.
        """
        seen_nodes = set()

        """
        Only component varies between invocations, create partial
        for fixed arguments to context manager.
        """
        component_exc_capture = partial(raiseorpush,
                                  raise_error=raise_on_error,
                                  raise_warning=raise_on_warning,
                                  ignore_warnings=ignore_warnings,
                                  dest=self)

        with component_exc_capture("metadata") as cc:
            self.metadata = PywrMetadata(self.src["metadata"])
            cc.capture_warnings(self.metadata)

        with component_exc_capture("timestepper") as cc:
            self.timestepper = PywrTimestepper(self.src["timestepper"])
            cc.capture_warnings(self.timestepper)

        for scenario in self.src.get("scenarios", []):
            with component_exc_capture("scenarios") as cc:
                scen = PywrScenario(scenario)
                cc.capture_warnings(scen)
                self.scenarios.append(scen)

        for combination in self.src.get("scenario_combinations", []):
            with component_exc_capture("scenario_combinations") as cc:
                comb = PywrScenarioCombination(combination)
                cc.capture_warnings(comb)
                self.scenario_combinations.append(comb)

        for table_name, table_data in self.src.get("tables", {}).items():
            with component_exc_capture("tables") as cc:
                t = PywrTable(table_name, table_data)
                cc.capture_warnings(t)
                self.tables[t.name] = t

        for param_name, param_data in self.src.get("parameters", {}).items():
            if m := re.search(DUP_KEY_RE, param_name):
                span_end = m.span()[1]
                raw_name = param_name[span_end+1:]
                self.errors["network"].append(PywrNetworkValidationError(f"Duplicate parameter name <{raw_name}>"))
            with component_exc_capture("parameters") as cc:
                p = PywrParameter(param_name, param_data)
                cc.capture_warnings(p)
                self.parameters[p.name] = p

        for rec_name, rec_data in self.src.get("recorders", {}).items():
            if m := re.search(DUP_KEY_RE, rec_name):
                span_end = m.span()[1]
                raw_name = rec_name[span_end+1:]
                self.errors["network"].append(PywrNetworkValidationError(f"Duplicate recorder name <{raw_name}>"))
            with component_exc_capture("recorders") as cc:
                r = PywrRecorder(rec_name, rec_data)
                cc.capture_warnings(r)
                self.recorders[r.name] = r

        try:
            for node in self.src["nodes"]:
                with component_exc_capture("nodes") as cc:
                    n = PywrNode(node)
                    cc.capture_warnings(n)

                    if n.name in seen_nodes:
                        self.errors["network"].append(PywrNetworkValidationError(f"Duplicate node name <{n.name}>"))
                    else:
                        self.nodes[n.name] = n
                        seen_nodes.add(n.name)
        except KeyError:
            self.errors["network"].append(PywrNetworkValidationError(f"Network contains no nodes"))


        try:
            for edge in self.src["edges"]:
                with component_exc_capture("edges") as cc:
                    e = PywrEdge(edge)
                    cc.capture_warnings(e)
                    self.edges.append(e)
        except KeyError:
            self.errors["network"].append(PywrNetworkValidationError(f"Network contains no edges"))

        if not allow_duplicate_edges and self.has_duplicate_edges:
            for edge in self.duplicate_edges:
                self.errors["network"].append(PywrNetworkValidationError(f"Duplicate edge <{edge}>"))


    @property
    def has_errors(self):
        """
        Indicates the presence of errors in the parsed input.

        Returns:
            bool: ``True`` if errors are present
        """
        return len(self.errors) > 0


    @property
    def has_warnings(self):
        """
        Indicates that warnings were generated by parsing the input.

        Returns:
            bool: ``True`` if warnings are present
        """
        return len(self.warnings) > 0

    @property
    def has_duplicate_edges(self):
        """
        Indicates the presence of duplicate edges in the parsed input.

        Returns:
            bool: ``True`` if duplicate edges are present
        """
        return len(self.duplicate_edges) > 0

    @property
    def duplicate_edges(self):
        """
        Return a dict of "duplicate" edges, that is edges of length `n`
        comprised of the same `n` nodes in the same order which are
        defined more than once.
        This is permitted by Pywr but may indicate a malformed network
        in some enviroments.

        Returns:
            duplicate_edges (Dict[PywrEdge, Int]): A mapping from each duplicate
                edge to its multiplicity in the network
        """
        edge_count = Counter((n1, n2) for (n1, n2) in self.edges)
        return {edge: count for edge, count in edge_count.items() if count > 1}
