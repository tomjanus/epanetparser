""" """
from typing import Any, Optional
import inspect
import json
from epanetparser.epanet_types.exceptions import (
    WNTREPANETTypeValidationError,
    WNTREPANETTypeValidationErrorBundle
)
from epanetparser.epanet_types.warnings import WNTREPANETTypeValidationWarning


class WNTREPANETTypeValidator:
    """Descriptor class for validating EPANET component data.
    
    This descriptor validates component data by running all 'rule_*' and 'warn_*'
    methods defined on the component class. Rules must pass (no AssertionError)
    for validation to succeed. Warnings are collected but don't prevent validation.
    
    Args:
        max_value_len: Maximum length for serialized value text in error messages.
        store_passed_rules: If True, store a list of passed rules on the instance.
    
    Attributes:
        max_value_len: Maximum length for value text in error/warning messages.
        store_passed_rules: Whether to store passed rule names on instances.
        instattr: Name of the private attribute for storing validated data.
    """

    def __init__(self, max_value_len: int = 200, store_passed_rules: bool = False) -> None:
        self.max_value_len = int(max_value_len)
        self.store_passed_rules = store_passed_rules
        self.instattr: str = ''  # Set by __set_name__ during class creation


    def __set_name__(self, inst: type, name: str) -> None:
        """Store the attribute name for this descriptor.
        
        Called automatically when the descriptor is assigned to a class attribute.
        
        Args:
            inst: The owner class.
            name: Name of the attribute this descriptor is assigned to.
        """
        self.instattr = '_' + name


    def __get__(self, inst: Optional['WNTREPANETType'], dtype: Optional[type] = None) -> Any:
        """Get the validated data from the instance.
        
        Args:
            inst: Instance to get data from (None if accessed from class).
            dtype: Type of the owner class.
        
        Returns:
            The validated data stored in the instance.
        """
        if inst is None:
            return self
        return getattr(inst, self.instattr)


    def __set__(self, inst: 'WNTREPANETType', value: dict) -> None:
        """Set and validate the component data.
        
        Stores the value and triggers validation by running all rule_* and warn_*
        methods on the instance.
        
        Args:
            inst: Instance to set data on.
            value: Dictionary of component data to validate.
        
        Raises:
            WNTREPANETTypeValidationErrorBundle: If any validation rules fail.
        """
        setattr(inst, self.instattr, value)
        self.validate(inst, value)


    def validate(self, inst: 'WNTREPANETType', value: dict) -> None:
        """Validate component data by running all rules and warnings.
        
        Collects all 'rule_*' and 'warn_*' methods from the instance and executes them.
        Failed rules are collected into an error bundle. Warnings are collected separately.
        
        Args:
            inst: Component instance to validate.
            value: Component data dictionary.
        
        Raises:
            WNTREPANETTypeValidationErrorBundle: If any validation rules fail.
        """
        ifuncs = inspect.getmembers(inst, inspect.ismethod)
        irules = {n: f for n, f in ifuncs if n.startswith("rule")}
        iwarns = {n: f for n, f in ifuncs if n.startswith("warn")}

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
        """Serialize and trim value text for error/warning messages.
        
        Converts the value to JSON and truncates if it exceeds max_value_len,
        appending a character count of the truncated portion.
        
        Args:
            value: Dictionary value to serialize and trim.
        
        Returns:
            Trimmed JSON string representation of the value.
        """
        value_text = json.dumps(value)
        remainder = len(value_text) - self.max_value_len
        if remainder > 0:
            s = "s" if remainder > 1 else ""
            value_text = value_text[:self.max_value_len] + f"...[+{remainder} char{s}]"

        return value_text

