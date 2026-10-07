.. |badge1| image:: https://github.com/tomjanus/epanetparser/workflows/CI/badge.svg
.. |badge2| image:: https://github.com/tomjanus/epanetparser/workflows/sphinx-docs-to-gh-pages/badge.svg

|badge1| |badge2|

.. image:: assets/banner.png
   :alt: Banner
   :width: 100%
   :align: center

EPANET Parser -- A toolkit for validating EPANET models
=======================================================

**EPANETParser** is a fork of **PywrParser** -- *"An experimental parser
for Pywr json network definitions"* developed by Dr. Paul Slavin from the University
of Manchester, UK. While `pywrparser` enables validation and manipulation of **Pywr** networks,
`epanetparser` is a modification of `pywrparser` that enables validation of **EPANET**
network models. The source code for `pywrparser
<https://github.com/pmslavin/pywrparser>`_ and its `documentation
<https://pmslavin.github.io/pywrparser/>`_ are maintained upstream by
Dr. Slavin.

The source code for `epanetparser <https://github.com/tomjanus/epanetparser>`_
and its `docs <https://tomjanus.github.io/epanetparser/>`_ are maintained
here.

`epanetparser` works on `JSON` representations of **EPANET** network models that use the
format/schema defined in `USEPA WNTR - The Water Network Tool for Resilience <https://github.com/USEPA/WNTR>`_
-- a Python package designed to simulate and analyze resilience of water distribution
networks. **WNTR** is a high-level Python wrapper that uses **EPANET** as a simulation engine
and extends it with additional functionalities. For more information on **WNTR**, please
refer to its documentation at http://wntr.readthedocs.io

Both WNTR `JSON` and native **EPANET** `INP` files are accepted. An `INP` file is converted
to the JSON representation before being parsed by `epanetparser`.

Installation
------------

Requires **Python 3.10 or later**. EPANETParser can be installed with either
`Poetry <https://python-poetry.org>`_ or ``pip``:

**Using Poetry:**

.. code-block:: console

    ❯ git clone git@github.com:tomjanus/epanetparser.git
    ❯ cd epanetparser
    ❯ poetry install

**Using pip:**

.. code-block:: console

    ❯ git clone git@github.com:tomjanus/epanetparser.git
    ❯ cd epanetparser
    ❯ pip install .

Quick start
-----------

Validate a model. Five example networks ship with the package, so there is
something to try this on immediately:

.. code-block:: console

    ❯ epanetparser validate -f Net1.inp
    File: Net1.inp
    Nodes: 11
    Links: 13
    Curves: 1
    Patterns: 1
    Controls: 2

They live in ``epanetparser/networks/core/``, and are reachable as
``epanetparser.networks.core.Net1.inp``.

A valid model produces a brief summary and exit status 0. An invalid one produces a
report of findings and exit status 2:

.. code-block:: console

    ❯ epanetparser validate -f tests/data/invalid_network.json --no-digest

    ─────────────────────────────────────── 1 ───────────────────────────────────────

      🔴  1 'E_CURVE_TYPE_UNSUPPORTED' -> Unsupported curve type None

    ─────────────────────────────────────────────────────────────────────────────────
    File: invalid_network.json
    Nodes: 785
    Links: 909
    Curves: 1
    Patterns: 3
    Controls: 2

    ❯ echo $?
    2

Every finding carries a stable code, such as ``E_CURVE_TYPE_UNSUPPORTED``, so downstream
tooling can match on it without depending on message text.

Or from Python, where parsing and validation are separate steps:

.. code-block:: python

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    from importlib.resources import files

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork

    model = files("epanetparser.networks.core") / "Net1.inp"
    network, errors, warnings = WNTREPANETNetwork.from_file(model)
    if network is None:
        raise SystemExit(f"Could not parse the model: {errors}")

    report = network.validate()
    for issue in report.errors:
        print(issue.code, issue.component_name, issue.message)

CLI usage
---------

The ``epanetparser`` command has four subcommands: ``validate``, ``convert``,
``info`` and ``download-extra``.

