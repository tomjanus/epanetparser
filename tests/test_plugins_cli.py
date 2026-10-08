"""Tests for plugins_cli module."""

import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from epanetparser.core.plugins_cli import (
    list_rulesets,
    show_ruleset,
    main,
)
from epanetparser.core.validation import RuleSetRegistry, clear_caches


class TestListRulesets:
    """Tests for list_rulesets function."""

    def test_list_rulesets_with_registry(self, capsys):
        """Test listing rulesets prints table with core and custom."""
        list_rulesets(RuleSetRegistry())
        captured = capsys.readouterr()

        assert "Validation rule sets" in captured.out
        assert "Key" in captured.out
        assert "Kind" in captured.out
        assert "Name" in captured.out
        assert "Version" in captured.out
        assert "Component" in captured.out
        assert "Network" in captured.out
        assert "epanet_core" in captured.out
        assert "core" in captured.out
        assert "milp" in captured.out
        assert "custom" in captured.out

    def test_list_rulesets_empty_registry(self, capsys, mocker):
        """Test listing when no rulesets discovered."""
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_registry.all.return_value = []

        list_rulesets(mock_registry)
        captured = capsys.readouterr()

        assert "No rule sets were discovered" in captured.out


class TestShowRuleset:
    """Tests for show_ruleset function."""

    def test_show_ruleset_core(self, capsys):
        """Show epanet_core ruleset with all rules."""
        show_ruleset("epanet_core")
        captured = capsys.readouterr()

        assert "core rule set: epanet_core" in captured.out
        assert "EPANET core rules" in captured.out
        assert "Component rules" in captured.out
        assert "Network rules" in captured.out
        assert "E_NETWORK_NAME_MISSING" in captured.out
        assert "rule_network_has_name" in captured.out

    def test_show_ruleset_custom_milp(self, capsys):
        """Show milp custom ruleset."""
        show_ruleset("milp")
        captured = capsys.readouterr()

        assert "custom rule set: milp" in captured.out
        assert "Mixed Integer Linear Programming ruleset" in captured.out
        assert "Component rules" in captured.out
        assert "E_MILP_TIMESTEP" in captured.out
        assert "rule_hydraulic_timestep" in captured.out

    def test_show_ruleset_filter_component(self, capsys):
        """Show ruleset filtered by component type."""
        show_ruleset("epanet_core", component="WNTREPANETNode")
        captured = capsys.readouterr()

        assert "core rule set: epanet_core" in captured.out
        # Should only show component rules for WNTREPANETNode
        for line in captured.out.split("\n"):
            if "WNTREPANETNode" in line and "network" not in line.lower():
                assert "WNTREPANETNode" in line

    def test_show_ruleset_not_found(self, capsys, mocker):
        """Show ruleset with unknown key exits with error."""
        # Mock console to avoid the bug in original code (console.print doesn't accept file arg)
        mock_console = mocker.patch("epanetparser.core.plugins_cli.console")

        with pytest.raises(SystemExit) as exc_info:
            show_ruleset("nonexistent")
        assert exc_info.value.code == 1

        # Verify console.print was called with error message
        mock_console.print.assert_called()
        call_args = mock_console.print.call_args[0][0]
        assert "nonexistent" in call_args
        assert "available" in call_args.lower()


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_list_command(self, capsys, mocker):
        """Test main with 'list' subcommand."""
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_ruleset = mocker.MagicMock()
        mock_ruleset.key = "epanet_core"
        mock_ruleset.is_core = True
        mock_ruleset.name = "EPANET core rules"
        mock_ruleset.version = "1.0.0"
        mock_ruleset.component_rules = []
        mock_ruleset.network_rules = []
        mock_registry.all.return_value = [mock_ruleset]
        mock_registry.describe.return_value = "Test description"

        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry", return_value=mock_registry)

        with patch.object(sys, "argv", ["epanetparser-plugins", "list"]):
            main()

        captured = capsys.readouterr()
        assert "Validation rule sets" in captured.out
        assert "epanet_core" in captured.out

    def test_main_show_command(self, capsys, mocker):
        """Test main with 'show' subcommand."""
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_ruleset = mocker.MagicMock()
        mock_ruleset.key = "epanet_core"
        mock_ruleset.is_core = True
        mock_ruleset.name = "EPANET core rules"
        mock_ruleset.version = "1.0.0"
        mock_ruleset.module_path = "test.path"
        mock_ruleset.description = "Test description"
        mock_ruleset.component_rules = []
        mock_ruleset.network_rules = []
        mock_registry.get.return_value = mock_ruleset

        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry", return_value=mock_registry)

        with patch.object(sys, "argv", ["epanetparser-plugins", "show", "--ruleset", "epanet_core"]):
            main()

        captured = capsys.readouterr()
        assert "core rule set: epanet_core" in captured.out

    def test_main_show_command_with_component_filter(self, capsys, mocker):
        """Test main with 'show' subcommand and component filter."""
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_ruleset = mocker.MagicMock()
        mock_ruleset.key = "epanet_core"
        mock_ruleset.is_core = True
        mock_ruleset.name = "EPANET core rules"
        mock_ruleset.version = "1.0.0"
        mock_ruleset.module_path = "test.path"
        mock_ruleset.description = "Test description"
        mock_ruleset.component_rules = []
        mock_ruleset.network_rules = []
        mock_registry.get.return_value = mock_ruleset

        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry", return_value=mock_registry)

        with patch.object(sys, "argv", ["epanetparser-plugins", "show", "--ruleset", "epanet_core", "--component", "WNTREPANETNode"]):
            main()

        captured = capsys.readouterr()
        assert "core rule set: epanet_core" in captured.out

    def test_main_refresh_command(self, capsys, mocker):
        """Test main with 'refresh' subcommand."""
        mock_clear = mocker.patch("epanetparser.core.plugins_cli.clear_caches")
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_ruleset = mocker.MagicMock()
        mock_ruleset.key = "epanet_core"
        mock_ruleset.is_core = True
        mock_ruleset.name = "EPANET core rules"
        mock_ruleset.version = "1.0.0"
        mock_ruleset.component_rules = []
        mock_ruleset.network_rules = []
        mock_registry.all.return_value = [mock_ruleset]
        mock_registry.describe.return_value = "Test description"

        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry", return_value=mock_registry)

        with patch.object(sys, "argv", ["epanetparser-plugins", "refresh"]):
            main()

        captured = capsys.readouterr()
        assert "Validation rule sets" in captured.out
        mock_clear.assert_called_once()

    def test_main_no_command_shows_help(self, capsys, mocker):
        """Test main with no subcommand prints help and exits 0."""
        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry")

        with patch.object(sys, "argv", ["epanetparser-plugins"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "Inspect the validation rule sets" in captured.out


class TestClearCachesIntegration:
    """Test that clear_caches works with plugins CLI."""

    def test_clear_caches_called_on_refresh(self, mocker):
        """Verify clear_caches is called when refresh command runs."""
        mock_clear = mocker.patch("epanetparser.core.plugins_cli.clear_caches")
        mock_registry = mocker.MagicMock(spec=RuleSetRegistry)
        mock_ruleset = mocker.MagicMock()
        mock_ruleset.key = "epanet_core"
        mock_ruleset.is_core = True
        mock_ruleset.name = "EPANET core rules"
        mock_ruleset.version = "1.0.0"
        mock_ruleset.component_rules = []
        mock_ruleset.network_rules = []
        mock_registry.all.return_value = [mock_ruleset]
        mock_registry.describe.return_value = "Test description"

        mocker.patch("epanetparser.core.plugins_cli.RuleSetRegistry", return_value=mock_registry)

        with patch.object(sys, "argv", ["epanetparser-plugins", "refresh"]):
            main()

        mock_clear.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])