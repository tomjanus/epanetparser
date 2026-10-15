"""Configuration in one glance.

Loads the merged configuration (bundled defaults plus any user file) and
prints the two settings a caller most often needs: which packages are
searched for rule sets, and the logging level. Configuration is peripheral
to validation, so this demo stays short.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from epanetparser.core.config.manager import ConfigLoader


def main() -> None:
    config = ConfigLoader().load()
    discovery = config.get("rule_set_discovery", {}) or {}
    print("Rule-set search paths:")
    for package in discovery.get("packages", []):
        print(f"   {package}")
    print(f"Extra packages: {discovery.get('extra_packages', [])}")
    print(f"Logging level: {(config.get('logging', {}) or {}).get('level')}")
    print("06_configuration_demo completed")


if __name__ == "__main__":
    main()
