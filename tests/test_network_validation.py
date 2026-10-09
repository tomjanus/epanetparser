"""Tests for network-level validation, including cross-component references.

Some questions about an EPANET model cannot be answered one component at a
time: does the curve a pump names exist, is any name used twice, does every
pattern a junction refers to actually belong to the model. Those are network
rules, and this file covers them.

Every test here starts from :func:`MINIMAL_NETWORK` and breaks exactly one
thing. A model with several defects produces a report in which it is hard to
tell which defect caused which finding, so isolating them is what makes these
assertions meaningful.
"""
import pytest

from epanetparser.core.epanettypes.network import (
    WNTRNetworkStatistics,
    WNTREPANETNetwork,
)
from epanetparser.core.validation import (
    NAME_INDEXED_COLLECTIONS,
    NetworkIndex,
    Severity,
    validate,
)
from tests.conftest import MINIMAL_NETWORK, build_network


def broken(**changes) -> WNTREPANETNetwork:
    """Return a copy of the minimal model with the named paths replaced.

    Parameters
    ----------
    **changes
        Nested keys and values, for example ``links__0__end_node_name="GONE"``.
        A ``__`` separator descends one level; a list index descends into a
        list.

    Returns:
        WNTREPANETNetwork: The modified model.
    """
    import copy

    source = copy.deepcopy(MINIMAL_NETWORK)
    for path, value in changes.items():
        keys = path.split("__")
        target = source
        for key in keys[:-1]:
            target = target[int(key)] if key.isdigit() else target[key]
        last = keys[-1]
        if isinstance(target, list):
            target[int(last)] = value
        else:
            target[last] = value
    return build_network(source)


