import json

from abc import ABC
from typing import Dict

from pywrparser.utils import PywrTypeValidator


class PywrType(ABC):

    data = PywrTypeValidator()

    def as_dict(self) -> Dict[str, Dict]:
        return self.data

    def as_json(self) -> str:
        return json.dumps(self.data)

    @property
    def has_warnings(self):
        return hasattr(self, "warnings") and len(self.warnings)
