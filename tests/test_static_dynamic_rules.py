"""Tests for the static/dynamic layer split.

Three claims are covered:

* ``milp`` is a mixed module: one rule set contributing static component
  rules and a simulation rule, discovered through one mechanism;
* the milp dynamic rule judges timestep coverage from the results object
  alone, so it is testable with a stub and needs no WNTR;
* the Pandera schema checks run when pandera is installed and are skipped
  when it is not.
"""
from types import SimpleNamespace

import pytest

from epanetparser.core.validation import RuleSetRegistry, Validator
from epanetparser.core_rules.core_dynamic.hydraulic import schemas
from epanetparser.custom_rules import milp


class _StubResults:
    """Minimal stand-in for a WNTR simulation results object.

    The milp dynamic rule reads only ``results.node["pressure"].shape``,
    so a stub exposing exactly that is enough to run it. No WNTR, no pandas.
    """

    def __init__(self, timesteps: int, *, with_pressure: bool = True) -> None:
        node = {}
        if with_pressure:
            node["pressure"] = SimpleNamespace(shape=(timesteps, 1))
        self.node = node
        self.link = {}


class TestMixedModule:
    """milp is one rule set with static and simulation rules."""

    def test_the_mixed_module_collects_both_kinds(self):
        """Component rules and the simulation rule belong to one rule set."""
        milp_ruleset = RuleSetRegistry().get("milp")
        component_ids = {
            spec.rule_id for spec in milp_ruleset.component_rules
        }
        assert "rule_pattern_length" in component_ids
        simulation_ids = {
            spec.rule_id for spec in milp_ruleset.simulation_rules
        }
        assert simulation_ids == {"rule_simulation_timestep_count"}

    def test_the_mixed_module_declares_the_static_layer(self):
        """The ruleset layer is static; its simulation rule is simulation."""
        milp_ruleset = RuleSetRegistry().get("milp")
        assert milp_ruleset.layer == "static"
        (spec,) = milp_ruleset.simulation_rules
        assert spec.layer == "simulation"
        assert spec.code == "E_MILP_SIMULATION_TIMESTEPS"
        assert list(spec.required_outputs) == ["node.pressure"]


class TestMilpDynamicRule:
    """The timestep-count rule, run against stub results."""

    def test_a_full_horizon_passes(self):
        """24 timesteps cover the 24 hour schedule horizon."""
        milp.rule_simulation_timestep_count(_StubResults(24))

    def test_a_longer_run_passes(self):
        """A run covering more than the horizon still has the period data."""
        milp.rule_simulation_timestep_count(_StubResults(25))

    def test_a_short_run_fails(self):
        """Fewer timesteps than the horizon leave periods without data."""
        with pytest.raises(AssertionError, match="12|24|timesteps"):
            milp.rule_simulation_timestep_count(_StubResults(12))

    def test_the_rule_reports_through_the_validator(self):
        """A short run becomes an E_MILP_SIMULATION_TIMESTEPS simulation issue."""
        validator = Validator.from_context(["epanet_core", "milp"])
        report = validator.validate_simulation(_StubResults(12))
        codes = [issue.code for issue in report]
        assert "E_MILP_SIMULATION_TIMESTEPS" in codes
        issue = next(
            issue
            for issue in report
            if issue.code == "E_MILP_SIMULATION_TIMESTEPS"
        )
        assert issue.validation_layer == "simulation"
        assert issue.ruleset_key == "milp"

    def test_the_rule_is_skipped_without_pressure_output(self):
        """No node.pressure table means the rule is skipped, not failed."""
        validator = Validator.from_context(["epanet_core", "milp"])
        report = validator.validate_simulation(_StubResults(12, with_pressure=False))
        assert "E_MILP_SIMULATION_TIMESTEPS" not in report.codes()


def _pandas_results(pressure_value: float):
    """WNTR-shaped stub results: dicts of components-x-timesteps frames."""
    pandas = pytest.importorskip("pandas")
    node = {
        name: pandas.DataFrame({"n1": [1.0] * 24, "n2": [1.0] * 24}).T
        for name in ("pressure", "demand", "head", "quality")
    }
    node["pressure"] = pandas.DataFrame(
        {"n1": [pressure_value] * 24, "n2": [pressure_value] * 24}
    ).T
    link = {
        name: pandas.DataFrame({"p1": [1.0] * 24}).T
        for name in ("flowrate", "velocity", "headloss", "setting")
    }
    link["status"] = pandas.DataFrame({"p1": ["Open"] * 24}).T
    return SimpleNamespace(node=node, link=link)


class TestPanderaSkipPath:
    """Schema checks run with pandera and are skipped without it."""

    def test_schema_failure_is_reported_when_pandera_is_present(self):
        """Negative pressure fails the schema and becomes E_SIMULATION_SCHEMA."""
        pytest.importorskip("pandera")
        validator = Validator.from_context(["epanet_core"])
        report = validator.validate_simulation(_pandas_results(-5.0))
        assert "E_SIMULATION_SCHEMA" in report.codes()
        issue = next(
            issue
            for issue in report
            if issue.code == "E_SIMULATION_SCHEMA"
        )
        assert issue.validation_layer == "simulation"

    def test_schema_checks_are_skipped_when_pandera_is_absent(self, monkeypatch):
        """Simulating a missing pandera skips the schema checks entirely."""
        monkeypatch.setattr(schemas, "PANDERA_AVAILABLE", False)
        validator = Validator.from_context(["epanet_core"])
        report = validator.validate_simulation(_pandas_results(-5.0))
        assert "E_SIMULATION_SCHEMA" not in report.codes()

    def test_schemas_available_reflects_the_import_guard(self, monkeypatch):
        """The helper reports what the guard found, and can be overridden."""
        pytest.importorskip("pandera")
        assert schemas.schemas_available() is True
        monkeypatch.setattr(schemas, "PANDERA_AVAILABLE", False)
        assert schemas.schemas_available() is False
