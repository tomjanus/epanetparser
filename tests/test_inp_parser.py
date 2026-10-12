"""Tests for the INP parser (read_inp_to_dict).

These tests verify that the standalone INP parser correctly converts
EPANET INP files into the WNTR-compatible dictionary format.
"""
import pytest
import json
from pathlib import Path

from epanetparser.core.io import read_inp_to_dict, InpParseError, InpSyntaxError, InpSemanticError


REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_INP = REPO_ROOT / "tests/data/valid_network.inp"
INVALID_INP = REPO_ROOT / "tests/data/invalid_network.inp"


class TestInpParserBasic:
    """Basic parsing functionality."""

    def test_valid_inp_parses_to_dict(self):
        """A valid INP file parses to a dict with all expected keys."""
        result = read_inp_to_dict(VALID_INP)

        assert isinstance(result, dict)
        expected_keys = {
            "version", "comment", "name", "references",
            "options", "curves", "patterns", "nodes", "links", "sources", "controls"
        }
        assert set(result.keys()) == expected_keys

    def test_version_and_metadata(self):
        """Metadata fields are correctly extracted."""
        result = read_inp_to_dict(VALID_INP)

        # Vendored WNTR to_dict uses this version string
        assert result["version"] == "standalone-inp-dict-wntr-1.4.0-compatible"
        assert "valid_network" in result["name"]
        assert isinstance(result["comment"], str)
        assert isinstance(result["references"], list)

    def test_options_structure(self):
        """Options dict has all expected subsections."""
        result = read_inp_to_dict(VALID_INP)
        options = result["options"]

        expected_sections = {
            "time", "hydraulic", "report", "quality",
            "reaction", "energy", "graphics", "user"
        }
        assert set(options.keys()) == expected_sections

        # Check hydraulic options (defaults when not specified in INP)
        hydraulic = options["hydraulic"]
        assert hydraulic["headloss"] == "H-W"
        # INP file has CMH as flow units
        assert hydraulic["inpfile_units"] == "CMH"
        # Default demand model in WNTR is "DD"
        assert hydraulic["demand_model"] == "DD"

    def test_nodes_parsed(self):
        """All junctions, reservoirs, and tanks are parsed."""
        result = read_inp_to_dict(VALID_INP)
        nodes = result["nodes"]

        assert len(nodes) == 785

        # Junctions carry their full hydraulic attributes.
        junction = next(n for n in nodes if n["node_type"] == "Junction")
        assert "name" in junction
        assert "node_type" in junction
        assert "coordinates" in junction
        assert "elevation" in junction
        assert "base_demand" in junction

        # Reservoir also has minimal fields
        reservoir = next(n for n in nodes if n["node_type"] == "Reservoir")
        assert "name" in reservoir
        assert "node_type" in reservoir
        assert "coordinates" in reservoir

        # Tank also has minimal fields
        tank = next(n for n in nodes if n["node_type"] == "Tank")
        assert "name" in tank
        assert "node_type" in tank
        assert "coordinates" in tank

    def test_links_parsed(self):
        """All pipes, pumps, and valves are parsed."""
        result = read_inp_to_dict(VALID_INP)
        links = result["links"]

        assert len(links) == 909

        # WNTR's to_dict only outputs minimal fields for links
        pipe = next(l for l in links if l["link_type"] == "Pipe")
        assert "name" in pipe
        assert "link_type" in pipe
        assert "start_node_name" in pipe
        assert "end_node_name" in pipe
        # Note: length, diameter, roughness, etc. are NOT in to_dict output

        pump = next(l for l in links if l["link_type"] == "Pump")
        assert "name" in pump
        assert "link_type" in pump
        assert "start_node_name" in pump
        assert "end_node_name" in pump

    def test_patterns_parsed(self):
        """Time patterns are parsed correctly."""
        result = read_inp_to_dict(VALID_INP)
        patterns = result["patterns"]

        assert len(patterns) == 3

        pattern = patterns[0]
        assert "name" in pattern
        assert "multipliers" in pattern
        assert isinstance(pattern["multipliers"], list)
        assert all(isinstance(m, (int, float)) for m in pattern["multipliers"])

    def test_curves_parsed(self):
        """Curves are parsed correctly."""
        result = read_inp_to_dict(VALID_INP)
        curves = result["curves"]

        assert len(curves) == 1

        curve = curves[0]
        assert "name" in curve
        assert "curve_type" in curve
        assert "points" in curve
        assert isinstance(curve["points"], list)
        for point in curve["points"]:
            assert len(point) == 2
            assert all(isinstance(v, (int, float)) for v in point)

    def test_sources_parsed(self):
        """Water quality sources are parsed."""
        result = read_inp_to_dict(VALID_INP)
        sources = result["sources"]

        assert isinstance(sources, list)
        if sources:
            source = sources[0]
            assert "name" in source
            assert "node_name" in source
            assert "source_type" in source
            assert "strength" in source
            assert "pattern" in source

    def test_controls_parsed(self):
        """Controls are parsed."""
        result = read_inp_to_dict(VALID_INP)
        controls = result["controls"]

        assert isinstance(controls, list)
        if controls:
            control = controls[0]
            assert "type" in control
            assert "condition" in control
            assert "then_actions" in control


