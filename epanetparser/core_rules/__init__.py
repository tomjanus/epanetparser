"""Core rulesets for EPANET models.

A ruleset is a collection of validation rules, discovered by the same
mechanism whether it is core or custom. This package holds the core rulesets;
at present there is exactly one, :mod:`epanetparser.core_rules.epanet_core`,
and exactly one core ruleset may be selected for a validation run.

Custom rulesets live in :mod:`epanetparser.custom_rules` and are discovered by
the same pass. The only difference between the two is module metadata: a core
ruleset sets ``__is_core__ = True``, a custom ruleset leaves it unset.

Notes
-----
Modules in this package are imported by the discovery pass, so a module that
fails to import is logged and skipped rather than breaking validation
entirely. Keep imports here cheap and side-effect free.
"""
