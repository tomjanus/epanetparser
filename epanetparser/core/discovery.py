"""Introspection helpers for EPANET classes and rule methods.

This module answers two kinds of question about Python objects at runtime:
which classes a module defines, and which ``rule_*`` or ``warn_*`` methods a
class or instance carries.

It is not how validation selects rules. Rules are declared with
:func:`~epanetparser.core.validation.rules.rule` in rule set modules and are
found by :mod:`epanetparser.core.validation.discovery`, which works from module
metadata rather than from method-name conventions. What is left here is used to
*describe* classes: by the ``epanetparser-plugins`` command, and by tests.

Functions
---------
discover_classes
    List the classes a module defines, excluding imported ones.
discover_methods_in_class
    List a class's methods, optionally filtered by name prefix, optionally
    including inherited ones.
get_rule_methods
    Discover ``rule_*`` methods on a class or instance.
get_warning_methods
    Discover ``warn_*`` methods on a class or instance.

Classes
-------
FileInfo
    Description of a Python file found in a module or package.
MethodInfo
    Description of a discovered method, with its signature and description.

Notes
-----
Method discovery resolves names through the class's MRO, so a method that a
subclass overrides is reported once, attributed to the subclass. With
``local_only=False`` the report also records where each method was defined and
whether it was inherited.

Examples
--------
>>> from epanetparser.core.discovery import discover_classes
>>> import epanetparser.core.epanettypes.link as link_module
>>> [cls.__name__ for cls in discover_classes(link_module)]
['WNTREPANETLink']
"""
from __future__ import annotations

from typing import List, Dict, Optional, Callable, cast
from typing import ParamSpec, TypeVar, TYPE_CHECKING
from dataclasses import dataclass, asdict
import inspect
from types import ModuleType

from rich.panel import Panel
from rich.text import Text
from epanetparser.core.decorators import DescribedCallable, extract_quick_description
from epanetparser.core.logger_setup import get_logger

if TYPE_CHECKING:
    from epanetparser.core.epanettypes.base import WNTREPANETType

logger = get_logger(__name__, level="WARNING")
P = ParamSpec("P")
R = TypeVar("R")

__all__ = [
    "FileInfo",
    "MethodInfo",
    "discover_classes",
    "discover_methods_in_class",
    "get_rule_methods",
    "get_warning_methods",
]


@dataclass
class FileInfo:
    """Information about a Python file in a module or package.
    
    Attributes
    ----------
    name : str
        Module name without extension (e.g., 'demo_rules').
    file_path : str
        Full absolute path to the .py file.
    module_path : str
        Full import path (e.g., 'epanetparser.rules.demo.demo_rules').
    """
    name: str
    file_path: str
    module_path: str
    
    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return f"FileInfo(name={self.name!r}, file_path={self.file_path!r}, module_path={self.module_path!r})"
    
    def __str__(self) -> str:
        """Return a simple string representation."""
        return f"📄 {self.name} ({self.module_path})"
    
    def __rich__(self):
        """Return a rich representation for pretty printing.
        
        Returns
        -------
        Panel
            A rich Panel with file information.
        """
        content = Text()
        content.append("📄 ", style="bold")
        content.append(self.name, style="cyan bold")
        content.append("\n\n")
        content.append("Path: ", style="yellow")
        content.append(self.file_path, style="dim")
        content.append("\n")
        content.append("Module: ", style="yellow")
        content.append(self.module_path, style="dim")
        return Panel(content, title=f"[bold]File: {self.name}[/bold]", border_style="blue")

    def to_dict(self) -> dict:
        """ Convert the FileInfo instance to a dictionary. """
        return asdict(self)

