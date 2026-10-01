"""Shared rule set discovery for core and custom rule sets.

Core rule sets and custom rule sets are discovered by exactly the same code.
The only difference between them is module metadata: a rule set module declares
``__is_core__ = True`` if it is a core rule set, and leaves it unset otherwise.
There is no separate discovery path, registry or plugin framework for the two
kinds.

Two layouts are supported, and a single discovery pass finds both:

- a rule set as a package, with its rules split across submodules
  (``epanetparser.core_rules.epanet_core.nodes``);
- a rule set as a plain module holding its rules directly
  (``epanetparser.custom_rules.milp``).

Functions
---------
discover_ruleset_modules
    Import the candidate rule set modules below one or more packages.
ruleset_rule_modules
    Return the modules whose rules belong to a rule set.
entry_point_modules
    Discover third-party rule sets registered as entry points.
"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Dict, Iterable, List, Optional, Sequence

from epanetparser.core.logger_setup import get_logger

logger = get_logger(__name__, level="WARNING")

#: Module attributes every rule set module must define.
REQUIRED_METADATA = ("__key__", "__ruleset_name__", "__version__")

#: Entry point group third-party rule sets may register under.
ENTRY_POINT_GROUP = "epanetparser.rulesets"

__all__ = [
    "ENTRY_POINT_GROUP",
    "REQUIRED_METADATA",
    "default_packages",
    "discover_ruleset_modules",
    "entry_point_modules",
    "missing_metadata",
    "ruleset_key",
    "ruleset_rule_modules",
]


def default_packages() -> List[str]:
    """Return the packages searched for rule sets by default.

    Returns
    -------
    List[str]
        Import paths of the core and custom rule set packages, in search
        order. Both are scanned by the same pass; ``__is_core__`` decides the
        classification.

    Notes
    -----
    The search paths come from the ``rule_set_discovery.packages`` section of
    ``default_config.yaml`` when it is present, and fall back to this list.

    Examples
    --------
    >>> default_packages()
    ['epanetparser.core_rules', 'epanetparser.custom_rules']
    """
    configured = _configured_packages()
    return configured or [
        "epanetparser.core_rules",
        "epanetparser.custom_rules",
    ]


def _configured_packages() -> Optional[List[str]]:
    """Read the rule set search paths from user or package configuration."""
    try:
        from epanetparser.core.config.manager import ConfigManager

        config = ConfigManager().load()
        section = config.get("rule_set_discovery", {}) or {}
    except Exception as err:  # pragma: no cover - configuration is optional
        logger.debug("Falling back to default rule set packages: %s", err)
        return None
    packages = section.get("packages") if isinstance(section, dict) else None
    if isinstance(packages, (list, tuple)) and packages:
        return [str(package) for package in packages]
    return None


def missing_metadata(module: ModuleType) -> List[str]:
    """Return the rule set metadata attributes absent from ``module``.

    Parameters
    ----------
    module : ModuleType
        Candidate rule set module.

    Returns
    -------
    List[str]
        Names of the required attributes the module does not define. Empty
        when the module is a valid rule set.
    """
    return [name for name in REQUIRED_METADATA if not hasattr(module, name)]


def ruleset_key(module: ModuleType) -> Optional[str]:
    """Return the declared rule set key, or None if the module declares none."""
    return getattr(module, "__key__", None)


def _import(path: str) -> Optional[ModuleType]:
    """Import ``path``, returning None and logging if that fails."""
    importlib.invalidate_caches()
    try:
        return importlib.import_module(path)
    except Exception as err:
        logger.warning("Failed to import rule set module '%s': %s", path, err)
        return None


def _rule_modules_of(module: ModuleType) -> List[ModuleType]:
    """Return the submodules of a rule set package.

    A rule set package holds its rules in submodules; the package itself only
    carries metadata. Non-packages have no submodules, so their own rule
    functions are collected directly by the caller.
    """
    path = getattr(module, "__path__", None)
    if path is None:
        return []
    found: List[ModuleType] = []
    for _, name, _ in pkgutil.iter_modules(path):
        child_path = f"{module.__name__}.{name}"
        child = _import(child_path)
        if child is not None:
            found.append(child)
    return found


def discover_ruleset_modules(
    packages: Optional[Sequence[str]] = None,
) -> Dict[str, ModuleType]:
    """Import every rule set module found below ``packages``.

    Parameters
    ----------
    packages : Optional[Sequence[str]]
        Import paths of packages to search. Each package is searched for rule
        set modules and, one level down, for rule set packages whose rules
        live in submodules. Defaults to :func:`default_packages`.

    Returns
    -------
    Dict[str, ModuleType]
        Mapping of rule set key to module. A module without the required
        metadata, or a package that cannot be imported, is skipped and logged
        rather than failing the whole scan.

    Notes
    -----
    The same function discovers core and custom rule sets. A module is a core
    rule set when it sets ``__is_core__ = True``; read that with
    :func:`epanetparser.core.validation.registry.RuleSet.is_core`.

    Examples
    --------
    >>> modules = discover_ruleset_modules(["epanetparser.core_rules"])
    >>> sorted(modules)
    ['epanet_core']
    """
    search_packages = list(packages) if packages is not None else default_packages()
    found: Dict[str, ModuleType] = {}
    for package_name in search_packages:
        package = _import(package_name)
        if package is None:
            continue
        if not hasattr(package, "__path__"):
            logger.warning(
                "Rule set search path '%s' is not a package; skipping", package_name
            )
            continue
        for _, name, _ in pkgutil.iter_modules(package.__path__):
            candidate_path = f"{package_name}.{name}"
            candidate = _import(candidate_path)
            if candidate is None:
                continue
            candidates = [candidate]
            candidates.extend(_rule_modules_of(candidate))
            for module in candidates:
                absent = missing_metadata(module)
                if absent:
                    if module is candidate:
                        logger.debug(
                            "Module '%s' is missing rule set metadata %s; skipping",
                            candidate_path,
                            absent,
                        )
                    continue
                key = ruleset_key(module)
                if key in found:
                    logger.warning(
                        "Duplicate rule set key '%s' in '%s'; keeping '%s'",
                        key,
                        module.__name__,
                        found[key].__name__,
                    )
                    continue
                found[key] = module
    return dict(sorted(found.items()))


def ruleset_rule_modules(module: ModuleType) -> List[ModuleType]:
    """Return the modules that hold the rules of a rule set.

    Parameters
    ----------
    module : ModuleType
        Rule set module, as returned by :func:`discover_ruleset_modules`.

    Returns
    -------
    List[ModuleType]
        For a rule set package, its submodules in sorted order; for a plain
        rule set module, the module itself.

    Notes
    -----
    Submodules that define no rules are returned too, so callers can report
    what a rule set contains; :func:`epanetparser.core.validation.rules.collect_rules`
    filters them out when it collects the actual rules.
    """
    submodules = _rule_modules_of(module)
    if submodules:
        return sorted(submodules, key=lambda mod: mod.__name__)
    return [module]


def entry_point_modules(
    group: str = ENTRY_POINT_GROUP,
) -> Dict[str, ModuleType]:
    """Discover rule sets published by third-party packages.

    Parameters
    ----------
    group : str
        Entry point group to search. Defaults to
        :data:`ENTRY_POINT_GROUP`.

    Returns
    -------
    Dict[str, ModuleType]
        Mapping of entry point name to imported module. Entry points that
        cannot be loaded are logged and skipped.

    Notes
    -----
    This is an optional extension point. Nothing in the package requires an
    entry point to be registered, and none of the bundled rule sets use one.

    Examples
    --------
    >>> isinstance(entry_point_modules(), dict)
    True
    """
    from importlib.metadata import entry_points

    modules: Dict[str, ModuleType] = {}
    try:
        selected: Iterable = entry_points().select(group=group)
    except Exception as err:  # pragma: no cover - depends on installed metadata
        logger.warning("Failed to read entry point group '%s': %s", group, err)
        return modules
    for entry_point in selected:
        try:
            modules[entry_point.name] = entry_point.load()
        except Exception as err:
            logger.warning(
                "Failed to load rule set entry point '%s': %s", entry_point.name, err
            )
    return modules
