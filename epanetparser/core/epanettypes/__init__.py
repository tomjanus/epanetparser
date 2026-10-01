"""EPANET component types.

This package holds one class per component collection. Each is a thin wrapper
around the dictionary the parser produced, plus read-only accessors for the
fields its collection is expected to have.

Component classes contain no validation logic and are not extended to add it.
Validation rules live in rule sets under :mod:`epanetparser.core_rules` and
:mod:`epanetparser.custom_rules`, are selected through
:mod:`epanetparser.core.validation`, and run when ``component.validate()`` or
``network.validate()`` is called.

The classes are imported lazily through :func:`__getattr__`, which keeps
``import epanetparser.core.epanettypes`` cheap and avoids a circular import
between the model and the validation package.

# TODO: the component inventory in ``_TYPE_MODULES`` below is a fourth place the
#       same list is written down, and the map is maintained by hand. See
#       docs/TODO_MODEL_LAYER_DUPLICATION.md, section 1.

Classes
-------
WNTREPANETControl
    Simple and rule-based controls.
WNTREPANETCurve
    Pump, head, efficiency and volume curves.
WNTREPANETLink
    Pipes, pumps and valves.
WNTREPANETNode
    Junctions, reservoirs and tanks.
WNTREPANETNetworkInfo
    Model metadata.
WNTREPANETOptions
    Simulation options.
WNTREPANETPattern
    Time patterns.
WNTREPANETSource
    Water quality sources.

Examples
--------
>>> from epanetparser.core.epanettypes import WNTREPANETNode
>>> node = WNTREPANETNode({"name": "J1", "node_type": "Junction", "elevation": 10.0})
>>> node.validate().is_valid
True

See Also
--------
epanetparser.core.epanettypes.base : Abstract base class for all components.
epanetparser.core.validation : Rule execution and structured results.
"""
from types import ModuleType
from importlib import import_module
from typing import Dict

#: Component class name to the submodule that defines it.
_TYPE_MODULES: Dict[str, str] = {
    "WNTREPANETControl": "control",
    "WNTREPANETCurve": "curve",
    "WNTREPANETLink": "link",
    "WNTREPANETNode": "node",
    "WNTREPANETNetworkInfo": "network_info",
    "WNTREPANETOptions": "options",
    "WNTREPANETPattern": "pattern",
    "WNTREPANETSource": "source",
}

__all__ = sorted(_TYPE_MODULES)


def __getattr__(name: str) -> type:
    """Import a component class on first access (PEP 562).

    Parameters
    ----------
    name : str
        Attribute being looked up on the module.

    Returns
    -------
    type
        The requested component class, cached in the module namespace so
        later accesses skip the import.

    Raises
    ------
    AttributeError
        If ``name`` is not a component class defined in this package.
    """
    module_name = _TYPE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(
            f"module '{__name__}' has no attribute '{name}'; "
            f"available: {', '.join(__all__)}"
        )
    module: ModuleType = import_module(f".{module_name}", package=__name__)
    cls = getattr(module, name)
    globals()[name] = cls
    return cls


def __dir__() -> list:
    """List module attributes, including the lazily imported classes."""
    return sorted(set(globals()) | set(_TYPE_MODULES))
