Architecture
============

``epanetparser`` is organised around a single pipeline that turns an EPANET
model file into a validated in-memory model, and — optionally — feeds that
model through a hydraulic simulator whose outputs are validated in turn.

Pipeline
--------

::

    EPANET INP file  ──▶  INP parser  ──▶  ``dict`` (SI, WNTR schema)
                                                     │
    EPANET JSON file ──▶  WNTR JSON parser ──▶  ─────┤
                                                     ▼
                                          WNTREPANETNetwork
                                                     │
                          ┌──────────────────────────┼──────────────────────────┐
                          │                          │                          │
                    structural                    static                    simulation
                   validation                  validation                 validation
              (parse-time; InpParseError    (core + custom rule          (post-simulation;
               subclasses become             sets, @rule /                @simulation_rule,
               layer-tagged issues)          @network_rule)               Pandera schemas)
                          │                          │                          │
                          └──────────────────────────┼──────────────────────────┘
                                                     ▼
                                              ValidationReport
                                        (layered issues, schema_version "2.0")
                                                     │
                                          to_wntr() → WNTR WaterNetworkModel
                                  ──▶  simulator.run_sim() ──▶  results
                                                     │
                                          validate_simulation(results, report)

The pipeline keeps parsing, validation, and simulation as separate, explicitly
linked steps. Parsing builds a model and reports only structural problems,
raised as ``InpParseError`` subclasses and presented as
``validation_layer="structural"`` issues. Static validation runs afterwards
against a chosen rule set and returns a structured ``ValidationReport``.
Simulation runs only on demand and produces its own post-simulation validation
layer. All three layers append to one report; the class-level view is in
:doc:`hierarchy` and the layer-by-layer detail, including the error taxonomies
and CLI switches, is in :doc:`validation_layers`.

Modules
-------

======================  =====================================================
Module                  Responsibility
======================  =====================================================
``core.io``             Vendored WNTR 1.4.0 parsing/serialisation code plus
                        the standalone INP parser. See :doc:`parser`.
``core.io.inp_errors``  Structured ``InpParseError`` subclasses, the EPANET
                        code map and their ``ValidationIssue`` mapping.
``core.parsers``        WNTR JSON parser (structural only).
``core.epanettypes``    ``WNTREPANETNetwork`` and component wrappers with
                        read-only accessors over the parsed dictionaries.
``core.lib``            INP ↔ JSON conversion.
``core.validation``     Rule metadata, discovery, registry, engine, and the
                        ``ValidationReport``/``ValidationIssue`` types.
``core_rules``          Core rule sets by layer: ``core_static`` holds the
                        simulator-agnostic ``epanet_core`` rule set;
                        ``core_dynamic`` holds the ``hydraulic`` simulation
                        rule set with its Pandera schemas.
``custom_rules``        Application rule sets (e.g. ``milp``), which may mix
                        static and simulation rules in one module.
``core.parse``          The ``epanetparser`` command-line interface.
======================  =====================================================

Key design decisions
--------------------

* **Parsing without WNTR.** The INP reading code is a self-contained,
  trimmed extraction of WNTR 1.4.0. WNTR is only required as an optional
  extra for hydraulic simulation.
* **Three validation layers.** Structural, static, and simulated results
  converge into a single ``ValidationReport`` so consumers see one unified
  result. Structural failures use the ``InpParseError`` tree, static rules use
  ``@rule``/``@network_rule``, and simulation rules use ``@simulation_rule``.
  See :doc:`validation_layers` and :doc:`hierarchy`.
* **Dict serialisation is canonical.** Both parsers produce plain Python
  dictionaries in the WNTR SI schema; the network wrappers are read-only views
  over those dictionaries. See :doc:`parser`.
* **Simulation validation is opt-in.** ``@simulation_rule`` rules run only
  when simulation is requested, and are skipped when the required outputs are
  not present. See :doc:`simulation_validation`.

Diagrams
--------

The class hierarchy, model layer, validation engine, and rule-set layout are
rendered in :doc:`hierarchy`.