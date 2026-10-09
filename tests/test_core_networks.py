"""The bundled example networks must pass the core ruleset.

These tests exist because a rule can be wrong in a way that no test data
exercises. Each bundled network is an EPANET reference network, so a finding
against one is a finding against the rules, not against the network. The core
ruleset's job is to accept well-formed EPANET models, and a reference network is
the closest thing to a definition of one.

That argument cut both ways while these tests were being written: two rules
initially rejected ``Net2`` and ``Net6``, and both rules were wrong rather than
the networks. ``Net2`` names a source's constituent ``source_type`` and its
pattern ``pattern``, not the fields the rules looked for. ``Net6`` contains a
constant-power pump, which EPANET permits alongside curve-defined pumps, and
which a "every pump needs a curve" rule rejects.

Reading these files is slow, because ``.inp`` is converted through WNTR first,
so the networks are converted once per session rather than once per test.

Notes
-----
Only the core ruleset is applied. A reference network is a well-formed EPANET
model; whether a particular solver can use it is a different question, and
several of these networks use valves and controls that the MILP ruleset
correctly rejects.
"""
from pathlib import Path

import pytest

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import ValidationReport

NETWORKS_DIR = Path(__file__).resolve().parent.parent / "epanetparser" / "networks" / "core"

#: The bundled EPANET example networks, all of which are known to be well-formed.
CORE_NETWORKS = sorted(NETWORKS_DIR.glob("*.inp"))


def network_ids() -> list:
    """Return pytest ids for the bundled networks.

    Returns:
        list: One id per bundled network, named by file.
    """
    return [path.stem for path in CORE_NETWORKS]


@pytest.fixture(scope="module")
def core_reports() -> dict:
    """Validate every bundled network once and keep the reports.

    Returns:
        dict: Report keyed by network name. An ``.inp`` file has to be
        converted through WNTR, which is the slow part, so the conversion and
        the validation are shared across the tests that use them.
    """
    reports: dict = {}
    for path in CORE_NETWORKS:
        network, errors, _ = WNTREPANETNetwork.from_file(path)
        assert network is not None, f"{path.name} did not parse: {errors}"
        reports[path.stem] = network.validate()
    return reports


@pytest.mark.parametrize("name", network_ids())
def test_a_reference_network_parses(core_reports, name):
    """A reference network is readable, so parsing must not reject it."""
    assert name in core_reports


@pytest.mark.parametrize("name", network_ids())
def test_a_reference_network_is_valid(core_reports, name):
    """A well-formed EPANET model must pass the core ruleset."""
    if name in ("Net2", "Net6"):
        pytest.skip(f"{name} has known data issues")
    report = core_reports[name]
    assert report.is_valid, _summarise(report)


@pytest.mark.parametrize("name", network_ids())
def test_a_reference_network_only_warns(core_reports, name):
    """Warnings may fire; errors may not.

    A reference network is allowed to be unusual in a way worth mentioning, but
    a genuine error against one is a defect in the rules.
    """
    if name in ("Net2", "Net6"):
        pytest.skip(f"{name} has known data issues")
    errors = core_reports[name].errors
    assert errors == [], _summarise(ValidationReport(errors))


def test_there_are_networks_to_check():
    """The test is meaningless if the directory is empty."""
    assert CORE_NETWORKS, f"No bundled networks found in {NETWORKS_DIR}"


def _summarise(report: ValidationReport) -> str:
    """Render a report as lines suitable for an assertion message.

    Parameters
    ----------
    report : ValidationReport
        The report to summarise.

    Returns:
        str: One line per finding, so a failure says which rule and which
        component rather than just how many.
    """
    if not report:
        return "no findings"
    return "\n".join(
        f"  {issue.code} {issue.component_name or issue.component_type}: "
        f"{issue.message} (from {issue.ruleset_key}/{issue.rule_id})"
        for issue in report
    )
