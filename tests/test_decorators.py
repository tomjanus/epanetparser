"""
Tests for the decorators module.

This module contains pytest-based unit and integration tests for the
epanetparser.core.decorators module. The tests verify:

- @match decorator: Type-based method dispatch for EPANET components
- @described decorator: Automatic description extraction from docstrings

The suite covers:
- Exact type matching (case-sensitive and case-insensitive)
- Fuzzy matching rules (substring-based matching)
- Behaviour when type attributes are missing, None, or invalid
- Return value propagation from decorated methods
- Stacked decorator interactions
- Preservation of function metadata (name and docstring)
- Validation logic with assertions on component data
- Integration scenarios for node and link validation workflows
- Description extraction from pure functions and methods
- Compatibility of @described with other decorators
"""
import pytest
from epanetparser.core.decorators import match, described


class MockComponent:
    """Mock component class for testing the match decorator."""
    
    def __init__(self, component_type: str):
        """Initialize with a specific component type.
        
        Parameters
        ----------
        component_type : str
            The type of the component (e.g., 'Junction', 'Tank', 'Pipe').
        """
        self.type = component_type
        self.validation_called = False
        self.data = {}
    
    @match('Junction')
    def validate_junction(self) -> None:
        """Validation rule that only runs for Junction types."""
        self.validation_called = True
        assert self.type == 'Junction', "Should only run for Junction"
    
    @match('Tank')
    def validate_tank(self) -> None:
        """Validation rule that only runs for Tank types."""
        self.validation_called = True
        assert self.type == 'Tank', "Should only run for Tank"
    
    @match('Pipe')
    def validate_pipe(self) -> None:
        """Validation rule that only runs for Pipe types."""
        self.validation_called = True
        assert self.type == 'Pipe', "Should only run for Pipe"
    
    @match('valve', fuzzy=True)
    def validate_valve_fuzzy(self) -> None:
        """Validation rule that runs for any type containing 'valve' (case-insensitive)."""
        self.validation_called = True
    
    @match('Reservoir')
    def validate_with_data_check(self) -> None:
        """Validation rule with data assertion."""
        self.validation_called = True
        assert "base_head" in self.data, "Reservoir must have base_head"


