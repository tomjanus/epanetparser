""" """
from typing import Dict
from collections.abc import KeysView
from .base import WNTREPANETType


TIME_HORIZON = 24 # MILOPS scheduling time-horizon (make configurable)
TIME_STEP = 1 # MILOPS timestep of 1hr (make configurable)
HEADLOSS_MODELS = ("D-W", "H-W") # Unsupported model: C-M


class WNTREPANETOptions(WNTREPANETType):
    """ """
    def __init__(self, data):
        self.data = data

    @property
    def time_options(self) -> Dict:
        return self.data.get("time")
    
    @property
    def hydraulic_options(self) -> Dict:
        return self.data.get("hydraulic")

    @property
    def report_options(self) -> Dict:
        return self.data.get("report")
    
    @property
    def quality_options(self) -> Dict:
        return self.data.get("quality")
    
    @property
    def reaction_options(self) -> Dict:
        return self.data.get("reaction")

    @property
    def energy_options(self) -> Dict:
        return self.data.get("energy")
    
    @property
    def graphics_options(self) -> Dict:
        return self.data.get("graphics")
    
    @property
    def attrs(self) -> KeysView:
        return self.data.keys()
    
    @property
    def type(self) -> str:
        return "WNTR_Network_Options"

    """ Generic validation rules for networks not requiring quality and reaction modelling """

    def rule_time_section_required(self) -> None:
        assert self.time_options is not None, "Time section not defined"

    def rule_hydraulic_section_required(self) -> None:
        assert self.hydraulic_options is not None, "Hydraulics not defined"

    def rule_energy_section_required(self) -> None:
        assert self.energy_options is not None, "Energy options not defined"

    """ MILOPS-specific validation rules """

    def rule_simulation_time_horizon(self) -> None:
        sim_time_horizon = self.time_options.get("duration")
        assert self.time_options.get("duration") >= TIME_HORIZON * 3600, \
            f"Simulation time horizon {sim_time_horizon} seconds shorter than schedule time horizon {TIME_HORIZON * 3600} seconds"

    def rule_hydraulic_timestep(self) -> None:
        hydraulic_timestep = self.time_options.get("hydraulic_timestep")
        assert hydraulic_timestep == TIME_STEP * 3600, \
            f"Simulation timestep {hydraulic_timestep} seconds not equal to MILOPS timestep {TIME_STEP * 3600} seconds"
        
    # The below rules can be moved to strict ruleset

    def rule_headloss_model(self) -> None:
        supported_models: str = ", ".join(HEADLOSS_MODELS)
        assert self.hydraulic_options.get("headloss") in HEADLOSS_MODELS, \
            f"Improper headloss model. Supported models {supported_models}"
        
    def rule_viscosity(self) -> None:
        assert self.hydraulic_options.get("viscosity") == 1, "Viscosity is not 1.0"

    def rule_specific_gravity(self) -> None:
        assert self.hydraulic_options.get("specific_gravity") == 1, \
            "Specific gravity is not 1.0"

    def rule_demand_model(self) -> None:
        assert self.hydraulic_options.get("demand_model") == "DDA", \
            "Demand model is not DDA (fixed demand)"

    def rule_pressure_units(self) -> None:
        inpfile_pressure_units = self.hydraulic_options.get("inpfile_pressure_units")
        assert inpfile_pressure_units is None, \
            f"Unsupported pressure units: {inpfile_pressure_units}"

    def rule_zero_demand_charge(self) -> None:
        demand_charge = self.energy_options.get("demand_charge")
        assert demand_charge == 0, "Nonzero demand charge"

    def warn_inpfile_units(self) -> None:
        inpfile_units = self.hydraulic_options.get("inpfile_units")
        # Available unit options:
        # CFS/GPM/MGD/IMGD/AFD/LPS/LPM/MLD/CMH/CMD
        assert inpfile_units == "LPS", "Units not in litres per second. Units in INP file will be different than simulated"