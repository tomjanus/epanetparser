"""Validation engine: context selection, rule execution and result assembly.

The engine is the only place where rules are executed. It resolves a
:class:`ValidationContext` into rule sets, runs the component-level and
network-level rules that apply, and returns a
:class:`~epanetparser.core.validation.results.ValidationReport`.

Static validation is simulator-agnostic by design. Nothing in this module
knows about a particular solver or analysis; rules that encode application
constraints live in custom rule sets and are selected explicitly.

Classes
-------
ValidationContext
    Selection of one core rule set and any number of custom rule sets.
NetworkIndex
    Name-to-component index of a network, used by network-level rules to
    resolve cross-component references.
Validator
    Executes the selected rules against components and networks.

Functions
---------
validate
    Validate a component or a network with an optional context.

Examples
--------
>>> from epanetparser.core.validation import ValidationContext, validate
>>> report = validate(network, ValidationContext(custom=["milp"]))
>>> report.is_valid
True
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from epanetparser.core.logger_setup import get_logger
from epanetparser.core.validation.registry import (
    DEFAULT_CORE_KEY,
    RuleSet,
    RuleSetRegistry,
    RuleSetSelectionError,
)
from epanetparser.core.validation.results import ValidationIssue, ValidationReport
from epanetparser.core.validation.rules import (
    RuleExecutionError,
    RuleSpec,
    RuleViolation,
)

logger = get_logger(__name__, level="WARNING")

__all__ = [
    "NetworkIndex",
    "ValidationContext",
    "Validator",
    "validate",
]

#: Every component collection of a network, in the order they are validated.
#: ``network_info`` and ``options`` are single components rather than lists, but
#: they carry rules, so they are validated alongside the rest.
COMPONENT_COLLECTIONS: Tuple[str, ...] = (
    "network_info",
    "options",
    "curves",
    "patterns",
    "nodes",
    "links",
    "sources",
    "controls",
)

#: Collections whose components are identified by name, and which the
#: :class:`NetworkIndex` therefore resolves references against. ``network_info``
#: and ``options`` are singletons and are not name-addressable.
NAME_INDEXED_COLLECTIONS: Tuple[str, ...] = (
    "curves",
    "patterns",
    "nodes",
    "links",
    "sources",
    "controls",
)

#: Attributes whose presence as a sequence identifies a network. Used to tell a
#: network apart from a single component when both are handed to
#: :func:`validate`.
_NETWORK_MARKERS: Tuple[str, ...] = ("nodes", "links", "curves", "patterns")


class ValidationContext:
    """Selection of the rule sets to run.

    Parameters
    ----------
    core : Optional[Union[str, Sequence[str]]]
        The core rule set, or a sequence naming exactly one. Defaults to
        ``"epanet_core"``. A sequence is accepted so that passing more than one
        produces a clear selection error rather than a silent choice.
    custom : Optional[Sequence[str]]
        Keys of custom rule sets to run alongside the core rule set. Order is
        preserved and reported in the resulting issues.
    registry : Optional[RuleSetRegistry]
        Registry to resolve the selection against. Defaults to a shared
        process-wide registry, which discovers rule sets once and caches them.

    Attributes
    ----------
    registry : RuleSetRegistry
        Registry used to resolve this context.

    Notes
    -----
    The context is a value object: it selects rules, it does not run them.
    Two contexts with the same keys behave identically, which is what makes
    validators safe to cache and share.

    Examples
    --------
    >>> context = ValidationContext(core="epanet_core", custom=["milp"])
    >>> context.core_keys
    ('epanet_core',)
    >>> context.custom
    ('milp',)
    >>> context.ruleset_keys
    ('epanet_core', 'milp')
    """

    def __init__(
        self,
        core: Optional[Union[str, Sequence[str]]] = DEFAULT_CORE_KEY,
        custom: Optional[Sequence[str]] = None,
        registry: Optional[RuleSetRegistry] = None,
    ) -> None:
        if core is None:
            core_keys: Tuple[str, ...] = (DEFAULT_CORE_KEY,)
        elif isinstance(core, str):
            core_keys = (core,)
        else:
            core_keys = tuple(str(key) for key in core)
        self.core_keys: Tuple[str, ...] = core_keys
        self.custom: Tuple[str, ...] = tuple(str(key) for key in (custom or ()))
        self.registry: RuleSetRegistry = registry if registry is not None else _shared_registry()

    def __repr__(self) -> str:
        return f"ValidationContext(core={list(self.core_keys)!r}, custom={list(self.custom)!r})"

    def __str__(self) -> str:
        core = ", ".join(self.core_keys) or "<none>"
        custom = ", ".join(self.custom) or "<none>"
        return f"core={core}; custom={custom}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationContext):
            return NotImplemented
        return self.ruleset_keys == other.ruleset_keys

    def __hash__(self) -> int:
        return hash(self.ruleset_keys)

    @property
    def ruleset_keys(self) -> Tuple[str, ...]:
        """Keys of the selected rule sets, core first, in requested order."""
        return self.core_keys + self.custom

    @classmethod
    def from_any(cls, context: Any = None) -> "ValidationContext":
        """Coerce a loose specification into a :class:`ValidationContext`.

        Parameters
        ----------
        context : Any
            ``None`` for the default context, a :class:`ValidationContext`,
            a rule set key string, a sequence of keys, or a mapping with
            ``core`` and/or ``custom`` entries.

        Returns
        -------
        ValidationContext
            The equivalent context.

        Raises
        ------
        TypeError
            If ``context`` cannot be interpreted.

        Examples
        --------
        >>> ValidationContext.from_any(None).ruleset_keys
        ('epanet_core',)
        >>> ValidationContext.from_any("milp").ruleset_keys
        ('milp',)
        >>> ValidationContext.from_any({"custom": ["milp"]}).ruleset_keys
        ('epanet_core', 'milp')
        """
        if context is None:
            return cls()
        if isinstance(context, ValidationContext):
            return context
        if isinstance(context, str):
            return cls(core=context)
        if isinstance(context, Mapping):
            unknown = set(context) - {"core", "custom"}
            if unknown:
                raise TypeError(
                    f"Unknown validation context keys: {sorted(unknown)}; "
                    "expected 'core' and/or 'custom'"
                )
            return cls(
                core=context.get("core", DEFAULT_CORE_KEY),
                custom=context.get("custom"),
            )
        if isinstance(context, (list, tuple, set, frozenset)):
            keys = [str(key) for key in context]
            if not keys:
                return cls()
            return cls(core=keys[0], custom=keys[1:])
        raise TypeError(
            f"Cannot interpret {type(context).__name__} as a ValidationContext"
        )


class NetworkIndex:
    """Name-to-component index of a network.

    Network-level rules need to resolve references between components, for
    example whether the curve named by a pump exists. The index is that
    lookup table, built once and reused for every network rule.

    Parameters
    ----------
    network : Any
        Network to index. Any object with the standard component collections
        as attributes is accepted.

    Attributes
    ----------
    network : Any
        The indexed network.

    Notes
    -----
    Components without a usable name are not indexed; a nameless component is
    reported by a component-level rule, not by the index.

    Examples
    --------
    >>> index = NetworkIndex(network)
    >>> "T1" in index.nodes
    True
    >>> index.curves_of_type("HEAD") == {"1"}
    True
    """

    def __init__(self, network: Any) -> None:
        self.network = network
        self._by_collection: Dict[str, Dict[str, Any]] = {}
        self._duplicates: Dict[str, List[str]] = {}
        for collection in NAME_INDEXED_COLLECTIONS:
            self._by_collection[collection] = self._build(collection)
        self.curves_by_type: Dict[str, set] = self._build_curve_types()

    def __repr__(self) -> str:
        return f"NetworkIndex({self.counts()!r})"

    def _components(self, collection: str) -> Sequence[Any]:
        store = getattr(self.network, collection, None)
        if store is None:
            return ()
        if isinstance(store, Mapping):
            return list(store.values())
        return list(store)

    @staticmethod
    def _name_of(component: Any) -> Optional[str]:
        name = getattr(component, "name", None)
        if name is None and isinstance(getattr(component, "data", None), Mapping):
            name = component.data.get("name")
        return name if isinstance(name, str) and name else None

    def _build(self, collection: str) -> Dict[str, Any]:
        mapping: Dict[str, Any] = {}
        duplicates: List[str] = []
        for component in self._components(collection):
            name = self._name_of(component)
            if name is None:
                continue
            if name in mapping:
                if name not in duplicates:
                    duplicates.append(name)
                continue
            mapping[name] = component
        self._duplicates[collection] = duplicates
        return mapping

    def _build_curve_types(self) -> Dict[str, set]:
        by_type: Dict[str, set] = {}
        for name, curve in self._by_collection["curves"].items():
            curve_type = getattr(curve, "type", None)
            if isinstance(curve_type, str):
                by_type.setdefault(curve_type, set()).add(name)
        return by_type

    @property
    def nodes(self) -> Dict[str, Any]:
        """Nodes indexed by name."""
        return self._by_collection["nodes"]

    @property
    def links(self) -> Dict[str, Any]:
        """Links indexed by name."""
        return self._by_collection["links"]

    @property
    def curves(self) -> Dict[str, Any]:
        """Curves indexed by name."""
        return self._by_collection["curves"]

    @property
    def patterns(self) -> Dict[str, Any]:
        """Patterns indexed by name."""
        return self._by_collection["patterns"]

    @property
    def sources(self) -> Dict[str, Any]:
        """Sources indexed by name."""
        return self._by_collection["sources"]

    @property
    def controls(self) -> Dict[str, Any]:
        """Controls indexed by name."""
        return self._by_collection["controls"]

    def collection(self, name: str) -> Dict[str, Any]:
        """Return the index of a component collection.

        Parameters
        ----------
        name : str
            Collection name, one of :data:`COMPONENT_COLLECTIONS`.

        Returns
        -------
        Dict[str, Any]
            Mapping of component name to component. Empty for an unknown
            collection, so rules can probe optional collections safely.
        """
        return self._by_collection.get(name, {})

    def curves_of_type(self, curve_type: str) -> set:
        """Return the names of the curves of the given type.

        Parameters
        ----------
        curve_type : str
            Curve type as written in the model, for example ``"HEAD"`` or
            ``"VOLUME"``.

        Returns
        -------
        set of str
            Names of the matching curves. Empty when there are none.
        """
        return set(self.curves_by_type.get(curve_type, set()))

    def duplicates(self, collection: str) -> List[str]:
        """Return the names that occur more than once in a collection.

        Parameters
        ----------
        collection : str
            Collection name, for example ``"nodes"``.

        Returns
        -------
        List[str]
            Duplicated names, in the order they were first seen again. Empty
            when the collection has no duplicates.
        """
        return list(self._duplicates.get(collection, []))

    def has(self, collection: str, name: Optional[str]) -> bool:
        """Return True if ``name`` resolves in ``collection``."""
        if not name:
            return False
        return name in self._by_collection.get(collection, {})

    def counts(self) -> Dict[str, int]:
        """Return the number of named components per collection."""
        return {
            collection: len(mapping)
            for collection, mapping in self._by_collection.items()
        }


class Validator:
    """Executes selected rule sets against components and networks.

    Parameters
    ----------
    rulesets : Sequence[RuleSet]
        Rule sets to run, in report order. Normally obtained from
        :meth:`from_context` so that the core rule set runs first.

    Attributes
    ----------
    rulesets : Tuple[RuleSet, ...]
        The selected rule sets.

    Notes
    -----
    A validator is stateless and safe to share: it holds rule metadata, not
    results, and every run produces a fresh
    :class:`~epanetparser.core.validation.results.ValidationReport`.

    Examples
    --------
    >>> validator = Validator.from_context()
    >>> report = validator.validate_component(network.nodes[0])
    >>> report.is_valid
    True
    """

    def __init__(self, rulesets: Sequence[RuleSet]) -> None:
        if not rulesets:
            raise RuleSetSelectionError("A validator needs at least one rule set")
        self.rulesets: Tuple[RuleSet, ...] = tuple(rulesets)

    def __repr__(self) -> str:
        return f"Validator(rulesets={list(self.ruleset_keys)!r})"

    def __str__(self) -> str:
        return f"Validator({' + '.join(self.ruleset_keys)})"

    @property
    def ruleset_keys(self) -> Tuple[str, ...]:
        """Keys of the selected rule sets, in run order."""
        return tuple(ruleset.key for ruleset in self.rulesets)

    @classmethod
    def from_context(
        cls,
        context: Any = None,
        registry: Optional[RuleSetRegistry] = None,
    ) -> "Validator":
        """Build a validator for the rule sets selected by ``context``.

        Parameters
        ----------
        context : Any
            Anything :meth:`ValidationContext.from_any` accepts.
        registry : Optional[RuleSetRegistry]
            Registry to resolve against. Defaults to the registry carried by
            the context, which is the shared process-wide registry.

        Returns
        -------
        Validator
            Validator with the resolved rule sets.
        """
        resolved = ValidationContext.from_any(context)
        if registry is not None:
            resolved = ValidationContext(
                core=resolved.core_keys,
                custom=resolved.custom,
                registry=registry,
            )
        return cls(resolved.registry.resolve(resolved))

    def rules_for(self, component: Any) -> List[Tuple[RuleSet, RuleSpec]]:
        """Return the rules that apply to a component, in run order.

        Parameters
        ----------
        component : Any
            Component to be validated.

        Returns
        -------
        List[Tuple[RuleSet, RuleSpec]]
            Pairs of owning rule set and rule, flattened over the selected
            rule sets in order.
        """
        applicable: List[Tuple[RuleSet, RuleSpec]] = []
        for ruleset in self.rulesets:
            for spec in ruleset.component_rules:
                if spec.applies_to(component):
                    applicable.append((ruleset, spec))
        return applicable

    def validate(self, target: Any, index: Optional[NetworkIndex] = None) -> ValidationReport:
        """Validate a component or a whole network.

        Parameters
        ----------
        target : Any
            A network, which is validated in full, or a single component.
        index : Optional[NetworkIndex]
            Prebuilt index for network validation. One is built on demand
            when omitted.

        Returns
        -------
        ValidationReport
            Issues found, in rule order.
        """
        if _is_network(target):
            return self.validate_network(target, index=index)
        return self.validate_component(target)

    def validate_component(self, component: Any) -> ValidationReport:
        """Run the component-level rules against a single component.

        Parameters
        ----------
        component : Any
            Component to validate. Rules that name a different component type
            are skipped; rules restricted by ``@match`` decide for themselves
            whether to run.

        Returns
        -------
        ValidationReport
            Issues found for this component. An empty report is valid.

        Notes
        -----
        No model state is modified: the component is read, not rewritten.
        """
        report = ValidationReport()
        context = self._component_context(component)
        for ruleset, spec in self.rules_for(component):
            self._run(spec, component, ruleset, report, context)
        return report

    def validate_network(
        self,
        network: Any,
        index: Optional[NetworkIndex] = None,
    ) -> ValidationReport:
        """Run component-level rules for every component, then network rules.

        Parameters
        ----------
        network : Any
            Network to validate.
        index : Optional[NetworkIndex]
            Prebuilt index. When omitted, the network's own ``index``
            attribute is used if it is a :class:`NetworkIndex`, and otherwise
            one is built.

        Returns
        -------
        ValidationReport
            Component issues in component order, followed by network issues.

        Notes
        -----
        Component rules run first so that a report reads from the specific to
        the general: a dangling reference is easier to act on once the
        components it refers to are known to exist.

        The name-to-component index is built once per call and, when the
        network has an ``index`` attribute, reused from it. Network rules
        reach it as ``network.index``.
        """
        report = ValidationReport()
        _ensure_index(network)
        for collection in COMPONENT_COLLECTIONS:
            for component in self._components_of(network, collection):
                report.extend(self.validate_component(component))
        for ruleset, spec in self._network_rules():
            self._run(spec, network, ruleset, report, {"network": type(network).__name__})
        return report

    def _components_of(self, network: Any, collection: str) -> Sequence[Any]:
        """Return a collection's components as a sequence.

        ``network_info`` and ``options`` are single components rather than
        collections, so a non-sequence value is returned as a one-item
        sequence. That lets every collection be validated by the same loop.
        """
        store = getattr(network, collection, None)
        if store is None:
            return ()
        if isinstance(store, Mapping):
            return list(store.values())
        if isinstance(store, (list, tuple)):
            return store
        return (store,)

    def _network_rules(self) -> List[Tuple[RuleSet, RuleSpec]]:
        applicable: List[Tuple[RuleSet, RuleSpec]] = []
        for ruleset in self.rulesets:
            for spec in ruleset.network_rules:
                applicable.append((ruleset, spec))
        return applicable

    @staticmethod
    def _component_context(component: Any) -> Dict[str, Any]:
        """Build the shared per-component context recorded on its issues."""
        context: Dict[str, Any] = {}
        subtype = getattr(component, "type", None)
        if isinstance(subtype, str):
            context["component_subtype"] = subtype
        return context

    @staticmethod
    def _issue_context(
        spec: RuleSpec,
        ruleset: RuleSet,
        target: Any,
        base: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assemble the context dict stored on an issue."""
        context = spec.issue_context()
        context["ruleset"] = ruleset.key
        context.update(base)
        return context

    @staticmethod
    def _run(
        spec: RuleSpec,
        target: Any,
        ruleset: RuleSet,
        report: ValidationReport,
        base_context: Dict[str, Any],
    ) -> None:
        """Execute one rule and record its outcome in ``report``."""
        try:
            spec.func(target)
        except AssertionError as err:
            context = Validator._issue_context(spec, ruleset, target, base_context)
            if isinstance(err, RuleViolation):
                context.update(err.context)
            report.add(
                ValidationIssue(
                    code=spec.code,
                    message=str(err) or spec.description,
                    severity=spec.severity,
                    rule_id=spec.rule_id,
                    ruleset_key=ruleset.key,
                    component_type=(
                        "network" if spec.is_network else type(target).__name__
                    ),
                    component_name=_target_name(target),
                    attribute=spec.attribute,
                    context=context,
                )
            )
        except Exception as err:
            raise RuleExecutionError(
                f"Rule '{spec.rule_id}' from rule set '{ruleset.key}' failed: {err}"
            ) from err


