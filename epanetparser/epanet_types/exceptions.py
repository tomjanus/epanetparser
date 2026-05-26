"""Exception classes for EPANET parser validation errors.

This module defines custom exception types used throughout the EPANET parser
to handle validation errors at different levels (network, component, type).
It also provides bundled exceptions that can contain multiple errors and warnings.
"""
from typing import Dict, List, Any
from .warnings import WNTREPANETParserWarning


class WNTREPANETParserException(Exception):
    """Base exception class for all EPANET parser errors.
    
    This is the parent class for all custom exceptions raised during
    EPANET network model parsing and validation.
    
    Args:
        message: Human-readable error message describing the exception.
    """
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.message})"


class WNTREPANETTypeValidationError(WNTREPANETParserException):
    """Exception raised when a component fails a validation rule.
    
    This exception is raised when a specific component (node, link, pattern, etc.)
    violates a validation rule defined in the active ruleset.
    
    Args:
        component: Name/type of the component being validated (e.g., 'Junction', 'Pipe').
        rule: Name of the validation rule that failed.
        exc: The underlying exception or error message.
        valuetext: String representation of the value that caused the validation failure.
    
    Attributes:
        desc_text: Display text prefix for this error type.
    """
    desc_text = "[FAILURE]"

    def __init__(self, component: str, rule: str, exc: Any, valuetext: str) -> None:
        super().__init__(f"{component} validation error: {rule}")
        self.component = component
        self.rule = rule
        self.exc = exc
        self.valuetext = valuetext

    def __str__(self) -> str:
        return f"{self.desc_text} {self.component} '{self.rule}' -> {self.exc}:\n          {self.valuetext}"

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.component}, {self.rule}, {self.exc})"

    def as_dict(self) -> Dict[str, Any]:
        """ Convert the error details to a dictionary format for structured output."""
        return {
            "component": self.component,
            "rule": self.rule,
            "exception": str(self.exc),
            "value": self.valuetext
        }


class WNTREPANETTypeValidationErrorBundle(WNTREPANETParserException):
    """Bundle of multiple validation errors and warnings.
    
    This exception aggregates multiple validation errors and warnings that occurred
    during parsing. It provides properties to separate errors from warnings.
    
    Args:
        message: Summary message describing the bundle.
        bundle: List of WNTREPANETParserException and WNTREPANETParserWarning objects.
    """
    def __init__(self, message: str, bundle: List[WNTREPANETParserException]) -> None:
        super().__init__(message)
        self.message = message
        self.bundle = bundle

    @property
    def errors(self) -> List[WNTREPANETParserException]:
        """Extract all errors from the bundle.
        
        Returns:
            List of WNTREPANETParserException objects from the bundle.
        """
        return [exc for exc in self.bundle if isinstance(exc, WNTREPANETParserException)]

    @property
    def warnings(self) -> List[WNTREPANETParserWarning]:
        """Extract all warnings from the bundle.
        
        Returns:
            List of WNTREPANETParserWarning objects from the bundle.
        """
        return [exc for exc in self.bundle if isinstance(exc, WNTREPANETParserWarning)]


class WNTREPANETNetworkValidationError(WNTREPANETParserException):
    """Exception raised when network-level validation fails.
    
    This exception is raised for validation errors that apply to the entire
    network rather than individual components.
    
    Args:
        message: Human-readable error message describing the network validation failure.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.component = "network"

    def as_dict(self) -> Dict[str, Any]:
        """ Convert the network validation error to a dictionary format for structured output."""
        return {
            "component": self.component,
            "message": self.message
        }