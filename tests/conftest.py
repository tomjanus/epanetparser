import copy
import json
import os
from pathlib import Path

import pytest

from epanetparser.core.epanettypes.network import WNTREPANETNetwork

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"
NETWORKS_DIR = Path(os.environ.get("EPANET_NETWORKS_DIR", TEST_DIR / "networks"))

#: A two-node, one-pipe model with everything the core ruleset requires and
#: nothing that could make a test fail for an incidental reason.
MINIMAL_NETWORK: dict = {
    "name": "minimal",
    "version": "wntr-1.4.0",
    "comment": "",
    "references": [],
    "options": {
        "time": {
            "duration": 86400.0,
            "hydraulic_timestep": 3600,
            "quality_timestep": 3600,
            "pattern_timestep": 7200,
            "report_timestep": 3600,
            "rule_timestep": 3600,
        },
        "hydraulic": {
            "headloss": "H-W",
            "viscosity": 1.0,
            "specific_gravity": 1.0,
            "demand_model": "DDA",
            "inpfile_units": "LPS",
            "inpfile_pressure_units": None,
        },
        "energy": {"global_efficiency": 75.0, "demand_charge": 0.0},
    },
    "curves": [
        {"name": "1", "curve_type": "HEAD", "points": [[0.0, 100.0], [1.0, 50.0]]},
        {"name": "2", "curve_type": "HEAD", "points": [[0.0, 80.0]]}
    ],
    "patterns": [{"name": "1", "multipliers": [1.0] * 12}],
    "nodes": [
        {
            "name": "J1",
            "node_type": "Junction",
            "elevation": 10.0,
            "coordinates": [0.0, 0.0],
            "demand_pattern": "1",
        },
        {
            "name": "R1",
            "node_type": "Reservoir",
            "base_head": 50.0,
            "coordinates": [10.0, 0.0],
        },
    ],
    "links": [
        {
            "name": "P1",
            "link_type": "Pipe",
            "start_node_name": "R1",
            "end_node_name": "J1",
            "length": 100.0,
            "diameter": 0.1,
            "roughness": 100.0,
            "check_valve": False,
        }
    ],
    "sources": [],
    "controls": [],
}


@pytest.fixture
def minimal_network_json() -> str:
    """A small valid model, as JSON text, for tests that need exact control."""
    import json

    return json.dumps(MINIMAL_NETWORK)


@pytest.fixture
def minimal_network(minimal_network_json: str):
    """A small parsed model, valid by construction."""
    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    network, errors, _ = WNTREPANETNetwork.from_json(minimal_network_json)
    assert network is not None, f"Failed to parse the minimal model: {errors}"
    return network


@pytest.fixture
def minimal_network_dict() -> dict:
    """A mutable copy of the minimal model's fields.

    Tests that need an invalid model start from this and break one thing, so
    that a single defect explains the whole report.
    """
    import copy

    return copy.deepcopy(MINIMAL_NETWORK)


def build_network(source: dict):
    """Parse a model from a field dictionary.

    Parameters
    ----------
    source : Dict[str, Any]
        A model in WNTR's JSON shape.

    Returns:
        WNTREPANETNetwork: The parsed model.

    Raises:
        AssertionError: If the dictionary cannot be parsed.
    """
    import json

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    network, errors, _ = WNTREPANETNetwork.from_json(json.dumps(source))
    assert network is not None, f"Failed to parse the model: {errors}"
    return network


def component_names(components: list):
    """Return the names of a list of components.

    Parameters
    ----------
    components : List[Any]
        Components of any kind.

    Returns:
        List[str]: The components' names, in order.
    """
    return [getattr(component, "name", None) for component in components]



@pytest.fixture
def valid_network(valid_network_json_file: Path):
    """A parsed valid EPANET model."""
    return _network_from(valid_network_json_file)


@pytest.fixture
def valid_network_milp(valid_network_milp_json_file: Path):
    """A parsed model satisfying both the core and the MILP rulesets."""
    return _network_from(valid_network_milp_json_file)


