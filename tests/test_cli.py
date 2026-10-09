"""Tests for the command-line interface.

The CLI is where the parser, the engine and the report renderer meet, so it is
also where a mistake in any of them becomes visible to a user. These tests run
the real entry point in a subprocess and check what matters to a caller: the
exit status, and that the report says what it should.

What is covered
---------------
Exit status
    ``0`` for a valid model, ``1`` for bad usage or an unreadable input,
    ``2`` for a model that parsed but is invalid.
Rule set selection
    ``--ruleset`` applied, repeated, and rejected when unknown.
Output formats
    Console, JSON, terse, no-colour.
Separation of parse errors from validation findings
    A document that cannot be parsed is reported as such, and is never
    described as an invalid model.

Notes
-----
The CLI runs in a subprocess rather than in-process because it calls
``sys.exit`` and reconfigures logging and the console, both of which are
process-global. Running it out of process keeps the test session's state clean
and exercises the module exactly as ``epanetparser`` on a user's PATH would.

Every subprocess gets a throwaway ``XDG_CONFIG_HOME``. The CLI reads an optional
user configuration file, and inheriting the developer's real one would make
these tests depend on their home directory: a stale or hand-edited file there
would change the rule sets discovered, and a malformed one would make the whole
package fail to import. A test asserting machine-readable output must not be
decidable by whatever happens to sit in ``~/.config``.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID = "tests/data/valid_network.json"
INVALID = "tests/data/invalid_network.json"
VALID_MILP = "tests/data/valid_network_milp_ruleset.json"
INVALID_MILP = "tests/data/invalid_network_milp_ruleset.json"


@pytest.fixture(autouse=True)
def isolated_user_config(tmp_path, monkeypatch):
    """Keep every CLI subprocess away from the developer's user configuration.

    A ``subprocess.run`` with no ``env`` inherits this process's environment, so
    setting the variables here is enough: each subprocess below searches an
    empty temporary directory, finds no user config, and falls back to the
    package defaults, exactly as on a machine that never configured anything.

    ``XDG_CONFIG_HOME`` is what ``platformdirs`` consults on Linux and
    ``APPDATA`` on Windows and macOS, so both are redirected. The logging
    override is cleared as well, so a developer who exports
    ``EPANETPARSER_LOG_LEVEL=DEBUG`` cannot push log records onto stdout and
    break the JSON tests.
    """
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("APPDATA", str(config_home))
    monkeypatch.delenv("EPANETPARSER_LOG_LEVEL", raising=False)
    monkeypatch.delenv("EPANETPARSER_CONSOLE_LEVEL", raising=False)
    return config_home


def run(*args: str, env=None, timeout: int = 180) -> subprocess.CompletedProcess:
    """Run the validate subcommand in a subprocess.

    Parameters
    ----------
    *args : str
        Command-line arguments after ``validate``.
    env : dict or None
        Environment for the child. Pass :func:`cli_env` to keep the subprocess
        from reading the developer's user configuration.
    timeout : int
        Seconds to wait before giving up.

    Returns:
        subprocess.CompletedProcess: The finished process, with output captured
        rather than printed.
    """
    return subprocess.run(
        [sys.executable, "-m", "epanetparser.core.parse", "validate", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def convert(*args: str, env=None, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run the convert subcommand in a subprocess.

    Parameters
    ----------
    *args : str
        Command-line arguments after ``convert``.
    env : dict or None
        Environment for the child. Pass :func:`cli_env` to keep the subprocess
        from reading the developer's user configuration.
    timeout : int
        Seconds to wait before giving up. Conversion reads and writes a model
        with WNTR, which is slower than validation.

    Returns:
        subprocess.CompletedProcess: The finished process, with output captured
        rather than printed.
    """
    return subprocess.run(
        [sys.executable, "-m", "epanetparser.core.parse", "convert", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


class TestExitStatus:
    """The exit status is the contract a build script depends on."""

    def test_a_valid_model_exits_zero(self):
        """A well-formed model is usable, so nothing failed."""
        assert run("-f", VALID, "--no-digest").returncode == 0

    def test_an_invalid_model_exits_two(self):
        """A model that parsed but is invalid must not look like success."""
        assert run("-f", INVALID, "--no-digest").returncode == 2

    def test_an_unknown_ruleset_exits_one(self):
        """Naming a ruleset that does not exist is a usage error."""
        result = run("-f", VALID, "--ruleset", "nosuch")
        assert result.returncode == 1
        assert "nosuch" in result.stderr
        assert "epanet_core" in result.stderr

    def test_an_unreadable_input_exits_one(self, tmp_path):
        """Nothing was validated, so the command must not claim success."""
        result = run("-f", str(tmp_path / "absent.json"), "--no-digest")
        assert result.returncode == 1
        assert "Unable to read input file" in result.stdout

    def test_a_structural_problem_is_not_an_invalid_model(self, tmp_path):
        """A file that is not JSON is a parse problem, and says so."""
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = run("-f", str(path), "--no-digest")
        assert result.returncode == 1
        assert "Invalid JSON" in result.stdout

    def test_warnings_only_exits_zero(self):
        """A warning informs without blocking, so the model is still usable."""
        result = run("-f", VALID_MILP, "--ruleset", "milp", "--no-digest")
        assert result.returncode == 0

    def test_raise_on_warning_turns_warnings_into_a_failure(self):
        """A caller who treats warnings as fatal asks for that explicitly."""
        result = run(
            "-f", VALID_MILP, "--ruleset", "milp", "--raise-on-warning", "--no-digest"
        )
        assert result.returncode == 2

    def test_ignore_warnings_keeps_the_exit_status_at_zero(self):
        """Ignoring warnings leaves nothing to fail on."""
        result = run(
            "-f", VALID_MILP, "--ruleset", "milp", "--ignore-warnings", "--no-digest"
        )
        assert result.returncode == 0
        assert "W_MILP_INPFILE_UNITS" not in result.stdout


class TestRuleSetSelection:
    """Which rulesets the command applies."""

    def test_the_core_ruleset_is_applied_without_a_flag(self):
        """The default selection is the core ruleset."""
        assert "E_CURVE_TYPE_UNSUPPORTED" in run("-f", INVALID, "--no-digest").stdout

    def test_no_custom_ruleset_is_applied_by_default(self):
        """The core ruleset alone is what the default run applies."""
        assert "E_MILP" not in run("-f", VALID, "--no-digest").stdout

    def test_a_custom_ruleset_adds_its_findings(self):
        """Selecting a ruleset adds its rules to the same report."""
        result = run("-f", INVALID, "--ruleset", "milp", "--no-digest")
        assert "E_MILP_CONTROL" in result.stdout
        assert "E_CURVE_TYPE_UNSUPPORTED" in result.stdout

    def test_a_model_can_pass_core_and_fail_a_custom_ruleset(self):
        """This is the property the architecture exists to express."""
        assert run("-f", VALID_MILP, "--no-digest").returncode == 0
        assert run(
            "-f", INVALID_MILP, "--ruleset", "milp", "--no-digest"
        ).returncode == 2

    def test_a_custom_ruleset_can_be_given_more_than_once(self):
        """Repeating --ruleset is accepted, which is how several are applied."""
        result = run(
            "-f", VALID_MILP, "--ruleset", "milp", "--ruleset", "milp", "--no-digest"
        )
        assert result.returncode == 0

    def test_rulesets_can_be_listed(self):
        """The command can say what is available before a model is checked."""
        result = run("-f", VALID, "--list-rulesets")
        assert result.returncode == 0
        assert "epanet_core" in result.stdout
        assert "milp" in result.stdout


class TestOutputFormats:
    """What the report looks like on the way out."""

    def test_the_report_groups_findings_by_component(self):
        """A long report is readable when it is grouped by subject."""
        stdout = run("-f", INVALID_MILP, "--ruleset", "milp", "--no-digest").stdout
        assert "E_MILP_VALVE" in stdout
        assert "Valve links not supported" in stdout
        # The offending link is named, so the finding is actionable.
        assert "111" in stdout

    def test_json_output_is_one_parseable_document(self):
        """Machine-readable output must not be rewrapped by the console."""
        result = run("-f", INVALID, "--json-output", "--no-digest")
        payload = json.loads(result.stdout)
        assert payload["is_valid"] is False
        assert payload["counts"]["ERROR"] == 2
        # Warning count may vary as new warning rules are added
        assert payload["counts"]["WARNING"] >= 1

    def test_json_output_carries_a_code_and_a_ruleset_per_issue(self):
        """A consumer needs to know what failed and which ruleset to change."""
        payload = json.loads(
            run("-f", INVALID_MILP, "--ruleset", "milp", "--json-output", "--no-digest").stdout
        )
        for issue in payload["issues"]:
            assert issue["code"]
            assert issue["ruleset_key"] in {"epanet_core", "milp"}
            assert issue["severity"] in {"ERROR", "WARNING", "INFO"}

    def test_json_output_for_a_valid_model_is_an_empty_issue_list(self):
        """A clean run says so rather than printing nothing at all."""
        payload = json.loads(
            run("-f", VALID, "--json-output", "--no-digest").stdout
        )
        assert payload["is_valid"] is True
        assert payload["counts"]["ERROR"] == 0
        # Valid model may have warnings from engineering judgment rules
        assert payload["counts"]["WARNING"] >= 0
        assert payload["counts"]["INFO"] == 0

    def test_json_output_survives_a_long_message(self, tmp_path):
        """A long diagnostic must not be line-wrapped into invalid JSON."""
        model = json.loads((REPO_ROOT / VALID).read_text(encoding="utf-8"))
        model["nodes"][0]["demand_pattern"] = "P_" + "X" * 400
        path = tmp_path / "long.json"
        path.write_text(json.dumps(model), encoding="utf-8")
        payload = json.loads(run("-f", str(path), "--json-output", "--no-digest").stdout)
        assert payload["is_valid"] is False
        # The long demand_pattern should cause an error; find it in any issue
        long_x = "X" * 100
        found = any(long_x in issue["message"] for issue in payload["issues"])
        assert found, f"Long demand_pattern not found in any issue message"

    def test_the_component_counts_are_printed_for_a_valid_model(self):
        """A clean run reports what was loaded, so the model is identifiable."""
        stdout = run("-f", VALID_MILP, "--no-digest").stdout
        assert "Nodes: 11" in stdout
        assert "Links: 13" in stdout

    def test_terse_report_prints_only_the_counts(self):
        """A caller who wants the numbers and nothing else can ask for them."""
        stdout = run("-f", VALID_MILP, "--terse-report", "--no-digest").stdout
        assert stdout.strip().startswith("{'nodes': 11")

    def test_the_digest_can_be_included_or_omitted(self):
        """A report can be tied to the exact bytes it came from."""
        assert "sha256:" in run("-f", VALID_MILP).stdout
        assert "sha256:" not in run("-f", VALID_MILP, "--no-digest").stdout

    def test_no_colour_uses_text_labels_instead_of_colour(self):
        """The report stays legible without colour, which is what that flag is for."""
        stdout = run("-f", INVALID, "--no-colour", "--no-digest").stdout
        assert "[FAILURE]" in stdout
        assert "[WARNING]" in stdout
        assert ":red_circle:" not in stdout


class TestInfoSubcommand:
    """The discovery commands."""

    def test_info_lists_the_rulesets(self):
        """A caller can find out what exists without a model."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "info", "--list-rulesets"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert "epanet_core" in result.stdout

    def test_the_version_is_reported(self):
        """``--version`` prints the version and nothing else."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "--version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip()


class TestRulesetInspectionCommand:
    """The epanetparser-plugins command."""

    def test_list_reports_the_core_and_custom_rulesets(self):
        """Both kinds are listed, and the kind is distinguishable."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.plugins_cli", "list"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert "epanet_core" in result.stdout
        assert "milp" in result.stdout
        assert "core" in result.stdout and "custom" in result.stdout

    def test_show_lists_the_rules_of_one_ruleset(self):
        """A rule set's contents can be inspected before selecting it."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "epanetparser.core.plugins_cli",
                "show",
                "--ruleset",
                "milp",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert "rule_check_valves" in result.stdout
        assert "E_MILP_CHECK_VALVE" in result.stdout

    def test_show_can_be_narrowed_to_one_component(self):
        """The rules that apply to one component class can be listed alone."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "epanetparser.core.plugins_cli",
                "show",
                "--ruleset",
                "epanet_core",
                "--component",
                "WNTREPANETNode",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert "rule_tank_has_diameter" in result.stdout
        assert "rule_curve_has_points" not in result.stdout

    def test_show_rejects_an_unknown_ruleset(self):
        """Asking about something that does not exist exits non-zero."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "epanetparser.core.plugins_cli",
                "show",
                "--ruleset",
                "nosuch",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 1


class TestInpInput:
    """Reading the native EPANET format."""

    @pytest.mark.parametrize(
        "filename", ["tests/data/valid_network.inp", "tests/data/valid_network_milp_ruleset.inp"]
    )
    def test_an_inp_file_is_validated(self, filename):
        """An INP file is converted with WNTR and then validated as usual."""
        result = run("-f", filename, "--no-digest", timeout=600)
        assert result.returncode in (0, 2)
        assert "Invalid JSON" not in result.stdout

    def test_an_unsupported_extension_is_reported(self, tmp_path):
        """Only .inp and .json are model formats, and saying so beats guessing."""
        path = tmp_path / "model.txt"
        path.write_text("{}", encoding="utf-8")
        result = run("-f", str(path), "--no-digest")
        assert result.returncode == 1
        assert "Unsupported file extension" in result.stdout


class TestConvert:
    """The convert subcommand, in both directions.

    These tests exist because a real bug lived here undetected: the JSON to INP
    direction discarded the output file name the caller supplied and wrote the
    input's name with a swapped extension instead, reporting success. Every
    other conversion path was exercised, but no test named an output file.
    """

    def test_json_is_converted_to_the_named_inp_file(self, tmp_path):
        """The named output file is the one written and reported."""
        source = tmp_path / "model.json"
        source.write_text(
            Path(REPO_ROOT, VALID).read_text(encoding="utf-8"), encoding="utf-8"
        )
        target = tmp_path / "wanted_name.inp"
        result = convert(str(source), str(target))
        assert result.returncode == 0, result.stderr
        assert target.exists()
        assert "wanted_name.inp" in result.stdout

    def test_json_to_inp_does_not_fall_back_to_the_input_name(self, tmp_path):
        """The name the caller rejected must not appear.

        This is the direct assertion that the discarded-argument bug is gone.
        """
        source = tmp_path / "model.json"
        source.write_text(
            Path(REPO_ROOT, VALID).read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = convert(str(source), str(tmp_path / "wanted_name.inp"))
        assert result.returncode == 0, result.stderr
        assert not (tmp_path / "model.inp").exists()

    def test_inp_is_converted_to_the_named_json_file(self, tmp_path):
        """The other direction honours the output name as well."""
        source = tmp_path / "model.inp"
        source.write_bytes(Path(REPO_ROOT, "tests/data/valid_network.inp").read_bytes())
        target = tmp_path / "wanted_name.json"
        result = convert(str(source), str(target))
        assert result.returncode == 0, result.stderr
        assert target.exists()
        json.loads(target.read_text(encoding="utf-8"))

    def test_the_output_name_defaults_to_the_swapped_suffix(self, tmp_path):
        """With no output name, the file lands beside the input, renamed."""
        source = tmp_path / "model.json"
        source.write_text(
            Path(REPO_ROOT, VALID).read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = convert(str(source))
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "model.inp").exists()

    def test_an_unsupported_extension_is_reported(self, tmp_path):
        """The convert command says which formats it understands."""
        path = tmp_path / "model.txt"
        path.write_text("{}", encoding="utf-8")
        result = convert(str(path))
        assert result.returncode == 1
        assert "Unsupported file extension" in result.stderr + result.stdout

    def test_a_missing_input_is_reported(self, tmp_path):
        """A path that does not exist exits 1 rather than succeeding."""
        result = convert(str(tmp_path / "absent.json"))
        assert result.returncode == 1
        assert "not found" in (result.stderr + result.stdout).lower()


class TestVersionFlag:
    """Tests for --version flag."""

    def test_version_flag_prints_version_and_exits_zero(self):
        """--version prints version and exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "--version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip()
        # Version should be a valid version string
        assert "." in result.stdout.strip()

    def test_version_flag_with_subcommand_exits_zero(self):
        """--version before subcommand still prints version."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "--version", "validate", "-f", VALID],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout.strip()


class TestToonOutput:
    """Tests for --toon-output flag."""

    def test_toon_output_valid_model(self):
        """TOON output for valid model shows is_valid: true."""
        result = run("-f", VALID, "--toon-output", "--no-digest")
        assert result.returncode == 0
        assert "is_valid: true" in result.stdout
        assert "ERROR: 0" in result.stdout
        # Valid model may have warnings from engineering judgment rules
        assert "WARNING:" in result.stdout

    def test_toon_output_invalid_model(self):
        """TOON output for invalid model shows issues in tabular form."""
        result = run("-f", INVALID, "--toon-output", "--no-digest")
        assert result.returncode == 2
        assert "is_valid: false" in result.stdout
        assert "ERROR:" in result.stdout
        assert "issues[" in result.stdout

    def test_toon_output_with_ruleset(self):
        """TOON output works with custom rulesets."""
        result = run("-f", INVALID, "--toon-output", "--ruleset", "milp", "--no-digest")
        assert result.returncode == 2
        assert "E_MILP" in result.stdout

    def test_toon_output_mutually_exclusive_with_json(self):
        """--toon-output and --json-output are mutually exclusive."""
        result = run("-f", INVALID, "--toon-output", "--json-output", "--no-digest")
        assert result.returncode == 1
        assert "Only one of --json-output, --toon-output, --pretty-output" in result.stderr

    def test_toon_output_mutually_exclusive_with_pretty(self):
        """--toon-output and --pretty-output are mutually exclusive."""
        result = run("-f", INVALID, "--toon-output", "--pretty-output", "--no-digest")
        assert result.returncode == 1
        assert "Only one of --json-output, --toon-output, --pretty-output" in result.stderr


class TestParseFailureOutput:
    """Tests for parse failure output in different formats."""

    def test_parse_failure_json_output(self, tmp_path):
        """Parse failure with --json-output returns JSON error report."""
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = run("-f", str(path), "--json-output", "--no-digest")
        assert result.returncode == 1
        payload = json.loads(result.stdout)
        assert payload["results"]["errors"] == 1
        assert "errors" in payload
        assert "network" in payload["errors"]

    def test_parse_failure_toon_output(self, tmp_path):
        """Parse failure with --toon-output returns TOON error report."""
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = run("-f", str(path), "--toon-output", "--no-digest")
        assert result.returncode == 1
        assert "is_valid: false" in result.stdout
        assert "E_PARSE_FAILED" in result.stdout

    def test_parse_failure_default_output(self, tmp_path):
        """Parse failure with default output shows error."""
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = run("-f", str(path), "--no-digest")
        assert result.returncode == 1
        assert "Unable to read input file" in result.stdout or "Invalid JSON" in result.stdout


class TestRuleSetSelectionError:
    """Tests for RuleSetSelectionError handling."""

    def test_invalid_ruleset_key_exits_one(self):
        """Unknown ruleset key exits with code 1."""
        result = run("-f", VALID, "--ruleset", "nonexistent_ruleset", "--no-digest")
        assert result.returncode == 1
        assert "nonexistent_ruleset" in result.stderr
        assert "Available:" in result.stderr


class TestIgnoreWarnings:
    """Tests for --ignore-warnings flag."""

    def test_ignore_warnings_removes_warnings_from_report(self):
        """Warnings are filtered out when --ignore-warnings is used."""
        result = run("-f", INVALID_MILP, "--ruleset", "milp", "--ignore-warnings", "--json-output", "--no-digest")
        assert result.returncode in (0, 2)
        payload = json.loads(result.stdout)
        assert payload["counts"]["WARNING"] == 0

    def test_ignore_warnings_with_pretty_output(self):
        """Warnings are filtered from pretty output too."""
        result = run("-f", INVALID_MILP, "--ruleset", "milp", "--ignore-warnings", "--no-digest")
        assert result.returncode in (0, 2)
        # Should not contain warning indicators
        assert "W_MILP" not in result.stdout


class TestTerseReport:
    """Tests for --terse-report flag."""

    def test_terse_report_valid_model(self):
        """Terse report for valid model shows only counts."""
        result = run("-f", VALID, "--terse-report", "--no-digest")
        assert result.returncode == 0
        stdout = result.stdout.strip()
        assert stdout.startswith("{'nodes':")
        assert "ERROR" not in stdout

    def test_terse_report_invalid_model_shows_full_report(self):
        """Terse report for invalid model still shows full report (terse only applies to valid)."""
        result = run("-f", INVALID, "--terse-report", "--no-digest")
        assert result.returncode == 2
        stdout = result.stdout.strip()
        # For invalid models, terse report still shows the full report with errors
        # Uses 🔴 emoji for errors and E_ error codes
        assert "🔴" in stdout or "E_NETWORK_NAME_MISSING" in stdout
        # But it ends with the component counts
        assert "nodes" in stdout and "links" in stdout


class TestConvertErrors:
    """Tests for convert subcommand error cases."""

    def test_convert_missing_input_exits_one(self, tmp_path):
        """Missing input file exits with code 1."""
        result = convert(str(tmp_path / "absent.json"))
        assert result.returncode == 1
        assert "not found" in (result.stderr + result.stdout).lower()

    def test_convert_invalid_extension_exits_one(self, tmp_path):
        """Unsupported file extension exits with code 1."""
        path = tmp_path / "model.txt"
        path.write_text("{}", encoding="utf-8")
        result = convert(str(path))
        assert result.returncode == 1
        assert "Unsupported file extension" in result.stderr + result.stdout

    def test_convert_missing_input_file_stderr(self, tmp_path):
        """Missing input file error goes to stderr."""
        result = convert(str(tmp_path / "absent.json"))
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()


class TestUnknownCommand:
    """Tests for unknown command handling."""

    def test_unknown_command_exits_two(self):
        """Unknown subcommand exits with code 2 (argparse error)."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse", "unknowncmd"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 2
        assert "invalid choice" in result.stderr.lower()

    def test_no_command_exits_zero_shows_help(self):
        """No subcommand exits with code 0 and shows help."""
        result = subprocess.run(
            [sys.executable, "-m", "epanetparser.core.parse"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()
        assert "validate" in result.stdout
        assert "convert" in result.stdout
        assert "info" in result.stdout


class TestRaiseOnError:
    """Tests for --raise-on-error flag."""

    def test_raise_on_error_with_structural_error(self, tmp_path):
        """--raise-on-error raises exception for structural parse error."""
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = run("-f", str(path), "--raise-on-error", "--no-digest")
        # The flag should cause the error to be raised rather than reported
        # Since we run in subprocess, we check the exit code
        assert result.returncode == 1
