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
epanetparser.core.config.loader : ConfigLoader class for accessing configuration values
"""
from typing import Optional, Any
from pathlib import Path
from importlib.resources import files
import shutil
import yaml
from platformdirs import user_config_dir
from epanetparser.core.config.loader import ConfigLoader


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
            Path(user_config_dir(self.APP_NAME)) / "config.yaml"
        
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
        
    def ensure_user_config(self, overwrite: bool = False) -> Path:
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
        _destination = self.user_config_path
        if _destination and not overwrite:
            return _destination
        _destination.parent.mkdir(parents=True, exist_ok=True)
        with (
            self.default_config_resource.open("rb") as src,
            _destination.open("wb") as dst,
        ):
            shutil.copyfileobj(src, dst)
        return _destination
        
    def load(self) -> ConfigLoader:
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
        if self.user_config_path.exists():
            with self.user_config_path.open("r", encoding="utf8") as file_handle:
                user = yaml.safe_load(file_handle) or {}
            _config = self._deep_merge(_config, user)
        return ConfigLoader(_config)

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
    from rich import print as rprint
    from rich.panel import Panel
    from rich.console import Console
    
    console = Console()
    
    rprint("[bold yellow]═══ ConfigManager Demo ═══[/bold yellow]\n")
    
    # Initialize manager
    manager = ConfigManager()
    
    # 1. Show configuration paths
    rprint("[bold cyan]1. Configuration Paths[/bold cyan]")
    rprint(f"   Default config resource: {manager.default_config_resource}")
    rprint(f"   User config location: {manager.user_config_path}")
    rprint(f"   User config exists: {manager.user_config_path is not None}\n")
    
    # 2. Load configuration (before ensuring user config exists)
    rprint("[bold cyan]2. Load Configuration (Package Defaults)[/bold cyan]")
    config = manager.load()
    rprint(f"   ConfigLoader type: {type(config).__name__}")
    config_keys = list(config.data.keys())
    rprint(f"   Configuration sections: {config_keys}\n")
    
    # 3. Ensure user config exists
    rprint("[bold cyan]3. Ensure User Configuration Exists[/bold cyan]")
    user_config_path = manager.ensure_user_config()
    rprint(f"   User config path: {user_config_path}")
    rprint(f"   File exists: {user_config_path.exists()}\n")
    
    # 4. Reload configuration (now with user config)
    rprint("[bold cyan]4. Reload Configuration (With User Overrides)[/bold cyan]")
    config = manager.load()
    rprint(f"   ConfigLoader loaded successfully")
    rprint(f"   Total sections: {len(config.data)}\n")
    
    # 5. Show example configuration access
    rprint("[bold cyan]5. Example Configuration Access[/bold cyan]")
    # Show a sample of the configuration structure (first 3 sections)
    sample_config = dict(list(config.data.items())[:3])
    if sample_config:
        rprint("   Sample configuration (first 3 sections):")
        yaml_output = yaml.dump(sample_config, default_flow_style=False, sort_keys=False)
        console.print(Panel(yaml_output, title="Configuration Sample", border_style="green"))
    else:
        rprint("   [dim]No configuration data available[/dim]")
    
    # 6. Show how to access specific values
    rprint("\n[bold cyan]6. Accessing Configuration Values[/bold cyan]")
    if config_keys:
        first_key = config_keys[0]
        rprint(f"   Example: config.data['{first_key}']")
        try:
            value = config.data[first_key]
            rprint(f"   Type: {type(value).__name__}")
            if isinstance(value, dict):
                rprint(f"   Keys: {list(value.keys())[:5]}")  # Show first 5 keys
        except Exception as e:
            rprint(f"   [red]Error: {e}[/red]")
    
    rprint("\n[bold green]✓ ConfigManager demo completed successfully![/bold green]")