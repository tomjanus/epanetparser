"""Utilities for configuring Rich-based logging in epanetparser.

This module centralizes console and rotating-file logging setup, supports
environment-variable overrides, and exposes helpers for creating configured
loggers throughout the package.
"""
from __future__ import annotations
import logging
import logging.config
import logging.handlers
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping
from rich.console import Console
from rich.logging import RichHandler


# Set your project environment prefix here
ENV_PREFIX = "EPANETPARSER"


@dataclass(slots=True)
class LoggingConfig:
    """Configuration container for Rich logging behaviour.

    Parameters
    ----------
    level : int or str, default=logging.INFO
        Default log level applied to the root logger.
    show_time : bool, default=True
        Whether to display timestamps in console log output.
    show_path : bool, default=False
        Whether to include the source path in console log output.
    enable_link_path : bool, default=False
        Whether to enable clickable paths in Rich output.
    markup : bool, default=True
        Whether Rich should interpret markup in log messages.
    rich_tracebacks : bool, default=True
        Whether to render rich traceback formatting.
    tracebacks_show_locals : bool, default=False
        Whether to include local variables in tracebacks.
    tracebacks_extra_lines : int, default=3
        Number of extra lines shown around traceback frames.
    tracebacks_theme : str or None, default=None
        Optional Rich traceback theme name.
    datefmt : str, default="[%X]"
        Date format used for console timestamps.
    log_format : str, default="%(message)s"
        Formatter string for console logging output.
    file_format : str, default="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        Formatter string for rotating file log output.
    logfile : Path or None, default=None
        Optional path to a rotating log file.
    max_bytes : int, default=5 * 1024 * 1024
        Maximum size of each log file before rotation.
    backup_count : int, default=5
        Number of rotated files to keep.
    console_level : int, str, or None, default=None
        Override log level for the console handler.
    file_level : int, str, or None, default=None
        Override log level for the file handler.
    force : bool, default=False
        Whether to remove and rebuild existing root handlers.
    console : Console or None, default=None
        Optional Rich console instance to use for logging.
    ignored_loggers : tuple of str, default=()
        Logger names whose level should be suppressed to WARNING.
    """

    level: int | str = logging.DEBUG
    show_time: bool = True
    show_path: bool = False
    enable_link_path: bool = False
    markup: bool = True
    rich_tracebacks: bool = True
    tracebacks_show_locals: bool = False
    tracebacks_extra_lines: int = 3
    tracebacks_theme: str | None = None
    datefmt: str = "[%X]"
    log_format: str = "%(message)s"
    file_format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logfile: Path | None = None
    max_bytes: int = 5 * 1_024 * 1_024
    backup_count: int = 5
    console_level: int | str | None = None
    file_level: int | str | None = None
    force: bool = False
    console: Console | None = None
    ignored_loggers: tuple[str, ...] = field(default_factory=tuple)
        
    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        *,
        ignore_unknown: bool = False,
    ) -> LoggingConfig:
        """Create a LoggingConfig instance from a mapping.

        Parameters
        ----------
        data : Mapping[str, Any]
            Mapping of configuration values to convert into a LoggingConfig.
        ignore_unknown : bool, default=False
            If True, ignore keys that are not defined on LoggingConfig.

        Returns
        -------
        LoggingConfig
            A populated logging configuration object.
        """
        if ignore_unknown:
            valid = {f.name for f in fields(cls)}
            data = {k: v for k, v in data.items() if k in valid}
        return cls(**data)


def _lvl(v: int | str | None, default: int = logging.INFO, use_default: bool = True) -> int | None:
    """Normalize a logging level value to an integer.

    Parameters
    ----------
    v : int, str, or None
        Logging level provided as an integer, a named level string, or None.

    Returns
    -------
    int or None
        The corresponding logging level as an integer, or None if no level
        was provided.
    default : int, optional
        Default logging level to return if `v` is None and `use_default` is True
    use_default : bool, optional
        If True, return `default` when `v` is None; otherwise return None.
    """
    if v is None:
        if use_default:
            return default
        return None
    if isinstance(v, str):
        # Gracefully handle public names or standard lookups
        return logging.getLevelName(v.upper())  # type: ignore
    return v


