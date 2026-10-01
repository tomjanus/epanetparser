"""Utilities for parsing and reporting EPANET model results.

This module holds the small pieces shared by the parser, the display layer and
the tests: the context manager that decides whether a finding is raised or
collected, the file digest used to identify a model, and re-exports of the
rule and warning introspection helpers.

Introspection
-------------
:func:`get_rule_methods` and :func:`get_warning_methods` discover ``rule_*`` and
``warn_*`` methods on a class or instance. They are kept for inspecting
classes and for the plugins CLI. They are *not* how validation selects rules:
rules are declared with
:func:`~epanetparser.core.validation.rules.rule` in rule set modules and are
found by the registry, not by method-name convention.

Functions
---------
sha256digest
    Calculate the SHA-256 hash digest of a file.
get_rule_methods
    Discover ``rule_*`` methods on a class or instance.
get_warning_methods
    Discover ``warn_*`` methods on a class or instance.
raiseorpush
    Context manager that raises or collects a finding.

Notes
-----
The rule and warning introspection functions are defined in
:mod:`epanetparser.core.discovery` and re-exported here, so that the two
modules can be imported independently without a circular dependency.

Examples
--------
>>> from epanetparser.core.utils import sha256digest
>>> len(sha256digest("model.inp"))
64
"""
from __future__ import annotations

from typing import Any, Optional, Tuple
import hashlib

from epanetparser.core.discovery import (
    MethodInfo,
    discover_classes,
    discover_methods_in_class,
    get_rule_methods,
    get_warning_methods,
)
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle,
)

__all__ = [
    "MethodInfo",
    "discover_classes",
    "discover_methods_in_class",
    "get_rule_methods",
    "get_warning_methods",
    "raiseorpush",
    "sha256digest",
]


class raiseorpush:  # pylint: disable=invalid-name
    """Context manager that raises a finding or pushes it onto a destination.

    Parameters
    ----------
    component : str
        Name of the component being processed, used as the key the finding is
        filed under.
    raise_error : bool
        If True, raise a validation error instead of collecting it.
    raise_warning : bool
        If True, raise a validation warning instead of collecting it. Implies
        ``raise_error``, since a model that warns about something it has
        already rejected is not being reported clearly.
    dest : Any
        Object with ``errors`` and ``warnings`` mappings, typically a parser.
    ignore_warnings : bool
        If True, collect warnings rather than raising them, whatever
        ``raise_warning`` says.

    Notes
    -----
    Only the parser's structural findings pass through this context manager.
    Validation findings are collected into a
    :class:`~epanetparser.core.validation.results.ValidationReport` by the
    engine instead, which is why :meth:`capture_warnings` is not part of it.

    Examples
    --------
    >>> from collections import defaultdict
    >>> dest = type("Dest", (), {"errors": defaultdict(list),
    ...                          "warnings": defaultdict(list)})()
    >>> with raiseorpush("Node", raise_error=False, raise_warning=False, dest=dest):
    ...     raise WNTREPANETTypeValidationErrorBundle(
    ...         "failures", [WNTREPANETTypeValidationError("Node", "r", "boom", "{}")]
    ...     )
    >>> list(dest.errors)
    ['Node']
    """

    def __init__(
        self,
        component: str,
        raise_error: bool,
        raise_warning: bool,
        dest: Any,
        ignore_warnings: bool = False,
    ) -> None:
        self.component = component
        self.raise_error = raise_error
        self.raise_warning = raise_warning if not ignore_warnings else False
        self.ignore_warnings = ignore_warnings
        self.dest = dest
        self.error_set: Tuple[type, ...] = (WNTREPANETTypeValidationErrorBundle,)
        if not raise_error:
            self.error_set = (
                WNTREPANETTypeValidationError,
                WNTREPANETTypeValidationErrorBundle,
            )

    def __enter__(self) -> "raiseorpush":
        """Return self, so the context can be bound to a name."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_obj: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        """Collect or re-raise a validation error bundle.

        Parameters
        ----------
        exc_type : type or None
            Type of the exception in flight, if any.
        exc_obj : BaseException or None
            Exception in flight, if any.
        exc_tb : traceback or None
            Traceback of the exception in flight, if any.

        Returns
        -------
        bool
            True only when a bundle was collected here, so that the exception is
            suppressed. False in every other case, so that an exception the
            manager knows nothing about propagates rather than being swallowed.
        """
        if isinstance(exc_obj, WNTREPANETTypeValidationErrorBundle):
            for error in exc_obj.errors:
                if self.raise_warning or self.raise_error:
                    raise error from None
                self.dest.errors[self.component].append(error)
            return not self.raise_warning
        if isinstance(exc_obj, WNTREPANETTypeValidationError):
            if self.raise_warning or self.raise_error:
                raise exc_obj from None
            self.dest.errors[self.component].append(exc_obj)
            return not self.raise_warning
        return False


def sha256digest(filename: str) -> str:
    """Calculate the SHA-256 hash digest of a file.

    Parameters
    ----------
    filename : str
        Path to the file to hash.

    Returns
    -------
    str
        Hexadecimal digest, 64 characters long.

    Notes
    -----
    The file is read in 64 KiB chunks, so hashing a large model does not
    require holding it in memory. The digest is included in reports so that a
    result can be tied to the exact bytes it was produced from.

    Examples
    --------
    >>> sha256digest("model.inp")   # doctest: +SKIP
    '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
    """
    buffer_size = 64 * 1024
    digest = hashlib.sha256()
    with open(filename, "rb") as handle:
        while True:
            chunk = handle.read(buffer_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
