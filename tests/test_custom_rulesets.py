"""Tests for custom rulesets, applied without touching the component classes.

The claim being tested is specific: a user can add validation to an existing
model without modifying a component class, subclassing one, or registering
anything globally. A custom ruleset is a module of ``assert``-based functions
that the registry finds, and that is the entire integration surface.

If this file's tests start needing to subclass something, the design has
regressed towards the inheritance-based extension it replaced.
"""
import inspect

from epanetparser.core.epanettypes import (
    WNTREPANETControl,
    WNTREPANETLink,
    WNTREPANETNode,
    WNTREPANETOptions,
    WNTREPANETPattern,
)
from epanetparser.core.validation import (
    RuleSetRegistry,
    ValidationContext,
    Validator,
    get_validator,
)
from epanetparser.custom_rules import milp


def test_no_component_class_declares_a_rule():
    """No component class carries a rule or warning method."""
    from epanetparser.core.epanettypes import (
        WNTREPANETControl,
        WNTREPANETCurve,
        WNTREPANETNetworkInfo,
        WNTREPANETOptions,
        WNTREPANETPattern,
        WNTREPANETSource,
    )

    for cls in (
        WNTREPANETNode,
        WNTREPANETLink,
        WNTREPANETControl,
        WNTREPANETCurve,
        WNTREPANETPattern,
        WNTREPANETSource,
        WNTREPANETOptions,
        WNTREPANETNetworkInfo,
    ):
        offenders = [
            name
            for name in dir(cls)
            if name.startswith(("rule_", "warn_"))
        ]
        assert not offenders, f"{cls.__name__} declares {offenders}"


def test_no_component_class_is_a_ruleset_subclass():
    """Component classes are not bases any ruleset extends."""
    for ruleset in RuleSetRegistry().all():
        for module_name in (
            ruleset.module_path,
        ):
            module = __import__(module_name, fromlist=["*"])
            for _, value in vars(module).items():
                if not inspect.isclass(value):
                    continue
                if value.__module__.split(".")[0] != "epanetparser.core.epanettypes":
                    continue
                assert not issubclass(value, WNTREPANETNode) or value is WNTREPANETNode
                assert not issubclass(value, WNTREPANETLink) or value is WNTREPANETLink
                assert not issubclass(value, WNTREPANETOptions) or value is (
                    WNTREPANETOptions
                )
                assert not issubclass(value, WNTREPANETPattern) or value is (
                    WNTREPANETPattern
                )
                assert not issubclass(value, WNTREPANETControl) or value is (
                    WNTREPANETControl
                )


def test_the_custom_ruleset_declares_no_classes():
    """The MILP ruleset is functions, not types."""
    classes = [
        name
        for name, value in vars(milp).items()
        if inspect.isclass(value) and value.__module__ == milp.__name__
    ]
    assert classes == []


def test_the_custom_ruleset_is_not_flagged_core():
    """A custom ruleset is identified by the absence of __is_core__."""
    assert not hasattr(milp, "__is_core__")
    assert RuleSetRegistry().get("milp").is_core is False