def configure_logging(context: LoggingConfig | Mapping[str, Any] | None = None) -> None:
    """Configure the root logger with Rich console and optional file handlers.

    Parameters
    ----------
    context : LoggingConfig or Mapping[str, Any], optional
        Logging configuration values. If omitted, a default LoggingConfig is
        used.

    Notes
    -----
    Environment variables with the ``EPANETPARSER_`` prefix can override the
    configured log levels for the root, console, and file handlers.
    """
    if context is None:
        context = LoggingConfig()
    elif isinstance(context, Mapping):
        cfg = dict(context)
        if "logfile" in cfg and cfg["logfile"] is not None:
            cfg["logfile"] = Path(cfg["logfile"])
        if "ignored_loggers" in cfg and isinstance(cfg["ignored_loggers"], list):
            cfg["ignored_loggers"] = tuple(cfg["ignored_loggers"])
        context = LoggingConfig(**cfg)
    # 1. Environment Variable Overrides
    env_root = os.getenv(f"{ENV_PREFIX}_LOG_LEVEL")
    env_console = os.getenv(f"{ENV_PREFIX}_CONSOLE_LEVEL")
    env_file = os.getenv(f"{ENV_PREFIX}_FILE_LEVEL")
    base_level = env_root if env_root else context.level
    root_level = _lvl(base_level) or logging.INFO
    console_level = _lvl(env_console or context.console_level or base_level) or root_level
    file_level = _lvl(env_file or context.file_level or base_level) or root_level
    # 2. Setup Handlers Matrix safely
    # For Rich console injection to seamlessly play nice with dictConfig, 
    # we instantiate it explicitly and register via the lambda locator factory.
    console_handler = RichHandler(
        level=console_level,
        console=context.console,
        show_time=context.show_time,
        show_path=context.show_path,
        enable_link_path=context.enable_link_path,
        markup=context.markup,
        rich_tracebacks=context.rich_tracebacks,
        tracebacks_show_locals=context.tracebacks_show_locals,
        tracebacks_extra_lines=context.tracebacks_extra_lines,
        tracebacks_theme=context.tracebacks_theme,
    )
    # Give console its raw format structure
    console_handler.setFormatter(logging.Formatter(context.log_format, datefmt=context.datefmt))
    # Set logging handlers
    handlers: dict[str, Any] = {
        "console": {
            "()": lambda: console_handler,
            "level": console_level,
        }
    }
    root_handlers = ["console"]
    # 3. Handle File Handler Generation if target output exists
    if context.logfile:
        # Ensure target directory structure exists safely
        context.logfile.parent.mkdir(parents=True, exist_ok=True)
        
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(context.logfile),
            "maxBytes": context.max_bytes,
            "backupCount": context.backup_count,
            "formatter": "file_standard",
            "level": file_level,
            "encoding": "utf-8",
        }
        root_handlers.append("file")
    # 4. Clean out existing roots cleanly if force configuration is requested (Crucial for Unit Tests)
    if context.force:
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
    # 5. Apply configuration dictionary layout
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "file_standard": {
                    "format": context.file_format,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": handlers,
            "root": {"level": root_level, "handlers": root_handlers},
            "incremental": False,
        }
    )
    # 6. Apply suppressions to noisy external dependencies
    for name in context.ignored_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)


def reset_logging_to_defaults() -> None:
    """Reset the global logging state to Python's default behavior.

    Notes
    -----
    This removes any handlers attached to the root logger, closes them safely,
    and clears explicit per-logger configuration so subsequent logging uses
    the standard Python defaults.
    """
    root = logging.getLogger()
    # 1. Safely shutdown and detach all attached root handlers
    for handler in list(root.handlers):
        try:
            handler.acquire()
            handler.flush()
            handler.close()
        except (OSError, ValueError):
            pass  # Handler might already be closed
        finally:
            handler.release()
        root.removeHandler(handler)

    # 2. Reset the default Root Logger level (Python default is WARNING)
    root.setLevel(logging.WARNING)

    # 3. Reset any child loggers that were explicitly configured
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        if isinstance(logger, logging.Logger):
            logger.setLevel(logging.NOTSET)
            logger.handlers.clear()
            logger.propagate = True


def get_logger(name: str, level: int | str | None = None) -> logging.Logger:
    """Return a logger with optional level configuration.

    Parameters
    ----------
    name : str
        Logger name to retrieve.
    level : int, str, or None, default=None
        Optional level to apply to the logger.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(_lvl(level))
    return logger


if __name__ == "__main__":
    pass
