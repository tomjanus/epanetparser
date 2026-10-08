"""Tests for environment module."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

import pytest

from epanetparser.core.environment import (
    InstallMode,
    PackageInfo,
    PackageResolver,
    APPLICATION_NAME,
)

# Import rich.console for patching
from rich.console import Console as RichConsole


class TestInstallMode:
    """Tests for InstallMode enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert InstallMode.WHEEL == "wheel"
        assert InstallMode.EDITABLE == "editable"
        assert InstallMode.DEVELOPMENT == "development"
        assert InstallMode.UNKNOWN == "unknown"


class TestPackageInfo:
    """Tests for PackageInfo dataclass."""

    def test_creation_with_all_fields(self):
        """Test PackageInfo can be created with all fields."""
        info = PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=Path("/dist"),
            project_root=Path("/project"),
            install_mode=InstallMode.EDITABLE,
            is_installed=True,
        )
        assert info.package_name == "test"
        assert info.import_root == Path("/import")
        assert info.distribution_root == Path("/dist")
        assert info.project_root == Path("/project")
        assert info.install_mode == InstallMode.EDITABLE
        assert info.is_installed is True

    def test_str_representation(self):
        """Test __str__ returns formatted string."""
        info = PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=Path("/dist"),
            project_root=Path("/project"),
            install_mode=InstallMode.EDITABLE,
            is_installed=True,
        )
        str_repr = str(info)
        assert "Package Information: test" in str_repr
        assert "✓ Installed" in str_repr
        assert "editable" in str_repr
        assert "/import" in str_repr
        assert "/dist" in str_repr
        assert "/project" in str_repr

    def test_str_representation_not_installed(self):
        """Test __str__ for not installed package."""
        info = PackageInfo(
            package_name="test",
            import_root=None,
            distribution_root=None,
            project_root=None,
            install_mode=InstallMode.UNKNOWN,
            is_installed=False,
        )
        str_repr = str(info)
        assert "✗ Not Installed" in str_repr
        assert "unknown" in str_repr
        assert "N/A" in str_repr

    def test_display_method(self, mocker):
        """Test display method uses rich table."""
        mock_console_class = mocker.patch("rich.console.Console")
        mock_console_instance = MagicMock()
        mock_console_class.return_value = mock_console_instance

        info = PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=Path("/dist"),
            project_root=Path("/project"),
            install_mode=InstallMode.WHEEL,
            is_installed=True,
        )
        info.display()

        mock_console_class.assert_called_once()
        mock_console_instance.print.assert_called()