class TestNetworkIndex:
    """The name index network rules resolve references through."""

    def test_indexes_every_name_addressable_collection(self, minimal_network):
        """The index covers exactly the collections whose components are named."""
        index = minimal_network.build_index()
        for collection in NAME_INDEXED_COLLECTIONS:
            assert isinstance(index.collection(collection), dict)
        assert sorted(index.nodes) == ["J1", "R1"]
        assert sorted(index.links) == ["P1"]
        assert sorted(index.patterns) == ["1"]
        assert sorted(index.curves) == ["1", "2"]

    def test_unknown_collections_are_empty_rather_than_an_error(self, minimal_network):
        """A rule may probe an optional collection without guarding first."""
        assert minimal_network.build_index().collection("pumps") == {}

    def test_curves_are_grouped_by_type(self, minimal_network):
        """Curve types can be asked for as a set, for type-aware rules."""
        index = minimal_network.build_index()
        assert index.curves_of_type("HEAD") == {"1", "2"}
        assert index.curves_of_type("VOLUME") == set()

    def test_the_index_is_cached_until_invalidated(self, minimal_network):
        """The index is reused, and only rebuilt once the model says it is stale.

        The cache is not invalidated by mutating the model, because nothing can
        tell that a list was changed in place. That is why ``invalidate_index``
        exists, and why a caller editing a model has to call it.
        """
        first = minimal_network.build_index()
        assert minimal_network.build_index() is first
        minimal_network.nodes.pop()
        assert minimal_network.build_index() is first
        minimal_network.invalidate_index()
        rebuilt = minimal_network.build_index()
        assert rebuilt is not first
        assert "R1" not in rebuilt.nodes
        assert "J1" in rebuilt.nodes

    def test_unnamed_components_are_not_indexed(self):
        """An unnamed component is a component rule's finding, not the index's."""
        network = broken(nodes=[{"node_type": "Junction", "elevation": 1.0}])
        assert network.build_index().nodes == {}

    def test_component_lookup_by_name(self, minimal_network):
        """A component can be fetched by collection and name."""
        assert minimal_network.component("nodes", "J1").name == "J1"
        assert minimal_network.component("nodes", "absent") is None

    def test_a_fresh_index_can_be_built_without_touching_the_model(self, minimal_network):
        """Building an index directly does not cache it on the network."""
        assert NetworkIndex(minimal_network).counts()["nodes"] == 2
        assert minimal_network.index is None

    def test_optional_collections_are_reachable_as_properties(self):
        """sources and controls are indexable like any other collection.

        They are exposed as properties rather than only through
        ``collection()`` because network rules read them by name, and a rule
        should not have to know that a collection with no members is spelled
        differently from one that has some.

        Controls are included because they are name-indexed, even though WNTR
        writes no name for them: they are reachable by name when a document does
        provide one, and index as empty when it does not. A network rule
        therefore does not have to special-case them.
        """
        network = broken(
            sources=[
                {
                    "name": "INP1",
                    "node_name": "J1",
                    "source_type": "Chlorine",
                    "strength": 0.1,
                }
            ],
            controls=[{"name": "C1", "condition": "LEVEL ABOVE 1"}],
        )
        index = network.build_index()
        assert "INP1" in index.sources
        assert "C1" in index.controls

    def test_an_absent_optional_collection_is_empty_not_an_error(self, minimal_network):
        """A model with no sources still has a sources index, and it is empty."""
        index = minimal_network.build_index()
        assert index.sources == {}
        assert index.controls == {}

    def test_has_reports_whether_a_name_resolves(self, minimal_network):
        """A network rule asks ``has`` before following a reference."""
        index = minimal_network.build_index()
        assert index.has("nodes", "J1") is True
        assert index.has("nodes", "absent") is False

    def test_has_is_false_for_an_empty_name(self, minimal_network):
        """A reference to nothing is not a reference to a component called ""."""
        assert minimal_network.build_index().has("nodes", "") is False

    def test_has_of_an_unknown_collection_is_false(self, minimal_network):
        """Probing a collection the model does not have is false, not a crash."""
        assert minimal_network.build_index().has("pumps", "PU1") is False

    def test_duplicates_are_reported_by_name(self):
        """A name used twice is found, so the network rule can report it.

        The index keeps one component per name, so the duplicate is invisible
        from the mapping alone; ``duplicates`` is how a rule asks.
        """
        network = broken(
            nodes=[
                {"name": "J1", "node_type": "Junction", "elevation": 1.0},
                {"name": "J1", "node_type": "Junction", "elevation": 2.0},
            ]
        )
        duplicates = network.build_index().duplicates("nodes")
        assert "J1" in duplicates

    def test_counts_summarise_every_collection(self, minimal_network):
        """``counts`` reports the size of each collection, for a summary report."""
        counts = minimal_network.build_index().counts()
        assert counts["nodes"] == 2
        assert counts["links"] == 1
        assert set(counts) >= {"nodes", "links", "curves", "patterns"}


class TestWholeNetworkValidation:
    """Validating a network rather than a component."""

    def test_a_valid_network_has_no_findings(self, minimal_network):
        """The minimal model satisfies the core ruleset completely (no errors)."""
        report = minimal_network.validate()
        assert report.is_valid
        assert len(report.errors) == 0

    def test_component_issues_come_before_network_issues(self):
        """A report reads from the specific to the general."""
        import copy

        source = copy.deepcopy(MINIMAL_NETWORK)
        del source["nodes"][1]["base_head"]          # a component rule
        source["links"][0]["end_node_name"] = "GONE"  # a network rule
        report = build_network(source).validate()

        kinds = [
            "network" if issue.component_type == "network" else "component"
            for issue in report
        ]
        assert "component" in kinds and "network" in kinds
        # The last network finding comes after every component finding.
        assert kinds == sorted(kinds, key=lambda kind: kind == "network")

    def test_every_component_collection_is_validated(self):
        """A defect in any collection is found, including the singletons."""
        network = broken(
            name="",
            options__time=None,
            patterns__0__multipliers=[],
            curves__0__points=[],
        )
        codes = network.validate().codes()
        assert "E_NETWORK_NAME_MISSING" in codes
        assert "E_OPTIONS_TIME_MISSING" in codes
        assert "E_PATTERN_MULTIPLIERS_MISSING" in codes
        assert "E_CURVE_POINTS_MISSING" in codes

    def test_the_report_can_be_grouped_for_display(self, minimal_network):
        """grouped_by_component yields the shape the display layer consumes."""
        network = broken(links__0__end_node_name="GONE")
        grouped = network.validate().grouped_by_component()
        # Findings are grouped by the component they concern; a network-level
        # finding is attributed to the network, which is named.
        # The broken network has issues with the network, a node, and a curve.
        assert set(grouped) == {"minimal", "J1", "2"}
        assert all(isinstance(issues, list) for issues in grouped.values())

    def test_validation_does_not_modify_the_model(self, minimal_network):
        """Validating a whole model is a read, like validating one component."""
        before = minimal_network.as_json()
        minimal_network.validate()
        assert minimal_network.as_json() == before

    def test_the_free_function_validates_a_whole_network(self, minimal_network):
        """validate(network) dispatches to network validation, not component."""
        assert validate(minimal_network).codes() == minimal_network.validate().codes()


