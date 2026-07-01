"""
Validation descriptor for EPANET component types.

This module provides a descriptor-based validator that automatically executes validation 
rules and warning checks whenever component data is assigned to an object attribute.

The validator follows the Python descriptor protocol and integrates
with component classes that define ``rule_*`` and ``warn_*`` methods.
"""
from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING, List, Tuple, Dict, TypeAlias
from collections.abc import Callable
import inspect
import json
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.core.epanettypes.validation_warnings import WNTREPANETTypeValidationWarning
if TYPE_CHECKING:
    from epanetparser.core.epanet_types.base import WNTREPANETType

FuncName: TypeAlias = str
RuleTrace: TypeAlias = str


class WNTREPANETTypeValidator:
    """
    Descriptor-based validator for EPANET component data.

    The validator automatically intercepts attribute assignment and
    executes validation logic whenever new data is assigned.

    Validation is performed by discovering and executing methods
    defined on the owning instance:

    - ``rule_*`` methods define mandatory validation rules
    - ``warn_*`` methods define non-fatal warning checks

    Any ``AssertionError`` raised inside a rule method is converted
    into a :class:`WNTREPANETTypeValidationError`.

    Any ``AssertionError`` raised inside a warning method is converted
    into a :class:`WNTREPANETTypeValidationWarning`.

    Notes
    -----
    This class implements Python's descriptor protocol through:

    This allows validation to happen automatically during attribute
    assignment without requiring explicit validation calls.

    Parameters
    ----------
    max_value_len : int, optional
        Maximum length of serialized values included in validation
        messages. Longer values are truncated.
        Default is ``200``.

    store_passed_rules : bool, optional
        If ``True``, names of successfully executed validation rules
        are stored on the validated instance in ``rules_passed``.
        Default is ``False``.

    Attributes
    ----------
    max_value_len : int
        Maximum length for serialized values in messages.

    store_passed_rules : bool
        Whether successful rules are stored on instances.

    instattr : str
        Name of the private instance attribute used for storing
        validated data.

    Examples
    --------
    Basic usage:

    >>> class Pipe:
    ...     data = WNTREPANETTypeValidator()
    ...
    ...     def __init__(self, data):
    ...         self.data = data
    ...
    ...     def rule_diameter_positive(self):
    ...         assert self.data["diameter"] > 0, \
    ...             "Diameter must be positive"

    >>> pipe = Pipe({"diameter": 100})

    Invalid assignment:

    >>> pipe = Pipe({"diameter": -5})
    Traceback (most recent call last):
        ...
    WNTREPANETTypeValidationErrorBundle
    """

    def __init__(
            self,
            max_value_len: int = 200,
            store_passed_rules: bool = False) -> None:
        """
        Initialize the validator descriptor.

        Parameters
        ----------
        max_value_len : int, optional
            Maximum number of characters allowed in serialized values
            shown in error and warning messages.

        store_passed_rules : bool, optional
            Whether to store successfully executed rule names on the
            validated instance.
        """
        self.max_value_len = int(max_value_len)
        self.store_passed_rules = store_passed_rules
        self.instattr: str = ''  # Set by __set_name__ during class creation


    def __set_name__(self, inst: type, name: str) -> None:
        """
        Configure descriptor during class creation and determines the internal 
        attribute name used to store validated values on instances.

        Parameters
        ----------
        owner : type
            Class owning the descriptor.

        name : str
            Name of the managed attribute.

        Examples
        --------
        Given:

        >>> class Pipe:
        ...     data = WNTREPANETTypeValidator()

        Python automatically executes:

        >>> validator.__set_name__(Pipe, "data")

        resulting in:

        >>> self.instattr == "_data"
        """
        self.instattr = '_' + name


    def __get__(
            self,
            inst: Optional[WNTREPANETType],
            dtype: Optional[type] = None) -> Any:
        """
        Retrieve validated data from an instance.

        This method is automatically triggered whenever the managed
        attribute is accessed.

        Parameters
        ----------
        inst : WNTREPANETType or None
            Instance from which the value is retrieved.

            If ``None``, the descriptor itself is returned.
            This occurs during class-level access.

        dtype : type, optional
            Owner class type.

        Returns
        -------
        Any
            Stored validated value.

        Notes
        -----
        Python internally translates:

        >>> obj.data

        into:

        >>> descriptor.__get__(obj, type(obj))

        while:

        >>> MyClass.data

        becomes:

        >>> descriptor.__get__(None, MyClass)
        """
        if inst is None:
            return self
        return getattr(inst, self.instattr)


    def __set__(self, inst: WNTREPANETType, value: dict) -> None:
        """
        Assign and validate component data.

        This method is automatically triggered whenever the managed
        attribute is assigned.

        The value is first stored internally and then validated.

        Parameters
        ----------
        inst : WNTREPANETType
            Instance receiving the value.

        value : dict
            Component data to validate.

        Raises
        ------
        WNTREPANETTypeValidationErrorBundle
            Raised if one or more validation rules fail.

        Notes
        -----
        Python internally translates:

        >>> obj.data = value

        into:

        >>> descriptor.__set__(obj, value)
        """
        setattr(inst, self.instattr, value)
        self.validate(inst, value)


    def validate(self, inst: WNTREPANETType, value: dict) -> None:
        """
        Execute validation rules and warning checks, including warning and
        validation rules in plugins.

        The method dynamically discovers methods on the instance:

        - ``rule_*`` methods are treated as validation rules
        - ``warn_*`` methods are treated as warning checks

        Rules and warnings are expected to raise ``AssertionError``
        when validation conditions fail.

        Parameters
        ----------
        inst : WNTREPANETType
            Component instance being validated.

        value : dict
            Component data.

        Raises
        ------
        WNTREPANETTypeValidationErrorBundle
            Raised if any validation rule fails.
        """
        # Dunamically discover rule and warning methods on the instance
        ifuncs: List[Tuple[FuncName, Any]] = inspect.getmembers(inst, inspect.ismethod)
        irules: Dict[FuncName, Callable[[], Any]] = {n: f for n, f in ifuncs if n.startswith("rule")}
        iwarns: Dict[FuncName, Callable[[], Any]] = {n: f for n, f in ifuncs if n.startswith("warn")}
        rules_passed: Dict[FuncName, RuleTrace] = {}
        # Record exceptions and warnings as lists of validation error/warning objects
        exc_bundle: List[WNTREPANETTypeValidationError] = []
        warn_bundle: List[WNTREPANETTypeValidationWarning] = []
        # Trim the value for inclusion in error/warning messages
        value_text = self.trim_value(value)
        # Process warnings
        for _func_name, _func in iwarns.items():
            try:
                _func()
            except AssertionError as err:
                warn_bundle.append(
                    WNTREPANETTypeValidationWarning(
                        inst.__class__.__qualname__, _func_name, err, value_text
                    )
                )
        # Process rules
        for _func_name, _func in irules.items():
            try:
                result = _func()
                if self.store_passed_rules:
                    rules_passed[_func_name] = f"[PASSED] {_func_name} -> {result}"
            except AssertionError as err:
                exc_bundle.append(
                    WNTREPANETTypeValidationError(
                        inst.__class__.__qualname__, _func_name, err, value_text
                    )
                )
        if self.store_passed_rules:
            inst.rules_passed = rules_passed
        if exc_bundle:
            raise WNTREPANETTypeValidationErrorBundle(
                f"{inst.__class__.__qualname__} rule failures", exc_bundle
            )
        inst.warnings = warn_bundle

    def trim_value(self, value: dict) -> str:
        """
        Serialize and truncate validation values.

        The value dictionary is converted to JSON for inclusion
        in error and warning messages.

        Long strings are truncated to improve readability.

        Parameters
        ----------
        value : dict
            Value to serialize.

        Returns
        -------
        str
            Serialized and optionally truncated JSON string.
        """
        value_text = json.dumps(value)
        remainder = len(value_text) - self.max_value_len
        if remainder > 0:
            s = "s" if remainder > 1 else ""
            value_text = value_text[:self.max_value_len] + f"...[+{remainder} char{s}]"
        return value_text


