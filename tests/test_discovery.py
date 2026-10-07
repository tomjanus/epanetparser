"""Tests for epanetparser.core.discovery.

This module tests the introspection helpers used to describe classes and their
``rule_*`` and ``warn_*`` methods: which classes a module defines, which
methods a class carries, and where each method came from.

It does not test how validation selects rules. That is rule set discovery, in
:mod:`tests.test_ruleset_registry`, and it works from rule set module metadata
rather than from method-name conventions. What is tested here is the
description machinery, which the ``epanetparser-plugins`` command and the
documentation rely on.

Covered
-------
discover_classes
    Classes a module defines, excluding imported ones.
discover_methods_in_class
    Methods of a class, filtered by prefix, local or including inherited.
get_rule_methods / get_warning_methods
    The same, for a class or a bound instance, filtered to rules or warnings.
FileInfo / MethodInfo
    The dataclasses those functions return.

Notes
-----
These tests build their own classes rather than using the EPANET component
classes, because the component classes deliberately carry no ``rule_*`` or
``warn_*`` methods: rules live in rule sets now, not on the model.
"""
import pytest
from types import ModuleType

from epanetparser.core.validation.introspection import (
    discover_classes,
    discover_methods_in_class,
    get_rule_methods,
    get_warning_methods,
    FileInfo,
    MethodInfo,
)


@pytest.fixture
def mock_classes():
    """Create mock classes for testing."""
    class BaseComponent:
        """Base component class."""
        def rule_base_validation(self):
            """Base validation rule."""
            pass
        
        def warn_base_check(self):
            """Base warning check."""
            pass
    
    class DerivedComponent(BaseComponent):
        """Derived component class."""
        def __init__(self, data=None):
            self.data = data or {}
        
        def rule_derived_validation(self):
            """Derived validation rule."""
            assert self.data.get("valid", True), "Invalid component"
        
        def warn_derived_check(self):
            """Derived warning check."""
            pass
        
        def utility_method(self):
            """Non-validation utility method."""
            pass
    
    class SpecializedComponent(DerivedComponent):
        """Specialized component class."""
        def rule_specialized_validation(self):
            """Specialized validation rule."""
            pass
    
    return BaseComponent, DerivedComponent, SpecializedComponent


@pytest.fixture
def mock_module(mock_classes):
    """Create a mock module with classes."""
    BaseComponent, DerivedComponent, SpecializedComponent = mock_classes
    
    # Create mock module
    module = ModuleType("test_module")
    
    # Set __module__ attribute for discover_classes to work
    BaseComponent.__module__ = "test_module"
    DerivedComponent.__module__ = "test_module"
    SpecializedComponent.__module__ = "test_module"
    
    # Add classes to module
    module.BaseComponent = BaseComponent
    module.DerivedComponent = DerivedComponent
    module.SpecializedComponent = SpecializedComponent
    
    return module


@pytest.fixture
def sample_file_info():
    """Create sample FileInfo instance."""
    return FileInfo(
        name="test_rules",
        file_path="/path/to/test_rules.py",
        module_path="epanetparser.rules.test_rules"
    )


# ============================================================================
# Tests for discover_classes
# ============================================================================

class TestDiscoverClasses:
    """Test discover_classes function."""
    
    def test_discovers_classes_in_module(self, mock_module):
        """Test that discover_classes finds all classes in a module."""
        classes = discover_classes(mock_module)
        
        assert len(classes) == 3
        class_names = [cls.__name__ for cls in classes]
        assert "BaseComponent" in class_names
        assert "DerivedComponent" in class_names
        assert "SpecializedComponent" in class_names
    
    def test_excludes_imported_classes(self):
        """Test that imported classes are excluded."""
        module = ModuleType("test_module")
        
        # Define a class in this module
        class LocalClass:
            pass
        LocalClass.__module__ = "test_module"
        
        # Import a class from another module
        class ImportedClass:
            pass
        ImportedClass.__module__ = "other_module"
        
        module.LocalClass = LocalClass
        module.ImportedClass = ImportedClass
        
        classes = discover_classes(module)
        
        assert len(classes) == 1
        assert classes[0].__name__ == "LocalClass"
    
    def test_returns_empty_list_for_module_without_classes(self):
        """Test that empty list is returned for module without classes."""
        module = ModuleType("empty_module")
        module.some_function = lambda: None
        module.some_variable = 42
        
        classes = discover_classes(module)
        
        assert classes == []


# ============================================================================
# Tests for discover_methods_in_class
# ============================================================================

