"""Utilities for loading and accessing YAML configuration for `epanetparser`.

This module provides :class:`Config`, a lightweight wrapper around
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
    """ Protocol for classes that can be instantiated from a mapping, such as
    dict, ChainMap or any object implementing the mapping interface."""
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> T: ... # pylint: disable=missing-function-docstring


class ConfigError(Exception):
    """Exception raised for configuration-related errors.

    This includes invalid YAML, missing configuration sections,
    and invalid configuration structure.
    """


class Config(Mapping[str, Any]):
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
    >>> config["example_section"]
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
        if not isinstance(data, Mapping):
            raise ConfigError("Configuration root must be a dictionary/mapping.")
        self._data = MappingProxyType(data)
        
    def __iter__(self) -> Iterator[str]:
        return iter(self._data)
    
    def __len__(self) -> int:
        return len(self._data)
    
    def __getitem__(self, key: str) -> Any:
        """Return a top-level configuration value."""
        return self._data[key]
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({dict(self._data)!r})"
        )

    def __rich__(self):
        return Pretty(dict(self._data))
    
    def to_yaml(self) -> str:
        """Serialize the configuration to YAML format.
        
        Useful for exporting, debugging, or saving configuration.

        Returns
        -------
        str
            YAML representation of the configuration.
        
        Examples
        --------
        >>> config = Config.from_dict({'key': 'value'})
        >>> print(config.to_yaml())
        key: value
        """
        return yaml.safe_dump(dict(self._data), sort_keys=False)

    def to_file(self, path: str | Path) -> None:
        """Write the configuration to a YAML file.

        Parameters
        ----------
        path
            Path to the output YAML file.

        Raises
        ------
        OSError
            If the file cannot be written.
        
        Examples
        --------
        >>> config = Config.from_dict({'key': 'value'})
        >>> config.to_file("output.yaml")
        """
        path = Path(path)
        with path.open("w", encoding="utf8") as f:
            yaml.safe_dump(dict(self._data), f, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Config:
        """Load configuration from a dictionary.

        Parameters
        ----------
        data
            Configuration data mapping.

        Returns
        -------
        Config
            Loaded configuration.
        """
        return cls(data)
    
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
        >>> config_dict = {'db': {'host': 'localhost', 'port': 5432}}
        >>> config = Config.from_dict(config_dict)
        >>> db_config = config.section('db')
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
        >>> config_dict = {'database': {'host': 'localhost'}}
        >>> config = Config.from_dict(config)
        >>> db = config.instantiate('database', DatabaseConfig)  # doctest: +SKIP
        """
        return cls.from_dict(self.section(key))
