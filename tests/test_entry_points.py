"""Discovering rule sets published through package entry points.

A third-party package can advertise a rule set by registering an entry point in
the ``epanetparser.rulesets`` group, without being added to the configured
search paths. :class:`RuleSetRegistry` reads those entry points during discovery
and merges them with the rule sets found by scanning its packages.

These tests are the only reason to believe that path works. The function that
reads entry points, :func:`~epanetparser.core.validation.discovery.entry_point_modules`,
is defensive by design — a missing or broken entry point is logged and skipped
rather than allowed to break discovery — so without tests it could silently stop
being called and nothing would fail.

How the tests work
------------------
The function imports ``entry_points`` into its own scope on every call, so
replacing ``importlib.metadata.entry_points`` is enough to control what the scan
sees. The fakes mimic the one method the code uses, ``select(group=...)``, and
return real modules from ``tests.mock_rulesets`` so that the whole path from
entry point to validation finding is exercised, not just the loading step.
"""
from epanetparser.core.validation import RuleSetRegistry, ValidationContext
from epanetparser.core.validation.discovery import (
    ENTRY_POINT_GROUP,
    entry_point_modules,
)


class FakeEntryPoint:
    """The part of an entry point that the discovery code uses."""

    def __init__(self, name, module=None, error=None):
        self.name = name
        self._module = module
        self._error = error

    def load(self):
        if self._error is not None:
            raise self._error
        return self._module


class FakeSelection:
    """The result of ``entry_points().select(group=...)``."""

    def __init__(self, entry_points, group):
        self.group = group
        self._entry_points = [
            ep for ep in entry_points if getattr(ep, "group", None) in (None, group)
        ]

    def __iter__(self):
        return iter(self._entry_points)


class FakeEntryPoints:
    """A stand-in for the object ``entry_points()`` returns."""

    def __init__(self, entry_points):
        self._entry_points = entry_points

    def select(self, group):
        return FakeSelection(self._entry_points, group)


def patch_entry_points(monkeypatch, entry_points, group=ENTRY_POINT_GROUP):
    """Make ``entry_points()`` return ``entry_points``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        The monkeypatch fixture.
    entry_points : list of FakeEntryPoint
        The entry points the scan should see.
    group : str
        Group name the fakes will report, so selection can filter on it.
    """
    for ep in entry_points:
        if getattr(ep, "group", None) is None:
            ep.group = group
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda: FakeEntryPoints(entry_points),
    )


class TestEntryPointLoading:
    """Loading the modules named by entry points."""

    def test_a_registered_module_is_returned(self, monkeypatch):
        """A loadable entry point becomes a module in the result."""
        import tests.mock_rulesets.advanced_ruleset as module

        patch_entry_points(monkeypatch, [FakeEntryPoint("advanced", module)])
        found = entry_point_modules()
        assert found["advanced"] is module

    def test_a_custom_group_selects_nothing_by_default(self, monkeypatch):
        """A different group does not leak into the default scan."""
        import tests.mock_rulesets.advanced_ruleset as module

        ep = FakeEntryPoint("advanced", module)
        ep.group = "some.other.group"
        patch_entry_points(monkeypatch, [ep], group=ENTRY_POINT_GROUP)
        assert entry_point_modules() == {}

    def test_a_failing_entry_point_is_skipped(self, monkeypatch, caplog):
        """One broken entry point must not break discovery for the rest."""
        import tests.mock_rulesets.advanced_ruleset as module

        patch_entry_points(
            monkeypatch,
            [
                FakeEntryPoint("broken", error=ImportError("no such module")),
                FakeEntryPoint("working", module),
            ],
        )
        found = entry_point_modules()
        assert "broken" not in found
        assert found["working"] is module
        assert "broken" in caplog.text

    def test_a_broken_metadata_scan_is_survivable(self, monkeypatch):
        """If the metadata API itself fails, the scan returns nothing cleanly."""
        def explode():
            raise RuntimeError("no metadata available")

        monkeypatch.setattr("importlib.metadata.entry_points", explode)
        assert entry_point_modules() == {}


class TestRegistryIntegration:
    """Entry points reaching the registry and a validation report.

    These are the tests that make the feature real. Loading a module in isolation
    would not prove that a third-party rule set can actually constrain a model.
    """

    def test_an_entry_point_ruleset_is_discovered(self, monkeypatch):
        """A published rule set appears in the registry alongside the core."""
        import tests.mock_rulesets.advanced_ruleset as module

        patch_entry_points(monkeypatch, [FakeEntryPoint("advanced", module)])
        registry = RuleSetRegistry()
        assert "advanced" in registry.keys()
        assert registry.get("advanced").name == "Advanced Test Ruleset"

    def test_an_entry_point_ruleset_constrains_a_model(
        self, monkeypatch, minimal_network
    ):
        """A rule set that arrives by entry point actually reports findings.

        This is the behaviour that matters: a downstream package installs a rule
        set, and every model is then validated against it without the application
        naming the package anywhere.
        """
        import tests.mock_rulesets.advanced_ruleset as module

        patch_entry_points(monkeypatch, [FakeEntryPoint("advanced", module)])
        registry = RuleSetRegistry()
        context = ValidationContext(
            core="epanet_core", custom=["advanced"], registry=registry
        )
        report = minimal_network.validate(context)
        assert "E_ADVANCED_NO_LINKS" in report.codes()
        assert "E_ADVANCED_NODE_NAME" in report.codes()

    def test_a_colliding_entry_point_does_not_shadow_a_package_ruleset(
        self, monkeypatch, caplog
    ):
        """A package rule set wins when both mechanisms supply the same key.

        Two rule sets claiming one key would make selection ambiguous. The
        package scan is the configured, intentional mechanism, so it takes
        precedence and the collision is reported rather than resolved silently.
        """
        import tests.mock_rulesets.advanced_ruleset as module

        # Discover ``advanced`` by scanning the mock package *and* by entry point.
        patch_entry_points(monkeypatch, [FakeEntryPoint("advanced", module)])
        registry = RuleSetRegistry(packages=["tests.mock_rulesets"])
        found = registry.discover()
        # The key resolves once, to one rule set, without raising.
        assert "advanced" in found
        assert found["advanced"].module_path == module.__name__
        assert "collides" in caplog.text or "already found" in caplog.text

    def test_entry_points_do_not_break_the_built_in_rulesets(self, monkeypatch):
        """With entry points patched away, discovery finds the shipped rulesets."""
        import tests.mock_rulesets.advanced_ruleset as module

        patch_entry_points(monkeypatch, [FakeEntryPoint("advanced", module)])
        registry = RuleSetRegistry()
        keys = registry.keys()
        assert "epanet_core" in keys
        assert "milp" in keys
