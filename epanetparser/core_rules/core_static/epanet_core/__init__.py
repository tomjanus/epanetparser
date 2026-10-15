"""Core static ruleset for EPANET models.

This is the single core ruleset of the static layer. It encodes what EPANET
itself requires of a well-formed model, and nothing more: a model that passes
these rules is simulator-agnostic and free of internal contradictions, but
nothing here constrains what a particular application can do with it.

The ruleset is a package, so its rules are split by component collection:

===============  ======================================================
Module           Covers
===============  ======================================================
``nodes``        Junctions, reservoirs, tanks
``links``        Pipes, pumps, valves
``curves``       Curve names, types and points
``patterns``     Pattern names
``options``      Required option groups
``sources``      Water quality sources
``controls``     Control kinds
``network_info`` Model metadata
``network``      Names, duplicates and cross-component references
===============  ======================================================

Custom rulesets are discovered through the same mechanism and differ only in
that they do not set ``__is_core__``. Selecting a custom ruleset adds its rules
to this one; it never replaces or subclasses anything here. Core dynamic
rule sets (see :mod:`epanetparser.core_rules.core_dynamic`) are selected as
custom rule sets too; they never replace this one.
"""
#: Stable key of this ruleset, used in a ValidationContext.
__key__ = "epanet_core"

#: Human-readable name.
__ruleset_name__ = "EPANET core rules"

#: Version of this ruleset.
__version__ = "1.0.0"

#: Marks this ruleset as the core ruleset. Exactly one core ruleset of the
#: static layer may be selected for a validation run; custom rulesets and
#: dynamic core rule sets leave this unset or carry a different layer.
__is_core__ = True

#: The validation layer this ruleset belongs to: rules here run against a
#: parsed model without any simulation, so the layer is static.
__layer__ = "static"

#: Summary of what this ruleset checks.
__description__ = (
    "Simulator-agnostic checks that a model is a well-formed EPANET model: "
    "required component fields, valid component types, well-formed curves, "
    "unique component names, and resolvable references between components."
)
