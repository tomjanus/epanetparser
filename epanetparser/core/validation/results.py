"""Structured results for static validation of EPANET models.

Validation is explicit in this package: nothing is validated implicitly while
a model is built. Rules are executed by the engine
(:mod:`epanetparser.core.validation.engine`) and every rule failure becomes a
:class:`ValidationIssue`. Issues are collected in a :class:`ValidationReport`,
which is the only value returned to callers.

Classes
-------
Severity
    Classification of an issue: ``ERROR``, ``WARNING`` or ``INFO``.
ValidationIssue
    A single rule failure, with a stable ``code`` and the provenance of the
    rule that produced it.
ValidationReport
    Ordered collection of issues with query and presentation helpers.

Notes
-----
``Severity`` values are ordered, so ``Severity.ERROR > Severity.WARNING >
Severity.INFO``. Only ``ERROR`` issues make a report invalid.

Examples
--------
>>> from epanetparser.core.validation import Severity, ValidationIssue
>>> issue = ValidationIssue(
...     code="E_NODE_NAME_MISSING",
...     message="Missing node must have a name",
...     severity=Severity.ERROR,
...     rule_id="rule_node_has_name",
...     ruleset_key="epanet_core",
...     component_type="WNTREPANETNode",
... )
>>> issue.is_error
True
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Iterable, Iterator, List, Optional

from epanetparser.core.toon import encode_validation_report


class Severity(IntEnum):
    """Severity of a :class:`ValidationIssue`.

    Attributes
    ----------
    ERROR : int
        The model violates a rule and cannot be simulated as-is.
    WARNING : int
        The model is valid but contains a questionable or unsupported
        configuration.
    INFO : int
        Informational finding; never affects ``is_valid``.

    Notes
    -----
    Members are ordered by seriousness so that severity comparisons and
    ``max()`` behave as expected.
    """

    ERROR = 3
    WARNING = 2
    INFO = 1

    @classmethod
    def _missing_(cls, value: Any) -> "Severity":
        """Resolve a severity named by string, in any case.

        Reports and configuration refer to severities by name, so
        ``Severity("warning")`` and ``Severity("WARNING")`` both resolve. The
        members are integers so that they order by seriousness; the names are
        what callers write.
        """
        if isinstance(value, str):
            member = cls.__members__.get(value.strip().upper())
            if member is not None:
                return member
        return None

    def __str__(self) -> str:
        """Return the upper-case member name, for example ``ERROR``."""
        return self.name


@dataclass(frozen=True)
class ValidationIssue:
    """A single rule failure produced by the validation engine.

    Attributes
    ----------
    code : str
        Stable, machine-readable identifier of the violated condition, for
        example ``"E_NODE_NAME_MISSING"``. Codes are part of the public API and
        are safe to match on; messages are not.
    message : str
        Human-readable description, taken from the ``AssertionError`` raised
        by the rule.
    severity : Severity
        Classification of the issue.
    rule_id : str
        Name of the rule function that failed.
    ruleset_key : str
        Key of the rule set the rule belongs to (for example
        ``"epanet_core"``).
    component_type : Optional[str]
        Class name of the validated component, or ``"network"`` for
        network-level rules.
    component_name : Optional[str]
        Name of the validated component, if it has one.
    attribute : Optional[str]
        Name of the attribute or field the rule is concerned with, if known.
    component_data : Dict[str, Any]
        Full data dictionary of the validated component (or empty for network
        rules). This allows issues to be self-contained for reporting without
        needing access to the original model.
    context : Dict[str, Any]
        Additional contextual metadata supplied by the engine or the rule.

    Notes
    -----
    Instances are frozen, so a reported finding cannot be edited afterwards.
    They are not hashable, because :attr:`context` is a mutable mapping that a
    rule is expected to build up.

    Examples
    --------
    >>> issue = ValidationIssue(
    ...     code="E_TANK_DIAMETER_MISSING",
    ...     message="Tank does not define a diameter",
    ...     severity=Severity.ERROR,
    ...     rule_id="rule_tank_has_diameter",
    ...     ruleset_key="epanet_core",
    ...     component_type="WNTREPANETNode",
    ...     component_name="T1",
    ...     attribute="diameter",
    ... )
    >>> issue.as_dict()["code"]
    'E_TANK_DIAMETER_MISSING'
    """

    code: str
    message: str
    severity: Severity = Severity.ERROR
    rule_id: str = ""
    ruleset_key: str = ""
    component_type: Optional[str] = None
    component_name: Optional[str] = None
    attribute: Optional[str] = None
    component_data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        """True if this issue has :attr:`Severity.ERROR`."""
        return self.severity is Severity.ERROR

    @property
    def is_warning(self) -> bool:
        """True if this issue has :attr:`Severity.WARNING`."""
        return self.severity is Severity.WARNING

    @property
    def is_info(self) -> bool:
        """True if this issue has :attr:`Severity.INFO`."""
        return self.severity is Severity.INFO

    def __str__(self) -> str:
        target = self.component_name or self.component_type or "model"
        return f"[{self.severity}] {target} '{self.code}' -> {self.message}"

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the issue.

        Returns
        -------
        Dict[str, Any]
            Mapping with the issue ``code``, ``message``, ``severity``,
            ``rule_id``, ``ruleset_key``, ``component_type``,
            ``component_name``, ``attribute``, ``component_data`` and ``context``.

        Examples
        --------
        >>> ValidationIssue(code="E_X", message="m").as_dict()["severity"]
        'ERROR'
        """
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.name,
            "rule_id": self.rule_id,
            "ruleset_key": self.ruleset_key,
            "component_type": self.component_type,
            "component_name": self.component_name,
            "attribute": self.attribute,
            "component_data": dict(self.component_data),
            "context": dict(self.context),
        }


