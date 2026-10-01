"""Mock rulesets for testing ruleset discovery and selection.

These modules are ordinary rule sets: plain ``assert``-based functions declared
with :func:`~epanetparser.core.validation.rule`, carrying the metadata a rule
set module needs. They deliberately do not subclass or patch the component
classes, because that is the design this package implements, and a mock that
subclassed them would test a design the package no longer has.

``basic_ruleset`` is the core rule set of the mock package and declares no
rules at all. It exists to prove that a rule set is discovered from its metadata
rather than from its contents, and that the ``__is_core__`` attribute is what
marks a rule set as core.

``advanced_ruleset`` and ``extra_ruleset`` are custom rule sets, so that
selecting more than one of them can be tested. Together they declare a rule that
always passes, rules that always fail, a rule carrying structured context, a
rule restricted to one component type with ``@match``, and a network rule, so
that discovery, selection and execution can all be exercised.
"""
