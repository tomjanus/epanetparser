"""Decorators for EPANET component validation.

This module provides lightweight decorators for validation rules.
Separated to avoid circular imports with utils and epanettypes.

Functions
---------
extract_quick_description
    Extract brief description from a function's docstring.
described
    Decorator to add a 'description' attribute to a function based on its docstring.
match
    Decorator to apply validation rules only to components of a specific type.
    
Classes
-------
DescribedCallable
    Protocol for a callable with a 'description' attribute.
"""
from typing import Any, Protocol, ParamSpec, TypeVar, Optional, cast, overload
from enum import Enum
from dataclasses import dataclass
import inspect
from collections.abc import Callable
import functools

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])
P = ParamSpec("P")
R = TypeVar("R")

class RuleType(str, Enum):
    """Enumeration of rule severities used by validation decorators.

    Attributes
    ----------
    ERROR : str
        Indicates that a rule violation should be treated as an error.
    WARNING : str
        Indicates that a rule violation should be treated as a warning.
    """

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class RuleMetadata:
    """Container for metadata attached to a registered validation rule.

    Attributes
    ----------
    component_type : str
        Component type this rule applies to (for example, ``Junction``).
    rule_type : RuleType
        Severity classification for the rule.
    name : str or None
        Optional explicit rule name used for registration and replacement.
    replace : bool
        Whether this rule should replace an existing rule with the same name.
    """

    component_type: str
    rule_type: RuleType
    name: str | None
    replace: bool = False


class RuleMethod(Protocol[P, R]):
    """Protocol describing a callable rule with attached registration metadata.

    Attributes
    ----------
    __rule_metadata__ : RuleMetadata
        Metadata populated by :func:`register_rule`.
    """

    __rule_metadata__: RuleMetadata

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        ...
        

class DescribedCallable(Protocol[P, R]):
    """
    Protocol for a callable that carries a human-readable description.

    This is used to attach metadata (typically extracted from a docstring
    or provided via decorator override) to validation or rule functions.

    Attributes
    ----------
    description : str
        Human-readable description of the callable.
    """
    description: str
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        ...


class DescribedRuleMethod(
    RuleMethod[P, R],
    DescribedCallable[P, R],
    Protocol[P, R],
):
    """Protocol combining descriptive and rule-registration metadata.

    Notes
    -----
    This protocol is satisfied by callables that provide both a
    ``description`` attribute and ``__rule_metadata__`` metadata.
    """

    pass


def register_rule(
    component_type: str,
    rule_type: RuleType | str,
    *,
    name: str | None = None,
    replace: bool = False):
    """ Decorator to register a validation rule for a specific component type. """
    rule_type = RuleType(rule_type)
    def decorator(func: Callable[P, R]) -> RuleMethod[P, R]:
        func.__rule_metadata__ = RuleMetadata(
            component_type=component_type,
            rule_type=rule_type,
            name=name,
            replace=replace,
        ) # attach metadata
        return cast(RuleMethod[P, R], func)
    return decorator


def extract_quick_description(func: Callable, use_summary: bool = True) -> str:
    """
    Extract a short human-readable description from a function docstring.

    Priority:
    1. RST-style ':summary:' field (if `use_summary=True`)
    2. First non-empty line of the docstring (PEP 257 style)
    
    Parameters
    ----------
    func : Callable
        Function or method to extract description from.
    use_summary : bool, optional
        If True, attempts to extract a ':summary:' field from the docstring.
        If not found or False, falls back to the first docstring line.
    
    Returns
    -------
    str
        Brief description, or empty string if no docstring exists.
    
    Examples
    --------
    Standard docstring:

    >>> def f():
    ...     \"\"\"Validate positive value.\"\"\"
    ...     pass
    >>> extract_quick_description(f)
    'Validate positive value.'

    With :summary: field:

    >>> def f():
    ...     \"\"\"Validate tank.
    ...
    ...     :summary: Ensure tank configuration is valid.
    ...     \"\"\"
    >>> extract_quick_description(f)
    'Ensure tank configuration is valid.'
    
    Notes
    -----
    When `use_summary=True`, the function searches for a line matching the pattern
    `:summary: <text>` in the docstring. The text after the colon is extracted.
    
    If no `:summary:` field is found or `use_summary=False`, the first line of
    the docstring is used, following PEP 257 and Numpy docstring conventions.
    
    See Also
    --------
    get_rule_methods : Uses this function to extract rule descriptions
    get_warning_methods : Uses this function to extract warning descriptions
    """
    doc = inspect.getdoc(func)
    if not doc:
        return ""
    if use_summary:
        import re # pylint: disable=import-outside-toplevel
        summary_match = re.search(r':summary:\s*(.+)', doc, re.IGNORECASE)
        if summary_match:
            return summary_match.group(1).strip()
    first_line = doc.split('\n', maxsplit=1)[0] # Fall back to first line
    return first_line


