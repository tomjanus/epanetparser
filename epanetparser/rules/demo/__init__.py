"""Demo rule module for testing rule discovery.

This package demonstrates how to create a rule module that can be
auto-discovered by the discovery system. It contains example validation
rules and warnings that can be registered with the parser.
"""

# Required metadata fields for rule module discovery
__key__ = "demo"
__rule_module_name__ = "Demo Validation Rules"
__version__ = "1.0.0"
__description__ = "Demonstration validation rules for EPANET networks"

# Optional metadata
__author__ = "EPANET Parser Team"
__required_types__ = ["WNTREPANETNode", "WNTREPANETLink"]
