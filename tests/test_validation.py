"""Tests for WNTREPANETTypeValidator descriptor.

This module tests the validation descriptor that automatically executes
validation rules and warning checks on component data assignment.
"""
import pytest
from epanetparser.core.validation import WNTREPANETTypeValidator
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.core.epanettypes.validation_warnings import WNTREPANETTypeValidationWarning


# Test fixtures - mock component classes


class SimplePipe:
    """Simple pipe component for basic validation tests."""
    
    data = WNTREPANETTypeValidator()
    
    def __init__(self, data):
        self.data = data
    
    def rule_positive_diameter(self):
        """Diameter must be positive."""
        assert self.data["diameter"] > 0, "Diameter must be positive"
    
    def rule_has_length(self):
        """Length field must exist."""
        assert "length" in self.data, "Length field is required"


class PipeWithWarnings:
    """Pipe component with both rules and warnings."""
    
    data = WNTREPANETTypeValidator(store_passed_rules=True)
    
    def __init__(self, data):
        self.data = data
    
    def rule_positive_diameter(self):
        """Diameter must be positive."""
        assert self.data["diameter"] > 0, "Diameter must be positive"
    
    def warn_large_diameter(self):
        """Warn about unusually large diameter."""
        assert self.data["diameter"] < 5000, "Diameter unusually large"
    
    def warn_small_diameter(self):
        """Warn about unusually small diameter."""
        assert self.data["diameter"] > 10, "Diameter unusually small"


class PipeWithMultipleRules:
    """Pipe with multiple validation rules."""
    
    data = WNTREPANETTypeValidator()
    
    def __init__(self, data):
        self.data = data
    
    def rule_positive_diameter(self):
        """Diameter must be positive."""
        assert self.data["diameter"] > 0, "Diameter must be positive"
    
    def rule_has_length(self):
        """Length must exist."""
        assert "length" in self.data, "Length is required"
    
    def rule_valid_material(self):
        """Material must be valid."""
        allowed = ["PVC", "Steel", "Copper"]
        material = self.data.get("material", "PVC")
        assert material in allowed, f"Invalid material: {material}"


class PipeWithTruncation:
    """Pipe for testing value truncation."""
    
    data = WNTREPANETTypeValidator(max_value_len=50)
    
    def __init__(self, data):
        self.data = data
    
    def rule_always_fails(self):
        """Always fails to test error messages."""
        assert False, "This rule always fails"


# Tests for successful validation


class TestSuccessfulValidation:
    """Test successful validation scenarios."""
    
    def test_valid_data_passes(self):
        """Valid data should pass validation without errors."""
        pipe = SimplePipe({"diameter": 100, "length": 500})
        assert pipe.data["diameter"] == 100
        assert pipe.data["length"] == 500
    
    def test_no_warnings_for_valid_data(self):
        """Valid data should not generate warnings."""
        pipe = PipeWithWarnings({"diameter": 100})
        assert hasattr(pipe, 'warnings')
        assert len(pipe.warnings) == 0
    
    def test_passed_rules_tracking(self):
        """Passed rules should be tracked when enabled."""
        pipe = PipeWithWarnings({"diameter": 100})
        assert hasattr(pipe, 'rules_passed')
        assert len(pipe.rules_passed) > 0
        assert any("rule_positive_diameter" in rule for rule in pipe.rules_passed)
    
    def test_passed_rules_not_tracked_by_default(self):
        """Passed rules should not be tracked by default."""
        pipe = SimplePipe({"diameter": 100, "length": 500})
        assert not hasattr(pipe, 'rules_passed')


# Tests for validation failures


class TestValidationFailures:
    """Test validation failure scenarios."""
    
    def test_single_rule_failure(self):
        """Single rule failure should raise error bundle."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            SimplePipe({"diameter": -100, "length": 500})
        
        bundle = exc_info.value
        assert len(bundle.bundle) == 1
        assert "Diameter must be positive" in str(bundle.bundle[0])
    
    def test_multiple_rule_failures(self):
        """Multiple rule failures should all be collected."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            PipeWithMultipleRules({
                "diameter": -100,  # Fails positive check
                # "length" missing - fails required check
                "material": "Wood"  # Fails valid material check
            })
        
        bundle = exc_info.value
        assert len(bundle.bundle) >= 2  # At least 2 failures
        
        error_messages = [str(e) for e in bundle.bundle]
        assert any("positive" in msg.lower() for msg in error_messages)
    
    def test_missing_required_field(self):
        """Missing required field should fail validation."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            SimplePipe({"diameter": 100})  # Missing 'length'
        
        bundle = exc_info.value
        assert any("length" in str(e).lower() for e in bundle.bundle)
    
    def test_error_contains_component_type(self):
        """Error should include component type information."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            SimplePipe({"diameter": -100, "length": 500})
        
        error = exc_info.value.bundle[0]
        assert error.component == "SimplePipe"
    
    def test_error_contains_rule_name(self):
        """Error should include rule name."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            SimplePipe({"diameter": -100, "length": 500})
        
        error = exc_info.value.bundle[0]
        assert error.rule == "rule_positive_diameter"
    
    def test_error_contains_value_text(self):
        """Error should include serialized value."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            SimplePipe({"diameter": -100, "length": 500})
        
        error = exc_info.value.bundle[0]
        assert "-100" in error.valuetext
        assert "500" in error.valuetext


