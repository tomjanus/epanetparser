"""Structured outputs: JSON and TOON side by side.

Validates one network, renders the report as JSON and as TOON, and checks
the two agree: same validity, same per-severity counts, same issue codes.
A character/token comparison shows why TOON is the cheaper wire format for
agents. No simulation is involved, so no optional extra is needed.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.validation import validate

NETWORK = PROJECT_ROOT / "tests" / "data" / "invalid_network.json"


def main() -> None:
    network, errors, _ = WNTREPANETNetwork.from_file(str(NETWORK))
    assert network is not None, f"could not parse {NETWORK}: {errors}"
    report = validate(network)
    print(f"Invalid network: is_valid={report.is_valid}, "
          f"issues={len(report)}")

    payload = report.as_dict()
    json_text = json.dumps(payload, indent=2)
    toon_text = report.as_toon()

    print("1. Agreement between the two encodings")
    assert ("is_valid: false" in toon_text) == (not payload["is_valid"])
    for severity, count in payload["counts"].items():
        assert f"{severity}: {count}" in toon_text, severity
    json_codes = [issue["code"] for issue in payload["issues"]]
    for code in set(json_codes):
        assert code in toon_text, code
    assert f"issues[{len(payload['issues'])}]" in toon_text
    print(f"   agreed on {len(json_codes)} issues, "
          f"counts {payload['counts']}")

    print("2. Size comparison (roughly 4 characters per token)")
    json_chars, toon_chars = len(json_text), len(toon_text)
    saved = (json_chars - toon_chars) / json_chars * 100
    print(f"   JSON: {json_chars:,} chars (~{json_chars // 4:,} tokens)")
    print(f"   TOON: {toon_chars:,} chars (~{toon_chars // 4:,} tokens)")
    print(f"   TOON saves {saved:.1f}% of the characters")

    print("3. TOON sample (first 6 lines)")
    for line in toon_text.splitlines()[:6]:
        print(f"   {line}")

    print("03_structured_outputs completed")


if __name__ == "__main__":
    main()
