"""Tests for epanetparser.core.utils.

The module holds the pieces shared by the parser, the display layer and the
tests: the context manager that decides whether a finding is raised or
collected, the file digest that identifies a model, and the re-exports of the
rule and warning introspection helpers.

What is covered
---------------
raiseorpush
    Raising a finding instead of collecting it, and the interaction between
    error and warning handling.
sha256digest
    Correctness, determinism and chunking of the file digest.
Re-exports
    The rule and warning introspection helpers are importable from here, so a
    caller need not know which module defines them.

Notes
-----
The introspection tests build their own classes rather than using the EPANET
component classes, because the component classes deliberately carry no
``rule_*`` or ``warn_*`` methods. Validation rules live in rule sets now; these
helpers describe classes, and are used by the plugins command and by
documentation.
"""
from collections import defaultdict
from types import ModuleType

import pytest

from epanetparser.core.validation.introspection import MethodInfo
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle,
)
from epanetparser.core.utils import (
    discover_classes,
    discover_methods_in_class,
    get_rule_methods,
    get_warning_methods,
    raiseorpush,
    sha256digest,
)


@pytest.fixture
def rules_class():
    """A class carrying one rule and one warning, defined in a test module."""

    class Pipe:
        """A component with a rule and a warning."""

        def __init__(self, data=None):
            self.data = data or {}

        def rule_has_length(self):
            """Length must be present."""
            assert "length" in self.data, "Length is required"

        def warn_short_pipe(self):
            """Warn about a very short pipe."""
            assert self.data.get("length", 0) >= 10, "Pipe is very short"

    Pipe.__module__ = "tests.test_utils"
    return Pipe


def bundle(count: int = 1) -> WNTREPANETTypeValidationErrorBundle:
    """Build a validation error bundle for testing.

    Parameters
    ----------
    count : int
        Number of errors in the bundle.

    Returns:
        WNTREPANETTypeValidationErrorBundle: The bundle.
    """
    return WNTREPANETTypeValidationErrorBundle(
        "failures",
        [
            WNTREPANETTypeValidationError("Pipe", f"rule_{index}", "boom", "{}")
            for index in range(count)
        ],
    )


def destination():
    """Build a destination object for collected findings.

    Returns:
        An object with ``errors`` and ``warnings`` mappings.
    """
    return type(
        "Destination",
        (),
        {"errors": defaultdict(list), "warnings": defaultdict(list)},
    )()


class TestRaiseOrPush:
    """The context manager that raises or collects a finding."""

    def test_records_how_it_was_configured(self):
        """The manager keeps the settings it was given."""
        dest = destination()
        manager = raiseorpush("Node", True, True, dest)
        assert manager.component == "Node"
        assert manager.raise_error is True
        assert manager.raise_warning is True
        assert manager.dest is dest

    def test_enter_returns_the_manager(self):
        """Binding the context yields the manager itself."""
        manager = raiseorpush("Node", False, False, destination())
        with manager as entered:
            assert entered is manager

    def test_collects_a_bundle_when_not_raising(self):
        """A bundle is pushed onto the destination, keyed by component."""
        dest = destination()
        with raiseorpush("Node", raise_error=False, raise_warning=False, dest=dest):
            raise bundle(2)
        assert len(dest.errors["Node"]) == 2

    def test_suppresses_the_exception_when_collecting(self):
        """Collecting means the caller carries on."""
        dest = destination()
        with raiseorpush("Node", raise_error=False, raise_warning=False, dest=dest):
            raise bundle()
        assert dest.errors

    def test_raises_the_first_error_when_asked_to(self):
        """Raising surfaces one error rather than the whole bundle."""
        with pytest.raises(WNTREPANETTypeValidationError):
            with raiseorpush("Node", raise_error=True, raise_warning=False,
                             dest=destination()):
                raise bundle(3)

    def test_raising_on_warnings_implies_raising_on_errors(self):
        """A model that is being rejected anyway should not also be collected."""
        with pytest.raises(WNTREPANETTypeValidationError):
            with raiseorpush("Node", raise_error=False, raise_warning=True,
                             dest=destination()):
                raise bundle()

    def test_ignoring_warnings_overrides_raising_on_them(self):
        """ignore_warnings wins, so a caller can collect rather than raise."""
        manager = raiseorpush(
            "Node", raise_error=False, raise_warning=True, dest=destination(),
            ignore_warnings=True,
        )
        assert manager.raise_warning is False
        assert manager.ignore_warnings is True

    def test_an_unrelated_exception_propagates(self):
        """The manager only handles validation findings, not every exception."""
        with pytest.raises(ZeroDivisionError):
            with raiseorpush("Node", raise_error=False, raise_warning=False,
                             dest=destination()):
                1 / 0

    def test_a_clean_block_collects_nothing(self):
        """Nothing raised means nothing collected."""
        dest = destination()
        with raiseorpush("Node", raise_error=False, raise_warning=False, dest=dest):
            pass
        assert dest.errors == {}
        assert dest.warnings == {}

    def test_the_error_set_widens_when_not_raising(self):
        """A single error is only caught when it is going to be collected."""
        raising = raiseorpush("Node", True, False, destination())
        collecting = raiseorpush("Node", False, False, destination())
        assert raising.error_set == (WNTREPANETTypeValidationErrorBundle,)
        assert collecting.error_set == (
            WNTREPANETTypeValidationError,
            WNTREPANETTypeValidationErrorBundle,
        )


