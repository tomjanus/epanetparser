# EPANET Networks

This directory contains EPANET water distribution network models used for testing, validation, and benchmarking of the `epanetparser` package. The networks are organized into three categories based on their purpose and distribution method.

## Directory Structure

### 📦 Core Networks (`core/`)

These are standard EPANET example networks that are **shipped with the package**. They serve as reference models and are commonly used for demonstration and basic testing purposes.

| Network | Description | Source |
|---------|-------------|--------|
| **Net1.inp** | Simple 9-node network with a single reservoir, 2 tanks, 6 junctions, and 12 pipes/pumps used as a simple example of modeling chlorine decay | WNTR distribution example network |
| **Net2.inp** | Medium-sized network with 36 nodes, demonstrating modeling a 55-hour fluoride tracer study | WNTR distribution example network |
| **Net3.inp** | Complex network with 97 nodes, showing how the percent of Lake water in a dual-source system changes over time | WNTR distribution example network |
| **Net6.inp** | Network used for formulation and optimization of robust sensor placement problems for drinking water contamination warning systems | WNTR distribution example network, Watson, J.P., Murray, R. and Hart, W.E., 2009 |
| **Anytown.inp** | Classic benchmark network used extensively in research for optimal design and operation studies | Walski et al. (1987) - Battle of the Network Models |

### 🧪 Test Networks (`test/`)

Minimal test networks used for **quick validation testing** of the parser functionality. These networks are **shipped with the package** and include both valid and intentionally invalid models to test error detection capabilities.

| Network | Description |
|---------|-------------|
| **test_valid_network.inp/json** | Minimal valid EPANET network for positive test cases |
| **test_invalid_network.inp/json** | Network with intentional errors for negative test cases |

### 🌐 Extra Networks (`extra/`)

Extended collection of benchmark and research networks imported from the **WNTR (Water Network Tool for Resilience)** package. These networks **need to be downloaded from external sources** and are used for comprehensive benchmarking and advanced testing scenarios.

| Network | Description | Source/Purpose |
|---------|-------------|----------------|
| **Hanoi.inp** | 34-node benchmark network for optimal pipe sizing studies | Fujiwara & Khang (1990) |
| **hanoi-exeter.inp** | Modified Hanoi network from University of Exeter research | Exeter Benchmark Suite |
| **anytown-exeter.inp** | Modified Anytown network from University of Exeter research | Exeter Benchmark Suite |
| **gessler1985.inp** | Network from Gessler's battle competition | Gessler (1985) |
| **ky4.inp** | Kentucky network #4 - small distribution system | KYPIPE benchmark suite |
| **ky10.inp** | Kentucky network #10 - medium distribution system | KYPIPE benchmark suite |
| **L-TOWN.inp** | Large network used in Battle of Water Networks competitions | BattLeDIM competition (2016) |
| **nytun.inp** | New York Tunnel optimization problem - classic large-scale benchmark | Schaake & Lai (1969) |
| **Richmond_skeleton.inp** | Skeleton model of Richmond, VA water distribution system | Real-world network model |

> **Note**: Networks in the `extra/` directory are available in both EPANET INP format (`.inp`) and WNTR JSON format (`.json`).

## Usage

### Accessing Core and Test Networks

Core and test networks are included with the package installation and can be accessed directly:

```python
from pathlib import Path
import epanetparser

# Get package directory
package_dir = Path(epanetparser.__file__).parent.parent

# Access core networks
core_networks = package_dir / "networks" / "core"
net1_path = core_networks / "Net1.inp"

# Access test networks
test_networks = package_dir / "networks" / "test"
```

### Obtaining Extra Networks

Extra networks need to be obtained from external sources. These can be:
- Downloaded from the [WNTR repository](https://github.com/USEPA/WNTR)
- Obtained from published benchmark suites
- Downloaded from research repositories

## File Formats

Networks are provided in two formats:

- **`.inp`** - Standard EPANET input file format (text-based)
- **`.json`** - WNTR JSON format (structured data representation)

The `epanetparser` package can validate and convert between both formats.

## Contributing

To add new benchmark networks:
1. Place INP files in the appropriate subdirectory (`core/` or `extra/`)
2. Ensure proper documentation of the network source
3. Include both `.inp` and `.json` formats when possible. Conversion to `.json` can be performed using the `epanetparser` CLI - see usage.
4. Update this **README** with network details
