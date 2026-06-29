.. |badge1| image:: https://github.com/tomjanus/epanetparser/workflows/CI/badge.svg
.. |badge2| image:: https://github.com/tomjanus/epanetparser/workflows/sphinx-docs-to-gh-pages/badge.svg

|badge1| |badge2|

.. image:: assets/banner.png
   :alt: Banner
   :width: 100%
   :align: center

EPANET Parser -- A toolkit for validating EPANET models
=======================================================

**🚧 Active Development Notice**

**EPANETParser** is currently under active development. While the core functionality 
is operational, some features are still being refined and documentation is being 
updated. The tool is usable for:

* Validating EPANET network models in INP or WNTR JSON formats
* Converting between INP and JSON formats
* Applying custom validation rulesets

Please report any issues or suggestions at https://github.com/tomjanus/epanetparser/issues

Expected stable release: Coming soon!

----

**EPANETParser** is a fork of **PywrParser** -- *"An experimental parser 
for Pywr json network definitions"* developed by Dr. Paul Slavin from the University 
of Manchester, UK. While `pywrparser` enables validation and manipulation of **Pywr** networks,
`epanetparser` is a modification of `pywrparser` that enables validation of **EPANET** 
network models. The source code for `pywrparser` is available at 
https://github.com/pmslavin/pywrparser whereas its documentation can be found at 
https://pmslavin.github.io/pywrparser/. 

The source code for `epanetparser` is available at https://github.com/tomjanus/epanetparser. 
The documentation is located at https://tomjanus.github.io/epanetparser/. 

What does EPANETParser take from PywrParser and what is new?
------------------------------------------------------------

The structure of the package remains largely the same as **PywrParser**, with modifications
specific to **EPANET** network models and auto-discovery and registration of core rules and custom 
rulesets. The core parsing and validation framework has been adapted to work with EPANET-specific
components and their associated validation rules.

The errors and warning display mechanisms are the same as in **PywrParser** but due to adopting a
new ruleset discovery and registration mechanism, the rules are now displayed in a more structured
and organized manner. The rules are now grouped by the component type they apply to, making it
easier to understand which rules are relevant to which components of the network model.
The rule descriptions are separate from ruleset descriptions and follow a hierarchy of how they
are applied in practice. The rules are applied first to the network components followed by ruleset-specific
rules and warnings. Effectively, rulesets are treated as additional rules that are applied after 
the core rules have been validated. 
This allows validating networks for user-specific purposes, where additional restrictions need to be 
imposed on the network components and the network as a whole, whilst core rules enforce network constraints
that are universal and applicable to all networks.

EPANETParser Structure
----------------------

**EPANETParser** is built upon the following core components:

* `WNTRJSONParser`: The main parser class that orchestrates the parsing and validation of EPANET network models in WNTR JSON format.
* `WNTREPANETType`: The base class for all EPANET network components, such as nodes, links, patterns, controls, etc. It provides common functionality for validation and rule management.
* `WNTREPANETTypeValidator`: A descriptor class that handles the validation of individual attributes of EPANET network components. It allows for the definition of validation rules and their application to specific attributes.
* `WNTREPANETTypeValidationErrorBundle`: A class that collects and manages validation errors and warnings encountered during the parsing process. It provides a structured way to report issues found during validation.

The UML diagram describing the core EPANETParser classes and their relationships can be found in the `docs/epanetparser_class_hierarchy.puml` file. 
This diagram provides a visual representation of the class hierarchy and the interactions between the different components of the parser.

The core logic behind the parsing and validation process is implemented in the `epanetparser/core/validation.py` file. 
This file contains the main validation logic, including the application of rules and the collection of errors and warnings.

The validation mechanism relies on and leverages the descriptor protocol, which allows for the definition 
of validation rules as methods on the `WNTREPANETType` classes. The descriptor implemented in `WNTREPANETTypeValidator` 
is used for the discovery of rule and warning methods and their application to the attributes of the EPANET network components
upon assigning each network component to the `WNTRJSONParser`. 
The validation process is initiated by calling the `validate()` method on the `WNTRJSONParser` instance, 
which triggers the validation of all network components and their associated rules.

Validation Architecture
~~~~~~~~~~~~~~~~~~~~~~~

