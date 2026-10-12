"""Equivalence tests for the standalone INP parser.

``InpParser(path).parse()`` is the standalone parser in
``epanetparser.core.io.inp_parser``.  The public ``read_inp_to_dict`` export
still delegates to the vendored WNTR ``InpFile`` and is used here as the
reference implementation.

For each core network the two implementations must produce identical
``nodes``, ``links``, ``curves``, ``patterns``, ``sources``, ``controls`` and
``options`` collections.
"""
from pathlib import Path

import pytest

from epanetparser.core.io import read_inp_to_dict
from epanetparser.core.io.inp_parser import InpParser


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "epanetparser" / "networks" / "core"
CORE_NETS = sorted(p.name for p in CORE_DIR.glob("*.inp"))

COLLECTIONS = [
    "nodes",
    "links",
    "curves",
    "patterns",
    "sources",
    "controls",
    "options",
]


def _standalone(net: str) -> dict:
    return InpParser(str(CORE_DIR / net)).parse()


def _wrapper(net: str) -> dict:
    return read_inp_to_dict(str(CORE_DIR / net))


def _diff(coll: str, net: str, got, ref) -> str:
    """Build a compact, human-readable description of the first differences."""
    lines = [f"{net}: standalone {coll!r} != wrapper {coll!r}"]
    if isinstance(ref, list):
        got_by_name = {x.get("name"): x for x in got}
        ref_by_name = {x.get("name"): x for x in ref}
        if set(got_by_name) != set(ref_by_name):
            lines.append(f"  only standalone: {sorted(set(got_by_name) - set(ref_by_name))}")
            lines.append(f"  only wrapper   : {sorted(set(ref_by_name) - set(got_by_name))}")
        for name in sorted(set(got_by_name) & set(ref_by_name), key=str):
            gk, rk = set(got_by_name[name]), set(ref_by_name[name])
            if gk != rk:
                lines.append(
                    f"  {name!r}: standalone-only keys {sorted(gk - rk)}; "
                    f"wrapper-only keys {sorted(rk - gk)}"
                )
            for key in sorted(gk & rk):
                if got_by_name[name][key] != ref_by_name[name][key]:
                    lines.append(
                        f"  {name!r}[{key!r}]: standalone={got_by_name[name][key]!r} "
                        f"wrapper={ref_by_name[name][key]!r}"
                    )
    elif isinstance(ref, dict):
        gk, rk = set(got), set(ref)
        if gk != rk:
            lines.append(
                f"  standalone-only groups {sorted(gk - rk)}; wrapper-only groups {sorted(rk - gk)}"
            )
        for group in sorted(gk & rk):
            if not isinstance(ref[group], dict):
                if got[group] != ref[group]:
                    lines.append(
                        f"  {group!r}: standalone={got[group]!r} wrapper={ref[group]!r}"
                    )
                continue
            keys = set(got[group]) | set(ref[group])
            for key in sorted(keys):
                if got[group].get(key) != ref[group].get(key):
                    lines.append(
                        f"  {group}.{key}: standalone={got[group].get(key)!r} "
                        f"wrapper={ref[group].get(key)!r}"
                    )
    return "\n".join(lines[:60])


@pytest.mark.parametrize("net", CORE_NETS)
@pytest.mark.parametrize("coll", COLLECTIONS)
def test_collection_matches_wrapper(net, coll):
    """Each parsed collection equals the vendored-WNTR-backed reference."""
    got = _standalone(net)[coll]
    ref = _wrapper(net)[coll]
    assert got == ref, _diff(coll, net, got, ref)


@pytest.mark.parametrize("net", CORE_NETS)
def test_top_level_keys_match(net):
    """Both parsers expose the same top-level keys and scalar metadata."""
    got = _standalone(net)
    ref = _wrapper(net)
    assert set(got) == set(ref)
    for key in ("version", "comment", "name", "references"):
        assert got[key] == ref[key], f"{net}: top-level {key!r} differs"


class TestMetadata:
    def test_version(self):
        assert _standalone("Net1.inp")["version"] == "standalone-inp-dict-wntr-1.4.0-compatible"

    def test_comment(self):
        assert _standalone("Net1.inp")["comment"] == "WaterNetworkModel - all values given in SI units"

    def test_references(self):
        assert _standalone("Net1.inp")["references"] == []

    def test_name_is_input_path(self):
        assert _standalone("Net1.inp")["name"] == str(CORE_DIR / "Net1.inp")
        assert _standalone("Net1.inp")["name"] == _wrapper("Net1.inp")["name"]


