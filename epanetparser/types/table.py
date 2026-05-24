from .base import PywrType


class PywrTable(PywrType):
    def __init__(self, name, data):
        self.name = str(name)
        self.data = data


    @property
    def type(self):
        return self.data.get("type")


    @property
    def attrs(self):
        return self.data.keys()


    """ Validation rules """

    def rule_name_required(self):
        assert isinstance(self.name, str), "Invalid table name"

    def rule_url_required(self):
        assert "url" in self.data, "Table <{self.name}> does not include url"