Each base **component** and the whole **network** (container of components) - all of which are defined in `epanetparser.core.epanettypes` - can be associated with validation rules and warnings which are defined in three separate places:

* base class definitions
* core rule definitions managed in rule registry
* rulesets autodiscovered by the rulesets module

During validation the following steps are carried out in this order:

1. Collect all warnings and rules for all network components, i.e. from base class definitions, rule registry, and rulesets.
2. Check for any conflicts and repeated rule definitions. If there exist any conflicts, preserve only those rules and warnings with the highest priority. Priority is set as follows (in order of decreasing priority): base class definitions → core rule definitions → rulesets. I.e., a rule from a ruleset cannot overwrite a core rule.
3. Execute instance rules (from base class)
4. Execute plugin rules (from registry)
5. Execute ruleset rules (from active ruleset subclass)

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
new network used in the tool can be validated.

Quick Description
-----------------

`epanetparser` works on `JSON` representations of the **EPANET** network models that use
the format/schema defined in `USEPA WNTR - The Water Network Tool for Resilience <https://github.com/USEPA/WNTR>`_ -- a Python package designed to simulate and analyze resilience of water distribution networks. **WNTR** is a high-level Python wrapper that uses **EPANET** as a simulation engine and extends it with additional functionalities. For more information on **WNTR**, please refer to its documentation at http://wntr.readthedocs.io

As in **PywrParser**, each category of the **EPANET** model building blocks such 
as *nodes*, *links*, *patterns*, *controls*, etc., are parsed and validated against 
pre-defined sets of rules. Depending on the configuration, the parser raises an error 
upon violating one of the rules or continues and collects all rule violations before issuing 
a final report. In addition to rules, warnings are issued on the **passing** network components, 
i.e., on the network components that do not violate any rules but also don't meet some of the 
non-essential criteria. The purpose of warnings is to inform the user about potential issues that 
may arise in the future, such as future compatibility issues, or to provide additional information 
and explanation about the behaviour of certain components that might be difficult to pick up from 
source code and documentation. 

Rules, i.e., `rule_` and `warn_` validation methods for each component can be added or updated 
using `rulesets`. A ruleset is a set of rules that is specific to a certain model application. 
For example, in case of a hypothetical test ruleset called `test1.0`, the use of check valves is 
prohibited. This restriction could be applied within a package that does not allow check valves, 
e.g., due to certain limitations of the computational engine.

Plugins vs Rulesets
-------------------

**When to use Plugins:**

* Universal validation that applies to ALL EPANET models
* Shared standards across projects
* External package providing validation

**When to use Rulesets:**

* Domain-specific constraints (pump scheduling, leakage detection method, etc. that do not work on all generic networks)
* Switchable validation contexts
* Temporary/experimental rules

Applications
------------

`epanetparser` can be used as a custom network model validator that is specific to a tool
that is being developed which imposes restrictions on network models it can work with, e.g.,
topological restrictions, types of junctions, presence/absence of controls and rules, etc.

Additionally, `epanetparser` can be developed into a generic parser for any EPANET network model
that defines the universal requirements that any EPANET network needs to fulfill in order to run
without failures and/or output correct results.

Installation
------------

EPANETParser can be installed with either `Poetry <https://python-poetry.org>`_ or ``pip``:

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

CLI Usage
---------

The ``epanetparser`` usage can be displayed with:

.. code-block:: console

    ❯ epanetparser -h
    usage: epanetparser [-f <filename> | -l] [OPTIONS]

    Validator of EPANET models in WNTR JSON format prior to conversion to a mixed integer linear programme.

    options:
    -h, --help            show this help message and exit
    -f <filename>, --filename <filename>
                            File containing a EPANET model in WNTR JSON format
    -l, --list-rulesets   Display a list of all available rulesets

    validation options:
    --use-ruleset <ruleset>
                            Apply the specified ruleset during parsing
    --raise-on-warning    Raise failures of parsing warnings as exceptions. Implies `--raise-on-error`
    --raise-on-error      Raise failures of parsing rules as exceptions
    --ignore-warnings     Do not display parsing report if only warnings are present

    display options:
    --json-output         Display parsing report in json format for machine reading
    --pretty-output       Display parsing report on the console with colour. This is the default output format
    --no-emoji            Omit emoji in console parsing reports
    --no-colour           Omit colour output in console parsing reports. Implies `--no-emoji`
    --terse-report        Display only a terse report for valid networks

    general options:
    --no-digest           Omit sha256 digest in JSON and dict parsing reports
    --version             Display the version of epanetparser

    The tool is an adaptation of the toolkit for parsing and validating Pywr models written by Paul Slavin, https://github.com/pmslavin/pywrparser,
    https://pmslavin.github.io/pywrparser


