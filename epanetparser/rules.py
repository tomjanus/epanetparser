import importlib
import inspect

RULESET_BASE = "pywrparser.rulesets"
ACTIVE_RULESET_KEY = None


def get_rulesets():
    mods = get_ruleset_modules()
    modules = {}
    for mod in mods:
        modules[mod[1].__key__] = {
            "name": mod[1].__ruleset_name__,
            "modpath": mod[0],
            "version": mod[1].__version__,
            "description": mod[1].__description__
        }

    return modules


def get_ruleset_modules(base=RULESET_BASE):
    importlib.invalidate_caches()
    base = importlib.import_module(RULESET_BASE)
    return inspect.getmembers(base, inspect.ismodule)


def get_ruleset_module(key):
    modules = (m for _, m in get_ruleset_modules())
    for module in modules:
        if module.__key__ == key:
            return module


def describe_rulesets():
    modules = get_rulesets()

    output = "Available Rulesets:\n"
    for idx, (key, mod) in enumerate(modules.items(), 1):
        output += f"[{idx}]\tName: '{mod['name']}'  Version: {mod['version']}"
        output += f"  Key: {key}\n"
        output += f"{mod['description']}\n\n"

    return output


def identify_types(module):
    """
      Return a mapping from the default types to any
      particular subclasses loaded by the active ruleset.
      Types not specialised by the ruleset simply map to themselves.
    """
    from pywrparser.types.node import PywrNode
    from pywrparser.types.timestepper import PywrTimestepper
    from pywrparser.types.metadata import PywrMetadata
    from pywrparser.types.scenario import PywrScenario, PywrScenarioCombination
    from pywrparser.types.table import PywrTable
    from pywrparser.types.parameter import PywrParameter
    from pywrparser.types.recorder import PywrRecorder
    from pywrparser.types.edge import PywrEdge

    base_types = (
        PywrNode, PywrTimestepper, PywrMetadata, PywrScenario,
        PywrTable, PywrParameter, PywrRecorder, PywrEdge,
        PywrScenarioCombination
    )

    typemap = {t.__qualname__: t for t in base_types}
    if not module:
        return typemap

    classes = inspect.getmembers(module, inspect.isclass)
    for cls in classes:
        for t in base_types:
            if not cls[1] is t and issubclass(cls[1], t):
                typemap[t.__qualname__] = cls[1]

    return typemap


def set_active_ruleset(key):
    global ACTIVE_RULESET_KEY
    ACTIVE_RULESET_KEY = key


class Ruleset():
    def __init__(self):
        module = get_ruleset_module(ACTIVE_RULESET_KEY)
        self.typemap = identify_types(module)