def _target_name(target: Any) -> Optional[str]:
    """Return the name of a validated target, if it has one."""
    name = getattr(target, "name", None)
    if isinstance(name, str) and name:
        return name
    if isinstance(target, Mapping):
        raw = target.get("name")
        if isinstance(raw, str) and raw:
            return raw
    return None


def _ensure_index(network: Any) -> NetworkIndex:
    """Return the network's index, building and caching one if needed.

    Network rules read the index as ``network.index``. Reusing a cached index
    keeps repeated validation of the same network cheap, and keeps issue
    provenance stable across runs.
    """
    existing = getattr(network, "index", None)
    if isinstance(existing, NetworkIndex):
        return existing
    index = NetworkIndex(network)
    try:
        network.index = index
    except (AttributeError, TypeError):  # pragma: no cover - exotic network objects
        logger.debug("Could not cache NetworkIndex on %r", type(network).__name__)
    return index


def _is_network(target: Any) -> bool:
    """Return True if ``target`` looks like a network rather than a component.

    Parameters
    ----------
    target : Any
        Object handed to :func:`validate`.

    Returns
    -------
    bool
        True when every marker collection is present as a sequence or mapping.
        A component class holds one component's fields and has none of them.
    """
    if isinstance(target, NetworkIndex):
        return True
    return all(
        isinstance(getattr(target, collection, None), (list, tuple, Mapping))
        for collection in _NETWORK_MARKERS
    )


