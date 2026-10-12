Parsing
=======

Two parsers produce the same canonical output: a plain Python ``dict`` in the
WNTR SI schema. ``read_inp_to_dict`` is the public entry point used by
``from_file`` and the converter; ``InpParser`` is the standalone parser.

``read_inp_to_dict``
--------------------

.. autofunction:: epanetparser.core.io.read_inp_to_dict

It reads the INP file with the vendored WNTR ``InpFile`` model and serialises
it with ``network.io.to_dict``. No external WNTR installation is required.

``InpParser``
-------------

.. autoclass:: epanetparser.core.io.inp_parser.InpParser
   :members: parse

``InpParser`` parses the INP text directly and emits the identical WNTR SI
dictionary. The two implementations are exercised against each other on every
bundled core network; see ``tests/test_inp_parser_equivalence.py``.

Structured errors
-----------------

Malformed input raises a structured exception from
``epanetparser.core.io.inp_errors`` rather than a generic parse failure. Each
error carries a stable code, the offending line, and suggestions, so callers
and the CLI can report precisely what went wrong.

.. autoexception:: epanetparser.core.io.inp_errors.InpParseError
.. autoexception:: epanetparser.core.io.inp_errors.InpSyntaxError
.. autoexception:: epanetparser.core.io.inp_errors.InpSemanticError
.. autoexception:: epanetparser.core.io.inp_errors.InpStructuralError

.. autofunction:: epanetparser.core.io.inp_errors.create_inp_error

WNTR JSON parser
----------------

.. autoclass:: epanetparser.core.parsers.wntrjsonparser.WNTRJSONParser
   :members: parse, enforce_unique, missing_keys, has_errors, has_warnings
   :undoc-members:

   .. automethod:: __init__