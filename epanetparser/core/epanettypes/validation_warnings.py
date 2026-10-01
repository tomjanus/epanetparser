"""Warning classes for EPANET parser validation warnings.

This module defines custom warning types used throughout the EPANET parser
to handle non-critical validation issues. Warnings indicate potential problems
that don't prevent parsing but may affect network behavior or future compatibility.
"""
from typing import Any, Dict


class WNTREPANETParserWarning(Warning):
    """Base warning class for all EPANET parser warnings.
    
    This is the parent class for all custom warnings raised during
    EPANET network model parsing and validation.
    
    Args:
        message: Human-readable warning message describing the issue.
    """
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.message})"


class WNTREPANETTypeValidationWarning(WNTREPANETParserWarning):
    """Warning raised when a component violates a non-critical validation rule.
    
    This warning is raised when a specific component (node, link, pattern, etc.)
    violates a non-critical validation rule. Unlike errors, warnings don't prevent
    parsing from completing successfully.
    
    Args:
        component: Name/type of the component being validated (e.g., 'Junction', 'Pipe').
        warning: Name of the validation warning rule that was triggered.
        exc: The underlying exception or warning message.
        valuetext: String representation of the value that triggered the warning.
    
    Attributes:
        desc_text: Display text prefix for this warning type.
    """
    desc_text = "[WARNING]"

    def __init__(self, component: str, warning: str, exc: Any, valuetext: str) -> None:
        super().__init__(f"{component} validation warning: {warning}")
        self.component = component
        self.warning = warning
        self.exc = exc
        self.valuetext = valuetext

    def __str__(self) -> str:
        return f"{self.desc_text} {self.component} '{self.warning}' -> {self.exc}:\n          {self.valuetext}"

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.component}, {self.warning}, {self.exc})"

    def as_dict(self) -> Dict[str, Any]:
        """Convert warning to dictionary representation.
        
        Returns:
            Dictionary containing component, warning name, exception, and value.
        """
        return {
            "component": self.component,
            "warning": self.warning,
            "exception": str(self.exc),
            "value": self.valuetext
        }



#class WNTREPANETNameWarning(WNTREPANETParserWarning):
#   """Warning raised for issues related to component naming.
#    
#    This warning is raised when component names may cause issues or
#    don't follow recommended naming conventions.
#    
#    Args:
#        message: Human-readable warning message describing the naming issue.
#        component: Name/type of the component with the naming issue.
#    """
#    def __init__(self, message: str, component: str) -> None:
#        super().__init__(message)
#        self.component = component
