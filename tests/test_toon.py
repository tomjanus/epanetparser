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


class TestTOONCLI:
    """Tests for CLI --toon-output flag (integration tests)."""

    def test_toon_output_valid_network(self, capsys):
        from epanetparser.core.parse import configure_args, handle_validate
        from epanetparser.core.epanettypes.network import WNTREPANETNetwork
        from importlib.resources import files

        model = files("epanetparser.networks.core") / "Net1.inp"
        network, errors, warnings = WNTREPANETNetwork.from_file(model)
        assert network is not None

        # Test with --toon-output
        args = configure_args(["validate", "-f", str(model), "--toon-output"])
        handle_validate(args)
        captured = capsys.readouterr()
        assert "is_valid: true" in captured.out
        assert "issues[0]{code,message,severity,rule_id,ruleset_key" in captured.out

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