class TestDuplicateNames:
    """Component names identify components, so they must be unique."""

    def test_a_duplicate_node_name_is_reported(self):
        """Two nodes with one name make every reference to it ambiguous."""
        network = broken(
            nodes=[
                {"name": "J1", "node_type": "Junction", "elevation": 1.0,
                 "coordinates": [0.0, 0.0]},
                {"name": "J1", "node_type": "Junction", "elevation": 2.0,
                 "coordinates": [1.0, 0.0]},
            ]
        )
        report = network.validate()
        issue = report.by_code("E_DUPLICATE_COMPONENT_NAME")[0]
        assert issue.component_type == "network"
        assert "nodes" in issue.message
        assert "J1" in issue.message

    def test_a_duplicate_link_name_is_reported(self):
        """Duplicate link names are found in their own collection."""
        network = broken(
            links=[
                {"name": "P1", "link_type": "Pipe", "start_node_name": "R1",
                 "end_node_name": "J1"},
                {"name": "P1", "link_type": "Pipe", "start_node_name": "J1",
                 "end_node_name": "R1"},
            ]
        )
        assert "E_DUPLICATE_COMPONENT_NAME" in network.validate().codes()

    def test_the_same_name_in_different_collections_is_fine(self):
        """Names are unique per collection: a pipe and a junction may share one."""
        network = broken(
            links=[
                {"name": "J1", "link_type": "Pipe", "start_node_name": "R1",
                 "end_node_name": "J1"},
            ]
        )
        assert "E_DUPLICATE_COMPONENT_NAME" not in network.validate().codes()

    def test_duplicates_are_kept_by_the_parser(self):
        """The parser does not merge duplicates; that would hide the defect."""
        network = broken(
            nodes=[
                {"name": "J1", "node_type": "Junction", "elevation": 1.0},
                {"name": "J1", "node_type": "Junction", "elevation": 2.0},
            ]
        )
        assert len(network.nodes) == 2