@pytest.fixture
def invalid_network(invalid_network_json_file: Path):
    """A parsed model that the core ruleset rejects."""
    return _network_from(invalid_network_json_file)


@pytest.fixture
def invalid_network_milp(invalid_network_milp_json_file: Path):
    """A parsed model that only the MILP ruleset rejects."""
    return _network_from(invalid_network_milp_json_file)



@pytest.fixture
def valid_network_json_file() -> Path:
    """Path to a valid EPANET model in WNTR JSON format."""
    return DATA_DIR / "valid_network.json"


@pytest.fixture
def valid_network_milp_json_file() -> Path:
    """Path to a valid model that also satisfies the MILP ruleset."""
    return DATA_DIR / "valid_network_milp_ruleset.json"


@pytest.fixture
def invalid_network_json_file() -> Path:
    """Path to a model with defects the core ruleset reports."""
    return DATA_DIR / "invalid_network.json"


@pytest.fixture
def invalid_network_milp_json_file() -> Path:
    """Path to a model the core ruleset accepts and the MILP ruleset rejects."""
    return DATA_DIR / "invalid_network_milp_ruleset.json"



def _network_from(source: Path):
    """Parse a model file into a network.

    Parameters
    ----------
    path : pathlib.Path
        Path to a WNTR JSON model.

    Returns
    -------
    WNTREPANETNetwork: The parsed model. The fixture asserts, so a broken
    test-data file fails the test rather than producing None.
    """
    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    network, errors, _ = WNTREPANETNetwork.from_file(source)
    assert network is not None, f"Failed to parse {source.name}: {errors}"
    return network


@pytest.fixture
def minimal_valid_network():
    """A minimal valid EPANET network created programmatically.
    
    This network has all required fields populated and passes the core ruleset.
    """
    from epanetparser.core.epanettypes.network import WNTREPANETNetwork
    from epanetparser.core.epanettypes import (
        WNTREPANETNetworkInfo,
        WNTREPANETOptions,
        WNTREPANETJunction,
        WNTREPANETReservoir,
        WNTREPANETTank,
        WNTREPANETPipe,
        WNTREPANETPump,
        WNTREPANETValve,
        WNTREPANETPattern,
        WNTREPANETCurve,
        WNTREPANETSource,
        WNTREPANETControl,
    )
    
    network = WNTREPANETNetwork()
    
    # Network info
    network.network_info = WNTREPANETNetworkInfo({
        "name": "minimal_valid",
        "version": "test-1.0",
        "comment": "Minimal valid network for testing",
        "references": [],
    })
    
    # Options
    network.options = WNTREPANETOptions({
        "time": {
            "duration": 86400.0,
            "hydraulic_timestep": 3600,
            "quality_timestep": 3600,
            "pattern_timestep": 3600,
            "pattern_start": 0.0,
            "report_timestep": 3600,
            "report_start": 0.0,
            "start_clocktime": 0.0,
            "statistic": "NONE",
        },
        "hydraulic": {
            "headloss": "H-W",
            "demand_model": "DDA",
            "inpfile_units": "LPS",
        },
        "report": {},
        "quality": {"parameter": "NONE"},
        "reaction": {},
        "energy": {},
    })
    
    # Pattern
    pattern = WNTREPANETPattern({
        "name": "1",
        "multipliers": [1.0] * 24,
    })
    network._pattern_registry["1"] = pattern
    network._patterns_list.append(pattern)
    
    # Junctions
    j1 = WNTREPANETJunction({
        "name": "J1",
        "node_type": "Junction",
        "elevation": 10.0,
        "base_demand": 0.0,
        "demand_pattern_name": "1",
        "coordinates": [0.0, 0.0],
    })
    network._node_registry["J1"] = j1
    network._nodes_list.append(j1)
    
    j2 = WNTREPANETJunction({
        "name": "J2",
        "node_type": "Junction",
        "elevation": 20.0,
        "base_demand": 10.0,
        "demand_pattern_name": "1",
        "coordinates": [100.0, 0.0],
    })
    network._node_registry["J2"] = j2
    network._nodes_list.append(j2)
    
    # Reservoir
    r1 = WNTREPANETReservoir({
        "name": "R1",
        "node_type": "Reservoir",
        "base_head": 50.0,
        "coordinates": [0.0, 100.0],
    })
    network._node_registry["R1"] = r1
    network._nodes_list.append(r1)
    
    # Tank
    t1 = WNTREPANETTank({
        "name": "T1",
        "node_type": "Tank",
        "elevation": 10.0,
        "init_level": 5.0,
        "min_level": 0.0,
        "max_level": 10.0,
        "diameter": 10.0,
        "min_vol": 0.0,
        "coordinates": [50.0, 50.0],
    })
    network._node_registry["T1"] = t1
    network._nodes_list.append(t1)
    
    # Pipe
    p1 = WNTREPANETPipe({
        "name": "P1",
        "link_type": "Pipe",
        "start_node_name": "R1",
        "end_node_name": "J1",
        "length": 100.0,
        "diameter": 0.3,
        "roughness": 100.0,
        "initial_status": "OPEN",
    })
    network._link_registry["P1"] = p1
    network._links_list.append(p1)
    
    p2 = WNTREPANETPipe({
        "name": "P2",
        "link_type": "Pipe",
        "start_node_name": "J1",
        "end_node_name": "J2",
        "length": 100.0,
        "diameter": 0.3,
        "roughness": 100.0,
        "initial_status": "OPEN",
    })
    network._link_registry["P2"] = p2
    network._links_list.append(p2)
    
    p3 = WNTREPANETPipe({
        "name": "P3",
        "link_type": "Pipe",
        "start_node_name": "J2",
        "end_node_name": "T1",
        "length": 100.0,
        "diameter": 0.3,
        "roughness": 100.0,
        "initial_status": "OPEN",
    })
    network._link_registry["P3"] = p3
    network._links_list.append(p3)
    
    # Pump
    pump1 = WNTREPANETPump({
        "name": "PUMP1",
        "link_type": "Pump",
        "start_node_name": "R1",
        "end_node_name": "T1",
        "pump_type": "POWER",
        "power": 50.0,
        "initial_status": "OPEN",
    })
    network._link_registry["PUMP1"] = pump1
    network._links_list.append(pump1)
    
    # Valve - removed to avoid E_PARALLEL_LINKS with P2
