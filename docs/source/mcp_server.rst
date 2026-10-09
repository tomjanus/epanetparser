MCP Server Reference
====================

The epanetparser MCP (Model Context Protocol) server exposes epanetparser
functionality as standardized tools for agentic AI systems. It communicates
via stdio transport using JSON-RPC 2.0.

Installation
------------

.. code-block:: console

    pip install epanetparser[agentic]

This installs the ``mcp`` package and registers the ``epanetparser-mcp`` console
script.

Running the Server
------------------

.. code-block:: console

    epanetparser-mcp

The server runs on stdio (standard input/output), which is the transport
mechanism used by MCP clients like Claude Desktop, Cursor, and VS Code.

Client Configuration
--------------------

Claude Desktop (``claude_desktop_config.json``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
      "mcpServers": {
        "epanetparser": {
          "command": "epanetparser-mcp"
        }
      }
    }

On macOS: ``~/Library/Application Support/Claude/claude_desktop_config.json``
On Windows: ``%APPDATA%\Claude\claude_desktop_config.json``
On Linux: ``~/.config/Claude/claude_desktop_config.json``

Cursor (``.cursor/mcp.json``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
      "mcpServers": {
        "epanetparser": {
          "command": "epanetparser-mcp"
        }
      }
    }

VS Code (``settings.json``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
      "mcp": {
        "servers": {
          "epanetparser": {
            "command": "epanetparser-mcp"
          }
        }
      }
    }

After configuration, restart your MCP client to connect to the server.

Available Tools
---------------

The server exposes 5 tools:

1. validate_network
^^^^^^^^^^^^^^^^^^^

Validate an EPANET network model with optional custom rulesets.

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``file_path``
     - string
     - No*
     - Path to .inp or .json file
   * - ``json_content``
     - string
     - No*
     - Raw JSON string of WNTR network model
   * - ``rulesets``
     - array[string]
     - No
     - Custom ruleset keys (e.g., ``["milp"]``)
   * - ``output_format``
     - string
     - No
     - ``"json"`` or ``"toon"`` (default: ``"json"``)

\*Provide exactly one of ``file_path`` or ``json_content``.

**Returns:** ValidationReport as JSON string or TOON string.

**Example Request**

.. code-block:: json

    {
      "file_path": "network.json",
      "rulesets": ["milp"],
      "output_format": "toon"
    }

**Example Response (JSON)**

.. code-block:: json

    {
      "is_valid": false,
      "counts": {"ERROR": 2, "WARNING": 1, "INFO": 0},
      "issues": [
        {
          "code": "E_MILP_TIMESTEP",
          "message": "Simulation timestep 7200 seconds not equal to MILOPS timestep 3600 seconds",
          "severity": "ERROR",
          "rule_id": "rule_hydraulic_timestep",
          "ruleset_key": "milp",
          "component_type": "network",
          "component_name": null,
          "attribute": "hydraulic_timestep",
          "component_data": {},
          "context": {"ruleset": "milp"},
          "category": "Option",
          "fix_suggestion": "Set hydraulic timestep to 3600 seconds in [OPTIONS] TIME section."
        }
      ]
    }

**Example Response (TOON)**

.. code-block:: text

    is_valid: false
    counts: {ERROR: 2, WARNING: 1, INFO: 0}
    issues[3]{code,message,severity,rule_id,ruleset_key,component_type,component_name,attribute,component_data,context,category,fix_suggestion}:
    E_MILP_TIMESTEP,"Simulation timestep 7200 seconds not equal to MILOPS timestep 3600 seconds",ERROR,rule_hydraulic_timestep,milp,network,,hydraulic_timestep,{}, {ruleset: milp},Option,Set hydraulic timestep to 3600 seconds in [OPTIONS] TIME section.

2. parse_network
^^^^^^^^^^^^^^^^

Parse a network and return summary statistics without validation.

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``file_path``
     - string
     - No*
     - Path to .inp or .json file
   * - ``json_content``
     - string
     - No*
     - Raw JSON string of WNTR network model

\*Provide exactly one of ``file_path`` or ``json_content``.

**Returns:** Network summary with name, component counts, and metadata.

**Example Request**

.. code-block:: json

    {
      "file_path": "network.json"
    }

**Example Response**

.. code-block:: json

    {
      "success": true,
      "name": "Net1",
      "comment": "Example network",
      "version": "2.2",
      "component_counts": {
        "nodes": 11,
        "links": 13,
        "curves": 1,
        "patterns": 2,
        "controls": 0
      },
      "verbose_counts": {
        "Nodes": 11,
        "Links": 13,
        "Curves": 1,
        "Patterns": 2,
        "Controls": 0
      }
    }

3. convert_format
^^^^^^^^^^^^^^^^^

Convert between EPANET INP and WNTR JSON formats.

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``input_path``
     - string
     - Yes
     - Path to input file (.inp or .json)
   * - ``output_path``
     - string
     - No
     - Output path (default: same name with swapped extension)
   * - ``epanet_version``
     - number
     - No
     - EPANET version for INP output (default: 2.2)

**Returns:** Conversion result with output file path.