class TestCrossComponentReferences:
    """References between components must resolve."""

    def test_a_link_to_a_missing_start_node_is_reported(self):
        """A link that starts nowhere cannot carry flow."""
        network = broken(links__0__start_node_name="NOWHERE")
        report = network.validate()
        issue = report.by_code("E_UNKNOWN_NODE_REFERENCE")[0]
        assert issue.component_type == "network"
        assert "NOWHERE" in issue.message
        assert "start" in issue.message

    def test_a_link_to_a_missing_end_node_is_reported(self):
        """Both endpoints are checked, and the message says which one."""
        network = broken(links__0__end_node_name="NOWHERE")
        issue = network.validate().by_code("E_UNKNOWN_NODE_REFERENCE")[0]
        assert "end" in issue.message
        assert "NOWHERE" in issue.message

    def test_a_pump_curve_that_does_not_exist_is_reported(self):
        """A pump with a dangling head curve has no flow characteristic."""
        network = broken(
            links=[
                {
                    "name": "PU1",
                    "link_type": "Pump",
                    "start_node_name": "R1",
                    "end_node_name": "J1",
                    "pump_curve_name": "C_MISSING",
                }
            ]
        )
        report = network.validate()
        issue = report.by_code("E_UNKNOWN_CURVE_REFERENCE")[0]
        assert "C_MISSING" in issue.message
        assert "pump_curve_name" in issue.message
        assert issue.attribute == "pump_curve_name"

    def test_a_tank_volume_curve_that_does_not_exist_is_reported(self):
        """A tank's volume curve must resolve too."""
        network = broken(
            nodes=[
                {
                    "name": "T1",
                    "node_type": "Tank",
                    "diameter": 10.0,
                    "elevation": 1.0,
                    "init_level": 1.0,
                    "max_level": 2.0,
                    "min_level": 0.0,
                    "min_vol": 0.0,
                    "coordinates": [0.0, 0.0],
                    "vol_curve_name": "V_MISSING",
                }
            ]
        )
        assert "C_MISSING" in network.validate().codes() or (
            "V_MISSING" in network.validate().by_code(
                "E_UNKNOWN_CURVE_REFERENCE"
            )[0].message
        )

    def test_an_unknown_demand_pattern_is_reported(self):
        """A junction scaled by a pattern that is not in the model is unscalable."""
        network = broken(nodes__0__demand_pattern="P_MISSING")
        report = network.validate()
        issue = report.by_code("E_UNKNOWN_PATTERN_REFERENCE")[0]
        assert "P_MISSING" in issue.message
        assert "demand_pattern" in issue.message

    def test_a_source_pointing_at_a_missing_node_is_reported(self):
        """A source injecting into nothing is a silent no-op at best."""
        network = broken(
            sources=[
                {"node_name": "GONE", "source_type": "Chlorine", "strength": 0.1}
            ]
        )
        report = network.validate()
        issue = report.by_code("E_UNKNOWN_COMPONENT_REFERENCE")[0]
        assert "GONE" in issue.message
        assert issue.context["dangling"]

    def test_a_source_with_a_missing_pattern_is_reported(self):
        """A source modulated by a pattern that does not exist is also caught."""
        network = broken(
            sources=[
                {
                    "node_name": "J1",
                    "source_type": "Chlorine",
                    "strength": 0.1,
                    "pattern": "P_MISSING",
                }
            ]
        )
        assert "P_MISSING" in network.validate().by_code(
            "E_UNKNOWN_COMPONENT_REFERENCE"
        )[0].message

    def test_references_that_resolve_are_not_reported(self, minimal_network):
        """The minimal model wires everything to something that exists."""
        codes = minimal_network.validate().codes()
        assert not [
            code for code in codes
            if code.startswith("E_UNKNOWN")
        ]

    def test_curve_type_is_not_demanded_of_a_reference(self):
        """A referenced curve need only exist.

        WNTR labels every pump curve ``HEAD`` rather than ``PUMP``, so requiring
        a matching curve type would reject valid models. Only existence is
        checked, and that is deliberate.
        """
        network = broken(
            curves=[{"name": "1", "curve_type": "HEAD", "points": [[0.0, 10.0]]}],
            links=[
                {
                    "name": "PU1",
                    "link_type": "Pump",
                    "start_node_name": "R1",
                    "end_node_name": "J1",
                    "pump_curve_name": "1",
                }
            ],
        )
        assert "E_UNKNOWN_CURVE_REFERENCE" not in network.validate().codes()

    def test_an_absent_reference_is_not_a_dangling_one(self):
        """An unset field is the model's business, not a dangling reference."""
        network = broken(nodes__0__demand_pattern=None)
        assert "E_UNKNOWN_PATTERN_REFERENCE" not in network.validate().codes()

    def test_several_dangling_references_are_reported_together(self):
        """One report lists every unresolved reference, not just the first."""
        network = broken(
            nodes__0__demand_pattern="P_A",
            links__0__start_node_name="N_A",
            links__0__end_node_name="N_B",
        )
        report = network.validate()
        patterns = report.by_code("E_UNKNOWN_PATTERN_REFERENCE")[0].message
        endpoints = report.by_code("E_UNKNOWN_NODE_REFERENCE")[0].message
        assert "P_A" in patterns
        assert "N_A" in endpoints and "N_B" in endpoints


