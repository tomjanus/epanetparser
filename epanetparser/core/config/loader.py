"""Utilities for loading and accessing YAML configuration for `epanetparser`.

This module provides :class:`ConfigLoader`, a lightweight wrapper around
configuration dictionaries loaded from YAML files. It offers convenient access
to nested configuration sections and supports instantiating typed configuration
objects via their ``from_dict`` class methods.

The loader intentionally separates configuration parsing from configuration
management. Locating configuration files, merging defaults with user
configuration, and other application-specific concerns should be handled by
``ConfigManager` in epanetparser.core.config.manager`.
"""
from __future__ import annotations
from pathlib import Path
from typing import TypeVar, Protocol, Any
from types import MappingProxyType
from collections.abc import Mapping, Iterator
import yaml
from rich.pretty import Pretty


T = TypeVar("T")


class FromDict(Protocol[T]): # pylint: disable=too-few-public-methods
    """ Protocol for classes that can be instantiated from a dictionary. 
    
    By design each configuration class should implement a class method `from_dict` 
    that takes a dictionary and returns an instance of the class. This way we can
    have individual specialized configuration classes that configure specific
    behaviour of epanetparser, e.g. RuleDiscovery, etc.
    """
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> T: # pylint: disable=missing-function-docstring
        ...


class ConfigError(Exception):
    """Exception raised for configuration-related errors.

    This includes invalid YAML, missing configuration sections,
    and invalid configuration structure.
    """


