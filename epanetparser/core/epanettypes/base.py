"""Base class for EPANET network component types.

Every EPANET component, whether it is a junction, a pipe, a pattern or the
network options block, is a thin wrapper around the dictionary the parser
produced. :class:`WNTREPANETType` provides that wrapper's contract: a ``data``
attribute, read-only accessors for the fields a component is expected to have,
serialisation, and a ``validate()`` entry point.

Validation is deliberately *not* part of assignment. ``component.data = ...``
stores a dictionary; it never runs a rule and never raises a validation error.
Rules live outside the model, in rule sets discovered by
:mod:`epanetparser.core.validation`, and run only when ``validate()`` is
called. This keeps parsing, validation and simulation separable, and it means
custom rules can be added without subclassing or modifying these classes.

Classes
-------
WNTREPANETType
    Abstract base class for all EPANET network components.

Notes
-----
Subclasses implement the abstract :attr:`WNTREPANETType.type` property to name
the concrete component type, such as ``"Junction"`` or ``"Pipe"``.

Examples
--------
>>> from epanetparser.core.epanettypes.base import WNTREPANETType
>>> class Junction(WNTREPANETType):
...     @property
...     def type(self) -> str:
...         return "Junction"
>>> junction = Junction({"name": "J1", "elevation": 100.0})
>>> junction.type
'Junction'
>>> junction.validate().is_valid
True

See Also
--------
epanetparser.core.validation : Rule execution and structured results.
epanetparser.core.epanettypes.node : Node components.
epanetparser.core.epanettypes.link : Link components.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json

from epanetparser.core.validation import ValidationReport


class WNTREPANETType(ABC):
    """Abstract base class for all EPANET network components.

    A component owns a ``data`` dictionary and nothing else. Accessors are
    derived from that dictionary so that the parser can hand over whatever the
    source document contained, including fields this version of the parser
    does not know about.

    Attributes
    ----------
    data : Dict[str, Any]
        The component's fields, exactly as parsed. Assignment is plain
        attribute assignment and performs no validation.
    component_kind : Optional[str]
        Name of the component collection the component belongs to, for
        example ``"nodes"``. Used when reporting issues against a network and
        by the statistics helper; not required for validation, which selects
        rules by class name.

    Methods
    -------
    validate
        Run the selected validation rules against this component.
    as_dict
        Return the component's fields as a dictionary.
    as_json
        Return the component's fields as a JSON string.

    Notes
    -----
    ``data`` is a plain attribute rather than a descriptor. Validation
    results are returned by :meth:`validate` and are not cached on the
    instance, so two calls with the same context return equal reports and a
    stale report can never be mistaken for a current one.

    Examples
    --------
    >>> from epanetparser.core.epanettypes import WNTREPANETNode
    >>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction", "elevation": 10.0})
    >>> node.data = {"name": "J1", "node_type": "Junction"}   # no validation
    >>> report = node.validate()
    >>> report.is_valid
    False
    >>> report.codes()
    ['E_JUNCTION_HAS_ELEVATION']
    """

    #: Collection this component belongs to within a network. Optional.
    component_kind: Optional[str] = None

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Store the component's fields.

        Parameters
        ----------
        data : Optional[Dict[str, Any]]
            Fields parsed from the source document.
        """
        self.data: Dict[str, Any] = data if data is not None else {}

    def validate(self, context: Any = None) -> ValidationReport:
        """Run the selected validation rules against this component.

        Parameters
        ----------
        context : Any
            Rule set selection. Anything
            :meth:`~epanetparser.core.validation.engine.ValidationContext.from_any`
            accepts: a rule set key, a sequence of keys, a context, or a
            mapping with ``core`` and ``custom`` entries. Defaults to the core
            rule set alone.

        Returns
        -------
        ValidationReport
            Structured result. Check
            :attr:`~epanetparser.core.validation.results.ValidationReport.is_valid`;
            no exception is raised for a rule failure.

        Notes
        -----
        This method contains no rule logic of its own; it delegates to the
        engine, which selects rule sets by class name. Subclasses therefore do
        not need to override it, and custom rules apply to existing component
        classes unchanged.

        Raises
        ------
        RuleSetSelectionError
            If ``context`` names a rule set that has not been discovered, or
            does not select exactly one core rule set.
        RuleExecutionError
            If a selected rule raises an exception other than
            ``AssertionError``, which indicates a defect in the rule.

        Examples
        --------
        >>> from epanetparser.core.epanettypes import WNTREPANETNode
        >>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        >>> node.validate().is_valid
        False
        """
        from epanetparser.core.validation import validate

        return validate(self, context)

    def as_dict(self) -> Dict[str, Any]:
        """Return the component's fields as a dictionary.

        Returns
        -------
        Dict[str, Any]
            The component's ``data``. The returned dictionary is the live one,
            not a copy, so callers that intend to modify the model should copy
            it first.

        Examples
        --------
        >>> WNTREPANETType  # doctest: +SKIP
        >>> node.as_dict()["name"]
        'J1'
        """
        return self.data

    def as_json(self) -> str:
        """Return the component's fields as a JSON string.

        Returns
        -------
        str
            JSON representation of :meth:`as_dict`.

        Examples
        --------
        >>> WNTREPANETType  # doctest: +SKIP
        >>> node.as_json()
        '{"name": "J1"}'
        """
        return json.dumps(self.data)

    @property
    @abstractmethod
    def type(self) -> str:
        """Concrete type identifier of the component.

        Subclasses return the EPANET type, such as ``"Junction"``,
        ``"Reservoir"``, ``"Tank"``, ``"Pipe"``, ``"Pump"`` or ``"Valve"``.
        Rules restricted with ``@match`` compare against this value.
        """
