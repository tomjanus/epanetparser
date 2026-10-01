"""Converting between EPANET's INP format and WNTR's JSON.

The converter is the only path that reads and writes the native model format,
so it is the one place where a silent mistake is expensive: a wrong output path
does not corrupt data, it just puts the file somewhere the caller did not ask
for and reports success.

The regression test that shapes this file is
:func:`TestJsonToInp.test_an_explicit_output_path_is_honoured`. The converter
used to overwrite its ``inp_path`` argument with a suffix swap on the *input*
path, so ``epanetparser convert model.json wanted_name.inp`` wrote
``model.inp`` and printed ``Converted JSON to INP: model.inp`` with exit status
0. Every conversion path was exercised by the CLI tests at the time, and none
of them named an output file, so nothing caught it.

The round-trip assertions below were previously a ``__main__`` block at the end
of the converter module, where they never ran under pytest.

Notes
-----
Every test converts the real ``tests/data/valid_network.inp``. A synthetic model
would be faster but would not exercise WNTR's INP reader and writer, which is
the part most likely to lose or rename something.
"""
import json
from pathlib import Path

import pytest

from epanetparser.core.epanettypes.network import WNTREPANETNetwork
from epanetparser.core.lib.converter import WNTRINPJSONConverter

DATA_DIR = Path(__file__).resolve().parent / "data"

#: A real, well-formed EPANET model, used as the subject of every round trip.
INP_FILE = DATA_DIR / "valid_network.inp"


@pytest.fixture(scope="module")
def converted(tmp_path_factory) -> Path:
    """Convert the sample INP file to JSON once for the read-only tests.

    Returns:
        pathlib.Path: The generated JSON file.
    """
    out = tmp_path_factory.mktemp("converted") / "model.json"
    WNTRINPJSONConverter.inp_to_json(INP_FILE, json_path=out)
    return out


@pytest.fixture(scope="module")
def round_tripped(tmp_path_factory) -> Path:
    """Convert the sample model to JSON and back to INP.

    The round trip is done once per module because reading and writing an INP
    file with WNTR is the slow part of these tests.

    Returns:
        pathlib.Path: The reconstructed INP file.
    """
    work = tmp_path_factory.mktemp("roundtrip")
    json_path = work / "model.json"
    WNTRINPJSONConverter.inp_to_json(INP_FILE, json_path=json_path)
    inp_path = work / "model.inp"
    WNTRINPJSONConverter.json_to_inp(json_path, inp_path=inp_path)
    return inp_path


class TestInpToJson:
    """Reading the native format."""

    def test_the_generated_json_holds_the_model(self, converted):
        """The JSON document carries the model, not an empty shell."""
        payload = json.loads(converted.read_text(encoding="utf-8"))
        assert payload["nodes"], "no nodes were converted"
        assert payload["links"], "no links were converted"

    def test_the_generated_json_parses_and_validates(self, converted):
        """A converted model is usable by the rest of the toolkit."""
        network, errors, _ = WNTREPANETNetwork.from_file(converted)
        assert network is not None, f"converted model did not parse: {errors}"
        assert network.report()["nodes"] > 0
        assert network.report()["links"] > 0

    def test_the_output_path_defaults_to_the_swapped_suffix(self, tmp_path):
        """With no output path, the file lands beside the input, renamed."""
        source = tmp_path / "beside.inp"
        source.write_bytes(INP_FILE.read_bytes())
        generated = WNTRINPJSONConverter.inp_to_json(source)
        assert Path(generated) == tmp_path / "beside.json"
        assert Path(generated).exists()

    def test_an_explicit_output_path_is_honoured(self, tmp_path):
        """The caller names the output file, so that is the file written."""
        source = tmp_path / "model.inp"
        source.write_bytes(INP_FILE.read_bytes())
        target = tmp_path / "somewhere" / "else.json"
        target.parent.mkdir()
        generated = WNTRINPJSONConverter.inp_to_json(source, json_path=target)
        assert Path(generated) == target
        assert target.exists()

    def test_a_non_inp_input_is_rejected(self, tmp_path):
        """Only .inp is a model; guessing at other extensions helps nobody."""
        source = tmp_path / "model.json"
        source.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a .inp file"):
            WNTRINPJSONConverter.inp_to_json(source)

    def test_the_string_form_checks_the_extension_too(self, tmp_path):
        """``inp_to_json_string`` guards itself, not just its caller.

        It is a public static method, so it can be called directly; relying on
        the caller's check would let a non-INP file reach WNTR's parser and
        produce an obscure error instead of a clear one.
        """
        source = tmp_path / "model.json"
        source.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a .inp file"):
            WNTRINPJSONConverter.inp_to_json_string(source)

    def test_a_missing_input_is_reported(self, tmp_path):
        """A path that does not exist is an error, not an empty model."""
        with pytest.raises(FileNotFoundError):
            WNTRINPJSONConverter.inp_to_json(tmp_path / "absent.inp")


