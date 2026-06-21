""" Tests for ruleset discovery, type mapping, and active ruleset management. """
import pytest
from epanetparser.core import rulesets as rs
from epanetparser.core.epanettypes.node import WNTREPANETNode
from epanetparser.core.epanettypes.link import WNTREPANETLink
from epanetparser.core.epanettypes.control import WNTREPANETControl
from epanetparser.core.epanettypes.curve import WNTREPANETCurve
# Import mock rulesets for testing
from tests.mock_rulesets import basic_ruleset, advanced_ruleset

# Base path for mock rulesets used in tests
MOCK_BASE = "tests.mock_rulesets"


class TestRulesetDiscovery:
    """Test ruleset discovery and enumeration functionality."""

    def test_get_ruleset_modules(self):
        """Test that _get_ruleset_modules returns all available ruleset modules."""
        modules = rs.get_ruleset_modules(base=MOCK_BASE)
        # Should return a list of tuples
        assert isinstance(modules, list)
        assert len(modules) == 2
    
    def test_get_rulesets_metadata(self):
        """Test that get_rulesets returns correct metadata for all rulesets."""
        rulesets = rs.get_rulesets_metadata(base=MOCK_BASE)
        # Should return a dictionary
        assert isinstance(rulesets, dict)
        assert len(rulesets) >= 2
        # Check that our mock rulesets are present
        assert "basic" in rulesets
        # Verify basic ruleset metadata
        basic = rulesets["basic"]
        assert basic["name"] == "Basic Test Ruleset"
        assert basic["version"] == "1.0.0"
        assert basic["description"] == "A simple ruleset for testing basic functionality"
    
    def test_get_ruleset_module_by_key(self):
        """Test that get_ruleset_module retrieves the correct module by key."""
        # Test retrieving basic ruleset
        basic_mod = rs.get_ruleset_module("basic", base=MOCK_BASE)
        assert basic_mod is not None
        assert basic_mod.__key__ == "basic"
        assert basic_mod.__ruleset_name__ == "Basic Test Ruleset"
    
    def test_get_ruleset_module_none_key(self):
        """Test that get_ruleset_module returns None for None key."""
        result = rs.get_ruleset_module(None, base=MOCK_BASE)
        assert result is None
    
    def test_get_ruleset_module_nonexistent_key(self):
        """Test that get_ruleset_module returns None for nonexistent key."""
        result = rs.get_ruleset_module("nonexistent_ruleset", base=MOCK_BASE)
        assert result is None
    
    def test_describe_rulesets(self):
        """Test that describe_rulesets generates formatted output."""
        # Note: This uses the default base, so it will describe actual rulesets
        # We'll just verify it returns a non-empty string with expected format
        description = rs.describe_rulesets()
        assert isinstance(description, str)
        assert len(description) > 0
        assert "Available Rulesets" in description


class TestTypeMapping:
    """Test type mapping and identification functionality."""
    
    def test_identify_types_with_none_module(self):
        """Test that identify_types returns base types when module is None."""
        typemap = rs.identify_types(None)
        
        # Should contain all base types
        assert "WNTREPANETNode" in typemap
        assert "WNTREPANETLink" in typemap
        assert "WNTREPANETControl" in typemap
        assert "WNTREPANETCurve" in typemap
        assert "WNTREPANETNetworkInfo" in typemap
        assert "WNTREPANETOptions" in typemap
        assert "WNTREPANETPattern" in typemap
        assert "WNTREPANETSource" in typemap
        # Should map to actual base types
        assert typemap["WNTREPANETNode"] is WNTREPANETNode
        assert typemap["WNTREPANETLink"] is WNTREPANETLink
        assert typemap["WNTREPANETControl"] is WNTREPANETControl
        assert typemap["WNTREPANETCurve"] is WNTREPANETCurve
    
    def test_identify_types_with_basic_module(self):
        """Test that identify_types returns base types for ruleset without custom types."""
        typemap = rs.identify_types(basic_ruleset)
        # Should still map to base types since basic_ruleset has no custom types
        assert typemap["WNTREPANETNode"] is WNTREPANETNode
        assert typemap["WNTREPANETLink"] is WNTREPANETLink
    
    def test_identify_types_with_advanced_module(self):
        """Test that identify_types returns custom types when available."""
        typemap = rs.identify_types(advanced_ruleset)
        # Should map to custom types for Node and Link
        assert typemap["WNTREPANETNode"] is advanced_ruleset.CustomNode
        assert typemap["WNTREPANETLink"] is advanced_ruleset.CustomLink
        # Custom types should be subclasses of base types
        assert issubclass(typemap["WNTREPANETNode"], WNTREPANETNode)
        assert issubclass(typemap["WNTREPANETLink"], WNTREPANETLink)


class TestActiveRuleset:
    """Test active ruleset management and Ruleset class."""
    
    def test_set_active_ruleset(self):
        """Test that set_active_ruleset updates the global state."""
        original = rs.ACTIVE_RULESET_KEY
        try:
            # Set to a test key
            rs.set_active_ruleset("test_key")
            assert rs.ACTIVE_RULESET_KEY == "test_key"
            # Set to None
            rs.set_active_ruleset(None)
            assert rs.ACTIVE_RULESET_KEY is None
        finally:
            # Restore original state
            rs.set_active_ruleset(original)
    
    def test_ruleset_class_with_no_active_ruleset(self):
        """Test Ruleset class initialization with no active ruleset."""
        original = rs.ACTIVE_RULESET_KEY
        try:
            rs.set_active_ruleset(None)
            ruleset = rs.Ruleset()
            # Should have typemap with base types
            assert hasattr(ruleset, 'typemap')
            assert isinstance(ruleset.typemap, dict)
            assert ruleset.typemap["WNTREPANETNode"] is WNTREPANETNode
            assert ruleset.typemap["WNTREPANETLink"] is WNTREPANETLink
        finally:
            rs.set_active_ruleset(original)
    
    def test_ruleset_class_with_active_basic_ruleset(self):
        """Test Ruleset class initialization with basic active ruleset."""
        original = rs.ACTIVE_RULESET_KEY
        try:
            rs.set_active_ruleset("basic")
            ruleset = rs.Ruleset()
            # Should have typemap with base types (basic has no custom types)
            assert ruleset.typemap["WNTREPANETNode"] is WNTREPANETNode
            assert ruleset.typemap["WNTREPANETLink"] is WNTREPANETLink
        finally:
            rs.set_active_ruleset(original)


class TestRulesetIntegrity:
    """Test that all defined rulesets have required attributes."""
    
    def test_all_rulesets_complete(self):
        """Test that each defined ruleset contains the required attributes."""
        _rulesets = rs.get_rulesets_metadata()
        for ruleset_key, data in _rulesets.items():
            ruleset_mod = rs.get_ruleset_module(ruleset_key)
            assert ruleset_key == ruleset_mod.__key__
            assert data["name"] == ruleset_mod.__ruleset_name__
            assert data["version"] == ruleset_mod.__version__
            assert data["description"] == ruleset_mod.__description__
    
    def test_mock_rulesets_complete(self):
        """Test that mock rulesets have all required attributes."""
        _rulesets = rs.get_rulesets_metadata(base=MOCK_BASE)
        for ruleset_key, data in _rulesets.items():
            ruleset_mod = rs.get_ruleset_module(ruleset_key, base=MOCK_BASE)
            assert ruleset_key == ruleset_mod.__key__
            assert data["name"] == ruleset_mod.__ruleset_name__
            assert data["version"] == ruleset_mod.__version__
            assert data["description"] == ruleset_mod.__description__
