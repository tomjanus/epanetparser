TOON Format Reference
=====================

TOON (Token-Oriented Object Notation) is a compact encoding of the JSON data
model designed for LLM consumption. It reduces token usage by approximately 66%
compared to JSON while maintaining lossless round-trips.

This document describes the TOON format as implemented in epanetparser (SPEC v4.1
compliance).

Overview
--------

TOON provides five array forms and an object form for nested structures:

1. **Inline** — Primitive arrays on header line (e.g., ``tags[3]: a,b,c``)
2. **List** — Non-uniform arrays, one ``- item`` per element
3. **Tabular** — Uniform object arrays, declare fields once then stream rows
4. **Keyed Tabular** — Objects of uniform objects, rows carry their own key
5. **Object** — Nested objects using indentation

Design Goals
------------

- **Token Efficiency**: Minimize LLM context usage for structured data
- **Human Readable**: Familiar syntax (YAML-like indentation, CSV-like tables)
- **LLM Guardrails**: Explicit lengths and field declarations prevent hallucination
- **Deterministic**: Same input always produces same output
- **Streaming Friendly**: Tabular form enables incremental parsing

Quick Example
-------------

JSON::

    {
        "is_valid": false,
        "counts": {"ERROR": 2, "WARNING": 1},
        "issues": [
            {"code": "E_X", "severity": "ERROR", "message": "msg1"},
            {"code": "W_Y", "severity": "WARNING", "message": "msg2"}
        ]
    }

TOON::

    is_valid: false
    counts: {ERROR: 2, WARNING: 1}
    issues[2]{code,severity,message}:
    E_X,ERROR,msg1
    W_Y,WARNING,msg2

TOON Forms in Detail
--------------------

Inline Form (Primitive Arrays)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Used for arrays of primitives (strings, numbers, booleans, null) when the array
has 10 or fewer items and the total line width is under 120 characters.

.. code-block:: text

    # Inline array of numbers
    values[4]: 1,2,3,4

    # Inline array of strings
    tags[3]: alpha,beta,gamma

    # Inline array with null
    optional[2]: value,null

    # Inline array of booleans
    flags[3]: true,false,true

List Form (Non-Uniform Arrays)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Used when array elements are not uniform objects or when inline form limits
are exceeded. Each element prefixed with ``-``.

.. code-block:: text

    mixed:
    - 42
    - "hello"
    - true
    - null

    objects:
    - name: Alice
      age: 30
    - id: 123
      role: admin

Tabular Form (Uniform Object Arrays)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most token-efficient form for arrays of objects with identical keys. Fields
declared once in header, then one row per object.

.. code-block:: text

    users[3]{id,name,role}:
    1,Alice,admin
    2,Bob,user
    3,Carol,user

    # With nested objects in cells (inline encoding)
    items[2]{id,metadata}:
    1,{created:2024-01-01,active:true}
    2,{created:2024-01-02,active:false}

Keyed Tabular Form (Uniform Object Maps)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Used for objects whose values are uniform objects. Each row includes its key.

.. code-block:: text

    users[2]{id,name}:
    alice,1,Alice
    bob,2,Bob

Object Form (Nested Objects)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Standard indentation-based key-value pairs for nested structures.

.. code-block:: text

    server:
      host: localhost
      port: 8080
      ssl: true
      routes[2]{path,handler}:
        /api/users,handle_users
        /api/health,handle_health

String Quoting Rules
--------------------

Strings are quoted only when necessary:

- **Unquoted**: Alphanumeric plus ``_``, ``-``, ``.``, ``/``, ``:`` (no spaces, no special chars)
- **Quoted**: Contains spaces, ``,``, ``:``, ``[``, ``]``, ``{``, ``}``, ``#``, ``'``, ``"``, or starts with ``-``

.. code-block:: text

    unquoted: hello_world
    quoted: "hello, world"
    quoted: "contains: colon"
    quoted: "starts with -dash"

Escaping in quoted strings: ``\\`` → ``\\\\``, ``"`` → ``\"``, newline → ``\n``.

Special Values
--------------

- ``null`` — JSON null
- ``true`` / ``false`` — Booleans (lowercase)
- Numbers — Integers and floats as-is (NaN/Inf become ``null``)

ValidationReport TOON Encoding
------------------------------