Usage Examples
--------------

Invalid network with ``strict`` **milops10** ruleset (failed run)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    ❯ epanetparser -f ../../../models/epanetparser_test_models/invalid_network.inp --use-ruleset test10

    ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
    │ This is epanetparser - a parser for EPANET network models based on pywrparser: `A parser for Pywr json network definitions` by Paul Slavin. It works with  │
    │ JSON representations of EPANET models adhering to the JSON format specified by WNTR - `A Python package designed to simulate and analyze resilience of     │
    │ water distribution networks.`                                                                                                                              │
    ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

                             ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────╮                          
                             │ Parser results for '../../../models/epanetparser_test_models/invalid_network.inp': 6 errors, 0 warnings │                          
                             ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯                          

    ────────────────────────────────────────────────────────────────────────── Options ───────────────────────────────────────────────────────────────────────────

      🔴  MILOPS_1_0_Options 'rule_hydraulic_timestep' -> Simulation timestep 7200 seconds not equal to MILOPS timestep 3600 seconds                              
                {"time": {"duration": 936400.0, "hydraulic_timestep": 7200, "quality_timestep": 300, "rule_timestep": 360, "pattern_timestep": 7200,              
                "pattern_start": 0.0, "report_timestep": 3600, "report_start": 0.0, "start_clocktime": 0.0, "statistic": "NONE",                                  
                "pattern_interpolation": false}, "hydraulic": {"headloss": "H-W", "hydraulics": null, "hydraulics_filename": null, "viscosity": 1.0,              
                "specific_gravity": 1...[+1647 chars]                                                                                                             
      🔴  MILOPS_1_0_Options 'rule_simulation_time_horizon' -> Simulation time horizon 936400.0 seconds not equal to schedule time horizon 86400 seconds          
                {"time": {"duration": 936400.0, "hydraulic_timestep": 7200, "quality_timestep": 300, "rule_timestep": 360, "pattern_timestep": 7200,              
                "pattern_start": 0.0, "report_timestep": 3600, "report_start": 0.0, "start_clocktime": 0.0, "statistic": "NONE",                                  
                "pattern_interpolation": false}, "hydraulic": {"headloss": "H-W", "hydraulics": null, "hydraulics_filename": null, "viscosity": 1.0,              
                "specific_gravity": 1...[+1647 chars]                                                                                                             

    ─────────────────────────────────────────────────────────────────────────── Links ────────────────────────────────────────────────────────────────────────────

      🔴  MILOPS_1_0_Links 'rule_check_valves' -> Check valves not supported                                                                                      
                {"name": "112", "link_type": "Pipe", "start_node_name": "12", "end_node_name": "22", "bulk_coeff": null, "check_valve": true,                     
                "diameter": 0.30479999999999996, "initial_setting": null, "initial_status": "Open", "length": 1609.344, "minor_loss": 0.0,                        
                "roughness": 100.0, "tag": null, "vertices": [], "wall_coeff": null}                                                                              
      🔴  MILOPS_1_0_Links 'rule_no_valves_allowed' -> Valve links not supported                                                                                  
                {"name": "111", "link_type": "Valve", "start_node_name": "11", "end_node_name": "21", "valve_type": "PRV", "diameter":                            
                0.19999999999919998, "initial_setting": 39.99999999974152, "initial_status": "Active", "minor_loss": 0.0, "tag": null, "vertices": []}            

    ────────────────────────────────────────────────────────────────────────── Controls ──────────────────────────────────────────────────────────────────────────

      🔴  MILOPS_1_0_Control 'rule_no_controls_allowed' -> Controls not supported                                                                                 
                {"type": "simple", "condition": "TANK 2 LEVEL BELOW 33.528", "then_actions": ["PUMP 9 STATUS IS OPEN"]}                                           
      🔴  MILOPS_1_0_Control 'rule_no_controls_allowed' -> Controls not supported                                                                                 
                {"type": "simple", "condition": "TANK 2 LEVEL ABOVE 42.672000000000004", "then_actions": ["PUMP 9 STATUS IS CLOSED"]}                             

    ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Invalid network without ``strict`` ruleset (failed run)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    ❯ epanetparser -f ../../../models/epanetparser_test_models/invalid_network.inp

    ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
    │ This is epanetparser - a parser for EPANET network models based on pywrparser: `A parser for Pywr json network definitions` by Paul Slavin. It works with  │
    │ JSON representations of EPANET models adhering to the JSON format specified by WNTR - `A Python package designed to simulate and analyze resilience of     │
    │ water distribution networks.`                                                                                                                              │
    ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

                             ╭─────────────────────────────────────────────────────────────────────────────────────────────────────────╮                          
                             │ Parser results for '../../../models/epanetparser_test_models/invalid_network.inp': 3 errors, 0 warnings │                          
                             ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────╯                          

    ────────────────────────────────────────────────────────────────────────── Options ───────────────────────────────────────────────────────────────────────────

      🔴  WNTREPANETOptions 'rule_hydraulic_timestep' -> Simulation timestep 7200 seconds not equal to MILOPS timestep 3600 seconds                               
                {"time": {"duration": 936400.0, "hydraulic_timestep": 7200, "quality_timestep": 300, "rule_timestep": 360, "pattern_timestep": 7200,              
                "pattern_start": 0.0, "report_timestep": 3600, "report_start": 0.0, "start_clocktime": 0.0, "statistic": "NONE",                                  
                "pattern_interpolation": false}, "hydraulic": {"headloss": "H-W", "hydraulics": null, "hydraulics_filename": null, "viscosity": 1.0,              
                "specific_gravity": 1...[+1647 chars]                                                                                                             

    ────────────────────────────────────────────────────────────────────────── Controls ──────────────────────────────────────────────────────────────────────────

      🔴  WNTREPANETControl 'rule_no_controls_allowed' -> Controls not supported                                                                                  
                {"type": "simple", "condition": "TANK 2 LEVEL BELOW 33.528", "then_actions": ["PUMP 9 STATUS IS OPEN"]}                                           
      🔴  WNTREPANETControl 'rule_no_controls_allowed' -> Controls not supported                                                                                  
                {"type": "simple", "condition": "TANK 2 LEVEL ABOVE 42.672000000000004", "then_actions": ["PUMP 9 STATUS IS CLOSED"]}                             

    ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Valid network without any rule violations (success)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    ❯ epanetparser -f ../../../models/epanetparser_test_models/valid_network.inp --use-ruleset milops10

    ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
    │ This is epanetparser - a parser for EPANET network models based on pywrparser: `A parser for Pywr json network definitions` by Paul Slavin. It works with  │
    │ JSON representations of EPANET models adhering to the JSON format specified by WNTR - `A Python package designed to simulate and analyze resilience of     │
    │ water distribution networks.`                                                                                                                              │
    ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

                               ╭──────────────────────────────────────────────────────────────────────────────────────────────────────╮                           
                               │ Parser results for '../../../models/epanetparser_test_models/valid_network.inp': 0 errors, 1 warning │                           
                               ╰──────────────────────────────────────────────────────────────────────────────────────────────────────╯                           

    ────────────────────────────────────────────────────────────────────────── Options ───────────────────────────────────────────────────────────────────────────

      🟡  MILOPS_1_0_Options 'warn_inpfile_units' -> Units not in litres per second. Units in INP file will be different than simulated                           
                {"time": {"duration": 86400.0, "hydraulic_timestep": 3600, "quality_timestep": 300, "rule_timestep": 360, "pattern_timestep": 7200,               
                "pattern_start": 0.0, "report_timestep": 3600, "report_start": 0.0, "start_clocktime": 0.0, "statistic": "NONE",                                  
                "pattern_interpolation": false}, "hydraulic": {"headloss": "H-W", "hydraulics": null, "hydraulics_filename": null, "viscosity": 1.0,              
                "specific_gravity": 1....[+1646 chars]                                                                                                            

    ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    File: valid_network.inp
    sha256: ac05b0412f7f70e5ae10c18fbe3f1daeca880906a0b78067f3fb5c8a6e875bf2
    Nodes: 11
    Links: 13
    Curves: 1
    Patterns: 1

