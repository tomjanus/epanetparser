"""Plugin system for extending EPANET component validation.

This module provides a plugin architecture that allows external
packages to register custom validation rules and warnings for 
EPANET components.

The plugin system supports:
- Automatic discovery via Python entry points
- Manual registration via decorators
- Type-safe validation functions
- Component-specific rules and warnings

Examples
--------
Register a custom rule for pipes::

    from epanetparser.plugins import register_rule
    
    @register_rule("WNTREPANETLink", "pipe_length_reasonable")
    def check_pipe_length(instance):
        if instance.type == "Pipe":
            length = instance.data.get("length", 0)
            assert length < 10000, "Pipe length exceeds 10km"

Create an installable plugin package::

    # In your plugin's pyproject.toml
    [project.entry-points."epanetparser.validation_plugins"]
    my_plugin = "my_plugin.validators:register_validators"
"""
from typing import List, Optional
import logging
import importlib.util
from pathlib import Path
import os
from .rule_registry import RuleRegistry

logger = logging.getLogger(__name__)

__version__ = '0.1.0'

# Global registry instance
_registry = RuleRegistry()


def register_rule(component_type: str, name: Optional[str] = None, replace: bool = False):
    """Decorator to register a validation rule.
    
    Parameters
    ----------
    component_type : str
        Name of the component class (e.g., 'WNTREPANETLink').
    name : str, optional
        Rule name. If None, uses the function name.
    replace : bool, optional
        If True, replace existing rule with same name. Default is False.
    
    Examples
    --------
    >>> @register_rule("WNTREPANETLink", "pipe_length_check")
    ... def validate_pipe_length(instance):
    ...     if instance.type == "Pipe":
    ...         assert instance.data.get("length", 0) > 0, "Length must be positive"
    """
    def decorator(func):
        rule_name = name or func.__name__
        _registry.register_rule(component_type, rule_name, func, replace=replace)
        return func
    return decorator


def register_warning(
        component_type: str,
        name: Optional[str] = None,
        replace: bool = False) -> None:
    """Decorator to register a warning check.
    
    Parameters
    ----------
    component_type : str
        Name of the component class (e.g., 'WNTREPANETLink').
    name : str, optional
        Warning name. If None, uses the function name.
    replace : bool, optional
        If True, replace existing warning with same name. Default is False.
    
    Examples
    --------
    >>> @register_warning("WNTREPANETLink", "roughness_coefficient_check")
    ... def validate_roughness_coefficient(instance):
    ...     if instance.type == "Pipe":
    ...         assert instance.data.get("roughness", 0) > 0, "Roughness must be positive"
    """
    def decorator(func):
        warn_name = name or func.__name__
        _registry.register_warning(component_type, warn_name, func, replace=replace)
        return func
    return decorator


def get_plugin_registry() -> RuleRegistry:
    """Get the global plugin registry."""
    return _registry


def load_plugins() -> int:
    """Discover and load all installed validation plugins.
    
    This function searches for packages that have registered themselves
    under the 'epanetparser.validation_plugins' entry point group.
    
    Returns
    -------
    int
        Number of plugins successfully loaded.
    
    Notes
    -----
    This function is called automatically when epanetparser is imported.
    """
    try:
        import importlib.metadata as importlib_metadata
    except ImportError:
        # Python < 3.8
        import importlib_metadata  # type: ignore
    
    loaded_count = 0
    entry_points = importlib_metadata.entry_points()
    
    # Handle both old and new entry_points API
    if hasattr(entry_points, 'select'):
        # Python 3.10+
        plugins = entry_points.select(group='epanetparser.validation_plugins')
    else:
        # Python 3.8-3.9
        plugins = entry_points.get('epanetparser.validation_plugins', [])
    
    for entry_point in plugins:
        plugin_name = entry_point.name
        
        # Skip if already loaded
        if plugin_name in _registry.list_plugins():
            logger.debug(f"Plugin '{plugin_name}' already loaded, skipping")
            continue
        
        try:
            # Load the plugin's registration function
            register_func = entry_point.load()
            # Call it to register validations
            register_func()
            # Mark as loaded
            _registry.mark_plugin_loaded(plugin_name)
            loaded_count += 1
            logger.info(f"Loaded validation plugin: {plugin_name}")
        except Exception as exc:
            logger.error(f"Failed to load plugin '{plugin_name}': {exc}")
    
    return loaded_count


