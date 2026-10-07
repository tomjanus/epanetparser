"""Tests for the structured results of static validation.

These tests cover the value objects the engine produces: severities, issues and
reports. They are deliberately independent of any rule set, because a report is
the contract between validation and everything downstream of it, and that
contract should hold whatever rules ran.

What is covered
---------------
* severity classification and its effect on validity;
* the fields an issue carries, and that they survive serialisation;
* report queries: by severity, by code, by rule, by component;
* report grouping, which is the shape the display layer consumes;
* the rule context carried on issues that reference a model.
"""
import pytest

from epanetparser.core.validation import (
    RuleViolation,
    Severity,
    ValidationIssue,
    ValidationReport,
    network_rule,
    rule,
)

NODE = "WNTREPANETNode"


class FakeNode:
    """Stand-in for a component, so result tests need no parser or rule set."""

    def __init__(self, name="T1", node_type="Tank"):
        self.name = name
        self.type = node_type
        self.data = {"name": name, "node_type": node_type}


def make_issue(**overrides) -> ValidationIssue:
    """Build an issue, defaulting every field so a test states only what matters.

    Parameters
    ----------
    **overrides
        Fields to override. ``code`` and ``message`` always have defaults.

    Returns:
        ValidationIssue: The issue.
    """
    fields = {
        "code": "E_EXAMPLE",
        "message": "example failure",
        "severity": Severity.ERROR,
        "rule_id": "rule_example",
        "ruleset_key": "epanet_core",
        "component_type": NODE,
        "component_name": "T1",
        "attribute": "diameter",
        "context": {},
    }
    fields.update(overrides)
    return ValidationIssue(**fields)


class TestSeverity:
    """Severity classification."""

    def test_members_are_ordered_by_seriousness(self):
        """Errors outrank warnings, which outrank informational findings."""
        assert Severity.ERROR > Severity.WARNING > Severity.INFO

    def test_string_form_is_the_member_name(self):
        """Rendering a severity yields the name callers match on in reports."""
        assert str(Severity.ERROR) == "ERROR"
        assert str(Severity.WARNING) == "WARNING"
        assert str(Severity.INFO) == "INFO"

    def test_converts_from_string(self):
        """A severity name resolves to its member, for configuration input."""
        assert Severity("error") is Severity.ERROR
        assert Severity("WARNING") is Severity.WARNING


class TestValidationIssue:
    """The individual finding."""

    def test_carries_every_provenance_field(self):
        """An issue says what failed, which rule said so, and against what."""
        issue = make_issue()
        assert issue.code == "E_EXAMPLE"
        assert issue.message == "example failure"
        assert issue.severity is Severity.ERROR
        assert issue.rule_id == "rule_example"
        assert issue.ruleset_key == "epanet_core"
        assert issue.component_type == NODE
        assert issue.component_name == "T1"
        assert issue.attribute == "diameter"
        assert issue.context == {}

    def test_severity_predicates(self):
        """Each severity is identifiable without comparing enum members."""
        assert make_issue(severity=Severity.ERROR).is_error
        assert make_issue(severity=Severity.WARNING).is_warning
        assert make_issue(severity=Severity.INFO).is_info
        assert not make_issue(severity=Severity.WARNING).is_error

    def test_string_form_names_the_component_and_the_code(self):
        """Rendering an issue puts the subject first, then the stable code."""
        text = str(make_issue())
        assert "T1" in text
        assert "E_EXAMPLE" in text
        assert "example failure" in text

    def test_string_form_falls_back_to_type_then_model(self):
        """An issue with no name still says what it is about."""
        assert "WNTREPANETNode" in str(make_issue(component_name=None))
        text = str(make_issue(component_name=None, component_type=None))
        assert "model" in text

    def test_as_dict_is_json_serialisable_and_complete(self):
        """Serialising an issue yields every field, with a readable severity."""
        import json

        payload = make_issue(context={"reference": "P1"}).as_dict()
        assert set(payload) == {
            "code",
            "message",
            "severity",
            "rule_id",
            "ruleset_key",
            "component_type",
            "component_name",
            "attribute",
            "component_data",
            "context",
        }
        assert payload["severity"] == "ERROR"
        assert payload["context"] == {"reference": "P1"}
        assert payload["component_data"] == {}
        json.dumps(payload)  # must not raise

    def test_as_dict_copies_context(self):
        """Serialising does not hand out the issue's own mutable context."""
        issue = make_issue(context={"a": 1})
        payload = issue.as_dict()
        payload["context"]["a"] = 2
        assert issue.context == {"a": 1}

    def test_issues_compare_by_value(self):
        """Equal issues compare equal, so findings can be compared in tests."""
        assert make_issue() == make_issue()
        assert make_issue() != make_issue(code="E_OTHER")

    def test_issues_are_immutable(self):
        """An issue cannot be edited after the engine has reported it."""
        issue = make_issue()
        with pytest.raises(Exception):
            issue.code = "E_CHANGED"  # type: ignore[misc]


