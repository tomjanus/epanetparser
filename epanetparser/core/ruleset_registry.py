"""Ruleset discovery and management for EPANET parser validation.

This module handles the discovery and loading of validation rulesets that define
specialized validation rules for EPANET network components. 
It provides functionality to:

- Discover and enumerate available rulesets
- Load and activate specific rulesets
- Map base component types to ruleset-specific subclasses
- Activate rulesets and manage the active ruleset state

Rulesets are Python modules located in the epanetparser.core.rulesets package. Each ruleset
can define specialized versions of base component types with additional validation rules.

Note
-----
Rulesets and rule validation plugins are complementary but distinct concepts.

A ruleset specifies a collection of validation rules, constraints, and type
definitions that describe how a particular class of EPANET models should be
validated for a specific purpose, e.g. for a particular application or analysis
that might impose certain restrictions on the already valid model. 

On the other hand, a rule validation plugin (see epanetparser.core.rule_registry) 
is responsible for registering generic rules with the validation framework and 
exposing them to users, which allows these rules to be written in separate modules 
instead of being hardcoded into the core validation logic.

In other words, core rules and warnings are implemented as plugins to enable the 
development of shared validation standards that can be applied consistently across EPANET
models. Such standards are intended to be generally applicable and independent
of specific modelling objectives. Rulesets extend these standards by introducing 
additional constraints tailored to particular domains or workflows, such as pump 
scheduling, leak detection, optimization, or other specialized analyses.
"""
from typing import List, Tuple, Dict, Any, Optional, TypeAlias
from types import ModuleType
import importlib
import inspect

RULESET_BASE = "epanetparser.rulesets"
ACTIVE_RULESET_KEY: Optional[str] = None

ModuleKey: TypeAlias = str


class RulesetRegistry:
    """Central registry for ruleset discovery, activation, and management.
    
    Manages:
    - Discovery of available rulesets
    - Activation/deactivation of rulesets
    - Type mapping (base types → ruleset-specific types)
    - Metadata caching
    
    Attributes
    ----------
    _base : str
        Base module path for rulesets
    _active_key : Optional[ModuleKey]
        Currently active ruleset key
    _metadata_cache : Optional[Dict]
        Cached ruleset metadata
    _module_cache : Dict[ModuleKey, ModuleType]
        Cache of loaded ruleset modules
    """
    def __init__(self, base: str = RULESET_BASE) -> None:
        self._base = base
        self._active_key: Optional[ModuleKey] = None
        self._metadata_cache: Optional[Dict] = None
        self._module_cache: Dict[ModuleKey, ModuleType] = {}
        
    def discover_rulesets(self) -> List[Tuple[ModuleKey, ModuleType]]:
        """Discover all available ruleset modules in the rulesets package.
        
        Returns
        -------
        List[Tuple[str, ModuleType]]
            List of (name, module) tuples for all modules in the rulesets package.
        """
        importlib.invalidate_caches()
        base_module = importlib.import_module(self._base)
        return inspect.getmembers(base_module, inspect.ismodule)

    def activate(self, key: Optional[str]) -> None:
        """Activate a ruleset by key."""
        self._active_key = key
        global ACTIVE_RULESET_KEY  # pylint: disable=global-statement
        ACTIVE_RULESET_KEY = key
        
    def deactivate(self) -> None:
        """Deactivate the current ruleset."""
        self._active_key = None
        global ACTIVE_RULESET_KEY  # pylint: disable=global-statement
        ACTIVE_RULESET_KEY = None
        self._metadata_cache = None
        self._module_cache.clear()
        
    def get_module(self, key: Optional[str]) -> Optional[ModuleType]:
        """
        Get a specific ruleset module by its key.
        
        Searches all available ruleset modules for one matching the given key.
        
        Parameters
        ----------
        key : Optional[str]
            Unique identifier for the ruleset to retrieve.
        base : str, default=RULESET_BASE
            Base module path for rulesets.
        
        Returns
        -------
        Optional[ModuleType]
            The ruleset module object if found, None otherwise.
        """
        if key is None:
            return None
        try:
            return self._module_cache[key]
        except KeyError:
            modules = (_module for _, _module in self.discover_rulesets())
            for module in modules:
                if module.__key__ == key:
                    return module
        return None
        
    def get_metadata(self) -> Dict[ModuleKey, Dict[str, Any]]:
        """
        Get metadata for all available rulesets.
        
        Discovers all rulesets in the rulesets package and returns their metadata
        including name, module path, version, and description.
        
        Parameters
        ----------
        base : str, default=RULESET_BASE
            Base module path for rulesets.
        
        Returns
        -------
        Dict[ModuleKey, Dict[str, Any]]
            Dictionary mapping ruleset keys to their metadata dictionaries.
            Each metadata dict contains:
            
            - name : Human-readable ruleset name
            - modpath : Full module path
            - version : Ruleset version string
            - description : Ruleset description
            - required_rules : List of rules required by this ruleset
            - conflicting_rules : List of rules that conflict with this ruleset
        """
        if self._metadata_cache is not None:
            return self._metadata_cache
        modules = {}
        for _module in self.discover_rulesets():
            # Required attributes: raise AttributeError if missing
            _modpath = _module[0]
            _mod_data = _module[1]
            for attr in ("__key__", "__ruleset_name__", "__version__"):
                if not hasattr(_mod_data, attr):
                    raise AttributeError(
                        f"Ruleset module '{_modpath}' is missing required attribute {attr}"
                    )
            modules[_mod_data.__key__] = {
                "name": _mod_data.__ruleset_name__,
                "modpath": _modpath,
                "version": _mod_data.__version__,
                "description": getattr(_mod_data, "__description__", None),
                "required_rules": getattr(_mod_data, "__required_rules__", None),
                "conflicting_rules": getattr(_mod_data, "__conflicting_rules__", None),
            }
        self._metadata_cache = modules
        return modules
    
    def describe_rulesets(self, use_rich: bool = True) -> str:
        """
        Generate a formatted description of all available rulesets.
        
        Parameters
        ----------
        use_rich : bool, optional
            If True, format output for rich console display. Default is True.
        
        Returns
        -------
        str
            Formatted string describing all available rulesets.
        """
        modules = self.get_metadata()
        if use_rich:
            output = "\n[bold underline]Available Rulesets[/bold underline]\n\n"
            for idx, (key, mod) in enumerate(modules.items(), 1):
                output += (
                    f"[bold cyan][{idx}][/bold cyan] "
                    "[bold green]Name: [/bold green]"
                    f"[bold]{mod['name']}[/bold]\n"
                    f"    [dim]Version:[/dim] {mod['version']}\n"
                    f"    [dim]Key:[/dim]     {key}\n"
                    f"    [dim]Required Rules:[/dim] {mod['required_rules']}\n"
                    f"    [dim]Conflicting Rules:[/dim] {mod['conflicting_rules']}\n"
                    f"    [dim]Summary:[/dim] [blue][italic]{mod['description']}[/italic][/blue]\n\n"
                )
        else:
            output = "Available Rulesets:\n\n"
            for idx, (key, mod) in enumerate(modules.items(), 1):
                output += (
                    f"[{idx}] Name: {mod['name']}\n"
                    f"    Version: {mod['version']}\n"
                    f"    Key:     {key}\n"
                    f"    Required Rules: {mod['required_rules']}\n"
                    f"    Conflicting Rules: {mod['conflicting_rules']}\n"
                    f"    Summary: {mod['description']}\n\n"
                )
        return output

