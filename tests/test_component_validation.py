"""Tests for component-level validation.

A component is validated on its own terms, with no access to the rest of the
model. This file covers what that means concretely: which rules run against a
component, that ``@match`` restricts a rule to a concrete type, that the report
says which component and field an issue is about, and that validating a
component never modifies it.

Cross-component questions are in ``test_network_validation.py``.
"""
import pytest

from epanetparser.core.epanettypes import (
    WNTREPANETControl,
    WNTREPANETCurve,
    WNTREPANETLink,
    WNTREPANETNetworkInfo,
    WNTREPANETNode,
    WNTREPANETOptions,
    WNTREPANETPattern,
    WNTREPANETSource,
)
from epanetparser.core.validation import (
    RuleSetSelectionError,
    Severity,
    ValidationContext,
    validate,
)


class TestAssignmentDoesNotValidate:
    """Parsing and validation are separate steps."""

    def test_assigning_invalid_data_does_not_raise(self):
        """A component holds whatever it is given; judging it is a separate step."""
        node = WNTREPANETNode({"node_type": "NotAType"})
        assert node.data == {"node_type": "NotAType"}
        assert not node.validate().is_valid

    def test_validation_does_not_modify_the_component(self):
        """Validation is a read: a valid model comes back byte-for-byte the same."""
        node = WNTREPANETNode(
            {"name": "J1", "node_type": "Junction", "elevation": 10.0}
        )
        before = dict(node.data)
        node.validate()
        assert node.data == before

    def test_repeated_validation_gives_equal_reports(self):
        """Results are not cached on the instance, so they cannot go stale."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        assert node.validate().codes() == node.validate().codes()

    def test_the_component_has_no_validation_methods(self):
        """Rules are not methods on the class, so nothing can be overridden."""
        assert not [
            name
            for name in dir(WNTREPANETNode)
            if name.startswith(("rule", "warn"))
        ]

    def test_data_is_a_plain_attribute(self):
        """Assigning data is plain attribute assignment, not descriptor magic."""
        node = WNTREPANETNode({"name": "J1"})
        assert node.data == {"name": "J1"}
        assert "_data" not in node.__dict__
        assert not hasattr(WNTREPANETNode, "__epanetparser_rule__")


class TestValidComponents:
    """Components that satisfy the core ruleset."""

    @pytest.mark.parametrize(
        "component",
        [
            WNTREPANETNode({"name": "J1", "node_type": "Junction", "elevation": 10.0,
                            "coordinates": [0.0, 0.0]}),
            WNTREPANETNode({"name": "R1", "node_type": "Reservoir", "base_head": 50.0,
                            "coordinates": [1.0, 0.0]}),
            WNTREPANETNode(
                {
                    "name": "T1",
                    "node_type": "Tank",
                    "diameter": 10.0,
                    "elevation": 5.0,
                    "init_level": 1.0,
                    "max_level": 6.0,
                    "min_level": 0.5,
                    "min_vol": 1.0,
                    "coordinates": [2.0, 0.0],
                }
            ),
            WNTREPANETLink({"name": "P1", "link_type": "Pipe"}),
            WNTREPANETCurve(
                {"name": "1", "curve_type": "HEAD", "points": [[0.0, 10.0], [1.0, 5.0]]}
            ),
            WNTREPANETPattern({"name": "1", "multipliers": [1.0, 0.5]}),
            WNTREPANETOptions(
                {"time": {}, "hydraulic": {}, "energy": {}}
            ),
            WNTREPANETNetworkInfo({"name": "Net1", "version": "wntr-1.4.0"}),
            WNTREPANETSource(
                {"node_name": "J1", "source_type": "Chlorine", "strength": 0.001}
            ),
            WNTREPANETControl({"type": "simple", "condition": "TIME > 8"}),
        ],
        ids=[
            "junction", "reservoir", "tank", "pipe", "curve", "pattern",
            "options", "network_info", "source", "control",
        ],
    )
    def test_valid_components_produce_no_errors(self, component):
        """A component that satisfies its rules produces no errors."""
        assert component.validate().errors == []

    def test_a_valid_network_has_no_findings(self, valid_network):
        """A well-formed model passes the core ruleset cleanly."""
        report = valid_network.validate()
        assert report.is_valid
        assert len(report) == 0


class TestJunctionRules:
    """A junction must define the fields its type requires."""

    def test_missing_elevation_is_reported(self):
        """A junction without an elevation is an error naming the field."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "coordinates": [0.0, 0.0]})
        report = node.validate()
        assert not report.is_valid
        issue = report.by_code("E_NODE_ELEVATION_MISSING")[0]
        assert issue.component_name == "J1"
        assert issue.component_type == "WNTREPANETNode"
        assert issue.attribute == "elevation"
        assert issue.rule_id == "rule_junction_has_elevation"
        assert issue.ruleset_key == "epanet_core"
        assert issue.context["component_subtype"] == "Junction"

    def test_a_tank_rule_does_not_apply_to_a_junction(self):
        """@match keeps a tank's requirements off a junction."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "coordinates": [0.0, 0.0]})
        codes = node.validate().codes()
        assert "E_TANK_DIAMETER_MISSING" not in codes

    def test_a_tank_rule_applies_to_a_tank(self):
        """The same rule fires when the component is a tank."""
        node = WNTREPANETNode(
            {
                "name": "T1",
                "node_type": "Tank",
                "elevation": 1.0,
                "init_level": 1.0,
                "max_level": 2.0,
                "min_level": 0.0,
                "min_vol": 0.0,
                "coordinates": [0.0, 0.0],
            }
        )
        codes = node.validate().codes()
        assert "E_TANK_DIAMETER_MISSING" in codes
        assert "E_NODE_ELEVATION_MISSING" not in codes

    def test_an_unsupported_type_is_reported(self):
        """A node that is not a junction, reservoir or tank is an error."""
        node = WNTREPANETNode({"name": "X1", "node_type": "Cistern",
                               "coordinates": [0.0, 0.0]})
        report = node.validate()
        assert report.by_code("E_NODE_TYPE_UNSUPPORTED")
        assert "Cistern" in report.by_code("E_NODE_TYPE_UNSUPPORTED")[0].message

    def test_a_missing_name_is_an_error_and_a_missing_type_a_warning(self):
        """An unnamed node cannot be reported on; an untyped one is only a hint."""
        node = WNTREPANETNode({"node_type": "Junction", "elevation": 1.0})
        report = node.validate()
        assert "E_NODE_NAME_MISSING" in report.codes()
        assert report.by_code("W_NODE_COORDINATES_MISSING")[0].severity is Severity.WARNING
        assert report.is_valid is False

    def test_missing_type_is_reported_as_a_warning(self):
        """A node that does not say what it is warns, without failing."""
        node = WNTREPANETNode({"name": "X1", "coordinates": [0.0, 0.0]})
        report = node.validate()
        assert "W_NODE_TYPE_MISSING" in report.codes()
        assert "E_NODE_TYPE_UNSUPPORTED" in report.codes()
        assert len(report.warnings) >= 1


class TestLinkRules:
    """A link must be a pipe, a pump or a valve."""

    def test_an_unsupported_type_is_reported(self):
        """A link of an unknown kind is an error naming the field."""
        link = WNTREPANETLink({"name": "X1", "link_type": "Culvert"})
        report = link.validate()
        assert report.by_code("E_LINK_TYPE_UNSUPPORTED")
        assert report.by_code("E_LINK_TYPE_UNSUPPORTED")[0].attribute == "link_type"

    def test_a_pump_must_be_defined_by_a_curve_or_a_power(self):
        """A pump with neither a curve nor a power rating has no flow-head relation."""
        pump = WNTREPANETLink({"name": "PU1", "link_type": "Pump"})
        assert "E_PUMP_UNDEFINED" in pump.validate().codes()
        pipe = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
        assert "E_PUMP_UNDEFINED" not in pipe.validate().codes()

    @pytest.mark.parametrize(
        "definition",
        [
            {"pump_curve_name": "1"},
            {"power": 11185.5},
            {"pump_curve_name": "1", "power": 11185.5},
        ],
        ids=["curve", "power", "both"],
    )
    def test_either_definition_is_enough(self, definition):
        """EPANET describes a pump by a curve or by constant power; either suffices."""
        pump = WNTREPANETLink({"name": "PU1", "link_type": "Pump", **definition})
        assert pump.validate().is_valid

    def test_a_zero_power_pump_is_not_defined(self):
        """A power of zero describes no pump, so it does not count as a definition."""
        pump = WNTREPANETLink({"name": "PU1", "link_type": "Pump", "power": 0})
        assert "E_PUMP_UNDEFINED" in pump.validate().codes()

    def test_a_pump_curve_that_does_not_exist_is_a_network_problem(self):
        """A component rule cannot see the curves, so it does not judge the reference."""
        pump = WNTREPANETLink(
            {"name": "PU1", "link_type": "Pump", "pump_curve_name": "MISSING"}
        )
        assert pump.validate().is_valid


class TestCurveRules:
    """A curve must be named, typed, and hold usable points."""

    def test_points_must_be_present(self):
        """A curve with no points cannot be interpolated."""
        curve = WNTREPANETCurve({"name": "1", "curve_type": "HEAD"})
        assert "E_CURVE_POINTS_MISSING" in curve.validate().codes()

    def test_points_must_be_pairs(self):
        """Each point must be an (x, y) pair."""
        curve = WNTREPANETCurve(
            {"name": "1", "curve_type": "HEAD", "points": [[0.0, 1.0, 2.0]]}
        )
        assert "E_CURVE_POINT_MALFORMED" in curve.validate().codes()

    def test_points_must_be_numeric(self):
        """Non-numeric coordinates are rejected."""
        curve = WNTREPANETCurve(
            {"name": "1", "curve_type": "HEAD", "points": [["0", 1.0]]}
        )
        assert "E_CURVE_POINT_NOT_NUMERIC" in curve.validate().codes()

    def test_points_must_ascend_in_x(self):
        """Unsorted x values make interpolation ambiguous."""
        curve = WNTREPANETCurve(
            {"name": "1", "curve_type": "HEAD", "points": [[1.0, 5.0], [0.0, 10.0]]}
        )
        assert "E_CURVE_POINTS_UNSORTED" in curve.validate().codes()

    def test_an_unknown_curve_type_is_reported(self):
        """A curve type EPANET does not define is an error."""
        curve = WNTREPANETCurve({"name": "1", "curve_type": "WIGGLE",
                                 "points": [[0.0, 1.0]]})
        assert "E_CURVE_TYPE_UNSUPPORTED" in curve.validate().codes()


class TestPatternRules:
    """A pattern must be named and hold numeric multipliers."""

    def test_multipliers_are_required(self):
        """A pattern with no multipliers does nothing."""
        pattern = WNTREPANETPattern({"name": "1"})
        assert "E_PATTERN_MULTIPLIERS_MISSING" in pattern.validate().codes()

    def test_multipliers_must_be_numeric(self):
        """Non-numeric multipliers cannot be applied to a demand."""
        pattern = WNTREPANETPattern({"name": "1", "multipliers": ["high", "low"]})
        assert "E_PATTERN_MULTIPLIER_NOT_NUMERIC" in pattern.validate().codes()

    def test_the_core_ruleset_imposes_no_pattern_length(self):
        """EPANET has no fixed pattern length, so the core ruleset must not invent one."""
        pattern = WNTREPANETPattern({"name": "1", "multipliers": [1.0] * 2016})
        assert pattern.validate().is_valid


class TestOptionsRules:
    """A model must say when, how and at what energy cost to simulate."""

    def test_each_required_group_is_reported(self):
        """A missing option group is named in the report."""
        required = {"time": {}, "hydraulic": {}, "energy": {}}
        expected = {
            "time": "E_OPTIONS_TIME_MISSING",
            "hydraulic": "E_OPTIONS_HYDRAULIC_MISSING",
            "energy": "E_OPTIONS_ENERGY_MISSING",
        }
        for group, code in expected.items():
            incomplete = {k: v for k, v in required.items() if k != group}
            options = WNTREPANETOptions(incomplete)
            assert code in options.validate().codes(), group
            # Only the absent group is reported, so the message is unambiguous.
            assert options.validate().codes() == [code]

    def test_all_groups_present_is_valid(self):
        """A model with the three required groups passes."""
        options = WNTREPANETOptions({"time": {}, "hydraulic": {}, "energy": {}})
        assert options.validate().is_valid

    def test_an_unmodelled_user_group_is_not_validated(self):
        """The [USER] group is not part of the model, so nothing is required of it."""
        options = WNTREPANETOptions({"time": {}, "hydraulic": {}, "energy": {},
                                     "user": {}})
        assert options.validate().is_valid
        assert options.user_options == {}


class TestNetworkInfoRules:
    """Model metadata is checked, but only the name is required."""

    def test_a_missing_name_is_an_error(self):
        """A report that cannot name its subject is not usable."""
        info = WNTREPANETNetworkInfo({"version": "wntr-1.4.0"})
        report = info.validate()
        assert "E_NETWORK_NAME_MISSING" in report.codes()
        assert not report.is_valid

    def test_a_missing_version_is_a_warning(self):
        """A model without a recorded version is still simulable."""
        info = WNTREPANETNetworkInfo({"name": "Net1"})
        report = info.validate()
        assert "W_NETWORK_VERSION_MISSING" in report.codes()
        assert report.is_valid

    def test_unrecognised_metadata_is_dropped(self):
        """Only the known metadata fields are retained on the component."""
        info = WNTREPANETNetworkInfo(
            {"name": "Net1", "version": "v", "surprise": 1}
        )
        assert "surprise" not in info.data


class TestSourceAndControlRules:
    """Sources and controls, which previously had no rules at all."""

    def test_a_source_needs_a_node_a_constituent_and_a_strength(self):
        """A source that omits any of the three is incomplete."""
        codes = WNTREPANETSource({}).validate().codes()
        assert "E_SOURCE_NODE_MISSING" in codes
        assert "E_SOURCE_TYPE_MISSING" in codes
        assert "E_SOURCE_STRENGTH_MISSING" in codes

    def test_a_source_keeps_its_fields(self):
        """The source's fields survive construction, which they previously did not.

        An earlier version read ``data.get("sources", [])`` and so stored an
        empty list in place of the source it was given.
        """
        source = WNTREPANETSource(
            {
                "name": "INP1",
                "node_name": "J1",
                "source_type": "Chlorine",
                "strength": 0.001,
                "pattern": "1",
            }
        )
        assert source.data["node_name"] == "J1"
        assert source.node_name == "J1"
        assert source.source_type == "Chlorine"
        assert source.strength == 0.001
        assert source.pattern == "1"
        assert source.validate().is_valid

    def test_a_control_kind_must_be_known(self):
        """A control of an unrecognised kind cannot be interpreted."""
        control = WNTREPANETControl({"type": "psychic", "condition": "TIME > 8"})
        assert "E_CONTROL_TYPE_UNSUPPORTED" in control.validate().codes()

    def test_a_control_needs_a_condition(self):
        """A control with nothing to react to does nothing."""
        control = WNTREPANETControl({"type": "simple"})
        assert "E_CONTROL_CONDITION_MISSING" in control.validate().codes()

    @pytest.mark.parametrize("kind", ["simple", "rule"])
    def test_both_control_kinds_are_accepted(self, kind):
        """Both kinds WNTR distinguishes are valid."""
        control = WNTREPANETControl({"type": kind, "condition": "TIME > 8"})
        assert control.validate().is_valid


class TestContextSelection:
    """A component's ruleset is chosen by the caller, not fixed."""

    def test_the_core_ruleset_is_the_default(self):
        """Validating with no context applies the core ruleset alone."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "elevation": 1.0, "coordinates": [0.0, 0.0]})
        report = node.validate()
        assert {issue.ruleset_key for issue in report} <= {"epanet_core"}

    def test_a_custom_ruleset_changes_the_verdict(self):
        """Adding a custom ruleset can turn a passing component into a failing one."""
        link = WNTREPANETLink({"name": "PRV1", "link_type": "Valve"})
        assert link.validate().is_valid
        report = link.validate(["epanet_core", "milp"])
        assert not report.is_valid
        assert "E_MILP_VALVE" in report.codes()
        assert report.by_code("E_MILP_VALVE")[0].ruleset_key == "milp"

    def test_issue_codes_are_stable_across_contexts(self):
        """A custom ruleset adds findings; it does not renumber the core ones."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "coordinates": [0.0, 0.0]})
        core = set(node.validate().codes())
        combined = set(node.validate(["epanet_core", "milp"]).codes())
        assert core <= combined
        assert "E_NODE_ELEVATION_MISSING" in core

    def test_an_unknown_context_is_reported_clearly(self):
        """Selecting a rule set that does not exist fails, and says so."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "elevation": 1.0})
        with pytest.raises(RuleSetSelectionError) as excinfo:
            node.validate(["epanet_core", "nosuch"])
        assert "nosuch" in str(excinfo.value)

    def test_a_context_object_is_accepted(self):
        """The explicit context form works wherever a loose selection does."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "elevation": 1.0, "coordinates": [0.0, 0.0]})
        context = ValidationContext(custom=["milp"])
        assert node.validate(context).is_valid
        assert validate(node, context).is_valid

    def test_the_free_function_matches_the_method(self):
        """validate(component) and component.validate() agree."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "coordinates": [0.0, 0.0]})
        assert validate(node).codes() == node.validate().codes()
