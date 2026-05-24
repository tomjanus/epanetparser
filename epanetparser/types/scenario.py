from .base import PywrType


class PywrScenario(PywrType):
    def __init__(self, data):
        self.data = data


    @property
    def name(self):
        return self.data.get("name")


    """ Validation rules """

    def rule_name_required(self):
        assert isinstance(self.name, str), "Scenario has invalid name"



class PywrScenarioCombination(PywrType):
    def __init__(self, data):
        self.data = data


    """ Validation rules """

    def rule_name_required(self):
        assert isinstance(self.data, list), "Scenario combination must be a list of scenario numbers"
