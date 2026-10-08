"""Agentic AI Integration Demo for epanetparser.

This example demonstrates how to use epanetparser in agentic AI workflows:
1. Programmatic Python API with TOON output
2. CLI with --toon-output flag
3. MCP server integration (if mcp package installed)
4. Token efficiency comparison between JSON and TOON
"""

import json
import sys
import subprocess
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import validate, ValidationContext
from epanetparser.core.toon import encode_validation_report


def demo_python_api():
    """Demonstrate programmatic Python API with TOON output."""
    print("=" * 60)
    print("1. PROGRAMMATIC PYTHON API WITH TOON OUTPUT")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    invalid_path = project_root / "tests" / "data" / "invalid_network.json"

    # Load networks
    valid_network, _, _ = WNTREPANETNetwork.from_file(str(valid_path))
    invalid_network, _, _ = WNTREPANETNetwork.from_file(str(invalid_path))

    print(f"\nValid network: {valid_network.name}")
    print(f"  Nodes: {len(valid_network.nodes)}, Links: {len(valid_network.links)}")

    print(f"\nInvalid network: {invalid_network.name}")
    print(f"  Nodes: {len(invalid_network.nodes)}, Links: {len(invalid_network.links)}")

    # Validate with core ruleset
    print("\n--- Core Ruleset Only ---")
    report_valid = validate(valid_network)
    report_invalid = validate(invalid_network)

    print(f"Valid network: is_valid={report_valid.is_valid}, issues={len(report_valid)}")
    print(f"Invalid network: is_valid={report_invalid.is_valid}, issues={len(report_invalid)}")

    # TOON output for valid network
    print("\n--- TOON Output (Valid Network) ---")
    toon_output = report_valid.as_toon()
    print(toon_output[:500] + ("..." if len(toon_output) > 500 else ""))

    # TOON output for invalid network
    print("\n--- TOON Output (Invalid Network) ---")
    toon_output = report_invalid.as_toon()
    print(toon_output[:800] + ("..." if len(toon_output) > 800 else ""))

    # Validate with custom ruleset (MILP)
    print("\n--- Core + MILP Ruleset ---")
    context = ValidationContext(custom=["milp"])
    report_milp = validate(invalid_network, context)
    print(f"Invalid network + MILP: is_valid={report_milp.is_valid}, issues={len(report_milp)}")

    toon_milp = report_milp.as_toon()
    print("\nTOON output (first 800 chars):")
    print(toon_milp[:800] + ("..." if len(toon_milp) > 800 else ""))


def demo_token_comparison():
    """Compare JSON vs TOON token usage."""
    print("\n" + "=" * 60)
    print("2. TOKEN EFFICIENCY COMPARISON: JSON vs TOON")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    invalid_path = project_root / "tests" / "data" / "invalid_network.json"
    invalid_network, _, _ = WNTREPANETNetwork.from_file(str(invalid_path))

    report = validate(invalid_network, ValidationContext(custom=["milp"]))

    # JSON output
    json_str = json.dumps(report.as_dict(), indent=2)
    json_chars = len(json_str)
    json_tokens_est = json_chars / 4  # Rough estimate: 4 chars per token

    # TOON output
    toon_str = report.as_toon()
    toon_chars = len(toon_str)
    toon_tokens_est = toon_chars / 4

    print(f"\nReport: {len(report)} issues ({len(report.errors)} errors, {len(report.warnings)} warnings)")
    print(f"\nJSON:  {json_chars:,} chars  ~{json_tokens_est:,.0f} tokens")
    print(f"TOON:  {toon_chars:,} chars  ~{toon_tokens_est:,.0f} tokens")
    print(f"Reduction: {((json_chars - toon_chars) / json_chars * 100):.1f}% fewer characters")

    print("\n--- JSON Sample (first 300 chars) ---")
    print(json_str[:300] + "...")

    print("\n--- TOON Sample (first 300 chars) ---")
    print(toon_str[:300] + "...")


def demo_cli_usage():
    """Demonstrate CLI usage with --toon-output."""
    print("\n" + "=" * 60)
    print("3. CLI USAGE WITH --toon-output")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"
    invalid_path = project_root / "tests" / "data" / "invalid_network.json"

    print("\nCommand: epanetparser validate -f valid_network.json --toon-output")
    result = subprocess.run(
        ["python", "-m", "epanetparser.core.parse", "validate", "-f", str(valid_path), "--toon-output"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output (first 400 chars):\n{result.stdout[:400]}...")

    print("\nCommand: epanetparser validate -f invalid_network.json --toon-output --ruleset milp")
    result = subprocess.run(
        ["python", "-m", "epanetparser.core.parse", "validate", "-f", str(invalid_path), "--toon-output", "--ruleset", "milp"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output (first 600 chars):\n{result.stdout[:600]}...")


def demo_mcp_integration():
    """Demonstrate MCP server integration (requires mcp package)."""
    print("\n" + "=" * 60)
    print("4. MCP SERVER INTEGRATION")
    print("=" * 60)

    try:
        import mcp
        print("MCP package is available.")
        print("\nTo start the MCP server:")
        print("  epanetparser-mcp")
        print("\nOr via Python:")
        print("  python -m epanetparser.core.mcp_server")
        print("\nThe server exposes these tools:")
        print("  - validate_network(file_path, json_content, rulesets, output_format)")
        print("  - parse_network(file_path, json_content)")
        print("  - convert_format(input_path, output_path, epanet_version)")
        print("  - list_rulesets()")
        print("  - get_ruleset_details(ruleset_key, component_type)")

        # Show example of calling tools programmatically
        print("\n--- Example: Calling MCP tools via Python ---")
        print("""
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def call_validate():
    async with stdio_client("epanetparser-mcp") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("validate_network", {
                "file_path": "tests/data/invalid_network.json",
                "rulesets": ["milp"],
                "output_format": "toon",
            })
            print(result.content[0].text)

asyncio.run(call_validate())
""")

    except ImportError:
        print("MCP package not installed.")
        print("Install with: pip install epanetparser[agentic]")
        print("\nOnce installed, start the server with:")
        print("  epanetparser-mcp")


def demo_raw_json_input():
    """Demonstrate validating raw JSON content (useful for agents with in-memory models)."""
    print("\n" + "=" * 60)
    print("5. VALIDATING RAW JSON CONTENT (IN-MEMORY MODELS)")
    print("=" * 60)

    project_root = Path(__file__).resolve().parent.parent
    valid_path = project_root / "tests" / "data" / "valid_network.json"

    with open(valid_path) as f:
        json_content = f.read()

    print(f"Loaded JSON ({len(json_content):,} chars)")
    print("Validating from JSON string...")

    network, errors, warnings = WNTREPANETNetwork.from_json(json_content)
    if network:
        report = validate(network)
        print(f"Result: is_valid={report.is_valid}, issues={len(report)}")
        print(f"TOON output:\n{report.as_toon()[:400]}...")
    else:
        print(f"Parse failed: {errors}")


def main():
    print("EPANETParser Agentic AI Integration Demo")
    print("=========================================\n")

    demo_python_api()
    demo_token_comparison()
    demo_cli_usage()
    demo_mcp_integration()
    demo_raw_json_input()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()