_ruleset_registry = RulesetRegistry()  # Singleton instance for global access

from dataclasses import dataclass, field


@dataclass
class BaseTypes:
    node: Any
    
    @classmethod
    def from_defaults(cls) -> "BaseTypes":
        """ """
        
    

class Ruleset:
    """
    Container for active ruleset type mappings.
    
    This class loads the currently active ruleset and creates a mapping from
    base component type names to their corresponding classes (either base classes
    or ruleset-specific subclasses).
    
    Attributes
    ----------
    typemap : Dict[str, type]
        Dictionary mapping qualified type names to class objects.
    """
    def __init__(self, registry: RulesetRegistry, active_ruleset_key: Optional[str] = None) -> None:
        """
        Initialize the ruleset with type mappings from the active ruleset.
        
        Loads the currently active ruleset (if any) and creates a type mapping
        that maps base type names to ruleset-specific implementations where available.
        """
        self.registry = registry
        if not active_ruleset_key:
            active_ruleset_key = ACTIVE_RULESET_KEY
        module: ModuleType | None = self.registry.get_module(active_ruleset_key)
        self.typemap: Dict[str, type] = self.get_typemap(module)

    def get_typemap(self, module: Optional[ModuleType]) -> Dict[str, type]:
        """
        Create a type mapping from base types to ruleset-specific subclasses.
        
        Maps base EPANET component type names to their corresponding classes,
        using ruleset-specific subclasses if available, or base classes otherwise.
        This allows rulesets to override validation behavior by subclassing base types.
        
        Parameters
        ----------
        module : ModuleType or None
            Ruleset module to search for specialized type subclasses.
            If None, returns mapping to base types only.
        
        Returns
        -------
        Dict[str, type]
            Dictionary mapping qualified type names (e.g., 'WNTREPANETNode') to
            their corresponding class objects (base or ruleset-specific).
        """   
        from epanetparser.core.epanettypes.node import WNTREPANETNode                 # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.control import WNTREPANETControl           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.curve import WNTREPANETCurve               # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.link import WNTREPANETLink                 # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.network_info import WNTREPANETNetworkInfo  # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.options import WNTREPANETOptions           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.pattern import WNTREPANETPattern           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.source import WNTREPANETSource             # pylint: disable=import-outside-toplevel

        base_types: Tuple = (
            WNTREPANETNode, WNTREPANETControl, WNTREPANETCurve, WNTREPANETLink,
            WNTREPANETNetworkInfo, WNTREPANETOptions, WNTREPANETPattern, WNTREPANETSource
        )
        # Create a defautlt mapping to base types
        typemap = {t.__qualname__: t for t in base_types}
        if not module:
            return typemap
        classes: List[Tuple[str, Any]] = inspect.getmembers(module, inspect.isclass)
        for cls in classes:
            # Replace base type with ruleset-specific subclass if it exists and is a subclass of the base type
            for t in base_types:
                if cls[1] is not t and issubclass(cls[1], t):
                    typemap[t.__qualname__] = cls[1]
        return typemap
    
    def update_typemap(self, module: Optional[ModuleType]) -> None:
        """
        Update the typemap with new ruleset-specific subclasses from the given module.
        
        This method allows dynamic updating of the typemap when a new ruleset is
        activated or when additional component types are defined in a ruleset module.
        
        Parameters
        ----------
        module : ModuleType or None
            Ruleset module to search for specialized type subclasses.
            If None, no changes are made to the typemap.
        """
        if not module:
            return
        new_typemap = self.get_typemap(module)
        self.typemap.update(new_typemap)
        
    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}(active_ruleset_key={ACTIVE_RULESET_KEY})"
    
    def __str__(self) -> str:
        return f"Ruleset(active_ruleset_key={ACTIVE_RULESET_KEY}, typemap={self.typemap})"