class TestSelectionWithoutInheritance:
    """Selecting a custom ruleset is all that is required."""

    def test_a_model_can_be_valid_for_core_and_invalid_for_a_custom_ruleset(self):
        """This is the property inheritance-based extension could not express.

        The same object is simultaneously a well-formed EPANET model and
        unusable by one application. Under an inheritance design the two
        verdicts would have to come from two different classes, and the model
        could only be one of them.
        """
        valve = WNTREPANETLink({"name": "PRV1", "link_type": "Valve"})
        assert valve.validate().is_valid
        assert not valve.validate(["epanet_core", "milp"]).is_valid

    def test_a_custom_ruleset_adds_findings_to_the_same_report(self):
        """Core and custom findings arrive together, each attributed."""
        valve = WNTREPANETLink(
            {"name": "PRV1", "link_type": "Valve", "check_valve": True}
        )
        report = valve.validate(["epanet_core", "milp"])
        by_ruleset = {}
        for issue in report:
            by_ruleset.setdefault(issue.ruleset_key, []).append(issue.code)
        assert by_ruleset["milp"] == ["E_MILP_CHECK_VALVE", "E_MILP_VALVE"]
        assert "epanet_core" not in by_ruleset

    def test_several_custom_rulesets_can_be_applied_at_once(self, minimal_network):
        """More than one application ruleset can constrain the same model.

        The mock package supplies a core ruleset and two custom ones, so this
        exercises the selection path without depending on which custom rulesets
        happen to ship with the package.
        """
        registry = RuleSetRegistry(packages=["tests.mock_rulesets"])
        context = ValidationContext(
            core="basic", custom=["advanced", "extra"], registry=registry
        )
        report = minimal_network.validate(context)
        rulesets = {issue.ruleset_key for issue in report}
        assert rulesets == {"advanced", "extra"}
        # The advanced ruleset rejects everything but a node named J1, and no
        # links at all, so the model is invalid on its account alone.
        assert not report.is_valid
        assert "E_ADVANCED_NO_LINKS" in report.codes()
        assert "E_ADVANCED_NODE_NAME" in report.codes()

    def test_a_custom_ruleset_can_sit_beside_the_real_core_ruleset(
        self, minimal_network
    ):
        """Custom rulesets compose with the shipped core ruleset, not replace it.

        The registry is seeded with the mock custom rulesets and the real core
        ruleset, which is the situation a project is in when it has written its
        own rules but still wants the standard checks.
        """
        mock = RuleSetRegistry(packages=["tests.mock_rulesets"])
        real = RuleSetRegistry()
        seeded = RuleSetRegistry(rulesets=[real.get("epanet_core"), *mock.all()])
        context = ValidationContext(
            core="epanet_core", custom=["extra"], registry=seeded
        )
        report = minimal_network.validate(context)
        # The minimal model satisfies the core ruleset; the extra ruleset's
        # single-point-curve warning is the only finding.
        assert report.codes() == ["W_EXTRA_SINGLE_POINT_CURVE"]
        assert report.issues[0].ruleset_key == "extra"

    def test_a_custom_ruleset_can_be_applied_to_whole_networks(self):
        """A custom ruleset reaches every component, not just one instance."""
        from tests.conftest import build_network

        network = build_network(
            {
                "name": "with-valve",
                "version": "v",
                "options": {"time": {}, "hydraulic": {}, "energy": {}},
                "nodes": [
                    {"name": "A", "node_type": "Reservoir", "base_head": 10.0},
                    {"name": "B", "node_type": "Reservoir", "base_head": 10.0},
                ],
                "links": [
                    {
                        "name": "V1",
                        "link_type": "Valve",
                        "start_node_name": "A",
                        "end_node_name": "B",
                    }
                ],
            }
        )
        assert network.validate().is_valid
        report = network.validate(["epanet_core", "milp"])
        assert "E_MILP_VALVE" in report.codes()

    def test_a_custom_rule_sees_the_component_it_names(self):
        """A rule is handed the component, so it can read the component's API."""
        seen = []

        validator = Validator.from_context(["epanet_core", "milp"])
        rules = validator.rules_for(
            WNTREPANETNode({"name": "T1", "node_type": "Tank", "emitter_coefficient": 0.5})
        )
        for _, spec in rules:
            seen.append(spec.rule_id)
        assert "rule_no_emitters" in seen
        assert "rule_tank_has_diameter" in seen


