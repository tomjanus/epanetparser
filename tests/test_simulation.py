"""End-to-end simulation tests for epanetparser.

These tests verify that parsed and converted networks can be successfully
simulated using WNTR's EpanetSimulator.
"""

import pytest
import tempfile
import os
from pathlib import Path

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.lib.converter import WNTRINPJSONConverter
from epanetparser.core.validation import validate, ValidationContext
from epanetparser.core.io.network.model import WaterNetworkModel as EPANETParserWaterNetworkModel

# Skip if wntr or EPANET simulator not available
try:
    import wntr
    from wntr.sim.epanet import EpanetSimulator
    WNTR_AVAILABLE = True
except ImportError:
    WNTR_AVAILABLE = False

try:
    # Check if EPANET binary is available by trying to run a simple simulation
    wn = wntr.network.WaterNetworkModel()
    wn.add_junction("J1", base_demand=10, elevation=10)
    wn.add_reservoir("R1", base_head=50)
    wn.add_pipe("P1", "R1", "J1", length=100, diameter=0.3)
    sim = EpanetSimulator(wn)
    results = sim.run_sim()
    EPANET_AVAILABLE = True
except Exception:
    EPANET_AVAILABLE = False


@pytest.mark.skipif(not WNTR_AVAILABLE, reason="WNTR not available")
class TestSimulation:
    """Test that parsed networks can be simulated."""

    def test_core_network_simulation(self):
        """Test that core networks can be parsed and simulated."""
        # Use a simple valid network
        network, errors, warnings = WNTREPANETNetwork.from_file(
            "tests/data/valid_network.json"
        )
        assert network is not None, f"Failed to parse: {errors}"

        # Validate with core ruleset
        report = network.validate()
        # The test network may have warnings but should not have structural errors
        # that prevent simulation
        
        # Convert to WNTR and simulate
        wn = network.to_wntr()
        assert wn is not None
        assert hasattr(wn, '_inpfile'), "WNTR model missing _inpfile"
        
        sim = EpanetSimulator(wn)
        results = sim.run_sim()
        
        # Verify results structure - results.node is a dict of DataFrames
        assert isinstance(results.node, dict)
        assert isinstance(results.link, dict)
        assert 'head' in results.node
        assert 'pressure' in results.node
        assert 'flowrate' in results.link
        assert 'velocity' in results.link
        
        # Check we have results for all nodes and links
        assert len(results.node['head'].columns) == len(network.nodes)
        assert len(results.link['flowrate'].columns) == len(network.links)

    def test_inp_parse_and_simulate(self):
        """Test INP file parsing and simulation."""
        network, errors, warnings = WNTREPANETNetwork.from_file(
            "tests/data/valid_network.inp"
        )
        assert network is not None, f"Failed to parse INP: {errors}"
        
        wn = network.to_wntr()
        sim = EpanetSimulator(wn)
        results = sim.run_sim()
        
        assert isinstance(results.node, dict)
        assert isinstance(results.link, dict)

    def test_json_to_inp_roundtrip_simulation(self):
        """Test INP -> JSON -> INP roundtrip preserves simulatable model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inp_path = "tests/data/valid_network.inp"
            json_path = os.path.join(tmpdir, "roundtrip.json")
            inp_path2 = os.path.join(tmpdir, "roundtrip.inp")
            
            # INP -> JSON
            WNTRINPJSONConverter.inp_to_json(inp_path, json_path)
            
            # JSON -> INP
            WNTRINPJSONConverter.json_to_inp(json_path, inp_path2)
            
            # Load roundtrip INP and simulate
            network, errors, warnings = WNTREPANETNetwork.from_file(inp_path2)
            assert network is not None, f"Failed to parse roundtrip INP: {errors}"
            
            wn = network.to_wntr()
            sim = EpanetSimulator(wn)
            results = sim.run_sim()
            
            assert isinstance(results.node, dict)
            assert isinstance(results.link, dict)

    def test_converter_cli_roundtrip(self):
        """Test CLI converter roundtrip produces simulatable model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inp_path = "tests/data/valid_network.inp"
            json_path = os.path.join(tmpdir, "cli.json")
            inp_path2 = os.path.join(tmpdir, "cli.inp")
            
            # Use converter
            WNTRINPJSONConverter.inp_to_json(inp_path, json_path)
            WNTRINPJSONConverter.json_to_inp(json_path, inp_path2)
            
            network, errors, warnings = WNTREPANETNetwork.from_file(inp_path2)
            assert network is not None
            
            wn = network.to_wntr()
            sim = EpanetSimulator(wn)
            results = sim.run_sim()
            
            assert isinstance(results.node, dict)
            assert isinstance(results.link, dict)


