"""Ruleset discovery and management for EPANET parser validation.

This module handles the discovery and loading of validation rulesets that define
specialized validation rules for EPANET network components. It provides functionality to:

- Discover and enumerate available rulesets
- Load and activate specific rulesets
- Map base component types to ruleset-specific subclasses
- Manage the active ruleset state

Rulesets are Python modules located in the epanetparser.rulesets package. Each ruleset
can define specialized versions of base component types with additional validation rules.
"""
from typing import Tuple, Dict, Any, Optional
import importlib
import inspect

RULESET_BASE = "epanetparser.rulesets"
ACTIVE_RULESET_KEY: Optional[str] = None


def get_rulesets() -> Dict[str, Dict[str, Any]]:
    """Get metadata for all available rulesets.
    
    Discovers all rulesets in the rulesets package and returns their metadata
    including name, module path, version, and description.
    
    Returns:
        Dictionary mapping ruleset keys to their metadata dictionaries.
        Each metadata dict contains:
            - name: Human-readable ruleset name
            - modpath: Full module path
            - version: Ruleset version string
            - description: Ruleset description
    """
    mods = get_ruleset_modules()
    modules = {}
    for mod in mods:
        modules[mod[1].__key__] = {
            "name": mod[1].__ruleset_name__,
            "modpath": mod[0],
            "version": mod[1].__version__,
            "description": mod[1].__description__
        }

    return modules


def get_ruleset_modules(base: str = RULESET_BASE) -> list:
    """Get all ruleset modules from the rulesets package.
    
    Dynamically imports the rulesets base package and retrieves all module members.
    Invalidates import caches before loading to ensure fresh module state.
    
    Args:
        base: Base module path for rulesets. Defaults to RULESET_BASE.
    
    Returns:
        List of (name, module) tuples for all modules in the rulesets package.
    """
    importlib.invalidate_caches()
    base_module = importlib.import_module(base)
    return inspect.getmembers(base_module, inspect.ismodule)


def get_ruleset_module(key: Optional[str]):
    """Get a specific ruleset module by its key.
    
    Searches all available ruleset modules for one matching the given key.
    
    Args:
        key: Unique identifier for the ruleset to retrieve.
    
    Returns:
        The ruleset module object if found, None otherwise.
    """
    if key is None:
        return None
    
    modules = (m for _, m in get_ruleset_modules())
    for module in modules:
        if module.__key__ == key:
            return module
    
    return None


def describe_rulesets() -> str:
    """Generate a formatted description of all available rulesets.
    
    Creates a human-readable string listing all available rulesets with their
    metadata including name, version, key, and description.
    
    Returns:
        Formatted string describing all available rulesets.
    """
    modules = get_rulesets()

    output = "Available Rulesets:\n"
    for idx, (key, mod) in enumerate(modules.items(), 1):
        output += f"[{idx}]\tName: '{mod['name']}'  Version: {mod['version']}"
        output += f"  Key: {key}\n"
        output += f"{mod['description']}\n\n"

    return output


def identify_types(module) -> Dict[str, type]:
    """Create a type mapping from base types to ruleset-specific subclasses.
    
    Maps base EPANET component type names to their corresponding classes,
    using ruleset-specific subclasses if available, or base classes otherwise.
    This allows rulesets to override validation behavior by subclassing base types.
    
    Args:
        module: Ruleset module to search for specialized type subclasses.
                If None, returns mapping to base types only.
    
    Returns:
        Dictionary mapping qualified type names (e.g., 'WNTREPANETNode') to
        their corresponding class objects (base or ruleset-specific).
    """   
    from epanetparser.epanet_types.node import WNTREPANETNode
    from epanetparser.epanet_types.control import WNTREPANETControl
    from epanetparser.epanet_types.curve import WNTREPANETCurve
    from epanetparser.epanet_types.link import WNTREPANETLink
    from epanetparser.epanet_types.network_info import WNTREPANETNetworkInfo
    from epanetparser.epanet_types.options import WNTREPANETOptions
    from epanetparser.epanet_types.pattern import WNTREPANETPattern
    from epanetparser.epanet_types.source import WNTREPANETSource

    base_types: Tuple = (
        WNTREPANETNode, WNTREPANETControl, WNTREPANETCurve, WNTREPANETLink,
        WNTREPANETNetworkInfo, WNTREPANETOptions, WNTREPANETPattern, WNTREPANETSource
    )
    typemap = {t.__qualname__: t for t in base_types}
    if not module:
        return typemap
    classes = inspect.getmembers(module, inspect.isclass)
    for cls in classes:
        for t in base_types:
            if cls[1] is not t and issubclass(cls[1], t):
                typemap[t.__qualname__] = cls[1]
    return typemap


def set_active_ruleset(key: Optional[str]) -> None:
    """Set the active ruleset by its key.
    
    Updates the global ACTIVE_RULESET_KEY variable to activate a specific ruleset.
    The active ruleset determines which validation rules are applied during parsing.
    
    Args:
        key: Unique identifier for the ruleset to activate, or None to deactivate.
    """
    global ACTIVE_RULESET_KEY
    ACTIVE_RULESET_KEY = key


class Ruleset:
    """Container for active ruleset type mappings.
    
    This class loads the currently active ruleset and creates a mapping from
    base component type names to their corresponding classes (either base classes
    or ruleset-specific subclasses).
    
    Attributes:
        typemap: Dictionary mapping qualified type names to class objects.
    """
    def __init__(self) -> None:
        """Initialize the ruleset with type mappings from the active ruleset.
        
        Loads the currently active ruleset (if any) and creates a type mapping
        that maps base type names to ruleset-specific implementations where available.
        """
        module = get_ruleset_module(ACTIVE_RULESET_KEY)
        self.typemap = identify_types(module)


if __name__ == "__main__":
    pass