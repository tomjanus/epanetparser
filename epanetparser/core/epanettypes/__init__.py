"""EPANET component types package.

This package provides type classes representing all EPANET network components,
including nodes, links, patterns, curves, controls, sources, options, 
and network metadata.

All component classes inherit from the abstract base class `WNTREPANETType` and
use descriptor-based validation through `WNTREPANETTypeValidator` to ensure data
integrity according to configurable rulesets.

Key Features
------------
- **Lazy loading**: Component classes are imported on-demand to avoid circular
  import issues during module initialization.
- **Ruleset-based validation**: Components can be validated against different
  rulesets (e.g., MILP constraints, standard EPANET rules).
- **Automatic validation**: Data validation occurs automatically when component
  data is assigned, using the descriptor protocol.
- **Warning tracking**: Non-fatal validation warnings are collected and accessible
  via the `has_warnings` property.

Classes
-------
WNTREPANETNode
    Node components: Junction, Reservoir, Tank
WNTREPANETLink
    Link components: Pipe, Pump, Valve
WNTREPANETPattern
    Demand and control patterns
WNTREPANETCurve
    Pump and valve characteristic curves
WNTREPANETControl
    Simple and rule-based controls
WNTREPANETSource
    Water quality sources
WNTREPANETOptions
    Simulation options and parameters
WNTREPANETNetworkInfo
    Network metadata (name, description, etc.)

Functions
---------
_get_types
    Lazy initialization of type mappings from the active ruleset.
__getattr__
    Module-level attribute access hook for lazy class loading.
__dir__
    Custom module-level dir() implementation for autocompletion.

Notes
-----
This module uses PEP 562 (`__getattr__` at module level) to implement lazy
import of component classes. Classes are only imported when first accessed,
which prevents circular import issues that would occur if all classes were
imported at module initialization time.

Examples
--------
Import specific component types:

>>> from epanetparser.core.epanettypes import WNTREPANETNode, WNTREPANETLink
>>> node = WNTREPANETNode({"name": "J1", "elevation": 100.0})
>>> link = WNTREPANETLink({"name": "P1", "link_type": "Pipe"})

Import all types:

>>> from epanetparser.core import epanettypes
>>> junction_class = epanettypes.WNTREPANETNode

See Also
--------
epanetparser.core.epanettypes.base : Abstract base class for all components
epanetparser.core.validation : Descriptor-based validation system
epanetparser.core.rulesets : Ruleset definitions for validation
"""
from importlib import import_module
from epanetparser.core import ruleset_registry

# Imports are deferred to avoid circular import issues
# The __getattr__ function below handles lazy loading of type classes

__all__ = [ 
    "WNTREPANETControl",    # pylint: disable=undefined-all-variable
    "WNTREPANETCurve",      # pylint: disable=undefined-all-variable
    "WNTREPANETLink",       # pylint: disable=undefined-all-variable
    "WNTREPANETNode",       # pylint: disable=undefined-all-variable
    "WNTREPANETOptions",    # pylint: disable=undefined-all-variable
    "WNTREPANETPattern",    # pylint: disable=undefined-all-variable
    "WNTREPANETSource",     # pylint: disable=undefined-all-variable
    "WNTREPANETNetworkInfo" # pylint: disable=undefined-all-variable
]


# Lazy initialization to avoid circular imports
_rs = None                  # pylint: disable=invalid-name
_types_initialized = False  # pylint: disable=invalid-name


def _get_types() -> dict[str, type]:
    """Lazy initialization of type mappings from the active ruleset.
    
    This function initializes the global ruleset instance and retrieves the
    type mapping dictionary that maps component type names to their corresponding
    class implementations. The initialization is performed only once and cached
    globally.
    
    The type mapping is provided by the active ruleset, which may customize
    component classes based on validation requirements (e.g., different classes
    for MILP-compliant networks vs. standard EPANET networks).
    
    Returns
    -------
    dict of {str: type}
        Dictionary mapping component type names (e.g., 'WNTREPANETNode',
        'WNTREPANETLink') to their corresponding class objects.
    
    Notes
    -----
    This function uses module-level global variables `_rs` and `_types_initialized`
    to cache the ruleset instance and prevent redundant initialization.
    
    The function is called internally by `__getattr__` but can also be used
    directly to access the full type mapping.
    
    Examples
    --------
    >>> typemap = _get_types()
    >>> typemap['WNTREPANETNode']
    <class 'epanetparser.core.epanettypes.node.WNTREPANETNode'>
    
    See Also
    --------
    epanetparser.core.rulesets : Ruleset system that provides type mappings
    __getattr__ : Uses this function for lazy class loading
    """
    global _rs, _types_initialized # pylint: disable=global-statement
    if not _types_initialized:
        _rs = ruleset_registry.Ruleset()
        _types_initialized = True
    return _rs.typemap


