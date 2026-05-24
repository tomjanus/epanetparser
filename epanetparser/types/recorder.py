from .base import PywrType


class PywrRecorder(PywrType):
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
        assert isinstance(self.type, str), f"Recorder <{self.name}> does not define type"