#########################################################

def get_ruleset_modules() -> List[Tuple[str, ModuleType]]:
    """ Convenience function for backward compatibility to retrieve ruleset modules. """
    return _ruleset_registry.discover_rulesets()

def set_active_ruleset(key: Optional[str]) -> None:
    """
    Set the active ruleset by its key.
    
    Updates the global ACTIVE_RULESET_KEY variable to activate a specific ruleset.
    The active ruleset determines which validation rules are applied during parsing.
    
    Parameters
    ----------
    key : Optional[str]
        Unique identifier for the ruleset to activate, or None to deactivate.
    """
    global ACTIVE_RULESET_KEY # pylint: disable=global-statement
    ACTIVE_RULESET_KEY = key

def get_ruleset_module(key: Optional[str], base: str = RULESET_BASE) -> Optional[ModuleType]:
    """
    Get a specific ruleset module by its key.
    
    Searches all available ruleset modules for one matching the given key.
    
    Parameters
    ----------
    key : Optional[str]
        Unique identifier for the ruleset to retrieve.
    base : str, default=RULESET_BASE
        Base module path for rulesets.
    
    Returns
    -------
    Optional[ModuleType]
        The ruleset module object if found, None otherwise.
    """
    return _ruleset_registry.get_module(key)

def describe_rulesets(use_rich: bool = True) -> str:
    """
    Generate a formatted description of all available rulesets.
    
    Returns
    -------
    str
        Formatted string describing all available rulesets.
    """
    return _ruleset_registry.describe_rulesets(use_rich=use_rich)

#########################################################




def identify_types(module: Optional[ModuleType]) -> Dict[str, type]:
    """
    Create a type mapping from base types to ruleset-specific subclasses.
    
    Maps base EPANET component type names to their corresponding classes,
    using ruleset-specific subclasses if available, or base classes otherwise.
    This allows rulesets to override validation behavior by subclassing base types.
    
    Parameters
    ----------
    module : ModuleType or None
        Ruleset module to search for specialized type subclasses.
        If None, returns mapping to base types only.
    
    Returns
    -------
    Dict[str, type]
        Dictionary mapping qualified type names (e.g., 'WNTREPANETNode') to
        their corresponding class objects (base or ruleset-specific).
    """   
    ruleset = Ruleset(_ruleset_registry, ACTIVE_RULESET_KEY)
    return ruleset.typemap







if __name__ == "__main__":
    from rich import print as rprint
    # Describe rulesets
    rprint(describe_rulesets(use_rich=True))
    #print(describe_rulesets(use_rich=False))
    milp_ruleset = Ruleset(active_ruleset_key='milp')
    rprint(milp_ruleset)
    rprint("\nComponent type mappings for active ruleset:\n")
    for component_name, component_class in milp_ruleset.typemap.items():
        rprint("Component:", component_name, "->", component_class)