.. code-block:: console

    ❯ epanetparser -h
    usage: epanetparser [-h] [--version] {download-extra,validate,convert,info} ...

    Parser and validator of EPANET water distribution network models.

    options:
    -h, --help            show this help message and exit
    --version             Display the version of epanetparser

    available commands:
      download-extra       Download additional networks from GitHub release for
                          testing and benchmarking
      validate             Validate an EPANET model and display results
      convert              Convert between INP and JSON formats
      info                 Display information about the EPANET parser

    ❯ epanetparser validate -h
    usage: epanetparser validate [-h] -f <filename> [--ruleset <ruleset>]
                                 [--list-rulesets] [--raise-on-warning]
                                 [--ignore-warnings] [--raise-on-error]
                                 [--json-output] [--pretty-output] [--no-emoji]
                                 [--no-colour] [--terse-report] [--no-digest]

    Validation Options:
      --ruleset <ruleset>   Add a custom ruleset to the core ruleset. May be given
                            more than once to apply several, e.g. --ruleset milp
                            --ruleset project
      --list-rulesets       List the available rulesets and exit
      --raise-on-warning    Treat warnings as failures, so the exit status is
                            non-zero
      --ignore-warnings     Omit warnings from the report
      --raise-on-error      Raise a structural parsing problem as an exception
                            instead of reporting it

    Display Options:
      --json-output         Display parsing report in JSON format for machine
                            reading
      --pretty-output       Display parsing report on the console with colour
                            (default)
      --no-emoji            Omit emoji in console parsing reports
      --no-colour           Omit colour output in console parsing reports.
                            Implies --no-emoji
      --terse-report        Display only a terse report for valid networks
      --no-digest           Omit sha256 digest in JSON and dict parsing reports

The exit status says whether the model is usable, so the command composes with a
build:

.. code-block:: text

    0   the model parsed and validated with no errors
    1   bad usage: an unknown ruleset, or an unreadable file with --raise-on-error
    2   the model parsed but is invalid, or warned and --raise-on-warning was given

Converting between formats
--------------------------

The ``convert`` subcommand translates between `INP` and WNTR `JSON`. The direction
is inferred from the input extension, and the output filename is optional:

.. code-block:: console

    ❯ epanetparser convert Net1.inp Net1.json
    ✓ Converted INP to JSON: Net1.json

    ❯ epanetparser convert Net1.json roundtrip.inp
    ✓ Converted JSON to INP: roundtrip.inp

    ❯ epanetparser convert Net1.inp
    ✓ Converted INP to JSON: Net1.json

``--indent`` sets JSON indentation (default 2) and ``--epanet-version`` selects the
EPANET version targeted when writing `INP` (default 2.2):

.. code-block:: console

    ❯ epanetparser convert Net1.json Net1_2_0.inp --epanet-version 2.0

Downloading additional networks
-------------------------------

Additional benchmark networks are published as GitHub releases:

.. code-block:: console

    ❯ epanetparser download-extra --progress

Inspecting the rulesets
~~~~~~~~~~~~~~~~~~~~~~~

``epanetparser info --list-rulesets`` summarises what is available:

.. code-block:: console

    ❯ epanetparser info --list-rulesets
    Available rule sets:
      epanet_core (core) - EPANET core rules v1.0.0
          module: epanetparser.core_rules.epanet_core
          rules: 35 component, 9 network
          Simulator-agnostic checks that a model is a well-formed EPANET model.
      milp (custom) - Mixed Integer Linear Programming ruleset v0.2.0
          module: epanetparser.custom_rules.milp
          rules: 17 component, 0 network
          Constraints imposed by an example MILP optimal pump scheduling tool.

The ``epanetparser-plugins`` command shows more detail, and can discard the
discovery cache after a new rule set package is installed:

.. code-block:: console

    ❯ epanetparser-plugins list
    ❯ epanetparser-plugins show --ruleset milp
    ❯ epanetparser-plugins show --ruleset epanet_core --component WNTREPANETNode
    ❯ epanetparser-plugins refresh

Usage examples
--------------

A model that is well-formed but violates the MILP ruleset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same model passes the core ruleset and fails the custom one. That is the
distinction the architecture is built to express, and it is visible in the
report: the MILP findings are absent from the run without ``--ruleset``, and
every finding that does appear is attributed to the ``milp`` ruleset.