class TestDiscoverMethodsInClass:
    """Test discover_methods_in_class function."""
    
    def test_discovers_methods_with_prefix(self, mock_classes):
        """Test discovering methods with specific prefix."""
        _, DerivedComponent, _ = mock_classes
        
        methods = discover_methods_in_class(DerivedComponent, prefix='rule_')
        
        assert 'rule_derived_validation' in methods
        assert 'warn_derived_check' not in methods
        assert 'utility_method' not in methods
    
    def test_discovers_all_methods_without_prefix(self, mock_classes):
        """Test discovering all methods when no prefix specified."""
        _, DerivedComponent, _ = mock_classes
        
        methods = discover_methods_in_class(DerivedComponent, prefix=None, local_only=True)
        
        # Should include all non-dunder, non-static methods
        assert 'rule_derived_validation' in methods
        assert 'warn_derived_check' in methods
        assert 'utility_method' in methods
    
    def test_local_only_mode(self, mock_classes):
        """Test that local_only=True excludes inherited methods."""
        _, DerivedComponent, _ = mock_classes
        
        methods = discover_methods_in_class(DerivedComponent, prefix='rule_', local_only=True)
        
        assert 'rule_derived_validation' in methods
        assert 'rule_base_validation' not in methods
    
    def test_includes_inherited_methods(self, mock_classes):
        """Test that local_only=False includes inherited methods."""
        _, _, SpecializedComponent = mock_classes
        
        methods = discover_methods_in_class(SpecializedComponent, prefix='rule_', local_only=False)
        
        assert 'rule_specialized_validation' in methods
        assert 'rule_derived_validation' in methods
        assert 'rule_base_validation' in methods
    
    def test_method_info_structure(self, mock_classes):
        """Test that MethodInfo contains correct data."""
        _, DerivedComponent, _ = mock_classes
        
        methods = discover_methods_in_class(DerivedComponent, prefix='rule_', local_only=True)
        method_info = methods['rule_derived_validation']
        
        assert isinstance(method_info, MethodInfo)
        assert callable(method_info.method)
        assert method_info.description == "Derived validation rule."
        assert '(self)' in method_info.signature
        assert method_info.origin is None  # local_only=True
        assert method_info.is_inherited is None  # local_only=True
    
    def test_method_info_with_inheritance_tracking(self, mock_classes):
        """Test that MethodInfo tracks inheritance correctly."""
        _, _, SpecializedComponent = mock_classes
        
        methods = discover_methods_in_class(SpecializedComponent, prefix='rule_', local_only=False)
        
        # Check local method
        local_method = methods['rule_specialized_validation']
        assert local_method.origin == 'SpecializedComponent'
        assert local_method.is_inherited is False
        
        # Check inherited method
        inherited_method = methods['rule_base_validation']
        assert inherited_method.origin == 'BaseComponent'
        assert inherited_method.is_inherited is True
    
    def test_excludes_dunder_methods(self, mock_classes):
        """Test that dunder methods are excluded by default."""
        _, DerivedComponent, _ = mock_classes
        
        methods = discover_methods_in_class(DerivedComponent, prefix=None, local_only=True)
        
        assert '__init__' not in methods
        assert '__str__' not in methods
    
    def test_excludes_static_and_class_methods(self):
        """Test that static and class methods are excluded."""
        class TestClass:
            @staticmethod
            def static_method():
                pass
            
            @classmethod
            def class_method(cls):
                pass
            
            def instance_method(self):
                pass
        
        TestClass.__module__ = "test"
        methods = discover_methods_in_class(TestClass, prefix=None, local_only=True)
        
        assert 'static_method' not in methods
        assert 'class_method' not in methods
        assert 'instance_method' in methods


# ============================================================================
# Tests for get_rule_methods and get_warning_methods
# ============================================================================

