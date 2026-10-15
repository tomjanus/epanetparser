Validation layers
=================

``epanetparser`` validates a network at three distinct points. The layers are
independent but converge into a single
:class:`~epanetparser.core.validation.results.ValidationReport` so that callers
see one, uniformly structured result regardless of which checks produced the
issues.

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
       ``core_rules.core_dynamic.hydraulic.schemas`` provides Pandera-based
       checks over result tables (optional ``epanetparser[schemas]`` extra).

Each layer is described in turn below. :doc:`simulation_validation` covers
the third layer in more depth.

Layer 1: structural
-------------------

*When it runs.* While the input document is read, before a
``WNTREPANETNetwork`` exists. An INP document is read by
``read_inp_to_dict``; a WNTR JSON document is read by the WNTR JSON parser.

*What it checks.* That the document is well-formed and internally
consistent: section headers are recognised, data lines have the right number
of fields, numeric values parse, and names referenced within the document
resolve. The parser does not validate the model's hydraulics or its
EPANET conformance — those are the static layer's job.

*Error taxonomy.* Failures are raised as ``InpParseError`` subclasses, defined
in :mod:`epanetparser.core.io.inp_errors`:

.. list-table::
   :widths: 28 26 46
   :header-rows: 1

   * - Exception
     - EPANET codes
     - Meaning
   * - ``InpSyntaxError``
     - 201, 202, 213
     - Malformed section headers, wrong field counts, invalid values.
       Defaults to code 201.
   * - ``InpSemanticError``
     - 203, 205, 209, 211, 217, 225
     - Valid syntax but unresolved references or invalid values.
       Defaults to code 203.
   * - ``InpStructuralError``
     - 200, 204
     - Missing required sections or fundamental file problems.
       Defaults to code 204.

``EPANET_ERROR_MAP`` maps an EPANET code to the matching subclass, and
``create_inp_error`` uses it to construct the right exception from a code.
Each exception carries the offending ``line_number``, the ``section``, the
``error_code`` and a list of ``suggestions``.

*Into the report.* When a document cannot be parsed, the problem is presented
to callers as a ``ValidationIssue`` rather than only as an exception:
``InpParseError.to_validation_issue()`` maps the parser's fields onto the
shared issue shape, with code ``E_PARSE_FAILED``, ``validation_layer`` set to
``"structural"``, ``rule_id="parse"``, ``ruleset_key="parser"`` and the line,
section, error code and suggestions preserved in ``context``. This is what
lets a malformed file and a model-level rule failure be reported side by
side. Passing ``--raise-on-error`` re-raises the ``InpParseError`` instead.

Layer 2: static
---------------

*When it runs.* After the ``WNTREPANETNetwork`` is built, with no simulator
involved. ``network.validate()`` delegates to the validation engine.

*What it checks.* Simulator-agnostic rules from the core rule set
(``epanet_core``) and from any custom rule sets the caller selects. Component
rules run collection by collection; network rules run afterwards against the
whole model with the name index available for resolving references. Rules
assert required fields, valid types and values, well-formed curves, unique
names, and references between components.

*Codes and metadata.* Every rule declares a stable ``code`` (generated from
the rule id when not given explicitly) and a ``category``. Severity follows
the function name — ``rule_*`` reports ``ERROR`` and ``warn_*`` reports
``WARNING``. Issues carry ``fix_suggestion``, the validated component's
``component_data``, and a ``context`` mapping that records the ruleset,
component subtype and any failing fields. A rule that raises anything other
than ``AssertionError`` is a defect in the rule and raises
``RuleExecutionError``; it is not a finding about the model. Static issues use
the ``ValidationIssue`` default, ``validation_layer="static"``.

Layer 3: simulation
-------------------

*When it runs.* After a hydraulic simulation, on the WNTR results object
rather than the model. The layer only runs when simulation validation is
requested, via the CLI or programmatically.

*What it checks.* Post-simulation output: pressures, flows, velocities,
headloss, demand and energy, plus the structure and dtypes of the result
tables. The built-in ``hydraulic`` rule set provides the reference rules.

*How rules are declared.* Rules use the
:func:`~epanetparser.core.validation.rules.simulation_rule` decorator and take
the simulation results as their single positional argument. The decorator
attaches a ``SimulationRuleSpec`` carrying the rule id, severity, stable
``code``, ``attribute``, ``category``, ``fix_suggestion`` and the
``required_outputs`` the rule needs (for example ``"node.pressure"``).
``Validator.validate_simulation(results, report)`` inspects the outputs the
simulator produced and skips any rule whose ``required_outputs`` are absent,
so a rule set stays meaningful across simulators with different output.

*Codes and metadata.* Simulation issues use the decorator's stable ``code``
and are tagged ``validation_layer="simulation"``. Their
``simulation_metadata`` records the rule's ``required_outputs``, and their
``context`` carries the rule's static context. The
``core_rules.core_dynamic.hydraulic.schemas`` helpers
(``validate_node_results``, ``validate_link_results``) additionally check
whole result tables against Pandera schemas, failing when a present field
has the wrong dtype or violates its check. The schemas are optional
(``epanetparser[schemas]``); without Pandera the schema checks are skipped
and a failure is reported as ``E_SIMULATION_SCHEMA`` only when they run.

Unified report
--------------

Every issue carries a ``validation_layer`` so that layered checks can be
combined, filtered, and reported together:

* :class:`~epanetparser.core.validation.results.ValidationIssue` has a
  ``validation_layer`` field (one of ``"structural"``, ``"static"``, or
  ``"simulation"``) and a ``simulation_metadata`` dictionary for
  post-simulation context. It also carries ``category``, ``fix_suggestion``,
  ``component_data`` and ``context``.
* :class:`~epanetparser.core.validation.results.ValidationReport` aggregates
  issues from every layer. Its ``schema_version`` defaults to ``"2.0"``, and
  its JSON serialisation includes the layer fields so downstream consumers can
  reproduce the layered result. Only ``Severity.ERROR`` makes a report
  invalid; warnings and informational issues do not.

CLI switches
------------

The ``validate`` command exposes one switch per layer combination:

.. code-block:: console

    # Static validation, then a simulation run and result validation
    $ epanetparser validate -f model.inp --simulate \
        --simulation-ruleset hydraulic

    # Only the simulation validation (skip static rules)
    $ epanetparser validate -f model.inp --simulation-only \
        --simulation-ruleset hydraulic

* ``--simulate`` runs the static rules first, then a hydraulic simulation,
  then the simulation rules. ``--simulation-only`` skips the static rules and
  runs only the simulation layer.
* ``--simulation-ruleset <key>`` selects the simulation rule sets and may be
  repeated (for example ``--simulation-ruleset hydraulic``).
* ``--raise-on-error`` changes how the structural layer reports: a parsing
  failure is re-raised as an exception (an ``InpParseError`` for an INP file)
  instead of becoming a ``ValidationIssue``.

See :doc:`usage` for the full flag reference.

Why three layers
----------------

The layers answer different questions and fail at different stages:

#. Can the file be read at all? (structural)
#. Is the model a sound EPANET model? (static)
#. Does the model behave acceptably under hydraulics? (simulation)

Separating them means a structurally valid model can be rejected by an
application rule set, and a statically valid model can still fail at
simulation time — without any of those outcomes contaminating the others.
Because all three converge into one ``ValidationReport``, a caller can still
present a single, layer-tagged result.
