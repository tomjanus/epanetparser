"""Configuration management for epanetparser.

This module provides the ConfigManager class which handles all aspects of
application configuration including:

- Locating user-specific configuration files using platform-appropriate directories
- Creating default configuration on first run
- Loading package default configuration from resources
- Merging user configuration with defaults (user settings take precedence)
- Constructing ConfigLoader instances with merged configuration

The configuration system uses YAML files and follows a two-tier approach:

1. **Package defaults**: Bundled with the package in default_config.yaml
2. **User overrides**: Stored in platform-specific user config directory

User configuration is created automatically on first run by copying the package
defaults. Users can then customize settings, and their changes will be merged
with defaults on subsequent runs.

Examples
--------
>>> from epanetparser.core.config.manager import ConfigManager
>>> manager = ConfigManager()
>>> config = manager.load()
>>> print(config.get('setting_name'))

See Also
--------
epanetparser.core.config.config : ConfigLoader class for accessing configuration values
"""
from typing import Optional, Any
from pathlib import Path
from importlib.resources import files
import shutil
import yaml
from platformdirs import user_config_dir
from epanetparser.core.config import Config


class ConfigManager:
    """Manage package and user configuration.
    
    Handles loading, merging, and managing configuration from both package
    defaults and user-specific overrides. Automatically determines the
    appropriate user configuration directory based on the operating system.
    
    Attributes
    ----------
    APP_NAME : str
        Application name used for configuration directory identification.
    
    Notes
    -----
    This class uses platformdirs to locate the user configuration directory,
    ensuring cross-platform compatibility (Linux, macOS, Windows).
    
    The configuration hierarchy is:
    1. Package defaults (always loaded)
    2. User overrides (if present, merged on top of defaults)
    
    Examples
    --------
    >>> manager = ConfigManager()
    >>> config = manager.load()  # Load configuration
    >>> path = manager.ensure_user_config()  # Create user config if needed
    """
    APP_NAME = "epanetparser"

    def __init__(self):
        """Initialize the configuration manager.
        
        Sets up internal state and determines the user configuration file path
        based on the platform-specific user configuration directory.
        """
        self._config = None
        self._user_config_path: Path = \
            Path(user_config_dir(self.APP_NAME)) / "default_config.yaml"
        self.create_user_config()  # Ensure user config exists on initialization
        
    @property
    def user_config_path(self) -> Optional[Path]:
        """Get path to user configuration file if it exists.
        
        Returns
        -------
        Path or None
            Path to the user configuration file if it exists, None otherwise.
        
        Notes
        -----
        Uses platformdirs to determine the appropriate user config directory
        based on the operating system (Linux: ~/.config/epanetparser/,
        macOS: ~/Library/Application Support/epanetparser/, Windows: %APPDATA%).
        """
        if self._user_config_path.exists():
            return self._user_config_path
        return None
    
    @property
    def default_config_resource(self) -> Path:
        """Get path to the default configuration resource.
        
        Returns
        -------
        Path
            Path to default_config.yaml within the package resources.
        
        Notes
        -----
        This file is bundled with the package and serves as the template
        for creating user configuration files on first run.
        """
        return (
            files("epanetparser.core.config")
            .joinpath("default_config.yaml")
        )
        
    def create_user_config(self, overwrite: bool = False) -> Path:
        """Create user configuration file if it does not exist.
        
        Checks if the user configuration file exists. If not, creates the
        necessary directories and copies the default configuration from
        package resources to the user configuration path.
        
        Parameters
        ----------
        overwrite : bool, default=False
            If True, overwrite existing configuration file with package defaults.
        
        Returns
        -------
        Path
            Path to the user configuration file (created or existing).
        
        Examples
        --------
        >>> manager = ConfigManager()
        >>> config_path = manager.ensure_user_config()
        >>> print(f"Config file: {config_path}")
        """
        _destination = self._user_config_path
        if _destination.exists() and not overwrite:
            return _destination
        _destination.parent.mkdir(parents=True, exist_ok=True)
        with (
            self.default_config_resource.open("rb") as src,
            _destination.open("wb") as dst,
        ):
            shutil.copyfileobj(src, dst)
        return _destination
        
    def load(self) -> Config:
        """Load application configuration with user overrides.
        
        Loads the default package configuration and merges it with user-specific
        configuration if available. User settings take precedence over defaults.

        Returns
        -------
        ConfigLoader
            Configuration loader instance with merged settings.
        
        Notes
        -----
        If no user configuration exists, only packaged defaults are used.
        The merge operation is performed recursively, allowing users to
        override specific nested values without replacing entire sections.
        
        Examples
        --------
        >>> manager = ConfigManager()
        >>> config = manager.load()
        >>> value = config.get('section.subsection.key')
        """
        _config = self._load_defaults()
        if self._user_config_path.exists():
            with self.user_config_path.open("r", encoding="utf8") as file_handle:
                user = yaml.safe_load(file_handle) or {}
            _config = self._deep_merge(_config, user)
        return Config(_config)

    def _load_defaults(self) -> dict[str, Any]:
        """Load default configuration from package resources.
        
        Returns
        -------
        dict[str, Any]
            Default configuration as a dictionary.
        
        Notes
        -----
        This is an internal method that reads the bundled default_config.yaml
        file using importlib.resources for reliable cross-platform access.
        """
        with self.default_config_resource.open("r", encoding="utf8") as f_handle:
            return yaml.safe_load(f_handle) or {}

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge two dictionaries.
        
        Merges user configuration with default configuration. User values
        take precedence. Nested dictionaries are merged recursively, allowing
        partial overrides of configuration sections.

        Parameters
        ----------
        base : dict[str, Any]
            Base dictionary (typically default configuration).
        override : dict[str, Any]
            Dictionary with override values (typically user configuration).

        Returns
        -------
        dict[str, Any]
            Merged dictionary with override values taking precedence.
        
        Notes
        -----
        For nested dictionaries, the merge is recursive. For non-dict values,
        the override value completely replaces the base value.
        
        Examples
        --------
        >>> base = {'a': 1, 'b': {'c': 2, 'd': 3}}
        >>> override = {'b': {'c': 99}}
        >>> ConfigManager._deep_merge(base, override)
        {'a': 1, 'b': {'c': 99, 'd': 3}}
        """
        _merged_config = dict(base)
        for k, v in override.items():
            if (
                k in _merged_config
                and isinstance(_merged_config[k], dict)
                and isinstance(v, dict)
            ):
                _merged_config[k] = ConfigManager._deep_merge(_merged_config[k], v)
            else:
                _merged_config[k] = v
        return _merged_config


if __name__ == "__main__":
    pass
