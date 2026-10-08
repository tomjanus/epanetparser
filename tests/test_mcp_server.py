"""Tests for MCP server."""

import json
import pytest
from pathlib import Path

# Skip if mcp not installed
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not MCP_AVAILABLE, reason="mcp package not installed")


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
        return StdioServerParameters(
            command="epanetparser-mcp",
            args=[],
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
        assert "issues[0]{code,message,severity,rule_id,ruleset_key" in text

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])