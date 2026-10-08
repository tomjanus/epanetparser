# Agentic AI Integration

epanetparser provides three interfaces for integration with agentic AI systems:

1. **TOON Output** — Token-optimized format for LLM consumption
2. **MCP Server** — Standardized tool exposure via Model Context Protocol
3. **Python API** — Enhanced `ValidationReport.as_toon()` method

---

## Quick Start

Install with agentic extras:

```bash
pip install epanetparser[agentic]
```

### TOON Output (CLI)

```bash
# Validate and output TOON format
epanetparser validate -f network.json --toon-output

# With custom ruleset
epanetparser validate -f network.json --toon-output --ruleset milp
```

### MCP Server

```bash
# Start MCP server (stdio transport)
epanetparser-mcp
```

Configure in your MCP client (e.g., Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "epanetparser": {
      "command": "epanetparser-mcp"
    }
  }
}
```

---

## TOON Format

TOON (Token-Oriented Object Notation) is a compact, human-readable encoding of the JSON data model designed for LLM prompts. It reduces token usage by 40-50% compared to JSON while maintaining lossless round-trips.

### Why TOON?

- **Token Efficient**: ~42% fewer tokens than JSON (per TOON benchmarks)
- **LLM-Friendly**: Explicit array lengths `[N]` and field lists `{fields}` act as guardrails
- **Human Readable**: Indentation-based structure like YAML, tabular forms like CSV
- **Lossless**: Encodes the same JSON data model deterministically

### ValidationReport TOON Structure

```toon
is_valid: false
counts: {ERROR: 2, WARNING: 1, INFO: 0}
issues[3]{code,message,severity,rule_id,ruleset_key,component_type,component_name,attribute,component_data,context}:
E_NETWORK_NAME_MISSING,"Network missing a name",ERROR,rule_network_has_name,epanet_core,WNTREPANETNetworkInfo,,name,{}, {ruleset: epanet_core, component_subtype: network_info}
E_CURVE_TYPE_UNSUPPORTED,"Unsupported curve type None",ERROR,rule_curve_type_supported,epanet_core,WNTREPANETCurve,C1,type,{}, {ruleset: epanet_core}
W_UNKNOWN_PATTERN_REFERENCE,"Pattern 'P3' referenced but not defined",WARNING,rule_pattern_refs_exist,epanet_core,network,,pattern,, {ruleset: epanet_core}
```

**Forms used:**
- `is_valid`, `counts` → **Object form** (indented key-value)
- `issues` → **Tabular form** (uniform objects, fields declared once)
- `counts` values → **Inline form** (primitive object)

---

## Python API

### ValidationReport.as_toon()

```python
from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import validate, ValidationContext

network, _, _ = WNTREPANETNetwork.from_file("network.json")
report = validate(network, ValidationContext(custom=["milp"]))

# Get TOON string
toon_output = report.as_toon()
print(toon_output)

# Also available: JSON dict
json_dict = report.as_dict()
```

### Direct TOON Encoding

```python
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
```

---

## MCP Server Tools

The MCP server exposes 5 tools:

### 1. validate_network

Validate an EPANET network model.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | No* | Path to .inp or .json file |
| `json_content` | string | No* | Raw JSON string of WNTR model |
| `rulesets` | array[string] | No | Custom ruleset keys (e.g., `["milp"]`) |
| `output_format` | string | No | `"json"` or `"toon"` (default: `"json"`) |

*Provide exactly one of `file_path` or `json_content`.

**Returns:** ValidationReport as JSON or TOON string.

**Example:**
```json
{
  "file_path": "network.json",
  "rulesets": ["milp"],
  "output_format": "toon"
}
```

### 2. parse_network

Parse a network and return summary statistics (no validation).

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | No* | Path to .inp or .json file |
| `json_content` | string | No* | Raw JSON string of WNTR model |

**Returns:** Network summary with name, component counts, metadata.

### 3. convert_format

Convert between EPANET INP and WNTR JSON formats.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input_path` | string | Yes | Path to input file (.inp or .json) |
| `output_path` | string | No | Output path (default: same name, swapped extension) |
| `epanet_version` | number | No | EPANET version for INP output (default: 2.2) |

**Returns:** Conversion result with output file path.

### 4. list_rulesets

List all available validation rulesets.

**Parameters:** None

**Returns:** Core and custom rulesets with metadata.

### 5. get_ruleset_details

Get detailed information about a specific ruleset.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ruleset_key` | string | Yes | Ruleset key (e.g., `"epanet_core"`, `"milp"`) |
| `component_type` | string | No | Filter by component type (e.g., `"WNTREPANETNode"`) |

**Returns:** Ruleset details including all component and network rules.

---

## Integration Patterns

### Pattern 1: Agent with File Access

Agent reads/writes files, calls CLI:

```python
import subprocess

def validate_network(file_path: str, rulesets: list[str] = None) -> dict:
    cmd = ["epanetparser", "validate", "-f", file_path, "--json-output"]
    if rulesets:
        for rs in rulesets:
            cmd.extend(["--ruleset", rs])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)
```

### Pattern 2: Agent with In-Memory Model

Agent has model as JSON string, uses MCP tool:

```python
# Via MCP client
result = await session.call_tool("validate_network", {
    "json_content": json_model_string,
    "rulesets": ["milp"],
    "output_format": "toon",
})
```

### Pattern 3: Python Script in Agent Workflow

```python
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
```

### Pattern 4: Batch Validation

```python
from epanetparser.core.validation import validate, ValidationContext

context = ValidationContext(custom=["milp"])

for network_file in network_files:
    network, _, _ = WNTREPANETNetwork.from_file(network_file)
    report = validate(network, context)
    if not report.is_valid:
        # TOON is compact for logging/transmission
        log_issue(network_file, report.as_toon())
```

---

## Token Efficiency

Typical validation reports with multiple issues:

| Format | Characters | Est. Tokens | Reduction |
|--------|-----------|-------------|-----------|
| JSON (pretty) | ~3,200 | ~800 | baseline |
| JSON (compact) | ~1,800 | ~450 | 44% |
| TOON | ~1,100 | ~275 | **66%** |

TOON achieves greater savings on reports with many uniform issues (tabular form).

---

## Configuration

No additional configuration required. The `agentic` extra installs:
- `mcp` — MCP server implementation

TOON encoding is implemented internally with zero dependencies.

---

## Examples

See `examples/10_agentic_demo.py` for a complete demonstration:

```bash
python examples/10_agentic_demo.py
```

---

## Troubleshooting

### MCP Server Not Found

```bash
pip install epanetparser[agentic]
epanetparser-mcp
```

### TOON Output Too Verbose

Use `--ignore-warnings` to exclude warnings:
```bash
epanetparser validate -f network.json --toon-output --ignore-warnings
```

### Custom Ruleset Not Found

List available rulesets:
```bash
epanetparser info --list-rulesets
```

Then ensure the ruleset package is discoverable (see Configuration docs).