@overload
def described(func: Callable[P, R]) -> DescribedCallable[P, R]: ...

@overload
def described(desc: str) -> Callable[[Callable[P, R]], DescribedCallable[P, R]]: ...

def described(func_or_desc: Optional[Callable[P, R] | str] = None) -> Callable[[Callable[P, R]], DescribedCallable[P, R]] | DescribedCallable[P, R]:
    """
    Decorator that attaches a human-readable description to a function.

    The description is determined in the following order:
    1. Explicit override string passed to the decorator
    2. Extracted docstring summary (via `extract_quick_description`)
    3. Function name fallback

    Supports both direct usage and parameterized usage.

    Examples
    --------
    >>> @described
    ... def rule_x():
    ...     \"\"\"Check validity.\"\"\"
    ...     pass

    >>> rule_x.description
    'Check validity.'

    >>> @described("Custom description")
    ... def rule_y():
    ...     pass
    """
    # CASE 1: @described
    if callable(func_or_desc):
        func = func_or_desc
        func.description = extract_quick_description(func) or func.__name__
        return cast(DescribedCallable[P, R], func)
    # CASE 2: @described("...")
    def decorator(func: Callable[P, R]) -> DescribedCallable[P, R]:
        override = func_or_desc
        if isinstance(override, str) and override.strip():
            func.description = override.strip()
        else:
            func.description = extract_quick_description(func) or func.__name__
        return cast(DescribedCallable[P, R], func)
    return decorator


def match(typename: str, fuzzy: bool = False) -> Callable[[F], F]:
    """Decorator to apply validation rules only to components of a specific type.
    
    This decorator wraps validation rule methods to execute only when the component's
    'type' attribute matches the specified typename. All comparisons are case-insensitive.
    
    The decorated validation method will only execute when the instance's type matches
    the specified typename. If the type doesn't match, the method returns None without
    executing the validation logic.
    
    Parameters
    ----------
    typename : str
        Type name to match against (e.g., 'Junction', 'Pipe', 'Tank').
        Comparison is case-insensitive.
    fuzzy : bool, default=False
        If True, match if typename appears anywhere in the component's type.
        If False, require exact match (case-insensitive).
    
    Returns
    -------
    Callable[[F], F]
        Decorator function that wraps the validation method while preserving
        its signature and metadata.
    
    Examples
    --------
    >>> @match('Junction')
    ... def rule_junction_has_elevation(self) -> None:
    ...     assert "elevation" in self.data, "Junction must have elevation"
    
    >>> @match('Tank')
    ... def rule_tank_has_diameter(self) -> None:
    ...     assert "diameter" in self.data, "Tank must have diameter"
    
    >>> @match('Valve', fuzzy=True)
    ... def rule_valve_check(self) -> None:
    ...     # Matches 'PRV', 'PSV', 'PBV', 'FCV', 'TCV', 'GPV' (any type containing 'valve')
    ...     assert self.data.get("setting") is not None
    """
    def type_wrapper(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            # Skip validation if instance doesn't have a type attribute
            if not (hasattr(self, "type") and self.type):
                return None
            type_lower = self.type.lower()
            typename_lower = typename.lower()
            # Determine if type matches based on fuzzy flag
            if fuzzy:
                is_match = typename_lower in type_lower
            else:
                is_match = typename_lower == type_lower
            # Execute wrapped function only if type matches
            if is_match:
                return func(self, *args, **kwargs)
            return None
        return wrapper  # type: ignore[return-value]
    return type_wrapper


if __name__ == "__main__":
    pass