class TestNet1Values:
    def test_junction_10(self):
        j = {n["name"]: n for n in _standalone("Net1.inp")["nodes"]}["10"]
        assert j["node_type"] == "Junction"
        assert j["elevation"] == 216.40800000000002  # 710 ft -> m
        assert j["base_demand"] == 0.0
        assert j["coordinates"] == (20.0, 70.0)
        assert j["initial_quality"] == 0.0005
        assert j["demand_pattern"] == "1"
        assert j["demand_timeseries_list"] == [
            {"base_val": 0.0, "pattern_name": "1", "category": None}
        ]
        assert j["leak"] is False
        assert j["leak_area"] == 0.0
        assert j["leak_discharge_coeff"] == 0.0
        assert j["tag"] is None

    def test_reservoir_9(self):
        n = {x["name"]: x for x in _standalone("Net1.inp")["nodes"]}["9"]
        assert n["node_type"] == "Reservoir"
        assert n["base_head"] == 243.84  # 800 ft -> m
        assert n["elevation"] is None
        assert n["head_pattern_name"] is None
        assert n["initial_quality"] == 0.001

    def test_tank_2(self):
        n = {x["name"]: x for x in _standalone("Net1.inp")["nodes"]}["2"]
        assert n["node_type"] == "Tank"
        assert n["elevation"] == 259.08000000000004
        assert n["init_level"] == 36.576
        assert n["min_level"] == 30.48
        assert n["max_level"] == 45.72
        assert n["diameter"] == 15.3924
        assert n["min_vol"] == 0.0
        assert n["vol_curve_name"] is None
        assert n["overflow"] is False
        assert n["mixing_model"] is None
        assert n["bulk_coeff"] is None

    def test_pipe_10(self):
        l = {x["name"]: x for x in _standalone("Net1.inp")["links"]}["10"]
        assert l["link_type"] == "Pipe"
        assert l["diameter"] == 0.4572
        assert l["length"] == 3209.5440000000003
        assert l["roughness"] == 100.0
        assert l["minor_loss"] == 0.0
        assert l["check_valve"] is False
        assert l["bulk_coeff"] is None
        assert l["wall_coeff"] is None
        assert l["vertices"] == []
        assert l["initial_status"] == "Open"
        assert l["initial_setting"] == 1.0
        assert "coordinates" not in l
        assert "tag" not in l

    def test_pump_9(self):
        l = {x["name"]: x for x in _standalone("Net1.inp")["links"]}["9"]
        assert l["link_type"] == "Pump"
        assert l["pump_type"] == "HEAD"
        assert l["pump_curve_name"] == "1"
        assert l["base_speed"] == 1.0
        assert l["speed"] is None
        assert l["speed_pattern_name"] is None
        assert l["initial_setting"] == 1.0
        assert l["power"] is None
        assert l["efficiency_curve"] is None
        assert l["efficiency_curve_name"] is None
        assert l["energy_pattern"] is None
        assert l["energy_price"] is None
        assert l["initial_status"] == "Open"

    def test_controls(self):
        assert _standalone("Net1.inp")["controls"] == [
            {
                "type": "simple",
                "condition": "TANK 2 LEVEL BELOW 33.528",
                "then_actions": ["PUMP 9 STATUS IS OPEN"],
            },
            {
                "type": "simple",
                "condition": "TANK 2 LEVEL ABOVE 42.672000000000004",
                "then_actions": ["PUMP 9 STATUS IS CLOSED"],
            },
        ]

    def test_options(self):
        options = _standalone("Net1.inp")["options"]
        assert options["time"] == {
            "duration": 86400,
            "hydraulic_timestep": 3600,
            "quality_timestep": 300,
            "rule_timestep": 360,
            "pattern_timestep": 7200,
            "pattern_start": 0,
            "report_timestep": 3600,
            "report_start": 0,
            "start_clocktime": 0,
            "statistic": "NONE",
            "pattern_interpolation": False,
        }
        hydraulic = options["hydraulic"]
        assert hydraulic["headloss"] == "H-W"
        assert hydraulic["pattern"] == "1"
        assert hydraulic["demand_model"] == "DD"
        assert hydraulic["trials"] == 40
        assert hydraulic["accuracy"] == 0.001
        assert hydraulic["unbalanced"] == "CONTINUE"
        assert hydraulic["unbalanced_value"] == 10
        assert hydraulic["checkfreq"] == 2.0
        assert hydraulic["maxcheck"] == 10.0
        assert hydraulic["damplimit"] == 0.0
        assert hydraulic["headerror"] == 0
        assert hydraulic["flowchange"] == 0
        assert hydraulic["inpfile_units"] == "GPM"
        assert options["quality"]["parameter"] == "CHEMICAL"
        assert options["quality"]["chemical_name"] == "Chlorine"
        assert options["quality"]["inpfile_units"] == "mg/L"
        assert options["energy"] == {
            "global_price": 0.0,
            "global_pattern": None,
            "global_efficiency": 75.0,
            "demand_charge": 0.0,
        }
        assert options["reaction"] == {
            "bulk_order": 1,
            "wall_order": 1,
            "tank_order": 1,
            "bulk_coeff": -5.787037037037037e-06,
            "wall_coeff": -3.527777777777778e-06,
            "limiting_potential": 0.0,
            "roughness_correl": 0.0,
        }
        assert set(options["report"]) == {
            "pagesize",
            "report_filename",
            "status",
            "summary",
            "energy",
            "nodes",
            "links",
            "report_params",
            "param_opts",
        }