.. code-block:: console

    ❯ epanetparser validate -f tests/data/invalid_network_milp_ruleset.json --ruleset milp --no-digest

    ╭──────────────────────────────────────────────────────────────────────────────╮
    │ Results for 'invalid_network_milp_ruleset.json': 5 errors, 1 warning       │
    ╰──────────────────────────────────────────────────────────────────────────────╯
    ─────────────────────────────────── Network ────────────────────────────────────

      🔴  network 'E_MILP_TIMESTEP' -> Simulation timestep 7200 seconds not equal
      to MILOPS timestep 3600 seconds
      🟡  network 'W_MILP_INPFILE_UNITS' -> Units not in LPS. Units in INP file
      will be different than simulated: GPM
      🔴  network 'E_MILP_CONTROL' -> Controls not supported
      🔴  network 'E_MILP_CONTROL' -> Controls not supported

    ───────────────────────────────────── 112 ──────────────────────────────────────

      🔴  112 'E_MILP_CHECK_VALVE' -> Check valves not supported

    ───────────────────────────────────── 111 ──────────────────────────────────────

      🔴  111 'E_MILP_VALVE' -> Valve links not supported

    ─────────────────────────────────────────────────────────────────────────────────
    File: invalid_network_milp_ruleset.json
    Nodes: 11
    Links: 13
    Curves: 1
    Patterns: 1
    Controls: 2

    ❯ echo $?
    2

A model that passes the core ruleset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    ❯ epanetparser validate -f tests/data/valid_network.json --no-digest

    File: valid_network.json
    Nodes: 785
    Links: 909
    Curves: 1
    Patterns: 3
    Controls: 2

    ❯ echo $?
    0

Without a report, because there is nothing to report. The same model under the
MILP ruleset is rejected, since a 7 day simulation on a 5 minute timestep is
not what that formulation models.

A machine-readable report
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: console

    ❯ epanetparser validate -f tests/data/invalid_network.json --json-output --no-digest

    {
      "is_valid": false,
      "counts": {
        "ERROR": 2,
        "WARNING": 1,
        "INFO": 0
      },
      "issues": [
        {
          "code": "E_NETWORK_NAME_MISSING",
          "message": "Network missing a name",
          "severity": "ERROR",
          "rule_id": "rule_network_has_name",
          "ruleset_key": "epanet_core",
          "component_type": "WNTREPANETNetworkInfo",
          "component_name": null,
          "attribute": "name",
          "context": {
            "ruleset": "epanet_core",
            "component_subtype": "network_info"
          }
        },
        ...
      ]
    }


EPANETParser structure
----------------------

**EPANETParser** is built from the following components:

* ``WNTRJSONParser`` -- reads a WNTR JSON document and builds a model. It
  performs no validation; it reports only problems that make a model
  impossible to build, such as invalid JSON or a missing top-level section.
* ``WNTREPANETNetwork`` -- the model: the component collections, plus a
  name-to-component index for resolving references.
* ``WNTREPANETType`` and its subclasses -- one thin wrapper per component
  collection, holding a ``data`` dictionary and read-only accessors. They
  contain no rules and cannot be extended to add them.
* ``epanetparser.core.validation`` -- the validation engine: it selects rule
  sets, runs their rules, and returns structured results.
* ``epanetparser.core_rules`` and ``epanetparser.custom_rules`` -- the two rule
  set packages. They are searched by the same pass, and are distinguished only
  by the ``__is_core__`` attribute in their module metadata.

The pipeline is:

.. code-block:: text

    EPANET input
        |
        v
    Parser                    parsing and validation
        |
        v
    EPANET model
        |
        v
    Static validation         simulator-agnostic
        |
        v
    Simulator
        |
        v
    Simulation-specific validation

UML diagrams describing the core classes and their relationships are in
``docs/source/diagrams/``, and are rendered in the
`class hierarchy page <https://tomjanus.github.io/epanetparser/hierarchy.html>`_.

Validation architecture
~~~~~~~~~~~~~~~~~~~~~~~

A **rule set** is a module declaring ``__key__``, ``__ruleset_name__`` and
``__version__``, containing plain functions that ``assert``:

.. code-block:: python

    from epanetparser.core.validation import match, network_rule, rule

    __key__ = "my_project"
    __ruleset_name__ = "My project's rules"
    __version__ = "1.0.0"

    @rule("WNTREPANETLink", code="E_NO_CHECK_VALVES", attribute="check_valve")
    def rule_no_check_valves(link) -> None:
        """A check valve is not supported by our solver."""
        assert link.data.get("check_valve") in (False, None), "Check valves not supported"

    @rule("WNTREPANETNode", code="E_TANK_OVERFLOW", attribute="overflow")
    @match("Tank")
    def rule_no_tank_overflow(node) -> None:
        """Our solver models tanks as closed cylinders."""
        assert node.data.get("overflow") in (None, False), "Tank overflow not supported"

    @network_rule(code="E_UNKNOWN_CURVE", attribute="pump_curve_name")
    def rule_pump_curves_exist(network) -> None:
        """Every pump must reference a curve that exists."""
        for pump in network.links:
            curve = pump.data.get("pump_curve_name")
            assert not curve or curve in network.index.curves, "Unknown pump curve"

Drop the module into ``epanetparser/custom_rules/`` and it is discovered
automatically. Nothing else needs to change: no component class is imported, no
registry entry is written, and no base class is subclassed. A rule set
published as its own distribution can instead register through the
``epanetparser.rulesets`` entry point group.

**Exactly one** core rule set is selected per run; **any number** of custom rule
sets may be selected alongside it. The core rule set, ``epanet_core``, checks
that a model is a well-formed EPANET model: required component fields, valid
component types, well-formed curves, unique names, and references that
resolve. That is all it checks. It is simulator-agnostic, like a compiler's
static checks.

Constraints that belong to one application, such as the linearisation limits of
an MILP pump scheduling formulation, live in a custom rule set. That is the
distinction the architecture exists to express: a model can be a valid EPANET
model and still be unusable by a particular tool, and both statements can be
true of the same object at the same time.

Validation runs in three stages, and the order is what makes a report readable:

1. component-level rules run against every component, collection by collection;
2. network-level rules run against the model as a whole, with a name index
   available for resolving references;
3. each rule's ``AssertionError`` becomes a ``ValidationIssue`` carrying a
   stable ``code``, a severity, and the rule and rule set that produced it.

Only ``Severity.ERROR`` findings make a report invalid. Warnings inform without
blocking, which is the right default for a finding such as an input file
recorded in flow units other than the ones being simulated.

Python API
~~~~~~~~~~

.. code-block:: python

    from importlib.resources import files

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork
    from epanetparser.core.validation import Severity, ValidationContext, validate

    model = files("epanetparser.networks.core") / "Net1.inp"
    network, errors, warnings = WNTREPANETNetwork.from_file(model)
    if network is None:
        raise SystemExit(f"Could not parse the model: {errors}")

    # Core ruleset only.
    report = network.validate()
    assert report.is_valid, [issue.code for issue in report.errors]

    # Core ruleset plus an application ruleset.
    report = network.validate(["epanet_core", "milp"])

    for issue in report.errors:
        print(issue.code, issue.component_name, issue.message)

A single component can be validated on its own, with only the rules that apply
to it:

.. code-block:: python

    for node in network.nodes:
        for issue in node.validate().errors:
            print(issue.code, issue.component_name, issue.message)

The selection can be given as a key, a list of keys, a context, or a mapping,
so that a project can put the choice in one place:

.. code-block:: python

    context = ValidationContext(core="epanet_core", custom=["milp"])
    report = network.validate(context)

    # Equivalently:
    report = validate(network, context)

Any rule sets your project publishes are named here the same way. A key that is
not discovered raises ``RuleSetSelectionError`` rather than being ignored, so a
typo in a rule set name fails loudly instead of silently validating less than
you asked for.

Results
~~~~~~~

``validate()`` returns a ``ValidationReport``, never an exception for a rule
failure. A rule that raises anything other than ``AssertionError`` is a defect
in the rule, and raises ``RuleExecutionError`` instead of being reported as a
finding about the model.

.. code-block:: python

    report.is_valid            # False if any finding is Severity.ERROR
    report.errors              # the findings that block simulation
    report.warnings            # findings that inform without blocking
    report.by_code("E_UNKNOWN_CURVE_REFERENCE")
    report.by_component("T1")
    report.grouped_by_component()   # the shape display.write_results consumes
    report.as_dict()                # JSON-serialisable

An issue carries a stable code, so downstream tooling can match on it without
depending on message text:

.. code-block:: json

    {
      "code": "E_UNKNOWN_CURVE_REFERENCE",
      "message": "Links reference undefined curves: PU1 pump_curve_name <C9>",
      "severity": "ERROR",
      "rule_id": "rule_link_curves_exist",
      "ruleset_key": "epanet_core",
      "component_type": "network",
      "component_name": "Net1",
      "attribute": "pump_curve_name",
      "context": {"ruleset": "epanet_core"}
    }