class TestMilpRuleSet:
    """The bundled MILP ruleset, which is the worked example of a custom one."""

    def test_pattern_length_follows_the_schedule_resolution(self):
        """A pattern must hold one multiplier per scheduling period."""
        twelve = WNTREPANETPattern({"name": "1", "multipliers": [1.0] * 12})
        assert twelve.validate(["epanet_core", "milp"]).is_valid
        eleven = WNTREPANETPattern({"name": "1", "multipliers": [1.0] * 11})
        report = eleven.validate(["epanet_core", "milp"])
        issue = report.by_code("E_MILP_PATTERN_LENGTH")[0]
        assert issue.attribute == "multipliers"
        assert "11 multipliers" in issue.message
        assert "12" in issue.message

    def test_tank_volume_curves_and_overflow_are_rejected(self):
        """The formulation models tanks as cylinders and does not allow spilling."""
        overflow = WNTREPANETNode(
            {
                "name": "T1",
                "node_type": "Tank",
                "diameter": 10.0,
                "elevation": 1.0,
                "init_level": 1.0,
                "max_level": 2.0,
                "min_level": 0.0,
                "min_vol": 0.0,
                "coordinates": [0.0, 0.0],
                "overflow": True,
            }
        )
        assert overflow.validate().is_valid
        assert "E_MILP_TANK_OVERFLOW" in overflow.validate(
            ["epanet_core", "milp"]
        ).codes()

    def test_a_zero_emitter_is_allowed(self):
        """An emitter coefficient of zero is not an emitter."""
        node = WNTREPANETNode(
            {
                "name": "J1",
                "node_type": "Junction",
                "elevation": 1.0,
                "coordinates": [0.0, 0.0],
                "emitter_coefficient": 0.0,
            }
        )
        assert "E_MILP_EMITTER" not in node.validate(["epanet_core", "milp"]).codes()

    def test_a_nonzero_emitter_is_rejected(self):
        """An emitter is an unbounded demand the formulation cannot express."""
        node = WNTREPANETNode(
            {
                "name": "J1",
                "node_type": "Junction",
                "elevation": 1.0,
                "coordinates": [0.0, 0.0],
                "emitter_coefficient": 0.01,
            }
        )
        assert "E_MILP_EMITTER" in node.validate(["epanet_core", "milp"]).codes()

    def test_controls_are_rejected(self):
        """The formulation decides pump states itself."""
        control = WNTREPANETControl({"type": "simple", "condition": "TIME > 8"})
        assert control.validate().is_valid
        assert "E_MILP_CONTROL" in control.validate(["epanet_core", "milp"]).codes()

    def test_option_constraints_are_reported_per_setting(self):
        """Each solver assumption is its own finding, named by field."""
        options = WNTREPANETOptions(
            {
                "time": {"duration": 3600.0, "hydraulic_timestep": 60,
                         "pattern_timestep": 60},
                "hydraulic": {
                    "headloss": "C-M",
                    "viscosity": 1.5,
                    "specific_gravity": 0.9,
                    "demand_model": "PDD",
                    "inpfile_pressure_units": "PSI",
                },
                "energy": {"demand_charge": 1.0},
            }
        )
        codes = options.validate(["epanet_core", "milp"]).codes()
        assert "E_MILP_TIME_HORIZON" in codes
        assert "E_MILP_TIMESTEP" in codes
        assert "E_MILP_PATTERN_TIMESTEP" in codes
        assert "E_MILP_HEADLOSS_MODEL" in codes
        assert "E_MILP_VISCOSITY" in codes
        assert "E_MILP_SPECIFIC_GRAVITY" in codes
        assert "E_MILP_DEMAND_MODEL" in codes
        assert "E_MILP_PRESSURE_UNITS" in codes
        assert "E_MILP_DEMAND_CHARGE" in codes

    def test_a_unit_mismatch_only_warns(self):
        """An input file in other units is still simulable, so this is a warning.

        Treating it as an error would reject models that work. Reporting it
        keeps the mismatch visible without refusing the model.
        """
        options = WNTREPANETOptions(
            {
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
                    "inpfile_units": "GPM",
                    "inpfile_pressure_units": None,
                },
                "energy": {"demand_charge": 0.0},
            }
        )
        report = options.validate(["epanet_core", "milp"])
        issue = report.by_code("W_MILP_INPFILE_UNITS")[0]
        assert issue.severity.name == "WARNING"
        assert report.is_valid

    def test_the_bundled_milp_model_passes_both_rulesets(self, valid_network_milp):
        """The test data ships a model that satisfies the core and MILP rules."""
        report = valid_network_milp.validate(["epanet_core", "milp"])
        assert report.is_valid
        assert report.errors == []

    def test_the_bundled_invalid_milp_model_fails_only_milp(self, invalid_network_milp):
        """A model can be well-formed and still violate an application ruleset."""
        assert invalid_network_milp.validate().is_valid
        report = invalid_network_milp.validate(["epanet_core", "milp"])
        assert not report.is_valid
        assert {issue.ruleset_key for issue in report.errors} == {"milp"}


class TestValidatorsAreShared:
    """Validators are cached, so applying a ruleset repeatedly is cheap."""

    def test_equal_contexts_share_a_validator(self):
        """The same selection yields the same validator, not a new one each time."""
        left = get_validator(["epanet_core", "milp"])
        right = get_validator({"core": "epanet_core", "custom": ["milp"]})
        assert left is right

    def test_different_contexts_get_different_validators(self):
        """A different selection must not reuse the wrong rule sets."""
        assert get_validator("epanet_core") is not get_validator(
            ["epanet_core", "milp"]
        )

    def test_a_validator_holds_rules_not_results(self):
        """Reusing a validator does not carry findings over between runs."""
        validator = get_validator("epanet_core")
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction",
                               "coordinates": [0.0, 0.0]})
        first = validator.validate_component(node)
        second = validator.validate_component(node)
        assert first is not second
        assert first.codes() == second.codes()
