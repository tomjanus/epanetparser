Basic Usage
===========

Overview
--------

``epanetparser`` provides a command-line utility for validating EPANET models,
and a Python library which may be used to parse and validate EPANET networks.

This section covers the command-line utility. Use of the library is described in
the :doc:`library` section, and the rule set mechanism in :doc:`rules`.

Installation
============

``epanetparser`` requires Python 3.10 or later, and can be installed with either
`Poetry <https://python-poetry.org>`_ or ``pip``:

.. code-block:: console

    $ git clone git@github.com:tomjanus/epanetparser.git
    $ cd epanetparser
    $ poetry install

Or using ``pip``:

.. code-block:: console

    $ git clone git@github.com:tomjanus/epanetparser.git
    $ cd epanetparser
    $ pip install .

To display the usage guide:

.. code-block:: console

    $ epanetparser -h
    Usage: epanetparser [-h] [--version] ...

    Parser and validator of EPANET water distribution network models.

    Options:
      -h, --help      show this help message and exit
      --version       Display the version of epanetparser

    Available Commands:

        download-extra
                      Download additional networks from GitHub release for testing
                      and benchmarking
        validate      Validate an EPANET model and display results
        convert       Convert between EPANET's native INP format and WNTR JSON
                      format
        info          Display information about the EPANET parser

For further information, please visit https://tomjanus.github.io/epanetparser

Validation
----------

The basic operation of the ``epanetparser validate`` command validates an EPANET
model and returns either:

* A report describing a valid model, along with any warnings raised during
  validation
* A report detailing the errors that made the model invalid
* An exception, if the input could not be parsed at all

.. code-block:: console

    $ epanetparser validate --help
    Usage: epanetparser validate [-h] -f <filename> [--ruleset <ruleset>]
                                 [--list-rulesets] [--raise-on-warning]
                                 [--ignore-warnings] [--raise-on-error]
                                 [--json-output] [--pretty-output] [--no-emoji]
                                 [--no-colour] [--terse-report] [--no-digest]

    Options:
      -h, --help            show this help message and exit
      -f, --filename <filename>
                            File containing an EPANET model in INP or WNTR JSON
                            format

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
      --no-colour           Omit colour output in console parsing reports. Implies
                            --no-emoji
      --terse-report        Display only a terse report for valid networks
      --no-digest           Omit sha256 digest in JSON and dict parsing reports

Both INP and WNTR JSON files are accepted. An ``.inp`` file is converted to
WNTR's JSON representation with WNTR before being parsed.

An invalid model produces a report categorised by component, with each finding
carrying a stable code:

.. code-block:: console

    $ epanetparser validate -f invalid_network.json --no-digest

    ─────────────────────────────────────── 1 ───────────────────────────────────────

      🔴  1 'E_CURVE_TYPE_UNSUPPORTED' -> Unsupported curve type None

    ─────────────────────────────────────────────────────────────────────────────────
    File: invalid_network.json
    Nodes: 785
    Links: 909
    Curves: 1
    Patterns: 3
    Controls: 2

The code, rather than the message text, is the stable identifier, so downstream
tooling can match on it without depending on wording.

This report may be customised with the various configuration options described
in the `Display Options` section of the output from ``epanetparser validate -h``.

A *valid* model is one for which no error is raised. Warnings inform without
blocking. Validating a valid model results in a brief summary of the model, and
nothing more:

.. code-block:: console

    $ epanetparser validate -f valid_network.json --no-digest
    File: valid_network.json
    Nodes: 785
    Links: 909
    Curves: 1
    Patterns: 3
    Controls: 2

The ``--no-digest`` option causes the report to omit calculation and display of
the SHA256 digest, which may improve performance for large files on slow systems.

The ``--terse-report`` option causes only a summary of the numbers of each
component defined in the model to be displayed:

.. code-block:: console

    $ epanetparser validate -f valid_network.json --terse-report
    {'nodes': 785, 'links': 909, 'curves': 1, 'patterns': 3, 'controls': 2}