if __name__ == "__main__":
    """Interactive demonstration of WNTREPANETTypeValidator.
    
    This demo showcases:
    - Automatic validation on attribute assignment
    - Rule execution and error bundling
    - Warning checks and collection
    - Passed rule tracking
    - Value truncation in error messages
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import box
    from epanetparser.core.decorators import described
    from epanetparser.core.epanettypes.base import (
        WNTREPANETType, WNTREPANETTypeValidator
    )
    
    console = Console()
    #console.print("\n[bold cyan]═══ WNTREPANETTypeValidator Demo ═══[/bold cyan]\n")
    console.rule("[bold cyan]WNTREPANETTypeValidator Demo[/bold cyan]", style="bold cyan")
    console.print()
    
    # Define mock component classes for demonstration
    class Pipe(WNTREPANETType):
        """Mock Pipe component with validation rules and warnings."""
        data = WNTREPANETTypeValidator(store_passed_rules=True, max_value_len=100)
        def __init__(self, data): # pylint: disable=super-init-not-called
            self.data = data

        @property
        def type(self) -> str:
            return self.data.get("type")

        @described
        def rule_positive_diameter(self):
            """Diameter must be greater than zero."""
            assert self.data["diameter"] > 0, "Diameter must be positive"

        @described
        def rule_has_length(self):
            """Length field must be present."""
            assert "length" in self.data, "Length field is required"
        
        @described
        def rule_valid_material(self):
            """Material must be in allowed list."""
            allowed = ["PVC", "Steel", "Copper", "Cast Iron"]
            material = self.data.get("material", "PVC")
            assert material in allowed, f"Material '{material}' not in {allowed}"

        def warn_large_diameter(self):
            """Warn if diameter exceeds typical range."""
            assert self.data["diameter"] < 5000, "Diameter unusually large (>5000mm)"
        
        def warn_short_pipe(self):
            """Warn if pipe is very short."""
            length = self.data.get("length", 0)
            assert length >= 10, "Pipe length very short (<10m)"
    
    class Junction(WNTREPANETType):
        """Mock Junction component with different validation rules."""
        
        data = WNTREPANETTypeValidator(store_passed_rules=False)
        
        def __init__(self, data):  # pylint: disable=super-init-not-called
            self.data = data
            
        @property
        def type(self) -> str:
            return self.data.get("type")
        
        def rule_has_elevation(self):
            """Elevation field is required."""
            assert "elevation" in self.data, "Elevation is required for junctions"
        
        def rule_valid_demand(self):
            """Demand must be non-negative."""
            demand = self.data.get("demand", 0)
            assert demand >= 0, "Demand cannot be negative"
        
        def warn_high_elevation(self):
            """Warn about unusually high elevation."""
            elevation = self.data.get("elevation", 0)
            assert elevation < 1000, "Elevation very high (>1000m)"
    
    # Demo 1: Successful validation
    console.print("[bold]Demo 1: Successful Validation[/bold]", justify='center')
    console.print("\n[bold]Creating a valid pipe:[/bold]")
    valid_pipe_data = {
        "diameter": 200,
        "length": 1500,
        "material": "PVC",
        "roughness": 100
    }
    console.print(Panel(
        Syntax(f"pipe = Pipe({valid_pipe_data})", "python", theme="monokai"),
        title="[green]Input Data[/green]",
        border_style="green"
    ))
    
    try:
        pipe = Pipe(valid_pipe_data)
        console.print("✅ [bold green]Validation successful![/bold green]\n")
        
        # Show validation results
        results_table = Table(title="Validation Results", box=box.ROUNDED)
        results_table.add_column("Aspect", style="cyan")
        results_table.add_column("Value", style="white")
        
        results_table.add_row("Data Stored", f"✓ {len(pipe.data)} fields")
        results_table.add_row("Rules Passed", f"✓ {len(pipe.rules_passed)} rules")
        results_table.add_row("Warnings", f"{'⚠ ' + str(len(pipe.warnings)) if pipe.warnings else '✓ None'}")
        
        console.print(results_table)
        console.print()
        
        if pipe.rules_passed:
            console.print("[bold]Passed Rules:[/bold]")
            for rule_name, rule_trace in pipe.rules_passed.items():
                console.print(f"  • [green]{rule_trace}[/green]")
                rule = pipe.get_rule(rule_name)
                description = getattr(rule, "description", None)
                if description:
                    console.print(f"    [blue]Rule description: [/blue][dim]{rule.description}[/dim]")
                else:
                    console.print(f"    [blue]Rule description: [/blue][dim]No description available[/dim]")
        if pipe.warnings:
            console.print("\n[bold]Warnings:[/bold]")
            for warning in pipe.warnings:
                console.print(f"  • [yellow]{warning}[/yellow]")
    except WNTREPANETTypeValidationErrorBundle as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
    
    console.print()
    
    # Demo 2: Validation with warnings
    console.print("[bold]Demo 2: Validation with Warnings[/bold]", justify='center')
    console.print("\n[bold]Creating a pipe that triggers warnings but doesn't trigger errors:[/bold]")
    
    warning_pipe_data = {
        "diameter": 6000,  # Will trigger large diameter warning
        "length": 5,       # Will trigger short pipe warning
        "material": "Steel"
    }
    
    console.print(Panel(
        Syntax(f"pipe2 = Pipe({warning_pipe_data})", "python", theme="monokai"),
        title="[yellow]Input Data (with warning triggers)[/yellow]",
        border_style="yellow"
    ))
    
    try:
        pipe2 = Pipe(warning_pipe_data)
        console.print("✅ [bold green]Validation successful![/bold green]")
        
        if pipe2.warnings:
            print(pipe2.warnings)
            console.print(f"\n⚠️  [bold yellow]Warnings detected ({len(pipe2.warnings)}):[/bold yellow]")
            for i, warning in enumerate(pipe2.warnings, 1):
                console.print(Panel(
                    f"[dim]Rule: {warning.warning}[/dim]\n"
                    f"[dim]Component: {warning.component}[/dim]\n"
                    f"[dim]Message: {warning.exc}[/dim]\n"
                    f"[dim]Value: {warning.valuetext}[/dim]",
                    title=f"[bold]{warning.message}[/bold]",
                    border_style="yellow"
                ))
        
    except WNTREPANETTypeValidationErrorBundle as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
    
    console.print()
    
    # Demo 3: Validation failures (rule violations)
    console.print("[bold]Demo 3: Validation Failures (Rule Violations)[/bold]", justify='center')
    console.print("\n[bold]Creating a pipe with invalid data:[/bold]")
    
    invalid_pipe_data = {
        "diameter": -100,  # Invalid: negative diameter
        # "length" is missing - required field
        "material": "Wood"  # Invalid: not in allowed materials
    }
    
    console.print(Panel(
        Syntax(f"pipe3 = Pipe({invalid_pipe_data})", "python", theme="monokai"),
        title="[red]Input Data (with violations)[/red]",
        border_style="red"
    ))
    
    try:
        pipe3 = Pipe(invalid_pipe_data)
        console.print("✅ [bold green]Validation successful![/bold green]")
    except WNTREPANETTypeValidationErrorBundle as e:
        console.print(f"❌ [bold red]Validation failed![/bold red]\n")
        console.print(f"[red]Error bundle contains {len(e.bundle)} error(s):[/red]\n")
        
        for i, error in enumerate(e.bundle, 1):
            console.print(Panel(
                f"[dim]Rule: {error.rule}[/dim]\n"
                f"[dim]Component: {error.component}[/dim]\n"
                f"[dim]Message: {error.exc}[/dim]\n"
                f"[dim]Value: {error.valuetext[:80]}...[/dim]",
                title=f"[bold]{error.message}[/bold]",
                border_style="red"
            ))
    
    console.print()
    
    # Demo 4: Different component type (Junction)
    console.print("[bold]Demo 4: Different Component Type (Junction)[/bold]", justify='center')
    console.print("\n[bold]Creating a junction with different validation rules:[/bold]")
    
    valid_junction_data = {
        "name": "J1",
        "elevation": 100,
        "demand": 50
    }
    
    console.print(Panel(
        Syntax(f"junction = Junction({valid_junction_data})", "python", theme="monokai"),
        title="[green]Junction Data[/green]",
        border_style="green"
    ))
    
    try:
        junction = Junction(valid_junction_data)
        console.print("✅ [bold green]Junction validation successful![/bold green]")
        console.print(f"[dim]Note: This validator has store_passed_rules=False[/dim]")
        console.print(f"[dim]Warnings present: {len(junction.warnings) if hasattr(junction, 'warnings') else 0}[/dim]")
    except WNTREPANETTypeValidationErrorBundle as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
    
    console.print()
    
    # Demo 5: Value truncation
    console.print("[bold]Demo 5: Value Truncation in Error Messages[/bold]", justify='center')
    console.print("\n[bold]Creating a pipe with very long data to show truncation:[/bold]")
    
    long_data = {
        "diameter": -50,
        "length": 100,
        "material": "PVC",
        "description": "A" * 200,  # Very long description
        "extra_field_1": "X" * 100,
        "extra_field_2": "Y" * 100,
        "extra_field_3": "Z" * 100
    }
    
    console.print(f"[dim]Data size: {len(str(long_data))} characters[/dim]")
    console.print(f"[dim]Max value length setting: 100 characters[/dim]\n")
    
    try:
        pipe_long = Pipe(long_data)
    except WNTREPANETTypeValidationErrorBundle as e:
        console.print("[red]Validation failed (as expected)[/red]\n")
        console.print("[bold]Notice the truncated value in error message:[/bold]")
        for error in e.bundle[:1]:  # Show just first error
            console.print(Panel(
                f"[red]{error.message}[/red]\n"
                f"[yellow]Truncated value:[/yellow]\n[dim]{error.valuetext}[/dim]",
                title="Error with Truncation",
                border_style="red"
            ))
    
    console.print()
    
    # Demo 6: Descriptor protocol demonstration
    console.print("[bold]Demo 6: Descriptor Protocol in Action[/bold]", justify='center')
    console.print("\n[bold]Understanding the descriptor protocol:[/bold]\n")
    
    descriptor_table = Table(title="Descriptor Protocol Methods", box=box.ROUNDED)
    descriptor_table.add_column("Operation", style="cyan", width=30)
    descriptor_table.add_column("Descriptor Method Called", style="yellow", width=30)
    descriptor_table.add_column("Effect", style="white", width=40)
    
    descriptor_table.add_row(
        "pipe.data = {...}",
        "__set__(inst, value)",
        "Store value + trigger validation"
    )
    descriptor_table.add_row(
        "value = pipe.data",
        "__get__(inst, type)",
        "Return stored validated data"
    )
    descriptor_table.add_row(
        "Pipe.data",
        "__get__(None, Pipe)",
        "Return descriptor itself (class access)"
    )
    
    console.print(descriptor_table)
    console.print()
    
    # Demonstrate class-level vs instance-level access
    console.print("[bold]Class-level access:[/bold]")
    console.print(f"  Pipe.data = [cyan]{type(Pipe.data).__name__}[/cyan]")
    console.print()
    
    console.print("[bold]Instance-level access:[/bold]")
    valid_pipe = Pipe({"diameter": 100, "length": 50, "material": "PVC"})
    console.print(f"  valid_pipe.data = [cyan]{type(valid_pipe.data).__name__}[/cyan]")
    console.print(f"  Content: [green]{valid_pipe.data}[/green]")
    console.print()
    
    # Summary
    console.rule("[bold green]Demo Complete[/bold green]")