The ``encode_validation_report`` function produces optimized TOON for validation
reports with a fixed field order and tabular issues array.

Field Order
^^^^^^^^^^^

1. ``is_valid`` (boolean)
2. ``counts`` (inline object: ERROR, WARNING, INFO)
3. ``issues`` (tabular array with fixed column order)
4. Any additional fields

Issues Column Order
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    code,message,severity,rule_id,ruleset_key,component_type,component_name,attribute,component_data,context,category,fix_suggestion

Example Output
^^^^^^^^^^^^^^

.. code-block:: text

    is_valid: false
    counts: {ERROR: 1, WARNING: 2, INFO: 0}
    issues[3]{code,message,severity,rule_id,ruleset_key,component_type,component_name,attribute,component_data,context,category,fix_suggestion}:
    E_NODE_ELEVATION_MISSING,"Junction does not define elevation",ERROR,rule_junction_has_elevation,epanet_core,WNTREPANETNode,J1,elevation,{node_type: Junction, name: J1, elevation: null, base_demand: 0}, {ruleset: epanet_core, component_subtype: Junction},Parameter,Provide the junction elevation in meters.
    W_NODE_COORDINATES_MISSING,"Missing coordinates, node will not be displayed",WARNING,warn_node_missing_coord,epanet_core,WNTREPANETNode,J1,coordinates,{node_type: Junction, name: J1, elevation: 100, base_demand: 0}, {ruleset: epanet_core, component_subtype: Junction},Topology,Assign X,Y coordinates to the node for map display.
    E_UNKNOWN_CURVE_REFERENCE,"Links reference undefined curves: P1 pump_curve_name <C9>",ERROR,rule_link_curves_exist,epanet_core,network,,pump_curve_name,{}, {ruleset: epanet_core},Network,Ensure all link curve references (pump_curve_name, efficiency_curve_name, headloss_curve_name) point to existing curves.

Note that ``component_data`` and ``context`` are encoded as inline objects within
their tabular cells.

CLI Usage
---------

.. code-block:: console

    # TOON output for validation
    epanetparser validate -f network.json --toon-output

    # With custom ruleset
    epanetparser validate -f network.json --toon-output --ruleset milp

    # Mutually exclusive with --json-output and --pretty-output
    # Only one output format may be specified

Python API
----------

.. code-block:: python

    from epanetparser.core.toon import encode, encode_validation_report
    from epanetparser.core.validation import ValidationReport

    # Encode any JSON-compatible value
    data = {"items": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
    toon_str = encode(data)

    # Encode validation report with optimized structure
    report = network.validate()
    toon_str = report.as_toon()
    # Equivalent to:
    toon_str = encode_validation_report(report.as_dict())

TOONEncoder Options
-------------------

The ``TOONEncoder`` class accepts configuration options:

.. code-block:: python

    from epanetparser.core.toon import TOONEncoder

    encoder = TOONEncoder(
        indent="  ",           # Indentation string (default: two spaces)
        delimiter=",",         # Field delimiter: ",", "\t", or "|" (default: comma)
        max_inline_items=10,   # Max items for inline array form (default: 10)
        max_inline_width=120,  # Max character width for inline form (default: 120)
    )
    toon_str = encoder.encode(data)

Delimiter Options
-----------------

The default delimiter is comma (``,``). For data containing commas, use tab
(``\t``) or pipe (``|``):

.. code-block:: python

    encoder = TOONEncoder(delimiter="\t")
    # Uses tabs for field separation

    encoder = TOONEncoder(delimiter="|")
    # Uses pipes for field separation

Implementation Notes
--------------------

- **Tabular detection**: An array uses tabular form if all elements are objects
  with identical keys. Empty arrays with key ``"issues"`` also use tabular form
  with predefined ValidationReport issue fields.
- **Empty arrays**: Rendered as ``[]`` (inline) or ``key[0]{fields}:`` (tabular).
- **Nested structures**: Objects and arrays within tabular cells are encoded
  inline using the same rules recursively.
- **Field ordering**: ``encode_validation_report`` enforces a specific key order
  for deterministic output.

See Also
--------

- :doc:`agentic` — Agentic AI integration overview
- :doc:`library` — Python API for ``ValidationReport.as_toon()``
- :doc:`usage` — CLI ``--toon-output`` flag