@pytest.mark.skipif(not EPANET_AVAILABLE, reason="EPANET simulator not available")
class TestSimulationHydraulicResults:
    """Test hydraulic results are reasonable."""
    
    def test_head_pressure_relationship(self):
        """Verify head = pressure + elevation for junctions."""
        network, _, _ = WNTREPANETNetwork.from_file("tests/data/valid_network.json")
        wn = network.to_wntr()
        sim = EpanetSimulator(wn)
        results = sim.run_sim()
        
        # For each junction, head should equal pressure + elevation
        for node_name in wn.junction_name_list:
            node = wn.get_node(node_name)
            elevation = node.elevation
            # Check at a few time steps
            for t in [0, 3600, 86400]:
                if t < len(results.node['head'].index):
                    head = results.node['head'].loc[t, node_name]
                    pressure = results.node['pressure'].loc[t, node_name]
                    # head = pressure + elevation (in meters)
                    # pressure in WNTR is in meters of head
                    assert abs(head - (pressure + elevation)) < 1e-4, \
                        f"Head-pressure mismatch at {node_name}, t={t}: head={head}, pressure={pressure}, elevation={elevation}"

    def test_flow_conservation(self):
        """Verify flow conservation at junctions (approximately)."""
        network, _, _ = WNTREPANETNetwork.from_file("tests/data/valid_network.json")
        wn = network.to_wntr()
        sim = EpanetSimulator(wn)
        results = sim.run_sim()
        
        # At steady state (last timestep), net flow at each junction 
        # should approximately equal demand
        last_t = results.link['flowrate'].index[-1]
        
        for node_name in wn.junction_name_list:
            node = wn.get_node(node_name)
            demand = node.demand_timeseries_list[0].base_value if node.demand_timeseries_list else 0
            
            # Sum inflows - outflows
            net_flow = 0
            for link_name in wn.get_links_for_node(node_name):
                link = wn.get_link(link_name)
                flow = results.link['flowrate'].loc[last_t, link_name]
                if link.end_node_name == node_name:
                    net_flow += flow  # Inflow
                else:
                    net_flow -= flow  # Outflow
            
            # Net flow should approximately equal demand (with some tolerance for numerical error)
            # This is a loose check since EPANET uses pressure-dependent demand
            assert abs(net_flow - demand) < max(0.01, abs(demand) * 0.1), \
                f"Flow conservation failed at {node_name}: net={net_flow}, demand={demand}"


@pytest.mark.skipif(not WNTR_AVAILABLE, reason="WNTR not available")
class TestToWntrMethod:
    """Test the to_wntr() method specifically."""
    
    def test_to_wntr_returns_correct_type(self):
        """to_wntr() returns an epanetparser WaterNetworkModel (vendored WNTR)."""
        network, _, _ = WNTREPANETNetwork.from_file("tests/data/valid_network.json")
        wn = network.to_wntr()
        # Returns our vendored WaterNetworkModel, not the external wntr one
        assert isinstance(wn, EPANETParserWaterNetworkModel)
    
    def test_to_wntr_preserves_component_counts(self):
        """Component counts preserved in conversion."""
        network, _, _ = WNTREPANETNetwork.from_file("tests/data/valid_network.json")
        wn = network.to_wntr()
        
        assert wn.num_junctions == len([n for n in network.nodes if n.data.get('node_type') == 'Junction'])
        assert wn.num_tanks == len([n for n in network.nodes if n.data.get('node_type') == 'Tank'])
        assert wn.num_reservoirs == len([n for n in network.nodes if n.data.get('node_type') == 'Reservoir'])
        assert wn.num_pipes == len([l for l in network.links if l.data.get('link_type') == 'Pipe'])
        assert wn.num_pumps == len([l for l in network.links if l.data.get('link_type') == 'Pump'])
        assert wn.num_valves == len([l for l in network.links if l.data.get('link_type') == 'Valve'])
    
    def test_to_wntr_sets_inpfile(self):
        """to_wntr() sets _inpfile attribute."""
        network, _, _ = WNTREPANETNetwork.from_file("tests/data/valid_network.json")
        wn = network.to_wntr()
        assert hasattr(wn, '_inpfile')
        assert wn._inpfile is not None
        from epanetparser.core.io.epanet.io import InpFile
        assert isinstance(wn._inpfile, InpFile)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])