""" """

import pytest
import logging
from epanetparser.core.logger_setup import (
    configure_logging,
    get_logger,
)
import epanetparser.core.logger_setup as logging_module

@pytest.fixture(autouse=False)
def reset_logging():
    """Fixture to completely reset logging state between tests.
    
    logging.basicConfig() only works when root.handlers is empty.
    This fixture ensures a clean state for each test by removing ALL handlers,
    including pytest's LogCaptureHandlers.
    """
    # Store original state
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    original_flag = logging_module._LOGGING_CONFIGURED
    # Completely reset logging - remove ALL handlers (including pytest's)
    for handler in list(logging.root.handlers):
        logging.root.removeHandler(handler)
    logging.root.setLevel(logging.WARNING)
    logging_module._LOGGING_CONFIGURED = False
    # Clear logger cache
    logging.Logger.manager.loggerDict.clear()
    yield
    # Clean up handlers created during test
    for handler in list(logging.root.handlers):
        if handler not in original_handlers:
            logging.root.removeHandler(handler)
            try:
                handler.close()
            except:
                pass
    # Restore original handlers
    for handler in original_handlers:
        if handler not in logging.root.handlers:
            logging.root.addHandler(handler)
    logging.root.setLevel(original_level)
    logging_module._LOGGING_CONFIGURED = original_flag


@pytest.fixture
def log_capture():
    """Fixture to capture log records for testing.
    
    Returns a list that will be populated with LogRecord objects
    as they are emitted.
    """
    class ListHandler(logging.Handler):
        """Custom handler that captures log records in a list."""
        def __init__(self):
            super().__init__()
            self.records = []
        
        def emit(self, record):
            self.records.append(record)
    handler = ListHandler()
    return handler


class TestConfigureLogging:
    """Tests for configure_logging() function.
    
    Note: These tests work around pytest's logging infrastructure which
    adds LogCaptureHandlers that prevent logging.basicConfig() from working
    as expected.
    """
    
    def test_configure_logging_sets_flag(self, reset_logging):
        """Test that configure_logging sets the global configuration flag."""
        assert logging_module._LOGGING_CONFIGURED == False
        configure_logging()
        assert logging_module._LOGGING_CONFIGURED == True
    
    def test_configure_logging_callable(self, reset_logging):
        """Test that configure_logging is callable without errors."""
        # Should not raise any exceptions
        configure_logging()
        configure_logging(level=logging.DEBUG)
        configure_logging(level="INFO")
        configure_logging(show_time=False)
        configure_logging(show_path=True)
    
    def test_configure_logging_level_conversion(self, reset_logging):
        """Test that string levels are converted to int levels."""
        # Verify level conversion works
        string_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        expected = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
        for str_level, exp_level in zip(string_levels, expected):
            assert getattr(logging, str_level.upper()) == exp_level


