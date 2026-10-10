"""
Standalone INP <-> dictionary/JSON conversion module.

This package is a trimmed, self-contained extraction of the WNTR code that is
responsible for:

  * Reading an EPANET INP file into an in-memory water network model
    (``epanet.io.InpFile``).
  * Converting that model to/from a plain Python ``dict``
    (``network.io.to_dict`` / ``network.io.from_dict``).
  * Writing/reading that dictionary as JSON
    (``network.io.write_json`` / ``network.io.read_json``).
  * Writing the model back out to an EPANET INP file
    (``network.io.write_inpfile``).

It does **not** depend on the rest of WNTR (no simulation, GIS, graphics,
morphology, metrics, or multi-species water quality (MSX) support). See
README.md in this directory for details and usage examples.
"""

__version__ = "wntr-1.4.0-compatible"

from .network.model import WaterNetworkModel
from .epanet.io import InpFile
from .network.io import (
    to_dict,
    from_dict,
    write_json,
    read_json,
    write_inpfile,
    read_inpfile,
)

__all__ = [
    "WaterNetworkModel",
    "InpFile",
    "to_dict",
    "from_dict",
    "write_json",
    "read_json",
    "write_inpfile",
    "read_inpfile",
]
