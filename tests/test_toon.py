"""Tests for TOON encoder and ValidationReport.as_toon()."""

import json
import pytest
from epanetparser.core.toon import TOONEncoder, encode, encode_validation_report
from epanetparser.core.validation import ValidationReport, ValidationIssue, Severity


class TestTOONEncoder:
    """Tests for the TOONEncoder class."""

    def test_encode_primitive_null(self):
        encoder = TOONEncoder()
        assert encoder.encode(None) == "null"

    def test_encode_primitive_bool(self):
        encoder = TOONEncoder()
        assert encoder.encode(True) == "true"
        assert encoder.encode(False) == "false"

    def test_encode_primitive_int(self):
        encoder = TOONEncoder()
        assert encoder.encode(42) == "42"
        assert encoder.encode(-5) == "-5"

    def test_encode_primitive_float(self):
        encoder = TOONEncoder()
        assert encoder.encode(3.14) == "3.14"
        assert encoder.encode(-2.5) == "-2.5"

    def test_encode_primitive_string_simple(self):
        encoder = TOONEncoder()
        assert encoder.encode("hello") == "hello"
        assert encoder.encode("hello_world") == "hello_world"

    def test_encode_primitive_string_quoted(self):
        encoder = TOONEncoder()
        # Strings with special chars should be quoted
        result = encoder.encode("hello world")
        assert result == '"hello world"'
        result = encoder.encode("hello:world")
        assert result == '"hello:world"'
        result = encoder.encode('hello "world"')
        assert result == '"hello \\"world\\""'

    def test_encode_empty_array(self):
        encoder = TOONEncoder()
        assert encoder.encode([]) == "[]"

    def test_encode_primitive_array_inline(self):
        encoder = TOONEncoder()
        result = encoder.encode([1, 2, 3])
        assert "[3]:" in result
        assert "1" in result and "2" in result and "3" in result

    def test_encode_string_array_inline(self):
        encoder = TOONEncoder()
        result = encoder.encode(["a", "b", "c"])
        assert "[3]:" in result
        assert "a" in result and "b" in result and "c" in result

    def test_encode_uniform_objects_tabular(self):
        encoder = TOONEncoder()
        data = [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
        ]
        result = encoder.encode(data)
        assert "[2]{" in result
        assert "id,name,role" in result
        assert "1,Alice,admin" in result
        assert "2,Bob,user" in result

    def test_encode_non_uniform_objects_list_form(self):
        encoder = TOONEncoder()
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "role": "admin"},
        ]
        result = encoder.encode(data)
        assert "- " in result  # List form uses - prefix

    def test_encode_nested_object(self):
        encoder = TOONEncoder()
        data = {"user": {"name": "Alice", "age": 30}, "active": True}
        result = encoder.encode(data)
        assert "user:" in result
        assert "name: Alice" in result or "name:Alice" in result
        assert "age: 30" in result or "age:30" in result
        assert "active: true" in result

    def test_encode_with_key(self):
        encoder = TOONEncoder()
        # Test encoding with a key at root level
        lines = encoder._encode_value({"a": 1}, depth=0, key="root")
        result = "\n".join(lines)
        assert "root:" in result
        assert "a: 1" in result

    def test_encode_numeric_strings_are_quoted(self):
        """A string reading as another type stays a string after decoding."""
        encoder = TOONEncoder()
        assert encoder.encode("1") == '"1"'
        assert encoder.encode("3.14") == '"3.14"'
        assert encoder.encode("true") == '"true"'
        assert encoder.encode("null") == '"null"'
        # Genuine scalars are still bare, and plain strings stay unquoted.
        assert encoder.encode(1) == "1"
        assert encoder.encode(True) == "true"
        assert encoder.encode("hello") == "hello"

    def test_encode_nested_arrays_keep_their_content(self):
        """Nested arrays recurse instead of collapsing to a placeholder."""
        encoder = TOONEncoder()
        result = encoder.encode({"points": [[0, 1], [2, 3]]})
        assert "[...]" not in result
        assert "0,1" in result and "2,3" in result
        # The tabular-cell path inlines recursively as well.
        assert encoder._encode_nested_array_inline([[0, 1], [2, 3]]) == (
            "[[0,1],[2,3]]"
        )


