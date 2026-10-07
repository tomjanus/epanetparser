"""Rendering validation results.

Two different kinds of finding reach the renderer, and both are live:

* :class:`~epanetparser.core.validation.results.ValidationIssue`, produced by
  the validation engine for a model that parsed but is not correct;
* :class:`~epanetparser.core.epanettypes.exceptions.WNTREPANETParserException`,
  a structural problem raised when a document cannot be turned into a model at
  all.

The ``parse`` command passes the first when a model was validated and the
second when it could not be, so a renderer that only understood one kind would
silently render nothing for the other. That is why the type dispatch in this
module exists, and these tests pin it down rather than leaving it to the CLI
tests, which can only observe the end of the pipeline.

The counting logic is the part most worth testing directly. A finding's
severity, not the mapping it arrived in, decides whether the header says error
or warning, so a warning filed under ``errors`` must still be counted as a
warning.
"""
import io
import json

import pytest
from rich.console import Console

from epanetparser.core import display
from epanetparser.core.display import (
    coalesce_errors_and_warnings,
    count_errors_warnings,
    results_as_dict,
    results_as_json,
    write_results,
)
from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException
from epanetparser.core.validation import Severity, ValidationIssue, ValidationReport


def make_issue(**kwargs):
    """Build a ValidationIssue with sensible defaults.

    Parameters
    ----------
    **kwargs : Any
        Field overrides, forwarded to
        :class:`~epanetparser.core.validation.results.ValidationIssue`.

    Returns:
        ValidationIssue: The issue.
    """
    defaults = dict(
        code="E_TEST",
        message="something is wrong",
        severity=Severity.ERROR,
        rule_id="rule_test",
        component_type="WNTREPANETNode",
        component_name="J1",
    )
    defaults.update(kwargs)
    return ValidationIssue(**defaults)


@pytest.fixture
def captured(monkeypatch):
    """Capture everything written to the module console.

    Returns:
        function: A callable taking the render call, returning the text printed.
    """
    def capture(call):
        buffer = io.StringIO()
        monkeypatch.setattr(display, "console", Console(file=buffer, width=200, no_color=True))
        call()
        return buffer.getvalue()

    return capture


class TestCounts:
    """Severity decides the count, not the mapping a finding arrived in."""

    def test_errors_and_warnings_are_counted_separately(self):
        """Two errors and one warning are reported as such."""
        errors = {"nodes": [make_issue(), make_issue(code="E_TWO")]}
        warnings = {"nodes": [make_issue(code="W_ONE", severity=Severity.WARNING)]}
        assert count_errors_warnings(errors, warnings) == (2, 1)

    def test_a_warning_filed_under_errors_is_still_a_warning(self):
        """The mapping is a grouping convenience, not the severity.

        ``grouped_by_component`` keys by component rather than by severity, so a
        warning routinely appears in the same list as errors. Counting by
        position would misreport the header.
        """
        grouped = {"nodes": [make_issue(severity=Severity.WARNING)]}
        assert count_errors_warnings(grouped, None) == (0, 1)

    def test_an_error_filed_under_warnings_is_still_an_error(self):
        """The same holds in the other direction.

        A caller that keeps warnings and errors apart can file an error under
        ``warnings``; the header must not then claim the model has no errors.
        """
        warnings = {"nodes": [make_issue(severity=Severity.ERROR)]}
        assert count_errors_warnings(None, warnings) == (1, 0)

    def test_nothing_counts_as_nothing(self):
        """An empty report has no findings, not an error."""
        assert count_errors_warnings(None, None) == (0, 0)
        assert count_errors_warnings({}, {}) == (0, 0)


