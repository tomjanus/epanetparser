"""Rule set registry: discovery results, selection and rule lookup.

The registry is the single entry point for choosing which validation rules
run. It holds the rule sets found by
:func:`~epanetparser.core.validation.discovery.discover_ruleset_modules` and
resolves a :class:`~epanetparser.core.validation.engine.ValidationContext` into
an ordered list of :class:`RuleSet` objects.

Exactly one core rule set may be selected; any number of custom rule sets may
be selected alongside it. Core and custom rule sets are found and selected
through the same code, and are distinguished only by the ``__is_core__``
module attribute.

Rule sets are found by scanning the packages named by
:attr:`RuleSetRegistry.packages` and by reading the
:data:`~epanetparser.core.validation.discovery.ENTRY_POINT_GROUP` entry points
that installed third-party packages may register.

Classes
-------
RuleSet
    A discovered rule set and the rules it contains.
RuleSetRegistry
    Discovery cache plus selection and lookup.

Exceptions
----------
RuleSetSelectionError
    Raised when a selection is invalid, in particular when it does not name
    exactly one core rule set.

Examples
--------
>>> from epanetparser.core.validation import RuleSetRegistry, ValidationContext
>>> registry = RuleSetRegistry()
>>> selected = registry.resolve(ValidationContext())
>>> [ruleset.key for ruleset in selected]
['epanet_core']
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from epanetparser.core.logger_setup import get_logger
from epanetparser.core.validation.discovery import (
    default_packages,
    discover_ruleset_modules,
    entry_point_modules,
    ruleset_rule_modules,
)
from epanetparser.core.validation.rules import RuleSpec, collect_rules

logger = get_logger(__name__, level="WARNING")

#: Key of the core rule set used when a context does not name one.
DEFAULT_CORE_KEY = "epanet_core"

__all__ = [
    "DEFAULT_CORE_KEY",
    "RuleSet",
    "RuleSetRegistry",
    "RuleSetSelectionError",
]


class RuleSetSelectionError(ValueError):
    """Raised when a requested rule set selection cannot be satisfied.

    Raised when a key is not discovered, when a custom selection names a core
    rule set, or when the core selection does not resolve to exactly one rule
    set.
    """


@dataclass(frozen=True)
class RuleSet:
    """A rule set and the rules it contributes.

    Attributes
    ----------
    key : str
        Stable key of the rule set, from the module's ``__key__``. This is the
        value used in :class:`~epanetparser.core.validation.engine.ValidationContext`.
    name : str
        Human-readable name, from ``__ruleset_name__``.
    version : str
        Version string, from ``__version__``.
    description : str
        Description, from ``__description__``, empty when absent.
    is_core : bool
        True when the defining module sets ``__is_core__ = True``.
    module_path : str
        Import path of the defining module.
    component_rules : Tuple[RuleSpec, ...]
        Component-level rules, ordered by ``rule_id``.
    network_rules : Tuple[RuleSpec, ...]
        Network-level rules, ordered by ``rule_id``.

    Notes
    -----
    Instances are frozen and hashable. Rules are collected once, at
    construction, so selecting a rule set repeatedly is cheap.

    Examples
    --------
    >>> from epanetparser.core.validation import RuleSetRegistry
    >>> core = RuleSetRegistry().get("epanet_core")
    >>> core.is_core
    True
    >>> len(core.component_rules) > 0
    True
    """

    key: str
    name: str
    version: str
    description: str
    is_core: bool
    module_path: str
    component_rules: Tuple[RuleSpec, ...] = field(default=())
    network_rules: Tuple[RuleSpec, ...] = field(default=())

    def __str__(self) -> str:
        kind = "core" if self.is_core else "custom"
        return (
            f"{self.key} ({kind}): {self.name} v{self.version} "
            f"[{len(self.component_rules)} component, "
            f"{len(self.network_rules)} network rules]"
        )

    @property
    def rule_count(self) -> int:
        """Total number of rules in the rule set."""
        return len(self.component_rules) + len(self.network_rules)

    @classmethod
    def from_module(cls, module: ModuleType) -> "RuleSet":
        """Build a rule set from a discovered module.

        Parameters
        ----------
        module : ModuleType
            Module defining ``__key__``, ``__ruleset_name__`` and
            ``__version__``. Its rules are collected from the module itself
            or, for a package, from its submodules.

        Returns
        -------
        RuleSet
            The rule set with all of its rules already collected.

        Raises
        ------
        RuleSetSelectionError
            If the module lacks the required rule set metadata.
        """
        from epanetparser.core.validation.discovery import missing_metadata

        absent = missing_metadata(module)
        if absent:
            raise RuleSetSelectionError(
                f"Module '{module.__name__}' is not a rule set; "
                f"missing metadata {absent}"
            )
        component_rules: List[RuleSpec] = []
        network_rules: List[RuleSpec] = []
        for rule_module in ruleset_rule_modules(module):
            found_components, found_network = collect_rules(rule_module)
            component_rules.extend(found_components)
            network_rules.extend(found_network)
        component_rules.sort(key=lambda spec: (spec.component_type or "", spec.rule_id))
        network_rules.sort(key=lambda spec: spec.rule_id)
        return cls(
            key=module.__key__,
            name=module.__ruleset_name__,
            version=module.__version__,
            description=getattr(module, "__description__", "") or "",
            is_core=bool(getattr(module, "__is_core__", False)),
            module_path=module.__name__,
            component_rules=tuple(component_rules),
            network_rules=tuple(network_rules),
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary of the rule set.

        Returns
        -------
        Dict[str, Any]
            Metadata and the ``rule_id`` of every rule, grouped into
            ``component_rules`` and ``network_rules``.
        """
        return {
            "key": self.key,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "is_core": self.is_core,
            "module_path": self.module_path,
            "component_rules": [spec.rule_id for spec in self.component_rules],
            "network_rules": [spec.rule_id for spec in self.network_rules],
        }