class TestJsonToInp:
    """Writing the native format."""

    def test_an_explicit_output_path_is_honoured(self, converted, tmp_path):
        """The caller's ``inp_path`` must be the file that is written.

        This is the regression test for the bug described in the module
        docstring. The converter unconditionally overwrote its ``inp_path``
        argument with the input path's suffix swapped, so the requested name
        was discarded without any error.
        """
        target = tmp_path / "wanted_name.inp"
        generated = WNTRINPJSONConverter.json_to_inp(converted, inp_path=target)
        assert Path(generated) == target
        assert target.exists()
        # The name the caller did *not* ask for must not appear.
        assert not (tmp_path / "converted.inp").exists()

    def test_the_output_path_defaults_to_the_swapped_suffix(self, converted, tmp_path):
        """With no output path, the file lands beside the input, renamed."""
        local = tmp_path / "defaulted.json"
        local.write_bytes(converted.read_bytes())
        generated = WNTRINPJSONConverter.json_to_inp(local)
        assert Path(generated) == tmp_path / "defaulted.inp"
        assert Path(generated).exists()

    def test_the_requested_version_is_targeted(self, converted, tmp_path):
        """The caller chooses the EPANET version the output is written for.

        WNTR does not record the version in the file's header, so the effect is
        on the columns it emits. The tank ``Overflow`` column was added in
        EPANET 2.2, so a 2.2 target has it and a 2.0 target does not.
        """
        modern = tmp_path / "v22.inp"
        legacy = tmp_path / "v20.inp"
        WNTRINPJSONConverter.json_to_inp(converted, inp_path=modern, version=2.2)
        WNTRINPJSONConverter.json_to_inp(converted, inp_path=legacy, version=2.0)
        assert "Overflow" in modern.read_text(encoding="utf-8")
        assert "Overflow" not in legacy.read_text(encoding="utf-8")

    def test_a_non_json_input_is_rejected(self, tmp_path):
        """Only .json is accepted as input to this direction."""
        source = tmp_path / "model.inp"
        source.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="must have .json extension"):
            WNTRINPJSONConverter.json_to_inp(source)

    def test_a_missing_input_is_reported(self, tmp_path):
        """A path that does not exist is an error, not an empty model."""
        with pytest.raises(FileNotFoundError):
            WNTRINPJSONConverter.json_to_inp(tmp_path / "absent.json")

    def test_malformed_json_is_reported(self, tmp_path):
        """A corrupt document raises rather than writing an empty model."""
        source = tmp_path / "corrupt.json"
        source.write_text("{not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            WNTRINPJSONConverter.json_to_inp(source, inp_path=tmp_path / "out.inp")


class TestRoundTrip:
    """INP to JSON and back, which is what the pipeline actually does."""

    @pytest.mark.parametrize("collection", ["node_name_list", "link_name_list"])
    def test_component_names_survive(self, round_tripped, collection):
        """Every component keeps its name, or the model means something else.

        Names matter more than counts: a converter that renames a component
        silently breaks every rule and every reference to it.
        """
        import wntr

        original = wntr.network.WaterNetworkModel(str(INP_FILE))
        rebuilt = wntr.network.WaterNetworkModel(str(round_tripped))
        assert set(getattr(original, collection)) == set(getattr(rebuilt, collection))

    @pytest.mark.parametrize("collection", ["node_name_list", "link_name_list"])
    def test_component_counts_survive(self, round_tripped, collection):
        """No component is lost or duplicated by the round trip."""
        import wntr

        original = wntr.network.WaterNetworkModel(str(INP_FILE))
        rebuilt = wntr.network.WaterNetworkModel(str(round_tripped))
        assert len(getattr(original, collection)) == len(getattr(rebuilt, collection))

    def test_the_rebuilt_model_parses_and_validates(self, round_tripped):
        """The reconstructed INP is a model the toolkit can read back."""
        network, errors, _ = WNTREPANETNetwork.from_file(round_tripped)
        assert network is not None, f"rebuilt model did not parse: {errors}"
        assert network.report()["nodes"] > 0
        assert network.report()["links"] > 0

    def test_the_rebuilt_model_passes_the_core_ruleset(self, round_tripped):
        """A model that went out and came back is still a valid EPANET model.

        This is the strongest available statement that conversion is lossless
        for the fields the toolkit cares about. WNTR writes a subset of EPANET,
        so this does not claim byte fidelity; it claims that nothing the
        validator reads is lost.
        """
        network, errors, _ = WNTREPANETNetwork.from_file(round_tripped)
        assert network is not None, f"rebuilt model did not parse: {errors}"
        report = network.validate()
        assert report.is_valid, "\n".join(
            f"{issue.code} {issue.component_name}: {issue.message}" for issue in report
        )


class TestSuffixReplacement:
    """The path helper the CLI uses to pick a default output name."""

    def test_the_suffix_is_replaced(self):
        """The base name is kept and only the extension changes."""
        assert (
            WNTRINPJSONConverter.replace_file_suffix("a/b/model.inp", ".json")
            == Path("a/b/model.json")
        )