class TestSha256Digest:
    """The file digest included in every report."""

    def test_returns_a_hex_digest(self, tmp_path):
        """A digest is a hexadecimal string."""
        path = tmp_path / "model.inp"
        path.write_text("test content", encoding="utf-8")
        digest = sha256digest(str(path))
        assert isinstance(digest, str)
        assert len(digest) == 64
        int(digest, 16)  # must be valid hexadecimal

    def test_is_deterministic(self, tmp_path):
        """The same bytes always give the same digest, so a report is traceable."""
        path = tmp_path / "model.inp"
        path.write_text("deterministic test content", encoding="utf-8")
        assert sha256digest(str(path)) == sha256digest(str(path))

    def test_differs_between_files(self, tmp_path):
        """Different content gives a different digest."""
        left = tmp_path / "a.inp"
        right = tmp_path / "b.inp"
        left.write_text("content one", encoding="utf-8")
        right.write_text("content two", encoding="utf-8")
        assert sha256digest(str(left)) != sha256digest(str(right))

    def test_matches_the_known_empty_file_digest(self, tmp_path):
        """The digest of empty content is the well-known SHA-256 constant."""
        path = tmp_path / "empty.inp"
        path.write_bytes(b"")
        assert sha256digest(str(path)) == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_handles_a_file_larger_than_one_chunk(self, tmp_path):
        """A file larger than the 64 KiB read buffer is hashed correctly."""
        path = tmp_path / "big.inp"
        payload = "x" * (256 * 1024)
        path.write_text(payload, encoding="utf-8")
        assert len(sha256digest(str(path))) == 64

    def test_raises_for_a_missing_file(self, tmp_path):
        """A file that is not there is an error, not an empty digest."""
        with pytest.raises(OSError):
            sha256digest(str(tmp_path / "absent.inp"))


class TestIntrospectionReexports:
    """The introspection helpers are importable from utils."""

    def test_helpers_are_the_same_objects(self):
        """Re-exporting does not wrap or copy, so identity is preserved."""
        import epanetparser.core.validation.introspection as introspection

        assert get_rule_methods is introspection.get_rule_methods
        assert get_warning_methods is introspection.get_warning_methods
        assert discover_classes is introspection.discover_classes
        assert discover_methods_in_class is introspection.discover_methods_in_class

    def test_get_rule_methods_returns_a_mapping(self, rules_class):
        """Rules are returned keyed by name."""
        rules = get_rule_methods(rules_class)
        assert isinstance(rules, dict)
        assert "rule_has_length" in rules
        assert all(name.startswith("rule") for name in rules)

    def test_get_warning_methods_returns_a_mapping(self, rules_class):
        """Warnings are returned separately from rules."""
        warnings = get_warning_methods(rules_class)
        assert "warn_short_pipe" in warnings
        assert all(name.startswith("warn") for name in warnings)

    def test_rules_and_warnings_are_disjoint(self, rules_class):
        """A name is either a rule or a warning, never both."""
        rules = set(get_rule_methods(rules_class))
        warnings = set(get_warning_methods(rules_class))
        assert rules.isdisjoint(warnings)

    def test_an_instance_yields_bound_methods(self, rules_class):
        """Passing an instance binds the methods to it, so they can be called."""
        pipe = rules_class({"length": 5})
        rules = get_rule_methods(pipe)
        assert rules["rule_has_length"].method.__self__ is pipe

    def test_a_class_yields_unbound_methods(self, rules_class):
        """Passing a class leaves the methods unbound, bound by the caller."""
        rules = get_rule_methods(rules_class)
        assert not hasattr(rules["rule_has_length"].method, "__self__")

    def test_a_discovered_method_carries_its_description(self, rules_class):
        """Descriptions come from the docstring, for reporting and documentation."""
        info = get_rule_methods(rules_class)["rule_has_length"]
        assert isinstance(info, MethodInfo)
        assert info.description == "Length must be present."
        assert info.to_dict()["description"] == "Length must be present."

    def test_a_failing_rule_raises_when_executed(self, rules_class):
        """A discovered rule is the real callable, not a description of one."""
        pipe = rules_class({})
        with pytest.raises(AssertionError):
            get_rule_methods(pipe)["rule_has_length"].method()


class TestComponentClassesCarryNoRules:
    """The model has no rules, which is what makes rulesets composable."""

    @pytest.mark.parametrize(
        "module_name,class_name",
        [
            ("control", "WNTREPANETControl"),
            ("curve", "WNTREPANETCurve"),
            ("link", "WNTREPANETLink"),
            ("network_info", "WNTREPANETNetworkInfo"),
            ("node", "WNTREPANETNode"),
            ("options", "WNTREPANETOptions"),
            ("pattern", "WNTREPANETPattern"),
            ("source", "WNTREPANETSource"),
        ],
    )
    def test_no_component_declares_rule_or_warning_methods(self, module_name, class_name):
        """Rules are found by rule set metadata, not by method-name convention."""
        module = ModuleType(f"epanetparser.core.epanettypes.{module_name}")
        import importlib

        module = importlib.import_module(
            f"epanetparser.core.epanettypes.{module_name}"
        )
        cls = getattr(module, class_name)
        assert get_rule_methods(cls) == {}
        assert get_warning_methods(cls) == {}

    def test_discover_classes_finds_the_component_classes(self):
        """The introspection helper still describes the model accurately."""
        import epanetparser.core.epanettypes.node as node_module

        classes = discover_classes(node_module)
        assert [cls.__name__ for cls in classes] == ["WNTREPANETNode"]
