"""Demonstration of auto-discovered validation warnings.

This file will be automatically discovered and loaded because it matches
the naming pattern '*_warnings.py'. This demonstrates that you can organize
rules and warnings in separate files for better maintainability.
"""
from epanetparser.core import register_warning


@register_warning("WNTREPANETLink", "roughness_coefficient_unusual")
def warn_roughness_unusual(instance):
    """Warn if roughness coefficient is unusual for the pipe material."""
    if instance.type == "Pipe":
        roughness = instance.data.get("roughness", 0)
        # Typical roughness values range from 0.01 to 150
        assert 0.001 <= roughness <= 500, \
            f"Roughness coefficient {roughness} is outside typical range (0.001-500)"


@register_warning("WNTREPANETLink", "minor_loss_high")  
def warn_minor_loss_high(instance):
    """Warn if minor loss coefficient is unusually high."""
    if instance.type == "Pipe":
        minor_loss = instance.data.get("minor_loss", 0)
        assert minor_loss <= 10, \
            f"Minor loss coefficient {minor_loss} is very high (typical values < 10)"
