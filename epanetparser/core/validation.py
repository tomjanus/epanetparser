"""
Validation descriptor for EPANET component types.

This module provides a descriptor-based validator that automatically executes validation 
rules and warning checks whenever component data is assigned to an object attribute.

The validator follows the Python descriptor protocol and integrates
with component classes that define ``rule_*`` and ``warn_*`` methods.
"""
from typing import Any, Optional
import inspect
import json
from epanetparser.core.epanettypes.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.core.epanettypes.validation_warnings import WNTREPANETTypeValidationWarning


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

    def __init__(self, max_value_len: int = 200, store_passed_rules: bool = False) -> None:
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
        Configure descriptor during class creation and determines the internal attribute name used to
        store validated values on instances.

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


    def __get__(self, inst: Optional['WNTREPANETType'], dtype: Optional[type] = None) -> Any:
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


    def __set__(self, inst: 'WNTREPANETType', value: dict) -> None:
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


    def validate(self, inst: 'WNTREPANETType', value: dict) -> None:
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
        from epanetparser.core import get_plugin_registry
        
        ifuncs = inspect.getmembers(inst, inspect.ismethod)
        irules = {n: f for n, f in ifuncs if n.startswith("rule")}
        iwarns = {n: f for n, f in ifuncs if n.startswith("warn")}

        # ========== ADD PLUGIN SUPPORT ==========
        # Get plugin registry and load plugin rules/warnings
        registry = get_plugin_registry()
        component_type = inst.__class__.__name__
        # Get plugin rules/warnings and create bound methods
        plugin_rules = registry.get_rules(component_type)
        plugin_warns = registry.get_warnings(component_type)
        # Wrap plugin functions to bind to current instance
        # Using a factory function to capture the function in the closure properly
        def make_bound_func(func):
            return lambda: func(inst)
        plugin_rule_methods = {
            name: make_bound_func(func)
            for name, func in plugin_rules.items()
        }
        plugin_warn_methods = {
            name: make_bound_func(func)
            for name, func in plugin_warns.items()
        }
        # Merge plugin rules/warnings with instance rules/warnings
        irules.update(plugin_rule_methods)
        iwarns.update(plugin_warn_methods)
        # ========== END PLUGIN SUPPORT ==========
    
        rules_passed = []
        exc_bundle = []
        warn_bundle = []
        
        value_text = self.trim_value(value)

        # Process warnings
        for w, f in iwarns.items():
            try:
                f()
            except AssertionError as e:
                warn_bundle.append(
                    WNTREPANETTypeValidationWarning(
                        inst.__class__.__qualname__, w, e, value_text
                    )
                )

        # Process rules
        for r, f in irules.items():
            try:
                result = f()
                if self.store_passed_rules:
                    rules_passed.append(f"[PASSED] {r} -> {result}")
            except AssertionError as e:
                exc_bundle.append(
                    WNTREPANETTypeValidationError(
                        inst.__class__.__qualname__, r, e, value_text
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
    """ """
    class Pipe:

        data = WNTREPANETTypeValidator(
            store_passed_rules=True
        )

        def __init__(self, data):
            self.data = data

        def rule_positive_diameter(self):
            assert self.data["diameter"] > 0, (
                "Diameter must be positive"
            )

        def rule_has_length(self):
            assert "length" in self.data, (
                "Length missing"
            )

        def warn_large_diameter(self):
            assert self.data["diameter"] < 5000, (
                "Diameter unusually large"
            )
            
            
    pipe = Pipe({
        "diameter": 200,
        "length": 1500
    })

    print(pipe.data)
    print(pipe.rules_passed)
    print(pipe.warnings)
    print(pipe.__dict__)