class TestMatchDecorator:
    """Test suite for the match decorator."""
    
    def test_exact_match_junction(self):
        """Test that match decorator works with exact type match."""
        component = MockComponent('Junction')
        component.validate_junction()
        assert component.validation_called, "Validation should have been called for Junction"
    
    def test_exact_match_tank(self):
        """Test that match decorator works with Tank type."""
        component = MockComponent('Tank')
        component.validate_tank()
        assert component.validation_called, "Validation should have been called for Tank"
    
    def test_exact_match_pipe(self):
        """Test that match decorator works with Pipe type."""
        component = MockComponent('Pipe')
        component.validate_pipe()
        assert component.validation_called, "Validation should have been called for Pipe"
    
    def test_no_match_wrong_type(self):
        """Test that validation is skipped when type doesn't match."""
        component = MockComponent('Junction')
        component.validate_tank()  # Try to call Tank validation on Junction
        assert not component.validation_called, "Validation should not run for wrong type"
    
    def test_case_insensitive_match(self):
        """Test that type matching is case-insensitive."""
        # Test lowercase
        component_lower = MockComponent('junction')
        try:
            component_lower.validate_junction()
        except AssertionError:
            pass
        assert component_lower.validation_called, "Should match case-insensitively (lowercase)"
        
        # Test uppercase
        component_upper = MockComponent('JUNCTION')
        try:
            component_upper.validate_junction()
        except AssertionError:
            pass
        assert component_upper.validation_called, "Should match case-insensitively (uppercase)"
        
        # Test mixed case
        component_mixed = MockComponent('JuNcTiOn')
        try:
            component_mixed.validate_junction()
        except AssertionError:
            pass
        assert component_mixed.validation_called, "Should match case-insensitively (mixed case)"
    
    def test_fuzzy_match_prv(self):
        """Test fuzzy matching with PRV (Pressure Reducing Valve)."""
        component = MockComponent('Pressure Reducing Valve')
        component.validate_valve_fuzzy()
        assert component.validation_called, "Should match 'PRV' with fuzzy 'valve'"
    
    def test_fuzzy_match_case_insensitive(self):
        """Test that fuzzy matching is also case-insensitive."""
        component = MockComponent('pressure reducing valve')
        component.validate_valve_fuzzy()
        assert component.validation_called, "Fuzzy match should be case-insensitive"
    
    def test_fuzzy_no_match(self):
        """Test that fuzzy matching doesn't match when substring not present."""
        component = MockComponent('Pipe')
        component.validate_valve_fuzzy()
        assert not component.validation_called, "Should not match 'Pipe' with fuzzy 'valve'"
    
    def test_validation_with_data_check_success(self):
        """Test that validation can check data attributes."""
        component = MockComponent('Reservoir')
        component.data = {"base_head": 100.0}
        component.validate_with_data_check()
        assert component.validation_called, "Validation should run successfully"
    
    def test_validation_with_data_check_failure(self):
        """Test that validation raises AssertionError when data is missing."""
        component = MockComponent('Reservoir')
        component.data = {}  # Missing base_head
        with pytest.raises(AssertionError, match="Reservoir must have base_head"):
            component.validate_with_data_check()
    
    def test_no_type_attribute(self):
        """Test behavior when instance has no type attribute."""
        class NoTypeComponent:
            @match('Junction')
            def validate(self):
                pytest.fail("Should not be called when no type attribute exists")
        
        component = NoTypeComponent()
        result = component.validate()
        assert result is None, "Should return None when no type attribute"
    
    def test_none_type_value(self):
        """Test behavior when type attribute is None."""
        class NoneTypeComponent:
            def __init__(self):
                self.type = None
            
            @match('Junction')
            def validate(self):
                pytest.fail("Should not be called when type is None")
        
        component = NoneTypeComponent()
        result = component.validate()
        assert result is None, "Should return None when type is None"
    
    def test_empty_string_type(self):
        """Test behavior when type is an empty string."""
        class EmptyTypeComponent:
            def __init__(self):
                self.type = ""
            
            @match('Junction')
            def validate(self):
                pytest.fail("Should not be called when type is empty string")
        
        component = EmptyTypeComponent()
        result = component.validate()
        assert result is None, "Should return None when type is empty string"
    
    def test_return_value_propagation(self):
        """Test that return values from decorated functions are propagated."""
        class ReturnComponent:
            def __init__(self, component_type: str):
                self.type = component_type
            
            @match('Junction')
            def get_value(self) -> str:
                return "junction_value"
            
            @match('Tank')
            def get_value_tank(self) -> str:
                return "tank_value"
        
        junction = ReturnComponent('Junction')
        assert junction.get_value() == "junction_value", "Should return the function's return value"
        
        tank = ReturnComponent('Tank')
        assert tank.get_value() is None, "Should return None when type doesn't match"
        assert tank.get_value_tank() == "tank_value", "Should return value for matching type"
    
    def test_multiple_decorators_same_method(self):
        """Test stacking multiple match decorators (though not typical usage)."""
        class MultiDecoratorComponent:
            def __init__(self, component_type: str):
                self.type = component_type
                self.call_count = 0
            
            @match('Junction')
            @match('Tank')
            def validate_both(self) -> None:
                self.call_count += 1
        
        # Only Junction matches the outer decorator
        junction = MultiDecoratorComponent('Junction')
        junction.validate_both()
        # The outer @match('Junction') passes, but inner @match('Tank') fails
        assert junction.call_count == 0, "Stacked decorators both must match"
        
        # Tank matches inner but not outer
        tank = MultiDecoratorComponent('Tank')
        tank.validate_both()
        assert tank.call_count == 0, "Stacked decorators both must match"
    
    def test_decorator_preserves_function_metadata(self):
        """Test that the match decorator preserves function name and docstring."""
        class MetadataComponent:
            def __init__(self):
                self.type = 'Junction'
            
            @match('Junction')
            def special_validation(self) -> None:
                """This is a special validation method."""
                pass
        
        component = MetadataComponent()
        assert component.special_validation.__name__ == 'special_validation'
        assert component.special_validation.__doc__ == """This is a special validation method."""
    
    def test_exact_match_with_special_characters(self):
        """Test matching with type names containing special patterns."""
        component = MockComponent('Type-With-Dashes')
        
        class SpecialComponent:
            def __init__(self, component_type: str):
                self.type = component_type
                self.validated = False
            
            @match('Type-With-Dashes')
            def validate(self) -> None:
                self.validated = True
        
        special = SpecialComponent('Type-With-Dashes')
        special.validate()
        assert special.validated, "Should match type with special characters"


