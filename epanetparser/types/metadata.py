from .base import PywrType


class PywrMetadata(PywrType):
    def __init__(self, data):
        minver = data.get("minimum_version")
        if minver and not isinstance(minver, str):
            data["minimum_version"] = str(minver)

        self.data = data


    @property
    def title(self):
        return self.data.get("title")


    """ Validation rules """

    def rule_title_required(self):
        assert isinstance(self.title, str), "Metadata does not define 'title' key"