class TestValidationReport:
    """The collection of findings and the queries over it."""

    def test_empty_report_is_valid(self):
        """A model with no findings is valid."""
        report = ValidationReport()
        assert report.is_valid
        assert len(report) == 0
        assert not report
        assert report.as_dict()["is_valid"] is True

    def test_errors_make_a_report_invalid(self):
        """One error is enough to invalidate; the model cannot be simulated."""
        report = ValidationReport([make_issue()])
        assert not report.is_valid
        assert len(report.errors) == 1

    def test_warnings_and_info_do_not_invalidate(self):
        """Only errors decide validity, so a report can warn and still be valid."""
        report = ValidationReport(
            [
                make_issue(code="W_A", severity=Severity.WARNING),
                make_issue(code="I_B", severity=Severity.INFO),
            ]
        )
        assert report.is_valid
        assert len(report.warnings) == 1
        assert len(report.info) == 1

    def test_mixed_report_is_invalid_and_partitions_correctly(self):
        """A report with findings of every severity partitions by severity."""
        report = ValidationReport(
            [
                make_issue(code="E_A"),
                make_issue(code="W_B", severity=Severity.WARNING),
                make_issue(code="E_C"),
                make_issue(code="I_D", severity=Severity.INFO),
            ]
        )
        assert not report.is_valid
        assert [issue.code for issue in report.errors] == ["E_A", "E_C"]
        assert [issue.code for issue in report.warnings] == ["W_B"]
        assert [issue.code for issue in report.info] == ["I_D"]
        assert len(report) == 4

    def test_preserves_production_order(self):
        """Issues stay in the order the engine produced them."""
        report = ValidationReport(
            [make_issue(code=code) for code in ("E_Z", "E_A", "E_M")]
        )
        assert report.codes() == ["E_Z", "E_A", "E_M"]

    def test_iteration_and_bool(self):
        """A report iterates over its issues and is truthy when it has any."""
        report = ValidationReport([make_issue()])
        assert [issue.code for issue in report] == ["E_EXAMPLE"]
        assert bool(report)
        assert "errors=1" in repr(report)

    def test_by_severity(self):
        """Filtering by severity returns only that severity, in order."""
        report = ValidationReport(
            [
                make_issue(code="E_A"),
                make_issue(code="W_B", severity=Severity.WARNING),
            ]
        )
        assert [i.code for i in report.by_severity(Severity.WARNING)] == ["W_B"]
        assert [i.code for i in report.by_severity("ERROR")] == ["E_A"]
        assert report.by_severity(Severity.INFO) == []

    def test_by_code_by_rule_and_by_component(self):
        """Findings can be looked up by the identifiers a caller knows."""
        report = ValidationReport(
            [
                make_issue(code="E_A", rule_id="rule_a", component_name="T1"),
                make_issue(code="E_B", rule_id="rule_b", component_name="T2"),
                make_issue(code="E_A", rule_id="rule_a", component_name="T2"),
            ]
        )
        assert len(report.by_code("E_A")) == 2
        assert len(report.by_rule("rule_a")) == 2
        assert [i.rule_id for i in report.by_component("T2")] == ["rule_b", "rule_a"]
        assert report.by_code("E_MISSING") == []

    def test_grouped_by_component(self):
        """Grouping collects findings per component, with no-name ones as network."""
        report = ValidationReport(
            [
                make_issue(component_name="T1"),
                make_issue(component_name="T1", code="E_SECOND"),
                make_issue(component_name=None, code="E_NETWORK"),
            ]
        )
        grouped = report.grouped_by_component()
        assert sorted(grouped) == ["T1", "network"]
        assert [i.code for i in grouped["T1"]] == ["E_EXAMPLE", "E_SECOND"]
        assert [i.code for i in grouped["network"]] == ["E_NETWORK"]

    def test_grouped_by_severity_always_has_three_keys(self):
        """The severity grouping is complete, so callers never guard for a key."""
        report = ValidationReport([make_issue()])
        grouped = report.grouped_by_severity()
        assert set(grouped) == {Severity.ERROR, Severity.WARNING, Severity.INFO}
        assert len(grouped[Severity.ERROR]) == 1
        assert grouped[Severity.WARNING] == []

    def test_as_dict_counts_and_issues(self):
        """The serialised report says whether the model is valid and how badly."""
        payload = ValidationReport(
            [
                make_issue(code="E_A"),
                make_issue(code="W_B", severity=Severity.WARNING),
            ]
        ).as_dict()
        assert payload["is_valid"] is False
        assert payload["counts"] == {"ERROR": 1, "WARNING": 1, "INFO": 0}
        assert [item["code"] for item in payload["issues"]] == ["E_A", "W_B"]

    def test_add_and_extend(self):
        """A report can be assembled incrementally as rules run."""
        report = ValidationReport()
        report.add(make_issue(code="E_A"))
        report.extend([make_issue(code="W_B", severity=Severity.WARNING)])
        assert report.codes() == ["E_A", "W_B"]

    def test_construction_does_not_alias_the_input(self):
        """Building a report from a list leaves the caller's list alone."""
        issues = [make_issue()]
        report = ValidationReport(issues)
        report.add(make_issue(code="E_SECOND"))
        assert len(issues) == 1

    def test_str_is_readable_when_empty_and_when_not(self):
        """Rendering a report works for both the empty and the populated case."""
        assert "no issues" in str(ValidationReport())
        text = str(ValidationReport([make_issue()]))
        assert "1 issues" in text
        assert "E_EXAMPLE" in text


