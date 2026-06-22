"""Rich logging configuration and setup for logging outputs using Python's logging module.

- Rich logging configuration (`get_logger`, `configure_logging`)

Functions
---------
get_logger
    Get or create a logger with rich formatting for a module.
configure_logging
    Configure global logging settings with rich handler.

Examples
--------
Set up rich logging in a module:

>>> from epanetparser.core.logger_setup import get_logger
>>> logger = get_logger(__name__)
>>> logger.info("Processing network")
>>> logger.debug("Detailed information")
>>> logger.error("Something went wrong")

Configure logging at application startup:

>>> from epanetparser.core.logger_setup import configure_logging
>>> import logging
>>> configure_logging(level=logging.DEBUG, show_path=True)

See Also
--------
logging : Python standard library logging module
rich.logging.RichHandler : Rich console handler for Python logging

Notes
-----
Logging Best Practices for Library Development:
- Use `get_logger(__name__)` to create module-specific loggers
- Use WARNING as default level in library code (users can override)
- Use % formatting for log messages (lazy evaluation, not f-strings)
- Call `logger.exception()` to include tracebacks when logging errors
- Don't call `configure_logging()` in library code; let users do it
- Check `logger.isEnabledFor(level)` before expensive debug operations
"""
from typing import Optional
import logging
from rich.logging import RichHandler

# Global flag to track if logging has been configured
_LOGGING_CONFIGURED = False

def configure_logging(
    level: int | str = logging.INFO,
    show_time: bool = True,
    show_path: bool = False,
    enable_link_path: bool = False,
    log_format: Optional[str] = None
) -> None:
    """Configure global logging with rich formatting.
    
    Sets up the root logger with a RichHandler for beautiful console output.
    This should typically be called once at application startup.
    
    Parameters
    ----------
    level : int or str, default=logging.INFO
        Logging level (e.g., logging.DEBUG, logging.INFO, "DEBUG", "INFO").
    show_time : bool, default=True
        Whether to show timestamps in log output.
    show_path : bool, default=False
        Whether to show the file path in log output.
    enable_link_path : bool, default=False
        Whether to make file paths clickable (IDE integration).
    log_format : Optional[str], default=None
        Custom log format string. If None, uses rich's default format.
    
    Examples
    --------
    Configure logging for development (verbose):
    
    >>> from epanetparser.core.utils import configure_logging
    >>> import logging
    >>> configure_logging(level=logging.DEBUG, show_path=True)
    
    Configure logging for production (less verbose):
    
    >>> configure_logging(level=logging.WARNING, show_time=False)
    
    Configure with custom format:
    
    >>> configure_logging(log_format="%(name)s - %(message)s")
    
    Notes
    -----
    This function configures the root logger, which affects all loggers in
    the application. For library usage, users can override this configuration.
    
    The RichHandler provides:
    - Syntax highlighting for exception tracebacks
    - Pretty formatting for log messages
    - Support for rich markup in messages
    - Automatic indentation of multiline messages
    """
    global _LOGGING_CONFIGURED  # pylint: disable=global-statement
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    # Create rich handler with specified options
    rich_handler = RichHandler(
        show_time=show_time,
        show_path=show_path,
        enable_link_path=enable_link_path,
        rich_tracebacks=True,
        tracebacks_show_locals=level <= logging.DEBUG,  # Show locals in DEBUG mode
        markup=True  # Enable rich markup in log messages
    )
    # Set format if provided
    if log_format:
        formatter = logging.Formatter(log_format)
        rich_handler.setFormatter(formatter)
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s" if not log_format else log_format,
        datefmt="[%X]",
        handlers=[rich_handler]
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str, level: Optional[int | str] = None) -> logging.Logger:
    """Get or create a logger with rich formatting.
    
    Returns a logger instance for the specified module. If global logging
    hasn't been configured yet, configures it with sensible defaults.
    
    Parameters
    ----------
    name : str
        Name of the logger, typically `__name__` of the calling module.
    level : Optional[int or str], default=None
        Optional logging level for this specific logger. If None, inherits
        from parent loggers.
    
    Returns
    -------
    logging.Logger
        Configured logger instance with rich formatting.
    
    Examples
    --------
    In a module:
    
    >>> # At the top of your module
    >>> from epanetparser.core.utils import get_logger
    >>> logger = get_logger(__name__)
    >>> 
    >>> # Use throughout the module
    >>> logger.debug("Starting validation")
    >>> logger.info("Processing network: [cyan]%s[/cyan]", network_name)
    >>> logger.warning("Found %d potential issues", len(issues))
    >>> logger.error("Validation failed: %s", error)
    
    With custom level:
    
    >>> logger = get_logger(__name__, level=logging.DEBUG)
    >>> logger.debug("Detailed debugging information")
    
    Using rich markup:
    
    >>> logger.info("[bold green]✓[/bold green] Validation passed")
    >>> logger.error("[bold red]✗[/bold red] Validation failed")
    
    Logging exceptions:
    
    >>> try:
    ...     risky_operation()
    ... except Exception:
    ...     logger.exception("Operation failed")  # Includes traceback
    
    Notes
    -----
    Best practice for libraries:
    - Use `logger = get_logger(__name__)` at module level
    - Use appropriate log levels (DEBUG for verbose, INFO for normal, WARNING for issues)
    - Don't call `configure_logging()` in library code; let users configure it
    - Use string formatting with % instead of f-strings for lazy evaluation
    
    The logger name follows Python's module hierarchy, e.g.:
    - "epanetparser.core.parse"
    - "epanetparser.core.validation"
    
    This allows users to configure logging per-module:
    
    >>> import logging
    >>> logging.getLogger("epanetparser.core.parse").setLevel(logging.DEBUG)
    >>> logging.getLogger("epanetparser.core.validation").setLevel(logging.WARNING)
    """
    # Configure logging if not already done (with sensible defaults)
    if not _LOGGING_CONFIGURED:
        configure_logging(level=logging.WARNING)  # Default to WARNING for libraries
    # Get or create logger
    logger = logging.getLogger(name)
    # Set level if specified
    if level is not None:
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        logger.setLevel(level)
    return logger


if __name__ == "__main__":
    # Example usage of the logging setup
    configure_logging(level=logging.DEBUG, show_path=True)
    logger = get_logger(__name__)
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An exception occurred")