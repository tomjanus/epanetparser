import json

from pywrparser.types.base import PywrType
from pywrparser.types.network import PywrNetwork

class PywrTypeJSONEncoder(json.JSONEncoder):
    def default(self, inst):
        if isinstance(inst, PywrType):
            return inst.data

        return json.JSONEncoder.default(self, inst)


class PywrNetworkJSONEncoder(json.JSONEncoder):
    def default(self, inst):
        if isinstance(inst, PywrNetwork):
            return inst.as_dict()

        return json.JSONEncoder.default(self, inst)
