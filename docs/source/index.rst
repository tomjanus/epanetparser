epanetparser documentation master file.

The epanetparser Documentation
==============================

`epanetparser` is a toolkit for parsing, validating and converting
`EPANET <https://github.com/USEPA/EPANET2.2>`_ water distribution network
models. It works with both EPANET INP (text) format and
`WNTR <https://usepa.github.io/WNTR/>`_ JSON format.

The toolkit consists of a command-line utility and a library, which together
allow `epanetparser` to be used directly and as a component of other projects.

Parsing and validation are separate steps. Parsing builds a model and reports
only structural problems. Validation runs afterwards against a chosen rule set
and returns a structured report, so a model can be a valid EPANET model and
still be rejected by an application-specific rule set.

The `epanetparser` source code is hosted
`on GitHub <https://github.com/tomjanus/epanetparser>`_.

.. toctree::
   :maxdepth: 2
   :caption: Introduction

   usage
   hierarchy

.. toctree::
   :maxdepth: 2
   :caption: Rules and Rulesets

   rules
   validation_categories

.. toctree::
   :maxdepth: 2
   :caption: The epanetparser library

   library

.. toctree::
   :maxdepth: 2
   :caption: Agentic AI Integration

   agentic
   toon_format
   mcp_server

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