class TestEncodeValidationReport:
    """Tests for encode_validation_report function."""

    def test_empty_report(self):
        report_dict = {
            "is_valid": True,
            "counts": {"ERROR": 0, "WARNING": 0, "INFO": 0},
            "issues": [],
        }
        result = encode_validation_report(report_dict)
        assert "is_valid: true" in result
        assert "ERROR: 0" in result
        assert "issues[0]{code,message,severity,rule_id,ruleset_key" in result

    def test_report_with_issues(self):
        report_dict = {
            "is_valid": False,
            "counts": {"ERROR": 1, "WARNING": 1, "INFO": 0},
            "issues": [
                {
                    "code": "E_TEST_ERROR",
                    "message": "Test error message",
                    "severity": "ERROR",
                    "rule_id": "rule_test",
                    "ruleset_key": "epanet_core",
                    "component_type": "WNTREPANETNode",
                    "component_name": "N1",
                    "attribute": "elevation",
                    "component_data": {},
                    "context": {},
                },
                {
                    "code": "W_TEST_WARNING",
                    "message": "Test warning message",
                    "severity": "WARNING",
                    "rule_id": "rule_warn",
                    "ruleset_key": "epanet_core",
                    "component_type": "network",
                    "component_name": None,
                    "attribute": None,
                    "component_data": {},
                    "context": {},
                },
            ],
        }
        result = encode_validation_report(report_dict)
        assert "is_valid: false" in result
        assert "ERROR: 1" in result
        assert "WARNING: 1" in result
        assert "issues[2]{" in result
        assert "E_TEST_ERROR" in result
        assert "W_TEST_WARNING" in result

    def test_report_preserves_order(self):
        """Test that key order is preserved: is_valid, counts, issues."""
        report_dict = {
            "is_valid": True,
            "counts": {"ERROR": 0, "WARNING": 0, "INFO": 0},
            "issues": [],
            "extra_field": "should_be_last",
        }
        result = encode_validation_report(report_dict)
        # Check that is_valid comes first, then counts, then issues, then extra_field
        assert result.index("is_valid:") < result.index("counts:")
        assert result.index("counts:") < result.index("issues[0]{")
        assert result.index("issues[0]{") < result.index("extra_field:")


class TestValidationReportAsToon:
    """Tests for ValidationReport.as_toon() method."""

    def test_empty_report_as_toon(self):
        report = ValidationReport()
        result = report.as_toon()
        assert "is_valid: true" in result
        assert "ERROR: 0" in result
        assert "issues[0]{code,message,severity,rule_id,ruleset_key" in result

    def test_report_with_issues_as_toon(self):
        issue1 = ValidationIssue(
            code="E_NODE_NAME_MISSING",
            message="Node must have a name",
            severity=Severity.ERROR,
            rule_id="rule_node_has_name",
            ruleset_key="epanet_core",
            component_type="WNTREPANETNode",
            component_name="N1",
            attribute="name",
        )
        issue2 = ValidationIssue(
            code="W_UNKNOWN_PATTERN",
            message="Pattern 'P1' not found",
            severity=Severity.WARNING,
            rule_id="rule_pattern_exists",
            ruleset_key="epanet_core",
            component_type="network",
            component_name=None,
            attribute="pattern",
        )
        report = ValidationReport([issue1, issue2])
        result = report.as_toon()

        assert "is_valid: false" in result
        assert "ERROR: 1" in result
        assert "WARNING: 1" in result
        assert "issues[2]{" in result
        assert "E_NODE_NAME_MISSING" in result
        assert "W_UNKNOWN_PATTERN" in result
        assert "N1" in result

    def test_report_with_component_data_as_toon(self):
        issue = ValidationIssue(
            code="E_TANK_DIAMETER_MISSING",
            message="Tank does not define a diameter",
            severity=Severity.ERROR,
            rule_id="rule_tank_has_diameter",
            ruleset_key="epanet_core",
            component_type="WNTREPANETNode",
            component_name="T1",
            attribute="diameter",
            component_data={"name": "T1", "node_type": "Tank", "elevation": "100"},
            context={"ruleset": "epanet_core", "component_subtype": "node"},
        )
        report = ValidationReport([issue])
        result = report.as_toon()

        assert "E_TANK_DIAMETER_MISSING" in result
        assert "T1" in result
        # component_data should be encoded in the row


