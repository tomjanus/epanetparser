"""MCP (Model Context Protocol) server for epanetparser.

Exposes epanetparser functionality as MCP tools for agentic AI systems.
Run with: python -m epanetparser.core.mcp_server
Or via console script: epanetparser-mcp
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Disable logging before importing epanetparser to avoid stdout pollution
# which breaks the JSON-RPC protocol over stdio
logging.getLogger().handlers = []
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ["epanetparser", "wntr"]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).propagate = False

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolResult,
        ListToolsResult,
    )
except ImportError:
    print("MCP package not installed. Install with: pip install epanetparser[agentic]", file=sys.stderr)
    sys.exit(1)

from wntr.epanet.exceptions import EpanetException

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.epanettypes.exceptions import WNTREPANETParserException
from epanetparser.core.lib.converter import WNTRINPJSONConverter
from epanetparser.core.validation import (
    RuleSetRegistry,
    ValidationContext,
    validate,
)
from epanetparser.core.toon import encode_validation_report


server = Server("epanetparser")


def _load_network(
    file_path: Optional[str] = None,
    json_content: Optional[str] = None,
) -> tuple[Optional[WNTREPANETNetwork], Optional[str]]:
    """Load a network from file path or JSON content.

    Returns:
        Tuple of (network, error_message). If network is None, error_message contains the error.
    """
    if file_path is not None and json_content is not None:
        return None, "Provide either file_path or json_content, not both"
    if file_path is None and json_content is None:
        return None, "Must provide either file_path or json_content"

    try:
        if file_path:
            path = Path(file_path)
            if not path.exists():
                return None, f"File not found: {file_path}"
            network, errors, warnings = WNTREPANETNetwork.from_file(str(path))
        else:
            network, errors, warnings = WNTREPANETNetwork.from_json(json_content)

        if network is None:
            error_msgs = []
            if errors:
                for collection, errs in errors.items():
                    for err in errs:
                        error_msgs.append(f"{collection}: {err}")
            return None, "; ".join(error_msgs) if error_msgs else "Failed to parse network"

        return network, None
    except (OSError, TypeError, ValueError, EpanetException, WNTREPANETParserException) as exc:
        return None, f"Error loading network: {str(exc)}"


async def _validate_network_impl(
    file_path: Optional[str] = None,
    json_content: Optional[str] = None,
    rulesets: Optional[List[str]] = None,
    output_format: str = "json",
) -> List[TextContent]:
    """Validate an EPANET network model."""
    network, error = _load_network(file_path, json_content)
    if error:
        return [TextContent(type="text", text=json.dumps({
            "is_valid": False,
            "counts": {"ERROR": 1, "WARNING": 0, "INFO": 0},
            "issues": [{
                "code": "E_LOAD_FAILED",
                "message": error,
                "severity": "ERROR",
                "rule_id": "load",
                "ruleset_key": "parser",
                "component_type": "network",
                "component_name": None,
                "attribute": None,
                "component_data": {},
                "context": {},
            }]
        }))]

    context = ValidationContext(custom=tuple(rulesets or ()))
    report = validate(network, context)

    if output_format == "toon":
        return [TextContent(type="text", text=report.as_toon())]
    return [TextContent(type="text", text=json.dumps(report.as_dict(), indent=2))]


async def _parse_network_impl(
    file_path: Optional[str] = None,
    json_content: Optional[str] = None,
) -> List[TextContent]:
    """Parse an EPANET network and return summary statistics."""
    network, error = _load_network(file_path, json_content)
    if error:
        return [TextContent(type="text", text=json.dumps({
            "error": error,
            "success": False,
        }))]

    summary = {
        "success": True,
        "name": network.name,
        "comment": network.comment,
        "version": network.version,
        "component_counts": network.report(),
        "verbose_counts": network.verbose_report(),
    }
    return [TextContent(type="text", text=json.dumps(summary, indent=2))]


async def _convert_format_impl(
    input_path: str,
    output_path: Optional[str] = None,
    epanet_version: float = 2.2,
) -> List[TextContent]:
    """Convert between EPANET INP and WNTR JSON formats."""
    try:
        input_file = Path(input_path)
        if not input_file.exists():
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Input file not found: {input_path}",
            }))]

        if output_path is None:
            if input_file.suffix.lower() == ".inp":
                output_path = str(input_file.with_suffix(".json"))
            elif input_file.suffix.lower() == ".json":
                output_path = str(input_file.with_suffix(".inp"))
            else:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Unsupported file extension: {input_file.suffix}",
                }))]

        output_file = Path(output_path)

        if input_file.suffix.lower() == ".inp":
            generated = WNTRINPJSONConverter.inp_to_json(
                inp_path=input_file,
                json_path=output_file,
                indent=2,
            )
        elif input_file.suffix.lower() == ".json":
            generated = WNTRINPJSONConverter.json_to_inp(
                json_path=input_file,
                inp_path=output_file,
                version=epanet_version,
            )
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": f"Unsupported file extension: {input_file.suffix}",
            }))]

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "input_file": str(input_file),
            "output_file": str(generated),
            "direction": "inp_to_json" if input_file.suffix.lower() == ".inp" else "json_to_inp",
        }))]

    except (OSError, TypeError, ValueError, KeyError, EpanetException) as   :
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Conversion failed: {str(exc)}",
        }))]


async def _list_rulesets_impl() -> List[TextContent]:
    """List all available validation rulesets."""
    registry = RuleSetRegistry()
    result = {
        "core_rulesets": [],
        "custom_rulesets": [],
    }

    for key in registry.core_keys():
        rs = registry.get(key)
        result["core_rulesets"].append({
            "key": key,
            "name": rs.name,
            "version": rs.version,
            "type": "core",
            "description": rs.description,
            "component_rules": len(rs.component_rules),
            "network_rules": len(rs.network_rules),
        })

    for key in registry.custom_keys():
        rs = registry.get(key)
        result["custom_rulesets"].append({
            "key": key,
            "name": rs.name,
            "version": rs.version,
            "type": "custom",
            "description": rs.description,
            "component_rules": len(rs.component_rules),
            "network_rules": len(rs.network_rules),
        })

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_ruleset_details_impl(
    ruleset_key: str,
    component_type: Optional[str] = None,
) -> List[TextContent]:
    """Get detailed information about a specific ruleset."""
    registry = RuleSetRegistry()
    available = registry.keys()

    if ruleset_key not in available:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Ruleset '{ruleset_key}' not found. Available: {list(available)}",
        }))]

    rs = registry.get(ruleset_key)

    component_rules = []
    for spec in rs.component_rules:
        if component_type is None or spec.applies_to(component_type):
            component_rules.append({
                "rule_id": spec.rule_id,
                "code": spec.code,
                "description": spec.description,
                "severity": spec.severity.name,
                "attribute": spec.attribute,
                "component_type": spec.component_type,
            })

    network_rules = []
    for spec in rs.network_rules:
        network_rules.append({
            "rule_id": spec.rule_id,
            "code": spec.code,
            "description": spec.description,
            "severity": spec.severity.name,
            "attribute": spec.attribute,
        })

    result = {
        "key": rs.key,
        "name": rs.name,
        "version": rs.version,
        "type": "core" if rs.key in registry.core_keys() else "custom",
        "description": rs.description,
        "component_rules": component_rules,
        "network_rules": network_rules,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# Define tools
TOOLS = [
    Tool(
        name="validate_network",
        description="Validate an EPANET network model",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to .inp or .json file"},
                "json_content": {"type": "string", "description": "Raw JSON string of WNTR network model"},
                "rulesets": {"type": "array", "items": {"type": "string"}, "description": "Custom ruleset keys (e.g., [\"milp\"])"},
                "output_format": {"type": "string", "enum": ["json", "toon"], "default": "json", "description": "Output format"},
            },
        },
    ),
    Tool(
        name="parse_network",
        description="Parse an EPANET network and return summary statistics",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to .inp or .json file"},
                "json_content": {"type": "string", "description": "Raw JSON string of WNTR network model"},
            },
        },
    ),
    Tool(
        name="convert_format",
        description="Convert between EPANET INP and WNTR JSON formats",
        inputSchema={
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to input file (.inp or .json)"},
                "output_path": {"type": "string", "description": "Optional output path (default: same name with swapped extension)"},
                "epanet_version": {"type": "number", "default": 2.2, "description": "EPANET version for INP output"},
            },
            "required": ["input_path"],
        },
    ),
    Tool(
        name="list_rulesets",
        description="List all available validation rulesets",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_ruleset_details",
        description="Get detailed information about a specific ruleset",
        inputSchema={
            "type": "object",
            "properties": {
                "ruleset_key": {"type": "string", "description": "Ruleset key (e.g., \"epanet_core\", \"milp\")"},
                "component_type": {"type": "string", "description": "Optional filter by component type (e.g., \"WNTREPANETNode\")"},
            },
            "required": ["ruleset_key"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    try:
        if name == "validate_network":
            result = await _validate_network_impl(
                file_path=arguments.get("file_path"),
                json_content=arguments.get("json_content"),
                rulesets=arguments.get("rulesets"),
                output_format=arguments.get("output_format", "json"),
            )
        elif name == "parse_network":
            result = await _parse_network_impl(
                file_path=arguments.get("file_path"),
                json_content=arguments.get("json_content"),
            )
        elif name == "convert_format":
            result = await _convert_format_impl(
                input_path=arguments["input_path"],
                output_path=arguments.get("output_path"),
                epanet_version=arguments.get("epanet_version", 2.2),
            )
        elif name == "list_rulesets":
            result = await _list_rulesets_impl()
        elif name == "get_ruleset_details":
            result = await _get_ruleset_details_impl(
                ruleset_key=arguments["ruleset_key"],
                component_type=arguments.get("component_type"),
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )

        return CallToolResult(content=result)

    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        EpanetException,
        WNTREPANETParserException,
    ) as exc:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


def main() -> None:
    """Run the MCP server on stdio."""
    import asyncio
    asyncio.run(_async_main())


async def _async_main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    main()