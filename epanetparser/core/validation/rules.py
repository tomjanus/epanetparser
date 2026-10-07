"""Rule declaration and module scanning for EPANET static validation.

A rule is a plain module-level function that takes exactly one argument, the
component or network under test, and signals a violation with ``assert``::

    @rule("WNTREPANETNode", code="E_NODE_NAME_MISSING", attribute="name")
    def rule_node_has_name(component) -> None:
        \"\"\"A node must have a name.\"\"\"
        assert component.name is not None, "Missing node must have a name"

Network-level rules are declared with :func:`network_rule` and take the
network instead of a component. The engine catches the ``AssertionError`` and
turns it into a :class:`~epanetparser.core.validation.results.ValidationIssue`.

The :func:`~epanetparser.core.decorators.match` and
:func:`~epanetparser.core.decorators.described` decorators compose with
:func:`rule`: ``match`` narrows a component rule to a concrete component type
(for example ``"Tank"``) and ``described`` supplies the description shown in
reports.

Functions
---------
rule
    Declare a component-level rule.
network_rule
    Declare a network-level rule.
collect_rules
    Collect every rule declared in a module.
default_code
    Derive a stable issue code from a rule name.

Classes
-------
RuleSpec
    A rule function together with the metadata needed to report its failures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple, get_args, get_origin

from epanetparser.core.validation.decorators import extract_quick_description
from epanetparser.core.validation.results import Severity

__all__ = [
    "RULE_ATTRIBUTE",
    "NETWORK_RULE_ATTRIBUTE",
    "RuleExecutionError",
    "RuleSpec",
    "RuleViolation",
    "collect_rules",
    "default_code",
    "defined",
    "network_rule",
    "rule",
]


def defined(component: Any, field: str) -> bool:
    """Return True if a component field carries a value.

    Rules use this to express "this field is required" without repeating the
    same lookup, and, more importantly, to reject a field that is present but
    null. JSON producers routinely emit ``"elevation": null`` when they have
    nothing to put in it, and a junction with a null elevation is no more
    simulable than one whose elevation is absent, so both are reported the
    same way.

    Parameters
    ----------
    component : Any
        Component whose ``data`` dictionary is read.
    field : str
        Name of the field to check.

    Returns
    -------
    bool
        True if the field exists and its value is not None.

    Notes
    -----
    Zero, ``False`` and ``""`` count as values, not absences. A tank with an
    ``init_level`` of 0.0 is configured, not unconfigured.

    Examples
    --------
    >>> from epanetparser.core.epanettypes import WNTREPANETNode
    >>> node = WNTREPANETNode({"name": "T1", "elevation": None})
    >>> defined(node, "elevation")
    False
    >>> defined(node, "name")
    True
    """
    data = getattr(component, "data", None)
    if not isinstance(data, dict):
        return False
    return data.get(field) is not None


# Attribute under which :func:`rule` stores the resulting :class:`RuleSpec`.
RULE_ATTRIBUTE = "__epanetparser_rule__"

# Attribute under which :func:`network_rule` stores the resulting RuleSpec.
NETWORK_RULE_ATTRIBUTE = "__epanetparser_network_rule__"

# Prefix that a component type must start with for the auto-generated code
# severity letter to be ``E`` rather than ``W``.
ERROR_CODE_PREFIXES = ("rule_",)


def default_code(rule_name: str) -> str:
    """Derive a stable issue code from a rule function name.

    The mapping is deterministic so that codes stay stable across releases
    even when a rule's message text changes::

        rule_node_has_name -> E_NODE_NAME_MISSING
        warn_node_has_type -> W_NODE_HAS_TYPE

    Parameters
    ----------
    rule_name : str
        Name of the rule function.

    Returns
    -------
    str
        Issue code consisting of a severity letter (``E`` or ``W``), the
        ``rule_``/``warn_`` prefix stripped, upper-cased with underscores.

    Notes
    -----
    Rules that want a different code should pass ``code`` explicitly to
    :func:`rule`; this helper is only a default.

    Examples
    --------
    >>> default_code("rule_curve_points_sorted")
    'E_CURVE_POINTS_SORTED'
    >>> default_code("warn_network_has_version")
    'W_NETWORK_HAS_VERSION'
    """
    if rule_name.startswith("warn"):
        letter, stem = "W", rule_name[len("warn"):]
    else:
        letter = "E"
        for prefix in ERROR_CODE_PREFIXES:
            if rule_name.startswith(prefix):
                stem = rule_name[len(prefix):]
                break
        else:
            stem = rule_name
    return f"{letter}_{stem.upper()}"


@dataclass(frozen=True)
class RuleSpec:
    """A rule function and the metadata used to report its failures.

    Attributes
    ----------
    rule_id : str
        Name of the rule function, used as the stable ``rule_id`` of every
        issue the rule produces.
    func : Callable[[Any], None]
        The rule function. Called with a single positional argument, either
        the component or the network.
    component_type : Optional[str]
        Class name of the component this rule applies to, for example
        ``"WNTREPANETNode"``. ``None`` for network-level rules.
    severity : Severity
        Severity assigned to every issue produced by this rule.
    code : str
        Stable issue code. Defaults to :func:`default_code` of ``rule_id``.
    attribute : Optional[str]
        Name of the field the rule is concerned with, when meaningful.
    description : str
        Human-readable description, from the function docstring.
    is_network : bool
        True for rules declared with :func:`network_rule`.

    Notes
    -----
    Instances are frozen. The function itself carries the type filtering done
    by ``@match`` and the description set by ``@described``, so
    :attr:`description` is resolved once at scan time.
    """

    rule_id: str
    func: Callable[[Any], None]
    component_type: Optional[str] = None
    severity: Severity = Severity.ERROR
    code: str = ""
    attribute: Optional[str] = None
    description: str = ""
    is_network: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Fill in the defaults that depend on the wrapped function."""
        if not self.code:
            object.__setattr__(self, "code", default_code(self.rule_id))
        if not self.description:
            object.__setattr__(
                self,
                "description",
                extract_quick_description(self.func) or self.rule_id,
            )

    def __str__(self) -> str:
        target = "network" if self.is_network else self.component_type
        return f"{self.code} ({self.rule_id}, {target}, {self.severity})"

    @property
    def is_error(self) -> bool:
        """True if this rule reports :attr:`Severity.ERROR` failures."""
        return self.severity is Severity.ERROR

    @property
    def is_warning(self) -> bool:
        """True if this rule reports :attr:`Severity.WARNING` failures."""
        return self.severity is Severity.WARNING

    def applies_to(self, component: Any) -> bool:
        """Return True if this rule should be run against ``component``.

        Parameters
        ----------
        component : Any
            Component instance about to be validated. Its class name is
            compared against :attr:`component_type`.

        Returns
        -------
        bool
            True if :attr:`component_type` is ``None`` (the rule applies to
            every component) or matches the class name of ``component``.
        """
        if self.component_type is None:
            return True
        return type(component).__name__ == self.component_type

    def issue_context(self) -> Dict[str, Any]:
        """Return the static contextual metadata carried by this rule."""
        return dict(self.context)


