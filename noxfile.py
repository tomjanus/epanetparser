import nox

COV_MIN = 70

@nox.session
def lint(session):
    """ Lint to detect unused imports """
    session.install("flake8")
    session.run("flake8", "--select=E231,F401", "--per-file-ignores=__init__.py:F401", "pywrparser")


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"])
@nox.parametrize("rich", ["12.3.0", "12.4.4"])
def test(session, rich):
    """ Run pytest and coverage against Python and rich versions """
    session.install(".", f"rich=={rich}", "pytest", "pytest-cov")
    session.cd("tests")
    session.run("pytest", "--cov=pywrparser", f"--cov-fail-under={COV_MIN}", *session.posargs)
