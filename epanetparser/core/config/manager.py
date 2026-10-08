"""Configuration management for epanetparser.

This module provides the ConfigLoader class which handles all aspects of
application configuration including:

- Locating user-specific configuration files using platform-appropriate directories
- Loading package default configuration from resources
- Merging user configuration with defaults (user settings take precedence)
- Constructing Config instances with merged configuration

The configuration system uses YAML files and follows a two-tier approach:

1. **Package defaults**: Bundled with the package in default_config.yaml
2. **User overrides**: Stored in platform-specific user config directory

No user configuration file is created. If the user file is absent, the packaged
defaults are used unchanged; if it is present, its contents are merged
recursively on top of the defaults. A user file containing only a subset of
keys is valid and overrides only those keys.

Examples
--------
>>> from epanetparser.core.config.manager import ConfigLoader
>>> manager = ConfigLoader()
>>> config = manager.load()
>>> print(config.get('setting_name'))

See Also
--------
epanetparser.core.config.config : Config class for accessing configuration values
"""
try:
    from importlib.resources.abc import Traversable
except ImportError:
    from importlib.abc import Traversable
from typing import Any
from pathlib import Path
from importlib.resources import files
import yaml
from platformdirs import user_config_dir
from epanetparser.core.config import Config, ConfigError
from epanetparser.core.logger_setup import get_logger


logger = get_logger(__name__)


def get_config(
        user_config_path: Path | None = None,
        initialize_from_defaults: bool = True,
        override: bool = False) -> Config:
    """Get the merged configuration from package defaults and user overrides.

    Parameters
    ----------
    user_config_path : Path | None, optional
        Path to the user configuration file. If not provided, the default
        user configuration directory is used.
    initialize_from_defaults : bool, default=True
        Whether to initialize the configuration from defaults.
    override : bool, default=False
        Whether to overwrite an existing user configuration file with defaults.

    Notes
    -----
    If no user configuration exists, only packaged defaults are used. The merge
    operation is performed recursively, allowing users to override specific
    nested values without replacing entire sections. The user file is read and
    parsed exactly once. If the user configuration file cannot be read, contains 
    invalid YAML, or does not have a mapping at its root, a ConfigError is raised.

    Returns
    -------
    Config
        Configuration object composed of defaults and user overrides.
    """
    manager = ConfigLoader(
        user_config_path,
        initialize_from_defaults=initialize_from_defaults,
        override=override
    )
    return manager.load()


def _is_file_valid_yaml(file_path: Path) -> bool:
    """Check if a file exists and contains valid YAML.

    Parameters
    ----------
    file_path : Path
        Path to the file to check.

    Returns
    -------
    bool
        True if the file exists and contains valid YAML, False otherwise.
    """
    if not file_path.exists() or not file_path.is_file():
        return False
    try:
        with file_path.open("r", encoding="utf8") as f:
            yaml.safe_load(f)
        return True
    except (OSError, yaml.YAMLError):
        return False