class RuleSetRegistry:
    """Discovery cache with rule set selection and rule lookup.

    Parameters
    ----------
    packages : Optional[Sequence[str]]
        Import paths of packages to search for rule sets. Defaults to
        :func:`~epanetparser.core.validation.discovery.default_packages`.
    rulesets : Optional[Iterable[RuleSet]]
        Rule sets to seed the registry with, instead of discovering them.
        Used by tests and by callers that build rule sets programmatically.

    Attributes
    ----------
    packages : Tuple[str, ...]
        The search paths in use.

    Notes
    -----
    Discovery is lazy and happens on first use. Modules that fail to import,
    or that lack rule set metadata, are logged and skipped instead of
    failing the scan.

    Examples
    --------
    >>> registry = RuleSetRegistry()
    >>> sorted(registry.keys())
    ['epanet_core', 'milp']
    >>> registry.core_keys()
    ['epanet_core']
    """

    def __init__(
        self,
        packages: Optional[Sequence[str]] = None,
        rulesets: Optional[Iterable[RuleSet]] = None,
    ) -> None:
        self.packages: Tuple[str, ...] = tuple(
            packages if packages is not None else default_packages()
        )
        self._rulesets: Dict[str, RuleSet] = {}
        if rulesets is not None:
            for ruleset in rulesets:
                self._rulesets[ruleset.key] = ruleset

    def __repr__(self) -> str:
        return f"RuleSetRegistry(packages={list(self.packages)!r})"

    def __str__(self) -> str:
        return self.describe()

    def discover(self, refresh: bool = False) -> Dict[str, RuleSet]:
        """Discover rule sets and cache them.

        Rule sets are found two ways: by scanning the packages named by
        :attr:`packages`, and by reading the
        :data:`~epanetparser.core.validation.discovery.ENTRY_POINT_GROUP` entry
        points that installed packages may register. A package rule set wins if
        both mechanisms provide the same key.

        Parameters
        ----------
        refresh : bool
            If True, discard any cached rule sets and scan again.

        Returns
        -------
        Dict[str, RuleSet]
            Mapping of rule set key to rule set, sorted by key.
        """
        if self._rulesets and not refresh:
            return dict(sorted(self._rulesets.items()))
        discovered: Dict[str, RuleSet] = {}
        modules = dict(discover_ruleset_modules(self.packages))
        for name, module in entry_point_modules().items():
            if name in modules:
                logger.warning(
                    "Entry point '%s' collides with a rule set already found in"
                    " %s; keeping the discovered one",
                    name,
                    modules[name].__name__,
                )
                continue
            modules[name] = module
        for key, module in modules.items():
            try:
                discovered[key] = RuleSet.from_module(module)
            except Exception as err:
                logger.warning("Skipping rule set '%s': %s", key, err)
        self._rulesets = discovered
        return dict(sorted(self._rulesets.items()))

    def keys(self) -> List[str]:
        """Return the keys of all discovered rule sets, sorted."""
        return list(self.discover().keys())

    def all(self) -> List[RuleSet]:
        """Return all discovered rule sets, sorted by key."""
        return list(self.discover().values())

    def core_keys(self) -> List[str]:
        """Return the keys of the discovered core rule sets, sorted."""
        return [
            ruleset.key
            for ruleset in self.all()
            if ruleset.is_core
        ]

    def custom_keys(self) -> List[str]:
        """Return the keys of the discovered custom rule sets, sorted."""
        return [
            ruleset.key
            for ruleset in self.all()
            if not ruleset.is_core
        ]

    def get(self, key: str) -> RuleSet:
        """Return the rule set with the given key.

        Parameters
        ----------
        key : str
            Rule set key, for example ``"epanet_core"`` or ``"milp"``.

        Returns
        -------
        RuleSet
            The matching rule set.

        Raises
        ------
        RuleSetSelectionError
            If no discovered rule set has that key. The message lists the
            keys that are available.
        """
        available = self.discover()
        if key not in available:
            raise RuleSetSelectionError(
                f"No rule set with key '{key}'. Available: "
                f"{', '.join(available) or '<none>'}"
            )
        return available[key]

    def resolve(self, context: Any) -> List[RuleSet]:
        """Resolve a context into the ordered list of rule sets to run.

        Parameters
        ----------
        context : ValidationContext
            Selection of a core rule set and zero or more custom rule sets.
            The core rule set is placed first so that core issues are reported
            before custom ones.

        Returns
        -------
        List[RuleSet]
            Exactly one core rule set followed by the custom rule sets, in the
            order they were requested.

        Raises
        ------
        RuleSetSelectionError
            If the context selects zero or more than one core rule set, names
            an undiscovered key, or names a core rule set as custom.
        """
        from epanetparser.core.validation.engine import ValidationContext

        if not isinstance(context, ValidationContext):
            context = ValidationContext.from_any(context)
        selected: List[RuleSet] = []
        core_requests = list(context.core_keys)
        if not core_requests:
            raise RuleSetSelectionError(
                "Exactly one core rule set must be selected; none was requested"
            )
        if len(core_requests) > 1:
            raise RuleSetSelectionError(
                "Exactly one core rule set must be selected; "
                f"{len(core_requests)} were requested: {core_requests}"
            )
        core = self.get(core_requests[0])
        if not core.is_core:
            raise RuleSetSelectionError(
                f"Rule set '{core.key}' is not a core rule set; "
                "pass it as a custom rule set instead"
            )
        selected.append(core)
        for key in context.custom:
            ruleset = self.get(key)
            if ruleset.is_core:
                raise RuleSetSelectionError(
                    f"Core rule set '{ruleset.key}' cannot be selected as a "
                    "custom rule set"
                )
            selected.append(ruleset)
        return selected

    def describe(self) -> str:
        """Return a human-readable listing of the discovered rule sets.

        Returns
        -------
        str
            One block per rule set with its key, kind, name, version,
            description and rule counts.
        """
        lines: List[str] = ["Available rule sets:"]
        for ruleset in self.all():
            kind = "core" if ruleset.is_core else "custom"
            lines.append(f"  {ruleset.key} ({kind}) - {ruleset.name} v{ruleset.version}")
            lines.append(f"      module: {ruleset.module_path}")
            lines.append(
                f"      rules: {len(ruleset.component_rules)} component, "
                f"{len(ruleset.network_rules)} network"
            )
            if ruleset.description:
                lines.append(f"      {ruleset.description}")
        return "\n".join(lines)
