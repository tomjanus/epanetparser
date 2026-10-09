Agentic AI Integration
======================

epanetparser provides three interfaces for integration with agentic AI systems:

1. **TOON Output** — Token-optimized format for LLM consumption
2. **MCP Server** — Standardized tool exposure via Model Context Protocol
3. **Python API** — Enhanced ``ValidationReport.as_toon()`` method

Quick Start
-----------

Install with agentic extras:

.. code-block:: console

    pip install epanetparser[agentic]

TOON Output (CLI)
-----------------

.. code-block:: console

    # Validate and output TOON format
    epanetparser validate -f network.json --toon-output

    # With custom ruleset
    epanetparser validate -f network.json --toon-output --ruleset milp

    # Verbose output with full fix suggestions
    epanetparser validate -f network.json --toon-output --verbose

MCP Server
----------

.. code-block:: console

    # Start MCP server (stdio transport)
    epanetparser-mcp

Configure in your MCP client (e.g., Claude Desktop, Cursor):

.. code-block:: json

    {
      "mcpServers": {
        "epanetparser": {
          "command": "epanetparser-mcp"
        }
      }
    }

TOON Format
-----------

TOON (Token-Oriented Object Notation) is a compact, human-readable encoding of
the JSON data model designed for LLM prompts. It reduces token usage by
approximately 66% compared to JSON while maintaining lossless round-trips.

Why TOON?
---------

- **Token Efficient**: ~66% fewer tokens than JSON (per TOON benchmarks)
- **LLM-Friendly**: Explicit array lengths ``[N]`` and field lists ``{fields}`` act as guardrails
- **Human Readable**: Indentation-based structure like YAML, tabular forms like CSV
- **Lossless**: Encodes the same JSON data model deterministically

ValidationReport TOON Structure
-------------------------------

.. code-block:: text

    is_valid: false
    counts: {ERROR: 2, WARNING: 1, INFO: 0}
    issues[3]{code,message,severity,rule_id,ruleset_key,component_type,component_name,attribute,component_data,context,category,fix_suggestion}:
    E_NETWORK_NAME_MISSING,"Network missing a name",ERROR,rule_network_has_name,epanet_core,WNTREPANETNetworkInfo,,name,{}, {ruleset: epanet_core, component_subtype: network_info},Network,Provide a name for the network in the [TITLE] section.
    E_CURVE_TYPE_UNSUPPORTED,"Unsupported curve type None",ERROR,rule_curve_type_supported,epanet_core,WNTREPANETCurve,C1,type,{}, {ruleset: epanet_core},Curve,Change the curve type to one of the supported types: HEAD, PUMP, EFFICIENCY, VOLUME.
    W_UNKNOWN_PATTERN_REFERENCE,"Pattern 'P3' referenced but not defined",WARNING,rule_pattern_refs_exist,epanet_core,network,,pattern,, {ruleset: epanet_core},Network,Define the referenced pattern in the [PATTERNS] section.

Forms used:
- ``is_valid``, ``counts`` → **Object form** (indented key-value)
- ``issues`` → **Tabular form** (uniform objects, fields declared once)
- ``counts`` values → **Inline form** (primitive object)

Python API
----------

ValidationReport.as_toon()
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork
    from epanetparser.core.validation import validate, ValidationContext

    network, _, _ = WNTREPANETNetwork.from_file("network.json")
    report = validate(network, ValidationContext(custom=["milp"]))

    # Get TOON string
    toon_output = report.as_toon()
    print(toon_output)

    # Also available: JSON dict
    json_dict = report.as_dict()

Direct TOON Encoding
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from epanetparser.core.toon import encode, encode_validation_report

    # Encode any JSON-compatible value
    data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
    toon_str = encode(data)
    # users[2]{id,name}:
    # 1,Alice
    # 2,Bob

    # Encode validation report dict (optimized key order)
    report_dict = report.as_dict()
    toon_str = encode_validation_report(report_dict)

MCP Server Tools
----------------

The MCP server exposes 5 tools:

1. validate_network
^^^^^^^^^^^^^^^^^^^

Validate an EPANET network model.

**Parameters:**

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
     - Raw JSON string of WNTR model
   * - ``rulesets``
     - array[string]
     - No
     - Custom ruleset keys (e.g., ``["milp"]``)
   * - ``output_format``
     - string
     - No
     - ``"json"`` or ``"toon"`` (default: ``"json"``)

