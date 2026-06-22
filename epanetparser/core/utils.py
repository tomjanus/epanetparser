"""Utility functions and classes for EPANET parser validation.

This module provides core utilities for validating EPANET network components including:

- Context managers for error/warning aggregation (`raiseorpush`)
- Helper functions for introspecting validation methods (`get_rule_methods`, `get_warning_methods`)
- Description extraction from docstrings (`extract_quick_description`)
- File hashing utilities for data integrity (`sha256digest`)
- Rich logging configuration (`get_logger`, `configure_logging`)

Functions
---------
sha256digest
    Calculate SHA256 hash digest of a file.
get_rule_methods
    Retrieve validation rule methods from a component class or instance.
    Returns Dict[str, ValidatorInfo] mapping method names to ValidatorInfo objects.
get_warning_methods
    Retrieve warning check methods from a component class or instance.
    Returns Dict[str, ValidatorInfo] mapping method names to ValidatorInfo objects.
get_logger
    Get or create a logger with rich formatting for a module.
configure_logging
    Configure global logging settings with rich handler.


Classes
-------
raiseorpush
    Context manager for capturing and aggregating validation errors and warnings.
ValidatorInfo
    Dataclass containing validation method and its description.

Notes
-----
Validation methods follow naming conventions:
- Methods starting with 'rule_' are validation rules
- Methods starting with 'warn_' are warning checks

The introspection functions (`get_rule_methods`, `get_warning_methods`) work with
both component classes (returning unbound functions in ValidatorInfo) and instances
(returning bound methods in ValidatorInfo). All results are consistently returned as
Dict[str, ValidatorInfo], where ValidatorInfo contains the callable method and its
description extracted from the docstring.

Examples
--------
Introspect validation methods on an instance:

>>> from epanetparser.core.epanettypes import WNTREPANETNode
>>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
>>> rules = get_rule_methods(node)
>>> warnings = get_warning_methods(node)
>>> print(f"Rules: {list(rules.keys())}")
>>> # Access method and description from ValidatorInfo
>>> rules['rule_node_has_name'].method()  # Execute
>>> print(rules['rule_node_has_name'].description)  # Get description

Introspect validation methods on a class:

>>> from epanetparser.core.epanettypes import WNTREPANETLink
>>> rules = get_rule_methods(WNTREPANETLink)
>>> for name, info in rules.items():
...     print(f"{name}: {info.description}")
...     # info.method is an unbound function when introspecting a class

Set up rich logging in a module:

>>> from epanetparser.core.utils import get_logger
>>> logger = get_logger(__name__)
>>> logger.info("Processing network")
>>> logger.debug("Detailed information")
>>> logger.error("Something went wrong")

Configure logging at application startup:

>>> from epanetparser.core.utils import configure_logging
>>> import logging
>>> configure_logging(level=logging.DEBUG, show_path=True)

See Also
--------
epanetparser.core.decorators : Validation decorators including @match and @described
epanetparser.core.validation : Descriptor-based validation system
logging : Python standard library logging module
rich.logging.RichHandler : Rich console handler for Python logging

Notes
-----
Logging Best Practices for Library Development:
- Use `get_logger(__name__)` to create module-specific loggers
- Use WARNING as default level in library code (users can override)
- Use % formatting for log messages (lazy evaluation, not f-strings)
- Call `logger.exception()` to include tracebacks when logging errors
- Don't call `configure_logging()` in library code; let users do it
- Check `logger.isEnabledFor(level)` before expensive debug operations
"""
from __future__ import annotations
from typing import Dict, Any, Optional, TYPE_CHECKING
from collections.abc import Callable
import hashlib
import inspect
import logging
from rich.logging import RichHandler
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.core.decorators import extract_quick_description
if TYPE_CHECKING:
    from epanetparser.core.epanet_types.base import WNTREPANETType
    from epanetparser.core.decorators import DescribedCallable


# Global flag to track if logging has been configured
_LOGGING_CONFIGURED = False


