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

