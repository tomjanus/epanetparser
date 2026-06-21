"""Decorators for EPANET component validation.

This module provides lightweight decorators for validation rules.
Separated to avoid circular imports with utils and epanettypes.

Functions
---------
extract_quick_description
    Extract brief description from a function's docstring.
"""
from typing import Any, Protocol, ParamSpec, TypeVar, cast
import inspect
from collections.abc import Callable
import functools

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])
P = ParamSpec("P")
R = TypeVar("R")


class DescribedCallable(Protocol[P, R]): # pylint: disable=too-few-public-methods
    """Protocol for a callable with a 'description' attribute."""
    description: str
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        ...


def extract_quick_description(func: Callable, use_summary: bool = True) -> str:
    """Extract quick description from a function's docstring.
    
    Extracts a brief summary from a function's docstring, either from an
    RST `:summary:` field or from the first line following PEP 257 conventions.
    
    Parameters
    ----------
    func : Callable
        Function or method to extract description from.
    use_summary : bool, optional
        If True (default), attempt to extract description from `:summary:` RST field.
        Falls back to first line if field not found. If False, always use first line.
    
    Returns
    -------
    str
        Brief description, or empty string if no docstring exists.
    
    Examples
    --------
    From first line (standard):
    
    >>> def my_rule(self):
    ...     '''Validate positive value.
    ...     
    ...     Longer description here.
    ...     '''
    ...     pass
    >>> _extract_quick_description(my_rule)
    'Validate positive value.'
    
    From RST :summary: field:
    
    >>> def my_rule(self):
    ...     '''Validate tank configuration.
    ...     
    ...     :summary: Ensure tank has required parameters.
    ...     
    ...     Longer description here.
    ...     '''
    ...     pass
    >>> _extract_quick_description(my_rule, use_summary=True)
    'Ensure tank has required parameters.'
    
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


def described(func: Callable[P, R]) -> DescribedCallable[P, R]:
    """Decorator adding a 'description' attribute to a function.
    
    The 'description' attribute is extracted from the function's docstring,
    providing a brief summary of the validation rule. Works with both pure
    functions and methods defined in classes.
    
    Parameters
    ----------
    func : Callable[P, R]
        The function or method to decorate.
    
    Returns
    -------
    DescribedCallable[P, R]
        The original function with an added 'description' attribute.
    
    Examples
    --------
    With a pure function:
    
    >>> @described
    ... def validate_positive(value: float) -> None:
    ...     '''Ensure value is positive.'''
    ...     assert value > 0
    >>> validate_positive.description
    'Ensure value is positive.'
    
    With a method in a class:
    
    >>> class Component:
    ...     @described
    ...     def rule_has_name(self) -> None:
    ...         '''Validate that component has a name.'''
    ...         assert hasattr(self, 'name')
    >>> Component.rule_has_name.description
    'Validate that component has a name.'
    """
    setattr(func, "description", extract_quick_description(func))
    return cast(DescribedCallable[P, R], func)


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