def __dir__() -> list[str]:
    """Custom module-level dir() implementation for autocompletion.
    
    This function returns a list of all available attributes in the module,
    including lazily loaded component type classes. It is used by Python's
    built-in `dir()` function to provide a complete view of the module's
    namespace, even for attributes that are not yet imported.
    
    Returns
    -------
    list of str
        List of attribute names available in the module, including:
        - All component type class names (e.g., 'WNTREPANETNode', 'WNTREPANETLink')
        - Any other module-level attributes defined in this file.
    
    Notes
    -----
    This implementation ensures that IDEs and interactive shells can provide
    autocompletion for all component types, even though they are lazily imported
    via the `__getattr__` function. It combines the standard module attributes
    with the keys from the type mapping dictionary.
    """
    standard_attrs = list(globals().keys())
    type_attrs = list(_get_types().keys())
    return sorted(set(standard_attrs + type_attrs))


def __getattr__(name) -> type:
    """Lazy loading of type classes via module-level attribute access.
    
    This special function implements PEP 562 module `__getattr__`, which is
    automatically called by Python when an attribute is accessed on the module
    that doesn't exist in the module's namespace. It enables lazy (on-demand)
    importing of component type classes to avoid circular import issues.
    
    When a component class is first accessed (e.g., `from epanettypes import
    WNTREPANETNode`), this function:
    
    1. Looks up the module name for the requested class
    2. Dynamically imports the module
    3. Retrieves the class from the imported module
    4. Caches the class in the module's global namespace
    5. Returns the class
    
    Subsequent accesses to the same class will retrieve it directly from the
    module namespace without triggering this function again.
    
    Parameters
    ----------
    name : str
        Name of the attribute (class) being accessed. Expected to be one of
        the component type class names (e.g., 'WNTREPANETNode', 'WNTREPANETLink').
    
    Returns
    -------
    type
        The requested component class.
    
    Raises
    ------
    AttributeError
        If `name` is not a recognized component type class name.
    
    Notes
    -----
    This function is part of Python's module-level `__getattr__` protocol
    introduced in PEP 562. It allows modules to customize attribute access
    and implement features like lazy loading, deprecation warnings, or
    dynamic attribute generation.
    
    The implementation maintains a mapping (`type_module_map`) of class names
    to their source module names to facilitate dynamic imports.
    
    Caching the imported class in `globals()` ensures that subsequent imports
    are fast and don't trigger the dynamic import machinery again.
    
    Examples
    --------
    First access triggers lazy import:
    
    >>> from epanetparser.core.epanettypes import WNTREPANETNode
    # __getattr__('WNTREPANETNode') is called
    # Module 'node' is imported
    # WNTREPANETNode class is cached and returned
    
    Subsequent access uses cached class:
    
    >>> from epanetparser.core.epanettypes import WNTREPANETNode
    # Class is retrieved directly from module namespace
    # __getattr__ is not called
    
    Invalid attribute raises error:
    
    >>> from epanetparser.core.epanettypes import NonExistentClass
    AttributeError: module 'epanetparser.core.epanettypes' has no attribute 'NonExistentClass'
    
    See Also
    --------
    importlib.import_module : Used for dynamic module importing
    
    References
    ----------
    .. [1] PEP 562 -- Module __getattr__ and __dir__
           https://www.python.org/dev/peps/pep-0562/
    """
    # Mapping of class names to their module names
    type_module_map = {
        "WNTREPANETControl": "control",
        "WNTREPANETCurve": "curve",
        "WNTREPANETLink": "link",
        "WNTREPANETNode": "node",
        "WNTREPANETOptions": "options",
        "WNTREPANETPattern": "pattern",
        "WNTREPANETSource": "source",
        "WNTREPANETNetworkInfo": "network_info",
    }
    if name in type_module_map:
        module_name = f".{type_module_map[name]}"
        module = import_module(module_name, package=__name__)
        # Get the class from the module and cache it in this module's namespace
        cls = getattr(module, name)
        globals()[name] = cls
        return cls
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
