"""Tests for epanetparser.core.logger_setup.

Logging configuration is unrelated to parsing and validation, but the rest of
the package depends on it: every module obtains its logger through
:func:`get_logger`, and :func:`epanetparser.core.init.initialize` configures
logging from the user's configuration file at import time.

What is covered
---------------
LoggingConfig
    Defaults, and building one from a mapping, with and without ignoring
    unknown keys.
configure_logging
    Applying a configuration to the root logger, from an object or a mapping,
    including the environment-variable overrides.
get_logger
    Returning a named logger, and applying an explicit level to it.
reset_logging_to_defaults
    Returning logging to a known state, which is what isolates these tests.

Notes
-----
Logging is process-global state, so each test resets it through the module's
own API rather than by manipulating handlers directly. That keeps these tests
honest about what the module actually provides.
"""
import logging

import pytest

from epanetparser.core.logger_setup import (
    ENV_PREFIX,
    LoggingConfig,
    configure_logging,
    get_logger,
    reset_logging_to_defaults,
)


@pytest.fixture
def reset_logging():
    """Reset logging to a known state before and after each test.

    Yields:
        None: The fixture exists for its setup and teardown, not its value.
    """
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    reset_logging_to_defaults()
    yield
    reset_logging_to_defaults()
    for handler in original_handlers:
        if handler not in logging.root.handlers:
            logging.root.addHandler(handler)
    logging.root.setLevel(original_level)


@pytest.fixture
def log_capture():
    """Return a handler that records everything emitted to it."""
    class ListHandler(logging.Handler):
        """A handler that keeps emitted records in a list."""

        def __init__(self):
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    return ListHandler()


class TestLoggingConfig:
    """The configuration container."""

    def test_defaults_are_usable(self):
        """A default configuration needs no arguments."""
        config = LoggingConfig()
        assert config.level == logging.DEBUG
        assert config.logfile is None
        assert config.ignored_loggers == ()

    def test_from_dict_reads_known_fields(self):
        """Every documented field can be set from a mapping."""
        config = LoggingConfig.from_dict(
            {"level": "INFO", "show_path": True, "logfile": None}
        )
        assert config.level == "INFO"
        assert config.show_path is True

    def test_from_dict_can_ignore_unknown_fields(self):
        """Configuration files carry keys for other subsystems; ignoring them is normal."""
        data = {"level": "INFO", "not_a_logging_field": 1}
        assert LoggingConfig.from_dict(data, ignore_unknown=True).level == "INFO"
        with pytest.raises(TypeError):
            LoggingConfig.from_dict(data)


class TestConfigureLogging:
    """Applying a configuration to the root logger."""

    def test_is_callable_with_no_arguments(self, reset_logging):
        """Configuration with no arguments applies the defaults."""
        configure_logging()
        assert logging.getLogger().handlers

    def test_accepts_a_configuration_object(self, reset_logging):
        """A LoggingConfig is applied as given."""
        configure_logging(LoggingConfig(level=logging.WARNING))
        assert logging.getLogger().level == logging.WARNING

    def test_accepts_a_mapping(self, reset_logging):
        """A mapping is a convenience form, for configuration read from a file."""
        configure_logging({"level": "ERROR"})
        assert logging.getLogger().level == logging.ERROR

    def test_force_closes_handlers_before_replacing_them(self, reset_logging):
        """force=True is what lets a caller hand the root over completely.

        Replacing a handler is not the same as closing it. A rotating file
        handler that is dropped but not closed keeps its file open, so a caller
        reconfiguring a log file would leak the previous one unless force is
        set.
        """
        closed = []

        class ClosableHandler(logging.NullHandler):
            """A handler that records being closed."""

            def close(self) -> None:
                closed.append(self)
                super().close()

        stranger = ClosableHandler()
        logging.getLogger().addHandler(stranger)

        configure_logging(LoggingConfig(level=logging.WARNING, force=True))
        assert stranger in closed
        assert logging.getLogger().level == logging.WARNING

    def test_handlers_are_replaced_even_without_force(self, reset_logging):
        """dictConfig owns the root, so its handlers are replaced either way."""
        logging.getLogger().addHandler(logging.NullHandler())
        configure_logging(LoggingConfig(level=logging.INFO))
        assert all(
            isinstance(handler, logging.NullHandler) is False
            for handler in logging.getLogger().handlers
        )

    def test_a_logfile_adds_a_second_handler(self, reset_logging, tmp_path):
        """Naming a log file adds a rotating file handler alongside the console."""
        logfile = tmp_path / "epanetparser.log"
        configure_logging(LoggingConfig(level=logging.INFO, logfile=logfile))
        assert len(logging.getLogger().handlers) == 2
        logfile.unlink()

    def test_environment_variables_override_the_configuration(
        self, reset_logging, monkeypatch
    ):
        """A deployment can turn logging up without editing the config file."""
        monkeypatch.setenv(f"{ENV_PREFIX}_LOG_LEVEL", "CRITICAL")
        configure_logging(LoggingConfig(level=logging.DEBUG))
        assert logging.getLogger().level == logging.CRITICAL

    def test_ignored_loggers_are_suppressed(self, reset_logging):
        """A noisy dependency can be pinned to WARNING without silencing the rest."""
        configure_logging(LoggingConfig(level=logging.DEBUG, ignored_loggers=("wntr",)))
        assert logging.getLogger("wntr").level == logging.WARNING


