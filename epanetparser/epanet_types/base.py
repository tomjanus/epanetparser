"""Base classes for EPANET network component types.

This module provides the abstract base class for all EPANET network component types
(nodes, links, patterns, etc.). It defines the common interface for data validation,
serialization, and warning tracking.
"""
from typing import Dict
from abc import ABC, abstractmethod
import json
from epanetparser.validation import WNTREPANETTypeValidator


class WNTREPANETType(ABC):
    """Abstract base class for all EPANET network component types.
    
    This class provides common functionality for all EPANET components including
    data validation, serialization to dict/JSON formats, and warning tracking.
    All concrete component types (nodes, links, patterns, etc.) must inherit from
    this class and implement the abstract `type` property.
    
    Attributes:
        data: WNTREPANETTypeValidator instance for storing and validating component data.
        warnings: Optional list of validation warnings (if any warnings were generated).
    """
    data = WNTREPANETTypeValidator()

    def as_dict(self) -> Dict[str, Dict]:
        """Convert component data to dictionary representation.
        
        Returns:
            Dictionary containing the component's validated data.
        """
        return self.data

    def as_json(self) -> str:
        """Convert component data to JSON string representation.
        
        Returns:
            JSON string containing the component's validated data.
        """
        return json.dumps(self.data)
    
    @property
    @abstractmethod
    def type(self) -> str:
        """Get the type identifier for this component.
        
        This abstract property must be implemented by all concrete subclasses
        to return a string identifying the component type (e.g., 'Junction',
        'Pipe', 'Pattern', etc.).
        
        Returns:
            String identifier for the component type.
        """

    @property
    def has_warnings(self) -> bool:
        """Check if this component has any validation warnings.
        
        Returns:
            True if the component has warnings, False otherwise.
        """
        return hasattr(self, "warnings") and len(self.warnings) > 0 # pylint: disable=no-member
    
    
if __name__ == "__main__":
    # Example usage of the base type class (for testing purposes)
    class ExampleComponent(WNTREPANETType):
        @property
        def type(self) -> str:
            return "ExampleComponent"
    
    example = ExampleComponent()
    print(example.as_dict())
    print(example.as_json())