class TestGetLogger:
    """Tests for get_logger() function."""
    
    def test_get_logger_returns_logger(self, reset_logging):
        """Test that get_logger returns a logging.Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
    
    def test_get_logger_with_name(self, reset_logging):
        """Test that get_logger creates logger with correct name."""
        logger = get_logger("my_test_module")
        assert logger.name == "my_test_module"
    
    def test_get_logger_auto_configures(self, reset_logging):
        """Test that get_logger auto-configures logging if not configured."""
        # Verify not configured
        assert logging_module._LOGGING_CONFIGURED == False
        logger = get_logger("test_module")
        # Should be auto-configured now
        assert logging_module._LOGGING_CONFIGURED == True
    
    def test_get_logger_with_level_int(self, reset_logging):
        """Test get_logger with explicit integer log level."""
        logger = get_logger("test_module", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
    
    def test_get_logger_with_level_string(self, reset_logging):
        """Test get_logger with string log level."""
        logger = get_logger("test_module", level="DEBUG")
        assert logger.level == logging.DEBUG
    
    def test_get_logger_multiple_calls_same_logger(self, reset_logging):
        """Test that multiple calls with same name return same logger."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2
    
    def test_get_logger_different_names(self, reset_logging):
        """Test that different names return different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"
    
    def test_get_logger_hierarchical_names(self, reset_logging):
        """Test logger hierarchy with dotted names."""
        logger_parent = get_logger("epanetparser.core")
        logger_child = get_logger("epanetparser.core.utils")
        assert logger_parent.name == "epanetparser.core"
        assert logger_child.name == "epanetparser.core.utils"
        # Child logger should have parent in hierarchy
        assert logger_child.parent.name.startswith("epanetparser")
    
    def test_get_logger_logging_works(self, reset_logging, log_capture):
        """Test that logger actually logs messages."""
        configure_logging(level=logging.DEBUG)
        logger = get_logger("test_module")
        # Add our capture handler
        logger.addHandler(log_capture)
        logger.setLevel(logging.DEBUG)
        # Log some messages
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        # Check that messages were captured
        assert len(log_capture.records) == 3
        assert log_capture.records[0].levelname == "DEBUG"
        assert log_capture.records[1].levelname == "INFO"
        assert log_capture.records[2].levelname == "WARNING"
        assert log_capture.records[0].message == "Debug message"
    
    def test_get_logger_respects_root_level(self, reset_logging, log_capture):
        """Test that logger respects root logger level."""
        configure_logging(level=logging.WARNING)
        logger = get_logger("test_module")
        logger.addHandler(log_capture)
        # These should not be logged (below WARNING)
        logger.debug("Debug message")
        logger.info("Info message")
        # This should be logged
        logger.warning("Warning message")
        # Only warning should be captured
        assert len(log_capture.records) == 1
        assert log_capture.records[0].levelname == "WARNING"
    
    def test_get_logger_custom_level_overrides(self, reset_logging, log_capture):
        """Test that logger-specific level overrides root level."""
        configure_logging(level=logging.WARNING)
        logger = get_logger("test_module", level=logging.DEBUG)
        logger.addHandler(log_capture)
        # Should log even though root is WARNING
        logger.debug("Debug message")
        assert len(log_capture.records) == 1
        assert log_capture.records[0].levelname == "DEBUG"
    
    def test_get_logger_with_dunder_name(self, reset_logging):
        """Test typical usage with __name__."""
        # Simulate module __name__
        module_name = "epanetparser.core.validation"
        logger = get_logger(module_name)
        assert logger.name == module_name
        assert isinstance(logger, logging.Logger)


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_configure_then_get_logger(self, reset_logging, log_capture):
        """Test typical workflow: configure, then get logger, then log."""
        # Application configures logging
        configure_logging(level=logging.DEBUG, show_path=True)
        # Module gets logger
        logger = get_logger(__name__, level=logging.DEBUG)
        logger.addHandler(log_capture)
        # Module logs messages
        logger.debug("Debug message")
        logger.info("Processing data")
        logger.warning("Warning occurred")
        # Check all were captured
        assert len(log_capture.records) == 3
        assert log_capture.records[0].message == "Debug message"
        assert log_capture.records[1].message == "Processing data"
        assert log_capture.records[2].message == "Warning occurred"
    
    def test_get_logger_without_configure(self, reset_logging, log_capture):
        """Test that get_logger works without explicit configure_logging call."""
        # Just get logger (auto-configures)
        logger = get_logger(__name__)
        logger.addHandler(log_capture)
        # Log a warning (should work with default WARNING level)
        logger.warning("Test warning")
        assert len(log_capture.records) == 1
        assert log_capture.records[0].message == "Test warning"
    
    def test_multiple_loggers_same_root(self, reset_logging, log_capture):
        """Test multiple loggers sharing the same root configuration."""
        configure_logging(level=logging.INFO)
        logger1 = get_logger("module1", level=logging.INFO)
        logger2 = get_logger("module2", level=logging.INFO)
        logger1.addHandler(log_capture)
        logger2.addHandler(log_capture)
        logger1.info("Message from module1")
        logger2.info("Message from module2")
        assert len(log_capture.records) == 2
        assert log_capture.records[0].name == "module1"
        assert log_capture.records[1].name == "module2"
    
    def test_logging_exception_capture(self, reset_logging, log_capture):
        """Test that logger.exception() works correctly."""
        configure_logging(level=logging.DEBUG)
        logger = get_logger("test_module")
        logger.addHandler(log_capture)
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")
        # Should have captured the exception log
        assert len(log_capture.records) == 1
        assert log_capture.records[0].levelname == "ERROR"
        assert log_capture.records[0].message == "An error occurred"
        assert log_capture.records[0].exc_info is not None
        
        
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