This is useful where the output is intended to be consumed by an automated
process.

The ``--json-output`` option provides the full report as JSON, for machine
reading. The top level carries validity, per-severity counts, and the issues
themselves:

.. code-block:: console

    $ epanetparser validate -f invalid_network.json --json-output --no-digest
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

Exit status
-----------

The exit status says whether the model is usable, so the command composes with a
build or a test:

.. code-block:: text

    0   the model parsed and validated with no errors
    1   bad usage: an unknown ruleset, or an unreadable file with --raise-on-error
    2   the model parsed but is invalid, or warned and --raise-on-warning was given

.. code-block:: console

    $ epanetparser validate -f invalid_network.json --no-digest
    $ echo $?
    2

Selecting a rule set
--------------------

Exactly one core rule set is applied to every run. Custom rule sets are added
with ``--ruleset``, which may be given more than once:

.. code-block:: console

    $ epanetparser validate -f model.json --ruleset milp --ruleset project

To see what is available:

.. code-block:: console

    $ epanetparser info --list-rulesets
    Available rule sets:
      epanet_core (core) - EPANET core rules v1.0.0
          module: epanetparser.core_rules.epanet_core
          rules: 35 component, 9 network
          Simulator-agnostic checks that a model is a well-formed EPANET model:
          required component fields, valid component types, well-formed curves,
          unique component names, and resolvable references between components.
      milp (custom) - Mixed Integer Linear Programming ruleset v0.2.0
          module: epanetparser.custom_rules.milp
          rules: 17 component, 0 network
          Constraints imposed by an example MILP optimal pump scheduling tool.

Adding a custom rule set is how an application imposes its own restrictions on a
model. See :doc:`rules` for the mechanism.

Converting between formats
--------------------------

The ``convert`` subcommand translates between EPANET's native INP format and
WNTR's JSON format. The direction is inferred from the input extension:

.. code-block:: console

    $ epanetparser convert Net1.inp Net1.json
    ✓ Converted INP to JSON: Net1.json

    $ epanetparser convert Net1.json roundtrip.inp
    ✓ Converted JSON to INP: roundtrip.inp

The output filename is optional. Omitted, the input name is reused with the
extension swapped:

.. code-block:: console

    $ epanetparser convert Net1.inp
    ✓ Converted INP to JSON: Net1.json

Two options control the output. ``--indent`` sets JSON indentation, defaulting
to 2 spaces. ``--epanet-version`` selects the EPANET version targeted when
writing INP, defaulting to 2.2:

.. code-block:: console

    $ epanetparser convert Net1.inp Net1.json --indent 4
    $ epanetparser convert Net1.json Net1.inp --epanet-version 2.0

Downloading additional networks
-------------------------------

Additional benchmark networks are published as GitHub releases and can be
fetched for testing:

.. code-block:: console

    $ epanetparser download-extra --progress

Inspecting rule sets
--------------------

The ``epanetparser-plugins`` command inspects the discovered rule sets in more
detail than ``info --list-rulesets`` provides:

.. code-block:: console

    $ epanetparser-plugins list
    $ epanetparser-plugins show --ruleset milp
    $ epanetparser-plugins show --ruleset epanet_core --component WNTREPANETNode

Discovery is cached. After installing a new rule set package, discard the cache
so it is rescanned:

.. code-block:: console

    $ epanetparser-plugins refresh

Configuration
-------------

On first import, ``epanetparser`` writes a configuration file to a
platform-specific location:

* Linux: ``~/.config/epanetparser/default_config.yaml``
* macOS: ``~/Library/Application Support/epanetparser/default_config.yaml``
* Windows: ``%APPDATA%\\epanetparser\\default_config.yaml``

Your settings are merged with the package defaults, with yours taking
precedence. The rule set search paths live under ``rule_set_discovery``, and
this file, not ``pyproject.toml``, is the single source of truth for them:

.. code-block:: yaml

    rule_set_discovery:
      packages:
        - epanetparser.core_rules
        - epanetparser.custom_rules
