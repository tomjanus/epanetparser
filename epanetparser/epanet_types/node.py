""" """
from collections.abc import KeysView
from typing import Optional, Dict, List, Tuple
import copy
from .base import WNTREPANETType
from epanetparser.utils import match


class WNTREPANETNode(WNTREPANETType):
    node_types: Tuple[str, ...] = ("Junction", "Reservoir", "Tank")
    def __init__(self, data) -> None:
        name = data.get("name")
        if not isinstance(name, str):
            if not name:
                # Unnamed node - will fail validation
                pass
            else:
                # Other non-str name, cast to str
                data["name"] = str(name)
        self.data = data

    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        coordinates = self.data.get("coordinates")
        if coordinates is not None:
            return tuple(coordinates)
        return coordinates

    @property
    def type(self) -> str:
        return self.data.get("node_type")

    @property
    def name(self) -> str:
        return self.data.get("name")
    
    @property
    def emitter_coefficient(self) -> Optional[float]:
        """ """
        return self.data.get("emitter_coefficient")

    @property
    def attrs(self) -> KeysView:
        return self.data.keys()

    def as_dict(self) -> Dict:
        ret = copy.deepcopy(self.data)
        for k, v in ret.items():
            if isinstance(v, WNTREPANETType):
                ret[k] = v.as_dict()
        return ret


    """ Validation rules """
    def rule_node_has_name(self) -> None:
        assert self.name is not None, "Missing node must have a name"

    def warn_node_has_type(self) -> None:
        assert "node_type" in self.data, "Node does not define type"

    @match("Junction")
    def rule_junction_has_elevation(self) -> None:
        assert "elevation" in self.data, "Junction does not define elevation"

    @match("Reservoir")
    def rule_reservoir_base_head(self) -> None:
        assert "base_head" in self.data, "Reservoir does not define base_head"

    @match("Tank")
    def rule_tank_has_diameter(self) -> None:
        assert "diameter" in self.data, "Tank does not define a diameter"

    @match("Tank")
    def rule_tank_has_elevation(self) -> None:
        assert "elevation" in self.data, "Tank does not define elevation"
    
    @match("Tank")
    def rule_tank_has_init_level(self) -> None:
        assert "init_level" in self.data, "Tank does not define initial level"

    @match("Tank")
    def rule_tank_has_max_level(self) -> None:
        assert "max_level" in self.data, "Tank does not define maximum level"

    @match("Tank")
    def rule_tank_has_min_level(self) -> None:
        assert "min_level" in self.data, "Tank does not define minimum level"

    @match("Tank")
    def rule_tank_has_min_volume(self) -> None:
        assert "min_vol" in self.data, "Tank does not define minimum volume"        

    def rule_node_has_valid_type(self) -> None:
        assert self.type in self.node_types, \
            f"Unsupported node type {self.type}"

    def warn_node_missing_coord(self) -> None:
        assert self.coordinates, "Missing coordinates, node will not be displayed"

    