class TestPackageResolver:
    """Tests for PackageResolver class."""

    def test_init_defaults(self):
        """Test PackageResolver initializes with defaults."""
        resolver = PackageResolver()
        assert resolver.package_name == APPLICATION_NAME
        assert resolver.markers == ("pyproject.toml", "setup.cfg", "setup.py", ".git")

    def test_init_custom_package(self):
        """Test PackageResolver with custom package name."""
        resolver = PackageResolver("custom_package")
        assert resolver.package_name == "custom_package"

    def test_init_custom_markers(self):
        """Test PackageResolver with custom markers."""
        markers = ("custom.txt", "marker.py")
        resolver = PackageResolver(markers=markers)
        assert resolver.markers == markers

    @patch("epanetparser.core.environment.import_module")
    def test_import_root_success(self, mock_import):
        """Test _import_root returns module parent directory."""
        mock_module = MagicMock()
        mock_module.__file__ = "/path/to/package/__init__.py"
        mock_import.return_value = mock_module

        resolver = PackageResolver()
        result = resolver._import_root()

        assert result == Path("/path/to/package").resolve()

    @patch("epanetparser.core.environment.import_module")
    def test_import_root_namespace_package(self, mock_import):
        """Test _import_root handles namespace packages."""
        mock_module = MagicMock()
        mock_module.__file__ = None
        mock_module.__path__ = ["/path/to/namespace"]
        mock_import.return_value = mock_module

        resolver = PackageResolver()
        result = resolver._import_root()

        assert result == Path("/path/to/namespace").resolve()

    @patch("epanetparser.core.environment.import_module")
    def test_import_root_module_not_found(self, mock_import):
        """Test _import_root returns None when module not found."""
        mock_import.side_effect = ModuleNotFoundError()

        resolver = PackageResolver()
        result = resolver._import_root()

        assert result is None

    @patch("epanetparser.core.environment.distribution")
    def test_distribution_root_success(self, mock_distribution):
        """Test _distribution_root returns distribution location."""
        mock_dist = MagicMock()
        mock_dist.locate_file.return_value = "/site-packages/package"
        mock_distribution.return_value = mock_dist

        resolver = PackageResolver()
        result = resolver._distribution_root()

        assert result == Path("/site-packages/package").resolve()

    @patch("epanetparser.core.environment.distribution")
    def test_distribution_root_not_found(self, mock_distribution):
        """Test _distribution_root returns None when package not found."""
        from importlib.metadata import PackageNotFoundError
        mock_distribution.side_effect = PackageNotFoundError()

        resolver = PackageResolver()
        result = resolver._distribution_root()

        assert result is None

    def test_project_root_found(self, mocker):
        """Test _project_root finds project root with marker."""
        resolver = PackageResolver()
        
        # Mock _import_root to return a path
        mocker.patch.object(resolver, "_import_root", return_value=Path("/project/src/package"))
        
        # Mock Path.exists to return True for pyproject.toml
        mock_path = mocker.patch("epanetparser.core.environment.Path")
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__.side_effect = lambda x: MagicMock(
            exists=lambda: x.name == "pyproject.toml",
            name=x.name
        )
        mock_path.return_value = mock_path_instance
        
        # Actually, let's test the actual logic more directly
        # The _project_root searches upward from import_root for markers
        # We'll mock the filesystem traversal
        
        with patch.object(resolver, "_import_root", return_value=Path("/project/src/package")):
            # Create a temporary directory structure for testing
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                project_root = Path(tmpdir) / "project"
                project_root.mkdir()
                (project_root / "pyproject.toml").touch()
                
                src_package = project_root / "src" / "package"
                src_package.mkdir(parents=True)
                
                resolver_mock = PackageResolver()
                with patch.object(resolver_mock, "_import_root", return_value=src_package):
                    result = resolver_mock._project_root()
                    assert result == project_root

    def test_project_root_not_found(self, mocker):
        """Test _project_root returns None when no marker found."""
        resolver = PackageResolver()
        
        with patch.object(resolver, "_import_root", return_value=Path("/deep/nested/path")):
            # No markers in the path
            with patch("epanetparser.core.environment.Path.exists", return_value=False):
                result = resolver._project_root()
                assert result is None

    def test_project_root_no_import_root(self):
        """Test _project_root returns None when no import root."""
        resolver = PackageResolver()
        with patch.object(resolver, "_import_root", return_value=None):
            result = resolver._project_root()

        assert result is None

    @patch("epanetparser.core.environment.import_module")
    @patch("epanetparser.core.environment.distribution")
    def test_resolve_editable_mode(self, mock_distribution, mock_import):
        """Test resolve detects EDITABLE mode."""
        # Import root inside project root, distribution exists
        mock_module = MagicMock()
        mock_module.__file__ = "/project/src/package/__init__.py"
        mock_import.return_value = mock_module

        mock_dist = MagicMock()
        mock_dist.locate_file.return_value = "/site-packages"
        mock_distribution.return_value = mock_dist

        resolver = PackageResolver()
        with patch.object(resolver, "_project_root", return_value=Path("/project")):
            info = resolver.resolve()

        assert info.install_mode == InstallMode.EDITABLE
        assert info.is_installed is True
        assert info.import_root == Path("/project/src/package").resolve()
        assert info.project_root == Path("/project").resolve()

    @patch("epanetparser.core.environment.import_module")
    @patch("epanetparser.core.environment.distribution")
    def test_resolve_wheel_mode(self, mock_distribution, mock_import):
        """Test resolve detects WHEEL mode."""
        # Import root inside distribution root, no project root
        mock_module = MagicMock()
        mock_module.__file__ = "/site-packages/package/__init__.py"
        mock_import.return_value = mock_module

        mock_dist = MagicMock()
        mock_dist.locate_file.return_value = "/site-packages"
        mock_distribution.return_value = mock_dist

        resolver = PackageResolver()
        with patch.object(resolver, "_project_root", return_value=None):
            info = resolver.resolve()

        assert info.install_mode == InstallMode.WHEEL
        assert info.is_installed is True

    @patch("epanetparser.core.environment.import_module")
    @patch("epanetparser.core.environment.distribution")
    def test_resolve_development_mode(self, mock_distribution, mock_import):
        """Test resolve detects DEVELOPMENT mode."""
        # Import root has project root, no distribution
        mock_module = MagicMock()
        mock_module.__file__ = "/project/src/package/__init__.py"
        mock_import.return_value = mock_module

        from importlib.metadata import PackageNotFoundError
        mock_distribution.side_effect = PackageNotFoundError()

        resolver = PackageResolver()
        with patch.object(resolver, "_project_root", return_value=Path("/project")):
            info = resolver.resolve()

        assert info.install_mode == InstallMode.DEVELOPMENT
        assert info.is_installed is True

    @patch("epanetparser.core.environment.import_module")
    @patch("epanetparser.core.environment.distribution")
    def test_resolve_unknown_mode(self, mock_distribution, mock_import):
        """Test resolve detects UNKNOWN mode."""
        mock_import.side_effect = ModuleNotFoundError()
        from importlib.metadata import PackageNotFoundError
        mock_distribution.side_effect = PackageNotFoundError()

        resolver = PackageResolver()
        info = resolver.resolve()

        assert info.install_mode == InstallMode.UNKNOWN
        assert info.is_installed is False

    def test_resource_path(self, mocker):
        """Test resource_path returns correct path."""
        mock_files = mocker.patch("epanetparser.core.environment.files")
        mock_files.return_value.joinpath.return_value = "/package/data/config.yaml"

        resolver = PackageResolver()
        result = resolver.resource_path("data", "config.yaml")

        mock_files.assert_called_once_with(APPLICATION_NAME)
        assert result == Path("/package/data/config.yaml")

    def test_is_editable_property(self, mocker):
        """Test is_editable property."""
        resolver = PackageResolver()
        mocker.patch.object(resolver, "resolve", return_value=PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=Path("/dist"),
            project_root=Path("/project"),
            install_mode=InstallMode.EDITABLE,
            is_installed=True,
        ))
        assert resolver.is_editable is True

    def test_is_wheel_property(self, mocker):
        """Test is_wheel property."""
        resolver = PackageResolver()
        mocker.patch.object(resolver, "resolve", return_value=PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=Path("/dist"),
            project_root=Path("/project"),
            install_mode=InstallMode.WHEEL,
            is_installed=True,
        ))
        assert resolver.is_wheel is True

    def test_is_development_property(self, mocker):
        """Test is_development property."""
        resolver = PackageResolver()
        mocker.patch.object(resolver, "resolve", return_value=PackageInfo(
            package_name="test",
            import_root=Path("/import"),
            distribution_root=None,
            project_root=Path("/project"),
            install_mode=InstallMode.DEVELOPMENT,
            is_installed=True,
        ))
        assert resolver.is_development is True

    def test_detect_install_mode_editable(self):
        """Test detect_install_mode for EDITABLE."""
        resolver = PackageResolver()
        mode = resolver.detect_install_mode(
            import_root=Path("/project/src/package"),
            distribution_root=Path("/site-packages"),
            project_root=Path("/project"),
        )
        assert mode == InstallMode.EDITABLE

    def test_detect_install_mode_wheel(self):
        """Test detect_install_mode for WHEEL."""
        resolver = PackageResolver()
        mode = resolver.detect_install_mode(
            import_root=Path("/site-packages/package"),
            distribution_root=Path("/site-packages"),
            project_root=None,
        )
        assert mode == InstallMode.WHEEL

    def test_detect_install_mode_development(self):
        """Test detect_install_mode for DEVELOPMENT."""
        resolver = PackageResolver()
        mode = resolver.detect_install_mode(
            import_root=Path("/project/src/package"),
            distribution_root=None,
            project_root=Path("/project"),
        )
        assert mode == InstallMode.DEVELOPMENT

    def test_detect_install_mode_unknown_no_import(self):
        """Test detect_install_mode for UNKNOWN when no import root."""
        resolver = PackageResolver()
        mode = resolver.detect_install_mode(
            import_root=None,
            distribution_root=Path("/site-packages"),
            project_root=Path("/project"),
        )
        assert mode == InstallMode.UNKNOWN

    def test_detect_install_mode_unknown_no_match(self):
        """Test detect_install_mode for UNKNOWN when no path matches."""
        resolver = PackageResolver()
        mode = resolver.detect_install_mode(
            import_root=Path("/other/path"),
            distribution_root=Path("/site-packages"),
            project_root=Path("/project"),
        )
        assert mode == InstallMode.UNKNOWN

    def test_main_block_code_structure(self):
        """Test that main block code structure is present."""
        import inspect
        from epanetparser.core import environment

        source = inspect.getsource(environment)
        assert "if __name__ == \"__main__\":" in source
        assert "PackageResolver" in source
        assert "resolver.resolve()" in source
        assert "info.display()" in source
        assert "resolver.resource_path" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])