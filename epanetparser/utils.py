from __future__ import annotations
import functools
import inspect
import json
import re

from typing import Tuple

from pywrparser.types.exceptions import (
    PywrTypeValidationError,
    PywrTypeValidationErrorBundle
)
from pywrparser.types.warnings import PywrTypeValidationWarning


class raiseorpush():
    """
    Context manager to allow capture and aggregation of
    errors and warnings when parsing components
    """
    def __init__(self, component, raise_error, raise_warning, dest, ignore_warnings=False):
        self.component = component
        self.raise_error = raise_error
        self.raise_warning = raise_warning if not ignore_warnings else False
        self.ignore_warnings = ignore_warnings
        self.dest = dest
        self.error_set = (PywrTypeValidationErrorBundle, )
        if not raise_error:
            self.error_set = (PywrTypeValidationError, PywrTypeValidationErrorBundle)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_obj, exc_tb):
        if isinstance(exc_obj, PywrTypeValidationErrorBundle):
            for error in exc_obj.errors:
                #  Raise on warning implies raise on error
                if self.raise_warning or self.raise_error:
                    raise error from None
                self.dest.errors[self.component].append(error)

        return not self.raise_warning

    def capture_warnings(self, inst):
        """
        If a successfully created instance has warnings, either raise
        or push to the destination as appropriate
        """
        if inst.has_warnings and not self.ignore_warnings:
            for warning in inst.warnings:
                if self.raise_warning:
                    raise warning from None
                else:
                    self.dest.warnings[self.component].append(warning)


def canonical_name(nodename: str, attr: str) -> str:
    return f"__{nodename}__:{attr}"


def parse_reference_key(key: str) -> Tuple[str, str]:

    end_mark = "__:"
    name_end = key.rindex(end_mark)  # ValueError on fail
    sepidx = name_end + len(end_mark) - 1
    name, attr = key[:sepidx], key[sepidx+1:]

    name_pattern = r"^__[a-zA-Z0-9_ \/\:\.\-\(\)]+__$"
    if not re.search(name_pattern, name):
        raise ValueError(f"Invalid reference: {name}")

    return name.strip('_'), attr


class PywrTypeValidator():

    def __init__(self, max_value_len=200, store_passed_rules=False):
        self.max_value_len = int(max_value_len)
        self.store_passed_rules = store_passed_rules


    def __set_name__(self, inst: PywrType, name: str):
        self.instattr = '_' + name


    def __get__(self, inst: PywrType, dtype=None):
        return getattr(inst, self.instattr)


    def __set__(self, inst: PywrType, value: dict):
        setattr(inst, self.instattr, value)
        self.validate(inst, value)


    def validate(self, inst: PywrType, value: dict):
        ifuncs = inspect.getmembers(inst, inspect.ismethod)
        irules = {n: f for n, f in ifuncs if n.startswith("rule")}
        iwarns = {n: f for n, f in ifuncs if n.startswith("warn")}

        rules_passed = []
        exc_bundle = []
        warn_bundle = []

        for w, f in iwarns.items():
            try:
                f()
            except AssertionError as e:
                value_text = self.trim_value(value)
                warn_bundle.append(PywrTypeValidationWarning(inst.__class__.__qualname__, w, e, value_text))

        for r, f in irules.items():
            try:
                rules_passed.append(f"[PASSED] {r} -> {f()}")
            except AssertionError as e:
                value_text = self.trim_value(value)
                exc_bundle.append(PywrTypeValidationError(inst.__class__.__qualname__, r, e, value_text))

        if self.store_passed_rules:
            inst.rules_passed = rules_passed

        if len(exc_bundle) > 0:
            pveb = PywrTypeValidationErrorBundle(f"{inst.__class__.__qualname__} rule failures", exc_bundle)
            raise pveb

        inst.warnings = warn_bundle


    def trim_value(self, value):
        value_text = json.dumps(value)
        remainder = len(value_text) - self.max_value_len
        if remainder > 0:
            s = "s" if remainder > 1 else ""
            value_text = value_text[:self.max_value_len] + f"...[+{remainder} char{s}]"

        return value_text


def match(typename, fuzzy=False):
    """
    Decorator applies rules and warnings to only those node, parameter,
    or recorder components whose 'type' key is (roughly) equal to the
    'typename' argument.

    All comparisons are case-insensitive.

    The 'fuzzy' Boolean argument matches any type which contains the
    typename argument, irrespective of position.

    """
    def type_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not (hasattr(self, "type") and self.type):
                return
            if fuzzy:
                is_match = typename.lower() in self.type.lower()
            elif not self.type.lower().endswith("parameter"):
                if typename.lower().endswith("parameter"):
                    basematch = typename.lower()[:-9]
                else:
                    basematch = typename.lower()

                is_match = basematch == self.type.lower()
            else:
                is_match = typename.lower() == self.type.lower()

            if is_match:
                return func(self, *args, **kwargs)

        return wrapper
    return type_wrapper


def sha256digest(filename: str) -> str:
    import hashlib

    bufsz = 64 * 1024
    sha256 = hashlib.sha256()

    with open(filename, 'rb') as fp:
        while True:
            buf = fp.read(bufsz)
            if not buf:
                break
            sha256.update(buf)

    return sha256.hexdigest()