_SHARED_REGISTRY: Optional[RuleSetRegistry] = None
_REGISTRY_LOCK = threading.Lock()
_VALIDATOR_CACHE: Dict[Tuple[Any, ...], Validator] = {}
_VALIDATOR_LOCK = threading.Lock()


def _shared_registry() -> RuleSetRegistry:
    """Return the process-wide rule set registry, creating it on first use."""
    global _SHARED_REGISTRY  # pylint: disable=global-statement
    with _REGISTRY_LOCK:
        if _SHARED_REGISTRY is None:
            _SHARED_REGISTRY = RuleSetRegistry()
        return _SHARED_REGISTRY


def clear_caches() -> None:
    """Discard cached validators and the shared registry.

    Rule sets are discovered and rule functions are imported, both of which
    are cached for the life of the process. Call this after installing a new
    rule set at runtime, or in tests that change the search paths.

    Notes
    -----
    This is process-global state. Concurrent validation runs in other threads
    keep using the validator they already hold.
    """
    global _SHARED_REGISTRY  # pylint: disable=global-statement
    with _VALIDATOR_LOCK:
        _VALIDATOR_CACHE.clear()
    with _REGISTRY_LOCK:
        if _SHARED_REGISTRY is not None:
            _SHARED_REGISTRY.discover(refresh=True)
        else:
            _SHARED_REGISTRY = None