class raiseorpush:
    """Context manager for capturing and aggregating validation errors and warnings.
    
    This context manager provides flexible error handling during component parsing
    and validation. It can either raise errors/warnings immediately or collect them
    in a destination object for batch processing.
    
    Parameters
    ----------
    component : str
        Name or type identifier of the component being validated.
    raise_error : bool
        If True, raise validation errors immediately when encountered.
        If False, collect errors in the destination object.
    raise_warning : bool
        If True, raise validation warnings immediately when encountered.
        If False, collect warnings in the destination object.
    dest : Any
        Destination object for collecting errors and warnings. Must have
        'errors' and 'warnings' attributes (typically dictionaries).
    ignore_warnings : bool, optional
        If True, suppress all warning processing entirely. Default is False.
    
    Attributes
    ----------
    component : str
        Component identifier for error/warning messages.
    raise_error : bool
        Whether to raise errors immediately.
    raise_warning : bool
        Whether to raise warnings immediately.
    dest : Any
        Destination for collected errors/warnings.
    ignore_warnings : bool
        Whether warnings are ignored.
    error_set : tuple of type
        Tuple of exception types caught by the context manager.
    
    Examples
    --------
    Collect errors for batch processing:
    
    >>> from collections import defaultdict
    >>> dest = type('Dest', (), {'errors': defaultdict(list), 'warnings': defaultdict(list)})()
    >>> with raiseorpush('Node', raise_error=False, raise_warning=False, dest=dest):
    ...     # Validation code that may raise errors
    ...     pass
    >>> print(dest.errors)  # Check collected errors
    
    Raise errors immediately:
    
    >>> with raiseorpush('Node', raise_error=True, raise_warning=False, dest=dest):
    ...     # This will raise on first error
    ...     pass
    
    See Also
    --------
    WNTREPANETTypeValidationError : Single validation error
    WNTREPANETTypeValidationErrorBundle : Bundle of multiple validation errors
    """
    def __init__(
        self,
        component: str,
        raise_error: bool,
        raise_warning: bool,
        dest: Any,
        ignore_warnings: bool = False
    ) -> None:
        self.component = component
        self.raise_error = raise_error
        self.raise_warning = raise_warning if not ignore_warnings else False
        self.ignore_warnings = ignore_warnings
        self.dest = dest
        self.error_set = (WNTREPANETTypeValidationErrorBundle, )
        if not raise_error:
            self.error_set = (WNTREPANETTypeValidationError, WNTREPANETTypeValidationErrorBundle)

    def __enter__(self) -> 'raiseorpush':
        """Enter the context manager.
        
        Returns
        -------
        raiseorpush
            Self reference for use in 'with' statements.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_obj: Optional[Exception],
        exc_tb: Any
    ) -> bool:
        """Exit the context manager and handle any exceptions.
        
        If a validation error bundle is encountered, errors are either raised
        immediately (if raise_error or raise_warning is True) or collected
        in the destination object for later processing.
        
        Parameters
        ----------
        exc_type : type or None
            Exception type if an exception occurred, None otherwise.
        exc_obj : Exception or None
            Exception instance if an exception occurred, None otherwise.
        exc_tb : traceback or None
            Exception traceback if an exception occurred, None otherwise.
        
        Returns
        -------
        bool
            True to suppress the exception (don't propagate),
            False to propagate the exception.
        
        Notes
        -----
        The context manager catches `WNTREPANETTypeValidationError` and
        `WNTREPANETTypeValidationErrorBundle` exceptions based on the
        configuration set during initialization.
        """
        if isinstance(exc_obj, WNTREPANETTypeValidationErrorBundle):
            for error in exc_obj.errors:
                #  Raise on warning implies raise on error
                if self.raise_warning or self.raise_error:
                    raise error from None
                self.dest.errors[self.component].append(error)
        return not self.raise_warning

    def capture_warnings(self, inst: 'WNTREPANETType') -> None:
        """Capture warnings from a successfully validated instance.
        
        After successful validation, this method checks if the instance has
        any accumulated warnings and either raises them immediately or collects
        them in the destination object, depending on the configuration.
        
        Parameters
        ----------
        inst : WNTREPANETType
            The validated component instance to check for warnings.
        
        Notes
        -----
        This method should be called after successful component instantiation
        to process any non-fatal warnings that were generated during validation.
        
        If `ignore_warnings` is True, this method does nothing.
        """
        if inst.has_warnings and not self.ignore_warnings:
            for warning in inst.warnings:
                if self.raise_warning:
                    raise warning from None
                self.dest.warnings[self.component].append(warning)


def configure_logging(
    level: int | str = logging.INFO,
    show_time: bool = True,
    show_path: bool = False,
    enable_link_path: bool = False,
    log_format: Optional[str] = None
) -> None:
    """Configure global logging with rich formatting.
    
    Sets up the root logger with a RichHandler for beautiful console output.
    This should typically be called once at application startup.
    
    Parameters
    ----------
    level : int or str, default=logging.INFO
        Logging level (e.g., logging.DEBUG, logging.INFO, "DEBUG", "INFO").
    show_time : bool, default=True
        Whether to show timestamps in log output.
    show_path : bool, default=False
        Whether to show the file path in log output.
    enable_link_path : bool, default=False
        Whether to make file paths clickable (IDE integration).
    log_format : Optional[str], default=None
        Custom log format string. If None, uses rich's default format.
    
    Examples
    --------
    Configure logging for development (verbose):
    
    >>> from epanetparser.core.utils import configure_logging
    >>> import logging
    >>> configure_logging(level=logging.DEBUG, show_path=True)
    
    Configure logging for production (less verbose):
    
    >>> configure_logging(level=logging.WARNING, show_time=False)
    
    Configure with custom format:
    
    >>> configure_logging(log_format="%(name)s - %(message)s")
    
    Notes
    -----
    This function configures the root logger, which affects all loggers in
    the application. For library usage, users can override this configuration.
    
    The RichHandler provides:
    - Syntax highlighting for exception tracebacks
    - Pretty formatting for log messages
    - Support for rich markup in messages
    - Automatic indentation of multiline messages
    """
    global _LOGGING_CONFIGURED  # pylint: disable=global-statement
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    # Create rich handler with specified options
    rich_handler = RichHandler(
        show_time=show_time,
        show_path=show_path,
        enable_link_path=enable_link_path,
        rich_tracebacks=True,
        tracebacks_show_locals=level <= logging.DEBUG,  # Show locals in DEBUG mode
        markup=True  # Enable rich markup in log messages
    )
    # Set format if provided
    if log_format:
        formatter = logging.Formatter(log_format)
        rich_handler.setFormatter(formatter)
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s" if not log_format else log_format,
        datefmt="[%X]",
        handlers=[rich_handler]
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str, level: Optional[int | str] = None) -> logging.Logger:
    """Get or create a logger with rich formatting.
    
    Returns a logger instance for the specified module. If global logging
    hasn't been configured yet, configures it with sensible defaults.
    
    Parameters
    ----------
    name : str
        Name of the logger, typically `__name__` of the calling module.
    level : Optional[int or str], default=None
        Optional logging level for this specific logger. If None, inherits
        from parent loggers.
    
    Returns
    -------
    logging.Logger
        Configured logger instance with rich formatting.
    
    Examples
    --------
    In a module:
    
    >>> # At the top of your module
    >>> from epanetparser.core.utils import get_logger
    >>> logger = get_logger(__name__)
    >>> 
    >>> # Use throughout the module
    >>> logger.debug("Starting validation")
    >>> logger.info("Processing network: [cyan]%s[/cyan]", network_name)
    >>> logger.warning("Found %d potential issues", len(issues))
    >>> logger.error("Validation failed: %s", error)
    
    With custom level:
    
    >>> logger = get_logger(__name__, level=logging.DEBUG)
    >>> logger.debug("Detailed debugging information")
    
    Using rich markup:
    
    >>> logger.info("[bold green]✓[/bold green] Validation passed")
    >>> logger.error("[bold red]✗[/bold red] Validation failed")
    
    Logging exceptions:
    
    >>> try:
    ...     risky_operation()
    ... except Exception:
    ...     logger.exception("Operation failed")  # Includes traceback
    
    Notes
    -----
    Best practice for libraries:
    - Use `logger = get_logger(__name__)` at module level
    - Use appropriate log levels (DEBUG for verbose, INFO for normal, WARNING for issues)
    - Don't call `configure_logging()` in library code; let users configure it
    - Use string formatting with % instead of f-strings for lazy evaluation
    
    The logger name follows Python's module hierarchy, e.g.:
    - "epanetparser.core.parse"
    - "epanetparser.core.validation"
    
    This allows users to configure logging per-module:
    
    >>> import logging
    >>> logging.getLogger("epanetparser.core.parse").setLevel(logging.DEBUG)
    >>> logging.getLogger("epanetparser.core.validation").setLevel(logging.WARNING)
    """
    # Configure logging if not already done (with sensible defaults)
    if not _LOGGING_CONFIGURED:
        configure_logging(level=logging.WARNING)  # Default to WARNING for libraries
    # Get or create logger
    logger = logging.getLogger(name)
    # Set level if specified
    if level is not None:
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        logger.setLevel(level)
    return logger


def _add_description(func: Callable) -> Callable:
    """Add description attribute extracted from docstring."""
    func.description = extract_quick_description(func)
    return func


def sha256digest(filename: str) -> str:
    """Calculate SHA256 hash digest of a file.
    
    Reads the file in chunks to efficiently handle large files without
    loading the entire content into memory. Uses 64KB buffer for optimal
    performance.
    
    Parameters
    ----------
    filename : str
        Path to the file to hash.
    
    Returns
    -------
    str
        Hexadecimal string representation of the SHA256 hash digest.
    
    Examples
    --------
    >>> hash_value = sha256digest('network.inp')
    >>> len(hash_value)  # SHA256 produces 64 hex characters
    64
    
    Notes
    -----
    The file is read in 64KB chunks to balance memory usage and I/O efficiency.
    This approach works well for files of any size.
    """
    bufsz = 64 * 1024
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as fp:
        while True:
            buf = fp.read(bufsz)
            if not buf:
                break
            sha256.update(buf)
    return sha256.hexdigest()


def get_rule_methods(
    obj: 'type | WNTREPANETType'
) -> Dict[str, DescribedCallable]:
    """Retrieve validation rule methods from a component class or instance.
    
    Discovers all validation rule methods defined on a component class or instance.
    Rule methods are identified by the 'rule_' prefix in their name. Works with
    both classes (returning unbound functions) and instances (returning bound methods).
    
    Parameters
    ----------
    obj : type or WNTREPANETType
        Component class or instance to introspect for rule methods.
        If a class, returns unbound functions in ValidatorInfo objects.
        If an instance, returns bound methods in ValidatorInfo objects.
    
    Returns
    -------
    Dict[str, ValidatorInfo]
        Dictionary mapping rule method names to ValidatorInfo objects.
        Keys are method names (e.g., 'rule_positive_length').
        Values are ValidatorInfo objects containing:
        - method: Callable (unbound function for classes, bound method for instances)
        - description: str (brief description from docstring)
    
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
    ValidatorInfo : Data class containing method and description
    WNTREPANETTypeValidator : Automatic validation that uses these methods
    
    Notes
    -----
    When passed a class, this function uses `inspect.isfunction` to get unbound functions.
    When passed an instance, it uses `inspect.ismethod` to get bound methods.
    Both functions and methods are Callable, so ValidatorInfo.method is always callable.
    This allows the same function to work seamlessly with both use cases.
    """
    # Determine if obj is a class or instance and get appropriate members
    if inspect.isclass(obj):
        funcs = inspect.getmembers(obj, inspect.isfunction)
    else:
        funcs = inspect.getmembers(obj, inspect.ismethod)
    result = {}
    for name, func in funcs:
        if not name.startswith("rule"):
            continue
        # unwrap bound method → original function
        target = func if inspect.isfunction(func) else func.__func__
        if not hasattr(target, "description"):
            setattr(target, "description", extract_quick_description(target))
        # store the ORIGINAL callable (bound or unbound)
        result[name] = func
    return result


def get_warning_methods(
    obj: 'type | WNTREPANETType'
) -> Dict[str, DescribedCallable]:
    """Retrieve warning check methods from a component class or instance.
    
    Discovers all warning check methods defined on a component class or instance.
    Warning methods are identified by the 'warn_' prefix in their name. Works with
    both classes (returning unbound functions) and instances (returning bound methods).
    
    Parameters
    ----------
    obj : type or WNTREPANETType
        Component class or instance to introspect for warning methods.
        If a class, returns unbound functions in ValidatorInfo objects.
        If an instance, returns bound methods in ValidatorInfo objects.
    
    Returns
    -------
    Dict[str, DescribedCallable]
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
    ValidatorInfo : Data class containing method and description
    WNTREPANETTypeValidator : Automatic validation that uses these methods
    
    Notes
    -----
    Warning methods raise `AssertionError` to signal non-fatal issues.
    Unlike rules, warnings don't prevent component creation but are tracked
    for user notification.
    
    When passed a class, this function uses `inspect.isfunction` to get unbound functions.
    When passed an instance, it uses `inspect.ismethod` to get bound methods.
    Both functions and methods are Callable, so ValidatorInfo.method is always callable.
    This allows the same function to work seamlessly with both use cases.
    """
    # Determine if obj is a class or instance and get appropriate members
    if inspect.isclass(obj):
        funcs = inspect.getmembers(obj, inspect.isfunction)
    else:
        funcs = inspect.getmembers(obj, inspect.ismethod)
    result = {}
    for name, func in funcs:
        if not name.startswith("warn"):
            continue
        # unwrap bound method → original function
        target = func if inspect.isfunction(func) else func.__func__
        if not hasattr(target, "description"):
            target.description = extract_quick_description(func)
        result[name] = func
    return result


if __name__ == "__main__":
    from rich import print
    # Demonstration of get_rule_methods and get_warning_methods
    print("=" * 70)
    print("Demonstration: get_rule_methods() and get_warning_methods()")
    print("=" * 70)
    
    from epanetparser.core.epanettypes import WNTREPANETNode, WNTREPANETLink
    
    # Example 1: Instance-level introspection (bound methods)
    print("\n[1] Instance-Level Introspection (Bound Methods)")
    print("-" * 70)
    node_data = {
        "name": "Junction-1",
        "node_type": "Junction",
        "elevation": 100.0
    }
    node = WNTREPANETNode(node_data)
    
    rules = get_rule_methods(node)
    warnings = get_warning_methods(node)
    
    print(f"Component: {node.type} (name: {node.name})")
    print(f"\nValidation Rules ({len(rules)} found):")
    for rule_name in sorted(rules.keys()):
        info = rules[rule_name]
        desc = f" - {info.description}" if info.description else ""
        print(f"  • {rule_name}{desc}")
    
    print(f"\nWarning Checks ({len(warnings)} found):")
    if warnings:
        for warn_name in sorted(warnings.keys()):
            info = warnings[warn_name]
            desc = f" - {info.description}" if info.description else ""
            print(f"  • {warn_name}{desc}")
    else:
        print("  (No warning methods defined for this component)")
    
    # Example 2: Class-level introspection (unbound functions)
    print("\n[2] Class-Level Introspection (Unbound Functions)")
    print("-" * 70)
    
    rules = get_rule_methods(WNTREPANETLink)
    warnings = get_warning_methods(WNTREPANETLink)
    
    print(f"Class: WNTREPANETLink")
    print(f"\nValidation Rules ({len(rules)} found):")
    for rule_name, info in sorted(rules.items()):
        print(f"  • {rule_name}")
        if info.description:
            print(f"    → {info.description}")
    
    print(f"\nWarning Checks ({len(warnings)} found):")
    if warnings:
        for warn_name, info in sorted(warnings.items()):
            print(f"  • {warn_name}")
            if info.description:
                print(f"    → {info.description}")
    else:
        print("  (No warning methods defined for this component)")
    
    # Example 3: Execute rules and check type information
    print("\n[3] Execute Rules and Check Type Information")
    print("-" * 70)
    
    link_data = {
        "name": "Pipe-1",
        "link_type": "Pipe",
        "length": 1000.0,
        "diameter": 300.0
    }
    link = WNTREPANETLink(link_data)
    
    rules = get_rule_methods(link)
    
    print(f"Component: {link.type} (name: {link.name})")
    print(f"\nExecuting rules with ValidatorInfo:")
    for rule_name, info in sorted(rules.items()):
        desc = info.description if info.description else '(No description)'
        print(f"  • {rule_name}")
        print(f"    → {desc}")
        print(f"    → Type: {type(info).__name__}, Method callable: {callable(info.__call__)}")
        try:
            info()  # Execute the validation
            print(f"    ✓ Passed")
        except AssertionError as e:
            print(f"    ✗ Failed: {e}")
    
    # Example 4: Comparing base class vs ruleset-specific class
    print("\n[4] Comparing Base Class vs MILP Ruleset")
    print("-" * 70)
    
    try:
        from epanetparser.rulesets.milp import MILP_Links
        
        base_rules = get_rule_methods(WNTREPANETLink)
        milp_rules = get_rule_methods(MILP_Links)
        extra_rule_names = set(milp_rules.keys()) - set(base_rules.keys())
        
        print(f"Base WNTREPANETLink rules: {len(base_rules)}")
        print(f"MILP_Links rules: {len(milp_rules)}")
        print(f"\nExtra MILP-specific rules ({len(extra_rule_names)}):")
        
        if extra_rule_names:
            for rule_name in sorted(extra_rule_names):
                info = milp_rules[rule_name]
                print(f"  • {rule_name}")
                print(f"    → {info.description}")
        else:
            print("  (No extra rules)")
    except ImportError:
        print("  (MILP ruleset not available)")
    
    # Example 5: ValidatorInfo dataclass attributes
    print("\n[5] ValidatorInfo Dataclass Attributes")
    print("-" * 70)
    rules = get_rule_methods(link)
    if 'rule_link_has_valid_type' in rules:
        info = rules['rule_link_has_valid_type']
        print(f"Rule name: rule_link_has_valid_type")
        print(f"ValidatorInfo.method: {info()}")
        print(f"ValidatorInfo.description: {info.description}")
        print(f"Is method callable? {callable(info.__call__)}")
        try:
            print("\nExecuting: info")
            info()
            print("  ✓ Validation passed")
        except AssertionError as e:
            print(f"  ✗ Validation failed: {e}")
    
    print("\n" + "=" * 70)
    print("Demonstration complete.")
    print("=" * 70)