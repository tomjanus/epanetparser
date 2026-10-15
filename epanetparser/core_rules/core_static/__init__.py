"""Core static rule sets for EPANET models.

This package holds the core rule sets of the static layer: checks that run
against a parsed model without any simulation. A rule set here sets
``__is_core__ = True`` and ``__layer__ = "static"``.

Exactly one core static rule set may be selected for a validation run; any
number of custom rule sets may be added alongside it. Custom rule sets live
in :mod:`epanetparser.custom_rules`, and the dynamic core rule sets live in
:mod:`epanetparser.core_rules.core_dynamic`. All are discovered by the same
pass; only module metadata differs.

Notes
-----
Modules in this package are imported by the discovery pass, so a module that
fails to import is logged and skipped rather than breaking validation
entirely. Keep imports here cheap and side-effect free.
"""
