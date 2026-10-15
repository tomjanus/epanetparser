"""Custom and dynamic rulesets: discovery, layers, selection.

Shows the static/dynamic split from the caller's side: where the three
rule-set packages live, which layer each bundled rule set declares, that
``milp`` mixes static rules with a simulation rule, and that the dynamic
core rule set ``hydraulic`` is selected as a custom rule set alongside the
static core rule set. No simulation is run, so no optional extra is needed.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import (
    RuleSetRegistry,
    ValidationContext,
    default_packages,
    validate,
)

NETWORK = PROJECT_ROOT / "tests" / "data" / "valid_network_milp_ruleset.json"


def main() -> None:
    print("1. Discovery searches three leaf packages")
    for package in default_packages():
        print(f"   {package}")

    registry = RuleSetRegistry()
    print("2. Bundled rule sets and their layers")
    for ruleset in registry.all():
        kind = "core" if ruleset.is_core else "custom"
        print(f"   {ruleset.key} ({kind}, {ruleset.layer}): "
              f"{len(ruleset.component_rules)} component, "
              f"{len(ruleset.network_rules)} network, "
              f"{len(ruleset.simulation_rules)} simulation rules")

    print("3. milp is a mixed module: static rules plus one simulation rule")
    milp_ruleset = registry.get("milp")
    print(f"   layer: {milp_ruleset.layer}")
    for spec in milp_ruleset.simulation_rules:
        print(f"   simulation rule: {spec.rule_id} ({spec.code})")

    print("4. hydraulic is selected as a dynamic rule set, not as the core")
    selected = registry.resolve(ValidationContext(custom=["hydraulic"]))
    print(f"   resolved: {[ruleset.key for ruleset in selected]}")

    print("5. Static validation with the milp custom rule set")
    network, errors, _ = WNTREPANETNetwork.from_file(str(NETWORK))
    assert network is not None, f"could not parse {NETWORK}: {errors}"
    report = validate(network, ["epanet_core", "milp"])
    milp_codes = sorted(
        {issue.code for issue in report if issue.ruleset_key == "milp"}
    )
    print(f"   is_valid: {report.is_valid}, milp findings: {milp_codes}")

    print("04_custom_and_dynamic_rules completed")


if __name__ == "__main__":
    main()
