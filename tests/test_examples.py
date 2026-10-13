import importlib.util
import os
import sys
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The demo runs the simulation layer only when WNTR (the optional 'simulation'
# extra) can be imported. Detect it by spec so the assertions can require the
# artefact of whichever branch actually ran.
WNTR_AVAILABLE = importlib.util.find_spec("wntr") is not None


def _run_example(script_name: str, *, env=None, cwd=None, timeout=300):
    script = REPO_ROOT / "examples" / script_name
    test_env = os.environ.copy()
    # Ensure correct package is imported from repo root
    test_env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + test_env.get("PYTHONPATH", "")
    if env:
        test_env.update(env)
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=test_env,
        check=False,
    )
    return result


class TestExamples:
    @pytest.mark.integration
    def test_three_layer_validation_demo(self):
        result = _run_example("11_three_layer_validation_demo.py")
        assert result.returncode == 0, result.stdout + result.stderr

        # The banner mentions "structural", "static" and "simulation"
        # unconditionally, so matching those words proves nothing about which
        # layers ran. The section headers only render when their section
        # executes, so require those instead.
        assert "Structural Layer (Parser Errors)" in result.stdout
        assert "Static Layer (Core Validation Rules)" in result.stdout

        # Require an artefact specific to whichever simulation branch ran:
        # the hydraulic finding and completion line when WNTR is installed,
        # otherwise the explicit skip message. Without this, a demo that
        # silently skipped the simulation layer would still pass.
        if WNTR_AVAILABLE:
            assert "Hydraulic simulation completed" in result.stdout
            assert "E_MINIMUM_PRESSURE" in result.stdout
        else:
            assert "skipped — install epanetparser" in result.stdout