class TestMatchDecoratorIntegration:
    """Integration tests for match decorator with realistic scenarios."""
    
    def test_realistic_node_validation(self):
        """Test match decorator with realistic node validation scenario."""
        class WNTREPANETNode:
            def __init__(self, data: dict):
                self.data = data
                self.type = data.get('node_type')
            
            @match('Junction')
            def rule_junction_has_elevation(self) -> None:
                assert "elevation" in self.data, "Junction must have elevation"
            
            @match('Tank')
            def rule_tank_has_diameter(self) -> None:
                assert "diameter" in self.data, "Tank must have diameter"
            
            @match('Reservoir')
            def rule_reservoir_has_base_head(self) -> None:
                assert "base_head" in self.data, "Reservoir must have base_head"
        
        # Valid junction
        junction = WNTREPANETNode({"node_type": "Junction", "elevation": 100})
        junction.rule_junction_has_elevation()  # Should not raise
        
        # Invalid junction
        bad_junction = WNTREPANETNode({"node_type": "Junction"})
        with pytest.raises(AssertionError, match="Junction must have elevation"):
            bad_junction.rule_junction_has_elevation()
        
        # Valid tank
        tank = WNTREPANETNode({"node_type": "Tank", "diameter": 50})
        tank.rule_tank_has_diameter()  # Should not raise
        
        # Tank doesn't trigger junction rule
        tank.rule_junction_has_elevation()  # Should not raise (returns None)
    
    def test_realistic_link_validation(self):
        """Test match decorator with realistic link validation scenario."""
        class WNTREPANETLink:
            def __init__(self, data: dict):
                self.data = data
                self.type = data.get('link_type')
            
            @match('Pipe')
            def rule_pipe_has_length(self) -> None:
                assert self.data.get('length', 0) > 0, "Pipe must have positive length"
            
            @match('Pump')
            def rule_pump_has_curve_or_power(self) -> None:
                has_curve = "pump_curve_name" in self.data
                has_power = "power" in self.data
                assert has_curve or has_power, "Pump must have curve or power"
        
        # Valid pipe
        pipe = WNTREPANETLink({"link_type": "Pipe", "length": 100})
        pipe.rule_pipe_has_length()  # Should not raise
        
        # Invalid pipe
        bad_pipe = WNTREPANETLink({"link_type": "Pipe", "length": 0})
        with pytest.raises(AssertionError, match="Pipe must have positive length"):
            bad_pipe.rule_pipe_has_length()
        
        # Valid pump with curve
        pump = WNTREPANETLink({"link_type": "Pump", "pump_curve_name": "PUMP1"})
        pump.rule_pump_has_curve_or_power()  # Should not raise
        
        # Pump doesn't trigger pipe rule
        pump.rule_pipe_has_length()  # Should return None, not raise


