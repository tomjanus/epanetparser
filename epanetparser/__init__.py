"""EPANET Parser - A toolkit for EPANET network models.

epanetparser is a Python library for parsing, validating and converting EPANET
water distribution network models. It works with both EPANET INP (text) format
and WNTR JSON format, with a simulator-agnostic validation framework and a
ruleset registry for application-specific constraints.

Key Features
------------
- Parse EPANET networks from INP or WNTR JSON formats
- Simulator-agnostic static validation returning a structured report
- Any number of application rulesets, added without touching the model
- Bidirectional format conversion (INP ↔ JSON)
- Rich CLI with detailed error reporting and meaningful exit status
- Platform-independent configuration management

Quick Start
-----------
>>> from epanetparser.core.epanettypes.network import WNTREPANETNetwork
>>> from epanetparser.core.validation import validate
>>> network, errors, warnings = WNTREPANETNetwork.from_file("Net1.inp")
>>> report = validate(network)
>>> report.is_valid
True
>>> for issue in report.errors:
...     print(issue.code, issue.component_name, issue.message)

Parsing and validation are separate steps. Parsing builds a model and reports
only structural problems; validation is called explicitly and returns a report.

Configuration
-------------
epanetparser reads an optional user configuration file from your
platform-specific config directory:

- Linux: ~/.config/epanetparser/default_config.yaml
- macOS: ~/Library/Application Support/epanetparser/default_config.yaml
- Windows: %APPDATA%\\epanetparser\\default_config.yaml

The file is not created for you. If it does not exist, or is empty, the package
defaults are used unchanged. Create it to customise settings, setting only the
keys you want to change: your settings are merged with the package defaults,
with yours taking precedence. The rule set search paths live here, under
``rule_set_discovery``; list your own package under ``extra_packages``, which
appends, whereas ``packages`` replaces the built-in list.

Command-Line Interface
----------------------
epanetparser provides two commands:

1. `epanetparser` - Parse, validate and convert EPANET models
   $ epanetparser validate -f network.json
   $ epanetparser validate -f network.inp --ruleset milp
   $ epanetparser convert network.inp network.json
   $ epanetparser info --list-rulesets

2. `epanetparser-plugins` - Inspect the available rulesets
   $ epanetparser-plugins list
   $ epanetparser-plugins show --ruleset milp

Exit status is meaningful: 0 for a valid model, 1 for bad usage, 2 for an
invalid model.

See Also
--------
- Documentation: https://epanetparser.readthedocs.io/
- GitHub: https://github.com/tomjanus/epanetparser
- WNTR: https://usepa.github.io/WNTR/
"""

# Perform automatic initialization
from epanetparser.core.init import initialize

initialize()

# Package metadata
__version__ = "0.1.0"
__author__ = "Paul Slavin, Tomasz Janus"

__all__ = [
    "initialize",
    "__version__",
    "__author__",
]