**Example Request (INP to JSON)**

.. code-block:: json

    {
      "input_path": "Net1.inp",
      "output_path": "Net1.json"
    }

**Example Request (JSON to INP)**

.. code-block:: json

    {
      "input_path": "Net1.json",
      "output_path": "Net1_2_0.inp",
      "epanet_version": 2.0
    }

**Example Response**

.. code-block:: json

    {
      "success": true,
      "input_file": "Net1.inp",
      "output_file": "Net1.json",
      "direction": "inp_to_json"
    }

4. list_rulesets
^^^^^^^^^^^^^^^^

List all available validation rulesets (core and custom).

**Parameters:** None

**Returns:** Object with ``core_rulesets`` and ``custom_rulesets`` arrays.

**Example Response**

.. code-block:: json

    {
      "core_rulesets": [
        {
          "key": "epanet_core",
          "name": "EPANET core rules",
          "version": "1.0.0",
          "type": "core",
          "description": "Simulator-agnostic checks that a model is a well-formed EPANET model.",
          "component_rules": 44,
          "network_rules": 12
        }
      ],
      "custom_rulesets": [
        {
          "key": "milp",
          "name": "Mixed Integer Linear Programming ruleset",
          "version": "0.2.0",
          "type": "custom",
          "description": "Constraints imposed by an example MILP optimal pump scheduling tool.",
          "component_rules": 17,
          "network_rules": 0
        }
      ]
    }

5. get_ruleset_details
^^^^^^^^^^^^^^^^^^^^^^

Get detailed information about a specific ruleset, including all its rules.

**Parameters**

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Parameter
     - Type
     - Required
     - Description
   * - ``ruleset_key``
     - string
     - Yes
     - Ruleset key (e.g., ``"epanet_core"``, ``"milp"``)
   * - ``component_type``
     - string
     - No
     - Filter by component type (e.g., ``"WNTREPANETNode"``)

**Returns:** Ruleset details including all component and network rules.

**Example Request**

.. code-block:: json

    {
      "ruleset_key": "epanet_core",
      "component_type": "WNTREPANETNode"
    }

**Example Response**

.. code-block:: json

    {
      "key": "epanet_core",
      "name": "EPANET core rules",
      "version": "1.0.0",
      "type": "core",
      "description": "Simulator-agnostic checks that a model is a well-formed EPANET model.",
      "component_rules": [
        {
          "rule_id": "rule_node_has_name",
          "code": "E_NODE_NAME_MISSING",
          "description": "A node must have a name.",
          "severity": "ERROR",
          "attribute": "name",
          "component_type": "WNTREPANETNode"
        },
        {
          "rule_id": "warn_node_has_type",
          "code": "W_NODE_TYPE_MISSING",
          "description": "A node should declare which kind of node it is.",
          "severity": "WARNING",
          "attribute": "node_type",
          "component_type": "WNTREPANETNode"
        }
      ],
      "network_rules": [
        {
          "rule_id": "rule_network_has_name",
          "code": "E_NETWORK_NAME_MISSING",
          "description": "Network missing a name",
          "severity": "ERROR",
          "attribute": "name"
        }
      ]
    }

Error Handling
--------------

All tools return structured error responses when something goes wrong:

.. code-block:: json

    {
      "error": "File not found: network.json",
      "success": false
    }

Or for validation errors:

.. code-block:: json

    {
      "is_valid": false,
      "counts": {"ERROR": 1, "WARNING": 0, "INFO": 0},
      "issues": [
        {
          "code": "E_LOAD_FAILED",
          "message": "Error loading network: ...",
          "severity": "ERROR",
          "rule_id": "load",
          "ruleset_key": "parser",
          "component_type": "network",
          "component_name": null,
          "attribute": null,
          "component_data": {},
          "context": {}
        }
      ]
    }

The MCP protocol uses ``isError: true`` in the ``CallToolResult`` for tool-level
errors (e.g., unknown tool name).

Logging
-------

The MCP server suppresses all logging to stdout/stderr to avoid polluting the
JSON-RPC protocol stream. Logs are directed to the system logger at CRITICAL
level only.

To debug the server, run it directly in a terminal:

.. code-block:: console

    epanetparser-mcp

Type requests manually (JSON-RPC format) or use an MCP inspector tool.

Architecture
------------

The MCP server is implemented in ``epanetparser/core/mcp_server.py`` using the
official Python ``mcp`` SDK. It uses the stdio transport (``stdio_server``)
which communicates over standard input/output with line-delimited JSON-RPC 2.0
messages.

The server registers 5 tools at startup and handles ``call_tool`` requests by
dispatching to the appropriate implementation function. Each implementation
function:

1. Validates input parameters
2. Calls the corresponding epanetparser library function
3. Returns a ``CallToolResult`` with ``TextContent`` containing JSON or TOON

The server is stateless — each tool call is independent and does not share
state with other calls.

See Also
--------

- :doc:`agentic` — Agentic AI integration overview
- :doc:`toon_format` — TOON output format details
- :doc:`usage` — CLI equivalent commands
- MCP Specification: https://modelcontextprotocol.io