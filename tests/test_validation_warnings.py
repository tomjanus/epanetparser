"""Tests for validation_warnings module."""

from epanetparser.core.epanettypes.validation_warnings import (
    WNTREPANETParserWarning,
    WNTREPANETTypeValidationWarning,
)


class TestWNTREPANETParserWarning:
    """Tests for base WNTREPANETParserWarning class."""

    def test_init_sets_message(self):
        """Test that message is stored correctly."""
        warning = WNTREPANETParserWarning("Test warning message")
        assert warning.message == "Test warning message"

    def test_str_returns_message(self):
        """Test __str__ returns the message."""
        warning = WNTREPANETParserWarning("Test warning message")
        assert str(warning) == "Test warning message"

    def test_repr_includes_class_and_message(self):
        """Test __repr__ includes class name and message."""
        warning = WNTREPANETParserWarning("Test warning message")
        repr_str = repr(warning)
        assert "WNTREPANETParserWarning" in repr_str
        assert "Test warning message" in repr_str


class TestWNTREPANETTypeValidationWarning:
    """Tests for WNTREPANETTypeValidationWarning class."""

    def test_init_stores_all_attributes(self):
        """Test that all attributes are stored correctly."""
        warning = WNTREPANETTypeValidationWarning(
            component="Junction",
            warning="elevation_missing",
            exc=ValueError("Elevation is required"),
            valuetext="elevation: None",
        )
        assert warning.component == "Junction"
        assert warning.warning == "elevation_missing"
        assert isinstance(warning.exc, ValueError)
        assert str(warning.exc) == "Elevation is required"
        assert warning.valuetext == "elevation: None"

    def test_str_formats_output(self):
        """Test __str__ formats output with desc_text and attributes."""
        warning = WNTREPANETTypeValidationWarning(
            component="Junction",
            warning="elevation_missing",
            exc=ValueError("Elevation is required"),
            valuetext="elevation: None",
        )
        str_output = str(warning)
        assert "[WARNING]" in str_output
        assert "Junction" in str_output
        assert "elevation_missing" in str_output
        assert "Elevation is required" in str_output
        assert "elevation: None" in str_output

    def test_repr_includes_class_and_attributes(self):
        """Test __repr__ includes class name and key attributes."""
        warning = WNTREPANETTypeValidationWarning(
            component="Junction",
            warning="elevation_missing",
            exc=ValueError("Elevation is required"),
            valuetext="elevation: None",
        )
        repr_str = repr(warning)
        assert "WNTREPANETTypeValidationWarning" in repr_str
        assert "Junction" in repr_str
        assert "elevation_missing" in repr_str
        assert "Elevation is required" in repr_str

    def test_as_dict_returns_correct_structure(self):
        """Test as_dict returns dictionary with all attributes."""
        warning = WNTREPANETTypeValidationWarning(
            component="Junction",
            warning="elevation_missing",
            exc=ValueError("Elevation is required"),
            valuetext="elevation: None",
        )
        d = warning.as_dict()
        assert d["component"] == "Junction"
        assert d["warning"] == "elevation_missing"
        assert d["exception"] == "Elevation is required"
        assert d["value"] == "elevation: None"

    def test_desc_text_class_attribute(self):
        """Test that desc_text is a class attribute."""
        assert WNTREPANETTypeValidationWarning.desc_text == "[WARNING]"

    def test_inherits_from_base_warning(self):
        """Test that it inherits from WNTREPANETParserWarning."""
        warning = WNTREPANETTypeValidationWarning(
            component="Junction",
            warning="test",
            exc=Exception("test"),
            valuetext="test",
        )
        assert isinstance(warning, WNTREPANETParserWarning)
        assert isinstance(warning, Warning)

    def test_with_different_exception_types(self):
        """Test with various exception types."""
        for exc in [ValueError("test"), TypeError("test"), RuntimeError("test"), Exception("test")]:
            warning = WNTREPANETTypeValidationWarning(
                component="Test",
                warning="test_warning",
                exc=exc,
                valuetext="test_value",
            )
            assert str(exc) in str(warning)
            assert warning.as_dict()["exception"] == str(exc)

    def test_with_empty_valuetext(self):
        """Test with empty valuetext."""
        warning = WNTREPANETTypeValidationWarning(
            component="Test",
            warning="test_warning",
            exc=Exception("test"),
            valuetext="",
        )
        assert warning.valuetext == ""
        assert warning.as_dict()["value"] == ""

    def test_with_none_valuetext(self):
        """Test with None valuetext (converted to string)."""
        warning = WNTREPANETTypeValidationWarning(
            component="Test",
            warning="test_warning",
            exc=Exception("test"),
            valuetext=None,
        )
        assert warning.valuetext is None
        assert warning.as_dict()["value"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])