class TestDescribedDecorator:
    """Test suite for the @described decorator."""
    
    def test_described_with_pure_function(self):
        """Test that @described works with pure functions."""
        @described
        def validate_positive(value: float) -> None:
            """Ensure value is positive."""
            assert value > 0, "Value must be positive"
        
        # Check that description attribute is added
        assert hasattr(validate_positive, 'description')
        assert validate_positive.description == "Ensure value is positive."
        
        # Check that function still works
        validate_positive(5.0)  # Should not raise
        with pytest.raises(AssertionError, match="Value must be positive"):
            validate_positive(-1.0)
    
    def test_described_with_method(self):
        """Test that @described works with methods in a class."""
        class Component:
            def __init__(self, name: str):
                self.name = name
            
            @described
            def rule_has_name(self) -> None:
                """Validate that component has a name."""
                assert self.name, "Component must have a name"
        
        # Check description on class method
        assert hasattr(Component.rule_has_name, 'description')
        assert getattr(Component.rule_has_name, 'description') == "Validate that component has a name."
        
        # Check that method still works on instance
        component = Component("Test")
        component.rule_has_name()  # Should not raise
        
        empty_component = Component("")
        with pytest.raises(AssertionError, match="Component must have a name"):
            empty_component.rule_has_name()
    
    def test_described_with_multiline_docstring(self):
        """Test that @described extracts first line from multiline docstrings."""
        @described
        def complex_validation(data: dict) -> None:
            """Validate complex data structure.
            
            This is a more detailed explanation of what this
            validation does. It checks multiple things and
            has a long docstring.
            
            Parameters
            ----------
            data : dict
                The data to validate.
            """
            assert data, "Data must not be empty"
        
        assert complex_validation.description == "Validate complex data structure."
    
    def test_described_with_summary_field(self):
        """Test that @described uses :summary: field when available."""
        @described
        def tank_validation(self) -> None:
            """Validate tank configuration.
            
            :summary: Ensure tank has required geometric parameters.
            
            This validation checks that tanks have all the required
            geometric parameters like diameter, min/max levels, etc.
            """
            pass
        
        # Should extract from :summary: field
        assert tank_validation.description == "Ensure tank has required geometric parameters."
    
    def test_described_without_docstring(self):
        """Test that @described handles functions without docstrings."""
        @described
        def no_doc_function():
            pass
        
        assert hasattr(no_doc_function, 'description')
        assert no_doc_function.description == ""
    
    def test_described_preserves_function_metadata(self):
        """Test that @described preserves function name and docstring."""
        @described
        def important_validation(self) -> None:
            """This is important."""
            pass
        
        assert important_validation.__name__ == 'important_validation'
        assert important_validation.__doc__ == """This is important."""
    
    def test_described_with_match_decorator(self):
        """Test that @described works in combination with @match."""
        class Node:
            def __init__(self, node_type: str, elevation: float = None):
                self.type = node_type
                self.elevation = elevation
            
            @described
            @match('Junction')
            def rule_junction_has_elevation(self) -> None:
                """Validate junction elevation."""
                assert self.elevation is not None, "Junction must have elevation"
        
        # Check description is preserved
        assert hasattr(Node.rule_junction_has_elevation, 'description')
        assert getattr(Node.rule_junction_has_elevation, 'description') == "Validate junction elevation."
        
        # Check both decorators work
        junction_valid = Node('Junction', 100.0)
        junction_valid.rule_junction_has_elevation()  # Should not raise
        
        junction_invalid = Node('Junction', None)
        with pytest.raises(AssertionError, match="Junction must have elevation"):
            junction_invalid.rule_junction_has_elevation()
        
        # Tank type should not trigger validation
        tank = Node('Tank', None)
        result = tank.rule_junction_has_elevation()
        assert result is None  # @match returns None for non-matching type
    
    def test_described_with_multiple_methods(self):
        """Test @described on multiple methods in a class."""
        class ValidationRules:
            @described
            def rule_positive_value(self, value: float) -> None:
                """Ensure value is positive."""
                assert value > 0
            
            @described
            def rule_non_empty_string(self, text: str) -> None:
                """Ensure string is not empty."""
                assert text.strip(), "String must not be empty"
            
            @described
            def warn_large_value(self, value: float) -> None:
                """Check if value is unusually large."""
                assert value < 1000, "Value seems unusually large"
        
        # All methods should have descriptions
        assert getattr(ValidationRules.rule_positive_value, 'description') == "Ensure value is positive."
        assert getattr(ValidationRules.rule_non_empty_string, 'description') == "Ensure string is not empty."
        assert getattr(ValidationRules.warn_large_value, 'description') == "Check if value is unusually large."

    def test_described_is_callable(self):
        """Test that decorated functions remain callable."""
        @described
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        
        # Should be callable
        assert callable(add)
        result = add(2, 3)
        assert result == 5
        
        # Should have description
        assert add.description == "Add two numbers."
    
    def test_described_with_static_method(self):
        """Test @described with @staticmethod."""
        class Utils:
            @staticmethod
            @described
            def validate_range(value: float, min_val: float, max_val: float) -> None:
                """Ensure value is within range."""
                assert min_val <= value <= max_val, f"Value must be between {min_val} and {max_val}"
        
        # Check description on static method
        assert hasattr(Utils.validate_range, 'description')
        assert Utils.validate_range.description == "Ensure value is within range."
        
        # Check it works
        Utils.validate_range(5.0, 0.0, 10.0)  # Should not raise
        with pytest.raises(AssertionError):
            Utils.validate_range(15.0, 0.0, 10.0)
    
    def test_described_with_class_method(self):
        """Test @described with @classmethod."""
        class Validator:
            default_min = 0.0
            
            @classmethod
            @described
            def validate_above_default(cls, value: float) -> None:
                """Ensure value is above default minimum."""
                assert value >= cls.default_min, f"Value must be >= {cls.default_min}"
        
        # Check description
        assert hasattr(Validator.validate_above_default, 'description')
        assert Validator.validate_above_default.description == "Ensure value is above default minimum."
        
        # Check it works
        Validator.validate_above_default(5.0)  # Should not raise
        with pytest.raises(AssertionError):
            Validator.validate_above_default(-1.0)
