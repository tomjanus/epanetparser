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
             (parse-time, WNTR           (core + custom rule            (post-simulation,
              reader, errors in            sets, @rule /                 @simulation_rule,
              ValidationReport)            @network_rule)                Pandera schemas)
                          │                          │                          │
                          └──────────────────────────┼──────────────────────────┘
                                                     ▼
                                              ValidationReport
                                          (layered issues, 1.0 / 2.0 dicts)
                                                     │
                                          to_wntr() → WNTR WaterNetworkModel
                                  ──▶  simulator.run_sim() ──▶  results
                                                     │
                                          validate_simulation(results, report)

The pipeline keeps parsing, validation, and simulation as separate, explicitly
linked steps. Parsing builds a model and reports only structural problems.
Validation runs afterwards against a chosen rule set and returns a structured
``ValidationReport``. Simulation runs only on demand and produces its own
post-simulation validation layer.

Modules
-------

======================  =====================================================
Module                  Responsibility
======================  =====================================================
``core.io``             Vendored WNTR 1.4.0 parsing/serialisation code plus
                        the standalone INP parser. See :doc:`parser`.
``core.parsers``        WNTR JSON parser (structural only).
``core.epanettypes``    ``WNTREPANETNetwork`` and component wrappers with
                        read-only accessors over the parsed dictionaries.
``core.lib``            INP ↔ JSON conversion.
``core.validation``     Rule metadata, discovery, registry, engine, and the
                        ``ValidationReport``/``ValidationIssue`` types.
``core_rules``          Simulator-agnostic core rule sets (e.g. ``epanet_core``).
``custom_rules``        Application rule sets, including the simulation
                        ruleset (``hydraulic``) and its Pandera schemas.
``core.parse``          The ``epanetparser`` command-line interface.
======================  =====================================================

Key design decisions
--------------------

* **Parsing without WNTR.** The INP reading code is a self-contained,
  trimmed extraction of WNTR 1.4.0. WNTR is only required as an optional
  extra for hydraulic simulation.
* **Three validation layers.** Structural, static, and simulated results
  converge into a single ``ValidationReport`` so consumers see one unified
  result. See :doc:`validation_layers`.
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