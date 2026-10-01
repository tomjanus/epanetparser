The epanetparser Library
========================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   network
   parser


Usage
=====

Overview
--------

The :class:`WNTREPANETNetwork` class provides a simple interface for an EPANET
model to be parsed, represented as a Python object, and validated.

Two factory methods create an instance:

* :meth:`WNTREPANETNetwork.from_file`
* :meth:`WNTREPANETNetwork.from_json`

...which operate on a file and a JSON string respectively. For example, to load
a model with the default arguments:

.. code-block:: python

    from importlib.resources import files

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    model = files("epanetparser.networks.core") / "Net1.inp"
    network, errors, warnings = WNTREPANETNetwork.from_file(model)

Five example networks ship with the package under ``epanetparser.networks.core``,
so there is a model to try this against without downloading anything. Both
``.inp`` and WNTR ``.json`` files are accepted. An ``.inp`` file is converted to
WNTR's JSON representation with WNTR before being parsed, so the model you get
back is always built from the JSON form.

If the input parses, the ``network`` variable holds the model and ``errors`` is
``None``. If it does not, ``network`` is ``None`` and ``errors`` holds the
structural problems. ``warnings`` holds any warnings raised during parsing, or
is ``None`` if there were none. Either ``network`` or ``errors`` is ``not None``,
but not both.

Parsing reports structural problems only. Semantic checks are a separate step:

.. code-block:: python

    report = network.validate()
    assert report.is_valid, [issue.code for issue in report.errors]

This separation is deliberate: assigning ``component.data`` never validates and
never raises, so building a model cannot fail because of a rule.

The ``errors`` and ``warnings`` objects
---------------------------------------

When present, the ``errors`` and ``warnings`` objects returned by the factory
methods are each a dictionary mapping the string names of EPANET network
components (``nodes``, ``links``, ``curves``, and so on) to the list of errors or
warnings generated for them.

Rule sets
---------

Validation runs against a rule set. Exactly one core rule set is always applied;
custom rule sets are added alongside it:

.. code-block:: python

    report = network.validate(["epanet_core", "milp"])

The selection may be given as a key, a list of keys, a
:class:`ValidationContext`, or a mapping, so a project can put the choice in one
place:

.. code-block:: python

    from epanetparser.core.validation import ValidationContext

    context = ValidationContext(core="epanet_core", custom=["milp"])
    report = network.validate(context)

A key that is not discovered raises :exc:`RuleSetSelectionError` rather than
being ignored, so a typo in a rule set name fails loudly instead of silently
validating less than you asked for.

Results
-------

:func:`validate` returns a :class:`ValidationReport`, never an exception for a
rule failure. A rule that raises anything other than :exc:`AssertionError` is a
defect in the rule, and raises :exc:`RuleExecutionError` instead of being
reported as a finding about the model.

.. code-block:: python

    report.is_valid            # False if any finding is Severity.ERROR
    report.errors              # the findings that block simulation
    report.warnings            # findings that inform without blocking
    report.by_code("E_UNKNOWN_CURVE_REFERENCE")
    report.by_component("T1")
    report.grouped_by_component()   # the shape display.write_results consumes
    report.as_dict()                # JSON-serialisable

A single component can also be validated on its own, with only the rules that
apply to it:

.. code-block:: python

    for node in network.nodes:
        for issue in node.validate().errors:
            print(issue.code, issue.component_name, issue.message)

The ``results_as_dict`` and ``results_as_json`` functions in
:mod:`epanetparser.core.display` translate a report into ``dict`` and JSON forms
respectively, and :func:`write_results` renders it on the console.

See :doc:`rules` for how to write rules and rule sets.
