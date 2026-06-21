"""Demonstration of auto-discovered validation rules.

This file will be automatically discovered and loaded because it matches
the naming pattern '*_rules.py'. Any rules or warnings defined here using
the @register_rule and @register_warning decorators will be automatically
registered when the epanetparser.plugins module is imported.
"""
from epanetparser.core import register_rule, register_warning


@register_rule("WNTREPANETNode", "elevation_reasonable")
def validate_node_elevation(instance):
    """Node elevation should be within reasonable bounds."""
    elevation = instance.data.get("elevation", 0)
    assert -500 <= elevation <= 5000, \
        f"Node elevation {elevation}m is outside reasonable range (-500m to 5000m)"


@register_warning("WNTREPANETNode", "elevation_unusual")
def warn_node_elevation_unusual(instance):
    """Warn if node elevation is unusual but not invalid."""
    elevation = instance.data.get("elevation", 0)
    if elevation < 0:
        assert elevation >= -100, \
            f"Node elevation {elevation}m is below sea level (verify data)"
    elif elevation > 2000:
        assert elevation <= 3000, \
            f"Node elevation {elevation}m is very high (verify data)"
