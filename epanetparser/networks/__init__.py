"""
Data package containing EPANET network files.

This package contains example and benchmark EPANET networks in both
INP and JSON (WNTR) formats organized in the following structure:

- core/: Core EPANET example networks (Net1, Net2, Net3, etc.)
- extra/: Additional benchmark networks
"""

from pathlib import Path

# Provide easy access to the networks directory
NETWORKS_DIR = Path(__file__).parent
CORE_DIR = NETWORKS_DIR / "core"
EXTRA_DIR = NETWORKS_DIR / "extra"

__all__ = ["NETWORKS_DIR", "CORE_DIR", "EXTRA_DIR"]