@dataclass
class MethodInfo:
    """Information about a method discovered in a class.
    
    Attributes
    ----------
    method : Callable | DescribedCallable
        The method object itself.
    description : Optional[str]
        Description extracted from the method's docstring.
    signature : str
        Method signature string (e.g., '(self, arg1, arg2) -> None').
    origin : Optional[str]
        Name of the class where the method is defined (only present when local_only=False).
    is_inherited : Optional[bool]
        Whether the method is inherited from a parent class (only present when local_only=False).
    """
    method: Callable | DescribedCallable
    description: Optional[str]
    signature: str
    origin: Optional[str] = None
    is_inherited: Optional[bool] = None
    
    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        parts = [f"method={self.method.__name__!r}", f"signature={self.signature!r}"]
        if self.origin is not None:
            parts.append(f"origin={self.origin!r}")
        if self.is_inherited is not None:
            parts.append(f"is_inherited={self.is_inherited!r}")
        return f"MethodInfo({', '.join(parts)})"
    
    def __str__(self) -> str:
        """Return a simple string representation."""
        method_name = self.method.__name__
        base = f"{method_name}{self.signature}"
        if self.origin and self.is_inherited:
            base += f" [inherited from {self.origin}]"
        if self.description:
            base += f"\n  {self.description}"
        return base
    
    def __rich__(self):
        """Return a rich representation for pretty printing.
        
        Returns
        -------
        Panel
            A rich Panel with method information.
        """
        method_name = self.method.__name__
        content = Text()
        content.append("• ", style="bold")
        content.append(method_name, style="yellow bold")
        content.append(self.signature, style="cyan")
        if self.origin is not None:
            content.append("\n\n")
            content.append("Origin: ", style="magenta")
            content.append(self.origin, style="magenta bold")
            if self.is_inherited:
                content.append(" (inherited)", style="dim italic")
        if self.description:
            content.append("\n\n")
            content.append(self.description, style="dim italic")
        return Panel(
            content, 
            title=f"[bold]Method: {method_name}[/bold]",
            border_style="yellow")

    def to_dict(self) -> dict:
        """ Convert the MethodInfo instance to a dictionary. """
        return asdict(self)




def discover_classes(module: ModuleType) -> List[type]:
    """Discover all classes defined in a module.
    
    Parameters
    ----------
    module : ModuleType
        The module to inspect for class definitions.
    
    Returns
    -------
    List[type]
        List of all classes defined in the module (excludes imported classes).
    
    Notes
    -----
    Only returns classes that are actually defined in the module
    (checks that `cls.__module__ == module.__name__`).
    """
    return [
        _cls
        for _, _cls in inspect.getmembers(module, inspect.isclass)
        if _cls.__module__ == module.__name__
    ]

def discover_methods_in_class(
    target_cls: type,
    prefix: Optional[str] = None,
    local_only: bool = True,
    append_description: bool = False
) -> Dict[str, MethodInfo]:
    """Discover methods in a class, optionally filtered by prefix.
    
    Parameters
    ----------
    target_cls : type
        The class to inspect for methods.
    prefix : Optional[str], default=None
        If provided, only return methods whose names start with this prefix.
        If None, return all methods.
    local_only : bool, default=True
        If True, only return methods defined directly in `target_cls`.
        If False, includes inherited methods and populates 'origin' and 'is_inherited' fields.
    
    Returns
    -------
    Dict[str, MethodInfo]
        Dictionary mapping method names to MethodInfo objects.
    
    Examples
    --------
    >>> from epanetparser.rulesets.milp import MILPNode
    >>> methods = discover_methods_in_class(MILPNode, prefix='rule_')
    >>> for name, info in methods.items():
    ...     print(f"{name}: {info.description}")
    
    Note
    ----
    This method excludes static and class methods, returning only instance methods.
    It uses classes MRO (method resolution order) `__mro__` field to determine 
    which methods are inherited vs. defined locally. It skips the base `object` class.
    """
    _methods = {}
    # target_cls.__mro__ contains [target_cls, ParentClass, GrandparentClass, ..., object]
    classes_to_scan = [target_cls] if local_only else target_cls.__mro__
    for current_class in classes_to_scan:
        # Stop before inspecting the base 'object' class methods (like __init__)
        if current_class is object:
            continue
        for _name, _descriptor in current_class.__dict__.items():
            # If we already found an overridden version of this method in a
            # child class deeper in the loop, skip the parent's version.
            if _name in _methods:
                continue
            if prefix and not _name.startswith(prefix):
                continue
            if _name.startswith('__') and (prefix is None or not prefix.startswith('__')):
                continue
            if isinstance(_descriptor, (staticmethod, classmethod)): # exclude staticmethods and classmethods
                continue
            # Fetch the actual resolved method object (unbound function)
            _method = getattr(target_cls, _name)
            if not inspect.isroutine(_method): # Double check it's an actual routine/callable
                continue
            try:
                sig = str(inspect.signature(_method)) # Extract signature safely
            except (ValueError, TypeError):
                sig = "()"
            if append_description:
                _append_description(_method)
            # Create MethodInfo object
            if local_only:
                method_info = MethodInfo(
                    method=_method,
                    description=extract_quick_description(_method),
                    signature=sig
                )
            else:
                method_info = MethodInfo(
                    method=_method,
                    description=extract_quick_description(_method),
                    signature=sig,
                    origin=current_class.__name__,
                    is_inherited=(current_class is not target_cls)
                )
            _methods[_name] = method_info
    return _methods