class TestGetRuleAndWarningMethods:
    """Test get_rule_methods and get_warning_methods functions."""
    
    def test_get_rule_methods_from_class(self, mock_classes):
        """Test getting rule methods from a class."""
        _, DerivedComponent, _ = mock_classes
        
        rules = get_rule_methods(DerivedComponent)
        
        assert 'rule_derived_validation' in rules
        assert 'rule_base_validation' in rules  # Includes inherited
        assert 'warn_derived_check' not in rules
    
    def test_get_rule_methods_from_instance(self, mock_classes):
        """Test getting rule methods from an instance."""
        _, DerivedComponent, _ = mock_classes
        instance = DerivedComponent({"valid": True})
        
        rules = get_rule_methods(instance)
        
        assert 'rule_derived_validation' in rules
        # Verify it's a bound method
        assert callable(rules['rule_derived_validation'].method)
    
    def test_get_warning_methods_from_class(self, mock_classes):
        """Test getting warning methods from a class."""
        _, DerivedComponent, _ = mock_classes
        
        warnings = get_warning_methods(DerivedComponent)
        
        assert 'warn_derived_check' in warnings
        assert 'warn_base_check' in warnings  # Includes inherited
        assert 'rule_derived_validation' not in warnings
    
    def test_get_warning_methods_from_instance(self, mock_classes):
        """Test getting warning methods from an instance."""
        _, DerivedComponent, _ = mock_classes
        instance = DerivedComponent()
        
        warnings = get_warning_methods(instance)
        
        assert 'warn_derived_check' in warnings
        # Verify it's a bound method
        assert callable(warnings['warn_derived_check'].method)
    
    def test_bound_method_execution(self, mock_classes):
        """Test that bound methods can be executed."""
        _, DerivedComponent, _ = mock_classes
        instance = DerivedComponent({"valid": True})
        
        rules = get_rule_methods(instance)
        
        # Should not raise
        rules['rule_derived_validation'].method()
        
        # Should raise with invalid data
        instance.data = {"valid": False}
        with pytest.raises(AssertionError, match="Invalid component"):
            rules['rule_derived_validation'].method()


# ============================================================================
# Tests for Dataclasses
# ============================================================================

class TestFileInfo:
    """Test FileInfo dataclass."""
    
    def test_creation(self, sample_file_info):
        """Test FileInfo creation."""
        assert sample_file_info.name == "test_rules"
        assert sample_file_info.file_path == "/path/to/test_rules.py"
        assert sample_file_info.module_path == "epanetparser.rules.test_rules"
    
    def test_str_representation(self, sample_file_info):
        """Test string representation."""
        result = str(sample_file_info)
        assert "test_rules" in result
        assert "epanetparser.rules.test_rules" in result
    
    def test_to_dict(self, sample_file_info):
        """Test conversion to dictionary."""
        result = sample_file_info.to_dict()
        assert result["name"] == "test_rules"
        assert result["file_path"] == "/path/to/test_rules.py"
        assert result["module_path"] == "epanetparser.rules.test_rules"


class TestMethodInfo:
    """Test MethodInfo dataclass."""
    
    def test_creation(self):
        """Test MethodInfo creation."""
        def test_method():
            """Test description."""
            pass
        
        info = MethodInfo(
            method=test_method,
            description="Test description.",
            signature="()",
            origin="TestClass",
            is_inherited=False
        )
        
        assert info.method == test_method
        assert info.description == "Test description."
        assert info.signature == "()"
        assert info.origin == "TestClass"
        assert info.is_inherited is False
    
    def test_str_representation(self):
        """Test string representation."""
        def test_rule():
            """A test rule."""
            pass
        
        info = MethodInfo(
            method=test_rule,
            description="A test rule.",
            signature="(self)",
            origin="BaseClass",
            is_inherited=True
        )
        
        result = str(info)
        assert "test_rule" in result
        assert "(self)" in result
        assert "inherited from BaseClass" in result
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        def test_method():
            pass
        
        info = MethodInfo(
            method=test_method,
            description="Test",
            signature="()",
            origin=None,
            is_inherited=None
        )
        
        result = info.to_dict()
        assert result["method"] == test_method
        assert result["description"] == "Test"
        assert result["signature"] == "()"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple discovery functions."""
    
    def test_complete_class_introspection_workflow(self, mock_classes):
        """Test complete workflow from class to method discovery."""
        _, DerivedComponent, SpecializedComponent = mock_classes
        
        # 1. Get all rule methods from base class
        base_rules = get_rule_methods(DerivedComponent)
        
        # 2. Get all rule methods from specialized class
        specialized_rules = get_rule_methods(SpecializedComponent)
        
        # 3. Verify inheritance
        assert len(specialized_rules) > len(base_rules)
        assert 'rule_specialized_validation' in specialized_rules
        assert 'rule_specialized_validation' not in base_rules
        
        # 4. All base rules should be in specialized
        for rule_name in base_rules.keys():
            assert rule_name in specialized_rules
    
    def test_instance_vs_class_discovery(self, mock_classes):
        """Test that both instance and class discovery work correctly."""
        _, DerivedComponent, _ = mock_classes
        
        # From class
        class_rules = get_rule_methods(DerivedComponent)
        
        # From instance
        instance = DerivedComponent()
        instance_rules = get_rule_methods(instance)
        
        # Should find the same methods
        assert set(class_rules.keys()) == set(instance_rules.keys())
        
        # But class returns unbound functions, instance returns bound methods
        # (Both are callable though)
        assert all(callable(info.method) for info in class_rules.values())
        assert all(callable(info.method) for info in instance_rules.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
