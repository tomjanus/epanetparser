""" """
from .base import WNTREPANETType

class WNTREPANETCurve(WNTREPANETType):
    """ """
    curve_types = ("HEAD", "PUMP", "EFFICIENCY", "VOLUME", "HEADLOSS")
    def __init__(self, data) -> None:
        name = data.get("name")
        if not isinstance(name, str):
            if not name:
                # Unnamed curve - will fail validation
                pass
            else:
                # Other non-str name, cast to str
                data["name"] = str(name)
        self.data = data

    @property
    def type(self) -> str:
        return self.data.get("curve_type")

    @property
    def name(self) -> str:
        return self.data.get("name")
    
    """ Curve validation rules """
    
    def rule_curve_has_name(self) -> None:
        assert self.name is not None, "Missing curve name"
        
    def rule_curve_has_valid_type(self) -> None:
        assert self.type in self.curve_types, \
            f"Unsupported curve type {self.type}"
            
    def rule_curve_has_points(self) -> None:
        points = self.data.get("points")
        assert isinstance(points, list) and len(points) > 0, \
            "Curve must have a non-empty list of points"
            
    def rule_curve_points_valid(self) -> None:
        points = self.data.get("points")
        assert all(isinstance(pt, (list, tuple)) and len(pt) == 2 for pt in points), \
            "Each curve point must be a list or tuple of two values (x, y)"
            
    def rule_curve_points_numeric(self) -> None:
        points = self.data.get("points")
        assert all(isinstance(pt[0], (int, float)) and isinstance(pt[1], (int, float)) for pt in points), \
            "Curve points must be numeric values"
            
    def rule_curve_points_sorted(self) -> None:
        points = self.data.get("points")
        assert all(points[i][0] <= points[i+1][0] for i in range(len(points)-1)), \
            "Curve points must be sorted in ascending order by x-value"