"""Core dynamic rule sets for EPANET models.

This package holds the core rule sets of the dynamic layer: checks that run
after a hydraulic simulation against its results. A rule set here sets
``__is_core__ = True`` and ``__layer__ = "dynamic"``.

A dynamic core rule set cannot occupy the static core slot (that slot must
resolve to exactly one rule set that is core *and* static); it is selected
instead as a custom rule set alongside the static core rule set, which is
how the CLI's ``--simulation-ruleset hydraulic`` and the MCP validation
tools select it.
"""
