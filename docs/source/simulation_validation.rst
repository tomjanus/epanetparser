Simulation validation
=====================

Hydraulic simulation validates the *behaviour* of a network, as opposed to
its structure or static configuration. ``epanetparser`` runs a WNTR/EPANET
simulation on demand and validates the results with a dedicated layer of
rules.

This is the third of the three validation layers described in
:doc:`validation_layers`: structural checks run while the document is read,
static checks run on the parsed model, and simulation checks run last, on the
WNTR results object. All three append to the same
:class:`~epanetparser.core.validation.results.ValidationReport`, tagging every
issue with a ``validation_layer``.

When it runs
------------

The layer runs only when simulation validation is requested — via the CLI or
programmatically. It runs after a hydraulic simulation has produced WNTR
results, not against the model, so a network can pass static validation and
still fail here.

Requirements
------------

Simulation validation needs the optional ``simulation`` extra (WNTR and the
EPANET binary):

.. code-block:: console

    $ pip install .[simulation]

Writing a simulation rule
-------------------------

Simulation rules take the simulation results object (a WNTR
``SimulationResults``) as their single positional argument. They are declared
with :func:`~epanetparser.core.validation.rules.simulation_rule`:

.. code-block:: python

    from epanetparser.core.validation.rules import simulation_rule

    @simulation_rule(attribute="pressure", required_outputs=["node.pressure"])
    def rule_minimum_pressure(results) -> None:
        """Minimum pressure must be above 20 psi at all junctions."""
        pressures = results.node["pressure"].min()
        assert pressures >= 20, f"Pressure {pressures:.1f} psi below 20 psi"

The ``required_outputs`` argument lists the result fields the rule needs
(e.g. ``"node.pressure"``, ``"link.flowrate"``). The engine skips the rule
when the simulation did not produce those outputs, so a rule set stays
meaningful across simulators with different output.

Simulation rules are collected separately from static rules and are only
executed when simulation validation is requested — via the CLI or
programmatically.

Pandera schemas
---------------

``core_rules.core_dynamic.hydraulic.schemas`` validates entire result
tables with Pandera data-frame schemas (optional ``epanetparser[schemas]``
extra; skipped when Pandera is absent):

* ``validate_node_results`` — schema for nodal result fields
  (pressure, head, quality, ...).
* ``validate_link_results`` — schema for link result fields
  (flowrate, velocity, headloss, ...).
* ``get_required_outputs_for_rule`` / ``check_outputs_available`` — helpers
  that let a rule declare and verify the outputs it needs before the schema
  checks run.

The schemas fail a rule as soon as a result field is missing, has the wrong
dtype, or contains non-finite values.

Running simulation validation
-----------------------------

:doc:`validation_layers` describes all three layers and the full set of CLI
switches; :doc:`usage` is the flag reference. The three switches relevant here
are:

.. code-block:: console

    # Static validation, then a simulation run and result validation
    $ epanetparser validate -f model.inp --simulate \
        --simulation-ruleset hydraulic

    # Only the simulation validation (skip static rules)
    $ epanetparser validate -f model.inp --simulation-only \
        --simulation-ruleset hydraulic

``--simulate`` runs the static rules first and then adds the simulation layer;
``--simulation-only`` skips the static rules; ``--simulation-ruleset`` selects
which simulation rule sets to run and may be repeated.

Programming interface
---------------------

.. code-block:: python

    import wntr

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork
    from epanetparser.core.validation import ValidationContext, Validator

    network, errors, _ = WNTREPANETNetwork.from_file("model.inp")
    report = network.validate()                          # static layer

    # Convert to a WNTR model and run the hydraulic simulation
    simulator = wntr.sim.EpanetSimulator(network.to_wntr())
    results = simulator.run_sim()

    # Simulation layer, appended to the static report
    context = ValidationContext(custom=("hydraulic",))
    report = Validator.from_context(context).validate_simulation(results, report)

    for issue in report.errors:
        print(issue.rule_id, issue.validation_layer, issue.message)

Result metadata
---------------

Simulation issues have ``validation_layer`` set to ``"simulation"``, so they
can be filtered separately in the unified
:class:`~epanetparser.core.validation.results.ValidationReport`. Their
``simulation_metadata`` records the rule's ``required_outputs`` (the outputs
the engine checked before running it), and their ``context`` carries the
rule's static context, such as its ruleset. Together these let downstream
consumers tell a simulation finding from a static one and know which outputs
it depended on.