def _target_name(func: Callable[..., Any]) -> Optional[str]:
    """Return the annotated component type of a rule, if it declares one.

    The type is read from the first parameter's annotation so that rules can
    be written as ``def rule_x(node: WNTREPANETNode) -> None`` and discovered
    without repeating the class name in the decorator.
    """
    annotations = getattr(func, "__annotations__", {})
    if not annotations:
        return None
    first = next(iter(annotations.values()), None)
    if first is None:
        return None
    if isinstance(first, type):
        return first.__name__
    origin = get_origin(first)
    if origin is not None and get_args(first):
        arg = get_args(first)[0]
        if isinstance(arg, type):
            return arg.__name__
    return None


def _attach(
    func: Callable[..., Any],
    *,
    component_type: Optional[str],
    severity: Severity,
    code: Optional[str],
    attribute: Optional[str],
    is_network: bool,
) -> RuleSpec:
    """Create a :class:`RuleSpec` and attach it to ``func``."""
    spec = RuleSpec(
        rule_id=func.__name__,
        func=func,
        component_type=component_type or _target_name(func),
        severity=Severity(severity),
        code=code or "",
        attribute=attribute,
        description=getattr(func, "description", ""),
        is_network=is_network,
    )
    setattr(func, NETWORK_RULE_ATTRIBUTE if is_network else RULE_ATTRIBUTE, spec)
    return spec


_UNSET = object()


