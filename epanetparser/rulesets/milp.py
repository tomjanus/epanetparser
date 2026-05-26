""" """
from epanetparser.epanet_types.node import WNTREPANETNode
from epanetparser.epanet_types.control import WNTREPANETControl
from epanetparser.epanet_types.options import WNTREPANETOptions
from epanetparser.epanet_types.link import WNTREPANETLink
from epanetparser.utils import match

__key__ = "milp"
__ruleset_name__ = "Mixed Integer Linear Programming ruleset"
__version__ = "0.1.0"
__description__ = "A ruleset which strict requirements for an example MILP pump scheduuling code that has limited support for some network components, such as e.g. valves"


class MILP_Node(WNTREPANETNode):
    """ MILP_Node Validation rules """
    
    @match("Tank")
    def rule_no_tank_curve(self) -> None:
        if "vol_curve_name" in self.data:
            assert self.data["vol_curve_name"] == None, "Volume curves for tanks not supported"

    @match("Tank")
    def rule_no_tank_overflow(self) -> None:
        if "overflow" in self.data:
            assert self.data["overflow"] == False, "Overflows on tanks not supported"

    def rule_no_emitters(self) -> None:
        assert self.emitter_coefficient in (None, 0), "Emitters with nonzero coefficients not supported"


class MILP_Control(WNTREPANETControl):
    """ MILP_Control Validation rules """

    def rule_no_controls_allowed(self) -> None:
        assert False, "Controls not supported"


class MILP_Options(WNTREPANETOptions):
    """ MILP_Options Validation rules """

    def rule_simulation_time_horizon(self) -> None:
        assert (sim_time_horizon := self.time_options.get("duration")) == 24 * 3600, \
            f"Simulation time horizon {sim_time_horizon} seconds not equal to schedule time horizon {24 * 3600} seconds"

    def rule_hydraulic_timestep(self) -> None:
        hydraulic_timestep = self.time_options.get("hydraulic_timestep")
        assert hydraulic_timestep == 3600, \
            f"Simulation timestep {hydraulic_timestep} seconds not equal to MILOPS timestep {3600} seconds"


class MILP_Links(WNTREPANETLink):
    """ MILP_Links Validation rules """

    def rule_check_valves(self) -> None:
        check_valve_status: bool | False = self.data.get("check_valve")
        assert check_valve_status in (False, None), "Check valves not supported"

    @match("Valve")
    def rule_no_valves_allowed(self) -> None:
        assert False, "Valve links not supported"