def _get_methods_from_object(
        obj: type | WNTREPANETType,
        prefix: str,
        append_description: bool = False) -> Dict[str, MethodInfo]:
    """Helper method to normalize instance and class validation discovery.
    
    Parameters
    ----------
    obj : type or WNTREPANETType
        The class or instance to inspect for methods.
    prefix : str
        The prefix to filter method names (e.g., 'rule_' or 'warn_').
    append_description : bool, default=False
        If True, appends a 'description' attribute to each discovered method.
        
    Returns
    -------
    Dict[str, MethodInfo]
        Dictionary mapping method names to MethodInfo objects.
    """
    is_cls = inspect.isclass(obj) # true if obj is a class, false if it's not - e.g. it is an instance or a function
    target_cls = obj if is_cls else type(obj)
    # Extract base method details using deep lookups 
    # (local_only=False allows ruleset inheritance mapping)
    discovered = discover_methods_in_class(
        target_cls,
        prefix=prefix,
        local_only=False,
        append_description=append_description
    )
    # If dealing with an instance, bind the discovered functions to the live
    # instance
    if not is_cls:
        for _name, _info in discovered.items():
            bound_method = getattr(obj, _name)
            discovered[_name] = MethodInfo(
                method=bound_method,
                description=_info.description,
                signature=_info.signature,
                origin=_info.origin,
                is_inherited=_info.is_inherited
            )
    return discovered


def _append_description(func: Callable[P, R]) -> None:
    """Append a 'description' attribute to a function or method if not 
    already present.
    """
    target = func.__func__ if inspect.ismethod(func) else func
    target = cast(DescribedCallable[P, R], target)
    if not hasattr(target, "description"):
        target.description = extract_quick_description(func)


def get_rule_methods(
    obj: type | WNTREPANETType,
    append_description: bool = False
    ) -> Dict[str, MethodInfo]:
    """Retrieve validation rule methods from a component class or instance.
    
    Discovers all validation rule methods defined on a component class or instance.
    Rule methods are identified by the 'rule_' prefix in their name. Works with
    both classes (returning unbound functions) and instances (returning bound methods).
    
    Parameters
    ----------
    obj : type or WNTREPANETType
        Component class or instance to introspect for rule methods.
        If a class, returns unbound functions in MethodInfo objects.
        If an instance, returns bound methods in MethodInfo objects.
    append_description : bool, default=False
        If True, appends a 'description' attribute to each discovered method.
    
    Returns
    -------
    Dict[str, MethodInfo]
        Dictionary mapping rule method names to MethodInfo objects.
        Keys are method names (e.g., 'rule_positive_length').
        Values are MethodInfo objects containing:
        - method: Callable (unbound function for classes, bound method for instances)
        - description: str (brief description from docstring)
        - signature: str (method signature)
        - origin: Optional[str] (class where method is defined, if inherited)
        - is_inherited: Optional[bool] (True if method is inherited from a parent class)
    
    Examples
    --------
    From instance (bound methods):
    
    >>> from epanetparser.core.epanettypes import WNTREPANETNode
    >>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
    >>> rules = get_rule_methods(node)
    >>> print(list(rules.keys()))
    ['rule_node_has_name', 'rule_node_has_valid_type', ...]
    >>> rules['rule_node_has_name'].method()  # Execute validation rule
    >>> print(rules['rule_node_has_name'].description)  # Get description
    
    From class (unbound functions):
    
    >>> rules = get_rule_methods(WNTREPANETNode)
    >>> for name, info in rules.items():
    ...     print(f"{name}: {info.description}")
    
    Compare base vs ruleset classes:
    
    >>> from epanetparser.core.epanettypes import WNTREPANETLink
    >>> from epanetparser.rulesets.milp import MILP_Links
    >>> base_rules = set(get_rule_methods(WNTREPANETLink).keys())
    >>> milp_rules = set(get_rule_methods(MILP_Links).keys())
    >>> extra_rules = milp_rules - base_rules
    >>> for rule_name in extra_rules:
    ...     info = get_rule_methods(MILP_Links)[rule_name]
    ...     print(f"{rule_name}: {info.description}")
    
    See Also
    --------
    get_warning_methods : Retrieve warning check methods (also works on classes and instances)
    MethodInfo : Data class containing method, description, signature, origin, and inheritance info
    
    Notes
    -----
    When passed a class, this function uses `inspect.isfunction` to get unbound functions.
    When passed an instance, it uses `inspect.ismethod` to get bound methods.
    Both functions and methods are Callable, so MethodInfo.method is always callable.
    This allows the same function to work seamlessly with both use cases.
    """
    return _get_methods_from_object(obj, prefix="rule", append_description=append_description)