Motivation
----------

The water community keeps building various tools either to extend **EPANET** capabilities
or as new tools that are made to work with **EPANET** or that use **EPANET** for simulating
water distribution networks (WDNs). Some examples include:

* `MAGNets <https://github.com/meghnathomas/MAGNets>`_ -- *A Python package to aggregate and reduce water distribution network models*
* `MILPNet <https://github.com/meghnathomas/MILPNet>`_ -- *Mixed-Integer Linear Programming framework for water distribution system optimization*

These tools may impose certain restrictions on the networks, e.g., a mixed-integer linear
optimizer for pump scheduling might impose certain restrictions on the network such as
absence of certain types of pumps or valves, etc., that are not supported by the linearization
scheme. In such cases, authors of a package can create a set of rules against which every
new network used in the tool can be validated. Those rules belong in a custom rule set, where
they apply to a model without redefining what a valid EPANET model is.

Applications
------------

`epanetparser` can be used as a custom network model validator that is specific to a tool
that is being developed which imposes restrictions on network models it can work with, e.g.,
topological restrictions, types of junctions, presence/absence of controls and rules, etc.

Additionally, `epanetparser` can be developed into a generic parser for any EPANET network model
that defines the universal requirements that any EPANET network needs to fulfill in order to run
without failures and/or output correct results.

Configuration
-------------

On first import, `epanetparser` writes a configuration file to a platform-specific
location, and merges your settings over the package defaults:

* Linux: ``~/.config/epanetparser/default_config.yaml``
* macOS: ``~/Library/Application Support/epanetparser/default_config.yaml``
* Windows: ``%APPDATA%\\epanetparser\\default_config.yaml``

Rule set search paths live under ``rule_set_discovery`` in that file, which is the
single source of truth. Add your own package under ``extra_packages``; the merge
substitutes lists rather than extending them, so ``packages`` replaces the
built-in list while ``extra_packages`` appends to it, and the built-in packages
are always searched first. The ``[tool.epanetparser]`` section of
``pyproject.toml`` is not read by the code.

Contributing
------------

Contributions are welcome. Please run the test suite before opening a pull request:

.. code-block:: console

    ❯ poetry install
    ❯ poetry run pytest

CI runs the suite on Python 3.10 through 3.13. The two commands most worth running
locally are the linters and the test suite:

.. code-block:: console

    ❯ poetry run pyflakes epanetparser tests
    ❯ poetry run flake8 epanetparser tests

Adding a validation rule requires no registry entry and no base class. Add a
function decorated with ``@rule`` or ``@network_rule`` to the relevant module in
``epanetparser/core_rules/epanet_core/``, and a test that fails without it.

Please report bugs and feature requests as
`GitHub issues <https://github.com/tomjanus/epanetparser/issues>`_.

License
-------

**No license file has been added to this repository yet.** That is a deliberate
gap rather than an oversight in the documentation: the licensing terms for
`epanetparser` have not been settled, and choosing them is a decision for the
maintainers rather than something to be guessed at in a README.

Until a license is added, the absence of one means the default copyright rules
apply and no permission to copy, modify or redistribute is granted. If you intend
to use this code, please open an issue asking which license applies.

Because ``epanetparser`` is a fork of ``pywrparser``, the upstream project's
terms also apply to the code inherited from it, and that project carries no
license file either. The upstream URL is
https://github.com/pmslavin/pywrparser.

Citation
--------

If you use `epanetparser` in academic work, please cite the project and the
tools it builds on:

.. code-block:: text

    epanetparser: a toolkit for parsing, validating and converting EPANET
    network models. https://github.com/tomjanus/epanetparser

    Slavin, P. pywrparser: a parser and validator for Pywr
    network definitions. https://github.com/pmslavin/pywrparser

    Wagner, J. et al. WNTR: A Python package to simulate and analyze resilience
    of water distribution networks. https://github.com/USEPA/WNTR

Acknowledgments
----------------

``epanetparser`` is a fork of ``pywrparser`` by Dr. Paul Slavin, and depends
on some of the code from `WNTR <https://github.com/USEPA/WNTR>`_ by the US EPA.
Thanks are due to the authors of both.
