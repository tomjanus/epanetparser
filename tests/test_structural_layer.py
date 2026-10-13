"""Tests for the structural validation layer.

Structural problems are raised by the parser while a file is read, before a
network object exists. They are surfaced as
:class:`~epanetparser.core.validation.results.ValidationIssue` objects tagged
with ``validation_layer="structural"``, so that callers receive one uniformly
structured result whichever layer produced a finding.

What is covered
---------------
* ``InpParseError.to_validation_issue`` maps a parser problem onto the shared
  issue model, including its layer, code and structured context;
* ``WNTREPANETNetwork.from_file`` returns a malformed ``.inp`` as a structured
  error rather than letting the exception escape, unless the caller asks for
  it to be raised.
"""
import pytest

from epanetparser.core.io import (
    InpParseError,
    InpSyntaxError,
    read_inp_to_dict,
)
from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import Severity, ValidationIssue


def malformed_inp(tmp_path):
    """Write an INP with an unrecognised section and return its path."""
    path = tmp_path / "malformed.inp"
    path.write_text(
        "[TITLE]\nTest\n[INVALID_SECTION]\nsome data\n", encoding="utf-8"
    )
    return path


def parse_error(tmp_path):
    """Parse a malformed INP and return the structured error it raised."""
    path = malformed_inp(tmp_path)
    with pytest.raises(InpParseError) as exc_info:
        read_inp_to_dict(path)
    return exc_info.value


class TestToValidationIssue:
    """A parser error can present itself as a structural validation issue."""

    def test_identity_fields_are_stable(self, tmp_path):
        """The issue carries the agreed structural identity."""
        issue = parse_error(tmp_path).to_validation_issue()

        assert isinstance(issue, ValidationIssue)
        assert issue.validation_layer == "structural"
        assert issue.severity is Severity.ERROR
        assert issue.code == "E_PARSE_FAILED"
        assert issue.ruleset_key == "parser"
        assert issue.rule_id == "parse"
        assert issue.component_type == "network"

    def test_message_comes_from_the_error(self, tmp_path):
        """The human-readable message is the parser's own description."""
        error = parse_error(tmp_path)
        issue = error.to_validation_issue()

        assert issue.message == error.message

    def test_context_carries_structural_details(self, tmp_path):
        """Line, section, code, suggestions and type are all preserved."""
        error = parse_error(tmp_path)
        issue = error.to_validation_issue()

        assert set(issue.context) >= {
            "error_code",
            "line_number",
            "section",
            "suggestions",
            "exception_type",
        }
        assert issue.context["error_code"] == error.error_code
        assert issue.context["line_number"] == error.line_number
        assert issue.context["section"] == error.section
        assert issue.context["suggestions"] == error.suggestions
        assert issue.context["exception_type"] == "InpSyntaxError"

    def test_fix_suggestion_is_derived_from_suggestions(self, tmp_path):
        """The suggestions become an imperative fix hint."""
        error = parse_error(tmp_path)
        issue = error.to_validation_issue()

        assert issue.fix_suggestion
        for suggestion in error.suggestions:
            assert suggestion in issue.fix_suggestion

    def test_no_suggestions_yields_no_fix(self):
        """A bare parser error has nothing actionable to suggest."""
        error = InpParseError("boom")
        issue = error.to_validation_issue()

        assert issue.fix_suggestion == ""
        assert issue.validation_layer == "structural"
        assert issue.context["exception_type"] == "InpParseError"

    def test_issue_serialises_with_the_structural_layer(self, tmp_path):
        """The layer survives the report's JSON representation."""
        payload = parse_error(tmp_path).to_validation_issue().as_dict()

        assert payload["validation_layer"] == "structural"
        assert payload["code"] == "E_PARSE_FAILED"


class TestFromFileStructuralErrors:
    """``from_file`` reports a malformed INP instead of raising by default."""

    def test_malformed_inp_returns_a_structured_error(self, tmp_path):
        """The default is a returned error, so callers can render it."""
        network, errors, warnings = WNTREPANETNetwork.from_file(
            malformed_inp(tmp_path)
        )

        assert network is None
        assert warnings is None
        assert isinstance(errors["network"][0], InpParseError)
        assert isinstance(errors["network"][0], InpSyntaxError)

    def test_malformed_inp_raises_when_requested(self, tmp_path):
        """A caller who wants the exception gets the structured one."""
        with pytest.raises(InpParseError):
            WNTREPANETNetwork.from_file(
                malformed_inp(tmp_path), raise_on_parser_error=True
            )
