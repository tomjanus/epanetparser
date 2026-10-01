"""Custom rulesets for EPANET models.

A custom ruleset expresses the constraints of one application on top of the
core ruleset: what a particular solver can represent, what a particular study
assumes about a network. It is a plain module of ``assert``-based rules, and
it does not subclass, patch or otherwise depend on the component classes.

Discovery is the same mechanism used for the core ruleset: a module of this
package that declares ``__key__``, ``__ruleset_name__`` and ``__version__`` is
found automatically. Leaving ``__is_core__`` unset is what makes it custom.

Select custom rulesets alongside the core ruleset:

.. code-block:: python

    from epanetparser.core.validation import validate

    report = validate(network, ["epanet_core", "milp"])

Notes
-----
Modules in this package are imported by the discovery pass, so a module that
fails to import is logged and skipped rather than breaking validation
entirely. Keep imports here cheap and side-effect free.

Examples
--------
>>> from epanetparser.core.validation import discover_ruleset_modules
>>> sorted(discover_ruleset_modules(["epanetparser.custom_rules"]))
['milp']
"""
