"""Tests for epanetparser.core.utils module.

This test module covers utility functions for EPANET component validation,
including rule/warning method introspection and file hashing utilities.
"""
import pytest
import tempfile
import os
from pathlib import Path
from epanetparser.core.utils import (
    get_rule_methods,
    get_warning_methods,
    sha256digest,
    raiseorpush
)
from epanetparser.core.epanettypes import WNTREPANETNode, WNTREPANETLink
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from collections import defaultdict


class TestGetRuleMethods:
    """Tests for get_rule_methods() function."""
    
    def test_get_rule_methods_returns_dict(self):
        """Test that get_rule_methods returns a dictionary."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        rules = get_rule_methods(node)
        assert isinstance(rules, dict)
    
    def test_get_rule_methods_finds_rules(self):
        """Test that get_rule_methods finds methods starting with 'rule_'."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        rules = get_rule_methods(node)
        
        # Should find at least some rule methods
        assert len(rules) > 0
        
        # All keys should start with 'rule_'
        for rule_name in rules.keys():
            assert rule_name.startswith("rule_"), f"Method {rule_name} doesn't start with 'rule_'"
    
    def test_get_rule_methods_returns_callables(self):
        """Test that get_rule_methods returns callable methods."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        rules = get_rule_methods(node)
        
        # All values should be callable
        for rule_name, rule_func in rules.items():
            assert callable(rule_func), f"Rule {rule_name} is not callable"
    
    def test_get_rule_methods_link_component(self):
        """Test get_rule_methods with link components."""
        link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
        rules = get_rule_methods(link)
        
        assert isinstance(rules, dict)
        assert len(rules) > 0
        assert all(name.startswith("rule_") for name in rules.keys())
    
    def test_rule_methods_are_bound(self):
        """Test that returned rule methods are bound to the instance."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        rules = get_rule_methods(node)
        
        # Get any rule method
        if rules:
            rule_name, rule_func = next(iter(rules.items()))
            # Should be a bound method with __self__ pointing to the node
            assert hasattr(rule_func, '__self__')
            assert rule_func.__self__ is node


class TestGetWarningMethods:
    """Tests for get_warning_methods() function."""
    
    def test_get_warning_methods_returns_dict(self):
        """Test that get_warning_methods returns a dictionary."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        warnings = get_warning_methods(node)
        assert isinstance(warnings, dict)
    
    def test_get_warning_methods_finds_warnings(self):
        """Test that get_warning_methods finds methods starting with 'warn_'."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        warnings = get_warning_methods(node)
        
        # All keys should start with 'warn_' (if any exist)
        for warn_name in warnings.keys():
            assert warn_name.startswith("warn_"), f"Method {warn_name} doesn't start with 'warn_'"
    
    def test_get_warning_methods_returns_callables(self):
        """Test that get_warning_methods returns callable methods."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        warnings = get_warning_methods(node)
        
        # All values should be callable (if any exist)
        for warn_name, warn_func in warnings.items():
            assert callable(warn_func), f"Warning {warn_name} is not callable"
    
    def test_get_warning_methods_link_component(self):
        """Test get_warning_methods with link components."""
        link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
        warnings = get_warning_methods(link)
        
        assert isinstance(warnings, dict)
        # May or may not have warnings, but should return valid dict
        assert all(name.startswith("warn_") for name in warnings.keys())
    
    def test_warning_methods_are_bound(self):
        """Test that returned warning methods are bound to the instance."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        warnings = get_warning_methods(node)
        
        # If there are any warning methods, check they're bound
        if warnings:
            warn_name, warn_func = next(iter(warnings.items()))
            assert hasattr(warn_func, '__self__')
            assert warn_func.__self__ is node