class ConfigLoader:
    """Load package and user configuration.
    
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
    >>> loader = ConfigLoader()
    >>> config = loader.load()  # Load configuration
    >>> path = loader.config_path  # Location of the cofiguration file
    """
    APP_NAME = "epanetparser"

    def __init__(
            self,
            config_path: Path | None = None,
            initialize_from_defaults: bool = True,
            override: bool = False
        ) -> None:
        """Initialize the configuration loader.

        Sets up internal state and determines the user configuration file path.

        Parameters
        ----------
        config_path : Path or None, default=None
            Explicit path to the user configuration file. When given, it is
            stored verbatim: no existence or validity check is made and no
            redirection to the platform configuration directory occurs. When
            None, the platform-specific user configuration path is used.
        initialize_from_defaults : bool, default=True
            Whether to initialize the configuration from defaults. If False,
            the loader will not create a user configuration file if it does not exist.
        override : bool, default=False
            Whether to overwrite an existing user configuration file with defaults.

        Notes
        -----
        Uses platformdirs to determine the appropriate user config directory
        based on the operating system (Linux: ~/.config/epanetparser/,
        macOS: ~/Library/Application Support/epanetparser/, Windows: %APPDATA%).

        The configuration directory is not created here. Nothing reads it
        unless it contains a file, and creating it would make importing
        epanetparser fail on a read-only HOME.
        """
        self.config_init(
            config_path=config_path,
            initialize_from_defaults=initialize_from_defaults,
            override=override
        )

    def config_init(
            self,
            config_path: Path | None = None,
            initialize_from_defaults: bool = True,
            override: bool = False) -> None:
        """Initialize the configuration system from package defaults.

        This method is called automatically on first import of epanetparser
        to ensure that the configuration system is ready for use. It loads
        the default configuration and prepares the ConfigLoader for merging
        with user overrides.

        Parameters
        ----------
        config_path : Path or None, default=None
            Explicit path to the user configuration file. If None, the default
            user configuration directory is used.
        initialize_from_defaults : bool, default=True
            Whether to initialize the configuration from defaults.
        override : bool, default=False
            Whether to override an existing user configuration file.

        Notes
        -----
        This method is idempotent: calling it multiple times has no effect
        after the first successful initialization.

        The configuration directory is not created here. Nothing reads it
        unless it contains a file, and creating it would make importing
        epanetparser fail on a read-only HOME.
        """
        # Load defaults to ensure they are available for merging with user config
        default_config_dict = self._load_defaults()
        if config_path:
            self._config_path = Path(config_path)
        else:
            if not initialize_from_defaults:
                raise ValueError(
                    "Cannot initialize ConfigLoader without defaults or user path."
                )
            self._config_path = (
                Path(user_config_dir(self.APP_NAME)) / "config.yaml"
            )
        # Note: The configuration directory and file are NOT created here.
        # They are only created when explicitly requested via create_user_config()
        # or when override=True is used with a method that creates the file.

    @property
    def config_dir(self) -> Path:
        return self._config_path.parent
        
    @property
    def config_path(self) -> Path:
        return self._config_path
    
    @property
    def packaged_config_path(self) -> Traversable:
        """Get path to the default configuration resource.
        
        Returns
        -------
        Traversable
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
        
    def load(self) -> Config:
        """Load application configuration with user overrides.

        Loads the default package configuration and merges it with user-specific
        configuration if available. User settings take precedence over defaults.

        Returns
        -------
        Config
            Configuration with merged settings.

        Raises
        ------
        ConfigError
            If the user configuration file cannot be read, contains invalid
            YAML, or does not have a mapping at its root.

        Notes
        -----
        If no user configuration exists, only packaged defaults are used.
        The merge operation is performed recursively, allowing users to
        override specific nested values without replacing entire sections.
        The user file is read and parsed exactly once.

        Examples
        --------
        >>> manager = ConfigLoader()
        >>> config = manager.load()
        >>> value = config.get('section.subsection.key')
        """
        _config_dict = self._load_defaults()
        _user_path = self.config_path
        _config = _config_dict
        if _user_path.exists() and _user_path.is_file():
            try:
                with _user_path.open("r", encoding="utf8") as file_handle:
                    user_dict = yaml.safe_load(file_handle)
            except OSError as err:
                raise ConfigError(
                    f"Unable to read user configuration from '{_user_path}'."
                ) from err
            except yaml.YAMLError as err:
                _mark = getattr(err, "problem_mark", None)
                _location = (
                    f" at line {_mark.line + 1}, column {_mark.column + 1}"
                    if _mark is not None else ""
                )
                raise ConfigError(
                    f"Invalid YAML in user configuration '{_user_path}'{_location}: "
                    f"{err}"
                ) from err
            if user_dict is not None:
                if not isinstance(user_dict, dict):
                    raise ConfigError(
                        f"Root of user configuration '{_user_path}' must be a "
                        f"mapping, got {type(user_dict).__name__}."
                    )
                logger.debug(
                    "Merging user configuration from '%s' with defaults.",
                    _user_path,
                )
                _config = self._deep_merge(_config_dict, user_dict)
        _config = Config.from_dict(_config)
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
        with self.packaged_config_path.open("r", encoding="utf8") as f_handle:
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
        >>> ConfigLoader._deep_merge(base, override)
        {'a': 1, 'b': {'c': 99, 'd': 3}}
        """
        if base == override or not override:
            return base
        _merged_config = dict(base)
        for k, v in override.items():
            if (
                k in _merged_config
                and isinstance(_merged_config[k], dict)
                and isinstance(v, dict)
            ):
                _merged_config[k] = ConfigLoader._deep_merge(_merged_config[k], v)
            else:
                _merged_config[k] = v
        return _merged_config
