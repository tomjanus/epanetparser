"""Three-layer validation through the CLI.

Runs ``epanetparser validate`` as a subprocess three times over the same
network, one per output concern:

1. static validation with ``--json-output``;
2. static validation with ``--toon-output``;
3. static + simulation validation with ``--simulate --simulation-ruleset
   hydraulic`` (needs the optional ``simulation`` extra; skipped otherwise).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NETWORK = PROJECT_ROOT / "tests" / "data" / "valid_network.inp"

try:
    import wntr  # noqa: F401
    WNTR_AVAILABLE = True
except ImportError:
    WNTR_AVAILABLE = False


def run_cli(*args: str, quiet: bool = False) -> subprocess.CompletedProcess:
    """Run the CLI in-process-equivalent and return the finished process."""
    env = dict(os.environ)
    if quiet:
        # The simulation path logs through the console handler, which writes
        # to stdout and would corrupt --json-output; silence it instead.
        env["EPANETPARSER_CONSOLE_LEVEL"] = "CRITICAL"
    return subprocess.run(
        [sys.executable, "-m", "epanetparser.core.parse", *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )


def main() -> None:
    print("1. Static validation, JSON output")
    print("   $ epanetparser validate -f valid_network.inp --json-output")
    result = run_cli("validate", "-f", str(NETWORK), "--json-output")
    print(f"   exit code: {result.returncode}")
    payload = json.loads(result.stdout)
    print(f"   is_valid: {payload['is_valid']}, counts: {payload['counts']}")

    print("2. Static validation, TOON output")
    print("   $ epanetparser validate -f valid_network.inp --toon-output")
    result = run_cli("validate", "-f", str(NETWORK), "--toon-output")
    print(f"   exit code: {result.returncode}")
    print("   " + "\n   ".join(result.stdout.splitlines()[:4]))

    print("3. Static + simulation validation")
    print(
        "   $ epanetparser validate -f valid_network.inp "
        "--simulate --simulation-ruleset hydraulic --json-output"
    )
    if not WNTR_AVAILABLE:
        print("   skipped — install epanetparser[simulation] for this step")
    else:
        result = run_cli(
            "validate",
            "-f", str(NETWORK),
            "--simulate",
            "--simulation-ruleset", "hydraulic",
            "--json-output",
            quiet=True,
        )
        print(f"   exit code: {result.returncode}")
        payload = json.loads(result.stdout)
        layers = sorted({issue["validation_layer"] for issue in payload["issues"]})
        print(f"   layers in report: {layers or ['<no issues>']}")

    print("01_three_layer_validation_cli completed")


if __name__ == "__main__":
    main()