class TestRuleMetadataOnIssues:
    """The metadata a rule declares reaches the issue it produces."""

    def test_code_defaults_to_the_rule_name(self):
        """A rule that names no code gets a deterministic one from its name."""
        @rule(NODE)
        def rule_node_has_name(node) -> None:
            """A node must have a name."""
            assert node.name, "no name"

        spec = rule_node_has_name.__epanetparser_rule__
        assert spec.code == "E_NODE_HAS_NAME"
        assert spec.severity is Severity.ERROR
        assert spec.is_network is False

    def test_warn_prefixed_rule_defaults_to_warning_severity(self):
        """A rule named warn_* reports a warning without saying so explicitly."""
        @rule(NODE)
        def warn_node_has_type(node) -> None:
            """A node should declare its type."""
            assert node.type, "no type"

        assert warn_node_has_type.__epanetparser_rule__.severity is Severity.WARNING

    def test_explicit_severity_overrides_the_name(self):
        """An explicit severity wins over the convention implied by the name."""
        @rule(NODE, severity=Severity.ERROR)
        def warn_but_fatal(node) -> None:
            """A warning that is nonetheless fatal."""
            assert node, "no node"

        assert warn_but_fatal.__epanetparser_rule__.severity is Severity.ERROR

    def test_attribute_and_description_are_recorded(self):
        """The field and the docstring summary are available for reporting."""
        @rule(NODE, attribute="diameter")
        def rule_tank_diameter(node) -> None:
            """A tank must have a diameter."""
            assert node.data.get("diameter"), "no diameter"

        spec = rule_tank_diameter.__epanetparser_rule__
        assert spec.attribute == "diameter"
        assert spec.description == "A tank must have a diameter."

    def test_network_rule_is_marked_and_needs_no_component(self):
        """A network rule records that it applies to the whole model."""
        @network_rule(code="E_NETWORK_LEVEL")
        def rule_whole_model(network) -> None:
            """A model must have links."""
            assert network.links, "no links"

        spec = rule_whole_model.__epanetparser_network_rule__
        assert spec.is_network is True
        assert spec.component_type is None
        assert spec.applies_to(FakeNode()) is True

    def test_component_rule_targets_only_its_class(self):
        """A rule naming a component class runs against that class only."""
        from epanetparser.core.epanettypes import WNTREPANETLink, WNTREPANETNode

        @rule(NODE)
        def rule_nodes_only(node) -> None:
            """Applies to nodes."""
            assert node, "no node"

        spec = rule_nodes_only.__epanetparser_rule__
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
        assert spec.applies_to(node) is True
        assert spec.applies_to(link) is False

    def test_component_type_can_come_from_the_annotation(self):
        """A rule may name its target in the decorator or in its annotation."""
        from epanetparser.core.epanettypes import WNTREPANETNode

        @rule()
        def rule_from_annotation(node: WNTREPANETNode) -> None:
            """Target taken from the parameter annotation."""
            assert node, "no node"

        spec = rule_from_annotation.__epanetparser_rule__
        assert spec.component_type == "WNTREPANETNode"
        assert spec.applies_to(WNTREPANETNode({"name": "J1"})) is True

    def test_rule_violation_carries_context(self):
        """A rule can attach structured detail to the finding it reports."""
        violation = RuleViolation("curve not found", curve="C9")
        assert isinstance(violation, AssertionError)
        assert str(violation) == "curve not found"
        assert violation.context == {"curve": "C9"}