# Auto-load plugins on import
_auto_loaded = load_plugins()
if _auto_loaded > 0:
    logger.info(f"Auto-loaded {_auto_loaded} validation plugin(s)")
    
    
# ============================================================================
# Auto-load built-in plugins
# ============================================================================

# Default configuration for built-in plugin discovery
# Includes both pattern-based discovery and backward compatibility with examples.py
DEFAULT_BUILTIN_PATTERNS = ["*_rules.py", "*_warnings.py"]
DEFAULT_BUILTIN_SEARCH_PATHS = [
    Path(__file__).parent / "addons",
    Path(__file__).parent / "builtins"]

# Global configuration for built-in plugin discovery
_builtin_discovery_config = {
    'patterns': DEFAULT_BUILTIN_PATTERNS.copy(),
    'search_paths': DEFAULT_BUILTIN_SEARCH_PATHS.copy()
}


def configure_builtin_discovery(
    search_paths: Optional[List[str]] = None,
    patterns: Optional[List[str]] = None,
    append: bool = True
) -> None:
    """Configure auto-discovery of built-in validation plugins.
    
    This function allows you to customize which directories are searched
    and which file patterns are matched when auto-discovering built-in
    validation plugins.
    
    Parameters
    ----------
    search_paths : List[str], optional
        List of directory paths to search for plugin files. Paths can be
        absolute or relative. If None, uses the default (plugins directory).
    patterns : List[str], optional
        List of glob patterns to match plugin files (e.g., ['*_rules.py']).
        If None, uses the default patterns.
    append : bool, optional
        If True (default), append to existing configuration. If False,
        replace the existing configuration entirely.
    
    Examples
    --------
    Add an additional search path::
    
        configure_builtin_discovery(
            search_paths=['/path/to/custom/plugins'],
            append=True
        )
    
    Use only custom patterns::
    
        configure_builtin_discovery(
            patterns=['*_validators.py'],
            append=False
        )
    
    Notes
    -----
    This function modifies the global discovery configuration. Call it
    before importing epanetparser to affect the initial plugin loading,
    or call `reload_builtin_plugins()` after configuration to re-scan.
    """
    global _builtin_discovery_config
    
    if search_paths is not None:
        paths = [Path(p).resolve() for p in search_paths]
        if append:
            # Append, avoiding duplicates
            existing_paths = set(_builtin_discovery_config['search_paths'])
            for path in paths:
                if path not in existing_paths:
                    _builtin_discovery_config['search_paths'].append(path)
        else:
            _builtin_discovery_config['search_paths'] = paths
    
    if patterns is not None:
        if append:
            # Append, avoiding duplicates
            existing_patterns = set(_builtin_discovery_config['patterns'])
            for pattern in patterns:
                if pattern not in existing_patterns:
                    _builtin_discovery_config['patterns'].append(pattern)
        else:
            _builtin_discovery_config['patterns'] = patterns
    
    logger.info(
        f"Built-in plugin discovery configured: "
        f"patterns={_builtin_discovery_config['patterns']}, "
        f"search_paths={_builtin_discovery_config['search_paths']}"
    )
    

def _apply_env_config() -> None:
    """Apply configuration from environment variables.
    
    Environment Variables
    ---------------------
    EPANETPARSER_PLUGIN_PATHS : str
        Colon-separated (on Unix) or semicolon-separated (on Windows)
        list of additional paths to search for built-in plugins.
    EPANETPARSER_PLUGIN_PATTERNS : str
        Comma-separated list of glob patterns to match plugin files.
        If set, replaces the default patterns.
    """
    # Additional search paths from environment
    env_paths = os.environ.get('EPANETPARSER_PLUGIN_PATHS', '')
    if env_paths:
        paths = env_paths.split(os.pathsep)
        configure_builtin_discovery(search_paths=paths, append=True)
        logger.debug(f"Added search paths from environment: {paths}")
    
    # Custom patterns from environment
    env_patterns = os.environ.get('EPANETPARSER_PLUGIN_PATTERNS', '')
    if env_patterns:
        patterns = [p.strip() for p in env_patterns.split(',')]
        configure_builtin_discovery(patterns=patterns, append=False)
        logger.debug(f"Set patterns from environment: {patterns}")
        