class TestCurves:
    def test_anytown_curves(self):
        curves = {c["name"]: c for c in _standalone("Anytown.inp")["curves"]}
        assert curves["1"] == {
            "name": "1",
            "curve_type": "HEAD",
            "points": [
                (0.0, 91.44),
                (0.1261803928, 89.00160000000001),
                (0.2523607856, 82.296),
                (0.3785411784, 70.104),
                (0.5047215712, 55.168800000000005),
            ],
        }
        assert curves["E1"]["curve_type"] == "EFFICIENCY"

    def test_anytown_pump_82_embeds_efficiency_curve(self):
        l = {x["name"]: x for x in _standalone("Anytown.inp")["links"]}["82"]
        assert l["pump_curve_name"] == "1"
        assert l["efficiency_curve_name"] == "E1"
        assert l["efficiency_curve"] == {
            "name": "E1",
            "curve_type": "EFFICIENCY",
            "points": [
                (0.0, 0.0),
                (0.1261803928, 50.0),
                (0.2523607856, 65.0),
                (0.3785411784, 55.0),
                (0.5047215712, 40.0),
            ],
        }


class TestSources:
    def test_net2_source(self):
        assert _standalone("Net2.inp")["sources"] == [
            {
                "name": "INP1",
                "node_name": "1",
                "source_type": "CONCEN",
                "strength": 0.001,
                "pattern": "3",
            }
        ]


class TestNet3Controls:
    def test_controls(self):
        controls = _standalone("Net3.inp")["controls"]
        assert controls[0] == {
            "type": "simple",
            "condition": "SYSTEM TIME IS 01:00:00",
            "then_actions": ["PUMP 10 STATUS IS OPEN"],
        }
        assert controls[13] == {
            "type": "simple",
            "condition": "SYSTEM TIME IS 159:00:00",
            "then_actions": ["PUMP 10 STATUS IS CLOSED"],
        }
        assert controls[-2] == {
            "type": "simple",
            "condition": "TANK 1 LEVEL BELOW 5.21208",
            "then_actions": ["PIPE 330 STATUS IS CLOSED"],
        }
        assert controls[-1] == {
            "type": "simple",
            "condition": "TANK 1 LEVEL ABOVE 5.821680000000001",
            "then_actions": ["PIPE 330 STATUS IS OPEN"],
        }


class TestNet6Values:
    def test_power_pump(self):
        l = {x["name"]: x for x in _standalone("Net6.inp")["links"]}["PUMP-3889"]
        assert l["pump_type"] == "POWER"
        assert l["power"] == 11185.498080000001
        assert l["pump_curve_name"] is None
        assert l["base_speed"] == 1.0
        assert l["initial_status"] == "Open"

    def test_prv_valve(self):
        l = {x["name"]: x for x in _standalone("Net6.inp")["links"]}["VALVE-3890"]
        assert l["link_type"] == "Valve"
        assert l["valve_type"] == "PRV"
        assert l["diameter"] == 0.15239999999999998
        assert l["headloss_curve_name"] is None
        assert l["initial_setting"] == 35.171936302792524
        assert l["initial_status"] == "Active"
        assert l["minor_loss"] == 0.0
        assert l["tag"] is None
        assert l["vertices"] == []