def get_validator(context: Any = None) -> Validator:
    """Return a cached validator for a context.

    Parameters
    ----------
    context : Any
        Anything :meth:`ValidationContext.from_any` accepts.

    Returns
    -------
    Validator
        Validator for the selected rule sets. The same instance is returned
        for equal contexts, which avoids re-scanning rule sets for every
        component validated.

    Raises
    ------
    RuleSetSelectionError
        Propagated from registry resolution when the selection is invalid.
    """
    resolved = ValidationContext.from_any(context)
    cache_key = (resolved.registry.packages, resolved.ruleset_keys)
    with _VALIDATOR_LOCK:
        validator = _VALIDATOR_CACHE.get(cache_key)
    if validator is None:
        validator = Validator.from_context(resolved)
        with _VALIDATOR_LOCK:
            _VALIDATOR_CACHE[cache_key] = validator
    return validator


def validate(
    target: Any,
    context: Any = None,
    registry: Optional[RuleSetRegistry] = None,
) -> ValidationReport:
    """Validate a component or a network.

    Parameters
    ----------
    target : Any
        A network, validated in full, or a single component.
    context : Any
        Rule set selection. Defaults to the core rule set alone.
    registry : Optional[RuleSetRegistry]
        Registry to resolve the selection against.

    Returns
    -------
    ValidationReport
        Structured result. Check :attr:`ValidationReport.is_valid` rather
        than relying on an exception, which is reserved for broken rules.

    Examples
    --------
    >>> report = validate(network)
    >>> report.is_valid
    True
    >>> report = validate(network, custom=["milp"])
    >>> report.is_valid
    True
    """
    validator = get_validator(context) if registry is None else Validator.from_context(
        context, registry
    )
    return validator.validate(target)
