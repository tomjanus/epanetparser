"""EPANET component types package.

This package provides type classes for EPANET network components that can be
customized through rulesets for different validation requirements.

The type mappings are loaded lazily to avoid circular import issues.
"""

# Lazy initialization to avoid circular imports
_rs = None
_types_initialized = False


def _get_types():
    """Lazy initialization of type mappings from the active ruleset.
    
    Returns:
        dict: Mapping of type names to their corresponding classes.
    """
    global _rs, _types_initialized
    if not _types_initialized:
        from epanetparser import rules
        _rs = rules.Ruleset()
        _types_initialized = True
    return _rs.typemap


def __getattr__(name):
    """Lazy loading of type classes.
    
    This function is called when an attribute is accessed that doesn't exist
    in the module's namespace. It enables lazy loading of type classes to
    avoid circular import issues during module initialization.
    
    Args:
        name: Name of the attribute being accessed.
    
    Returns:
        The requested type class.
    
    Raises:
        AttributeError: If the requested attribute doesn't exist.
    """
    type_names = [
        "WNTREPANETNetworkInfo",
        "WNTREPANETOptions",
        "WNTREPANETCurve",
        "WNTREPANETPattern",
        "WNTREPANETNode",
        "WNTREPANETLink",
        "WNTREPANETSource",
        "WNTREPANETControl",
    ]
    
    if name in type_names:
        typemap = _get_types()
        return typemap[name]
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
