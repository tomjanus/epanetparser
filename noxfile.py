import nox

COV_MIN = 50

@nox.session
def lint(session):
    """ Lint to detect unused imports """
    session.install("flake8")
    session.run("flake8", "--select=E231,F401", "--per-file-ignores=__init__.py:F401", "--exclude=epanetparser/core/io", "epanetparser")


@nox.session(python=["3.10", "3.11", "3.12", "3.13"])
@nox.parametrize("rich", ["12.3.0", "12.4.4"])
def test(session, rich):
    """ Run pytest and coverage against Python and rich versions """
    # Install package and test dependencies
    # Note: vendored WNTR code in core.io requires numpy, scipy, pandas, six
    session.install(".", f"rich=={rich}", "pytest", "pytest-cov", "numpy", "scipy", "pandas", "six", "responses")
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
    session.install(".", "pytest", "pytest-cov", "wntr", "numpy", "scipy", "pandas", "six")
    session.run("pytest", "-m", "integration", *session.posargs)