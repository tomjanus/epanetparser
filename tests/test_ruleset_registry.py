"""Tests for rule set discovery and selection.

Rule set management is the part of validation that decides *what gets checked*.
Two properties matter and are tested here:

* discovery finds both core and custom rule sets, through one mechanism, and
  records the metadata that tells them apart;
* selection is constrained: exactly one core rule set, any number of custom
  ones, and nothing else accepted.

The tests use the mock rule sets in :mod:`tests.mock_rulesets` rather than the
bundled ones, so that what is discovered is known exactly. The bundled rule sets
are covered in ``test_custom_rulesets.py``.
"""
import pytest

from epanetparser.core.validation import (
    RuleSet,
    RuleSetRegistry,
    RuleSetSelectionError,
    ValidationContext,
    Validator,
    clear_caches,
    default_packages,
    discover_ruleset_modules,
)

MOCK_BASE = "tests.mock_rulesets"

#: The mock package's core rule set key.
MOCK_CORE = "basic"

#: Every key the mock package declares, sorted. Discovery returns keys sorted.
MOCK_KEYS = ["advanced", "basic", "extra"]

#: The mock package's custom rule set keys.
MOCK_CUSTOM = ("advanced", "extra")


@pytest.fixture
def registry() -> RuleSetRegistry:
    """A registry searching only the mock rule sets.

    Returns:
        RuleSetRegistry: A registry scoped to :data:`MOCK_BASE`.
    """
    return RuleSetRegistry(packages=[MOCK_BASE])