def discover_builtin_plugins(
    search_paths: Optional[List[Path]] = None,
    patterns: Optional[List[str]] = None
) -> List[Path]:
    """Discover plugin files matching patterns in search paths.
    
    Parameters
    ----------
    search_paths : List[Path], optional
        Directories to search. If None, uses global configuration.
    patterns : List[str], optional
        Glob patterns to match. If None, uses global configuration.
    
    Returns
    -------
    List[Path]
        List of discovered plugin file paths, sorted alphabetically.
    """
    if search_paths is None:
        search_paths = _builtin_discovery_config['search_paths']
    if patterns is None:
        patterns = _builtin_discovery_config['patterns']
    
    discovered = []
    for search_path in search_paths:
        if not search_path.is_dir():
            logger.debug(f"Search path does not exist or is not a directory: {search_path}")
            continue
        
        logger.debug(f"Searching for plugins in: {search_path}")
        for pattern in patterns:
            for file_path in search_path.glob(pattern):
                # Skip __init__.py and non-Python files
                if file_path.name == "__init__.py":
                    continue
                if not file_path.is_file():
                    continue
                if file_path.suffix != ".py":
                    continue
                
                discovered.append(file_path)
                logger.debug(f"Discovered plugin file: {file_path.name}")
    
    # Sort for consistent loading order
    return sorted(set(discovered))


def _load_builtin_plugins() -> int:
    """Load built-in validation plugins through auto-discovery.
    
    This function discovers and imports built-in plugin modules based on
    file naming conventions. By default, it searches the plugins directory
    for files matching patterns like '*_rules.py' and '*_warnings.py'.
    
    The discovery can be configured via:
    - `configure_builtin_discovery()` function
    - Environment variables (EPANETPARSER_PLUGIN_PATHS, EPANETPARSER_PLUGIN_PATTERNS)
    
    Returns
    -------
    int
        Number of built-in plugins successfully loaded.
    
    See Also
    --------
    configure_builtin_discovery : Configure discovery paths and patterns
    discover_builtin_plugins : Discover plugin files without loading them
    """
    builtin_count = 0
    
    # Discover plugin files
    plugin_files = discover_builtin_plugins()
    
    if not plugin_files:
        logger.debug("No built-in plugin files discovered")
        return 0
    
    logger.debug(f"Found {len(plugin_files)} built-in plugin file(s)")
    
    for plugin_file in plugin_files:
        try:
            # Create module name from file path
            module_name = f"epanetparser.plugins.{plugin_file.stem}"
            plugin_id = f"builtin:{plugin_file.stem}"
            
            # Skip if already loaded
            if plugin_id in _registry.list_plugins():
                logger.debug(f"Built-in plugin '{plugin_file.stem}' already loaded, skipping")
                continue
            
            # Import the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                _registry.mark_plugin_loaded(plugin_id)
                builtin_count += 1
                logger.debug(f"Loaded built-in plugin: {plugin_file.stem}")
            else:
                logger.warning(f"Could not create module spec for: {plugin_file}")
                
        except Exception as e:
            logger.warning(f"Failed to load built-in plugin '{plugin_file.name}': {e}")
    
    return builtin_count


def reload_builtin_plugins() -> int:
    """Reload built-in plugins after configuration changes.
    
    This function re-scans for built-in plugins using the current
    configuration. Useful after calling `configure_builtin_discovery()`.
    
    Returns
    -------
    int
        Number of newly loaded plugins (excludes already-loaded plugins).
    
    Examples
    --------
    >>> from epanetparser.plugins import configure_builtin_discovery, reload_builtin_plugins
    >>> configure_builtin_discovery(search_paths=['/custom/path'])
    >>> reload_builtin_plugins()
    2
    """
    return _load_builtin_plugins()


# Apply environment configuration and load built-in plugins
_apply_env_config()
_builtin_loaded = _load_builtin_plugins()
if _builtin_loaded > 0:
    logger.info(f"Loaded {_builtin_loaded} built-in validation plugin(s)")


__all__ = [
    'ValidatorRegistry',
    'register_rule',
    'register_warning',
    'get_plugin_registry',
    'load_plugins',
    'configure_builtin_discovery',
    'discover_builtin_plugins',
    'reload_builtin_plugins',
    '_registry',  # Private variable - use get_plugin_registry() instead
]
