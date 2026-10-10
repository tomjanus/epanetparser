# io (input/output) module

A **standalone** extraction of the WNTR code responsible for:

- Reading an EPANET INP file into an in-memory water network model.
- Converting that model to/from a plain Python `dict`.
- Reading/writing that dictionary as JSON.
- Writing the model back out to an EPANET INP file.

It is a copy of the following WNTR modules, trimmed and with imports
rewritten to be self-contained:

- `wntr.epanet.io` (`InpFile` INP reader/writer)
- `wntr.epanet.util`, `wntr.epanet.exceptions`
- `wntr.network.io` (`to_dict`/`from_dict`/`write_json`/`read_json`/
  `write_inpfile`/`read_inpfile`)
- `wntr.network.model`, `.base`, `.elements`, `.options`, `.controls`
- `wntr.utils.ordered_set`, `wntr.utils.doc_inheritor`

## Directory layout

```
epanetparser.core.io/
├── __init__.py            # convenience re-exports
├── epanet/
│   ├── io.py              # InpFile reader/writer, EpanetRule, control parsing
│   ├── util.py            # unit conversions (FlowUnits, HydParam, ...)
│   └── exceptions.py      # EPANET exception/error-code types
├── network/
│   ├── model.py           # WaterNetworkModel and element registries
│   ├── base.py            # Node/Link/Registry base classes
│   ├── elements.py        # Junction, Tank, Reservoir, Pipe, Pump, Valve, ...
│   ├── options.py         # Options (time, hydraulic, quality, ...)
│   ├── controls.py        # Control/Rule classes
│   └── io.py              # to_dict/from_dict/write_json/read_json/
│                          #    write_inpfile/read_inpfile
└── utils/
    ├── ordered_set.py
    └── doc_inheritor.py
```

## Usage

```python
import epanetparser.io as eio

# Read an EPANET INP file into a model
wn = eio.read_inpfile("network.inp")

# Convert the model to a plain dict
d = eio.to_dict(wn)

# ... inspect / modify / serialize the dict however you like ...

# Rebuild a model from a dict
wn2 = eio.from_dict(d)

# Or go straight to/from JSON
eio.write_json(wn, "network.json")
wn3 = eio.read_json("network.json")

# Write a model back out to an INP file
eio.write_inpfile(wn, "network_out.inp")
```

## Notes

- The dictionary returned by `to_dict` is the same schema WNTR uses for its
  own `WaterNetworkModel.to_dict()`/JSON export (keys: `version`, `comment`,
  `name`, `references`, `options`, `curves`, `patterns`, `nodes`, `links`,
  `sources`, `controls`), so files produced by this module and by full WNTR
  are interchangeable.
- All values in the dictionary are in SI units (meters, seconds, cubic
  meters per second, etc.), matching WNTR's internal representation,
  regardless of the units used in the source INP file.
- This code was extracted from WNTR (https://github.com/USEPA/WNTR) and
  keeps the original license headers/attributions where present. Refer to
  the main WNTR repository for the applicable license terms.