class TestCoalescing:
    """Errors and warnings merge into one per-component list."""

    def test_both_mappings_land_in_one_list(self):
        """A component's errors and warnings are concatenated in order."""
        merged = coalesce_errors_and_warnings(
            {"nodes": ["e1"]}, {"nodes": ["w1"], "links": ["w2"]}
        )
        assert merged == {"nodes": ["e1", "w1"], "links": ["w2"]}

    def test_the_inputs_are_not_modified(self):
        """Merging returns a new mapping so a caller's report stays intact."""
        errors = {"nodes": ["e1"]}
        merged = coalesce_errors_and_warnings(errors, {"nodes": ["w1"]})
        assert errors == {"nodes": ["e1"]}
        assert merged is not errors


class TestRenderingValidationIssues:
    """The branch used when a model parsed and was validated."""

    def test_the_header_reports_the_counts(self, captured):
        """The banner names the file and both totals."""
        report = ValidationReport(
            [
                make_issue(),
                make_issue(code="E_TWO"),
                make_issue(code="W_ONE", severity=Severity.WARNING),
            ]
        )
        output = captured(lambda: write_results("Net1.json", results=report))
        assert "Parser results for 'Net1.json'" in output
        assert "2 errors" in output
        assert "1 warning" in output

    def test_singular_totals_are_not_pluralised(self, captured):
        """One error is '1 error', not '1 errors'."""
        output = captured(
            lambda: write_results("Net1.json", results=ValidationReport([make_issue()]))
        )
        assert "1 error," in output
        assert "0 warnings" in output

    def test_findings_are_grouped_by_component(self, captured):
        """Each component gets its own section, headed by its name."""
        report = ValidationReport(
            [
                make_issue(component_name="J1", message="junction is high"),
                make_issue(component_type="WNTREPANETLink", component_name="P1",
                           message="pipe is short"),
            ]
        )
        output = captured(lambda: write_results("Net1.json", results=report))
        assert "junction is high" in output
        assert "pipe is short" in output
        # Sections are headed by the component name, so J1 and P1 each get one.
        assert "J1" in output
        assert "P1" in output

    def test_a_finding_shows_its_code_and_message(self, captured):
        """A finding reads as ``<target> <code> -> <message>``.

        The code, not the rule function's name, is what a reader can search for
        in the documentation, so it is what the renderer shows.
        """
        output = captured(
            lambda: write_results(
                "Net1.json",
                results=ValidationReport([make_issue(code="E_TANK_ELEVATION")]),
            )
        )
        assert "E_TANK_ELEVATION" in output
        assert "something is wrong" in output

    def test_network_findings_come_first(self, captured):
        """A dangling reference is reported before the components it names."""
        report = ValidationReport(
            [
                make_issue(
                    code="E_UNKNOWN_REF",
                    message="dangling",
                    component_type="network",
                    component_name=None,
                ),
                make_issue(message="a node problem"),
            ]
        )
        output = captured(lambda: write_results("Net1.json", results=report))
        assert output.index("dangling") < output.index("a node problem")

    def test_text_labels_are_used_when_emoji_are_suppressed(self, captured):
        """Without emoji a finding is marked with a word, not a colour."""
        output = captured(
            lambda: write_results(
                "Net1.json",
                results=ValidationReport([make_issue()]),
                use_emoji=False,
            )
        )
        assert "[FAILURE]" in output
        assert "[WARNING]" not in output


class TestRenderingStructuralProblems:
    """The branch used when a document could not be parsed.

    These findings are ``WNTREPANETParserException``, not ``ValidationIssue``.
    The renderer reaches them through its fallback branches, and a change that
    removed those branches would leave this path printing nothing at all.
    """

    @pytest.fixture
    def structural(self):
        """Return a mapping shaped like the parser's structural errors.

        Returns:
            dict: One component key holding one parser exception.
        """
        return {
            "nodes": [
                WNTREPANETParserException(
                    "Key 'nodes' must be a list of WNTREPANETNode objects"
                )
            ]
        }

    def test_a_structural_problem_is_rendered(self, captured, structural):
        """The component and the message both appear in the output."""
        output = captured(lambda: write_results("broken.json", structural, None))
        assert "Parser results for 'broken.json'" in output
        assert "1 error" in output
        assert "must be a list of WNTREPANETNode" in output

    def test_a_structural_problem_names_its_component(self, captured, structural):
        """The parser's component key is the finding's target.

        The renderer falls back to the component key for a finding that carries
        no name of its own, which is the case for every parser exception.
        """
        output = captured(lambda: write_results("broken.json", structural, None))
        assert "nodes" in output

    def test_a_structural_problem_is_an_error_not_a_warning(self, structural):
        """An unparseable document counts as an error.

        The count comes from severity, and a parser exception carries none, so
        the renderer treats it as an error. That is the correct reading: the
        model could not be checked at all.
        """
        assert count_errors_warnings(structural, None) == (1, 0)