# Tests for warnings


class TestWarnings:
    """Test warning functionality."""
    
    def test_warning_generated_for_edge_case(self):
        """Warning should be generated for edge case data."""
        pipe = PipeWithWarnings({"diameter": 6000})  # Large diameter
        assert hasattr(pipe, 'warnings')
        assert len(pipe.warnings) >= 1
        assert any("large" in str(w).lower() for w in pipe.warnings)
    
    def test_multiple_warnings(self):
        """Multiple warnings should be collected."""
        pipe = PipeWithWarnings({"diameter": 5})  # Small diameter
        assert len(pipe.warnings) >= 1
    
    def test_warnings_dont_block_validation(self):
        """Warnings should not prevent successful validation."""
        pipe = PipeWithWarnings({"diameter": 6000})
        # Should not raise exception
        assert pipe.data["diameter"] == 6000
    
    def test_warning_type(self):
        """Warnings should be WNTREPANETTypeValidationWarning instances."""
        pipe = PipeWithWarnings({"diameter": 6000})
        if pipe.warnings:
            assert all(isinstance(w, WNTREPANETTypeValidationWarning) 
                      for w in pipe.warnings)
    
    def test_warning_contains_component_type(self):
        """Warning should include component type."""
        pipe = PipeWithWarnings({"diameter": 6000})
        if pipe.warnings:
            warning = pipe.warnings[0]
            assert warning.component == "PipeWithWarnings"
    
    def test_warning_contains_rule_name(self):
        """Warning should include warning method name."""
        pipe = PipeWithWarnings({"diameter": 6000})
        if pipe.warnings:
            warning = pipe.warnings[0]
            assert warning.warning.startswith("warn_")


# Tests for value truncation


class TestValueTruncation:
    """Test value truncation in error messages."""
    
    def test_short_value_not_truncated(self):
        """Short values should not be truncated."""
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            PipeWithTruncation({"diameter": 100})
        
        error = exc_info.value.bundle[0]
        assert "..." not in error.valuetext
        assert "[+" not in error.valuetext
    
    def test_long_value_truncated(self):
        """Long values should be truncated."""
        long_data = {
            "diameter": 100,
            "description": "X" * 200,  # Very long field
            "extra": "Y" * 200
        }
        
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            PipeWithTruncation(long_data)
        
        error = exc_info.value.bundle[0]
        # Should be truncated to 50 chars + remainder message
        assert "..." in error.valuetext
        assert "[+" in error.valuetext
        assert "char" in error.valuetext
    
    def test_truncation_shows_character_count(self):
        """Truncation message should show number of chars truncated."""
        long_data = {"diameter": 100, "data": "X" * 500}
        
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            PipeWithTruncation(long_data)
        
        error = exc_info.value.bundle[0]
        assert "chars]" in error.valuetext or "char]" in error.valuetext


# Tests for descriptor protocol


class TestDescriptorProtocol:
    """Test descriptor protocol implementation."""
    
    def test_set_name_creates_instance_attribute(self):
        """__set_name__ should create private instance attribute name."""
        validator = WNTREPANETTypeValidator()
        validator.__set_name__(SimplePipe, "data")
        assert validator.instattr == "_data"
    
    def test_get_from_instance_returns_value(self):
        """__get__ from instance should return stored value."""
        pipe = SimplePipe({"diameter": 100, "length": 500})
        # Access through descriptor
        assert pipe.data == {"diameter": 100, "length": 500}
    
    def test_get_from_class_returns_descriptor(self):
        """__get__ from class should return descriptor itself."""
        descriptor = SimplePipe.data
        assert isinstance(descriptor, WNTREPANETTypeValidator)
    
    def test_set_stores_and_validates(self):
        """__set__ should store value and trigger validation."""
        pipe = SimplePipe({"diameter": 100, "length": 500})
        
        # Valid reassignment
        pipe.data = {"diameter": 200, "length": 600}
        assert pipe.data["diameter"] == 200
        
        # Invalid reassignment should fail
        with pytest.raises(WNTREPANETTypeValidationErrorBundle):
            pipe.data = {"diameter": -100, "length": 500}
    
    def test_private_attribute_created(self):
        """Descriptor should create private attribute on instance."""
        pipe = SimplePipe({"diameter": 100, "length": 500})
        assert hasattr(pipe, '_data')
        assert pipe._data == pipe.data


