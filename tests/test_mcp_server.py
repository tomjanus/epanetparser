"""Tests for MCP server."""

import importlib.util
import json
import os
import pytest
from pathlib import Path

# Skip if mcp not installed
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Simulation validation runs through WNTR, an optional extra. Detect it by spec
# so the simulation test skips cleanly when the extra is absent, mirroring the
# guard in tests/test_cli.py.
WNTR_AVAILABLE = importlib.util.find_spec("wntr") is not None
requires_wntr = pytest.mark.skipif(
    not WNTR_AVAILABLE, reason="WNTR (the 'simulation' extra) is not installed"
)

# Mark as integration tests requiring MCP server binary
pytestmark = [
    pytest.mark.skipif(not MCP_AVAILABLE, reason="mcp package not installed"),
    pytest.mark.integration,
]


class TestMCPServer:
    """Tests for MCP server tools via MCP client."""

    @pytest.fixture
    def valid_network_path(self):
        return "tests/data/valid_network.json"

    @pytest.fixture
    def invalid_network_path(self):
        return "tests/data/invalid_network.json"

    @pytest.fixture
    def server_params(self):
        # The console script would otherwise import `epanetparser` from the
        # editable install's site-packages path; prepend the repo root so the
        # server under test runs this checkout.
        repo_root = Path(__file__).resolve().parent.parent
        env = dict(os.environ)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo_root) + (os.pathsep + existing if existing else "")
        return StdioServerParameters(
            command="epanetparser-mcp",
            args=[],
            env=env,
        )

    async def _call_tool(self, server_params, tool_name: str, arguments: dict):
        """Helper to call a tool via MCP client."""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result

    @pytest.mark.asyncio
    async def test_validate_network_file_path(self, valid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_network", {
            "file_path": valid_network_path,
        })
        assert len(result.content) == 1
        report = json.loads(result.content[0].text)
        assert "is_valid" in report
        assert "counts" in report
        assert "issues" in report
        assert report["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_network_json_content(self, valid_network_path, server_params):
        with open(valid_network_path) as f:
            json_content = f.read()

        result = await self._call_tool(server_params, "validate_network", {
            "json_content": json_content,
        })
        report = json.loads(result.content[0].text)
        assert report["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_network_invalid(self, invalid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_network", {
            "file_path": invalid_network_path,
        })
        report = json.loads(result.content[0].text)
        assert report["is_valid"] is False
        assert len(report["issues"]) > 0

    @pytest.mark.asyncio
    async def test_validate_network_with_ruleset(self, valid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_network", {
            "file_path": valid_network_path,
            "rulesets": ["milp"],
        })
        report = json.loads(result.content[0].text)
        assert "is_valid" in report

    @pytest.mark.asyncio
    async def test_validate_network_toon_output(self, valid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_network", {
            "file_path": valid_network_path,
            "output_format": "toon",
        })
        assert len(result.content) == 1
        text = result.content[0].text
        assert "is_valid: true" in text
        assert "issues[" in text
        assert "{code,message,severity,rule_id,ruleset_key" in text
        assert "validation_layer" in text

    @pytest.mark.asyncio
    async def test_validate_network_error_both_inputs(self, valid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_network", {
            "file_path": valid_network_path,
            "json_content": "{}",
        })
        report = json.loads(result.content[0].text)
        assert report["is_valid"] is False
        assert any("E_LOAD_FAILED" in issue["code"] for issue in report["issues"])

    @pytest.mark.asyncio
    async def test_validate_network_error_neither_input(self, server_params):
        result = await self._call_tool(server_params, "validate_network", {})
        report = json.loads(result.content[0].text)
        assert report["is_valid"] is False

    @pytest.mark.asyncio
    async def test_parse_network_file_path(self, valid_network_path, server_params):
        result = await self._call_tool(server_params, "parse_network", {
            "file_path": valid_network_path,
        })
        assert len(result.content) == 1

        summary = json.loads(result.content[0].text)
        assert summary["success"] is True
        assert "name" in summary
        assert "component_counts" in summary
        assert "verbose_counts" in summary

    @pytest.mark.asyncio
    async def test_parse_network_json_content(self, valid_network_path, server_params):
        with open(valid_network_path) as f:
            json_content = f.read()

        result = await self._call_tool(server_params, "parse_network", {
            "json_content": json_content,
        })
        summary = json.loads(result.content[0].text)
        assert summary["success"] is True

    @pytest.mark.asyncio
    async def test_parse_network_invalid(self, invalid_network_path, server_params):
        result = await self._call_tool(server_params, "parse_network", {
            "file_path": invalid_network_path,
        })
        summary = json.loads(result.content[0].text)
        # The network parses successfully (it's valid JSON), but validation would fail
        assert summary["success"] is True
        assert "component_counts" in summary

    @pytest.mark.asyncio
    async def test_convert_format_json_to_inp(self, tmp_path, valid_network_path, server_params):
        output_path = tmp_path / "output.inp"
        result = await self._call_tool(server_params, "convert_format", {
            "input_path": valid_network_path,
            "output_path": str(output_path),
        })

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["direction"] == "json_to_inp"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_convert_format_auto_output_path(self, tmp_path, valid_network_path, server_params):
        import shutil
        test_file = tmp_path / "valid_network.json"
        shutil.copy(valid_network_path, test_file)

        result = await self._call_tool(server_params, "convert_format", {
            "input_path": str(test_file),
        })
        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["output_file"].endswith(".inp")

    @pytest.mark.asyncio
    async def test_convert_format_invalid_input(self, server_params):
        result = await self._call_tool(server_params, "convert_format", {
            "input_path": "/nonexistent/file.json",
        })
        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "error" in response

    @pytest.mark.asyncio
    async def test_list_rulesets(self, server_params):
        result = await self._call_tool(server_params, "list_rulesets", {})
        assert len(result.content) == 1

        data = json.loads(result.content[0].text)
        assert "core_rulesets" in data
        assert "custom_rulesets" in data
        assert len(data["core_rulesets"]) >= 1
        core_keys = [rs["key"] for rs in data["core_rulesets"]]
        assert "epanet_core" in core_keys

    @pytest.mark.asyncio
    async def test_get_ruleset_details_epanet_core(self, server_params):
        result = await self._call_tool(server_params, "get_ruleset_details", {
            "ruleset_key": "epanet_core",
        })
        assert len(result.content) == 1

        data = json.loads(result.content[0].text)
        assert data["key"] == "epanet_core"
        assert data["type"] == "core"
        assert "component_rules" in data
        assert "network_rules" in data
        assert len(data["component_rules"]) > 0

    @pytest.mark.asyncio
    async def test_get_ruleset_details_milp(self, server_params):
        result = await self._call_tool(server_params, "get_ruleset_details", {
            "ruleset_key": "milp",
        })
        assert len(result.content) == 1

        data = json.loads(result.content[0].text)
        assert data["key"] == "milp"
        assert data["type"] == "custom"

    @pytest.mark.asyncio
    async def test_get_ruleset_details_filter_component_type(self, server_params):
        result = await self._call_tool(server_params, "get_ruleset_details", {
            "ruleset_key": "epanet_core",
            "component_type": "WNTREPANETNode",
        })
        data = json.loads(result.content[0].text)
        for rule in data["component_rules"]:
            assert "WNTREPANETNode" in rule["component_types"]

    @pytest.mark.asyncio
    async def test_get_ruleset_details_unknown(self, server_params):
        result = await self._call_tool(server_params, "get_ruleset_details", {
            "ruleset_key": "nonexistent",
        })
        data = json.loads(result.content[0].text)
        assert "error" in data
        assert "nonexistent" in data["error"]

    @pytest.mark.asyncio
    async def test_check_inp_well_formed(self, server_params):
        result = await self._call_tool(server_params, "check_inp", {
            "file_path": "epanetparser/networks/core/Net1.inp",
        })
        payload = json.loads(result.content[0].text)
        assert payload["well_formed"] is True
        assert payload["issues"] == []

    @pytest.mark.asyncio
    async def test_check_inp_malformed(self, server_params):
        result = await self._call_tool(server_params, "check_inp", {
            "file_path": "tests/data/malformed_network.inp",
        })
        payload = json.loads(result.content[0].text)
        assert payload["well_formed"] is False
        assert len(payload["issues"]) >= 1
        for issue in payload["issues"]:
            assert issue["validation_layer"] == "structural"
            assert "error_code" in issue["context"]
            assert "line_number" in issue["context"]
            assert "section" in issue["context"]

    @pytest.mark.asyncio
    async def test_validate_static_all_issues_are_static(self, invalid_network_path, server_params):
        result = await self._call_tool(server_params, "validate_static", {
            "file_path": invalid_network_path,
        })
        report = json.loads(result.content[0].text)
        assert report["is_valid"] is False
        assert len(report["issues"]) > 0
        assert all(issue["validation_layer"] == "static" for issue in report["issues"])

    @requires_wntr
    @pytest.mark.asyncio
    async def test_validate_simulation_reports_simulation_issues(self, server_params):
        result = await self._call_tool(server_params, "validate_simulation", {
            "file_path": "tests/data/simulation_failing_network.inp",
        })
        assert result.isError is False
        report = json.loads(result.content[0].text)
        sim_issues = [
            issue for issue in report["issues"]
            if issue["validation_layer"] == "simulation"
        ]
        assert len(sim_issues) >= 1

    @pytest.mark.asyncio
    async def test_validate_simulation_without_wntr_returns_actionable_error(self):
        """The impl must fail cleanly, not with a traceback, when WNTR is absent.

        A ``None`` entry in ``sys.modules`` makes ``import wntr`` raise
        ``ImportError`` without touching the installed package, so the lazy
        import path can be exercised deterministically in-process.
        """
        import sys

        from epanetparser.core.mcp_server import _validate_simulation_impl
        from mcp.types import CallToolResult

        had_wntr = sys.modules.get("wntr")
        sys.modules["wntr"] = None
        try:
            result = await _validate_simulation_impl(
                file_path="epanetparser/networks/core/Net1.inp",
            )
        finally:
            if had_wntr is not None:
                sys.modules["wntr"] = had_wntr
            else:
                sys.modules.pop("wntr", None)

        assert isinstance(result, CallToolResult)
        assert result.isError is True
        assert "simulation" in result.content[0].text
        assert "pip install epanetparser[simulation]" in result.content[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])