# v1 = WNTREPANETValve({
#     "name": "V1",
#     "link_type": "Valve",
#     "start_node_name": "J2",
#     "end_node_name": "J1",
#     "valve_type": "PRV",
#     "diameter": 0.2,
#     "initial_status": "ACTIVE",
#     "initial_setting": 30.0,
# })
# network._link_registry["V1"] = v1
# network._links_list.append(v1)
    
    # Curve
    curve1 = WNTREPANETCurve({
        "name": "C1",
        "curve_type": "HEAD",
        "points": [[0.0, 50.0], [10.0, 30.0]],
    })
    network._curve_registry["C1"] = curve1
    network._curves_list.append(curve1)
    
    # Source
    s1 = WNTREPANETSource({
        "name": "S1",
        "node_name": "J1",
        "source_type": "CONCEN",
        "strength": 1.0,
        "pattern": "1",
    })
    network._source_registry["S1"] = s1
    network._sources_list.append(s1)
    
    # Control
    c1 = WNTREPANETControl({
        "name": "C1",
        "type": "simple",
        "condition": "TIME 12:00",
        "then_actions": ["PUMP1 CLOSED"],
    })
    network._controls["C1"] = c1
    network._controls_list.append(c1)
    
    # Finalize registries
    network._node_registry._finalize_(network)
    network._link_registry._finalize_(network)
    network._pattern_registry._finalize_(network)
    network._curve_registry._finalize_(network)
    network._source_registry._finalize_(network)
    
    # Add rule_timestep to options to avoid E_TIME_RULE_TIMESTEP_POSITIVE
    network.options.data.setdefault("time", {})["rule_timestep"] = 3600
    
    return network

