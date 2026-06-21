"""Mixed Integer Linear Programming (MILP) ruleset for EPANET networks.

This ruleset module defines specialized validation rules for EPANET network models
used in a Mixed Integer Linear Programming (MILP) optimal pump scheduling
software developed at De Montfort University, Leicester, UK.

The MILP ruleset enforces strict constraints required by MILP formulations, including:

- Prohibition of certain EPANET features not supported by the software
- Specific time horizon and timestep requirements
- Restrictions on network components (valves, emitters, controls, etc.)
- Tank configuration limitations

Ruleset Metadata
----------------
__key__ : str
    Unique identifier for this ruleset ('milp')
__ruleset_name__ : str
    Human-readable name of the ruleset
__version__ : str
    Semantic version of this ruleset
__required_rules__ : list of str
    List of required plugin rule sets that must be available
__conflicting_rules__ : list of str
    List of plugin rule sets that conflict with this ruleset
__description__ : str
    Detailed description of the ruleset's purpose and constraints

Examples
--------
Activate the MILP ruleset for validation:

>>> from epanetparser.core import rulesets
>>> rulesets.set_active_ruleset('milp')
>>> ruleset = rulesets.Ruleset()
>>> ruleset.typemap['WNTREPANETNode']
<class 'epanetparser.rulesets.milp.MILP_Node'>

Parse a network with MILP validation:

>>> from epanetparser.core.parsers.wntrjsonparser import WNTRJSONParser
>>> parser = WNTRJSONParser(json_data, ruleset='milp')
>>> parser.parse()
# Raises validation errors for MILP-incompatible features

See Also
--------
epanetparser.core.rulesets : Ruleset management system
epanetparser.core.epanettypes : Base EPANET component types
"""
from epanetparser.core.epanettypes.node import WNTREPANETNode
from epanetparser.core.epanettypes.control import WNTREPANETControl
from epanetparser.core.epanettypes.options import WNTREPANETOptions
from epanetparser.core.epanettypes.link import WNTREPANETLink
from epanetparser.core.decorators import match

__key__ = "milp"
__ruleset_name__ = "Mixed Integer Linear Programming ruleset"
__version__ = "0.1.0"
__required_rules__ = ["core 1.0"]
__conflicting_rules__ = []
__description__ = (
    "A ruleset that enforces the strict requirements of an example "
    "MILP pump scheduling implementation. The implementation provides "
    "limited support for certain EPANET network components, including "
    "valves."
)


class MILPNode(WNTREPANETNode):
    """MILP-specific validation rules for EPANET node components.
    
    The class prohibits:
    - Volume curves on tanks (non-cylindrical tanks)
    - Tank overflow settings
    - Emitters with non-zero coefficients
    
    Examples
    --------
    >>> node_data = {"name": "T1", "node_type": "Tank", "elevation": 100}
    >>> node = MILP_Node(node_data)
    # Validation passes
    
    >>> node_data_invalid = {
    ...     "name": "T1",
    ...     "node_type": "Tank",
    ...     "vol_curve_name": "VC1"
    ... }
    >>> node = MILP_Node(node_data_invalid)
    # Raises validation error: Volume curves not supported
    
    See Also
    --------
    WNTREPANETNode : Base class for node components
    match : Decorator for type-specific validation rules
    """
    
    @match("Tank")
    def rule_no_tank_curve(self) -> None:
        """Validate that tank does not have a volume curve."""
        if "vol_curve_name" in self.data:
            assert self.data["vol_curve_name"] == None, "Volume curves for tanks not supported"

    @match("Tank")
    def rule_no_tank_overflow(self) -> None:
        """Validate that tank overflow is not enabled."""
        if "overflow" in self.data:
            assert self.data["overflow"] == False, "Overflows on tanks not supported"

    def rule_no_emitters(self) -> None:
        """Validate that node does not have active emitters."""
        assert self.emitter_coefficient in (None, 0), "Emitters with nonzero coefficients not supported"


class MILPControl(WNTREPANETControl):
    """MILP-specific validation rules for EPANET control components.
    
    Examples
    --------
    >>> control_data = {"type": "simple", "condition": "TIME > 8"}
    >>> control = MILP_Control(control_data)
    
    See Also
    --------
    WNTREPANETControl : Base class for control components
    """

    def rule_no_controls_allowed(self) -> None:
        """Validate that no controls are present in the network."""
        assert False, "Controls not supported"


class MILPOptions(WNTREPANETOptions):
    """MILP-specific validation rules for EPANET simulation options.
    
    The class enforces:
    - 24-hour simulation duration (86400 seconds)
    - 1-hour hydraulic timestep (3600 seconds)
    
    Examples
    --------
    Valid options for MILP:
    
    >>> options_data = {
    ...     "time": {
    ...         "duration": 86400,
    ...         "hydraulic_timestep": 3600
    ...     }
    ... }
    >>> options = MILP_Options(options_data)
    # Validation passes
    
    Invalid options:
    
    >>> options_data = {
    ...     "time": {
    ...         "duration": 172800,  # 48 hours
    ...         "hydraulic_timestep": 3600
    ...     }
    ... }
    >>> options = MILP_Options(options_data)
    # Raises validation error: Duration must be 24 hours
    
    See Also
    --------
    WNTREPANETOptions : Base class for simulation options
    """

    def rule_simulation_time_horizon(self) -> None:
        """Validate that simulation duration is exactly 24 hours (86400 seconds)."""
        assert (sim_time_horizon := self.time_options.get("duration")) == 24 * 3600, \
            f"Simulation time horizon {sim_time_horizon} seconds not equal to schedule time horizon {24 * 3600} seconds"

    def rule_hydraulic_timestep(self) -> None:
        """Validate that hydraulic timestep is exactly 1 hour (3600 seconds)."""
        hydraulic_timestep = self.time_options.get("hydraulic_timestep")
        assert hydraulic_timestep == 3600, \
            f"Simulation timestep {hydraulic_timestep} seconds not equal to MILOPS timestep {3600} seconds"


class MILPLinks(WNTREPANETLink):
    """MILP-specific validation rules for EPANET link components.
    
    The class prohibits:
    - Check valves (unidirectional flow constraints)
    - Valve components (PRVs, PSVs, FCVs, TCVs, GPVs, PBVs)
    
    Examples
    --------
    Valid link (pipe without check valve):
    
    >>> link_data = {
    ...     "name": "P1",
    ...     "link_type": "Pipe",
    ...     "check_valve": False
    ... }
    >>> link = MILP_Links(link_data)
    # Validation passes
    
    Invalid link (with check valve):
    
    >>> link_data = {
    ...     "name": "P1",
    ...     "link_type": "Pipe",
    ...     "check_valve": True
    ... }
    >>> link = MILP_Links(link_data)
    # Raises validation error: Check valves not supported
    
    Invalid link (valve type):
    
    >>> link_data = {"name": "PRV1", "link_type": "Valve", "valve_type": "PRV"}
    >>> link = MILP_Links(link_data)
    # Raises validation error: Valve links not supported
    
    See Also
    --------
    WNTREPANETLink : Base class for link components
    match : Decorator for type-specific validation rules
    """

    def rule_check_valves(self) -> None:
        """Validate that link does not have check valve enabled."""
        check_valve_status: bool | False = self.data.get("check_valve")
        assert check_valve_status in (False, None), "Check valves not supported"

    @match("Valve")
    def rule_no_valves_allowed(self) -> None:
        """Validate that no valve-type links exist in the network."""
        assert False, "Valve links not supported"
