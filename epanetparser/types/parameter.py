from .base import PywrType
from pywrparser.utils import match


class PywrParameter(PywrType):
    def __init__(self, name, data):
        self.name = str(name)
        self.data = data


    @property
    def type(self):
        return self.data.get("type")


    @property
    def attrs(self):
        return tuple(self.data.keys())


    """ Validation rules """

    def rule_type_required(self):
        assert isinstance(self.type, str), f"Parameter <{self.name}> does not define type"


    """ Type-specific rules """

    @match("aggregatedparameter")
    def rule_aggregated_has_agg_func(self):
        assert "agg_func" in self.data, f"AggregatedParameter <{self.name}> does not define 'agg_func'"

    @match("aggregatedparameter")
    def rule_aggregated_has_parameters(self):
        assert "parameters" in self.data, f"AggregatedParameter <{self.name}> does not define 'parameters'"

    @match("aggregatedparameter")
    def rule_aggregated_has_paramlist(self):
        assert "parameters" in self.data and isinstance(self.data["parameters"], list),\
            f"AggregatedParameter <{self.name}> has invalid parameters"

    @match("controlcurveparameter")
    def rule_cc_has_storage(self):
        assert "storage_node" in self.data, f"ControlCurveParameter <{self.name}> does not define 'storage_node'"

    @match("monthlyprofileparameter")
    def warn_monthlyprofile_has_profile(self):
        assert "values" in self.data and isinstance(self.data["values"], list) and len(self.data["values"]) == 12,\
            f"MonthlyProfileParameter <{self.name}> has invalid profile values"

    @match("dataframe", fuzzy=True)
    def warn_outdated_pandas(self):
        assert "pandas_kwargs" not in self.data, f"Dataframe <{self.name}> uses outdated 'pandas_kwargs' key"
