"""Tests for main module."""

import yaml
from dataclasses import asdict
from unittest.mock import patch, MagicMock
from io import StringIO

from epanetparser import main as main_module
from epanetparser.core.logger_setup import LoggingConfig


class TestMainModule:
    """Tests for main module entry point."""

    def test_logging_config_yaml_structure(self):
        """Test that LoggingConfig produces valid YAML with expected keys."""
        config = LoggingConfig()
        yaml_config = yaml.safe_dump(asdict(config), sort_keys=False)
        
        parsed = yaml.safe_load(yaml_config)
        
        # Check for expected keys from LoggingConfig
        assert "level" in parsed
        assert "log_format" in parsed
        assert "datefmt" in parsed
        assert "show_time" in parsed

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        import logging
        config = LoggingConfig()
        
        # Basic validation that config can be created
        assert config is not None
        assert config.level == logging.DEBUG  # Actual default is DEBUG
        assert config.show_time is True

    def test_yaml_config_is_valid_yaml(self):
        """Test that the YAML config produced is valid YAML."""
        config = LoggingConfig()
        yaml_str = yaml.safe_dump(asdict(config), sort_keys=False)
        
        # Should not raise
        parsed = yaml.safe_load(yaml_str)
        assert isinstance(parsed, dict)

    def test_main_module_has_expected_exports(self):
        """Test main module has expected attributes."""
        assert hasattr(main_module, "console")
        assert hasattr(main_module, "config")
        assert isinstance(main_module.config, LoggingConfig)

    def test_main_module_code_execution(self, mocker):
        """Test that main module top-level code creates expected objects."""
        # The module top-level code runs on import
        # Verify the objects exist
        assert main_module.console is not None
        assert main_module.config is not None
        assert main_module.yaml_config is not None
        assert main_module.panel is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])