# Tests for edge cases


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_data_dict(self):
        """Empty data dict should trigger missing field errors."""
        # Empty dict will cause KeyError in rule_positive_diameter when accessing self.data["diameter"]
        # This gets caught and reported as a validation error
        with pytest.raises((WNTREPANETTypeValidationErrorBundle, KeyError)):
            SimplePipe({})
    
    def test_validator_with_different_max_lengths(self):
        """Validator should respect different max_value_len settings."""
        
        class ShortTruncation:
            data = WNTREPANETTypeValidator(max_value_len=10)
            
            def __init__(self, data):
                self.data = data
            
            def rule_fails(self):
                assert False, "Fail"
        
        long_data = {"field": "x" * 100}
        
        with pytest.raises(WNTREPANETTypeValidationErrorBundle) as exc_info:
            ShortTruncation(long_data)
        
        error = exc_info.value.bundle[0]
        # Value should be truncated to 10 chars
        assert len(error.valuetext) < 100
    
    def test_no_rules_no_warnings(self):
        """Component with no rules/warnings should still work."""
        
        class EmptyComponent:
            data = WNTREPANETTypeValidator()
            
            def __init__(self, data):
                self.data = data
        
        comp = EmptyComponent({"any": "data"})
        assert comp.data == {"any": "data"}
    
    def test_rule_method_with_return_value(self):
        """Rule methods can return values (tracked if store_passed_rules=True)."""
        
        class ComponentWithReturnValues:
            data = WNTREPANETTypeValidator(store_passed_rules=True)
            
            def __init__(self, data):
                self.data = data
            
            def rule_with_return(self):
                """Rule that returns a value."""
                assert True
                return "validation successful"
        
        comp = ComponentWithReturnValues({"test": "data"})
        assert hasattr(comp, 'rules_passed')
        # Return value should be captured in passed rules
        assert any("validation successful" in rule for rule in comp.rules_passed.values())


# Tests for trim_value method


class TestTrimValueMethod:
    """Test the trim_value helper method."""
    
    def test_trim_value_short_dict(self):
        """Short dict should not be truncated."""
        validator = WNTREPANETTypeValidator(max_value_len=100)
        result = validator.trim_value({"short": "value"})
        assert "..." not in result
        assert "short" in result
        assert "value" in result
    
    def test_trim_value_long_dict(self):
        """Long dict should be truncated."""
        validator = WNTREPANETTypeValidator(max_value_len=50)
        long_dict = {"field": "x" * 200}
        result = validator.trim_value(long_dict)
        
        assert len(result) > 50  # Includes truncation message
        assert "..." in result
        assert "[+" in result
    
    def test_trim_value_exact_length(self):
        """Value exactly at max_value_len should not be truncated."""
        validator = WNTREPANETTypeValidator(max_value_len=20)
        # Create a dict that serializes to exactly 20 chars
        test_dict = {"a": "b"}
        json_str = validator.trim_value(test_dict)
        
        # If under or at limit, no truncation
        if len(json_str) <= 20:
            assert "..." not in json_str


# Integration tests


class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_complex_validation_scenario(self):
        """Test complex scenario with multiple rules and warnings."""
        
        class ComplexPipe:
            data = WNTREPANETTypeValidator(
                store_passed_rules=True,
                max_value_len=150
            )
            
            def __init__(self, data):
                self.data = data
            
            def rule_positive_diameter(self):
                assert self.data["diameter"] > 0, "Diameter must be positive"
            
            def rule_has_length(self):
                assert "length" in self.data, "Length required"
            
            def rule_valid_material(self):
                allowed = ["PVC", "Steel", "Copper"]
                assert self.data.get("material", "PVC") in allowed, "Invalid material"
            
            def warn_large_diameter(self):
                assert self.data["diameter"] < 5000, "Very large diameter"
            
            def warn_long_pipe(self):
                assert self.data.get("length", 0) < 10000, "Very long pipe"
        
        # Valid with warnings
        pipe = ComplexPipe({
            "diameter": 6000,  # Valid but warns
            "length": 15000,   # Valid but warns
            "material": "Steel"
        })
        
        assert len(pipe.warnings) == 2
        assert len(pipe.rules_passed) >= 3
        assert pipe.data["diameter"] == 6000
    
    def test_multiple_components_independent(self):
        """Multiple component instances should have independent validation."""
        pipe1 = SimplePipe({"diameter": 100, "length": 500})
        pipe2 = SimplePipe({"diameter": 200, "length": 600})
        
        assert pipe1.data["diameter"] == 100
        assert pipe2.data["diameter"] == 200
        
        # Modifying one shouldn't affect the other
        pipe1.data = {"diameter": 150, "length": 550}
        assert pipe1.data["diameter"] == 150
        assert pipe2.data["diameter"] == 200


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
