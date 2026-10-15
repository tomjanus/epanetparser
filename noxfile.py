import nox

COV_MIN = 70

@nox.session
def lint(session):
    """ Lint to detect unused imports """
    session.install("flake8")
    session.run("flake8", "--select=E231,F401", "--per-file-ignores=__init__.py:F401", "--exclude=epanetparser/core/io", "epanetparser")


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
@nox.parametrize("rich", ["12.3.0", "12.4.4"])
def test(session, rich):
    """ Run pytest and coverage against Python and rich versions """
    # Install the simulation extra so the WNTR-comparison unit tests run.
    # The vendored parser in core.io needs numpy, scipy, pandas and six, which
    # are core dependencies; --extras simulation additionally installs WNTR.
    session.install(".[simulation]", f"rich=={rich}", "pytest", "pytest-cov", "responses")
    session.run(
        "pytest",
        "--cov=epanetparser",
        "--cov-config=.coveragerc",
        f"--cov-fail-under={COV_MIN}",
        *session.posargs
    )


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
def test_integration(session):
    """ Run integration tests (require external services) """
    session.install(".[simulation]", "pytest", "pytest-cov")
    session.run("pytest", "-m", "integration", *session.posargs)


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
def examples(session):
    """ Run every examples/NN_*.py demo plus the notebook smoke test """
    # The simulation extra lets the simulation-using demos run their full
    # three layers instead of skipping; nbformat is the examples group's
    # notebook tooling, kept installed for notebook-aware workflows.
    session.install(".[simulation]", "pytest", "nbformat")
    session.run("pytest", "tests/test_examples.py", *session.posargs)