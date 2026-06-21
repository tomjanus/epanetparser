""" """
from typing import Callable, Dict
from collections import defaultdict
import logging


logger = logging.getLogger(__name__)


class RuleRegistry:
    """Central registry for validation rules and warnings.
    
    This registry maintains mappings between component types and their
    associated validation rules and warning checks.
    
    Attributes
    ----------
    _rules : Dict[str, Dict[str, Callable]]
        Component type -> rule name -> rule function mapping.
    _warnings : Dict[str, Dict[str, Callable]]
        Component type -> warning name -> warning function mapping.
    _loaded_plugins : set
        Set of plugin entry point names that have been loaded.
    """
    
    def __init__(self):
        self._rules: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        self._warnings: Dict[str, Dict[str, Callable]] = defaultdict(dict)
        self._loaded_plugins: set = set()
    
    def register_rule(
        self,
        component_type: str,
        name: str, # rule name
        func: Callable,
        replace: bool = False
    ) -> None:
        """Register a validation rule for a component type.
        
        Parameters
        ----------
        component_type : str
            Name of the component class (e.g., 'WNTREPANETLink').
        name : str
            Rule name (will be prefixed with 'rule_' if not already).
        func : Callable
            Validation function that takes an instance and raises
            AssertionError on validation failure.
        replace : bool, optional
            If True, replace existing rule with same name. Default is False.
        
        Raises
        ------
        ValueError
            If a rule with the same name already exists and replace=False.
        """
        rule_name = name if name.startswith("rule_") else f"rule_{name}"
        if not replace and rule_name in self._rules[component_type]:
            raise ValueError(
                f"Rule '{rule_name}' already registered for {component_type}. "
                f"Use replace=True to override."
            )
        self._rules[component_type][rule_name] = func
        logger.debug(f"Registered rule: {component_type}.{rule_name}")
    
    def register_warning(
        self,
        component_type: str,
        name: str,
        func: Callable,
        replace: bool = False
    ) -> None:
        """Register a warning check for a component type."""
        warn_name = name if name.startswith("warn_") else f"warn_{name}"
        if not replace and warn_name in self._warnings[component_type]:
            raise ValueError(
                f"Warning '{warn_name}' already registered for {component_type}. "
                f"Use replace=True to override."
            )
        self._warnings[component_type][warn_name] = func
        logger.debug(f"Registered warning: {component_type}.{warn_name}")
    
    def get_rules(self, component_type: str) -> Dict[str, Callable]:
        """Get all registered rules for a component type."""
        return self._rules.get(component_type, {}).copy()
    
    def get_warnings(self, component_type: str) -> Dict[str, Callable]:
        """Get all registered warnings for a component type."""
        return self._warnings.get(component_type, {}).copy()
    
    def list_plugins(self) -> set:
        """Get set of loaded plugin names."""
        return self._loaded_plugins.copy()
    
    def mark_plugin_loaded(self, plugin_name: str) -> None:
        """Mark a plugin as loaded."""
        self._loaded_plugins.add(plugin_name)
    
    def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about registered validations."""
        stats = {}
        all_types = set(self._rules.keys()) | set(self._warnings.keys())
        for component_type in all_types:
            stats[component_type] = {
                "rules": len(self._rules.get(component_type, {})),
                "warnings": len(self._warnings.get(component_type, {}))
            }
        return stats
