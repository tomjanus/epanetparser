import copy

from .base import PywrType
from pywrparser.utils import match


class PywrNode(PywrType):
    def __init__(self, data):
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
    def type(self):
        return self.data.get("type")


    @property
    def name(self):
        return self.data.get("name")


    @property
    def attrs(self):
        return self.data.keys()


    def as_dict(self):
        ret = copy.deepcopy(self.data)

        for k, v in ret.items():
            if isinstance(v, PywrType):
                ret[k] = v.as_dict()

        return ret


    """ Validation rules """

    def rule_node_has_name(self):
        assert self.name is not None, "Missing node name"

    def rule_node_has_type(self):
        assert "type" in self.data, "Node does not define type"

    def warn_node_name_min_len(self):
        assert self.name and len(self.name) > 1, "Node name too short"

    """ Type-specific rules """

    @match("proportionalinput")
    def warn_proportionalinput_has_proportion(self):
        assert "proportion" in self.data, "<proportionalinput> node does not define 'proportion'"


    @match("storage")
    def warn_storage_has_max_volume(self):
        assert "max_volume" in self.data, "<storage> node does not define 'max_volume'"
