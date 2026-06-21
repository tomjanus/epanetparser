### 🧪 Test Networks

Minimal test networks used for **testing** of the parser functionality. These networks include both valid and intentionally invalid models to test error detection capabilities.

| Network | Description |
|---------|-------------|
| **valid_network.inp/json** | Complete mid-sized valid EPANET network for positive test cases based on the L-TOWN network |
| **invalid_network.inp/json** | Complete mid-sized network with intentional errors for negative test cases (modified L-TOWN) |
| **valid_network_milp_ruleset.inp/json** | Minimal valid EPANET network for positive test cases with the MILP ruleset applied |
| **invalid_network_milp_ruleset.inp/json** | Minimal EPANET network with errors only discovered when applying the MILP ruleset |
