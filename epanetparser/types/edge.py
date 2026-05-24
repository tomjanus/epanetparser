from .base import PywrType


class PywrEdge(PywrType):
    def __init__(self, data):
        """
          An edge vertex may be either a node or a slot.
          As node names are always cast to str, these
          must be str in either case.
        """
        self.data = [str(vert) for vert in data]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

    @property
    def is_simple(self):
        return len(self) == 2


    """ Validation rules """

    def rule_target_required(self):
        assert len(self) > 1, "Edge has no target"

    def rule_source_and_target_distinct(self):
        if len(self) > 1:
            assert self.data[0] != self.data[1], "Edge source and target are the same"