class ValidationReport:
    """Ordered collection of :class:`ValidationIssue` objects.

    Attributes
    ----------
    issues : List[ValidationIssue]
        Issues in the order they were produced by the engine.

    Notes
    -----
    The report is a plain mutable container: the engine is the only component
    that appends to it during a run. Callers may filter, group or serialise it
    but are not expected to mutate it.

    Examples
    --------
    >>> report = ValidationReport([
    ...     ValidationIssue(code="E_A", message="a"),
    ...     ValidationIssue(code="W_B", message="b", severity=Severity.WARNING),
    ... ])
    >>> report.is_valid
    False
    >>> len(report.warnings)
    1
    >>> [issue.code for issue in report.as_dict()["issues"]] is None
    False
    """

    def __init__(self, issues: Optional[Iterable[ValidationIssue]] = None) -> None:
        """Create a report from an iterable of issues.

        Parameters
        ----------
        issues : Optional[Iterable[ValidationIssue]]
            Issues to seed the report with. A new list is created, so the
            caller's iterable is never aliased.
        """
        self.issues: List[ValidationIssue] = list(issues) if issues else []

    def __iter__(self) -> Iterator[ValidationIssue]:
        """Iterate over the issues in insertion order."""
        return iter(self.issues)

    def __len__(self) -> int:
        """Return the total number of issues."""
        return len(self.issues)

    def __bool__(self) -> bool:
        """Return True when the report holds at least one issue."""
        return bool(self.issues)

    def __repr__(self) -> str:
        return (
            f"ValidationReport(errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, info={len(self.info)})"
        )

    def __str__(self) -> str:
        if not self.issues:
            return "ValidationReport(no issues)"
        body = "\n".join(f"  {issue}" for issue in self.issues)
        return f"ValidationReport({len(self.issues)} issues)\n{body}"

    def add(self, issue: ValidationIssue) -> None:
        """Append a single issue to the report."""
        self.issues.append(issue)

    def extend(self, issues: Iterable[ValidationIssue]) -> None:
        """Append several issues to the report."""
        self.issues.extend(issues)

    @property
    def errors(self) -> List[ValidationIssue]:
        """Issues with :attr:`Severity.ERROR`."""
        return [issue for issue in self.issues if issue.is_error]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Issues with :attr:`Severity.WARNING`."""
        return [issue for issue in self.issues if issue.is_warning]

    @property
    def info(self) -> List[ValidationIssue]:
        """Issues with :attr:`Severity.INFO`."""
        return [issue for issue in self.issues if issue.is_info]

    @property
    def is_valid(self) -> bool:
        """True when the report contains no :attr:`Severity.ERROR` issues.

        Notes
        -----
        Warnings and informational issues do not invalidate a model. A report
        with no issues at all is valid.
        """
        return not self.errors

    def by_severity(self, severity: Severity) -> List[ValidationIssue]:
        """Return the issues with the requested severity.

        Parameters
        ----------
        severity : Severity
            Severity to filter on. Plain strings are accepted and converted.

        Returns
        -------
        List[ValidationIssue]
            Matching issues in insertion order.
        """
        return [issue for issue in self.issues if issue.severity is Severity(severity)]

    def by_code(self, code: str) -> List[ValidationIssue]:
        """Return the issues with the requested stable ``code``.

        Parameters
        ----------
        code : str
            Stable issue code, for example ``"E_NODE_NAME_MISSING"``.

        Returns
        -------
        List[ValidationIssue]
            Matching issues in insertion order.
        """
        return [issue for issue in self.issues if issue.code == code]

    def by_rule(self, rule_id: str) -> List[ValidationIssue]:
        """Return the issues produced by the named rule.

        Parameters
        ----------
        rule_id : str
            Name of the rule function, for example ``"rule_node_has_name"``.

        Returns
        -------
        List[ValidationIssue]
            Matching issues in insertion order.
        """
        return [issue for issue in self.issues if issue.rule_id == rule_id]

    def by_component(self, component_name: str) -> List[ValidationIssue]:
        """Return the issues reported against the named component.

        Parameters
        ----------
        component_name : str
            Name of the component, for example ``"T1"``.

        Returns
        -------
        List[ValidationIssue]
            Matching issues in insertion order.
        """
        return [issue for issue in self.issues if issue.component_name == component_name]

    def codes(self) -> List[str]:
        """Return the stable codes of all issues, in insertion order."""
        return [issue.code for issue in self.issues]

    def grouped_by_component(self) -> Dict[str, List[ValidationIssue]]:
        """Group the issues by component name for presentation.

        Issues without a component name, which includes network-level issues,
        are collected under the key ``"network"``.

        Returns
        -------
        Dict[str, List[ValidationIssue]]
            Mapping of component name to its issues. This is the shape
            consumed by :func:`epanetparser.core.display.write_results`.

        Examples
        --------
        >>> report = ValidationReport([
        ...     ValidationIssue(code="E_A", message="a", component_name="T1"),
        ...     ValidationIssue(code="E_B", message="b"),
        ... ])
        >>> sorted(report.grouped_by_component())
        ['T1', 'network']
        """
        grouped: Dict[str, List[ValidationIssue]] = {}
        for issue in self.issues:
            key = issue.component_name or "network"
            grouped.setdefault(key, []).append(issue)
        return grouped

    def grouped_by_severity(self) -> Dict[Severity, List[ValidationIssue]]:
        """Group the issues by severity.

        Returns
        -------
        Dict[Severity, List[ValidationIssue]]
            Mapping of severity to its issues. Severities with no issues are
            present with an empty list, so the result always has three keys.
        """
        return {severity: self.by_severity(severity) for severity in Severity}

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable summary of the report.

        Returns
        -------
        Dict[str, Any]
            Mapping with ``is_valid``, the per-severity counts under
            ``counts`` and the full issue list under ``issues``. Each issue is
            serialised with :meth:`ValidationIssue.as_dict`.

        Examples
        --------
        >>> ValidationReport().as_dict()["is_valid"]
        True
        """
        return {
            "is_valid": self.is_valid,
            "counts": {
                Severity.ERROR.name: len(self.errors),
                Severity.WARNING.name: len(self.warnings),
                Severity.INFO.name: len(self.info),
            },
            "issues": [issue.as_dict() for issue in self.issues],
        }

    def as_toon(self) -> str:
        """Return a TOON representation of the validation report.

        Uses tabular form for the issues array for token efficiency.

        Returns
        -------
        str
            TOON-encoded string of the validation report.

        Examples
        --------
        >>> ValidationReport().as_toon()
        'is_valid: true\ncounts: {ERROR: 0, WARNING: 0, INFO: 0}\nissues[0]{}:'
        """
        return encode_validation_report(self.as_dict())