class ConfigLoader(Mapping[str, Any]):
    """Provide read-only access to configuration data and load configuration
    data from YAML files.

    The loader provides a lightweight wrapper around ``yaml.safe_load`` with
    validation and convenient access to nested configuration sections.

    Notes
    -----
    This class intentionally returns dictionaries rather than domain objects.
    Converting dictionaries into application-specific objects should be handled
    by those objects (for example, ``ExampleConfig.from_dict()``).

    MappingProxyType only makes the top-level dictionary read-only. 
    For example
        loader.data["rule_discovery"]["base_paths"].append("foo")
        or
        loader.data["rule_discovery"]["mandatory_fields"] = [
            "field1", "field2"
        ]
    will still succeed. To make the entire configuration immutable, you would
    need to recursively convert all nested dictionaries and lists into immutable
    types (e.g., MappingProxyType for dicts, tuple for lists). This is
    not done here for simplicity, but could be implemented if needed.
    
    Examples
    --------
    >>> loader = ConfigLoader.from_file("config.yaml")
    >>> loader["example_section"]
    {'key1': ['value1'], ...}
    """

    def __init__(self, data: dict[str, Any]):
        """
        Parameters
        ----------
        data
            Parsed configuration dictionary.
            
        Attributes
        ----------
        _data : MappingProxyType
            Immutable mapping of the configuration data (only at top-level).
        """
        self._data = MappingProxyType(data)
        
    def __iter__(self) -> Iterator[str]:
        return iter(self._data)
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __getitem__(self, key: str) -> Any:
        """Return a top-level configuration value."""
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        """Return whether a key exists."""
        return key in self._data
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({dict(self._data)!r})"
        )

    def __rich__(self):
        return Pretty(dict(self._data))
            
    @property
    def data(self) -> Mapping[str, Any]:
        """Return the underlying configuration mapping."""
        return self._data
    
    def to_yaml(self) -> str:
        """Serialize the configuration to YAML format.
        
        Useful for exporting, debugging, or saving configuration.

        Returns
        -------
        str
            YAML representation of the configuration.
        
        Examples
        --------
        >>> loader = ConfigLoader.from_dict({'key': 'value'})
        >>> print(loader.to_yaml())
        key: value
        """
        return yaml.safe_dump(
            dict(self._data),
            sort_keys=False,
        )
        
    @classmethod
    def from_file(cls, path: str | Path) -> ConfigLoader:
        """Load configuration from a YAML file.

        Parameters
        ----------
        path
            Path to the YAML configuration file.

        Returns
        -------
        ConfigLoader
            Loaded configuration.

        Raises
        ------
        ConfigError
            If the file cannot be read or the root element is not a mapping.
        """
        path = Path(path)
        try:
            with path.open("r", encoding="utf8") as f:
                data = yaml.safe_load(f) or {}
        except OSError as err:
            raise ConfigError(f"Unable to read '{path}'.") from err
        except yaml.YAMLError as err:
            raise ConfigError(f"Invalid YAML in '{path}'.") from err
        if not isinstance(data, dict):
            raise ConfigError("Configuration root must be a dictionary.")
        return cls(data)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConfigLoader:
        """Load configuration from a dictionary.

        Parameters
        ----------
        data
            Configuration data mapping.

        Returns
        -------
        ConfigLoader
            Loaded configuration.

        Raises
        ------
        ConfigError
            If the root element is not a mapping.
        """
        if not isinstance(data, dict):
            raise ConfigError("Configuration root must be a dictionary.")
        return cls(data)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default.
        
        Provides safe access to configuration values, returning a default
        if the key is not present (similar to dict.get()).

        Parameters
        ----------
        key : str
            Configuration key.
        default : Any, optional
            Value returned if the key is not present. Defaults to None.

        Returns
        -------
        Any
            The configuration value or default.
        
        Examples
        --------
        >>> loader = ConfigLoader.from_dict({'present': 'value'})
        >>> loader.get('present')
        'value'
        >>> loader.get('missing', 'default')
        'default'
        """
        return self._data.get(key, default)
    
    def require(self, key: str) -> Any:
        """Get a required configuration value.
        
        Use this when a configuration value must be present. Raises an
        error if the key is missing, making configuration requirements explicit.

        Parameters
        ----------
        key : str
            Configuration key.

        Returns
        -------
        Any
            The configuration value.

        Raises
        ------
        ConfigError
            If the key is missing.
        
        Examples
        --------
        >>> loader = ConfigLoader.from_dict({'required': 'value'})
        >>> loader.require('required')
        'value'
        >>> loader.require('missing')  # doctest: +SKIP
        ConfigError: Missing required configuration section 'missing'.
        """
        if key not in self._data:
            raise ConfigError(
                f"Missing required configuration section '{key}'."
            )
        return self._data[key]
    
    def section(self, *keys: str) -> Mapping[str, Any]:
        """Get a nested configuration section.
        
        Navigate through nested configuration dictionaries using a sequence
        of keys. Returns an immutable mapping of the section.

        Parameters
        ----------
        *keys : str
            Sequence of nested keys to traverse.

        Returns
        -------
        Mapping[str, Any]
            Immutable mapping of the nested configuration section.

        Raises
        ------
        ConfigError
            If the path does not exist or does not refer to a mapping.
        
        Examples
        --------
        >>> config = {'db': {'host': 'localhost', 'port': 5432}}
        >>> loader = ConfigLoader.from_dict(config)
        >>> db_config = loader.section('db')
        >>> db_config['host']
        'localhost'
        """
        _path = ".".join(keys)
        _node = self._data
        for key in keys:
            if not isinstance(_node, Mapping):
                raise ConfigError(
                    f"'{_path}' is not a configuration section."
                )
            try:
                _node = _node[key]
            except KeyError as err:
                raise ConfigError(
                    f"Missing configuration section '{_path}'."
                ) from err
        if not isinstance(_node, Mapping):
            raise ConfigError(
                f"'{_path}' must be a mapping."
            )
        return MappingProxyType(_node)

    def instantiate(self, key: str, cls: type[FromDict[T]]) -> T:
        """Construct an object from a configuration section.
        
        Instantiates a typed configuration object by calling its ``from_dict``
        class method with the configuration section data.

        Parameters
        ----------
        key : str
            Name of the configuration section.
        cls : type[FromDict[T]]
            Class providing a ``from_dict`` class method.

        Returns
        -------
        T   
            Instantiated object.
        
        Examples
        --------
        >>> class DatabaseConfig:
        ...     @classmethod
        ...     def from_dict(cls, data):
        ...         return cls(**data)
        >>> config = {'database': {'host': 'localhost'}}
        >>> loader = ConfigLoader.from_dict(config)
        >>> db = loader.instantiate('database', DatabaseConfig)  # doctest: +SKIP
        """
        return cls.from_dict(self.section(key))
    
    
if __name__ == "__main__":
    from rich import print as rprint
    from rich.panel import Panel
    from rich.console import Console
    from rich.syntax import Syntax
    
    console = Console()
    
    rprint("[bold yellow]═══ ConfigLoader Demo ═══[/bold yellow]\n")
    
    # 1. Load from file
    rprint("[bold cyan]1. Loading Configuration from File[/bold cyan]")
    config_path = Path(__file__).parent / "default_config.yaml"
    rprint(f"   Loading from: {config_path}")
    loader = ConfigLoader.from_file(config_path)
    rprint(f"   Type: {type(loader).__name__}")
    rprint(f"   Sections: {list(loader.data.keys())}\n")
    
    # 2. Access configuration values
    rprint("[bold cyan]2. Accessing Configuration Values[/bold cyan]")
    rprint("   Using dictionary-style access:")
    if 'rule_discovery' in loader:
        rule_discovery = loader['rule_discovery']
        rprint(f"   loader['rule_discovery']: {type(rule_discovery).__name__}")
        rprint(f"   Keys: {list(rule_discovery.keys())[:3]}...\n")
    
    # 3. Using get() method
    rprint("[bold cyan]3. Using get() Method (with defaults)[/bold cyan]")
    value = loader.get('rule_discovery')
    rprint(f"   loader.get('rule_discovery'): Found ✓")
    missing = loader.get('nonexistent_key', 'default_value')
    rprint(f"   loader.get('nonexistent_key', 'default_value'): {missing!r}\n")
    
    # 4. Using require() method
    rprint("[bold cyan]4. Using require() Method (for mandatory keys)[/bold cyan]")
    try:
        required = loader.require('rule_discovery')
        rprint("   loader.require('rule_discovery'): Found ✓")
    except ConfigError as e:
        rprint(f"   [red]Error: {e}[/red]")
    
    try:
        loader.require('missing_required_key')
    except ConfigError as e:
        rprint(f"   loader.require('missing_required_key'): [yellow]ConfigError raised ✓[/yellow]\n")
    
    # 5. Accessing nested sections
    rprint("[bold cyan]5. Accessing Nested Configuration Sections[/bold cyan]")
    if 'rule_discovery' in loader:
        section = loader.section('rule_discovery')
        rprint(f"   loader.section('rule_discovery'):")
        rprint(f"   Type: {type(section).__name__}")
        rprint(f"   Keys: {list(section.keys())}\n")
    
    # 6. Serialize to YAML
    rprint("[bold cyan]6. Serializing to YAML[/bold cyan]")
    yaml_output = loader.to_yaml()
    # Show first few lines
    yaml_lines = yaml_output.split('\n')[:15]
    yaml_preview = '\n'.join(yaml_lines)
    syntax = Syntax(yaml_preview, "yaml", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="YAML Output (first 15 lines)", border_style="green"))
    rprint()
    
    # 7. Creating from dictionary
    rprint("[bold cyan]7. Creating ConfigLoader from Dictionary[/bold cyan]")
    sample_config = {
        'database': {
            'host': 'localhost',
            'port': 5432,
            'name': 'mydb'
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(message)s'
        }
    }
    sample_loader = ConfigLoader.from_dict(sample_config)
    rprint("   Created from dictionary:")
    rprint(f"   Sections: {list(sample_loader.data.keys())}")
    db_section = sample_loader.section('database')
    rprint(f"   database.host: {db_section['host']}")
    rprint(f"   database.port: {db_section['port']}\n")
    
    # 8. Immutability demonstration
    rprint("[bold cyan]8. Configuration Immutability[/bold cyan]")
    rprint("   The top-level mapping is immutable (MappingProxyType):")
    try:
        sample_loader.data['new_key'] = 'value'
    except TypeError as e:
        rprint(f"   [yellow]Attempting to add new key: TypeError raised ✓[/yellow]")
    rprint("   [dim](Note: nested structures are still mutable)[/dim]\n")
    
    # 9. Iteration support
    rprint("[bold cyan]9. Iteration Support[/bold cyan]")
    rprint("   ConfigLoader supports Mapping protocol:")
    rprint(f"   len(loader): {len(loader)}")
    rprint(f"   Keys: {list(loader.keys())}")
    rprint(f"   'rule_discovery' in loader: {'rule_discovery' in loader}\n")
    
    rprint("[bold green]✓ ConfigLoader demo completed successfully![/bold green]")