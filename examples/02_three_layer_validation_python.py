"""Three-layer validation through the Python library API.

The same three stages as the CLI demo, called directly: parse the model,
validate it statically, run a hydraulic simulation, then validate the
simulation results. The simulation step needs the optional ``simulation``
extra; without it the static report is printed and the simulation is skipped.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import ValidationContext, Validator, validate

from common import render_section

NETWORK = PROJECT_ROOT / "tests" / "data" / "valid_network.inp"

try:
    import wntr
    WNTR_AVAILABLE = True
except ImportError:
    WNTR_AVAILABLE = False


def main() -> None:
    console = Console()
    render_section(
        console, 1, "Structural layer",
        "Parse the document; nothing is validated yet.",
    )
    network, errors, warnings = WNTREPANETNetwork.from_file(str(NETWORK))
    assert network is not None, f"could not parse {NETWORK}: {errors}"
    print(f"   parsed {network.name}: "
          f"{len(network.nodes)} nodes, {len(network.links)} links")

    render_section(
        console, 2, "Static layer",
        "Validate the model with the epanet_core rule set.",
    )
    static_report = validate(network)
    print(f"   is_valid: {static_report.is_valid}, "
          f"errors: {len(static_report.errors)}, "
          f"warnings: {len(static_report.warnings)}")

    render_section(
        console, 3, "Simulation layer",
        "Simulate, then validate the results with the hydraulic rule set.",
    )
    if not WNTR_AVAILABLE:
        print("   skipped — install epanetparser[simulation] for this step")
    else:
        wntr_model = network.to_wntr()
        simulation = wntr.sim.EpanetSimulator(wntr_model).run_sim()
        print("   hydraulic simulation completed")
        context = ValidationContext(custom=["hydraulic"])
        validator = Validator.from_context(context)
        sim_report = validator.validate_simulation(simulation, static_report)
        layers = sorted({issue.validation_layer for issue in sim_report})
        print(f"   is_valid: {sim_report.is_valid}, layers: {layers}")
        for issue in sim_report:
            if issue.validation_layer == "simulation":
                print(f"   [{issue.severity}] {issue.code}: {issue.message}")

    print("02_three_layer_validation_python completed")


if __name__ == "__main__":
    main()
