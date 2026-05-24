from pywrparser.types.node import PywrNode
from pywrparser.types.parameter import PywrParameter

__key__ = "strict"
__ruleset_name__ = "Strict Ruleset"
__version__ = "0.1.0"
__description__ = "A ruleset which enforces strict naming conventions"


class StrictNode(PywrNode):
    def __init__(self, data):
        super().__init__(data)

    """ StrictNode Validation rules """
    def rule_no_undersstart(self):
        if self.name:
            assert not self.name.lower().startswith('_'), "StrictNode name may not begin with '_' character"

    def rule_no_spacestart(self):
        if self.name:
            assert not self.name.lower().startswith(' '), "StrictNode name may not begin with space character"

    def rule_node_name_min_len(self):
        assert self.name and len(self.name) > 1, "Node name too short, at least four chars required"


class StrictParameter(PywrParameter):
    def __init__(self, name, data):
        super().__init__(name, data)

    def rule_no_spacestart(self):
        if self.name:
            assert not self.name.lower().startswith(' '), "StrictNode name may not begin with space character"
