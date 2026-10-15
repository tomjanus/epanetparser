"""Core rulesets for EPANET models.

A ruleset is a collection of validation rules, discovered by the same
mechanism whether it is core or custom. This package holds the core rule
sets, organised by validation layer:

* :mod:`epanetparser.core_rules.core_static` holds the core static rule set
  (:mod:`epanetparser.core_rules.core_static.epanet_core`), which encodes
  what EPANET itself requires of a well-formed model;
* :mod:`epanetparser.core_rules.core_dynamic` holds the core dynamic rule
  sets, which run after a hydraulic simulation against its results.

Exactly one core static rule set may be selected for a validation run; any
number of custom rule sets (from :mod:`epanetparser.custom_rules`) and
dynamic core rule sets may be added alongside it.

Custom rule sets live in :mod:`epanetparser.custom_rules` and are discovered by
the same pass. The only difference between the two is module metadata: a core
rule set sets ``__is_core__ = True``, a custom rule set leaves it unset. The
layer a rule set belongs to is declared with ``__layer__`` (``"static"`` or
``"dynamic"``).

Notes
-----
Modules in this package are imported by the discovery pass, so a module that
fails to import is logged and skipped rather than breaking validation
entirely. Keep imports here cheap and side-effect free.
"""