class TestSha256Digest:
    """Tests for sha256digest() function."""
    
    def test_sha256digest_returns_string(self):
        """Test that sha256digest returns a string."""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            digest = sha256digest(temp_path)
            assert isinstance(digest, str)
        finally:
            os.unlink(temp_path)
    
    def test_sha256digest_correct_length(self):
        """Test that SHA256 digest has correct length (64 hex characters)."""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            digest = sha256digest(temp_path)
            assert len(digest) == 64  # SHA256 = 256 bits = 64 hex chars
        finally:
            os.unlink(temp_path)
    
    def test_sha256digest_deterministic(self):
        """Test that same content produces same hash."""
        content = "deterministic test content"
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            digest1 = sha256digest(temp_path)
            digest2 = sha256digest(temp_path)
            assert digest1 == digest2
        finally:
            os.unlink(temp_path)
    
    def test_sha256digest_different_content(self):
        """Test that different content produces different hashes."""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f1:
            f1.write("content one")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f2:
            f2.write("content two")
            path2 = f2.name
        
        try:
            digest1 = sha256digest(path1)
            digest2 = sha256digest(path2)
            assert digest1 != digest2
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_sha256digest_empty_file(self):
        """Test sha256digest with empty file."""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            temp_path = f.name
        
        try:
            digest = sha256digest(temp_path)
            # Empty file has a known SHA256 hash
            expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert digest == expected
        finally:
            os.unlink(temp_path)
    
    def test_sha256digest_large_file(self):
        """Test sha256digest with a larger file (tests chunking)."""
        # Create a file larger than the buffer size (64KB)
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            # Write 100KB of data
            f.write("x" * (100 * 1024))
            temp_path = f.name
        
        try:
            digest = sha256digest(temp_path)
            assert len(digest) == 64
            assert isinstance(digest, str)
        finally:
            os.unlink(temp_path)


class TestRaiseOrPush:
    """Tests for raiseorpush context manager."""
    
    def test_raiseorpush_initialization(self):
        """Test basic initialization of raiseorpush."""
        dest = type('Dest', (), {
            'errors': defaultdict(list),
            'warnings': defaultdict(list)
        })()
        
        ctx = raiseorpush('TestComponent', True, True, dest)
        assert ctx.component == 'TestComponent'
        assert ctx.raise_error == True
        assert ctx.raise_warning == True
        assert ctx.dest is dest
    
    def test_raiseorpush_context_manager(self):
        """Test raiseorpush as context manager."""
        dest = type('Dest', (), {
            'errors': defaultdict(list),
            'warnings': defaultdict(list)
        })()
        
        with raiseorpush('TestComponent', False, False, dest) as ctx:
            assert ctx is not None
            assert ctx.component == 'TestComponent'
    
    def test_raiseorpush_ignore_warnings(self):
        """Test that ignore_warnings flag works."""
        dest = type('Dest', (), {
            'errors': defaultdict(list),
            'warnings': defaultdict(list)
        })()
        
        ctx = raiseorpush('TestComponent', False, True, dest, ignore_warnings=True)
        assert ctx.raise_warning == False
        assert ctx.ignore_warnings == True


class TestRuleWarningMethodsIntegration:
    """Integration tests for rule and warning methods."""
    
    def test_rules_and_warnings_are_separate(self):
        """Test that rules and warnings are properly separated."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        
        rules = get_rule_methods(node)
        warnings = get_warning_methods(node)
        
        # Rule names and warning names should not overlap
        rule_names = set(rules.keys())
        warning_names = set(warnings.keys())
        
        assert rule_names.isdisjoint(warning_names), \
            "Rules and warnings should have different names"
    
    def test_execute_valid_rule(self):
        """Test executing a valid rule that should pass."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        rules = get_rule_methods(node)
        
        # The rule_node_has_name should pass for a node with a name
        if 'rule_node_has_name' in rules:
            # Should not raise an exception
            rules['rule_node_has_name']()
    
    def test_different_components_different_rules(self):
        """Test that different component types have different rule sets."""
        node = WNTREPANETNode({"name": "J1", "node_type": "Junction"})
        link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})
        
        node_rules = set(get_rule_methods(node).keys())
        link_rules = set(get_rule_methods(link).keys())
        
        # There should be some differences in rule sets
        # (though some base rules might be common)
        assert node_rules != link_rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

