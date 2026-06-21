"""Base classes for EPANET network component types.

This module provides the abstract base class (`WNTREPANETType`) that serves as the
foundation for all EPANET network component types including nodes, links, patterns,
curves, controls, and other network`elements.

The base class enforces a consistent interface across all component types, providing:

- Automatic data validation through descriptor-based validation
- Serialization to Python dict and JSON formats
- Tracking of warnings for validation issues
- Type identification through abstract property

Classes
-------
WNTREPANETType
    Abstract base class for all EPANET network components.

Notes
-----
All concrete EPANET component classes must inherit from `WNTREPANETType` and
implement the abstract `type` property to identify the component type.

The `data` class attribute uses a descriptor pattern (`WNTREPANETTypeValidator`)
to automatically validate component data according to defined schemas.

Examples
--------
Create a custom EPANET component type:

>>> class Junction(WNTREPANETType):
...     @property
...     def type(self) -> str:
...         return "Junction"
...
>>> junction = Junction()
>>> junction.data = {"elevation": 100.0, "demand": 50.0}
>>> junction.as_dict()
{'elevation': 100.0, 'demand': 50.0}

See Also
--------
epanetparser.core.validation.WNTREPANETTypeValidator : Data validation descriptor
epanetparser.core.epanettypes.node : Node component implementations
epanetparser.core.epanettypes.link : Link component implementations
"""
from typing import Dict
from abc import ABC, abstractmethod
import json
from epanetparser.core.validation import WNTREPANETTypeValidator


class WNTREPANETType(ABC):
    """Abstract base class for all EPANET network component types.
    
    This class serves as the foundation for all EPANET network components, providing
    a consistent interface for data storage, validation, serialization, and warning
    management. All concrete component classes (Junction, Pipe, Pattern, etc.) must
    inherit from this class.
    
    Attributes
    ----------
    data : WNTREPANETTypeValidator
        Descriptor-based validator for storing and validating component data.
        Automatically validates data against component-specific schemas when set.
    warnings : list of str, optional
        List of validation warning messages. Only present if validation warnings
        were generated during data assignment or validation. Access via the
        `has_warnings` property to check existence.
    
    Methods
    -------
    as_dict()
        Convert component data to dictionary representation.
    as_json()
        Convert component data to JSON string representation.
    
    Properties
    ----------
    type : str
        Abstract property that must be implemented by subclasses to identify
        the component type (e.g., 'Junction', 'Pipe', 'Pattern').
    has_warnings : bool
        Check if the component has any validation warnings.
    
    Notes
    -----
    The `data` attribute uses a descriptor pattern to intercept attribute access
    and automatically validate incoming data according to schemas defined in the
    validation module.
    
    Subclasses must implement the abstract `type` property to provide a string
    identifier for the component type.
    
    Examples
    --------
    Create a concrete component type:
    
    >>> class Reservoir(WNTREPANETType):
    ...     @property
    ...     def type(self) -> str:
    ...         return "Reservoir"
    ...
    >>> reservoir = Reservoir()
    >>> reservoir.data = {"head": 150.0}
    >>> reservoir.type
    'Reservoir'
    >>> reservoir.as_dict()
    {'head': 150.0}
    
    Check for validation warnings:
    
    >>> component = SomeComponent()
    >>> component.data = some_data  # May generate warnings
    >>> if component.has_warnings:
    ...     print(component.warnings)
    
    See Also
    --------
    WNTREPANETTypeValidator : Descriptor class for data validation
    """
    data = WNTREPANETTypeValidator()

    def as_dict(self) -> Dict[str, Dict]:
        """Convert component data to dictionary representation.
        
        Returns the component's validated data as a Python dictionary. This is
        useful for serialization, data inspection, or conversion to other formats.
        
        Returns
        -------
        dict
            Dictionary containing the component's validated data with field names
            as keys and their corresponding values.
        
        Examples
        --------
        >>> component = SomeComponent()
        >>> component.data = {"field1": 10, "field2": "value"}
        >>> component.as_dict()
        {'field1': 10, 'field2': 'value'}
        
        See Also
        --------
        as_json : Convert component data to JSON string
        """
        return self.data

    def as_json(self) -> str:
        """Convert component data to JSON string representation.
        
        Serializes the component's validated data to a JSON-formatted string.
        This is useful for data export, API responses, or file storage.
        
        Returns
        -------
        str
            JSON string representation of the component's validated data.
        
        Examples
        --------
        >>> component = SomeComponent()
        >>> component.data = {"field1": 10, "field2": "value"}
        >>> component.as_json()
        '{"field1": 10, "field2": "value"}'
        
        See Also
        --------
        as_dict : Convert component data to dictionary
        """
        return json.dumps(self.data)
    
    @property
    @abstractmethod
    def type(self) -> str:
        """Get the type identifier for this component.
        
        This abstract property must be implemented by all concrete subclasses
        to return a string that uniquely identifies the component type. The
        type string is used for component categorization, validation schema
        selection, and serialization.
        
        Returns
        -------
        str
            String identifier for the component type. Common values include
            'Junction', 'Reservoir', 'Tank', 'Pipe', 'Pump', 'Valve',
            'Pattern', 'Curve', 'Control', etc.
        
        Notes
        -----
        This is an abstract property and will raise `TypeError` if instantiated
        without implementation in a subclass.
        
        Examples
        --------
        >>> class Pipe(WNTREPANETType):
        ...     @property
        ...     def type(self) -> str:
        ...         return "Pipe"
        ...
        >>> pipe = Pipe()
        >>> pipe.type
        'Pipe'
        """

    @property
    def has_warnings(self) -> bool:
        """Check if this component has any validation warnings.
        
        Determines whether the component has accumulated any validation warnings
        during data assignment or validation. Warnings are non-fatal issues that
        don't prevent component creation but may indicate potential problems.
        
        Returns
        -------
        bool
            True if the component has one or more validation warnings,
            False otherwise (including when no warnings attribute exists).
        
        Notes
        -----
        The `warnings` attribute is only created on the instance when validation
        warnings are generated. This method safely checks for its existence and
        content without raising an AttributeError.
        
        Examples
        --------
        >>> component = SomeComponent()
        >>> component.data = valid_data
        >>> component.has_warnings
        False
        
        >>> component.data = questionable_data  # Generates warnings
        >>> component.has_warnings
        True
        >>> component.warnings
        ['Warning: Unusual value detected', 'Warning: Field X deprecated']
        
        See Also
        --------
        warnings : List of validation warning messages (if any)
        """
        return hasattr(self, "warnings") and len(self.warnings) > 0 # pylint: disable=no-member
    
    
if __name__ == "__main__":
    # Example usage of the base type class (for testing purposes)
    class ExampleComponent(WNTREPANETType):
        @property
        def type(self) -> str:
            return "ExampleComponent"
    
    # Create an instance and set some example data
    example = ExampleComponent()
    example.data = {"field1": 10, "field2": "test_value"}
    
    # Test the serialization methods
    print("Dictionary representation:")
    print(example.as_dict())
    
    print("\nJSON representation:")
    print(example.as_json())
    
    print("\nComponent type:")
    print(example.type)
    
    print("\nHas warnings:")
    print(example.has_warnings)
