"""Utility functions and classes for EPANET parser validation.

This module provides core utilities for validating EPANET network components including:
- Context managers for error/warning aggregation (raiseorpush)
- Type validators for component data validation (WNTREPANETTypeValidator)
- Decorators for type-specific rule matching (match)
- Helper functions for name canonicalization and SHA256 hashing
"""
from __future__ import annotations
from typing import Tuple, Any, Optional, TYPE_CHECKING
import functools
import hashlib
import inspect
import json
import re
from epanetparser.epanet_types.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.epanet_types.warnings import WNTREPANETTypeValidationWarning

if TYPE_CHECKING:
    from epanetparser.epanet_types.base import WNTREPANETType


class raiseorpush:
    """Context manager for capturing and aggregating validation errors and warnings.
    
    This context manager allows flexible error handling during component parsing.
    Errors and warnings can either be raised immediately or collected in a destination
    object for batch processing, depending on the configuration.
    
    Args:
        component: Name/type of the component being validated.
        raise_error: If True, raise errors immediately; otherwise collect them.
        raise_warning: If True, raise warnings immediately; otherwise collect them.
        dest: Destination object with 'errors' and 'warnings' attributes for collecting issues.
        ignore_warnings: If True, suppress all warning processing.
    
    Attributes:
        error_set: Tuple of exception types that will be caught by the context manager.
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
        
        Returns:
            Self for use in 'with' statements.
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
        in the destination object.
        
        Args:
            exc_type: Exception type if an exception occurred.
            exc_obj: Exception object if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        
        Returns:
            True to suppress the exception, False to propagate it.
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
        
        If a created instance has validation warnings, they are either raised
        immediately (if raise_warning is True) or collected in the destination.
        
        Args:
            inst: The validated component instance to check for warnings.
        """
        if inst.has_warnings and not self.ignore_warnings:
            for warning in inst.warnings:
                if self.raise_warning:
                    raise warning from None
                self.dest.warnings[self.component].append(warning)


def canonical_name(nodename: str, attr: str) -> str:
    """Create a canonical reference key for a node attribute.
    
    Generates a standardized reference key in the format '__nodename__:attr'
    for linking component attributes.
    
    Args:
        nodename: Name of the node/component.
        attr: Attribute name to reference.
    
    Returns:
        Canonical reference key string.
    """
    return f"__{nodename}__:{attr}"


def parse_reference_key(key: str) -> Tuple[str, str]:
    """Parse a canonical reference key into node name and attribute.
    
    Extracts the node name and attribute from a canonical reference key
    created by canonical_name(). Validates that the name follows the
    expected pattern.
    
    Args:
        key: Canonical reference key in format '__nodename__:attr'.
    
    Returns:
        Tuple of (node_name, attribute_name).
    
    Raises:
        ValueError: If the key format is invalid or name pattern doesn't match.
    """
    end_mark = "__:"
    name_end = key.rindex(end_mark)  # ValueError on fail
    sepidx = name_end + len(end_mark) - 1
    name, attr = key[:sepidx], key[sepidx+1:]

    name_pattern = r"^__[a-zA-Z0-9_ \/\:\.\-\(\)]+__$"
    if not re.search(name_pattern, name):
        raise ValueError(f"Invalid reference: {name}")

    return name.strip('_'), attr


def match(typename: str, fuzzy: bool = False):
    """Decorator to apply validation rules only to components of a specific type.
    
    This decorator wraps validation rule methods to execute only when the component's
    'type' attribute matches the specified typename. All comparisons are case-insensitive.
    
    Args:
        typename: Type name to match against (e.g., 'Junction', 'Pipe').
        fuzzy: If True, match any type containing typename; if False, require exact match
               (with special handling for 'parameter' suffix).
    
    Returns:
        Decorator function that wraps the validation method.
    
    Example:
        @match('Junction')
        def rule_junction_specific(self):
            # This rule only runs for Junction components
            assert self.elevation > 0
    """
    def type_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not (hasattr(self, "type") and self.type):
                return
            
            type_lower = self.type.lower()
            typename_lower = typename.lower()
            
            if fuzzy:
                is_match = typename_lower in type_lower
            elif not type_lower.endswith("parameter"):
                # Special handling for parameter types
                basematch = typename_lower.removesuffix("parameter")
                is_match = basematch == type_lower
            else:
                is_match = typename_lower == type_lower

            if is_match:
                return func(self, *args, **kwargs)

        return wrapper
    return type_wrapper


def sha256digest(filename: str) -> str:
    """Calculate SHA256 hash digest of a file.
    
    Reads the file in chunks to efficiently handle large files without
    loading the entire content into memory.
    
    Args:
        filename: Path to the file to hash.
    
    Returns:
        Hexadecimal string representation of the SHA256 hash.
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