def rule(
    component_type: Optional[str] = None,
    *,
    severity: Any = _UNSET,
    code: Optional[str] = None,
    attribute: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a component-level validation rule.

    The decorated function must take a single positional argument, the
    component under test, and signal a violation with ``assert``. An
    ``AssertionError`` is what the engine converts into an issue; any other
    exception is a bug in the rule and is re-raised wrapped in a
    :class:`RuleExecutionError`.

    Parameters
    ----------
    component_type : Optional[str]
        Class name of the component the rule applies to, for example
        ``"WNTREPANETNode"``. Rules that do not name a component type run
        against every component. When omitted, the type is taken from the
        annotation of the first parameter, if present.
    severity : Any
        Severity for the rule's failures. When not given explicitly, a
        function named ``warn_*`` reports :attr:`Severity.WARNING` and any
        other function reports :attr:`Severity.ERROR`.
    code : Optional[str]
        Stable issue code. Defaults to :func:`default_code` of the function
        name. Pass a code explicitly when the generated one is unsuitable.
    attribute : Optional[str]
        Field the rule is concerned with, recorded on every issue the rule
        produces.

    Returns
    -------
    Callable[[Callable[..., Any]], Callable[..., Any]]
        Decorator returning the function unchanged, with a
        :class:`RuleSpec` attached for module scanning.

    Notes
    -----
    Combine with ``@match`` to restrict a rule to a concrete component type
    such as ``"Tank"``, and with ``@described`` to control the description.
    ``@match`` must be the outermost decorator so that it wraps the function
    the engine calls.

Examples
    --------
    >>> from epanetparser.core.validation import match
    >>> @rule("WNTREPANETNode", attribute="diameter")
    ... @match("Tank")
    ... def rule_tank_has_diameter(tank) -> None:
    ...     '''A tank must define a diameter.'''
    ...     assert tank.data.get("diameter") is not None, "Tank has no diameter"
    >>> spec = rule_tank_has_diameter.__epanetparser_rule__
    >>> spec.code
    'E_TANK_HAS_DIAMETER'
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        rule_severity = severity
        if rule_severity is _UNSET:
            rule_severity = (
                Severity.WARNING
                if func.__name__.startswith("warn")
                else Severity.ERROR
            )
        _attach(
            func,
            component_type=component_type,
            severity=rule_severity,
            code=code,
            attribute=attribute,
            is_network=False,
        )
        return func

    return decorator


def network_rule(
    *,
    severity: Any = Severity.ERROR,
    code: Optional[str] = None,
    attribute: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a network-level validation rule.

    Network rules see the whole model at once and are the mechanism for
    cross-component checks such as reference resolution and duplicate-name
    detection. The decorated function takes a single positional argument, the
    network, which exposes a name-to-component index for lookups.

    Parameters
    ----------
    severity : Any
        Severity for the rule's failures. ``Severity.ERROR`` by default.
    code : Optional[str]
        Stable issue code. Defaults to :func:`default_code` of the function
        name.
    attribute : Optional[str]
        Field the rule is concerned with, when meaningful.

    Returns
    -------
    Callable[[Callable[..., Any]], Callable[..., Any]]
        Decorator returning the function unchanged, with a
        :class:`RuleSpec` marked ``is_network=True``.

    Examples
    --------
    >>> @network_rule(code="E_DUPLICATE_NODE_NAME")
    ... def rule_node_names_unique(network) -> None:
    ...     \"\"\"Node names must be unique within a network.\"\"\"
    ...     assert network.index.duplicates("nodes") == [], "Duplicate node names"
    >>> rule_node_names_unique.__epanetparser_network_rule__.is_network
    True
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _attach(
            func,
            component_type=None,
            severity=severity,
            code=code,
            attribute=attribute,
            is_network=True,
        )
        return func

    return decorator


class RuleExecutionError(RuntimeError):
    """Raised when a rule fails for a reason other than a failed assertion.

    A broken rule is a defect in the rule itself, not a finding about the
    model, so the engine reports it by raising this error rather than adding an
    issue to the report.
    """


class RuleViolation(AssertionError):
    """A rule failure that carries structured context.

    Subclassing :class:`AssertionError` means a rule can signal a violation
    either with a bare ``assert`` or with ``raise RuleViolation(...)`` when it
    wants to attach detail. The engine treats both identically and merges
    :attr:`context` into the resulting issue.

    Parameters
    ----------
    message : str
        Human-readable description of the violation.
    failing_fields : Optional[List[str]]
        List of field names that failed validation (e.g., ["pump_curve_name"]).
        Used for structured reporting.
    component_data : Optional[Dict[str, Any]]
        Full component data dictionary. If provided, this overrides the
        automatically captured data from the target.
    **context : Any
        Arbitrary contextual metadata, for example the name that could not be
        resolved. Keys should be short and stable.

    Notes
    -----
    Prefer a bare ``assert`` when no context is needed; the assertion message
    becomes the issue message and the rule stays a single line.

    Examples
    --------
    >>> @network_rule(code="E_UNKNOWN_CURVE", attribute="pump_curve_name")
    ... def rule_pump_curve_exists(network) -> None:
    ...     \"\"\"A pump must reference an existing curve.\"\"\"
    ...     for pump in network.links:
    ...         curve = pump.data.get("pump_curve_name")
    ...         if curve and curve not in network.index.curves:
    ...             raise RuleViolation(
    ...                 "Unknown pump curve",
    ...                 failing_fields=["pump_curve_name"],
    ...                 component_data=pump.data,
    ...                 curve=curve,
    ...                 pump=pump.name
    ...             )
    """

    def __init__(
        self,
        message: str,
        *,
        failing_fields: Optional[List[str]] = None,
        component_data: Optional[Dict[str, Any]] = None,
        **context: Any,
    ) -> None:
        super().__init__(message)
        self.context: Dict[str, Any] = context
        self.failing_fields: List[str] = failing_fields or []
        self.component_data: Dict[str, Any] = component_data or {}


def _is_implicit_rule(func: Callable[..., Any]) -> bool:
    """Check if a function follows the implicit rule naming convention."""
    name = func.__name__
    return name.startswith("rule_") or name.startswith("warn_")


def _is_implicit_network_rule(func: Callable[..., Any]) -> bool:
    """Check if a function follows the implicit network rule naming convention.
    
    Network rules must use @network_rule decorator explicitly since there's
    no naming convention to distinguish them from component rules.
    """
    return False


def _create_implicit_spec(func: Callable[..., Any]) -> RuleSpec:
    """Create a RuleSpec for an implicitly discovered rule function."""
    name = func.__name__
    severity = Severity.WARNING if name.startswith("warn_") else Severity.ERROR
    component_type = _target_name(func)
    
    # Get description from @described decorator or docstring
    description = getattr(func, "description", "") or extract_quick_description(func) or name
    
    # Check if function has @match decorator applied (it wraps the function)
    # The match decorator adds a __wrapped__ attribute pointing to the original
    wrapped = getattr(func, "__wrapped__", func)
    
    spec = RuleSpec(
        rule_id=name,
        func=func,
        component_type=component_type,
        severity=severity,
        code="",
        attribute=None,
        description=description,
        is_network=False,
    )
    return spec


def collect_rules(module: ModuleType) -> Tuple[List[RuleSpec], List[RuleSpec]]:
    """Collect the rules declared in a module.

    Rules can be declared in two ways:
    
    1. Explicit: using ``@rule`` or ``@network_rule`` decorators (backward compatible)
    2. Implicit: functions named ``rule_*`` (error) or ``warn_*`` (warning) 
       are auto-discovered. Component type inferred from type annotation.
    
    Network-level rules must use ``@network_rule`` explicitly.

    Parameters
    ----------
    module : ModuleType
        Module to scan. Only attributes defined in the module itself are
        considered, so re-exported rules are not collected twice.

    Returns
    -------
    Tuple[List[RuleSpec], List[RuleSpec]]
        A pair ``(component_rules, network_rules)``, each sorted by
        ``rule_id`` so that report ordering is deterministic.

    Raises
    ------
    RuleExecutionError
        If two rules in the module share a ``rule_id``, which would make
        issue provenance ambiguous.

    Examples
    --------
    >>> from types import ModuleType
    >>> import epanetparser.core_rules.epanet_core.nodes as nodes
    >>> component_rules, network_rules = collect_rules(nodes)
    >>> len(network_rules)
    0
    """
    component_rules: List[RuleSpec] = []
    network_rules: List[RuleSpec] = []
    for name, value in sorted(vars(module).items()):
        if not callable(value):
            continue
        
        # Check for explicit decorators first (backward compatibility)
        spec = getattr(value, RULE_ATTRIBUTE, None)
        is_network = False
        if spec is None:
            spec = getattr(value, NETWORK_RULE_ATTRIBUTE, None)
            is_network = True
        
        if spec is not None:
            # Explicit decorator found
            if getattr(spec.func, "__module__", module.__name__) != module.__name__:
                # Re-exported from another module; that module collects it.
                continue
            if spec.is_network or is_network:
                network_rules.append(spec)
            else:
                component_rules.append(spec)
        elif _is_implicit_rule(value):
            # Implicit discovery: rule_* or warn_* function
            if getattr(value, "__module__", module.__name__) != module.__name__:
                # Re-exported from another module; that module collects it.
                continue
            if _is_implicit_network_rule(value):
                network_rules.append(_create_implicit_spec(value))
            else:
                component_rules.append(_create_implicit_spec(value))
        # Otherwise not a rule function, skip
    
    _reject_duplicates(component_rules, "component", module)
    _reject_duplicates(network_rules, "network", module)
    component_rules.sort(key=lambda spec: spec.rule_id)
    network_rules.sort(key=lambda spec: spec.rule_id)
    return component_rules, network_rules


def _reject_duplicates(
    specs: List[RuleSpec],
    kind: str,
    module: ModuleType,
) -> None:
    """Raise if ``specs`` contains two rules with the same ``rule_id``."""
    seen: Dict[str, RuleSpec] = {}
    for spec in specs:
        if spec.rule_id in seen:
            raise RuleExecutionError(
                f"Duplicate {kind} rule '{spec.rule_id}' in module "
                f"'{module.__name__}'"
            )
        seen[spec.rule_id] = spec