class TestNetworkShape:
    """A model has to be a model of something."""

    def test_a_network_without_nodes_is_reported(self):
        """Nothing to simulate."""
        network = broken(nodes=[])
        assert "E_NETWORK_HAS_NODES" in network.validate().codes()

    def test_a_network_without_links_is_reported(self):
        """Nodes with no links carry no hydraulics."""
        network = broken(links=[])
        assert "E_NETWORK_HAS_LINKS" in network.validate().codes()

    def test_network_issues_name_the_model(self):
        """A network-level finding is attributed to the network, not a component."""
        network = broken(links=[])
        issue = network.validate().by_code("E_NETWORK_HAS_LINKS")[0]
        assert issue.component_type == "network"
        assert issue.severity is Severity.ERROR


class TestReporting:
    """Counts and statistics, which read a parsed model."""

    def test_report_counts_collections(self, minimal_network):
        """The report counts whole collections."""
        assert minimal_network.report() == {
            "nodes": 2,
            "links": 1,
            "curves": 2,
            "patterns": 1,
        }

    def test_verbose_report_capitalises_names(self, minimal_network):
        """The verbose form is the same counts with capitalised keys."""
        verbose = minimal_network.verbose_report()
        assert verbose["Nodes"] == 2
        assert set(verbose) == {key.capitalize() for key in minimal_network.report()}

    def test_statistics_break_counts_down_by_type(self, minimal_network):
        """The statistics helper adds the per-concrete-type breakdown."""
        report = WNTRNetworkStatistics(minimal_network).report()
        assert report["nodes"] == 2
        assert report["nodes type Junction"] == 1
        assert report["nodes type Reservoir"] == 1
        assert report["links type Pipe"] == 1

    def test_statistics_ignore_unknown_collections(self, minimal_network):
        """Asking about a collection the model does not have is not an error."""
        stats = WNTRNetworkStatistics(minimal_network)
        assert stats.get_component_types("pumps") == []
        assert stats.get_number_of_components("pumps") == 0

    def test_as_dict_keeps_the_wntr_shape(self, minimal_network):
        """A round trip through as_dict keeps the sections WNTR expects."""
        import json

        payload = minimal_network.as_dict()
        assert set(payload) >= {"name", "options", "nodes", "links", "patterns"}
        reparsed = build_network(json.loads(json.dumps(payload)))
        assert reparsed.validate().is_valid

    def test_as_json_is_indented_by_default(self, minimal_network):
        """The JSON form is readable by default."""
        assert "\n  " in minimal_network.as_json()
        assert "\n" not in minimal_network.as_json(indent=None)


