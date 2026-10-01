"""Test fixtures for EPANET model loading and validation.

The fixtures here build models from the JSON test data and expose them at three
levels, so that a test can work against whichever is most convenient: a path to
a file, a parsed :class:`WNTRJSONParser`, or a
:class:`~epanetparser.core.epanettypes.network.WNTREPANETNetwork`.

Validation is a separate, explicit step, so no fixture validates. Tests that
want a report call ``network.validate()`` themselves, which keeps the ruleset
selection under the test's control rather than the fixture's.

Fixtures
--------
valid_network_json_file : pathlib.Path
    Path to a valid EPANET model in WNTR JSON format.

valid_network_milp_json_file : pathlib.Path
    Path to a valid EPANET model that also satisfies the MILP ruleset.

invalid_network_json_file : pathlib.Path
    Path to a model with defects the core ruleset reports.

invalid_network_milp_json_file : pathlib.Path
    Path to a model that is structurally fine but violates MILP constraints.

valid_network : WNTREPANETNetwork
    A parsed valid model.

valid_network_milp : WNTREPANETNetwork
    A parsed model that satisfies both the core and MILP rulesets.

invalid_network : WNTREPANETNetwork
    A parsed model that the core ruleset rejects.

invalid_network_milp : WNTREPANETNetwork
    A parsed model that the core ruleset accepts and the MILP ruleset rejects.

minimal_network_json : str
    A small hand-built model, valid by construction, for tests that need to
    control a model exactly rather than depend on a large fixture.

Notes
-----
The parser is imported lazily inside the fixtures. Importing it at module
level would run it before the test session is configured, and a broken
import would then fail collection for every test in the suite instead of
just the ones that need the parser.
"""
from pathlib import Path
from typing import Any, Dict, List

import pytest

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"

#: A two-node, one-pipe model with everything the core ruleset requires and
#: nothing that could make a test fail for an incidental reason.
MINIMAL_NETWORK: Dict[str, Any] = {
    "name": "minimal",
    "version": "wntr-1.4.0",
    "comment": "",
    "references": [],
    "options": {
        "time": {
            "duration": 86400.0,
            "hydraulic_timestep": 3600,
            "pattern_timestep": 7200,
        },
        "hydraulic": {
            "headloss": "H-W",
            "viscosity": 1.0,
            "specific_gravity": 1.0,
            "demand_model": "DDA",
            "inpfile_units": "LPS",
            "inpfile_pressure_units": None,
        },
        "energy": {"demand_charge": 0.0},
    },
    "curves": [{"name": "1", "curve_type": "HEAD", "points": [[0.0, 100.0]]}],
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


def _network_from(path: Path):
    """Parse a model file into a network.

    Parameters
    ----------
    path : pathlib.Path
        Path to a WNTR JSON model.

    Returns:
        WNTREPANETNetwork: The parsed model. The fixture asserts, so a broken
        test-data file fails the test rather than producing None.
    """
    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    network, errors, _ = WNTREPANETNetwork.from_file(path)
    assert network is not None, f"Failed to parse {path.name}: {errors}"
    return network


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
def minimal_network_dict() -> Dict[str, Any]:
    """A mutable copy of the minimal model's fields.

    Tests that need an invalid model start from this and break one thing, so
    that a single defect explains the whole report.
    """
    import copy

    return copy.deepcopy(MINIMAL_NETWORK)


def build_network(source: Dict[str, Any]):
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


def component_names(components: List[Any]) -> List[str]:
    """Return the names of a list of components.

    Parameters
    ----------
    components : List[Any]
        Components of any kind.

    Returns:
        List[str]: The components' names, in order.
    """
    return [getattr(component, "name", None) for component in components]