class TestStructuredOutput:
    """The machine-readable forms."""

    def test_the_sections_are_present(self, tmp_path):
        """A report records the file, the totals and the findings."""
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        result = results_as_dict(
            str(model), {"nodes": [make_issue()]}, None, include_digest=False
        )
        assert result["results"]["file"]["name"] == "Net1.json"
        assert result["results"]["errors"] == 1
        assert result["results"]["warnings"] == 0
        assert result["errors"]["nodes"][0]["code"] == "E_TEST"

    def test_the_selected_rulesets_are_recorded(self, tmp_path):
        """A stored report says which rules produced it."""
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        result = results_as_dict(str(model), {}, None, include_digest=False)
        assert result["results"]["rulesets"] == ["epanet_core"]

    def test_the_digest_can_be_included_or_omitted(self, tmp_path):
        """The digest is opt-out, because it costs a read of the model."""
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        with_digest = results_as_dict(str(model), {}, None, include_digest=True)
        without = results_as_dict(str(model), {}, None, include_digest=False)
        assert "sha256" in with_digest["results"]["file"]
        assert "sha256" not in without["results"]["file"]

    def test_a_clean_report_has_no_findings_sections(self, tmp_path):
        """A model with nothing to report does not carry empty error lists."""
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        result = results_as_dict(str(model), {}, None, include_digest=False)
        assert "errors" not in result
        assert "warnings" not in result

    def test_the_warnings_section_is_serialised(self, tmp_path):
        """Warnings reach the structured output, not only the console.

        A caller that stores a report and re-renders it needs the warnings
        section; omitting it would silently lose them.
        """
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        warnings = {"nodes": [make_issue(code="W_X", severity=Severity.WARNING)]}
        result = results_as_dict(str(model), None, warnings, include_digest=False)
        assert result["results"]["warnings"] == 1
        assert result["warnings"]["nodes"][0]["code"] == "W_X"

    def test_a_structural_problem_is_serialised(self, tmp_path):
        """A parser exception survives serialisation as a message.

        It has no ``as_dict``, so the renderer falls back to its string form. It
        must still be JSON-serialisable, or the JSON output would be broken
        exactly when a model is broken.
        """
        model = tmp_path / "broken.json"
        model.write_text("{}", encoding="utf-8")
        errors = {"nodes": [WNTREPANETParserException("not a list")]}
        result = results_as_dict(str(model), errors, None, include_digest=False)
        assert result["errors"]["nodes"][0]["message"] == "not a list"
        json.dumps(result)  # must not raise

    def test_standard_input_is_named_rather_than_digested(self):
        """A model read from stdin has no file to hash."""
        result = results_as_dict(io.StringIO("{}"), {}, None, include_digest=True)
        assert result["results"]["file"]["name"] == "stdin"
        assert "sha256" not in result["results"]["file"]

    def test_the_json_form_is_one_document(self, tmp_path):
        """The serialised form parses as a single JSON value.

        This function's output is written to stdout on its own, so a stray
        newline or a second document would make the output unusable.
        """
        model = tmp_path / "Net1.json"
        model.write_text("{}", encoding="utf-8")
        text = results_as_json(
            str(model), {"nodes": [make_issue(message="x" * 500)]}, None,
            include_digest=False,
        )
        parsed = json.loads(text)
        assert parsed["errors"]["nodes"][0]["message"] == "x" * 500