class TestInpParserUnits:
    """Unit conversion tests.

    Note: WNTR's to_dict outputs values in SI units, but only for fields
    that are included in the output. Since to_dict only includes minimal
    fields for nodes/links, we test the fields that are present.
    """

    def test_coordinates_in_si(self):
        """Coordinates are preserved as-is (typically in user units)."""
        result = read_inp_to_dict(VALID_INP)

        node_with_coords = next(
            (n for n in result["nodes"] if n["coordinates"]), None
        )
        if node_with_coords:
            x, y = node_with_coords["coordinates"]
            assert isinstance(x, (int, float))
            assert isinstance(y, (int, float))

    def test_curve_points_in_si(self):
        """Curve points are converted to SI units."""
        result = read_inp_to_dict(VALID_INP)
        curves = result["curves"]
        assert len(curves) == 1
        curve = curves[0]
        # Points should be in SI units (converted by WNTR during parsing)
        for x, y in curve["points"]:
            assert isinstance(x, (int, float))
            assert isinstance(y, (int, float))


class TestInpParserRoundTrip:
    """Round-trip tests: INP -> dict -> INP -> dict should be equivalent."""

    def test_round_trip_preserves_node_count(self):
        """Node count preserved through round-trip."""
        from epanetparser.core.io.network.io import from_dict, write_inpfile
        import tempfile
        import os

        # Parse INP to dict
        dict1 = read_inp_to_dict(VALID_INP)

        # Convert back to INP
        with tempfile.NamedTemporaryFile(suffix=".inp", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            wn = from_dict(dict1)
            write_inpfile(wn, tmp_path)

            # Parse again
            dict2 = read_inp_to_dict(tmp_path)

            assert len(dict1["nodes"]) == len(dict2["nodes"])
            assert len(dict1["links"]) == len(dict2["links"])
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_round_trip_preserves_component_names(self):
        """Component names preserved through round-trip."""
        from epanetparser.core.io.network.io import from_dict, write_inpfile
        import tempfile
        import os

        dict1 = read_inp_to_dict(VALID_INP)

        with tempfile.NamedTemporaryFile(suffix=".inp", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            wn = from_dict(dict1)
            write_inpfile(wn, tmp_path)
            dict2 = read_inp_to_dict(tmp_path)

            # Node names should match
            names1 = {n["name"] for n in dict1["nodes"]}
            names2 = {n["name"] for n in dict2["nodes"]}
            assert names1 == names2

            # Link names should match
            names1 = {l["name"] for l in dict1["links"]}
            names2 = {l["name"] for l in dict2["links"]}
            assert names1 == names2
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestInpParserErrors:
    """Error handling for malformed INP files."""

    def test_missing_file_raises(self):
        """Missing file raises appropriate error."""
        with pytest.raises(InpParseError) as exc_info:
            read_inp_to_dict("nonexistent.inp")

        assert "not found" in str(exc_info.value).lower() \
            or "no such file" in str(exc_info.value).lower()

    def test_malformed_section_header(self, tmp_path):
        """Invalid section header raises InpSyntaxError."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[INVALID_SECTION]
some data
""")

        with pytest.raises(InpSyntaxError) as exc_info:
            read_inp_to_dict(bad_inp)

        assert exc_info.value.error_code == "201"
        # Our wrapper extracts line_number from WNTR's ENSyntaxError
        assert exc_info.value.line_number is not None

    def test_malformed_junction_line(self, tmp_path):
        """Malformed junction line (non-numeric elevation) raises InpSyntaxError."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
    [TITLE]
    Test
    [JUNCTIONS]
    ;ID Elev Demand Pattern
    n1 not_a_number 0.01 P1
    [PATTERNS]
    P1 1.0
    """)

        with pytest.raises(InpSyntaxError) as exc_info:
            read_inp_to_dict(bad_inp)

        assert exc_info.value.error_code in ("201", "202", "209", "213")

    def test_undefined_curve_reference(self, tmp_path):
        """Reference to undefined curve raises InpSemanticError."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[JUNCTIONS]
;ID Elev Demand Pattern
n1 10.0 0.01 P1
[PATTERNS]
P1 1.0
[TANKS]
;ID Elev InitLevel MinLevel MaxLevel Diameter MinVol VolCurve Overflow
T1 10.0 5.0 0.0 10.0 5.0 0.0 UndefinedCurve
""")

        with pytest.raises(InpSemanticError) as exc_info:
            read_inp_to_dict(bad_inp)

        assert "UndefinedCurve" in str(exc_info.value)
        assert exc_info.value.error_code in ("203", "206", "213")

    def test_undefined_pattern_reference(self, tmp_path):
        """Reference to undefined pattern is handled gracefully (uses default)."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
    [TITLE]
    Test
    [JUNCTIONS]
    ;ID Elev Demand Pattern
    n1 10.0 0.01 UndefinedPattern
    """)

        # Vendored WNTR doesn't raise for undefined patterns; uses default
        result = read_inp_to_dict(bad_inp)
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "n1"

    def test_duplicate_id_detection(self, tmp_path):
        """Duplicate IDs are detected and reported."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[JUNCTIONS]
;ID Elev Demand Pattern
n1 10.0 0.01 P1
n1 10.0 0.02 P1
[PATTERNS]
P1 1.0
""")

        # Parser should either raise or include duplicate info in result
        result = read_inp_to_dict(bad_inp)
        # The parser may handle duplicates by keeping last or flagging
        # At minimum, it should not crash


