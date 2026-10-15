"""Smoke tests for the examples folder.

The examples are numbered demos plus a shared helper: every ``NN_*.py``
must run cleanly via :func:`runpy.run_path`, the notebook must parse as
JSON with every code cell compiling, and every example file must follow
the ``NN_name.ext`` naming convention.

Simulation-using demos need the optional ``simulation`` extra and are
skipped without WNTR; static demos always run. The MCP demo skips itself
when the ``agentic`` extra is absent.
"""
import json
import re
import runpy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "examples"

#: Demos that run a hydraulic simulation; skipped without the extra.
WNTR_DEMOS = {
    "01_three_layer_validation_cli.py",
    "02_three_layer_validation_python.py",
}

#: Files that are helpers, not runnable examples.
HELPERS = {"common.py"}

NAME_PATTERN = re.compile(r"^\d{2}_.+\.(py|ipynb)$")


def _example_files():
    """All example files, helpers excluded, sorted by name."""
    files = [
        path
        for path in sorted(EXAMPLES.iterdir())
        if path.is_file()
        and path.suffix in (".py", ".ipynb")
        and path.name not in HELPERS
    ]
    assert files, "no example files found"
    return files


def test_example_naming_convention():
    """Every example file is numbered ``NN_name.ext``."""
    for path in _example_files():
        assert NAME_PATTERN.match(path.name), (
            f"{path.name} does not follow the NN_name.ext convention"
        )


@pytest.mark.parametrize(
    "script", [path.name for path in _example_files() if path.suffix == ".py"]
)
def test_example_runs(script, capsys):
    """Each demo runs to its completion marker."""
    if script in WNTR_DEMOS:
        pytest.importorskip("wntr")
    if script == "05_mcp_server_outputs.py":
        # The MCP stdio client hands the process's stderr to the server
        # subprocess, which needs a real file descriptor: run uncaptured.
        # The demo asserts JSON/TOON agreement itself, so reaching the end
        # without an exception is the check.
        with capsys.disabled():
            runpy.run_path(str(EXAMPLES / script), run_name="__main__")
        return
    runpy.run_path(str(EXAMPLES / script), run_name="__main__")
    captured = capsys.readouterr()
    stem = Path(script).stem
    assert f"{stem} completed" in captured.out, (
        f"{script} did not reach its completion marker"
    )


def test_notebook_parses_and_cells_compile():
    """The notebook is valid JSON and every code cell compiles."""
    notebooks = [
        path for path in _example_files() if path.suffix == ".ipynb"
    ]
    assert notebooks, "no notebook found"
    for path in notebooks:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        code_cells = [
            cell for cell in notebook["cells"] if cell["cell_type"] == "code"
        ]
        assert code_cells, f"{path.name} has no code cells"
        for index, cell in enumerate(code_cells):
            source = "".join(cell["source"])
            compile(source, f"{path.name} cell {index}", "exec")