\*Provide exactly one of ``file_path`` or ``json_content``.

**Returns:** ValidationReport as JSON or TOON string.

**Example:**

.. code-block:: json

    {
      "file_path": "network.json",
      "rulesets": ["milp"],
      "output_format": "toon"
    }

2. parse_network
^^^^^^^^^^^^^^^^

Parse a network and return summary statistics (no validation).

**Parameters:**

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
     - Raw JSON string of WNTR model

\*Provide exactly one of ``file_path`` or ``json_content``.

**Returns:** Network summary with name, component counts, metadata.

3. convert_format
^^^^^^^^^^^^^^^^^

Convert between EPANET INP and WNTR JSON formats.

**Parameters:**

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
     - Output path (default: same name, swapped extension)
   * - ``epanet_version``
     - number
     - No
     - EPANET version for INP output (default: 2.2)

**Returns:** Conversion result with output file path.

4. list_rulesets
^^^^^^^^^^^^^^^^

List all available validation rulesets.

**Parameters:** None

**Returns:** Core and custom rulesets with metadata.

5. get_ruleset_details
^^^^^^^^^^^^^^^^^^^^^^

Get detailed information about a specific ruleset.

**Parameters:**

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

Integration Patterns
--------------------

Pattern 1: Agent with File Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Agent reads/writes files, calls CLI:

.. code-block:: python

    import subprocess
    import json

    def validate_network(file_path: str, rulesets: list[str] = None) -> dict:
        cmd = ["epanetparser", "validate", "-f", file_path, "--json-output"]
        if rulesets:
            for rs in rulesets:
                cmd.extend(["--ruleset", rs])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

Pattern 2: Agent with In-Memory Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Agent has model as JSON string, uses MCP tool:

.. code-block:: python

    # Via MCP client
    result = await session.call_tool("validate_network", {
        "json_content": json_model_string,
        "rulesets": ["milp"],
        "output_format": "toon",
    })

Pattern 3: Python Script in Agent Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from epanetparser.core.epanettypes.network import WNTREPANETNetwork
    from epanetparser.core.validation import validate, ValidationContext

    def check_network(json_str: str) -> str:
        network, errors, _ = WNTREPANETNetwork.from_json(json_str)
        if network is None:
            return f"Parse error: {errors}"

        report = validate(network, ValidationContext(custom=["milp"]))
        if not report.is_valid:
            return report.as_toon()  # Token-efficient for LLM
        return "VALID"

Pattern 4: Batch Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from epanetparser.core.validation import validate, ValidationContext

    context = ValidationContext(custom=["milp"])

    for network_file in network_files:
        network, _, _ = WNTREPANETNetwork.from_file(network_file)
        report = validate(network, context)
        if not report.is_valid:
            # TOON is compact for logging/transmission
            log_issue(network_file, report.as_toon())

Token Efficiency
----------------

Typical validation reports with multiple issues:

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15

   * - Format
     - Characters
     - Est. Tokens
     - Reduction
   * - JSON (pretty)
     - ~3,200
     - ~800
     - baseline
   * - JSON (compact)
     - ~1,800
     - ~450
     - 44%
   * - TOON
     - ~1,100
     - ~275
     - **66%**

TOON achieves greater savings on reports with many uniform issues (tabular form).

Configuration
-------------

No additional configuration required. The ``agentic`` extra installs:

- ``mcp`` — MCP server implementation

TOON encoding is implemented internally with zero dependencies.

Examples
--------

See ``examples/10_agentic_demo.py`` for a complete demonstration:

.. code-block:: console

    python examples/10_agentic_demo.py

Troubleshooting
---------------

MCP Server Not Found
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    pip install epanetparser[agentic]
    epanetparser-mcp

TOON Output Too Verbose
^^^^^^^^^^^^^^^^^^^^^^^

Use ``--ignore-warnings`` to exclude warnings:

.. code-block:: console

    epanetparser validate -f network.json --toon-output --ignore-warnings

Custom Ruleset Not Found
^^^^^^^^^^^^^^^^^^^^^^^^

List available rulesets:

.. code-block:: console

    epanetparser info --list-rulesets

Then ensure the ruleset package is discoverable (see Configuration docs).