from .base import PywrType


class PywrTimestepper(PywrType):
    def __init__(self, data):
        self.data = data

    """ Validation rules """
    def rule_start_required(self):
        assert "start" in self.data, "Timestepper does not define 'start' key"

    def rule_end_required(self):
        assert "end" in self.data, "Timestepper does not define 'end' key"

    def rule_start_before_end(self):
        pass