class TestGetLogger:
    """Obtaining a named logger."""

    def test_returns_a_logger(self, reset_logging):
        """The caller always gets a standard library logger."""
        assert isinstance(get_logger("test_module"), logging.Logger)

    def test_uses_the_name_it_is_given(self, reset_logging):
        """A module passes its own __name__, so the name identifies the source."""
        assert get_logger("my_test_module").name == "my_test_module"

    def test_the_same_name_gives_the_same_logger(self, reset_logging):
        """Logging is configured per name, so the name must be the identity."""
        assert get_logger("test_module") is get_logger("test_module")

    def test_different_names_give_different_loggers(self, reset_logging):
        """Two modules are configured independently."""
        assert get_logger("module1") is not get_logger("module2")

    def test_names_form_a_hierarchy(self, reset_logging):
        """Dotted names place a module under its package, so levels inherit."""
        child = get_logger("epanetparser.core.validation")
        assert child.name == "epanetparser.core.validation"
        assert child.parent is not None
        assert child.parent.name.startswith("epanetparser")

    def test_an_integer_level_is_applied(self, reset_logging):
        """A module can ask to be more verbose than the root."""
        assert get_logger("test_module", level=logging.DEBUG).level == logging.DEBUG

    def test_a_string_level_is_applied(self, reset_logging):
        """Levels may be named, as they are in the configuration file."""
        assert get_logger("test_module", level="DEBUG").level == logging.DEBUG

    def test_an_unrecognised_level_name_is_rejected(self, reset_logging):
        """A typo in a configured level is reported, not silently ignored.

        Falling back to a default would hide the typo: a module asking for
        DEBUG would quietly get INFO and the missing output would be very hard
        to account for.
        """
        with pytest.raises(ValueError):
            get_logger("test_module", level="NOT_A_LEVEL")

    def test_a_standard_level_alias_is_accepted(self, reset_logging):
        """The standard library's own aliases resolve, as the module intends."""
        assert get_logger("test_module", level="WARN").level == logging.WARNING

    def test_no_level_leaves_the_logger_alone(self, reset_logging):
        """Asking for a logger does not change how verbose it is."""
        assert get_logger("test_module").level == logging.NOTSET


class TestLoggingIntegration:
    """Configuration and loggers working together."""

    def test_configure_then_log(self, reset_logging, log_capture):
        """The ordinary workflow: configure, get a logger, log."""
        configure_logging(LoggingConfig(level=logging.DEBUG))
        logger = get_logger("test_module")
        logger.addHandler(log_capture)
        logger.setLevel(logging.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning occurred")

        assert [record.levelname for record in log_capture.records] == [
            "DEBUG",
            "INFO",
            "WARNING",
        ]
        assert log_capture.records[0].message == "Debug message"

    def test_the_root_level_is_respected(self, reset_logging, log_capture):
        """A quiet root means a quiet library."""
        configure_logging(LoggingConfig(level=logging.WARNING))
        logger = get_logger("test_module")
        logger.addHandler(log_capture)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        assert [record.levelname for record in log_capture.records] == ["WARNING"]

    def test_a_module_may_be_more_verbose_than_the_root(
        self, reset_logging, log_capture
    ):
        """A module asking for debug output gets it even under a quiet root."""
        configure_logging(LoggingConfig(level=logging.WARNING))
        logger = get_logger("test_module", level=logging.DEBUG)
        logger.addHandler(log_capture)

        logger.debug("Debug message")

        assert [record.levelname for record in log_capture.records] == ["DEBUG"]

    def test_several_modules_share_one_configuration(
        self, reset_logging, log_capture
    ):
        """Two modules logging under one configured root are both captured."""
        configure_logging(LoggingConfig(level=logging.INFO))
        first = get_logger("module1")
        second = get_logger("module2")
        first.addHandler(log_capture)
        second.addHandler(log_capture)

        first.info("Message from module1")
        second.info("Message from module2")

        assert [record.name for record in log_capture.records] == [
            "module1",
            "module2",
        ]

    def test_exceptions_are_logged_with_their_traceback(
        self, reset_logging, log_capture
    ):
        """logger.exception() attaches the traceback, which is why it exists."""
        configure_logging(LoggingConfig(level=logging.DEBUG))
        logger = get_logger("test_module")
        logger.addHandler(log_capture)

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")

        assert len(log_capture.records) == 1
        record = log_capture.records[0]
        assert record.levelname == "ERROR"
        assert record.message == "An error occurred"
        assert record.exc_info is not None

    def test_a_logger_works_without_explicit_configuration(
        self, reset_logging, log_capture
    ):
        """Obtaining a logger is enough; it does not require configuration first."""
        logger = get_logger("test_module")
        logger.addHandler(log_capture)
        logger.warning("Test warning")
        assert log_capture.records[0].message == "Test warning"


class TestResetLogging:
    """Returning logging to a known state."""

    def test_removes_root_handlers(self, reset_logging):
        """A reset leaves nothing attached, so the next configuration is exact."""
        configure_logging(LoggingConfig(level=logging.INFO))
        assert logging.getLogger().handlers
        reset_logging_to_defaults()
        assert logging.getLogger().handlers == []

    def test_restores_the_default_root_level(self, reset_logging):
        """Python's default root level is WARNING."""
        configure_logging(LoggingConfig(level=logging.DEBUG))
        reset_logging_to_defaults()
        assert logging.getLogger().level == logging.WARNING

    def test_clears_per_logger_levels(self, reset_logging):
        """A module that asked to be verbose does not stay that way."""
        get_logger("test_module", level=logging.DEBUG)
        reset_logging_to_defaults()
        assert logging.getLogger("test_module").level == logging.NOTSET


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
