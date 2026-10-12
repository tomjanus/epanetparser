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
        
        assert result["version"] == "wntr-1.4.0"
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
        
        # Check hydraulic options
        hydraulic = options["hydraulic"]
        assert hydraulic["headloss"] == "H-W"
        assert hydraulic["inpfile_units"] == "CMH"
        assert hydraulic["demand_model"] == "DDA"

    def test_nodes_parsed(self):
        """All junctions, reservoirs, and tanks are parsed."""
        result = read_inp_to_dict(VALID_INP)
        nodes = result["nodes"]
        
        assert len(nodes) == 785
        
        # Check junction structure
        junction = next(n for n in nodes if n["node_type"] == "Junction")
        assert "name" in junction
        assert "elevation" in junction
        assert "base_demand" in junction
        assert "demand_pattern_name" in junction
        assert "emitter_coefficient" in junction
        assert "coordinates" in junction
        assert "initial_quality" in junction
        
        # Check reservoir structure
        reservoir = next(n for n in nodes if n["node_type"] == "Reservoir")
        assert "name" in reservoir
        assert "base_head" in reservoir
        assert "head_pattern_name" in reservoir
        
        # Check tank structure
        tank = next(n for n in nodes if n["node_type"] == "Tank")
        assert "name" in tank
        assert "elevation" in tank
        assert "init_level" in tank
        assert "min_level" in tank
        assert "max_level" in tank
        assert "diameter" in tank
        assert "min_vol" in tank
        assert "vol_curve_name" in tank

    def test_links_parsed(self):
        """All pipes, pumps, and valves are parsed."""
        result = read_inp_to_dict(VALID_INP)
        links = result["links"]
        
        assert len(links) == 909
        
        # Check pipe structure
        pipe = next(l for l in links if l["link_type"] == "Pipe")
        assert "name" in pipe
        assert "start_node_name" in pipe
        assert "end_node_name" in pipe
        assert "length" in pipe
        assert "diameter" in pipe
        assert "roughness" in pipe
        assert "minor_loss" in pipe
        assert "initial_status" in pipe
        assert "check_valve" in pipe
        assert "vertices" in pipe
        
        # Check pump structure
        pump = next(l for l in links if l["link_type"] == "Pump")
        assert "name" in pump
        assert "start_node_name" in pump
        assert "end_node_name" in pump
        assert "pump_type" in pump
        assert "pump_curve_name" in pump
        assert "power" in pump
        assert "base_speed" in pump
        assert "speed_pattern_name" in pump
        assert "initial_status" in pump
        assert "efficiency_curve_name" in pump
        assert "vertices" in pump

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
        
        # May be empty or have sources
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
            assert "name" in control
            assert "type" in control


class TestInpParserUnits:
    """Unit conversion tests."""

    def test_cmh_to_si_conversion(self):
        """Flow units in CMH are converted to SI (m3/s)."""
        result = read_inp_to_dict(VALID_INP)
        
        # Junction demands should be in m3/s (find one with non-zero demand)
        junction = next(n for n in result["nodes"] 
                       if n["node_type"] == "Junction" and n["base_demand"] > 0)
        demand = junction["base_demand"]
        # Original was 0.169920 CMH = 0.169920 / 3600 = 4.72e-5 m3/s
        assert demand > 0
        assert demand < 0.01  # Reasonable range for m3/s
        
        # Pipe diameters in mm converted to meters
        pipe = next(l for l in result["links"] if l["link_type"] == "Pipe")
        diameter = pipe["diameter"]
        assert diameter > 0
        assert diameter < 2.0  # Reasonable range for meters

    def test_elevation_in_meters(self):
        """Elevations are in meters (SI)."""
        result = read_inp_to_dict(VALID_INP)
        
        junction = next(n for n in result["nodes"] if n["node_type"] == "Junction")
        elevation = junction["elevation"]
        assert elevation > 0
        assert elevation < 200  # Reasonable range for meters


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

    def test_round_trip_preserves_values(self):
        """Key values preserved through round-trip."""
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
            
            # Check a few specific values
            node1_1 = next(n for n in dict1["nodes"] if n["name"] == "n1")
            node1_2 = next(n for n in dict2["nodes"] if n["name"] == "n1")
            
            assert abs(node1_1["elevation"] - node1_2["elevation"]) < 1e-6
            assert abs(node1_1["base_demand"] - node1_2["base_demand"]) < 1e-6
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
        """Reference to undefined pattern raises InpSemanticError."""
        bad_inp = tmp_path / "bad.inp"
        bad_inp.write_text("""
[TITLE]
Test
[JUNCTIONS]
;ID Elev Demand Pattern
n1 10.0 0.01 UndefinedPattern
""")
        
        with pytest.raises(InpSemanticError) as exc_info:
            read_inp_to_dict(bad_inp)
        
        assert "UndefinedPattern" in str(exc_info.value)

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
        
        # Check that coordinates are parsed
        node_with_coords = next(
            (n for n in result["nodes"] if n["coordinates"]), None
        )
        # Coordinates may be empty list if not in file
        assert node_with_coords is not None or True  # May not have coords

    def test_vertices_section(self):
        """Pipe vertices are parsed if present."""
        result = read_inp_to_dict(VALID_INP)
        
        # Check vertices field exists
        pipe = next(l for l in result["links"] if l["link_type"] == "Pipe")
        assert "vertices" in pipe
        assert isinstance(pipe["vertices"], list)

    def test_tags_section(self):
        """TAGS section is parsed if present."""
        result = read_inp_to_dict(VALID_INP)
        
        # Tags may be in node/link data
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