def get_warning_methods(
        obj: type | WNTREPANETType,
        append_description: bool = False
    ) -> Dict[str, MethodInfo]:
    """Retrieve warning check methods from a component class or instance.
    
    Discovers all warning check methods defined on a component class or instance.
    Warning methods are identified by the 'warn_' prefix in their name. Works with
    both classes (returning unbound functions) and instances (returning bound methods).
    
    Parameters
    ----------
    obj : type or WNTREPANETType
        Component class or instance to introspect for warning methods.
        If a class, returns unbound functions in MethodInfo objects.
        If an instance, returns bound methods in MethodInfo objects.
    append_description : bool, default=False
        If True, appends a 'description' attribute to each discovered method.
    
    Returns
    -------
    Dict[str, MethodInfo]
        Dictionary mapping warning method names to described methods.
        Keys are method names (e.g., 'warn_unusual_diameter').
        Values are methods containing a description: str (brief description from docstring)
    
    Examples
    --------
    From instance (bound methods):
    
    >>> from epanetparser.core.epanettypes import WNTREPANETLink
    >>> link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
    >>> warnings = get_warning_methods(link)
    >>> print(list(warnings.keys()))
    ['warn_roughness_coefficient', ...]
    >>> warnings['warn_roughness_coefficient'].method()  # Execute warning
    
    From class (unbound functions):
    
    >>> warnings = get_warning_methods(WNTREPANETLink)
    >>> for name, info in warnings.items():
    ...     print(f"{name}: {info.description}")
    
    Iterate through all warnings:
    
    >>> for warn_name, info in warnings.items():
    ...     print(f"Checking: {warn_name}")
    ...     try:
    ...         info.method()
    ...     except AssertionError as e:
    ...         print(f"Warning: {e}")
    
    Generate documentation from class:
    
    >>> from epanetparser.rulesets.milp import MILP_Links
    >>> warnings = get_warning_methods(MILP_Links)
    >>> for name, info in sorted(warnings.items()):
    ...     print(f"- {name}")
    ...     print(f"  {info.description}")
    
    See Also
    --------
    get_rule_methods : Retrieve validation rule methods (also works on classes and instances)
    MethodInfo : Data class containing method and description
    Notes
    -----
    Warning methods raise `AssertionError` to signal non-fatal issues.
    Unlike rules, warnings don't prevent component creation but are tracked
    for user notification.
    
    When passed a class, this function uses `inspect.isfunction` to get unbound functions.
    When passed an instance, it uses `inspect.ismethod` to get bound methods.
    Both functions and methods are Callable, so MethodInfo method is always callable.
    This allows the same function to work seamlessly with both use cases.
    """
    return _get_methods_from_object(obj, prefix="warn", append_description=append_description)
