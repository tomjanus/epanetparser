"""Package environment detection and resource location utilities.

This module provides robust package resolution for different installation modes
including editable installs, wheel installs, and development environments. It
helps locate package resources, determine installation modes, and find project 
roots.

Key Components
--------------
InstallMode : Enum
    Enumeration of possible package installation modes.
PackageInfo : dataclass
    Container for resolved package information.
PackageResolver : class
    Main resolver for package paths and resources.

Examples
--------
>>> from epanetparser.environment import PackageResolver
>>> resolver = PackageResolver("epanetparser")
>>> info = resolver.resolve()
>>> print(info.install_mode)
InstallMode.EDITABLE
>>> config_path = resolver.resource_path("data", "config.yaml")

Notes
-----
Supports the following installation modes:
- pip install -e . (editable)
- pip install . (wheel)
- Direct execution from source (development)
- Namespace packages
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from importlib.metadata import PackageNotFoundError, distribution
from importlib.resources import files
from pathlib import Path
from typing import Optional
from rich import print as rprint


APPLICATION_NAME = "epanetparser"


class InstallMode(str, Enum):
    """Detected installation/runtime mode.
    
    Attributes
    ----------
    WHEEL : str
        Standard wheel install in site-packages.
    EDITABLE : str
        Editable install (pip install -e).
    DEVELOPMENT : str
        Running directly from source without installation.
    UNKNOWN : str
        Installation mode cannot be determined.
    """

    WHEEL = "wheel"
    EDITABLE = "editable"
    DEVELOPMENT = "development"
    UNKNOWN = "unknown"
    
    
@dataclass(frozen=True)
class PackageInfo:
    """Resolved package information.
    
    Attributes
    ----------
    package_name : str
        Name of the package.
    import_root : Optional[Path]
        Directory where Python imports code from.
    distribution_root : Optional[Path]
        Directory where the distribution is installed (e.g., site-packages).
    project_root : Optional[Path]
        Project root directory containing pyproject.toml or .git, if available.
    install_mode : InstallMode
        Detected installation/runtime mode.
    is_installed : bool
        Whether the package is importable.
    """
    package_name: str
    # Where Python imports code from
    import_root: Optional[Path]
    # Where the distribution is installed
    distribution_root: Optional[Path]
    # Project root (contains pyproject.toml/.git), if available
    project_root: Optional[Path]
    # Installation/runtime mode
    install_mode: InstallMode
    # Whether package is importable
    is_installed: bool
    
    def __str__(self) -> str:
        """Return formatted string representation of package information.
        
        Returns
        -------
        str
            Formatted multi-line string with all package information.
        """
        lines = [
            f"Package Information: {self.package_name}",
            "=" * 60,
            f"  Installation Status : {'✓ Installed' if self.is_installed else '✗ Not Installed'}",
            f"  Installation Mode   : {self.install_mode.value}",
            f"  Import Root         : {self.import_root or 'N/A'}",
            f"  Distribution Root   : {self.distribution_root or 'N/A'}",
            f"  Project Root        : {self.project_root or 'N/A'}",
            "=" * 60,
        ]
        return "\n".join(lines)
    
    def display(self) -> None:
        """Display package information with rich formatting.
        
        Uses the rich library to print a nicely formatted table of
        package information to the console.
        
        Examples
        --------
        >>> info = resolver.resolve()
        >>> info.display()
        """
        from rich.table import Table
        from rich.console import Console
        
        console = Console()
        table = Table(title=f"[bold]Package Information: {self.package_name}[/bold]")
        
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        status_emoji = "✓" if self.is_installed else "✗"
        status_color = "green" if self.is_installed else "red"
        table.add_row(
            "Installation Status",
            f"[{status_color}]{status_emoji} {'Installed' if self.is_installed else 'Not Installed'}[/{status_color}]"
        )
        
        mode_color = {
            InstallMode.EDITABLE: "yellow",
            InstallMode.WHEEL: "green",
            InstallMode.DEVELOPMENT: "blue",
            InstallMode.UNKNOWN: "red"
        }.get(self.install_mode, "white")
        table.add_row(
            "Installation Mode",
            f"[{mode_color}]{self.install_mode.value}[/{mode_color}]"
        )
        
        table.add_row("Import Root", str(self.import_root) if self.import_root else "[dim]N/A[/dim]")
        table.add_row("Distribution Root", str(self.distribution_root) if self.distribution_root else "[dim]N/A[/dim]")
        table.add_row("Project Root", str(self.project_root) if self.project_root else "[dim]N/A[/dim]")
        
        console.print(table)


class PackageResolver:
    """Robust package resolver supporting multiple installation modes.
    
    This resolver supports:
    - Editable installs (pip install -e)
    - Wheel/site-packages installs
    - Src-layout projects
    - Local development overrides
    - Namespace packages
    
    Parameters
    ----------
    package_name : str, optional
        Name of the package to resolve, by default APPLICATION_NAME.
    markers : tuple[str, ...], optional
        File/directory names that indicate project root, by default
        ("pyproject.toml", "setup.cfg", "setup.py", ".git").
    
    Attributes
    ----------
    package_name : str
        Name of the package being resolved.
    markers : tuple[str, ...]
        File/directory markers used to identify project root.
    
    Examples
    --------
    >>> resolver = PackageResolver("epanetparser")
    >>> info = resolver.resolve()
    >>> print(info.import_root)
    PosixPath('/home/user/project/epanetparser')
    >>> print(info.distribution_root)
    PosixPath('/home/user/.venv/lib/python3.11/site-packages')
    >>> print(info.project_root)
    PosixPath('/home/user/project')
    >>> print(info.install_mode)
    InstallMode.EDITABLE
    >>> config = resolver.resource_path("data", "config.yaml")
    """

    DEFAULT_MARKERS = ("pyproject.toml", "setup.cfg", "setup.py", ".git")

    def __init__(
        self,
        package_name: str = APPLICATION_NAME,
        markers: tuple[str, ...] = DEFAULT_MARKERS,
    ) -> None:
        self.package_name = package_name
        self.markers = markers

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def resolve(self) -> PackageInfo:
        """Resolve all package information.
        
        Returns
        -------
        PackageInfo
            Dataclass containing all resolved package paths and metadata.
        """

        import_root = self._import_root()
        distribution_root = self._distribution_root()
        project_root = self._project_root()

        mode = self.detect_install_mode(
            import_root=import_root,
            distribution_root=distribution_root,
            project_root=project_root,
        )

        return PackageInfo(
            package_name=self.package_name,
            import_root=import_root,
            distribution_root=distribution_root,
            project_root=project_root,
            install_mode=mode,
            is_installed=import_root is not None
            or distribution_root is not None,
        )

    def _import_root(self) -> Optional[Path]:
        """Return where Python is actually importing code from.
        
        Returns
        -------
        Optional[Path]
            Directory from which the package is imported, or None if
            the package is not importable.
        """
        try:
            module = import_module(self.package_name)
        except ModuleNotFoundError:
            return None
        module_file = getattr(module, "__file__", None)
        # Regular package/module
        if module_file:
            return Path(module_file).resolve().parent
        # Namespace package fallback
        module_path = getattr(module, "__path__", None)
        if module_path:
            return Path(list(module_path)[0]).resolve()
        return None

    def _distribution_root(self) -> Optional[Path]:
        """Return pip-installed distribution location.
        
        Returns
        -------
        Optional[Path]
            Distribution directory, or None if not installed via pip.
            For wheel installs: .../site-packages/
            For editable installs: often still site-packages, but linked to source tree.
        """
        try:
            dist = distribution(self.package_name)
            return Path(dist.locate_file("")).resolve()
        except PackageNotFoundError:
            return None

    def _project_root(self) -> Optional[Path]:
        """Attempt to locate development/project root.
        
        Searches upward from the import root for project markers
        (pyproject.toml, .git, etc.).
        
        Returns
        -------
        Optional[Path]
            Project root directory for editable/dev installs, or None
            for wheel installs where no project root is available.
        """
        start = self._import_root()
        if start is None:
            return None
        current = start.resolve()
        while current != current.parent:
            if any((current / marker).exists() for marker in self.markers):
                return current
            current = current.parent
        return None

    def resource_path(self, *parts: str) -> Path:
        """Return path to packaged resource.
        
        Parameters
        ----------
        *parts : str
            Path components relative to the package root.
        
        Returns
        -------
        Path
            Path to the requested resource within the package.
        
        Examples
        --------
        >>> resolver.resource_path("data", "config.yaml")
        PosixPath('.../epanetparser/data/config.yaml')
        >>> resolver.resource_path("networks", "core", "Net1.inp")
        PosixPath('.../epanetparser/networks/core/Net1.inp')
        """
        return Path(files(self.package_name).joinpath(*parts))

    # -------------------------------------------------------------------------
    # Install mode detection
    # -------------------------------------------------------------------------

    def detect_install_mode(
        self,
        import_root: Optional[Path],
        distribution_root: Optional[Path],
        project_root: Optional[Path],
    ) -> InstallMode:
        """Detect installation/runtime mode.
        
        Parameters
        ----------
        import_root : Optional[Path]
            Directory where code is imported from.
        distribution_root : Optional[Path]
            Directory where distribution is installed.
        project_root : Optional[Path]
            Project root directory, if found.
        
        Returns
        -------
        InstallMode
            Detected installation mode (WHEEL, EDITABLE, DEVELOPMENT, or UNKNOWN).
        """
        if import_root is None:
            return InstallMode.UNKNOWN
        # Development override:
        # importing directly from a repo checkout
        if project_root is not None:
            if distribution_root is None:
                return InstallMode.DEVELOPMENT
            try:
                import_root.relative_to(project_root)
                return InstallMode.EDITABLE
            except ValueError:
                pass
        # Standard wheel install
        if distribution_root is not None:
            try:
                import_root.relative_to(distribution_root)
                return InstallMode.WHEEL
            except ValueError:
                pass
        return InstallMode.UNKNOWN

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------

    @property
    def is_editable(self) -> bool:
        """Check if package is installed in editable mode.
        
        Returns
        -------
        bool
            True if package is installed with pip install -e.
        """
        return self.resolve().install_mode == InstallMode.EDITABLE

    @property
    def is_wheel(self) -> bool:
        """Check if package is installed as a wheel.
        
        Returns
        -------
        bool
            True if package is installed as a standard wheel in site-packages.
        """
        return self.resolve().install_mode == InstallMode.WHEEL

    @property
    def is_development(self) -> bool:
        """Check if package is running in development mode.
        
        Returns
        -------
        bool
            True if running directly from source without installation.
        """
        return self.resolve().install_mode == InstallMode.DEVELOPMENT


if __name__ == "__main__":
    resolver = PackageResolver(APPLICATION_NAME)
    info = resolver.resolve()
    
    # Method 1: Simple print using __str__
    rprint("\n" + "=" * 60)
    rprint("Method 1: Using print(info)")
    rprint("=" * 60)
    rprint(info)
    
    # Method 2: Rich formatted display
    rprint("\n" + "=" * 60)
    rprint("Method 2: Using info.display()")
    rprint("=" * 60)
    info.display()
    
    # Additional info
    rprint("\n" + "=" * 60)
    rprint("Additional Examples")
    rprint("=" * 60)
    rprint("Resource path example:", resolver.resource_path("networks", "extra"))