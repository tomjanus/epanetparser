"""Initialization system for epanetparser.

This module provides centralized initialization for the epanetparser library,
ensuring that essential setup tasks are performed before the library is used.
It runs automatically when epanetparser is imported or when CLI commands are
executed.

The initialization system is:
- **Thread-safe**: Uses a lock to prevent race conditions
- **Idempotent**: Can be called multiple times safely (runs only once)
- **Extensible**: Designed to support additional initialization tasks

Current Initialization Tasks
-----------------------------
1. **User Configuration Setup**
   - Checks if user config file exists in platform-specific directory
   - Creates config file from package defaults if missing
   - Uses ConfigManager for all config operations

2. **Logging Setup**
   - Configures logging from the merged configuration

Future Extensions
-----------------
- Cache directory setup
- Discovery of third-party rule sets registered as entry points

Rule sets themselves are *not* discovered here. Discovery is lazy and lives in
:mod:`epanetparser.core.validation.discovery`, so importing the package does not
walk the rule set packages unless validation is actually used.

Examples
--------
Explicit initialization (optional, as it runs automatically):

>>> from epanetparser.core.init import initialize
>>> initialize()
>>> # Library is now ready to use

The initialize function is called automatically when:
- You import epanetparser: `import epanetparser`
- You run CLI commands: `epanetparser`, `epanetparser-plugins`
"""

import logging
import threading
from pathlib import Path
from typing import Optional
from epanetparser.core.config.manager import ConfigManager
from epanetparser.core.logger_setup import LoggingConfig, configure_logging

# Thread-safe initialization state
_initialized = False
_init_lock = threading.Lock()


def initialize(force: bool = False) -> None:
    """Initialize the epanetparser library.
    
    Performs essential setup tasks including:
    - Creating the user configuration file if it doesn't exist
    - Configuring logging from the merged configuration

    Rule sets are deliberately not discovered here: discovery is lazy, in
    :mod:`epanetparser.core.validation.discovery`, so importing the package does
    not walk the rule set packages unless validation is used.
    
    This function is thread-safe and idempotent - it can be called multiple
    times but will only perform initialization once per session unless
    force=True is specified.
    
    Parameters
    ----------
    force : bool, default=False
        If True, perform initialization even if already initialized.
        Useful for testing or when configuration needs to be refreshed.
    
    Returns
    -------
    None
    
    Notes
    -----
    This function is called automatically when:
    - The epanetparser package is imported
    - Any CLI command is executed (epanetparser, epanetparser-plugins)
    
    Therefore, explicit calls are usually not necessary unless you need
    to force re-initialization.
    
    Examples
    --------
    >>> from epanetparser.core.init import initialize
    >>> initialize()  # Safe to call, even if already initialized
    >>> initialize(force=True)  # Force re-initialization
    
    See Also
    --------
    epanetparser.core.config.manager.ConfigManager : Configuration management
    """
    global _initialized # pylint: disable=global-statement
    if _initialized and not force:
        return
    # Acquire lock for thread-safe initialization
    with _init_lock:
        # Double-check pattern: another thread might have initialized
        # while we were waiting for the lock
        if _initialized and not force:
            return
        manager = ConfigManager()
        manager.create_user_config()
        
        # Setup logging from configuration upon initialization
        config = ConfigManager().load()
        logging_config = LoggingConfig.from_dict(config.get("logging", {}), ignore_unknown=True)
        configure_logging(logging_config)
        
        _initialized = True


def is_initialized() -> bool:
    """Check if epanetparser has been initialized.
    
    Returns
    -------
    bool
        True if initialize() has been successfully called, False otherwise.
    
    Examples
    --------
    >>> from epanetparser.core.init import is_initialized, initialize
    >>> is_initialized()
    False
    >>> initialize()
    >>> is_initialized()
    True
    """
    return _initialized


def reset_initialization() -> None:
    """Reset initialization state.
    
    This function is primarily intended for testing purposes. It resets
    the initialization state so that initialize() will perform its tasks
    again on the next call.
    
    Warning
    -------
    This function should not be used in production code. It's designed
    for testing scenarios where you need to verify initialization behavior.
    
    Examples
    --------
    >>> from epanetparser.core.init import initialize, reset_initialization
    >>> initialize()
    >>> reset_initialization()  # For testing only
    >>> initialize()  # Will run initialization tasks again
    """
    global _initialized
    with _init_lock:
        _initialized = False
        logging.getLogger(__name__).debug(
            "Initialization state reset (testing mode)"
        )
