"""
Test fixtures for EPANET network parsing.

This module provides reusable fixtures for loading valid and
invalid EPANET network definitions from both JSON and INP files and expositing
WNTRJSONParser instances for testing execution on valid and invalid networks.

Fixtures
--------
valid_network_json_file : pathlib.Path
    Path to a valid EPANET network represented in JSON format.

valid_network_inp_file : pathlib.Path
    Path to a valid EPANET network represented in INP format.

invalid_network_json_file : pathlib.Path
    Path to an intentionally malformed or semantically invalid EPANET
    network in JSON format.

invalid_network_inp_file : pathlib.Path
    Path to an intentionally malformed or semantically invalid EPANET
    network in INP format.

valid_network : WNTRJSONParser
    Parsed representation of a valid EPANET network created from the
    JSON test file.

invalid_network : WNTRJSONParser
    Parsed representation of an invalid EPANET network created from the
    JSON test file. This fixture is intended for testing validation and
    error handling logic after parsing.

Notes
-----
The test data files are expected to reside in the local ``data/``
directory adjacent to this module. Parsed network fixtures invoke
``WNTRJSONParser.parse()`` before returning the parser instance, making
them suitable for tests that operate on an initialized network model.
"""

from pathlib import Path
import pytest
from epanetparser.core.parsers import WNTRJSONParser

TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR / "data"


@pytest.fixture
def valid_network_json_file() -> Path:
    """ Fixture for the path to a valid EPANET network JSON file. """
    return DATA_DIR / "valid_network.json"

@pytest.fixture
def valid_network_inp_file() -> Path:
    """ Fixture for the path to a valid EPANET network INP file. """
    return DATA_DIR / "valid_network.inp"

@pytest.fixture
def invalid_network_json_file() -> Path:
    """ Fixture for the path to an invalid EPANET network JSON file. """
    return DATA_DIR / "invalid_network.json"

@pytest.fixture
def invalid_network_inp_file() -> Path:
    """ Fixture for the path to an invalid EPANET network INP file. """
    return DATA_DIR / "invalid_network.inp"

@pytest.fixture
def valid_network(valid_network_json_file: Path) -> WNTRJSONParser:    # pylint: disable=redefined-outer-name
    """ Fixture for a parsed valid EPANET network from a JSON file. """
    with open(valid_network_json_file, 'r', encoding='utf-8') as fp:
        json_src = fp.read()
    parser = WNTRJSONParser(json_src)
    parser.parse()
    return parser

@pytest.fixture
def invalid_network(invalid_network_json_file: Path) -> WNTRJSONParser: # pylint: disable=redefined-outer-name
    """ Fixture for a parsed invalid EPANET network from a JSON file. """
    with open(invalid_network_json_file, 'r', encoding='utf-8') as fp:
        json_src = fp.read()
    parser = WNTRJSONParser(json_src)
    parser.parse()
    return parser
