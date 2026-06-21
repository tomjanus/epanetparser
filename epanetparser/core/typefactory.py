""" """
from typing import TypeAlias
from dataclasses import dataclass
from types import ModuleType
from epanetparser.core.ruleset_registry import RulesetRegistry
from epanetparser.core.rule_registry import RuleRegistry

RuleName: TypeAlias = str
ComponentType: TypeAlias = str
ComponentValidatorName: TypeAlias = str

@dataclass
class ValidatedTypeFactory:
    """A factory for creating validated types based on a ruleset module."""
    ruleset_registry: RulesetRegistry
    rule_registry: RuleRegistry
    
    def get_basetypes(self) -> tuple[type, ...]:
        """Retrieve base types from the ruleset module."""
        from epanetparser.core.epanettypes.node import WNTREPANETNode                 # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.control import WNTREPANETControl           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.curve import WNTREPANETCurve               # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.link import WNTREPANETLink                 # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.network_info import WNTREPANETNetworkInfo  # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.options import WNTREPANETOptions           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.pattern import WNTREPANETPattern           # pylint: disable=import-outside-toplevel
        from epanetparser.core.epanettypes.source import WNTREPANETSource             # pylint: disable=import-outside-toplevel
        base_types: tuple = (
            WNTREPANETNode, WNTREPANETControl, WNTREPANETCurve, WNTREPANETLink, 
            WNTREPANETNetworkInfo, WNTREPANETOptions, WNTREPANETPattern, WNTREPANETSource
        )
        return base_types
    
    def _get_basetype_statistics(self) -> dict[ComponentType, dict[str, list[ComponentValidatorName]]]:
        """Get statistics about registered validations for each base type."""
        stats: dict[ComponentType, dict[str, list[ComponentValidatorName]]] = {}
        for component_type in self.rule_registry._rules.keys():
            rules = list(self.rule_registry._rules.get(component_type, {}).keys())
            warnings = list(self.rule_registry._warnings.get(component_type, {}).keys())
            stats[component_type] = {
                "rules": rules,
                "warnings": warnings
            }
        return stats
    
    def create_types(self) -> None:
        """Uses resolutions to create validated types for each base type in the 
        by extending base types with additional core rules and warnings defined
        in RuleRegistry and the active ruleset module defined in RulesetRegistry.
        """
        
    
    
    def get_typemap(self, module: ModuleType) -> dict[str, type]:
        """Retrieve a mapping of type names to their corresponding classes from the module."""
        typemap: dict[str, type] = {}
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type):
                typemap[attr_name] = attr
        return typemap
        
        
        
        
    def some_other_fun(self):
        basetypes = {}
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, module.WNTREPANETType):
                basetypes[attr_name] = attr
        return basetypes
    
    
if __name__ == "__main__":
    pass