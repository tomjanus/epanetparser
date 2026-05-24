from pywrparser.types.node import PywrNode
from pywrparser.types.parameter import PywrParameter
from pywrparser.utils import match

__key__ = "pywrmaster"
__ruleset_name__ = "Pywr Master"
__version__ = "0.1.0"
__description__ = """
This ruleset ensures that model definitions conform to the requirements
of the current release on the master branch of Pywr.
"""


class MasterNode(PywrNode):
    def __init__(self, data):
        super().__init__(data)


class MasterParameter(PywrParameter):
    def __init__(self, name, data):
        super().__init__(name, data)


    @match("InterpolatedVolume", fuzzy=True)
    def rule_interp_kwargs(self):
        ik_key = "interp_kwargs"
        assert ik_key in self.data and "kind" in self.data[ik_key], \
                f"{self.data['type']} parameter must contain valid {ik_key} attribute"

    @match("Dataframe", fuzzy=True)
    def rule_nopandas_kwargs(self):
        pk_key = "pandas_kwargs"
        assert pk_key not in self.data, f"{pk_key} is deprecated in {self.data['type']} parameter"