class TestReportParity:
    """ValidationReport.as_dict() and .as_toon() carry identical content."""

    @staticmethod
    def _mixed_report() -> ValidationReport:
        """A report holding one issue of each validation layer."""
        structural = ValidationIssue(
            code="E_PARSE_FAILED",
            message="Document is not valid JSON",
            severity=Severity.ERROR,
            rule_id="parse",
            ruleset_key="parser",
            component_type="network",
            validation_layer="structural",
            context={"exception_type": "ValueError"},
        )
        static = ValidationIssue(
            code="E_NODE_ELEVATION_MISSING",
            message="Junction J1 has no elevation",
            severity=Severity.ERROR,
            rule_id="rule_junction_has_elevation",
            ruleset_key="epanet_core",
            component_type="WNTREPANETNode",
            component_name="J1",
            attribute="elevation",
            component_data={"name": "J1", "node_type": "Junction"},
            context={"ruleset": "epanet_core"},
            category="Parameter",
            fix_suggestion="Set the elevation on junction J1.",
            validation_layer="static",
        )
        simulation = ValidationIssue(
            code="E_MINIMUM_PRESSURE",
            message="Minimum pressure 12.0 psi below required 20.0 psi",
            severity=Severity.ERROR,
            rule_id="rule_minimum_pressure",
            ruleset_key="hydraulic",
            component_type="simulation",
            attribute="pressure",
            category="Hydraulic",
            fix_suggestion="Increase pipe diameters or add pumps.",
            validation_layer="simulation",
            simulation_metadata={"required_outputs": ["node.pressure"]},
        )
        return ValidationReport([structural, static, simulation])

    def test_every_issue_field_name_appears_in_toon(self):
        """Each as_dict field name is present in the TOON encoding."""
        report = self._mixed_report()
        toon = report.as_toon()
        for issue in report.as_dict()["issues"]:
            for field in issue:
                assert field in toon, f"field {field!r} missing from TOON"

    def test_counts_match(self):
        """The per-severity counts are identical in both encodings."""
        report = self._mixed_report()
        toon = report.as_toon()
        for severity, count in report.as_dict()["counts"].items():
            assert f"{severity}: {count}" in toon
        assert ("is_valid: false" in toon) == (not report.is_valid)

    def test_severities_and_layers_are_preserved(self):
        """Severity names and validation layers survive the TOON round trip."""
        report = self._mixed_report()
        toon = report.as_toon()
        payload = report.as_dict()
        assert [issue["severity"] for issue in payload["issues"]] == [
            "ERROR",
            "ERROR",
            "ERROR",
        ]
        assert [issue["validation_layer"] for issue in payload["issues"]] == [
            "structural",
            "static",
            "simulation",
        ]
        for issue in payload["issues"]:
            assert issue["severity"] in toon
            assert issue["validation_layer"] in toon

    def test_simulation_metadata_category_and_fix_are_preserved(self):
        """The simulation-only and agent-facing fields are not dropped."""
        report = self._mixed_report()
        toon = report.as_toon()
        assert "simulation_metadata" in toon
        assert "Hydraulic" in toon
        assert "add pumps" in toon
        assert "node.pressure" in toon

    def test_numeric_string_fields_keep_their_type(self):
        """A component named "1" is quoted, not mistaken for a number."""
        issue = ValidationIssue(
            code="E_CURVE_TYPE_UNSUPPORTED",
            message="Curve 1 has an unsupported type",
            severity=Severity.ERROR,
            rule_id="rule_curve_type_supported",
            ruleset_key="epanet_core",
            component_type="WNTREPANETCurve",
            component_name="1",
            attribute="curve_type",
            component_data={"name": "1", "points": [[0, 1], [2, 3]]},
            validation_layer="static",
        )
        toon = ValidationReport([issue]).as_toon()
        assert '"1"' in toon
        assert "[[0,1],[2,3]]" in toon
        assert "[...]" not in toon


class TestTOONCLI:
    """Tests for CLI --toon-output flag (integration tests)."""

    def test_toon_output_valid_network(self, capsys):
        from epanetparser.core.parse import configure_args, handle_validate
        from epanetparser.core.epanettypes.network import WNTREPANETNetwork
        from pathlib import Path

        model = Path("tests/data/valid_network.json")
        network, errors, warnings = WNTREPANETNetwork.from_file(model)
        assert network is not None

        # Test with --toon-output
        args = configure_args(["validate", "-f", str(model), "--toon-output"])
        handle_validate(args)
        captured = capsys.readouterr()
        assert "is_valid: true" in captured.out
        assert "issues[85]{code,message,severity,rule_id,ruleset_key" in captured.out

    def test_toon_output_invalid_network(self, capsys):
        from epanetparser.core.parse import configure_args, handle_validate
        import pytest

        invalid_path = "tests/data/invalid_network.json"
        args = configure_args(["validate", "-f", invalid_path, "--toon-output"])
        with pytest.raises(SystemExit) as exc_info:
            handle_validate(args)
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "is_valid: false" in captured.out
        assert "ERROR:" in captured.out

    def test_toon_output_mutually_exclusive_with_json(self, capsys):
        from epanetparser.core.parse import configure_args, handle_validate
        import pytest

        invalid_path = "tests/data/invalid_network.json"
        args = configure_args(["validate", "-f", invalid_path, "--toon-output", "--json-output"])
        with pytest.raises(SystemExit) as exc_info:
            handle_validate(args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Only one of --json-output, --toon-output, --pretty-output may be used" in captured.err

    def test_toon_output_mutually_exclusive_with_pretty(self, capsys):
        from epanetparser.core.parse import configure_args, handle_validate
        import pytest

        invalid_path = "tests/data/invalid_network.json"
        args = configure_args(["validate", "-f", invalid_path, "--toon-output", "--pretty-output"])
        with pytest.raises(SystemExit) as exc_info:
            handle_validate(args)
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Only one of --json-output, --toon-output, --pretty-output may be used" in captured.err


if __name__ == "__main__":
    pytest.main([__file__, "-v"])