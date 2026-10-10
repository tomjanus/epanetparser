# coding: utf-8
"""
Single global switch for the internal (WNTR-derived) model validation checks.

The classes in this package perform their own validation when building objects
(asserts, and ValueError/TypeError/AttributeError raised from __setattr__ and
property setters). epanetparser owns validation itself and parses/builds raw,
possibly-invalid values, so by default this validation is disabled. It can be
turned back on (e.g. to restore the original WNTR-style behavior) via
`set_validation(True)`.
"""

VALIDATE = False


def set_validation(enabled: bool) -> None:
    """Globally enable or disable the network model's internal validation checks."""
    global VALIDATE
    VALIDATE = enabled


def is_validation_enabled() -> bool:
    return VALIDATE


def require(condition: bool, message: str, exc_type: type = ValueError) -> None:
    """Raise exc_type(message) if condition is False, unless validation is disabled."""
    if VALIDATE and not condition:
        raise exc_type(message)


def unvalidated_setattr(func):
    """Decorator for `__setattr__` overrides.

    When validation is disabled, stores the raw value directly (skipping both
    the checks and any value coercion done by `func`).
    """
    def wrapper(self, name, value):
        if not VALIDATE:
            self.__dict__[name] = value
            return
        return func(self, name, value)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def unvalidated_setter(func):
    """Decorator for `@x.setter` property setters.

    When validation is disabled, stores the raw value directly in the
    conventional `_<property_name>` backing attribute, skipping checks/coercion.
    """
    def wrapper(self, value):
        if not VALIDATE:
            self.__dict__['_' + func.__name__] = value
            return
        return func(self, value)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