class TestDiscovery:
    """Finding rule sets."""

    def test_default_packages_cover_core_and_custom(self):
        """Both rule set packages are searched, and they are the only defaults."""
        packages = default_packages()
        assert "epanetparser.core_rules" in packages
        assert "epanetparser.custom_rules" in packages

    def test_discovers_every_rule_set_in_a_package(self, registry):
        """Each rule set module in a package is found, keyed by its declared key."""
        assert registry.keys() == MOCK_KEYS

    def test_discovery_is_shared_between_core_and_custom(self):
        """One pass finds both kinds; the metadata is what distinguishes them."""
        modules = discover_ruleset_modules()
        assert "epanet_core" in modules
        assert "milp" in modules
        assert modules["epanet_core"].__is_core__ is True
        assert not hasattr(modules["milp"], "__is_core__")

    def test_core_and_custom_are_classified_by_metadata(self, registry):
        """A module setting __is_core__ is core; one that does not is custom."""
        assert registry.core_keys() == [MOCK_CORE]
        assert registry.custom_keys() == sorted(MOCK_CUSTOM)

    def test_metadata_is_recorded(self, registry):
        """A rule set carries the metadata its module declared."""
        basic = registry.get(MOCK_CORE)
        assert basic.key == MOCK_CORE
        assert basic.name == "Basic Test Ruleset"
        assert basic.version == "1.0.0"
        assert basic.description
        assert basic.module_path == "tests.mock_rulesets.basic_ruleset"

    def test_a_rule_set_with_no_rules_is_still_discovered(self, registry):
        """Discovery reads metadata, not contents, so an empty rule set is found."""
        assert registry.get(MOCK_CORE).rule_count == 0

    def test_rules_are_collected_from_submodules(self, registry):
        """A rule set package contributes the rules of all its submodules."""
        advanced = registry.get("advanced")
        assert len(advanced.component_rules) == 4
        assert len(advanced.network_rules) == 1
        assert "rule_node_name_is_j1" in {s.rule_id for s in advanced.component_rules}

    def test_rules_are_collected_from_a_plain_module(self, registry):
        """A rule set that is a plain module contributes its own rules."""
        advanced = registry.get("advanced")
        assert advanced.rule_count == 5
        assert len({spec.rule_id for spec in advanced.component_rules}) == 4

    def test_unknown_key_is_rejected_with_the_available_keys(self, registry):
        """Asking for a rule set that does not exist says what does."""
        with pytest.raises(RuleSetSelectionError) as excinfo:
            registry.get("nonexistent")
        message = str(excinfo.value)
        assert "nonexistent" in message
        assert MOCK_CORE in message

    def test_a_broken_module_does_not_break_discovery(self, tmp_path):
        """A module that fails to import is skipped, not propagated."""
        broken = tmp_path / "broken_ruleset"
        broken.mkdir()
        (broken / "__init__.py").write_text("__key__ = 'broken'\n", encoding="utf-8")
        (broken / "boom.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
        found = RuleSetRegistry(packages=[str(broken)]).discover()
        assert found == {}

    def test_discovery_is_cached_until_refreshed(self, registry):
        """The scan happens once; a refresh re-runs it."""
        assert registry.keys() == MOCK_KEYS
        assert registry.discover() is not None
        assert registry.keys() == MOCK_KEYS


class TestRuleSet:
    """A discovered rule set's own behaviour."""

    def test_repr_and_str_are_informative(self, registry):
        """Printing a rule set says what it is and how much it checks."""
        advanced = registry.get("advanced")
        assert "advanced" in str(advanced)
        assert "custom" in str(advanced)
        assert "4 component" in str(advanced)

    def test_as_dict_lists_the_rules(self, registry):
        """Serialising a rule set lists every rule id it holds."""
        payload = registry.get("advanced").as_dict()
        assert payload["key"] == "advanced"
        assert payload["is_core"] is False
        component_rule_ids = [r["rule_id"] for r in payload["component_rules"]]
        network_rule_ids = [r["rule_id"] for r in payload["network_rules"]]
        assert "rule_node_name_is_j1" in component_rule_ids
        assert "rule_pattern_present" in network_rule_ids

    def test_from_module_rejects_a_non_ruleset(self):
        """A module without the required metadata is not a rule set."""
        from types import ModuleType

        with pytest.raises(RuleSetSelectionError) as excinfo:
            RuleSet.from_module(ModuleType("not_a_ruleset"))
        assert "__key__" in str(excinfo.value)


class TestSelection:
    """Choosing which rule sets run."""

    def test_exactly_one_core_rule_set_is_required(self, registry):
        """A selection with no core rule set is rejected."""
        with pytest.raises(RuleSetSelectionError) as excinfo:
            registry.resolve(ValidationContext(core=None, registry=registry))
        assert "core" in str(excinfo.value).lower()

    def test_more_than_one_core_rule_set_is_rejected(self, registry):
        """A selection naming two core rule sets is rejected rather than guessed."""
        context = ValidationContext(
            core=[MOCK_CORE, "advanced"], registry=registry
        )
        with pytest.raises(RuleSetSelectionError) as excinfo:
            registry.resolve(context)
        assert "2 were requested" in str(excinfo.value)

    def test_a_core_rule_set_cannot_be_selected_as_custom(self, registry):
        """Core and custom are separate roles, not two labels for one thing."""
        context = ValidationContext(
            core=MOCK_CORE, custom=[MOCK_CORE], registry=registry
        )
        with pytest.raises(RuleSetSelectionError) as excinfo:
            registry.resolve(context)
        assert "cannot be selected as a custom" in str(excinfo.value)

    def test_a_custom_rule_set_cannot_be_selected_as_core(self, registry):
        """Naming a custom rule set as the core one is refused, not silently used."""
        context = ValidationContext(core="advanced", registry=registry)
        with pytest.raises(RuleSetSelectionError) as excinfo:
            registry.resolve(context)
        assert "not a core rule set" in str(excinfo.value)

    def test_unknown_keys_are_rejected(self, registry):
        """A selection naming a rule set that was never discovered fails."""
        context = ValidationContext(
            core=MOCK_CORE, custom=["missing"], registry=registry
        )
        with pytest.raises(RuleSetSelectionError):
            registry.resolve(context)

    def test_one_core_and_one_custom_resolve_in_order(self, registry):
        """The core rule set comes first so its findings are reported first."""
        context = ValidationContext(
            core=MOCK_CORE, custom=["advanced"], registry=registry
        )
        selected = registry.resolve(context)
        assert [ruleset.key for ruleset in selected] == [MOCK_CORE, "advanced"]
        assert selected[0].is_core is True
        assert selected[1].is_core is False

    def test_one_core_and_many_custom_resolve_in_requested_order(self, registry):
        """Several custom rule sets can be selected alongside the core one."""
        context = ValidationContext(
            core=MOCK_CORE, custom=["extra", "advanced"], registry=registry
        )
        selected = registry.resolve(context)
        assert [ruleset.key for ruleset in selected] == [
            MOCK_CORE,
            "extra",
            "advanced",
        ]

    def test_core_alone_resolves(self):
        """The default selection is the core rule set and nothing else."""
        selected = RuleSetRegistry().resolve(ValidationContext())
        assert [ruleset.key for ruleset in selected] == ["epanet_core"]

    def test_describe_lists_every_rule_set(self, registry):
        """The listing says what exists, where it came from and how big it is."""
        text = registry.describe()
        assert MOCK_CORE in text
        assert "advanced" in text and "extra" in text
        assert "tests.mock_rulesets" in text


class TestValidationContext:
    """Coercing a loose rule set selection into a context."""

    def test_none_selects_the_core_rule_set(self):
        """No context means the core rule set alone."""
        assert ValidationContext.from_any(None).ruleset_keys == ("epanet_core",)

    def test_a_string_selects_the_core_rule_set(self):
        """A single key names the core rule set."""
        assert ValidationContext.from_any("milp").ruleset_keys == ("milp",)

    def test_a_sequence_names_core_then_custom(self):
        """A list of keys is read as core first, then custom."""
        context = ValidationContext.from_any(["epanet_core", "milp"])
        assert context.core_keys == ("epanet_core",)
        assert context.custom == ("milp",)

    def test_a_mapping_is_read_field_by_field(self):
        """A mapping lets a caller name the roles explicitly."""
        context = ValidationContext.from_any({"custom": ["milp"]})
        assert context.ruleset_keys == ("epanet_core", "milp")

    def test_a_context_passes_through(self):
        """Coercing a context to a context returns it unchanged."""
        context = ValidationContext(core="epanet_core")
        assert ValidationContext.from_any(context) is context

    def test_an_uninterpretable_selection_is_rejected(self):
        """A value that names no rule sets at all fails loudly."""
        with pytest.raises(TypeError):
            ValidationContext.from_any(42)

    def test_unknown_mapping_keys_are_rejected(self):
        """A mapping with a misspelled key fails rather than being ignored."""
        with pytest.raises(TypeError) as excinfo:
            ValidationContext.from_any({"core_rules": ["milp"]})
        assert "core_rules" in str(excinfo.value)

    def test_equality_and_repr(self):
        """Contexts with the same selection are equal and print readably."""
        left = ValidationContext(core="epanet_core", custom=["milp"])
        right = ValidationContext(core="epanet_core", custom=["milp"])
        assert left == right
        assert "milp" in repr(left)
        assert "milp" in str(left)


class TestValidatorConstruction:
    """Turning a context into a validator."""

    def test_validator_needs_at_least_one_rule_set(self):
        """A validator with nothing to run is a programming error."""
        with pytest.raises(RuleSetSelectionError):
            Validator([])

    def test_from_context_records_the_selected_keys(self):
        """A validator knows which rule sets it will run."""
        validator = Validator.from_context(["epanet_core", "milp"])
        assert validator.ruleset_keys == ("epanet_core", "milp")
        assert "epanet_core" in repr(validator)

    def test_a_context_registry_is_used_for_resolution(self, registry):
        """A context carrying a registry resolves against that registry, not the default."""
        context = ValidationContext(core=MOCK_CORE, custom=["advanced"], registry=registry)
        validator = Validator.from_context(context)
        assert validator.ruleset_keys == (MOCK_CORE, "advanced")


class TestCacheInvalidation:
    """Discarding discovered rule sets."""

    def test_caches_can_be_cleared_and_refilled(self):
        """After clearing, discovery runs again and finds the same rule sets."""
        try:
            assert RuleSetRegistry().keys() == ["epanet_core", "milp"]
            clear_caches()
            assert RuleSetRegistry().keys() == ["epanet_core", "milp"]
        finally:
            clear_caches()