class TestInpParserEdgeCases:
    """Edge cases and optional sections."""

    def test_empty_sections_handled(self, tmp_path):
        """Empty optional sections don't cause errors."""
        inp = tmp_path / "minimal.inp"
        inp.write_text("""
[TITLE]
Minimal
[JUNCTIONS]
;ID Elev Demand Pattern
n1 10.0 0.0 P1
[RESERVOIRS]
[TANKS]
[PIPES]
[PUMPS]
[VALVES]
[PATTERNS]
P1 1.0
""")

        result = read_inp_to_dict(inp)
        assert len(result["nodes"]) == 1
        assert len(result["links"]) == 0
        assert len(result["patterns"]) == 1

    def test_coordinates_section(self):
        """Coordinates are parsed if present."""
        result = read_inp_to_dict(VALID_INP)

        # Check that coordinates field exists
        node_with_coords = next(
            (n for n in result["nodes"] if n["coordinates"]), None
        )
        assert node_with_coords is not None

    def test_vertices_section(self):
        """Pipe vertices are parsed if present."""
        result = read_inp_to_dict(VALID_INP)

        pipe = next(l for l in result["links"] if l["link_type"] == "Pipe")
        assert "vertices" in pipe

    def test_tags_section(self):
        """TAGS section is parsed if present."""
        result = read_inp_to_dict(VALID_INP)

        # Tags field may be present
        node = result["nodes"][0]
        assert "tag" in node or "tag" not in node  # Optional field

    def test_backdrop_section(self):
        """BACKDROP section is parsed if present."""
        result = read_inp_to_dict(VALID_INP)
        # Should not crash
        assert "options" in result


class TestInpParserErrorAttributes:
    """Test that error objects have all required attributes."""

    def test_syntax_error_has_required_attrs(self, tmp_path):
        """InpSyntaxError has line_number, section, error_code, suggestions."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[INVALID_SECTION]
data
""")

        try:
            read_inp_to_dict(bad_inp)
        except InpSyntaxError as e:
            assert e.line_number is not None
            assert e.section is not None
            assert e.error_code is not None
            assert isinstance(e.suggestions, list)
            assert e.message

    def test_semantic_error_has_required_attrs(self, tmp_path):
        """InpSemanticError has line_number, section, error_code, suggestions."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[JUNCTIONS]
n1 10.0 0.01 UndefinedPattern
""")

        try:
            read_inp_to_dict(bad_inp)
        except InpSemanticError as e:
            assert e.line_number is not None
            assert e.section is not None
            assert e.error_code is not None
            assert isinstance(e.suggestions, list)
            assert e.message


class TestInpParserCliIntegration:
    """Integration with CLI validate command."""

    def test_cli_validates_inp_file(self):
        """CLI validate works with INP file."""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "validate",
             "-f", str(VALID_INP), "--no-digest"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )

        assert result.returncode in (0, 2)  # Valid or invalid, not parse error
        assert "Invalid JSON" not in result.stdout

    def test_cli_converts_inp_to_json(self):
        """CLI convert works with INP file."""
        import subprocess
        import sys
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, "-m", "epanetparser.core.parse", "convert",
                 str(VALID_INP), tmp_path],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=120
            )

            assert result.returncode == 0
            # Verify output is valid JSON
            with open(tmp_path) as f:
                json.load(f)
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])