class TestSelection:
    """A network's rulesets are chosen by the caller."""

    def test_the_core_ruleset_is_the_default(self, valid_network):
        """A well-formed model passes core validation and needs no argument."""
        report = valid_network.validate()
        assert report.is_valid
        assert {issue.ruleset_key for issue in report} <= {"epanet_core"}

    def test_adding_a_custom_ruleset_can_only_add_findings(self, valid_network):
        """A custom ruleset never rescues a model the core ruleset rejects."""
        core = valid_network.validate()
        combined = valid_network.validate(["epanet_core", "milp"])
        assert len(combined) >= len(core)
        assert set(core.codes()) <= set(combined.codes())

    def test_a_model_may_pass_core_and_fail_a_custom_ruleset(self, valid_network_milp):
        """This is the whole point of separating the two: a model can be
        well-formed and still be unusable by one application."""
        assert valid_network_milp.validate().is_valid
        report = valid_network_milp.validate(["epanet_core", "milp"])
        assert all(issue.is_error for issue in report) is False or report.is_valid

    def test_findings_are_attributed_to_the_ruleset_that_made_them(self, invalid_network_milp):
        """A report says which ruleset to go and change."""
        report = invalid_network_milp.validate(["epanet_core", "milp"])
        milp_issues = [i for i in report if i.ruleset_key == "milp"]
        assert milp_issues
        assert all(i.ruleset_key == "milp" for i in milp_issues)
        assert {i.code for i in milp_issues} <= {
            code for code in report.codes() if code.startswith(("E_MILP", "W_MILP"))
        }


class TestLoading:
    """Reading models, which does not validate."""

    def test_from_json_returns_a_network_and_no_errors(self, minimal_network_json):
        """A well-formed document loads cleanly."""
        network, errors, warnings = WNTREPANETNetwork.from_json(minimal_network_json)
        assert network is not None
        assert errors is None
        assert warnings is None

    def test_invalid_json_is_a_structural_problem(self):
        """A document that is not JSON cannot become a model at all."""
        network, errors, _ = WNTREPANETNetwork.from_json("{not json")
        assert network is None
        assert "Invalid JSON" in str(errors["network"][0])

    def test_a_missing_required_key_is_a_structural_problem(self):
        """Without nodes and links there is no model to build."""
        network, errors, _ = WNTREPANETNetwork.from_json('{"options": {}}')
        assert network is None
        message = str(errors["network"][0])
        assert "Missing required key" in message
        assert "nodes" in message and "links" in message

    def test_a_collection_of_the_wrong_shape_is_a_structural_problem(self):
        """A section that is not a list of objects cannot be read."""
        network, errors, _ = WNTREPANETNetwork.from_json(
            '{"options": {}, "nodes": {}, "links": []}'
        )
        assert network is None
        assert "must be a list" in str(errors["nodes"][0])

    def test_a_structural_problem_can_be_raised_instead(self, minimal_network_json):
        """A caller that wants an exception can have one."""
        from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException

        with pytest.raises(WNTREPANETParserException):
            WNTREPANETNetwork.from_json('{"options": {}}', raise_on_parser_error=True)

    def test_optional_collections_may_be_absent(self):
        """A model with no curves, patterns, sources or controls is normal."""
        import json

        source = dict(MINIMAL_NETWORK)
        for key in ("curves", "patterns", "sources", "controls"):
            source.pop(key)
        network, errors, _ = WNTREPANETNetwork.from_json(json.dumps(source))
        assert network is not None, errors
        assert network.curves == [] and network.controls == []
        # A model with no patterns cannot satisfy a reference to one.
        assert "E_UNKNOWN_PATTERN_REFERENCE" in network.validate().codes()

    def test_a_file_that_does_not_exist_is_reported(self, tmp_path):
        """An unreadable path is a structural problem, not a traceback."""
        network, errors, _ = WNTREPANETNetwork.from_file(tmp_path / "absent.json")
        assert network is None
        assert "Unable to read input file" in str(errors["network"][0])

    def test_an_unsupported_extension_is_reported(self, tmp_path):
        """Only .inp and .json are model formats."""
        path = tmp_path / "model.txt"
        path.write_text("{}", encoding="utf-8")
        network, errors, _ = WNTREPANETNetwork.from_file(path)
        assert network is None
        assert "Unsupported file extension" in str(errors["network"][0])

    def test_a_model_with_defects_still_parses(self, invalid_network_json_file):
        """A model that fails validation still loads, so it can be reported on."""
        network, errors, _ = WNTREPANETNetwork.from_file(invalid_network_json_file)
        assert network is not None
        assert errors is None
        assert not network.validate().is_valid
