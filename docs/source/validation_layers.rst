Validation layers
=================

``epanetparser`` validates a network at three distinct points. The layers are
independent but converge into a single :class:`~epanetparser.core.validation.results.ValidationReport`
so that callers see one, uniformly structured result regardless of which
checks produced the issues.

The three layers
----------------

.. list-table::
   :widths: 18 30 52
   :header-rows: 1

   * - Layer
     - When it runs
     - What it checks
   * - Structural
     - While parsing the file, before a network object exists
     - The file is well-formed EPANET: valid section headers, required
       fields, numeric values, and references that resolve
       (e.g. ``start_node_name``/``end_node_name`` point at defined nodes).
       Problems surface as structured ``InpParseError`` subclasses and are
       also reported as issues with ``validation_layer="structural"``.
   * - Static
     - After the ``WNTREPANETNetwork`` is built
     - Simulator-agnostic rules from the core rule set (``epanet_core``)
       plus any custom rule sets. These check the model graph, parameters,
       units, and configuration without running a simulation.
       Rules are declared with ``@rule`` and ``@network_rule``.
   * - Simulation
     - After a hydraulic simulation, on the results object
     - Post-simulation output such as pressures, flows, velocities, and
       quality. Rules are declared with ``@simulation_rule`` and are only
       executed when simulation validation is requested. They are skipped
       when the outputs they require were not produced by the simulator.
       ``custom_rules.pandera_schemas`` provides Pandera-based checks over
       result tables.

Unified report
--------------

Every issue carries a ``validation_layer`` so that layered checks can be
combined, filtered, and reported together:

* :class:`~epanetparser.core.validation.results.ValidationIssue` gains a
  ``validation_layer`` field (one of ``"structural"``, ``"static"``, or
  ``"simulation"``) and a ``simulation_metadata`` dictionary for
  post-simulation context (e.g. a failing timestep or ``float('inf')`` value).
* :class:`~epanetparser.core.validation.results.ValidationReport` aggregates
  issues from every layer. Its JSON serialisation (``schema_version``
  ``"1.0"``/``"2.0"``) includes the new fields so downstream consumers can
  reproduce the layered result.

Why three layers
----------------

The layers answer different questions and fail at different stages:

#. Can the file be read at all? (structural)
#. Is the model a sound EPANET model? (static)
#. Does the model behave acceptably under hydraulics? (simulation)

Separating them means a structurally valid model can be rejected by an
application rule set, and a statically valid model can still fail at
simulation time — without any of those outcomes contaminating the others.
The CLI lets you run static only, simulation only, or both
(``--simulate`` and ``--simulation-only``; see :doc:`simulation_validation`
and :doc:`usage`).